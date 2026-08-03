"""Provider das dependências reais da orquestração (LLM + Qdrant + embedder).

Segue o padrão de `api/db.get_db_pool`: função com `@lru_cache`, overridável
em teste via `app.dependency_overrides`. Construído uma vez por processo —
`AnthropicVertex`/`QdrantIndexer`/`FastEmbedHybridEmbedder` abrem clientes que
não precisam ser recriados a cada request.
"""

from functools import lru_cache

from orquestracao.dependencias import DependenciasOrquestracao


@lru_cache
def get_dependencias_orquestracao() -> DependenciasOrquestracao:
    from orquestracao.config import OrquestracaoSettings
    from orquestracao.dependencias import criar_dependencias_reais

    settings = OrquestracaoSettings.from_env()
    return criar_dependencias_reais(settings)
