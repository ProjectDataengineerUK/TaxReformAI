import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OrquestracaoSettings:
    gcp_project_id: str
    vertex_ai_region: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str
    dense_embedding_model: str

    @classmethod
    def from_env(cls) -> "OrquestracaoSettings":
        from ingestion.embedding.hybrid_embedder import MODELO_DENSO_PADRAO

        missing = [
            var
            for var in ("GCP_PROJECT_ID", "QDRANT_URL", "QDRANT_API_KEY")
            if not os.environ.get(var)
        ]
        if missing:
            raise RuntimeError(
                f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}."
            )
        return cls(
            gcp_project_id=os.environ["GCP_PROJECT_ID"],
            vertex_ai_region=os.environ.get("VERTEX_AI_REGION", "global"),
            qdrant_url=os.environ["QDRANT_URL"],
            qdrant_api_key=os.environ["QDRANT_API_KEY"],
            qdrant_collection_name=os.environ.get(
                "QDRANT_COLLECTION_NAME", "legislacao_tributaria"
            ),
            dense_embedding_model=os.environ.get(
                "DENSE_EMBEDDING_MODEL", MODELO_DENSO_PADRAO
            ),
        )
