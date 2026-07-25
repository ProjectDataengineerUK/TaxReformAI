"""O upsert precisa ir em lotes: a primeira ingestão real da LCP 214/2025
gerou 2547 chunks, e num upsert único a Qdrant Cloud recusou o corpo com
"JSON payload (57359697 bytes) is larger than allowed". O erro aparece só
depois dos ~20 min de embedding, que é a etapa cara do pipeline.

`QdrantIndexer.__init__` constrói um QdrantClient real (rede), então os testes
instanciam a classe sem chamar o __init__ e injetam um cliente falso — o que
está sob teste é a política de lotes do upsert, não o cliente.
"""

import sys
import types
from datetime import date

import pytest

from ingestion.chunking.chunk_models import Chunk
from ingestion.embedding.hybrid_embedder import EmbeddedChunk
from ingestion.indexing.qdrant_indexer import TAMANHO_LOTE_UPSERT, QdrantIndexer


def _garantir_qdrant_models() -> None:
    """`upsert()` importa PointStruct/SparseVector de `qdrant_client.models`.

    O pacote instala no CI (está em requirements.txt) mas não neste sandbox. Em
    vez de pular o teste — o que o tornaria inútil justamente onde a correção
    precisa ser verificada agora — instala-se um stub mínimo só quando o pacote
    real está ausente. No CI o teste exercita o código real, sem stub nenhum.
    """
    try:
        import qdrant_client.models  # noqa: F401

        return
    except ImportError:
        pass

    class PointStruct:
        def __init__(self, id, vector, payload):
            self.id, self.vector, self.payload = id, vector, payload

    class SparseVector:
        def __init__(self, indices, values):
            self.indices, self.values = indices, values

    pacote = types.ModuleType("qdrant_client")
    modelos = types.ModuleType("qdrant_client.models")
    modelos.PointStruct = PointStruct
    modelos.SparseVector = SparseVector
    pacote.models = modelos
    sys.modules.setdefault("qdrant_client", pacote)
    sys.modules.setdefault("qdrant_client.models", modelos)


_garantir_qdrant_models()


class FakeQdrantClient:
    def __init__(self):
        self.lotes: list[int] = []
        self.ids_recebidos: list[str] = []

    def upsert(self, collection_name: str, points: list):
        self.lotes.append(len(points))
        self.ids_recebidos.extend(p.id for p in points)


def _indexer_com_cliente_falso() -> tuple[QdrantIndexer, FakeQdrantClient]:
    indexer = QdrantIndexer.__new__(QdrantIndexer)
    fake = FakeQdrantClient()
    indexer._client = fake
    indexer._collection_name = "teste"
    return indexer, fake


def _embedded(n: int) -> list[EmbeddedChunk]:
    return [
        EmbeddedChunk(
            chunk=Chunk(
                documento_id="LCP_214_2025",
                dispositivo=f"Art. {i}",
                esfera="FEDERAL_CBS_IBS",
                data_vigencia_inicio=date(2026, 1, 1),
                texto=f"texto do artigo {i}",
                fonte_url="https://exemplo/lei",
            ),
            dense_vector=[0.1, 0.2],
            sparse_indices=[1],
            sparse_values=[0.5],
        )
        for i in range(n)
    ]


@pytest.mark.parametrize("n", [1, TAMANHO_LOTE_UPSERT - 1, TAMANHO_LOTE_UPSERT])
def test_ate_um_lote_faz_uma_requisicao(n):
    indexer, fake = _indexer_com_cliente_falso()
    assert indexer.upsert(_embedded(n)) == n
    assert fake.lotes == [n]


def test_2547_chunks_viram_varios_lotes_pequenos():
    """O número real da LCP 214/2025 — o caso que quebrou em produção."""
    indexer, fake = _indexer_com_cliente_falso()

    assert indexer.upsert(_embedded(2547)) == 2547

    assert len(fake.lotes) == 26, "2547 pontos = 25 lotes cheios + 1 de 47"
    assert max(fake.lotes) <= TAMANHO_LOTE_UPSERT
    assert sum(fake.lotes) == 2547


def test_nenhum_ponto_e_perdido_nem_duplicado_entre_lotes():
    indexer, fake = _indexer_com_cliente_falso()
    embedded = _embedded(250)

    indexer.upsert(embedded)

    esperados = [e.chunk.qdrant_point_id() for e in embedded]
    assert fake.ids_recebidos == esperados
    assert len(set(fake.ids_recebidos)) == 250


def test_lista_vazia_nao_chama_o_cliente():
    indexer, fake = _indexer_com_cliente_falso()
    assert indexer.upsert([]) == 0
    assert fake.lotes == []
