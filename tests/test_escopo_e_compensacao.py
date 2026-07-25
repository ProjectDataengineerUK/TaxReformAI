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


def test_api_declara_que_nao_inclui_os_tributos_do_regime_antigo(resposta_2026):
    """Durante a transição PIS, COFINS, IPI, ICMS e ISS continuam devidos. Uma
    resposta que os omite sem dizer engana por omissão."""
    assert resposta_2026.status_code == 200
    escopo = resposta_2026.json()["escopo"]

    assert set(escopo["tributos_incluidos"]) == {"CBS", "IBS", "IS"}
    for antigo in ("PIS", "COFINS", "IPI", "ICMS", "ISS"):
        assert antigo in escopo["tributos_nao_incluidos"]
    assert "não representa a carga tributária total" in escopo["advertencia"]


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
