import datetime
from pathlib import Path

from ingestion.chunking.chunk_models import Chunk
from ingestion.embedding.hybrid_embedder import EmbeddedChunk
from ingestion.pipeline import executar_pipeline
from ingestion.storage.raw_storage import FakeInMemoryStorage

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_lei.html"


class FakeLegalSource:
    """Substitui o PlanaltoScraper — devolve o fixture local em vez de
    fazer uma chamada de rede real (Decision 5 do DESIGN)."""

    def __init__(self, html: str, storage: FakeInMemoryStorage):
        self._html = html
        self._storage = storage

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        uri = self._storage.save(f"raw/planalto/{documento_id}/test.html", self._html.encode())
        return self._html, uri


class FakeEmbedder:
    """Vetores determinísticos e baratos — evita baixar o modelo BGE-M3 real."""

    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(chunk=c, dense_vector=[0.1, 0.2, 0.3], sparse_indices=[1], sparse_values=[0.5])
            for c in chunks
        ]


class FailingEmbedder:
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        raise RuntimeError("modelo de embedding indisponível (simulado)")


class FakeIndexer:
    def __init__(self):
        self.collection_created = False
        self.upserted: list[EmbeddedChunk] = []

    def ensure_collection(self, dense_vector_size: int) -> None:
        self.collection_created = True
        self.dense_vector_size = dense_vector_size

    def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> int:
        self.upserted.extend(embedded_chunks)
        return len(embedded_chunks)


def _run(embedder=None):
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    storage = FakeInMemoryStorage()
    scraper = FakeLegalSource(html, storage)
    indexer = FakeIndexer()
    resumo = executar_pipeline(
        url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
        documento_id="LCP_214_2025",
        titulo="Lei Complementar 214/2025",
        esfera="FEDERAL_CBS_IBS",
        data_vigencia_inicio=datetime.date(2027, 1, 1),
        scraper=scraper,
        embedder=embedder or FakeEmbedder(),
        indexer=indexer,
    )
    return resumo, storage, indexer


def test_at001_happy_path_ponta_a_ponta():
    resumo, storage, indexer = _run()

    assert resumo["artigos"] == 11
    assert resumo["chunks"] == 117
    assert resumo["chunks_com_erro"] == 0
    assert indexer.collection_created
    assert len(indexer.upserted) == 117
    assert storage._data, "o HTML raw deveria ter sido salvo no storage"


def test_at002_html_invalido_aborta_sem_indexar():
    class FakeLegalSourceHtmlRuim:
        def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
            return "<html><body><p>nada aqui</p></body></html>", "memory://x"

    indexer = FakeIndexer()
    import pytest

    from ingestion.parser.ast_parser import ASTParseError

    with pytest.raises(ASTParseError):
        executar_pipeline(
            url="https://x",
            documento_id="X",
            titulo="x",
            esfera="FEDERAL_CBS_IBS",
            data_vigencia_inicio=datetime.date(2027, 1, 1),
            scraper=FakeLegalSourceHtmlRuim(),
            embedder=FakeEmbedder(),
            indexer=indexer,
        )
    assert not indexer.upserted, "nada deveria ser indexado quando o parsing falha"


def test_falha_de_embedding_por_chunk_nao_aborta_o_restante():
    resumo, _, indexer = _run(embedder=FailingEmbedder())

    assert resumo["chunks"] == 117
    assert resumo["chunks_com_erro"] == 117
    assert indexer.upserted == []
