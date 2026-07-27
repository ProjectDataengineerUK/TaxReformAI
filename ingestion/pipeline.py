import datetime
import json
import logging
from collections.abc import Callable
from typing import Protocol

from ingestion.chunking.chunk_models import Chunk
from ingestion.chunking.chunker import gerar_chunks
from ingestion.embedding.hybrid_embedder import EmbeddedChunk
from ingestion.parser.ast_models import Lei, Secao
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
    parser: Callable[..., Lei] = parse_lei,
    prefixo_dispositivo: str = "Art.",
) -> dict:
    """Orquestra scraper -> parser -> chunker -> embedder -> indexer.

    As dependências (scraper/embedder/indexer) são injetadas para permitir
    testes de integração com fakes/stubs, sem exigir GCP/Qdrant/modelos de
    ML reais (ver DESIGN, Testing Strategy). `parser` default `parse_lei`
    (Planalto/HTML); TCU passa `resolucao_parser.parse_resolucao` (ver
    DESIGN de INGESTAO_TCU_E_ETL_AIRFLOW, Decision 3) — mesma assinatura
    (texto, documento_id, titulo, fonte_url) -> Lei em ambos os casos.
    """
    resumo = {"documento_id": documento_id, "artigos": 0, "chunks": 0, "chunks_com_erro": 0}

    logger.info(json.dumps({"etapa": "scrape", "url": url}))
    conteudo, raw_uri = scraper.fetch(url, documento_id)
    logger.info(json.dumps({"etapa": "scrape", "status": "ok", "raw_uri": raw_uri}))

    logger.info(json.dumps({"etapa": "parse", "status": "iniciando"}))
    lei = parser(conteudo, documento_id=documento_id, titulo=titulo, fonte_url=url)
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
        prefixo_dispositivo=prefixo_dispositivo,
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


def construir_fonte(
    fonte: str,
    storage,
    *,
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> tuple[LegalSource, Callable[..., Lei], str]:
    """Mapeia o nome de uma fonte para o par (scraper, parser) que a atende.

    Planalto (HTML) e TCU (PDF via pdftotext) têm construtores e parsers de
    assinatura idêntica — foi exatamente isso que `INGESTAO_TCU_E_ETL_AIRFLOW`
    provou ao adicionar a segunda fonte sem tocar em `chunker.py`. O registro
    abaixo só torna essa equivalência explícita, para que a CLI (e portanto o
    workflow de ingestão) não precise de um comando por fonte.

    Fora de `_build_cli()` de propósito: assim é testável sem `typer`, que não
    instala neste sandbox.
    """
    from ingestion.parser.ementa_parser import PREFIXO_DISPOSITIVO, parse_ementas
    from ingestion.parser.resolucao_parser import parse_resolucao
    from ingestion.scraper.cgibs_scraper import CGIBSScraper
    from ingestion.scraper.planalto_scraper import PlanaltoScraper
    from ingestion.scraper.rfb_scraper import RFBScraper
    from ingestion.scraper.tcu_scraper import TCUScraper

    # (scraper, parser, prefixo do rótulo de dispositivo). O prefixo entra no
    # registro porque citar uma Solução de Consulta como "Art. 6006" seria uma
    # citação falsa — e a citação é o que o produto promete como auditável.
    fontes: dict[str, tuple[type, Callable[..., Lei], str]] = {
        "planalto": (PlanaltoScraper, parse_lei, "Art."),
        "tcu": (TCUScraper, parse_resolucao, "Art."),
        # CGIBS é PDF como o TCU, então reaproveita parse_resolucao inteiro.
        "cgibs": (CGIBSScraper, parse_resolucao, "Art."),
        # RFB entrega uma página de resultados com muitos atos, não um
        # documento com hierarquia — daí parser e prefixo próprios.
        "rfb": (RFBScraper, parse_ementas, PREFIXO_DISPOSITIVO),
    }
    if fonte not in fontes:
        raise ValueError(
            f"Fonte desconhecida: {fonte!r}. Conhecidas: {sorted(fontes)}"
        )
    classe_scraper, parser, prefixo = fontes[fonte]
    scraper = classe_scraper(
        storage, timeout_seconds=timeout_seconds, max_retries=max_retries
    )
    return scraper, parser, prefixo


def _build_cli():
    """CLI isolada atrás de uma factory — `executar_pipeline` acima não
    depende de `typer` para ser importado/testado (ver test_pipeline_integration.py)."""
    import typer

    from ingestion.config import Settings

    app = typer.Typer()

    @app.callback()
    def _main() -> None:
        """Pipeline de ingestão legal.

        O callback existe só para forçar o modo multi-comando: um Typer app com
        um único `@app.command()` e sem callback é achatado, e aí `... pipeline
        run --url ...` falha com "unexpected extra argument (run)". A invocação
        documentada (e usada por .github/workflows/ingestao.yml) passa `run`.
        """

    @app.command()
    def run(
        url: str = typer.Option(..., help="URL da lei no Planalto"),
        documento_id: str = typer.Option(..., help='Ex: "LCP_214_2025"'),
        titulo: str = typer.Option(..., help="Título legível da lei"),
        esfera: str = typer.Option(..., help='Ex: "FEDERAL_CBS_IBS"'),
        data_vigencia_inicio: str = typer.Option(..., help="YYYY-MM-DD"),
        data_vigencia_fim: str = typer.Option(None, help="YYYY-MM-DD, opcional"),
        regime: str = typer.Option(None),
        fonte: str = typer.Option("planalto", help="planalto | tcu | cgibs | rfb"),
        termo_busca: str = typer.Option(
            None,
            help="Só para --fonte rfb: termo da consulta ao SIJUT2. "
            "Estreite-o — a busca casa palavras soltas e resultados grandes "
            "vêm truncados (o parser falha alto nesse caso).",
        ),
        tipo_ato: str = typer.Option(
            None,
            help="Só para --fonte rfb: código do tipo de ato no SIJUT2 "
            '(72 = Solução de Consulta, o default; 9 = Ato Declaratório '
            "Executivo). Sem isto, usa o default de montar_url_busca().",
        ),
    ) -> None:
        settings = Settings.from_env()

        if fonte == "rfb" and termo_busca:
            from ingestion.scraper.rfb_scraper import montar_url_busca

            kwargs = {"tipo_ato": tipo_ato} if tipo_ato else {}
            url = montar_url_busca(termo_busca, **kwargs)

        from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
        from ingestion.indexing.qdrant_indexer import QdrantIndexer
        from ingestion.storage.raw_storage import GCSRawStorage

        storage = GCSRawStorage(
            bucket_name=settings.gcs_bucket_name, project_id=settings.gcp_project_id
        )
        try:
            scraper, parser, prefixo_dispositivo = construir_fonte(
                fonte,
                storage,
                timeout_seconds=settings.request_timeout_seconds,
                max_retries=settings.max_retries,
            )
        except ValueError as exc:
            logger.error(json.dumps({"etapa": "fonte", "erro": str(exc)}))
            raise typer.Exit(code=1) from exc
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
                parser=parser,
                prefixo_dispositivo=prefixo_dispositivo,
            )
        except (ASTParseError, RuntimeError) as exc:
            logger.error(json.dumps({"etapa": "pipeline", "erro": str(exc)}))
            raise typer.Exit(code=1) from exc

        typer.echo(json.dumps(resumo, ensure_ascii=False, indent=2))

    return app


if __name__ == "__main__":
    _build_cli()()
