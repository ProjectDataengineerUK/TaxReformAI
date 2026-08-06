"""Cobertura E2E específica de LLM_REAL_VERTEX_AI: `/v1/tax/query` com deps
fake injetadas via `app.dependency_overrides`, cobrindo o que `test_api_
query.py` (herdado de ORQUESTRACAO_MULTIAGENTE) não testava — indisponibilidade
do Vertex AI, guardrail do sintetizador e citação real de fontes recuperadas.
"""

import datetime

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.dependencias_orquestracao import get_dependencias_orquestracao
from api.main import app
from ingestion.chunking.chunk_models import Chunk
from orquestracao.dependencias import criar_dependencias_fake
from orquestracao.llm.cliente import (
    MODELO_HAIKU,
    MODELO_SONNET,
    ClienteLLM,
    ClienteLLMFake,
    LLMIndisponivelError,
)

CHAVE_VALIDA = "chave-teste-llm-real"

FONTE_LEGAL_2026 = (
    "LCP 214/2025, arts. 343 e 346 — fase de teste 2026: CBS 0,9% e IBS 0,1% (alíquota estadual)"
)

_ITEM_1000 = {
    "sku": "SKU-TESTE", "ncm": "99999999", "quantidade": 1, "valor_unitario": "1000.00",
    "uf_origem": "SP", "uf_destino": "SP",
}


class _ClienteQueEmpaca:
    def gerar(
        self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido"
    ) -> str:
        raise LLMIndisponivelError("Vertex AI indisponível (simulado)")


def _cliente_fake_feliz() -> ClienteLLMFake:
    # Payload de 1000.00 (único usado neste arquivo) — todos os campos
    # precisam bater, não só valor_liquido (guardrail do sintetizador).
    return ClienteLLMFake(
        respostas_por_modelo={
            MODELO_HAIKU: "SIMULACAO_TRIBUTARIA",
            MODELO_SONNET: (
                "## Parecer\n\nValor bruto total: R$ 1000.00\nValor líquido: R$ 990.00\n"
                "CBS: R$ 9.00\nIBS: R$ 1.00\nIS: R$ 0.00\nICMS interno: R$ 180.00\n"
                f"Fundamentação: {FONTE_LEGAL_2026}"
            ),
        }
    )


def _client(cliente_llm: ClienteLLM, chunks: list[Chunk] | None = None) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: "tenant-a"}
    )
    app.dependency_overrides[get_dependencias_orquestracao] = lambda: criar_dependencias_fake(
        cliente_llm=cliente_llm, chunks=chunks
    )
    return TestClient(app)


@pytest.fixture(autouse=True)
def _limpar_overrides():
    yield
    app.dependency_overrides.clear()


def test_resposta_nao_contem_marcador_fake():
    client = _client(_cliente_fake_feliz())
    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2026", "ano_operacao": 2026, "itens": [_ITEM_1000]},
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    assert "[FAKE]" not in response.text


def test_historico_reflete_chunks_reais_recuperados():
    chunk = Chunk(
        documento_id="LCP_214_2025",
        dispositivo="Art. 1, Inciso I",
        esfera="FEDERAL_CBS_IBS",
        data_vigencia_inicio=datetime.date(2026, 1, 1),
        texto="o Imposto sobre Bens e Serviços (IBS)",
        fonte_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
    )
    client = _client(_cliente_fake_feliz(), chunks=[chunk])

    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2026", "ano_operacao": 2026, "itens": [_ITEM_1000]},
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    historico_pesquisador = next(
        t for t in response.json()["historico"] if t["no"] == "pesquisador_legal"
    )
    assert "1 chunk" in historico_pesquisador["resumo_output"]


def test_vertex_ai_indisponivel_retorna_503_nao_200_com_dado_fabricado():
    client = _client(_ClienteQueEmpaca())

    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2026", "ano_operacao": 2026, "itens": [_ITEM_1000]},
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 503


def test_guardrail_do_sintetizador_retorna_503_quando_valor_nao_bate():
    cliente = ClienteLLMFake(
        respostas_por_modelo={
            MODELO_HAIKU: "SIMULACAO_TRIBUTARIA",
            MODELO_SONNET: "## Parecer\n\nValor líquido: R$ 999999.99",
        }
    )
    client = _client(cliente)

    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2026", "ano_operacao": 2026, "itens": [_ITEM_1000]},
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 503
