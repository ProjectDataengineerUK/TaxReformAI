import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OrquestracaoSettings:
    gcp_project_id: str | None
    vertex_ai_region: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str
    dense_embedding_model: str
    llm_provider: str
    anthropic_api_key: str | None

    @classmethod
    def from_env(cls) -> "OrquestracaoSettings":
        from ingestion.embedding.hybrid_embedder import MODELO_DENSO_PADRAO

        llm_provider = os.environ.get("LLM_PROVIDER", "direto")

        missing = [
            var for var in ("QDRANT_URL", "QDRANT_API_KEY") if not os.environ.get(var)
        ]
        # LLM_CLAUDE_API_DIRETA: GCP_PROJECT_ID só é usado por ClienteVertexAI e
        # ANTHROPIC_API_KEY só por ClienteAnthropicDireto — exigir os dois
        # incondicionalmente barraria o caminho que esta feature existe para
        # destravar (LLM_PROVIDER=direto, o default).
        if llm_provider == "vertex" and not os.environ.get("GCP_PROJECT_ID"):
            missing.append("GCP_PROJECT_ID")
        if llm_provider == "direto" and not os.environ.get("ANTHROPIC_API_KEY"):
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise RuntimeError(
                f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}."
            )
        return cls(
            gcp_project_id=os.environ.get("GCP_PROJECT_ID"),
            vertex_ai_region=os.environ.get("VERTEX_AI_REGION", "global"),
            qdrant_url=os.environ["QDRANT_URL"],
            qdrant_api_key=os.environ["QDRANT_API_KEY"],
            qdrant_collection_name=os.environ.get(
                "QDRANT_COLLECTION_NAME", "legislacao_tributaria"
            ),
            dense_embedding_model=os.environ.get(
                "DENSE_EMBEDDING_MODEL", MODELO_DENSO_PADRAO
            ),
            llm_provider=llm_provider,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
