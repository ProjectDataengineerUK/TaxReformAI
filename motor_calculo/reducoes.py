"""Reduções de alíquota aplicadas por ITEM, depois do cálculo por fase.

`engine.calcular()` resolve CBS/IBS por FASE, uniforme para todo o payload — não
existe nele conceito de alíquota por produto, e introduzi-lo exigiria que o motor
conhecesse um lookup em banco. Este módulo é a alternativa: recebe o
`ResultadoCalculo` pronto e devolve outro, sem I/O, sem import de infraestrutura.

Mora em `motor_calculo/` (e não em `api/`) porque a composição
`valor_liquido = valor_base - total_tributos` é invariante do engine: se um dia o
split payment mudar de fórmula, os dois arquivos aparecem lado a lado em qualquer
busca por `valor_liquido`. Ver Decisão 6.
"""

from dataclasses import replace
from decimal import Decimal

from motor_calculo.engine import ResultadoCalculo

ZERO = Decimal("0.00")


def aplicar_reducao_a_zero(
    resultado: ResultadoCalculo, *, split_payment_active: bool = True
) -> ResultadoCalculo:
    """CBS e IBS a zero; IS intacto; líquido recomposto.

    O art. 125 reduz a zero as alíquotas "do IBS e da CBS" — e só. O Imposto
    Seletivo tem lista própria (Anexo XVII), fora do escopo desta feature, então
    zerá-lo aqui seria inventar um benefício que a lei não deu.

    Recompor `total_tributos` e `valor_liquido` não é detalhe: zerar CBS/IBS e
    deixar o líquido como estava produziria uma resposta internamente
    contraditória — líquido menor que o bruto sem tributo que o justifique.

    `split_payment_active` precisa ser o MESMO valor passado a
    `engine.calcular()`; hoje as duas chamadas usam o default. Deduzi-lo do
    objeto (comparando líquido com bruto) seria adivinhar o passado dele.
    """
    total_tributos = resultado.valor_is
    return replace(
        resultado,
        valor_cbs=ZERO,
        valor_ibs=ZERO,
        total_tributos=total_tributos,
        valor_liquido=(
            resultado.valor_base - total_tributos
            if split_payment_active
            else resultado.valor_base
        ),
    )
