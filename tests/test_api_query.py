from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.dependencias_orquestracao import get_dependencias_orquestracao
from api.main import app
from orquestracao.dependencias import criar_dependencias_fake
from orquestracao.llm.cliente import MODELO_HAIKU, MODELO_SONNET, ClienteLLMFake

CHAVE_VALIDA = "chave-teste-valida"

FONTE_LEGAL_2026 = (
    "LCP 214/2025, arts. 343 e 346 — fase de teste 2026: CBS 0,9% e IBS 0,1% (alíquota estadual)"
)


def _cliente_fake_feliz() -> ClienteLLMFake:
    # Todos os campos calculados para valor_base=1000.00/ano=2026 (único
    # payload usado nos testes deste arquivo) precisam reaparecer no parecer
    # — o guardrail do sintetizador checa todos, não só valor_liquido.
    return ClienteLLMFake(
        respostas_por_modelo={
            MODELO_HAIKU: "SIMULACAO_TRIBUTARIA",
            MODELO_SONNET: (
                "## Parecer\n\nValor base: R$ 1000.00\nValor líquido: R$ 990.00\n"
                f"CBS: R$ 9.00\nIBS: R$ 1.00\nIS: R$ 0.00\nFundamentação: {FONTE_LEGAL_2026}"
            ),
        }
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: "tenant-a"}
    )
    app.dependency_overrides[get_dependencias_orquestracao] = lambda: criar_dependencias_fake(
        cliente_llm=_cliente_fake_feliz()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_happy_path_conversacional_ano_2026(client):
    response = client.post(
        "/v1/tax/query",
        json={
            "texto_consulta": "Quanto de imposto incide sobre eletrônicos em 2026?",
            "ano_operacao": 2026,
            "valor_base": "1000.00",
        },
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valor_liquido"] == "990.00"
    assert "2026" in body["fonte_legal"]
    assert "Parecer" in body["parecer_final"]
    assert [t["no"] for t in body["historico"]] == [
        "classificador",
        "pesquisador_legal",
        "extrator_regras",
        "deterministico",
        "sintetizador",
    ]


def test_at002_sem_api_key_retorna_401(client):
    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "teste", "ano_operacao": 2026, "valor_base": "1000.00"},
    )
    assert response.status_code == 401


def test_at003_ano_sem_aliquota_confirmada_retorna_422_nao_parecer_inventado(client):
    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2028", "ano_operacao": 2028, "valor_base": "1000.00"},
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 422
    assert "parecer_final" not in response.json()


def test_cpf_mascarado_nao_vaza_na_resposta_http(client):
    response = client.post(
        "/v1/tax/query",
        json={
            "texto_consulta": "CPF 555.444.333-22 quer simular para 2026",
            "ano_operacao": 2026,
            "valor_base": "1000.00",
        },
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    assert "555.444.333-22" not in response.text


class _FakePool:
    @contextmanager
    def connection(self):
        yield object()


def test_audit_log_grava_texto_mascarado_nao_o_bruto(client, monkeypatch):
    # Achado da revisão de segurança de LLM_REAL_VERTEX_AI: o audit log
    # persistia payload.texto_consulta (bruto) em vez de state.texto_mascarado,
    # reintroduzindo o CPF/CNPJ em texto plano no ponto de armazenamento
    # durável mesmo quando o mascaramento antes do LLM funcionava corretamente.
    import db.repositorio as repositorio

    tenant_uuid = uuid4()
    chamadas = []
    monkeypatch.setattr(repositorio, "resolver_tenant", lambda conn, ident: tenant_uuid)
    monkeypatch.setattr(repositorio, "registrar_parecer", lambda conn, p: chamadas.append(p))
    app.dependency_overrides[get_db_pool] = _FakePool

    response = client.post(
        "/v1/tax/query",
        json={
            "texto_consulta": "CPF 555.444.333-22 quer simular para 2026",
            "ano_operacao": 2026,
            "valor_base": "1000.00",
        },
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    assert len(chamadas) == 1
    assert "555.444.333-22" not in chamadas[0].prompt_consulta
    assert "[CPF_MASCARADO]" in chamadas[0].prompt_consulta


def test_at004_pergunta_fora_de_escopo_retorna_422_nao_simulacao_fabricada():
    # Achado real (2026-08-05): "uma receita de bolo de chocolate", com
    # valor_base/ano_operacao que sobravam no payload de um teste anterior,
    # gerava um parecer completo de simulação tributária em produção. O
    # classificador já dizia intencao=OUTRO — só nada usava isso.
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: "tenant-a"}
    )
    app.dependency_overrides[get_dependencias_orquestracao] = lambda: criar_dependencias_fake(
        cliente_llm=ClienteLLMFake(respostas_por_modelo={MODELO_HAIKU: "OUTRO"})
    )
    client = TestClient(app)

    try:
        response = client.post(
            "/v1/tax/query",
            json={
                "texto_consulta": "uma receita de bolo de chocolate",
                "ano_operacao": 2026,
                "valor_base": "1000.00",
            },
            headers={"X-API-Key": CHAVE_VALIDA},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "parecer_final" not in response.json()
