"""`RespostaSimulacao.piso_aliquota_ibs` via `TestClient` — cobre só o que
`/v1/tax/simulate` consegue alcançar hoje.

Achado real do `/build`: `/v1/tax/simulate` já devolve 422 para QUALQUER
`ano_operacao >= 2029` (nenhuma `RegraFiscal` existe para as fases
`TRANSICAO_ICMS_ISS_2029_2032`/`REGIME_PLENO_2033` em `TabelaAliquotasSeed`)
— exatamente a janela inteira em que o piso do Anexo XVI se aplica. Por isso
este arquivo só testa o caminho "fora da janela" (`None`, zero regressão); o
caminho "dentro da janela" (AT-001, AT-002, AT-003) só é alcançável pelo
endpoint dedicado, testado em `test_api_piso_aliquota_ibs.py` — ver
Decisão 4 do DESIGN.
"""

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.main import app

CHAVE = "chave-teste-piso"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def _payload(ano_operacao):
    return {
        "tenant_id": TENANT,
        "ano_operacao": ano_operacao,
        "operacao_tipo": "VENDA_ESTADUAL_B2B",
        "itens": [
            {
                "sku": "PROD-1",
                "ncm": "8471.30.12",
                "quantidade": 1,
                "valor_unitario": "100.00",
                "uf_origem": "SP",
                "uf_destino": "SP",
            }
        ],
    }


def test_ano_2029_ou_alem_devolve_422_independente_desta_feature(client):
    """Confirma o achado do /build: o bloqueio é do motor de CBS/IBS
    (`AliquotaNaoDisponivelError`), não desta feature — a mensagem cita a
    fase, não o piso."""
    resposta = client.post(
        "/v1/tax/simulate", json=_payload(2033), headers={"X-API-Key": CHAVE}
    )
    assert resposta.status_code == 422
    assert "REGIME_PLENO_2033" in resposta.json()["detail"]


# AT-007 (adaptado) — fora da janela, e zero regressão no resto da resposta -


def test_at007_ano_2026_nao_traz_o_bloco_do_piso(client):
    resposta = client.post(
        "/v1/tax/simulate", json=_payload(2026), headers={"X-API-Key": CHAVE}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()

    assert corpo["piso_aliquota_ibs"] is None
    # Zero regressão: o resto da resposta continua exatamente como antes
    # desta feature — o campo novo é puramente aditivo.
    assert corpo["resumo_financeiro"]["valor_bruto_total"] == "100.00"
    assert corpo["itens_detalhados"][0]["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"


def test_ano_2028_tambem_422_por_motivo_diferente_cbs_de_referencia_nao_fixada(client):
    """Achado do /build, mais amplo do que o esperado: 2027-2028
    (`PLENO_CBS_IS_2027`) também 422 — não pela mesma causa de 2029+
    (fase ausente de `TabelaAliquotasSeed`), mas porque `regra.
    tributos_indisponiveis()` recusa quando CBS/IS não têm alíquota
    fixada (art. 347 ainda pendente). Na prática, **2026 é o único ano em
    que `/v1/tax/simulate` responde 200 hoje** — reforça por que o
    endpoint dedicado (`test_api_piso_aliquota_ibs.py`) é indispensável."""
    resposta = client.post(
        "/v1/tax/simulate", json=_payload(2028), headers={"X-API-Key": CHAVE}
    )
    assert resposta.status_code == 422
