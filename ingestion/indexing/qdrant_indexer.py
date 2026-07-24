from ingestion.embedding.hybrid_embedder import EmbeddedChunk


class QdrantIndexer:
    """Conecta na Qdrant Cloud, garante a coleção (named vectors dense+sparse)
    e faz upsert dos chunks (Decision 4 do DESIGN)."""

    def __init__(self, url: str, api_key: str, collection_name: str):
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=url, api_key=api_key)
        self._collection_name = collection_name

    def ensure_collection(self, dense_vector_size: int) -> None:
        from qdrant_client.models import Distance, SparseVectorParams, VectorParams

        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection_name in existing:
            return

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config={"dense": VectorParams(size=dense_vector_size, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="data_vigencia_inicio",
            field_schema="datetime",
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="documento_id",
            field_schema="keyword",
        )

    def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> int:
        from qdrant_client.models import PointStruct, SparseVector

        points = [
            PointStruct(
                id=ec.chunk.qdrant_point_id(),
                vector={
                    "dense": ec.dense_vector,
                    "sparse": SparseVector(indices=ec.sparse_indices, values=ec.sparse_values),
                },
                payload=ec.chunk.model_dump(mode="json"),
            )
            for ec in embedded_chunks
        ]
        if not points:
            return 0
        self._client.upsert(collection_name=self._collection_name, points=points)
        return len(points)

    def search_hybrid(self, dense_query: list[float], sparse_indices: list[int], sparse_values: list[float], limit: int = 5):
        from qdrant_client.models import FusionQuery, Prefetch, SparseVector

        return self._client.query_points(
            collection_name=self._collection_name,
            prefetch=[
                Prefetch(query=dense_query, using="dense", limit=limit * 2),
                Prefetch(
                    query=SparseVector(indices=sparse_indices, values=sparse_values),
                    using="sparse",
                    limit=limit * 2,
                ),
            ],
            query=FusionQuery(fusion="rrf"),
            limit=limit,
        )
