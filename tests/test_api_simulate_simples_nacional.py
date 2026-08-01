"""AT-001 a AT-012 do DEFINE, via `TestClient`.

Endpoint dedicado (`POST /v1/tax/simulate-simples-nacional`) não faz nenhuma
consulta a banco para o cálculo em si — só o audit log usa `db_pool`, e este
já tem um caminho gracioso para `pool=None` (`api.audit.registrar_com_
seguranca`), então os testes aqui não precisam de um pool fake.
"""

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app

CHAVE = "chave-teste-simples-nacional"
TENANT = "f19c0413-1d3c-6f4e-aa44-345678901def"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _simular(client, corpo_extra: dict, ano=2027):
    corpo = {
        "tenant_id": TENANT,
        "ano_operacao": ano,
        **corpo_extra,
    }
    return client.post(
        "/v1/tax/simulate-simples-nacional", headers={"X-API-Key": CHAVE}, json=corpo
    )


# AT-001 — Comércio, 1a Faixa, 2027 -------------------------------------------


def test_at001_comercio_primeira_faixa_2027(client):
    resposta = _simular(
        client,
        {
            "atividade": "COMERCIO",
            "receita_bruta_acumulada_12_meses": "150000.00",
            "receita_bruta_mes": "12500.00",
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["faixa"] == 1
    tributos = {p["tributo"]: p for p in corpo["partilha"]}
    assert "CBS" in tributos
    assert "IBS" in tributos
    assert "Anexo XVIII" in corpo["dispositivo_legal_ref"]
    assert "LC 123/2006, art. 18" in corpo["dispositivo_legal_ref"]


# AT-002 — Indústria, 2033 (regime permanente) --------------------------------


def test_at002_industria_2033_regime_permanente(client):
    resposta = _simular(
        client,
        {
            "atividade": "INDUSTRIA",
            "receita_bruta_acumulada_12_meses": "500000.00",
            "receita_bruta_mes": "40000.00",
        },
        ano=2033,
    )
    corpo = resposta.json()
    tributos = {p["tributo"] for p in corpo["partilha"]}
    assert "ICMS" not in tributos
    assert "IBS" in tributos
    assert "IPI" in tributos


# AT-003 — Serviço Anexo IV (XXI) sem CPP -------------------------------------


def test_at003_servico_par_5c_nunca_tem_cpp(client):
    resposta = _simular(
        client,
        {
            "atividade": "SERVICO_PAR_5C",
            "receita_bruta_acumulada_12_meses": "150000.00",
            "receita_bruta_mes": "10000.00",
        },
    )
    corpo = resposta.json()
    tributos = {p["tributo"] for p in corpo["partilha"]}
    assert "CPP" not in tributos


# AT-004/AT-005 — teto de ISS acionado / não acionado -------------------------


def test_at004_teto_iss_acionado(client):
    resposta = _simular(
        client,
        {
            "atividade": "LOCACAO_SERVICO_GERAL",
            "receita_bruta_acumulada_12_meses": "3600000.00",
            "receita_bruta_mes": "300000.00",
        },
    )
    corpo = resposta.json()
    assert corpo["teto_iss_aplicado"] is True
    tributos = {p["tributo"]: p["valor_devido"] for p in corpo["partilha"]}
    assert tributos["ISS"] is not None


def test_at005_teto_iss_nao_acionado(client):
    resposta = _simular(
        client,
        {
            "atividade": "LOCACAO_SERVICO_GERAL",
            "receita_bruta_acumulada_12_meses": "1800000.01",
            "receita_bruta_mes": "50000.00",
        },
    )
    corpo = resposta.json()
    assert corpo["teto_iss_aplicado"] is False


# AT-006/AT-007 — MEI ----------------------------------------------------------


def test_at006_mei_valor_fixo(client):
    resposta = _simular(
        client, {"atividade": "MEI", "receita_bruta_mes": "1.00"}, ano=2029
    )
    corpo = resposta.json()
    tributos = {p["tributo"]: p["valor_devido"] for p in corpo["partilha"]}
    assert tributos["CBS"] == "1.00"
    assert tributos["IBS"] == "0.20"
    assert corpo["faixa"] is None
    assert corpo["aliquota_efetiva"] is None
    # MEI não tem alíquota — percentual_efetivo é sempre None.
    assert all(p["percentual_efetivo"] is None for p in corpo["partilha"])


def test_at007_mei_2033_sem_icms_iss(client):
    resposta = _simular(
        client, {"atividade": "MEI", "receita_bruta_mes": "1.00"}, ano=2033
    )
    corpo = resposta.json()
    tributos = {p["tributo"] for p in corpo["partilha"]}
    assert tributos == {"CBS", "IBS"}


# AT-008 — 6a Faixa sem ICMS/ISS/IBS -------------------------------------------


def test_at008_sexta_faixa_sem_icms_iss_ibs(client):
    resposta = _simular(
        client,
        {
            "atividade": "COMERCIO",
            "receita_bruta_acumulada_12_meses": "4000000.00",
            "receita_bruta_mes": "300000.00",
        },
    )
    corpo = resposta.json()
    assert corpo["faixa"] == 6
    assert corpo["icms_iss_fora_do_das"] is True
    tributos = {p["tributo"] for p in corpo["partilha"]}
    assert tributos == {"IRPJ", "CSLL", "CBS", "CPP"}


# AT-009 — endpoint do regime geral segue intocado -----------------------------


def test_at009_endpoint_do_regime_geral_nao_tem_campos_novos(client):
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": [
                {
                    "sku": "P-1",
                    "ncm": "00000000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "SP",
                }
            ],
        },
    )
    assert resposta.status_code == 200
    assert "receita_bruta_acumulada_12_meses" not in resposta.json()


# AT-010 — RBT12 ausente fora do MEI -------------------------------------------


def test_at010_rbt12_ausente_fora_do_mei_e_422(client):
    resposta = _simular(
        client, {"atividade": "COMERCIO", "receita_bruta_mes": "10000.00"}
    )
    assert resposta.status_code == 422


# AT-011 — ano fora da janela ---------------------------------------------------


def test_at011_ano_anterior_a_2027_e_422(client):
    resposta = _simular(
        client,
        {
            "atividade": "COMERCIO",
            "receita_bruta_acumulada_12_meses": "150000.00",
            "receita_bruta_mes": "12500.00",
        },
        ano=2026,
    )
    assert resposta.status_code == 422
    assert "2027" in resposta.json()["detail"]


# AT-012 — zero regressão -------------------------------------------------------


def test_at012_tenant_id_divergente_e_403(client):
    resposta = client.post(
        "/v1/tax/simulate-simples-nacional",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": "outro-tenant",
            "ano_operacao": 2027,
            "atividade": "COMERCIO",
            "receita_bruta_acumulada_12_meses": "150000.00",
            "receita_bruta_mes": "12500.00",
        },
    )
    assert resposta.status_code == 403


def test_receita_acima_do_teto_do_simples_e_422(client):
    resposta = _simular(
        client,
        {
            "atividade": "COMERCIO",
            "receita_bruta_acumulada_12_meses": "4800000.01",
            "receita_bruta_mes": "300000.00",
        },
    )
    assert resposta.status_code == 422
