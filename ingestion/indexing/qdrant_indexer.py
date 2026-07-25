from ingestion.embedding.hybrid_embedder import EmbeddedChunk

# A LCP 214/2025 gera 2547 chunks; num upsert único isso vira um corpo JSON de
# ~57 MB e a Qdrant Cloud recusa:
#   {"status":{"error":"JSON payload (57359697 bytes) is larger than allowed"}}
# Isso só apareceu na primeira ingestão real, depois de 20 minutos embedando —
# a etapa mais cara do pipeline roda inteira antes de o índice ser tocado.
#
# ~22 KB por ponto (1024 floats densos + esparso + payload com o texto do
# artigo). 100 pontos por lote dá ~2,2 MB, com folga larga sob o limite, sem
# transformar a ingestão numa sequência de milhares de requisições.
TAMANHO_LOTE_UPSERT = 100


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
        for inicio in range(0, len(points), TAMANHO_LOTE_UPSERT):
            lote = points[inicio : inicio + TAMANHO_LOTE_UPSERT]
            self._client.upsert(collection_name=self._collection_name, points=lote)
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
