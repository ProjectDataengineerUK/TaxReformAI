from unittest.mock import patch

import pytest

pytest.importorskip("anthropic", reason="anthropic[vertex] não instalado")

from orquestracao.config import OrquestracaoSettings
from orquestracao.dependencias import criar_dependencias_reais
from orquestracao.llm.cliente import ClienteAnthropicDireto, ClienteVertexAI


def _settings(**overrides) -> OrquestracaoSettings:
    base = dict(
        gcp_project_id="fake-project",
        vertex_ai_region="global",
        qdrant_url="http://fake-qdrant",
        qdrant_api_key="fake-qdrant-key",
        qdrant_collection_name="legislacao_tributaria",
        dense_embedding_model="intfloat/multilingual-e5-large",
        llm_provider="direto",
        anthropic_api_key="fake-anthropic-key",
    )
    base.update(overrides)
    return OrquestracaoSettings(**base)


@patch("ingestion.indexing.qdrant_indexer.QdrantIndexer")
@patch("ingestion.embedding.hybrid_embedder.FastEmbedHybridEmbedder")
def test_criar_dependencias_reais_usa_api_direta_por_default(_mock_embedder, _mock_qdrant):
    with patch("anthropic.Anthropic") as MockAnthropic:
        deps = criar_dependencias_reais(_settings())

    assert isinstance(deps.cliente_llm, ClienteAnthropicDireto)
    MockAnthropic.assert_called_once_with(api_key="fake-anthropic-key")


@patch("ingestion.indexing.qdrant_indexer.QdrantIndexer")
@patch("ingestion.embedding.hybrid_embedder.FastEmbedHybridEmbedder")
def test_criar_dependencias_reais_usa_vertex_quando_configurado(_mock_embedder, _mock_qdrant):
    with patch("anthropic.AnthropicVertex") as MockAnthropicVertex:
        deps = criar_dependencias_reais(_settings(llm_provider="vertex"))

    assert isinstance(deps.cliente_llm, ClienteVertexAI)
    MockAnthropicVertex.assert_called_once_with(project_id="fake-project", region="global")


def test_from_env_exige_gcp_project_id_so_com_vertex(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    monkeypatch.setenv("QDRANT_URL", "http://fake-qdrant")
    monkeypatch.setenv("QDRANT_API_KEY", "fake-qdrant-key")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GCP_PROJECT_ID"):
        OrquestracaoSettings.from_env()


def test_from_env_exige_anthropic_api_key_so_com_direto(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "direto")
    monkeypatch.setenv("QDRANT_URL", "http://fake-qdrant")
    monkeypatch.setenv("QDRANT_API_KEY", "fake-qdrant-key")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        OrquestracaoSettings.from_env()


def test_from_env_direto_nao_exige_gcp_project_id(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "direto")
    monkeypatch.setenv("QDRANT_URL", "http://fake-qdrant")
    monkeypatch.setenv("QDRANT_API_KEY", "fake-qdrant-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    settings = OrquestracaoSettings.from_env()

    assert settings.llm_provider == "direto"
    assert settings.gcp_project_id is None
