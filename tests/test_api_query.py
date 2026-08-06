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

# Item MERCADORIA único, SP -> SP (ICMS interno 18%, RICMS/SP) — mesmo
# padrão dos testes de orquestração, cobre regime_vigente sem precisar de
# db_pool real (ncm explícito nunca toca o catálogo empresa_skus).
_ITEM_1000 = {
    "sku": "SKU-TESTE", "ncm": "99999999", "quantidade": 1, "valor_unitario": "1000.00",
    "uf_origem": "SP", "uf_destino": "SP",
}


def _cliente_fake_feliz() -> ClienteLLMFake:
    # Todos os campos calculados para o payload de 1000.00 (único usado nos
    # testes deste arquivo) precisam reaparecer no parecer — o guardrail do
    # sintetizador checa todos os totais agregados, não só valor_liquido.
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
            "itens": [_ITEM_1000],
        },
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    body = response.json()
    resumo = body["resultado_simulacao"]["resumo_financeiro"]
    assert resumo["valor_liquido_projetado_split_payment"] == "990.00"
    assert "2026" in body["resultado_simulacao"]["fonte_legal_fase"]
    assert "Parecer" in body["parecer_final"]
    assert [t["no"] for t in body["historico"]] == [
        "classificador",
        "pesquisador_legal",
        "extrator_regras",
        "deterministico",
        "sintetizador",
    ]


def test_at004_valor_base_e_derivado_da_soma_dos_itens(client):
    # AT-004 do DEFINE: valor_base deixou de ser campo manual — precisa ser
    # exatamente a soma de quantidade x valor_unitario de todos os itens.
    response = client.post(
        "/v1/tax/query",
        json={
            "texto_consulta": "Quanto de imposto incide sobre 3 itens?",
            "ano_operacao": 2026,
            "itens": [
                {
                    "sku": "A", "ncm": "99999999", "quantidade": 2,
                    "valor_unitario": "100.00", "uf_origem": "SP", "uf_destino": "SP",
                },
                {
                    "sku": "B", "ncm": "99999999", "quantidade": 1,
                    "valor_unitario": "800.00", "uf_origem": "SP", "uf_destino": "SP",
                },
            ],
        },
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 200
    body = response.json()
    # 2*100.00 + 1*800.00 = 1000.00 — mesmo total do payload padrão do
    # arquivo, então o mesmo parecer fake continua batendo no guardrail.
    assert body["resultado_simulacao"]["resumo_financeiro"]["valor_bruto_total"] == "1000.00"


def test_at002_sem_api_key_retorna_401(client):
    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "teste", "ano_operacao": 2026, "itens": [_ITEM_1000]},
    )
    assert response.status_code == 401


def test_at003_ano_sem_aliquota_confirmada_retorna_422_nao_parecer_inventado(client):
    response = client.post(
        "/v1/tax/query",
        json={"texto_consulta": "simular para 2028", "ano_operacao": 2028, "itens": [_ITEM_1000]},
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
            "itens": [_ITEM_1000],
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
            "itens": [_ITEM_1000],
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
                "itens": [_ITEM_1000],
            },
            headers={"X-API-Key": CHAVE_VALIDA},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "parecer_final" not in response.json()


def test_at003_at008_paridade_numerica_com_simulador_para_o_mesmo_payload():
    # AT-003/AT-008 do DEFINE: /consulta precisa calcular os dois itens (IVA
    # Dual e regime atual) com a MESMA precisão de /v1/tax/simulate — mesma
    # função compartilhada (api/simulacao.py::calcular_simulacao_completa),
    # nunca uma cópia divergente.
    itens = [
        {
            "sku": "PROD-1", "ncm": "99999999", "quantidade": 3,
            "valor_unitario": "333.33", "uf_origem": "SP", "uf_destino": "RJ",
        }
    ]

    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: "tenant-a"}
    )
    try:
        client = TestClient(app)
        resposta_simulate = client.post(
            "/v1/tax/simulate",
            json={
                "tenant_id": "tenant-a",
                "ano_operacao": 2026,
                "operacao_tipo": "VENDA_ESTADUAL_B2B",
                "itens": itens,
            },
            headers={"X-API-Key": CHAVE_VALIDA},
        )
        assert resposta_simulate.status_code == 200
        simulado = resposta_simulate.json()
        resumo = simulado["resumo_financeiro"]
        regime = simulado["regime_vigente"]

        # Fake dedicado, construído a partir dos números REAIS devolvidos por
        # /v1/tax/simulate — garante que o guardrail do sintetizador passe
        # para QUALQUER payload, sem depender de um fake estático só válido
        # para o total de 1000.00 usado no resto deste arquivo.
        parecer_fake = (
            "## Parecer\n\n"
            f"Valor bruto total: R$ {resumo['valor_bruto_total']}\n"
            f"Valor líquido: R$ {resumo['valor_liquido_projetado_split_payment']}\n"
            f"CBS: R$ {resumo['total_cbs']}\nIBS: R$ {resumo['total_ibs']}\nIS: R$ {resumo['total_is']}\n"
            f"ICMS interestadual: R$ {regime['total_icms_interestadual']}\n"
            f"Fundamentação: {simulado['fonte_legal_fase']}"
        )
        app.dependency_overrides[get_dependencias_orquestracao] = lambda: criar_dependencias_fake(
            cliente_llm=ClienteLLMFake(
                respostas_por_modelo={
                    MODELO_HAIKU: "SIMULACAO_TRIBUTARIA",
                    MODELO_SONNET: parecer_fake,
                }
            )
        )
        resposta_query = client.post(
            "/v1/tax/query",
            json={
                "texto_consulta": "simular estes itens para 2026",
                "ano_operacao": 2026,
                "itens": itens,
            },
            headers={"X-API-Key": CHAVE_VALIDA},
        )
    finally:
        app.dependency_overrides.clear()

    assert resposta_query.status_code == 200
    consultado = resposta_query.json()["resultado_simulacao"]
    assert consultado["resumo_financeiro"] == simulado["resumo_financeiro"]
    assert consultado["regime_vigente"] == simulado["regime_vigente"]
    assert consultado["fonte_legal_fase"] == simulado["fonte_legal_fase"]
