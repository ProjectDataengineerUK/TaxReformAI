from dataclasses import dataclass
from typing import Protocol

from ingestion.chunking.chunk_models import Chunk
from orquestracao.config import OrquestracaoSettings
from orquestracao.llm.cliente import ClienteAnthropicDireto, ClienteLLM, ClienteVertexAI


class _EmbeddedQueryLike(Protocol):
    dense_vector: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


class Embedder(Protocol):
    def embed_consulta(self, texto: str) -> _EmbeddedQueryLike: ...


class QdrantSearcher(Protocol):
    def search_hybrid(
        self,
        dense_query: list[float],
        sparse_indices: list[int],
        sparse_values: list[float],
        limit: int = 5,
        documento_id: str | None = None,
    ): ...


@dataclass
class DependenciasOrquestracao:
    cliente_llm: ClienteLLM
    qdrant_indexer: QdrantSearcher
    embedder: Embedder
    # COMPARATIVO_REGIME_ATUAL_IVA_DUAL: no_deterministico precisa de
    # db_pool para chamar api.simulacao.calcular_simulacao_completa()
    # (Anexos de redução, IPI, catálogo de SKUs). `None` em teste continua
    # funcionando para os nós que não o tocam — mesmo padrão de
    # opcionalidade já usado no registrador de uso de LLM.
    db_pool: object = None


def criar_dependencias_reais(settings: OrquestracaoSettings, db_pool=None) -> DependenciasOrquestracao:
    from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
    from ingestion.indexing.qdrant_indexer import QdrantIndexer
    from orquestracao.llm.registrador import RegistradorUsoLLMPostgres

    # PAINEL_OBSERVABILIDADE: db_pool é opcional (mesmo estado de
    # api/db.py::get_db_pool() sem Cloud SQL configurado) — o registrador
    # devolvido lida com pool=None sozinho, nunca bloqueia a chamada ao LLM.
    registrador = RegistradorUsoLLMPostgres(db_pool)

    cliente_llm: ClienteLLM
    if settings.llm_provider == "vertex":
        cliente_llm = ClienteVertexAI(
            project_id=settings.gcp_project_id, region=settings.vertex_ai_region, registrador=registrador
        )
    else:
        cliente_llm = ClienteAnthropicDireto(api_key=settings.anthropic_api_key, registrador=registrador)

    return DependenciasOrquestracao(
        cliente_llm=cliente_llm,
        qdrant_indexer=QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        ),
        embedder=FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model),
        db_pool=db_pool,
    )


class FakeEmbedder:
    """Usado apenas em tests/ — devolve um `EmbeddedQuery` fixo, sem `fastembed`
    (não instalável neste sandbox, mesma situação de `ingestion/`)."""

    def __init__(self, dense_vector: list[float] | None = None):
        self._dense_vector = dense_vector or [0.1, 0.2, 0.3]

    def embed_consulta(self, texto: str):
        from ingestion.embedding.hybrid_embedder import EmbeddedQuery

        return EmbeddedQuery(
            dense_vector=self._dense_vector, sparse_indices=[1, 2], sparse_values=[0.5, 0.5]
        )


class FakeQdrantSearcher:
    """Usado apenas em tests/ — devolve pontos fixos no formato de
    `query_points` real (`.points`, cada um com `.payload`)."""

    def __init__(self, chunks: list[Chunk] | None = None):
        self._chunks = chunks if chunks is not None else []

    def search_hybrid(
        self,
        dense_query: list[float],
        sparse_indices: list[int],
        sparse_values: list[float],
        limit: int = 5,
        documento_id: str | None = None,
    ):
        from types import SimpleNamespace

        pontos = [
            SimpleNamespace(payload=chunk.model_dump(mode="json")) for chunk in self._chunks
        ]
        return SimpleNamespace(points=pontos)


def criar_dependencias_fake(
    cliente_llm: ClienteLLM | None = None,
    chunks: list[Chunk] | None = None,
    db_pool=None,
) -> DependenciasOrquestracao:
    from orquestracao.llm.cliente import ClienteLLMFake

    return DependenciasOrquestracao(
        cliente_llm=cliente_llm or ClienteLLMFake(),
        qdrant_indexer=FakeQdrantSearcher(chunks=chunks),
        embedder=FakeEmbedder(),
        db_pool=db_pool,
    )
