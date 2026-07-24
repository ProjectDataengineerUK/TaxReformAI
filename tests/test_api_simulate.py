import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.main import app

CHAVE_VALIDA = "chave-teste-valida"
# Mesmo tenant do exemplo da seção 8.1 do blueprint — a chave de API precisa
# mapear para ele, já que a rota agora exige que payload e credencial batam.
TENANT_VALIDO = "c39a8281-9b1a-4d2c-8822-123456789abc"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: TENANT_VALIDO}
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def _payload(ano_operacao=2026, n_itens=1, tenant_id=TENANT_VALIDO):
    return {
        "tenant_id": tenant_id,
        "ano_operacao": ano_operacao,
        "operacao_tipo": "VENDA_ESTADUAL_B2B",
        "itens": [
            {
                "sku": f"PROD-{i}",
                "ncm": "8471.30.12",
                "quantidade": 10,
                "valor_unitario": "2500.00",
                "uf_origem": "SP",
                "uf_destino": "MG",
            }
            for i in range(n_itens)
        ],
    }


def test_at001_happy_path_ano_2026(client):
    response = client.post(
        "/v1/tax/simulate", json=_payload(ano_operacao=2026), headers={"X-API-Key": CHAVE_VALIDA}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["resumo_financeiro"]["valor_bruto_total"] == "25000.00"
    assert body["resumo_financeiro"]["total_cbs"] == "225.00"
    assert body["resumo_financeiro"]["total_ibs"] == "25.00"
    assert body["resumo_financeiro"]["valor_liquido_projetado_split_payment"] == "24750.00"
    assert body["itens_detalhados"][0]["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert "2026" in body["itens_detalhados"][0]["fundamentacao_legal"]


def test_at002_sem_api_key_retorna_401(client):
    response = client.post("/v1/tax/simulate", json=_payload())
    assert response.status_code == 401


def test_at002_api_key_invalida_retorna_401(client):
    response = client.post(
        "/v1/tax/simulate", json=_payload(), headers={"X-API-Key": "chave-errada"}
    )
    assert response.status_code == 401


def test_tenant_id_do_payload_diferente_da_credencial_retorna_403(client):
    """Credencial autenticada é a autoridade sobre o tenant. Um cliente válido
    não pode simular declarando o tenant_id de outro (isolamento multi-tenant)."""
    response = client.post(
        "/v1/tax/simulate",
        json=_payload(tenant_id="tenant-de-outra-empresa"),
        headers={"X-API-Key": CHAVE_VALIDA},
    )

    assert response.status_code == 403
    # A resposta não pode revelar qual é o tenant real por trás da chave.
    assert TENANT_VALIDO not in response.text


def test_ano_2027_do_exemplo_do_blueprint_retorna_422_nao_numeros_inventados(client):
    """O exemplo da seção 8 do blueprint usa ano_operacao=2027 com alíquotas
    ilustrativas (8,80%/17,70%) que não são confirmadas em lei nesta fase
    (ver DESIGN, Decision 3). A API deve recusar, não simular esse exemplo."""
    response = client.post(
        "/v1/tax/simulate", json=_payload(ano_operacao=2027), headers={"X-API-Key": CHAVE_VALIDA}
    )

    assert response.status_code == 422
    assert "PLENO_CBS_IS_2027" in response.json()["detail"]


def test_itens_acima_do_limite_retorna_422(client):
    response = client.post(
        "/v1/tax/simulate", json=_payload(n_itens=101), headers={"X-API-Key": CHAVE_VALIDA}
    )
    assert response.status_code == 422


def test_itens_vazio_retorna_422(client):
    payload = _payload(n_itens=1)
    payload["itens"] = []
    response = client.post("/v1/tax/simulate", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert response.status_code == 422
