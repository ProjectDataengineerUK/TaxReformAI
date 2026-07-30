"""`aplicar_reducao_percentual` — a primeira função de cálculo nova desde o
Anexo I. Puro `motor_calculo`: sem banco, sem HTTP, sem uma linha de fake.

Os arts. 131 a 138 da LCP 214/2025 reduzem "em 60% (sessenta por cento) AS
ALÍQUOTAS do IBS e da CBS". O objeto da redução é a ALÍQUOTA, não o valor
devido, e essa distinção muda o número na resposta — é o que o teste de
arredondamento abaixo fixa.
"""

from decimal import Decimal

import pytest

from motor_calculo.engine import ResultadoCalculo, TaxCalculatorEngine, valor_do_tributo
from motor_calculo.fases import fase_para
from motor_calculo.reducoes import aplicar_reducao_a_zero, aplicar_reducao_percentual
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed

UM = Decimal("1.0000")
SESSENTA = Decimal("0.6000")

TABELA = TabelaAliquotasSeed()
REGRA_2026 = TABELA.buscar(fase_para(2026))


def _calcular(valor_base: str) -> ResultadoCalculo:
    """O resultado de verdade do engine, não um `ResultadoCalculo` montado à
    mão: a função nova recebe a MESMA `RegraFiscal` que produziu o resultado, e
    testar com um resultado inventado deixaria essa disciplina por verificar."""
    return TaxCalculatorEngine(tabela=TABELA).calcular(
        valor_base=Decimal(valor_base), ano_operacao=2026
    )


# A escolha que muda o número — Decisão 5 -------------------------------------


def test_reduz_a_aliquota_e_recalcula_em_vez_de_escalar_o_valor_arredondado():
    """O teste que FIXA a Decisão 5, com a entrada em que as duas leituras
    divergem.

    Com `base_iva = 137,49`:
      - escalar o valor já arredondado: round(137,49 x 0,9%) = 1,24 →
        1,24 x 0,40 = 0,496 → **0,50**
      - reduzir a alíquota e recalcular: 137,49 x 0,36% = 0,49496 → **0,49**

    Vale a segunda, e o argumento decisivo não é a lei (embora ela diga
    "alíquotas"): é que só ela é reproduzível pelo cliente a partir da alíquota
    que a resposta cita. Num produto cujo entregável é uma defesa fiscal, um
    número que não fecha com a própria fundamentação é pior que um número
    diferente.
    """
    resultado = _calcular("137.49")
    assert resultado.valor_is == Decimal("0.00"), "em 2026 o IS não incide"
    assert resultado.valor_cbs == Decimal("1.24"), "0,9% de 137,49, arredondado"

    reduzido = aplicar_reducao_percentual(resultado, REGRA_2026, SESSENTA)

    assert reduzido.valor_cbs == Decimal("0.49")
    assert reduzido.valor_cbs != Decimal("0.50"), (
        "0,50 é o resultado de escalar o valor JÁ ARREDONDADO — a leitura que a "
        "Decisão 5 rejeitou"
    )
    # E o número fecha com a alíquota que a resposta cita (0,36%).
    assert reduzido.valor_cbs == valor_do_tributo(
        Decimal("137.49"), REGRA_2026.aliq_cbs * Decimal("0.4000")
    )


def test_o_valor_reduzido_e_sempre_reproduzivel_pela_aliquota_citada():
    """A generalização do anterior sobre uma faixa de bases: para toda entrada, o
    cliente que refizer `base x alíquota_citada` tem de chegar ao mesmo centavo.
    """
    aliq_cbs_reduzida = REGRA_2026.aliq_cbs * (UM - SESSENTA)
    aliq_ibs_reduzida = REGRA_2026.aliq_ibs * (UM - SESSENTA)

    for centavos in range(1, 2000, 7):
        base = Decimal(centavos) / Decimal(100)
        reduzido = aplicar_reducao_percentual(_calcular(str(base)), REGRA_2026, SESSENTA)

        assert reduzido.valor_cbs == valor_do_tributo(base, aliq_cbs_reduzida), base
        assert reduzido.valor_ibs == valor_do_tributo(base, aliq_ibs_reduzida), base


