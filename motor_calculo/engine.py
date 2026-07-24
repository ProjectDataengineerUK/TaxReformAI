from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from motor_calculo.fases import fase_para
from motor_calculo.tabela_aliquotas import TabelaAliquotas


@dataclass
class ResultadoCalculo:
    valor_base: Decimal
    valor_is: Decimal
    valor_cbs: Decimal
    valor_ibs: Decimal
    total_tributos: Decimal
    valor_liquido: Decimal
    fonte_legal: str


class TaxCalculatorEngine:
    def __init__(self, tabela: TabelaAliquotas):
        self._tabela = tabela

    def calcular(
        self,
        valor_base: Decimal,
        ano_operacao: int,
        split_payment_active: bool = True,
    ) -> ResultadoCalculo:
        if valor_base <= 0:
            raise ValueError("valor_base deve ser positivo")

        fase = fase_para(ano_operacao)
        regra = self._tabela.buscar(fase)

        valor_is = (valor_base * regra.aliq_is).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        base_iva = valor_base + valor_is
        valor_cbs = (base_iva * regra.aliq_cbs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valor_ibs = (base_iva * regra.aliq_ibs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_tributos = valor_cbs + valor_ibs + valor_is
        valor_liquido = valor_base - (total_tributos if split_payment_active else Decimal("0"))

        return ResultadoCalculo(
            valor_base=valor_base,
            valor_is=valor_is,
            valor_cbs=valor_cbs,
            valor_ibs=valor_ibs,
            total_tributos=total_tributos,
            valor_liquido=valor_liquido,
            fonte_legal=regra.fonte_legal,
        )
