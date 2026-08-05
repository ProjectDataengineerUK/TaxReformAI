from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("anthropic", reason="anthropic[vertex] não instalado")

from orquestracao.llm.cliente import (
    MODELO_HAIKU,
    MODELO_SONNET,
    ClienteAnthropicDireto,
    ClienteLLMFake,
    ClienteVertexAI,
    LLMIndisponivelError,
)


def test_cliente_llm_fake_grava_chamadas_e_devolve_resposta_configurada():
    cliente = ClienteLLMFake(respostas_por_modelo={"modelo-x": "resposta configurada"})

    resultado = cliente.gerar("modelo-x", [{"role": "user", "content": "oi"}])

    assert resultado == "resposta configurada"
    assert cliente.chamadas == [
        {"modelo": "modelo-x", "mensagens": [{"role": "user", "content": "oi"}], "max_tokens": 1024}
    ]


def test_cliente_llm_fake_modelo_sem_resposta_configurada_usa_default():
    cliente = ClienteLLMFake()
    assert cliente.gerar("qualquer-modelo", []) == "resposta fake"


def _mock_anthropic_vertex_com_resposta(texto: str):
    bloco = SimpleNamespace(type="text", text=texto)
    resposta = SimpleNamespace(content=[bloco])
    mock_client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kwargs: resposta)
    )
    return mock_client


def test_cliente_vertex_ai_extrai_texto_do_bloco_de_resposta():
    with patch("anthropic.AnthropicVertex") as MockAnthropicVertex:
        MockAnthropicVertex.return_value = _mock_anthropic_vertex_com_resposta("olá do Vertex AI")
        cliente = ClienteVertexAI(project_id="fake-project", region="global")

        resultado = cliente.gerar("claude-sonnet-5", [{"role": "user", "content": "oi"}])

    assert resultado == "olá do Vertex AI"


def test_cliente_vertex_ai_resposta_sem_bloco_de_texto_levanta_erro():
    with patch("anthropic.AnthropicVertex") as MockAnthropicVertex:
        resposta_vazia = SimpleNamespace(content=[])
        MockAnthropicVertex.return_value = SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kwargs: resposta_vazia)
        )
        cliente = ClienteVertexAI(project_id="fake-project")

        with pytest.raises(LLMIndisponivelError):
            cliente.gerar("claude-sonnet-5", [{"role": "user", "content": "oi"}])


def test_cliente_vertex_ai_erro_de_rede_vira_llm_indisponivel_error():
    with patch("anthropic.AnthropicVertex") as MockAnthropicVertex:
        def _levanta(**kwargs):
            raise ConnectionError("timeout simulado")

        MockAnthropicVertex.return_value = SimpleNamespace(
            messages=SimpleNamespace(create=_levanta)
        )
        cliente = ClienteVertexAI(project_id="fake-project")

        with pytest.raises(LLMIndisponivelError):
            cliente.gerar("claude-sonnet-5", [{"role": "user", "content": "oi"}])


def _mock_anthropic_direto_capturando_modelo(texto: str, chamadas: list[str]):
    bloco = SimpleNamespace(type="text", text=texto)
    resposta = SimpleNamespace(content=[bloco])

    def _create(**kwargs):
        chamadas.append(kwargs["model"])
        return resposta

    return SimpleNamespace(messages=SimpleNamespace(create=_create))


def test_cliente_anthropic_direto_extrai_texto_do_bloco_de_resposta():
    with patch("anthropic.Anthropic") as MockAnthropic:
        chamadas: list[str] = []
        MockAnthropic.return_value = _mock_anthropic_direto_capturando_modelo(
            "olá da API direta", chamadas
        )
        cliente = ClienteAnthropicDireto(api_key="fake-key")

        resultado = cliente.gerar(MODELO_SONNET, [{"role": "user", "content": "oi"}])

    assert resultado == "olá da API direta"


def test_cliente_anthropic_direto_traduz_modelo_haiku_do_formato_vertex():
    with patch("anthropic.Anthropic") as MockAnthropic:
        chamadas: list[str] = []
        MockAnthropic.return_value = _mock_anthropic_direto_capturando_modelo(
            "resposta", chamadas
        )
        cliente = ClienteAnthropicDireto(api_key="fake-key")

        cliente.gerar(MODELO_HAIKU, [{"role": "user", "content": "oi"}])

    assert chamadas == ["claude-haiku-4-5-20251001"]


def test_cliente_anthropic_direto_modelo_sonnet_ja_identico_nos_dois_formatos():
    with patch("anthropic.Anthropic") as MockAnthropic:
        chamadas: list[str] = []
        MockAnthropic.return_value = _mock_anthropic_direto_capturando_modelo(
            "resposta", chamadas
        )
        cliente = ClienteAnthropicDireto(api_key="fake-key")

        cliente.gerar(MODELO_SONNET, [{"role": "user", "content": "oi"}])

    assert chamadas == ["claude-sonnet-5"]


def test_cliente_anthropic_direto_resposta_sem_bloco_de_texto_levanta_erro():
    with patch("anthropic.Anthropic") as MockAnthropic:
        resposta_vazia = SimpleNamespace(content=[])
        MockAnthropic.return_value = SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kwargs: resposta_vazia)
        )
        cliente = ClienteAnthropicDireto(api_key="fake-key")

        with pytest.raises(LLMIndisponivelError):
            cliente.gerar(MODELO_SONNET, [{"role": "user", "content": "oi"}])


def test_cliente_anthropic_direto_erro_de_rede_vira_llm_indisponivel_error():
    with patch("anthropic.Anthropic") as MockAnthropic:
        def _levanta(**kwargs):
            raise ConnectionError("timeout simulado")

        MockAnthropic.return_value = SimpleNamespace(messages=SimpleNamespace(create=_levanta))
        cliente = ClienteAnthropicDireto(api_key="fake-key")

        with pytest.raises(LLMIndisponivelError):
            cliente.gerar(MODELO_SONNET, [{"role": "user", "content": "oi"}])