def test_em_2026_a_aliquota_reduzida_e_0_36_por_cento_de_cbs_e_0_04_de_ibs():
    """Os dois números que o smoke test do deploy exige, calculados aqui: 0,9% x
    0,40 e 0,1% x 0,40. `0.36` é a asserção que SÓ o caminho novo satisfaz —
    `0` (zero) e `0.9` (sem redução) já existiam antes desta feature."""
    assert REGRA_2026.aliq_cbs * (UM - SESSENTA) * 100 == Decimal("0.36")
    assert REGRA_2026.aliq_ibs * (UM - SESSENTA) * 100 == Decimal("0.04")

    reduzido = aplicar_reducao_percentual(_calcular("1000.00"), REGRA_2026, SESSENTA)

    assert reduzido.valor_cbs == Decimal("3.60")  # 0,36% de 1000,00
    assert reduzido.valor_ibs == Decimal("0.40")  # 0,04% de 1000,00


# O que a redução NÃO toca ----------------------------------------------------


def test_o_imposto_seletivo_fica_intacto():
    """Os arts. 131-138 falam do IBS e da CBS. O IS tem lista própria (Anexo
    XVII, posição 16 do roadmap) — reduzi-lo aqui inventaria um benefício que a
    lei não deu, na direção perigosa."""
    resultado = ResultadoCalculo(
        valor_base=Decimal("1000.00"),
        valor_is=Decimal("50.00"),
        valor_cbs=Decimal("9.45"),
        valor_ibs=Decimal("1.05"),
        total_tributos=Decimal("60.50"),
        valor_liquido=Decimal("939.50"),
        fonte_legal="LCP 214/2025, arts. 343 e 346",
    )

    reduzido = aplicar_reducao_percentual(resultado, REGRA_2026, SESSENTA)

    assert reduzido.valor_is == Decimal("50.00")
    # A base do IVA continua sendo base + IS (o IS integra a base da CBS/IBS).
    assert reduzido.valor_cbs == valor_do_tributo(
        Decimal("1050.00"), REGRA_2026.aliq_cbs * Decimal("0.4000")
    )


def test_a_reducao_nao_muta_o_resultado_original():
    original = _calcular("1000.00")

    aplicar_reducao_percentual(original, REGRA_2026, SESSENTA)

    assert original.valor_cbs == Decimal("9.00")
    assert original.total_tributos == Decimal("10.00")


def test_a_fonte_legal_e_a_compensacao_atravessam_a_reducao():
    """`replace` preserva os campos que a redução não tem por que tocar — a
    citação da fase e o direito de compensação do art. 348 continuam valendo
    para o item reduzido."""
    resultado = _calcular("1000.00")

    reduzido = aplicar_reducao_percentual(resultado, REGRA_2026, SESSENTA)

    assert reduzido.fonte_legal == resultado.fonte_legal
    assert reduzido.compensavel == resultado.compensavel
    assert reduzido.fonte_legal_compensacao == resultado.fonte_legal_compensacao


# A invariante do líquido, compartilhada com `aplicar_reducao_a_zero` ---------


def test_o_liquido_e_recomposto_e_nao_fica_contraditorio():
    """Trocar CBS/IBS e deixar o líquido como estava produziria uma resposta
    internamente contraditória: líquido menor que o bruto sem tributo que o
    justifique. `_recompor` existe para essa invariante morar num lugar só."""
    reduzido = aplicar_reducao_percentual(_calcular("1000.00"), REGRA_2026, SESSENTA)

    assert reduzido.total_tributos == (
        reduzido.valor_cbs + reduzido.valor_ibs + reduzido.valor_is
    )
    assert reduzido.valor_liquido == reduzido.valor_base - reduzido.total_tributos
    assert reduzido.total_tributos == Decimal("4.00")  # 3,60 + 0,40 + 0,00
    assert reduzido.valor_liquido == Decimal("996.00")


