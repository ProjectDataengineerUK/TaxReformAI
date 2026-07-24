import datetime
import json
import logging
from typing import Protocol

from ingestion.chunking.chunk_models import Chunk
from ingestion.chunking.chunker import gerar_chunks
from ingestion.embedding.hybrid_embedder import EmbeddedChunk
from ingestion.parser.ast_models import Secao
from ingestion.parser.ast_parser import ASTParseError, parse_lei
from ingestion.scraper.planalto_scraper import LegalSource

logging.basicConfig(
    level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":%(message)r}'
)
logger = logging.getLogger("ingestion.pipeline")


class Indexer(Protocol):
    def ensure_collection(self, dense_vector_size: int) -> None: ...
    def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> int: ...


class Embedder(Protocol):
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...


def _contar_artigos(secao: Secao) -> int:
    n = len(secao.artigos)
    for sub in secao.subsecoes:
        n += _contar_artigos(sub)
    return n


def executar_pipeline(
    *,
    url: str,
    documento_id: str,
    titulo: str,
    esfera: str,
    data_vigencia_inicio: datetime.date,
    scraper: LegalSource,
    embedder: Embedder,
    indexer: Indexer,
    data_vigencia_fim: datetime.date | None = None,
    regime: str | None = None,
) -> dict:
    """Orquestra scraper -> parser -> chunker -> embedder -> indexer.

    As dependências (scraper/embedder/indexer) são injetadas para permitir
    testes de integração com fakes/stubs, sem exigir GCP/Qdrant/modelos de
    ML reais (ver DESIGN, Testing Strategy).
    """
    resumo = {"documento_id": documento_id, "artigos": 0, "chunks": 0, "chunks_com_erro": 0}

    logger.info(json.dumps({"etapa": "scrape", "url": url}))
    html, raw_uri = scraper.fetch(url, documento_id)
    logger.info(json.dumps({"etapa": "scrape", "status": "ok", "raw_uri": raw_uri}))

    logger.info(json.dumps({"etapa": "parse", "status": "iniciando"}))
    lei = parse_lei(html, documento_id=documento_id, titulo=titulo, fonte_url=url)
    total_artigos = len(lei.artigos_soltos) + sum(_contar_artigos(s) for s in lei.secoes)
    resumo["artigos"] = total_artigos
    logger.info(json.dumps({"etapa": "parse", "status": "ok", "artigos": total_artigos}))

    logger.info(json.dumps({"etapa": "chunk", "status": "iniciando"}))
    chunks = gerar_chunks(
        lei,
        esfera=esfera,
        data_vigencia_inicio=data_vigencia_inicio,
        data_vigencia_fim=data_vigencia_fim,
        regime=regime,
    )
    resumo["chunks"] = len(chunks)
    logger.info(json.dumps({"etapa": "chunk", "status": "ok", "chunks": len(chunks)}))

    logger.info(json.dumps({"etapa": "embed", "status": "iniciando"}))
    embedded_chunks: list[EmbeddedChunk] = []
    for chunk in chunks:
        try:
            embedded_chunks.extend(embedder.embed([chunk]))
        except Exception as exc:  # noqa: BLE001 — erro de inferência não aborta o restante
            resumo["chunks_com_erro"] += 1
            logger.error(
                json.dumps({"etapa": "embed", "dispositivo": chunk.dispositivo, "erro": str(exc)})
            )
    logger.info(json.dumps({"etapa": "embed", "status": "ok", "embutidos": len(embedded_chunks)}))

    logger.info(json.dumps({"etapa": "index", "status": "iniciando"}))
    dense_size = len(embedded_chunks[0].dense_vector) if embedded_chunks else 1024
    indexer.ensure_collection(dense_vector_size=dense_size)
    indexed_count = indexer.upsert(embedded_chunks)
    logger.info(json.dumps({"etapa": "index", "status": "ok", "indexados": indexed_count}))

    logger.info(json.dumps({"etapa": "resumo", **resumo}))
    return resumo


def _build_cli():
    """CLI isolada atrás de uma factory — `executar_pipeline` acima não
    depende de `typer` para ser importado/testado (ver test_pipeline_integration.py)."""
    import typer

    from ingestion.config import Settings

    app = typer.Typer()

    @app.command()
    def run(
        url: str = typer.Option(..., help="URL da lei no Planalto"),
        documento_id: str = typer.Option(..., help='Ex: "LCP_214_2025"'),
        titulo: str = typer.Option(..., help="Título legível da lei"),
        esfera: str = typer.Option(..., help='Ex: "FEDERAL_CBS_IBS"'),
        data_vigencia_inicio: str = typer.Option(..., help="YYYY-MM-DD"),
        data_vigencia_fim: str = typer.Option(None, help="YYYY-MM-DD, opcional"),
        regime: str = typer.Option(None),
    ) -> None:
        settings = Settings.from_env()

        from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
        from ingestion.indexing.qdrant_indexer import QdrantIndexer
        from ingestion.scraper.planalto_scraper import PlanaltoScraper
        from ingestion.storage.raw_storage import GCSRawStorage

        storage = GCSRawStorage(
            bucket_name=settings.gcs_bucket_name, project_id=settings.gcp_project_id
        )
        scraper = PlanaltoScraper(
            storage=storage,
            timeout_seconds=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )
        embedder = FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model)
        indexer = QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        )

        try:
            resumo = executar_pipeline(
                url=url,
                documento_id=documento_id,
                titulo=titulo,
                esfera=esfera,
                data_vigencia_inicio=datetime.date.fromisoformat(data_vigencia_inicio),
                data_vigencia_fim=(
                    datetime.date.fromisoformat(data_vigencia_fim)
                    if data_vigencia_fim
                    else None
                ),
                regime=regime,
                scraper=scraper,
                embedder=embedder,
                indexer=indexer,
            )
        except (ASTParseError, RuntimeError) as exc:
            logger.error(json.dumps({"etapa": "pipeline", "erro": str(exc)}))
            raise typer.Exit(code=1) from exc

        typer.echo(json.dumps(resumo, ensure_ascii=False, indent=2))

    return app


if __name__ == "__main__":
    _build_cli()()
