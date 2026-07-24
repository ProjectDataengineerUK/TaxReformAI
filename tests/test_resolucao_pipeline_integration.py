import datetime
import subprocess
from pathlib import Path

from ingestion.chunking.chunk_models import Chunk
from ingestion.embedding.hybrid_embedder import EmbeddedChunk
from ingestion.parser.resolucao_parser import parse_resolucao
from ingestion.pipeline import executar_pipeline
from ingestion.storage.raw_storage import FakeInMemoryStorage

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "resolucao_tcu_sample.pdf"


class FakeTCUSource:
    """Substitui TCUScraper — evita chamada de rede real em teste automatizado
    (mesmo padrão de FakeLegalSource em test_pipeline_integration.py)."""

    def __init__(self, storage: FakeInMemoryStorage):
        self._storage = storage

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        pdf_bytes = FIXTURE_PATH.read_bytes()
        uri = self._storage.save(f"raw/tcu/{documento_id}/test.pdf", pdf_bytes)
        texto = subprocess.run(
            ["pdftotext", "-layout", str(FIXTURE_PATH), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return texto, uri


class FakeEmbedder:
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(chunk=c, dense_vector=[0.1, 0.2, 0.3], sparse_indices=[1], sparse_values=[0.5])
            for c in chunks
        ]


class FakeIndexer:
    def __init__(self):
        self.collection_created = False
        self.upserted: list[EmbeddedChunk] = []

    def ensure_collection(self, dense_vector_size: int) -> None:
        self.collection_created = True

    def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> int:
        self.upserted.extend(embedded_chunks)
        return len(embedded_chunks)


def test_at001_pdf_tcu_ate_qdrant_sem_modificar_chunker():
    storage = FakeInMemoryStorage()
    indexer = FakeIndexer()

    resumo = executar_pipeline(
        url="https://rotadajurisprudencia.com.br/wp-content/uploads/2026/06/Resolucao-TCU-388_2026.pdf",
        documento_id="TCU_RES_388_2026",
        titulo="Resolução TCU 388/2026",
        esfera="FEDERAL_CBS_IBS_METODOLOGIA",
        data_vigencia_inicio=datetime.date(2026, 6, 10),
        scraper=FakeTCUSource(storage),
        embedder=FakeEmbedder(),
        indexer=indexer,
        parser=parse_resolucao,
    )

    assert resumo["artigos"] == 16
    assert resumo["chunks"] > 0
    assert resumo["chunks_com_erro"] == 0
    assert indexer.collection_created
    assert len(indexer.upserted) == resumo["chunks"]
    assert storage._data, "o PDF bruto deveria ter sido salvo no storage"

    dispositivos = {c.chunk.dispositivo for c in indexer.upserted}
    assert "Art. 1" in dispositivos
    assert "Art. 16" in dispositivos


def test_chunks_do_tcu_tem_mesmos_campos_obrigatorios_do_planalto():
    storage = FakeInMemoryStorage()
    resumo = executar_pipeline(
        url="https://x/resolucao.pdf",
        documento_id="TCU_RES_388_2026",
        titulo="Resolução TCU 388/2026",
        esfera="FEDERAL_CBS_IBS_METODOLOGIA",
        data_vigencia_inicio=datetime.date(2026, 6, 10),
        scraper=FakeTCUSource(storage),
        embedder=FakeEmbedder(),
        indexer=FakeIndexer(),
        parser=parse_resolucao,
    )
    assert resumo["chunks_com_erro"] == 0
