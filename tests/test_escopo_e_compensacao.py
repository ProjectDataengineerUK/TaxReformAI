"""A simulação precisa declarar o que NÃO calcula.

O motor estava aritmeticamente correto e materialmente enganoso: para R$ 100 em
2026 respondia `valor_liquido_projetado_split_payment: 99.00`, o que um
departamento fiscal lê como "esta operação custou R$ 1".

Não custou. O art. 348 da LCP 214/2025 determina que o montante recolhido de
IBS e CBS em 2026 seja compensado com o PIS/COFINS devido no mesmo período —
e, sem débitos suficientes, compensado com outro tributo federal ou ressarcido
em até 60 dias. Para quem tem débitos, o custo efetivo é zero.

Some-se que durante a transição os tributos do regime antigo continuam devidos
integralmente e este motor não calcula nenhum deles.

Erro plausível, com fonte legal ao lado, num produto que promete
auditabilidade — o pior tipo. Estes testes existem para que ele não volte.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.main import app
from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.fases import FaseTransicao
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed

CHAVE = "chave-teste-escopo"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_2026_e_compensavel_com_fonte_no_artigo_348():
    regra = TabelaAliquotasSeed().buscar(FaseTransicao.TESTE_2026)

    assert regra.compensavel is True
    assert "art. 348" in regra.fonte_legal_compensacao
    assert "compensado" in regra.fonte_legal_compensacao.lower()


def test_resultado_do_calculo_carrega_a_compensacao():
    """Se a compensação ficasse só na tabela e não chegasse ao resultado, a API
    não teria como informá-la — que era exatamente o estado anterior."""
    engine = TaxCalculatorEngine(TabelaAliquotasSeed())

    resultado = engine.calcular(valor_base=Decimal("100.00"), ano_operacao=2026)

    assert resultado.compensavel is True
    assert "art. 348" in resultado.fonte_legal_compensacao
    # O cálculo em si não muda: 0,9% + 0,1% continuam devidos e recolhidos.
    # O que muda é a informação de que o valor é recuperável.
    assert resultado.valor_cbs == Decimal("0.90")
    assert resultado.valor_ibs == Decimal("0.10")


@pytest.fixture
def resposta_2026(client):
    return client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "22030000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "RJ",
                }
            ],
        },
    )


def test_api_declara_escopo_sem_regime_apuracao(resposta_2026):
    """Sem regime_apuracao informado, PIS/COFINS não são calculados — e o
    escopo precisa dizer isso, não fingir que não existem."""
    assert resposta_2026.status_code == 200
    escopo = resposta_2026.json()["escopo"]

    assert set(escopo["tributos_incluidos"]) == {"CBS", "IBS", "IS", "ICMS_INTERESTADUAL"}
    assert "PIS" in escopo["tributos_nao_incluidos"]
    assert "COFINS" in escopo["tributos_nao_incluidos"]
    for indisponivel in ("IPI", "ICMS_INTERNO", "ISS"):
        assert indisponivel in escopo["tributos_nao_incluidos"]
    assert "não representa a carga tributária total" in escopo["advertencia"]


def test_api_calcula_icms_interestadual_sempre(resposta_2026):
    """uf_origem/uf_destino são obrigatórios no payload, então o ICMS
    interestadual é sempre calculável — sem depender de regime_apuracao."""
    corpo = resposta_2026.json()

    item = corpo["itens_regime_vigente"][0]
    assert item["icms_interestadual_percentual"] == "12.00"
    assert "22/1989" in item["fonte_legal_icms"]
    assert item["pis_percentual"] is None, "sem regime_apuracao, PIS fica None"


def test_api_calcula_pis_cofins_quando_regime_informado(client):
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "regime_apuracao": "NAO_CUMULATIVO",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "22030000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "RJ",
                }
            ],
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "PIS" in corpo["escopo"]["tributos_incluidos"]
    assert corpo["regime_vigente"]["total_pis"] == "1.65"
    assert corpo["regime_vigente"]["total_cofins"] == "7.60"
    assert "10.637" in corpo["itens_regime_vigente"][0]["fonte_legal_pis"]


def test_api_informa_a_compensacao_de_2026(resposta_2026):
    compensacao = resposta_2026.json()["compensacao"]

    assert compensacao["aplicavel"] is True
    assert "art. 348" in compensacao["fonte_legal"]


def test_valor_liquido_continua_exposto_mas_agora_qualificado(resposta_2026):
    """Não removemos o campo — quebraria o contrato com ERPs e o frontend. O
    que mudou é que ele deixa de ser a única informação: quem o lê agora recebe
    junto o escopo e a compensação que o qualificam."""
    corpo = resposta_2026.json()

    assert corpo["resumo_financeiro"]["valor_liquido_projetado_split_payment"] == "99.00"
    assert corpo["compensacao"]["aplicavel"] is True
    assert corpo["escopo"]["advertencia"]


# ICMS interno e ISS — 2026-07-27, ver motor_calculo/regime_atual.py --------


def test_api_usa_icms_interno_quando_uf_origem_e_destino_sao_iguais(client):
    """SP -> SP não é interestadual: a Resolução 22/1989 não rege isso, e
    usá-la citaria a norma errada. O endpoint precisa trocar para
    icms_interno() sozinho, só olhando uf_origem == uf_destino."""
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "22030000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "SP",
                }
            ],
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    item = corpo["itens_regime_vigente"][0]

    assert item["icms_interno_percentual"] == "18.00"
    assert "52" in item["fonte_legal_icms_interno"]
    assert item["icms_interestadual_percentual"] is None
    assert corpo["regime_vigente"]["total_icms_interno"] == "18.00"
    assert "ICMS_INTERNO" in corpo["escopo"]["tributos_incluidos"]
    assert "ICMS_INTERESTADUAL" in corpo["escopo"]["tributos_nao_incluidos"]


def test_api_icms_interno_rio_de_janeiro_expoe_fecp_separado(client):
    """FECP tem base legal própria (LC Estadual 210/2023) — não pode ficar
    somado silenciosamente dentro de icms_interno_percentual."""
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "22030000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "RJ",
                    "uf_destino": "RJ",
                }
            ],
        },
    )

    corpo = resposta.json()
    item = corpo["itens_regime_vigente"][0]

    assert item["icms_interno_percentual"] == "20.00"
    assert item["icms_interno_fecp_percentual"] == "2.00"
    assert "210/2023" in item["fonte_legal_icms_interno_fecp"]
    assert corpo["regime_vigente"]["total_icms_interno_fecp"] == "2.00"


def test_api_natureza_servico_calcula_iss_em_vez_de_icms(client):
    """natureza=SERVICO troca a base de ICMS para o piso/teto do ISS — as
    duas nunca coexistem no mesmo item."""
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "PRESTACAO_SERVICO",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "00000000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "SP",
                    "natureza": "SERVICO",
                }
            ],
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    item = corpo["itens_regime_vigente"][0]

    assert item["iss_piso_percentual"] == "2.00"
    assert item["iss_teto_percentual"] == "5.00"
    assert "116/2003" in item["fonte_legal_iss_piso"]
    assert item["icms_interno_percentual"] is None
    assert item["icms_interestadual_percentual"] is None
    assert corpo["regime_vigente"]["total_iss_piso"] == "2.00"
    assert corpo["regime_vigente"]["total_iss_teto"] == "5.00"
    assert "ISS" in corpo["escopo"]["tributos_incluidos"]
    assert "ICMS_INTERNO" in corpo["escopo"]["tributos_nao_incluidos"]
    assert "ICMS_INTERESTADUAL" in corpo["escopo"]["tributos_nao_incluidos"]


def test_api_natureza_mercadoria_e_o_default_sem_o_campo(client):
    """Payload sem `natureza` precisa continuar se comportando exatamente
    como antes deste campo existir — retrocompatibilidade."""
    resposta = client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": [
                {
                    "sku": "T-1",
                    "ncm": "22030000",
                    "quantidade": 1,
                    "valor_unitario": "100.00",
                    "uf_origem": "SP",
                    "uf_destino": "RJ",
                }
            ],
        },
    )

    corpo = resposta.json()
    assert corpo["itens_regime_vigente"][0]["natureza"] == "MERCADORIA"
    assert corpo["itens_regime_vigente"][0]["icms_interestadual_percentual"] == "12.00"
