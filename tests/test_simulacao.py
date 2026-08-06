"""Testes unitários de api/simulacao.py::calcular_simulacao_completa(),
extraída de api/routers/simulate.py::simular() sem mudar comportamento
(COMPARATIVO_REGIME_ATUAL_IVA_DUAL). db_pool=None em todos os testes —
mesmo caminho de degradação graciosa que api/reducao.py, api/ipi.py etc. já
usam em toda a suíte (nunca levanta, só marca "consulta indisponível")."""

from decimal import Decimal

import pytest

from api.schemas_simulate import ItemSimulacao
from api.simulacao import SkuNaoResolvidoError, calcular_simulacao_completa
from motor_calculo.regime_atual import RegimeApuracao
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError


def _item(**overrides) -> ItemSimulacao:
    base = {
        "sku": "SKU-1", "ncm": "99999999", "quantidade": 1, "valor_unitario": Decimal("1000.00"),
        "uf_origem": "SP", "uf_destino": "SP",
    }
    base.update(overrides)
    return ItemSimulacao(**base)


def test_calcula_iva_dual_sem_reducao():
    resposta = calcular_simulacao_completa(
        itens=[_item()], ano_operacao=2026, regime_apuracao=None,
        comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert resposta.resumo_financeiro.total_cbs == Decimal("9.00")
    assert resposta.resumo_financeiro.total_ibs == Decimal("1.00")
    assert "2026" in resposta.fonte_legal_fase


def test_regime_vigente_icms_interno_para_mesma_uf():
    resposta = calcular_simulacao_completa(
        itens=[_item(uf_origem="SP", uf_destino="SP")], ano_operacao=2026,
        regime_apuracao=None, comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert resposta.regime_vigente.total_icms_interno == Decimal("180.00")
    assert resposta.regime_vigente.total_icms_interestadual == Decimal(0)
    assert "ICMS_INTERNO" in resposta.escopo.tributos_incluidos


def test_regime_vigente_icms_interestadual_para_uf_diferente():
    resposta = calcular_simulacao_completa(
        itens=[_item(uf_origem="SP", uf_destino="RJ")], ano_operacao=2026,
        regime_apuracao=None, comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert resposta.regime_vigente.total_icms_interestadual > Decimal(0)
    assert resposta.regime_vigente.total_icms_interno == Decimal(0)


def test_regime_vigente_servico_aciona_iss_nunca_icms():
    resposta = calcular_simulacao_completa(
        itens=[_item(natureza="SERVICO", nbs=None)], ano_operacao=2026,
        regime_apuracao=None, comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert resposta.regime_vigente.total_iss_piso > Decimal(0)
    assert resposta.regime_vigente.total_iss_teto > Decimal(0)
    assert resposta.regime_vigente.total_icms_interno == Decimal(0)
    assert resposta.regime_vigente.total_icms_interestadual == Decimal(0)
    assert resposta.itens_regime_vigente[0].icms_interno_percentual is None


def test_regime_vigente_pis_cofins_so_calculado_com_regime_apuracao():
    sem_regime = calcular_simulacao_completa(
        itens=[_item()], ano_operacao=2026, regime_apuracao=None,
        comprador_tipo=None, db_pool=None, tenant_id="t",
    )
    com_regime = calcular_simulacao_completa(
        itens=[_item()], ano_operacao=2026, regime_apuracao=RegimeApuracao.NAO_CUMULATIVO,
        comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert sem_regime.regime_vigente.total_pis is None
    assert sem_regime.regime_vigente.total_cofins is None
    assert "PIS" in sem_regime.regime_vigente.tributos_nao_calculados
    assert com_regime.regime_vigente.total_pis is not None
    assert com_regime.regime_vigente.total_cofins is not None


def test_ano_sem_aliquota_levanta_erro_de_dominio_nunca_httpexception():
    with pytest.raises(AliquotaNaoDisponivelError):
        calcular_simulacao_completa(
            itens=[_item()], ano_operacao=2028, regime_apuracao=None,
            comprador_tipo=None, db_pool=None, tenant_id="t",
        )


def test_sku_sem_ncm_e_sem_catalogo_levanta_sku_nao_resolvido():
    with pytest.raises(SkuNaoResolvidoError):
        calcular_simulacao_completa(
            itens=[_item(ncm=None)], ano_operacao=2026, regime_apuracao=None,
            comprador_tipo=None, db_pool=None, tenant_id="t",
        )


def test_ipi_nao_resolvido_sem_db_pool_mas_nunca_propaga_excecao():
    # db_pool=None: consulta_ipi_com_seguranca degrada para "indisponível",
    # nunca levanta — o total_ipi vira None (não zero), com o motivo em
    # ipi_nao_resolvido, mesma disciplina de api/ipi.py.
    resposta = calcular_simulacao_completa(
        itens=[_item()], ano_operacao=2026, regime_apuracao=None,
        comprador_tipo=None, db_pool=None, tenant_id="t",
    )

    assert resposta.regime_vigente.total_ipi is None
    assert len(resposta.regime_vigente.ipi_nao_resolvido) == 1
    assert "IPI" in resposta.regime_vigente.tributos_nao_calculados