def test_sem_split_payment_o_liquido_e_o_bruto():
    reduzido = aplicar_reducao_percentual(
        _calcular("1000.00"), REGRA_2026, SESSENTA, split_payment_active=False
    )

    assert reduzido.valor_liquido == reduzido.valor_base


# A equivalência que substitui o acoplamento — Decisão 5, motivo 4 ------------


@pytest.mark.parametrize(
    "base", ["1000.00", "137.49", "0.01", "99999.99", "1.00", "333.33", "7.77"]
)
def test_percentual_de_100_por_cento_coincide_com_a_reducao_a_zero(base):
    """`aplicar_reducao_a_zero` mantém assinatura e comportamento — é o MUST do
    DEFINE, e o caminho de zero continua passando por ela mesmo sendo hoje
    matematicamente equivalente a `aplicar_reducao_percentual(..., 1.0000)`.

    Manter o caminho já shipado INDEPENDENTE da `RegraFiscal` significa que um
    bug na leitura da regra não pode transformar um zero provado em outra coisa.
    Este teste é como se tem a garantia sem ter o acoplamento: se as duas
    divergirem, a divergência aparece aqui e não em produção.
    """
    resultado = _calcular(base)

    assert aplicar_reducao_percentual(resultado, REGRA_2026, UM) == (
        aplicar_reducao_a_zero(resultado)
    )


def test_percentual_zero_devolve_o_resultado_cheio():
    """O outro extremo, que a lei não usa mas o domínio da função contém: reduzir
    em 0% tem de ser a identidade, senão a fórmula está errada em algum ponto
    intermediário e o erro só apareceria num percentual futuro."""
    resultado = _calcular("1000.00")

    reduzido = aplicar_reducao_percentual(resultado, REGRA_2026, Decimal("0.0000"))

    assert reduzido == resultado


# `valor_do_tributo` — a fórmula mora num lugar só ---------------------------


def test_a_formula_do_tributo_extraida_nao_mudou_o_engine():
    """A extração de `valor_do_tributo` é refatoração pura (Decisão 5, motivo 3):
    `calcular` passa a usá-la, e o resultado é bit a bit o mesmo. Sem ela, a
    fórmula `round(base x alíquota)` existiria em dois arquivos e o dia em que o
    arredondamento mudasse mudaria só num."""
    resultado = _calcular("1000.00")

    assert resultado.valor_cbs == valor_do_tributo(
        resultado.valor_base + resultado.valor_is, REGRA_2026.aliq_cbs
    )
    assert resultado.valor_ibs == valor_do_tributo(
        resultado.valor_base + resultado.valor_is, REGRA_2026.aliq_ibs
    )
    assert resultado.valor_is == valor_do_tributo(
        resultado.valor_base, REGRA_2026.aliq_is
    )


@pytest.mark.parametrize(
    ("base", "aliquota", "esperado"),
    [
        ("100.00", "0.009", "0.90"),
        ("137.49", "0.0036", "0.49"),
        # ROUND_HALF_UP, não bancário: 0,005 sobe. Um sistema financeiro que
        # arredondasse para o par produziria diferença sistemática de centavos.
        ("1.00", "0.005", "0.01"),
        ("3.00", "0.005", "0.02"),
    ],
)
def test_valor_do_tributo_arredonda_em_centavos_com_round_half_up(
    base, aliquota, esperado
):
    assert valor_do_tributo(Decimal(base), Decimal(aliquota)) == Decimal(esperado)


def test_motor_calculo_segue_sem_dependencia_de_infraestrutura():
    """MUST do DEFINE, verificado no import: a função nova é pura. Se um dia
    alguém importar `psycopg` ou `api.*` aqui, o motor deixa de rodar sem
    infraestrutura e o teste inteiro deste arquivo passa a mentir."""
    import motor_calculo.reducoes as modulo

    fonte = modulo.__file__
    with open(fonte, encoding="utf-8") as arquivo:
        texto = arquivo.read()

    for proibido in ("import psycopg", "from api", "import api", "requests", "google."):
        assert proibido not in texto, f"{proibido} entrou em motor_calculo/reducoes.py"
