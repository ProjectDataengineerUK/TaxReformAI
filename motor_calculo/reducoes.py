"""Reduções de alíquota aplicadas por ITEM, depois do cálculo por fase.

`engine.calcular()` resolve CBS/IBS por FASE, uniforme para todo o payload — não
existe nele conceito de alíquota por produto, e introduzi-lo exigiria que o motor
conhecesse um lookup em banco. Este módulo é a alternativa: recebe o
`ResultadoCalculo` pronto e devolve outro, sem I/O, sem import de infraestrutura.

Mora em `motor_calculo/` (e não em `api/`) porque a composição
`valor_liquido = valor_base - total_tributos` é invariante do engine: se um dia o
split payment mudar de fórmula, os dois arquivos aparecem lado a lado em qualquer
busca por `valor_liquido`. Ver Decisão 6.

Duas funções, dois mecanismos que a LCP 214/2025 escreve com verbos diferentes:
`aplicar_reducao_a_zero` para "ficam reduzidas a zero as alíquotas" (arts. 125,
144, 145, 148 — Anexos I, XII, XIII, XV) e `aplicar_reducao_percentual` para
"ficam reduzidas em 60% (sessenta por cento) as alíquotas" (arts. 131 a 138 —
Anexos IV, V, VI, VII, VIII, IX).
"""

from dataclasses import replace
from decimal import Decimal

from motor_calculo.engine import ResultadoCalculo, valor_do_tributo
from motor_calculo.regras_fiscais import RegraFiscal

ZERO = Decimal("0.00")
UM = Decimal("1.0000")


def _recompor(
    resultado: ResultadoCalculo,
    *,
    valor_cbs: Decimal,
    valor_ibs: Decimal,
    split_payment_active: bool,
) -> ResultadoCalculo:
    """Reescreve CBS/IBS e recompõe total e líquido.

    Não é detalhe: trocar CBS/IBS e deixar o líquido como estava produziria uma
    resposta internamente contraditória — líquido menor que o bruto sem tributo
    que o justifique. Compartilhado pelas duas funções públicas para que a
    invariante `valor_liquido = valor_base - total_tributos` exista uma vez só.
    """
    total_tributos = valor_cbs + valor_ibs + resultado.valor_is
    return replace(
        resultado,
        valor_cbs=valor_cbs,
        valor_ibs=valor_ibs,
        total_tributos=total_tributos,
        valor_liquido=(
            resultado.valor_base - total_tributos
            if split_payment_active
            else resultado.valor_base
        ),
    )


def aplicar_reducao_a_zero(
    resultado: ResultadoCalculo, *, split_payment_active: bool = True
) -> ResultadoCalculo:
    """CBS e IBS a zero; IS intacto; líquido recomposto.

    Os arts. 125/144/145/148 reduzem a zero as alíquotas "do IBS e da CBS" — e
    só. O Imposto Seletivo tem lista própria (Anexo XVII), fora do escopo desta
    feature, então zerá-lo aqui seria inventar um benefício que a lei não deu.

    Assinatura e comportamento INALTERADOS pela feature dos Anexos de 60%, de
    propósito: ela continua sendo a função chamada no caminho de zero, mesmo
    sendo hoje matematicamente equivalente a
    `aplicar_reducao_percentual(..., Decimal("1.0000"))` — um teste prova a
    equivalência. Manter o caminho já shipado independente da `RegraFiscal`
    significa que um bug na leitura da regra não pode transformar um zero
    provado em outra coisa.

    `split_payment_active` precisa ser o MESMO valor passado a
    `engine.calcular()`; hoje as duas chamadas usam o default. Deduzi-lo do
    objeto (comparando líquido com bruto) seria adivinhar o passado dele.
    """
    return _recompor(
        resultado,
        valor_cbs=ZERO,
        valor_ibs=ZERO,
        split_payment_active=split_payment_active,
    )


def aplicar_reducao_percentual(
    resultado: ResultadoCalculo,
    regra: RegraFiscal,
    percentual_reducao: Decimal,
    *,
    split_payment_active: bool = True,
) -> ResultadoCalculo:
    """CBS e IBS recalculados com a ALÍQUOTA reduzida; IS intacto.

    Os arts. 131 a 138 reduzem "em 60% (sessenta por cento) AS ALÍQUOTAS do IBS
    e da CBS" — o objeto da redução é a alíquota, não o valor devido. A
    diferença não é retórica: escalar o valor já arredondado
    (`round(round(base*0,9%)*0,4)`) diverge de recalcular (`round(base*0,36%)`)
    em 1 centavo para entradas reais (base_iva 137,49 → 0,50 contra 0,49), e só
    a segunda é reproduzível pelo cliente a partir da alíquota que a resposta
    cita (0,36%). Num produto cujo entregável é uma defesa fiscal, um número que
    não fecha com a própria fundamentação é pior que um número diferente.

    O Imposto Seletivo não é tocado: os arts. 131-138 falam do IBS e da CBS, e o
    IS tem lista própria (Anexo XVII, posição 16 do roadmap).

    `percentual_reducao` é a fração da alíquota REMOVIDA: `Decimal("0.6000")`
    deixa 40% da alíquota da fase de pé.

    `regra` precisa ser a MESMA passada a `engine.calcular()` — mesma disciplina
    de `split_payment_active`. Deduzi-la do `ResultadoCalculo` (dividindo valor
    por base) seria adivinhar o passado dele, e falharia justamente onde houve
    arredondamento.
    """
    fator_restante = UM - percentual_reducao
    base_iva = resultado.valor_base + resultado.valor_is
    return _recompor(
        resultado,
        valor_cbs=valor_do_tributo(base_iva, regra.aliq_cbs * fator_restante),
        valor_ibs=valor_do_tributo(base_iva, regra.aliq_ibs * fator_restante),
        split_payment_active=split_payment_active,
    )
