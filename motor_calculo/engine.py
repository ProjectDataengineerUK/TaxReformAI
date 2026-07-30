from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from motor_calculo.fases import fase_para
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotas


def valor_do_tributo(base: Decimal, aliquota: Decimal) -> Decimal:
    """Tributo em centavos, ROUND_HALF_UP.

    Pública porque `motor_calculo/reducoes.py` precisa da MESMA fórmula para
    recalcular CBS/IBS com a alíquota reduzida em 60% (arts. 131 a 138 da LCP
    214/2025). Duas cópias divergiriam no dia em que a regra de arredondamento
    mudasse — e a segunda ficaria para trás sem nenhum sintoma.
    """
    return (base * aliquota).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class ResultadoCalculo:
    valor_base: Decimal
    valor_is: Decimal
    valor_cbs: Decimal
    valor_ibs: Decimal
    total_tributos: Decimal
    valor_liquido: Decimal
    fonte_legal: str
    compensavel: bool = False
    fonte_legal_compensacao: str | None = None


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

        # Uma fase pode ser parcialmente conhecida (o art. 344 fixa o IBS de
        # 2027-2028, o art. 347 deixa a CBS pendente). Calcular só o que se sabe
        # produziria um total silenciosamente subestimado — pior que recusar.
        indisponiveis = regra.tributos_indisponiveis()
        if indisponiveis:
            raise AliquotaNaoDisponivelError(fase, tributos=indisponiveis, regra=regra)

        valor_is = valor_do_tributo(valor_base, regra.aliq_is)
        base_iva = valor_base + valor_is
        valor_cbs = valor_do_tributo(base_iva, regra.aliq_cbs)
        valor_ibs = valor_do_tributo(base_iva, regra.aliq_ibs)
        total_tributos = valor_cbs + valor_ibs + valor_is
        valor_liquido = valor_base - (total_tributos if split_payment_active else Decimal(0))

        return ResultadoCalculo(
            valor_base=valor_base,
            valor_is=valor_is,
            valor_cbs=valor_cbs,
            valor_ibs=valor_ibs,
            total_tributos=total_tributos,
            valor_liquido=valor_liquido,
            fonte_legal=regra.fonte_legal,
            compensavel=regra.compensavel,
            fonte_legal_compensacao=regra.fonte_legal_compensacao,
        )
