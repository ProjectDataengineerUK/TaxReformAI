import os
from dataclasses import dataclass

from ingestion.embedding.hybrid_embedder import MODELO_DENSO_PADRAO


@dataclass(frozen=True)
class Settings:
    planalto_base_url: str
    gcp_project_id: str
    gcs_bucket_name: str
    gcp_region: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str
    dense_embedding_model: str
    chunk_parent_level: str
    request_timeout_seconds: int
    max_retries: int

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [
            var
            for var in ("GCP_PROJECT_ID", "GCS_BUCKET_NAME", "QDRANT_URL", "QDRANT_API_KEY")
            if not os.environ.get(var)
        ]
        if missing:
            raise RuntimeError(
                f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}. "
                "Copie .env.example para .env e preencha os valores."
            )
        return cls(
            planalto_base_url=os.environ.get("PLANALTO_BASE_URL", "https://www.planalto.gov.br"),
            gcp_project_id=os.environ["GCP_PROJECT_ID"],
            gcs_bucket_name=os.environ["GCS_BUCKET_NAME"],
            gcp_region=os.environ.get("GCP_REGION", "southamerica-east1"),
            qdrant_url=os.environ["QDRANT_URL"],
            qdrant_api_key=os.environ["QDRANT_API_KEY"],
            qdrant_collection_name=os.environ.get(
                "QDRANT_COLLECTION_NAME", "legislacao_tributaria"
            ),
            dense_embedding_model=os.environ.get(
                "DENSE_EMBEDDING_MODEL", MODELO_DENSO_PADRAO
            ),
            chunk_parent_level=os.environ.get("CHUNK_PARENT_LEVEL", "artigo"),
            request_timeout_seconds=int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("MAX_RETRIES", "3")),
        )
