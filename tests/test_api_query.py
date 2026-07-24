import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.main import app

CHAVE_VALIDA = "chave-teste-valida"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE_VALIDA: "tenant-a"}
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
