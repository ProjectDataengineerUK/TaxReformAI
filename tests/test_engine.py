from decimal import Decimal

import pytest

from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed


@pytest.fixture
def engine():
    return TaxCalculatorEngine(tabela=TabelaAliquotasSeed())


def test_at001_happy_path_fase_teste_2026(engine):
    resultado = engine.calcular(valor_base=Decimal("1000.00"), ano_operacao=2026)

    assert resultado.valor_cbs == Decimal("9.00")
    assert resultado.valor_ibs == Decimal("1.00")
    assert resultado.valor_is == Decimal("0.00")
    assert resultado.total_tributos == Decimal("10.00")
    assert resultado.valor_liquido == Decimal("990.00")
    assert "2026" in resultado.fonte_legal


def test_at002_erro_explicito_para_fase_sem_aliquota_confirmada(engine):
    with pytest.raises(AliquotaNaoDisponivelError):
        engine.calcular(valor_base=Decimal("1000.00"), ano_operacao=2028)


def test_at003_split_payment_desativado_nao_retem_valor(engine):
    resultado = engine.calcular(
        valor_base=Decimal("1000.00"), ano_operacao=2026, split_payment_active=False
    )

    assert resultado.valor_liquido == resultado.valor_base
    assert resultado.total_tributos == Decimal("10.00")


def test_valor_base_invalido_levanta_value_error(engine):
    with pytest.raises(ValueError, match="valor_base deve ser positivo"):
        engine.calcular(valor_base=Decimal(0), ano_operacao=2026)

    with pytest.raises(ValueError, match="valor_base deve ser positivo"):
        engine.calcular(valor_base=Decimal(-10), ano_operacao=2026)


def test_arredondamento_usa_round_half_up():
    from motor_calculo.regras_fiscais import RegraFiscal

    class TabelaCustomizada:
        def buscar(self, fase):
            return RegraFiscal(
                fase=fase,
                aliq_cbs=Decimal("0.08505"),
                aliq_ibs=Decimal(0),
                aliq_is=Decimal(0),
                fonte_legal="teste de arredondamento",
            )

    engine = TaxCalculatorEngine(tabela=TabelaCustomizada())
    resultado = engine.calcular(valor_base=Decimal(100), ano_operacao=2026)

    # 100 * 0.08505 = 8.505 exatamente — ROUND_HALF_UP arredonda para 8.51,
    # diferente do default do Python (ROUND_HALF_EVEN, que daria 8.50)
    assert resultado.valor_cbs == Decimal("8.51")
