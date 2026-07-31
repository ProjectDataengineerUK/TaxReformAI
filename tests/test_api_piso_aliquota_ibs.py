"""`GET /v1/tax/piso-aliquota-ibs/{ano_operacao}` — AT-001..AT-005, via
`TestClient`. Único caminho hoje que alcança o piso do Anexo XVI: `/v1/tax/
simulate` 422 para todo `ano_operacao >= 2029` (ver
`test_api_simulate_piso.py`), e este endpoint não depende do motor de
cálculo do IVA Dual.
"""

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.main import app

CHAVE = "chave-teste-piso-endpoint"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def _consultar(client, ano):
    return client.get(f"/v1/tax/piso-aliquota-ibs/{ano}", headers={"X-API-Key": CHAVE})


# AT-001 — início da janela --------------------------------------------------


def test_at001_ano_2029_e_o_inicio_da_janela(client):
    resposta = _consultar(client, 2029)
    assert resposta.status_code == 200
    corpo = resposta.json()

    assert corpo["aplicavel"] is True
    assert corpo["ano_operacao"] == 2029
    assert corpo["limite_inferior_percentual"] == "81.0"
    assert corpo["dispositivo_legal_ref"] == "LCP 214/2025, art. 371, §1º, Anexo XVI"
    assert "NÃO calcula" in corpo["nota"]


# AT-002 — o único ano de salto -----------------------------------------------


def test_at002_ano_2033_e_o_unico_salto_para_cima(client):
    corpo = _consultar(client, 2033).json()
    assert corpo["limite_inferior_percentual"] == "90.5"


# AT-003 — fim da janela ------------------------------------------------------


def test_at003_ano_2077_e_o_fim_da_janela(client):
    corpo = _consultar(client, 2077).json()
    assert corpo["aplicavel"] is True
    assert corpo["limite_inferior_percentual"] == "6.9"


# AT-004 — antes da janela ----------------------------------------------------


def test_at004_ano_anterior_a_2029_nao_se_aplica(client):
    resposta = _consultar(client, 2026)
    assert resposta.status_code == 200
    corpo = resposta.json()

    assert corpo["aplicavel"] is False
    assert corpo["limite_inferior_percentual"] is None
    assert corpo["dispositivo_legal_ref"] is None
    assert "não se aplica" in corpo["nota"]


# AT-005 — depois da janela ---------------------------------------------------


def test_at005_ano_posterior_a_2077_nao_se_aplica(client):
    corpo = _consultar(client, 2078).json()
    assert corpo["aplicavel"] is False


def test_sem_api_key_retorna_401(client):
    resposta = client.get("/v1/tax/piso-aliquota-ibs/2033")
    assert resposta.status_code == 401


def test_nao_depende_do_motor_de_calculo_do_iva_dual(client):
    """O ponto inteiro do endpoint: funciona para 2033, mesmo ano em que
    /v1/tax/simulate 422 (ver test_api_simulate_piso.py)."""
    resposta = _consultar(client, 2033)
    assert resposta.status_code == 200
