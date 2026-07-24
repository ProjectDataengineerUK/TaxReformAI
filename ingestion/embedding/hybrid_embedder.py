from dataclasses import dataclass
from typing import Protocol

from ingestion.chunking.chunk_models import Chunk


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    dense_vector: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


@dataclass
class EmbeddedQuery:
    """Lado da consulta. Separado de EmbeddedChunk porque uma consulta não tem
    Chunk de origem — e porque BM25 pondera consulta e documento de formas
    diferentes (ver embed_consulta)."""

    dense_vector: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


class Embedder(Protocol):
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...


class FastEmbedHybridEmbedder:
    """Gera vetor denso (BGE-M3) + esparso (BM25) por chunk via `fastembed`
    (Decision 4 do DESIGN — busca híbrida nativa do Qdrant)."""

    def __init__(self, dense_model_name: str = "BAAI/bge-m3"):
        from fastembed import SparseTextEmbedding, TextEmbedding

        self._dense_model = TextEmbedding(model_name=dense_model_name)
        self._sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def _texto_para_embedding(self, chunk: Chunk) -> str:
        if chunk.parent_texto and chunk.parent_texto != chunk.texto:
            return f"{chunk.parent_texto}\n{chunk.texto}"
        return chunk.texto

    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        textos = [self._texto_para_embedding(c) for c in chunks]
        dense_vectors = list(self._dense_model.embed(textos))
        sparse_vectors = list(self._sparse_model.embed(textos))

        resultado: list[EmbeddedChunk] = []
        for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors):
            resultado.append(
                EmbeddedChunk(
                    chunk=chunk,
                    dense_vector=dense.tolist(),
                    sparse_indices=sparse.indices.tolist(),
                    sparse_values=sparse.values.tolist(),
                )
            )
        return resultado

    def embed_consulta(self, texto: str) -> EmbeddedQuery:
        """Contraparte de `embed()` para o lado da consulta — sem isto,
        `QdrantIndexer.search_hybrid()` não tinha como ser chamado.

        Usa `query_embed`, não `embed`: no BM25 o vetor esparso de consulta é
        construído de forma diferente do de documento (sem a ponderação por
        frequência do documento). Embutir a consulta com `embed()` produziria
        pontuações esparsas silenciosamente erradas.
        """
        dense = next(iter(self._dense_model.query_embed(texto)))
        sparse = next(iter(self._sparse_model.query_embed(texto)))
        return EmbeddedQuery(
            dense_vector=dense.tolist(),
            sparse_indices=sparse.indices.tolist(),
            sparse_values=sparse.values.tolist(),
        )
