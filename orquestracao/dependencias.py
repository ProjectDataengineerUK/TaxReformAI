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


def criar_dependencias_reais(settings: OrquestracaoSettings) -> DependenciasOrquestracao:
    from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
    from ingestion.indexing.qdrant_indexer import QdrantIndexer

    cliente_llm: ClienteLLM
    if settings.llm_provider == "vertex":
        cliente_llm = ClienteVertexAI(
            project_id=settings.gcp_project_id, region=settings.vertex_ai_region
        )
    else:
        cliente_llm = ClienteAnthropicDireto(api_key=settings.anthropic_api_key)

    return DependenciasOrquestracao(
        cliente_llm=cliente_llm,
        qdrant_indexer=QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        ),
        embedder=FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model),
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
) -> DependenciasOrquestracao:
    from orquestracao.llm.cliente import ClienteLLMFake

    return DependenciasOrquestracao(
        cliente_llm=cliente_llm or ClienteLLMFake(),
        qdrant_indexer=FakeQdrantSearcher(chunks=chunks),
        embedder=FakeEmbedder(),
    )
