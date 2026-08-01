"""Integração de CBS/IBS à partilha do Simples Nacional (LCP 214/2025, Anexos
XVIII-XXIII — que reproduzem, com CBS/IBS incorporados, os Anexos I, II, III,
IV, V e VII da LC 123/2006).

Regime SUBSTITUTIVO, não uma redução sobre `engine.py`/`tabela_aliquotas.py`:
o Simples Nacional troca IRPJ/CSLL/CBS/CPP/ICMS-ou-ISS/IBS por um DAS único,
calculado sobre a receita bruta mensal por uma fórmula própria (LC 123/2006,
art. 18, §§1º, 1º-A e 1º-B, redação da LC 155/2016) — nunca a partir da
alíquota do IVA Dual do regime geral. Por isso este módulo não importa nada
de `engine.py`/`tabela_aliquotas.py`/`fases.py`.

Todos os números vêm do PDF "Texto Atualizado" da LCP 214/2025 (Câmara dos
Deputados) e do texto compilado da LC 123/2006 (planalto.gov.br), verificados
linha a linha contra o próprio texto (cross-check com legis.senado.leg.br em
5 dos 6 Anexos) no `/define`/`/design` — ver
`.claude/sdd/features/DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md` para o
método de verificação e as duas armadilhas de extração encontradas (WebFetch
truncando o Anexo XXIII em 2031; uma célula do Anexo XXI/2029 desambiguada
com `pdftotext -raw` em vez de `-layout`).

Achado central do art. 19, §4º da LC 123/2006: acima do "sublimite" de
R$3.600.000,00 (o piso da 6ª Faixa), ICMS e ISS — e por extensão o IBS, seu
substituto na reforma — são recolhidos SEPARADAMENTE, fora do DAS, pelo
regime geral. É por isso que a 6ª Faixa de todo Anexo "percentual" não tem
essas colunas: não é lacuna de transcrição.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

CEM = Decimal(100)
CENTAVOS = Decimal("0.01")

FONTE_FORMULA = "LC 123/2006, art. 18, §§1º, 1º-A e 1º-B (redação da LC 155/2016)"
FONTE_SUBLIMITE = "LC 123/2006, art. 19, §4º"


def _p(valor: str | None) -> Decimal | None:
    """Converte uma string de percentual literal (\"15.33\") na fração que o
    resto do projeto usa (Decimal(\"0.1533\")) — mesma convenção de
    `regime_atual.py`. `None` permanece `None` (tributo ausente naquela
    faixa/Anexo, nunca zero)."""
    return None if valor is None else Decimal(valor) / CEM


class Atividade(StrEnum):
    COMERCIO = "COMERCIO"  # Anexo XVIII -> LC 123/2006, Anexo I
    INDUSTRIA = "INDUSTRIA"  # Anexo XIX -> Anexo II
    LOCACAO_SERVICO_GERAL = "LOCACAO_SERVICO_GERAL"  # Anexo XX -> Anexo III (teto ISS)
    SERVICO_PAR_5C = "SERVICO_PAR_5C"  # Anexo XXI -> Anexo IV (sem CPP, teto ISS)
    SERVICO_PAR_5I = "SERVICO_PAR_5I"  # Anexo XXII -> Anexo V
    MEI = "MEI"  # Anexo XXIII -> Anexo VII (valor fixo)


ANEXO_REF: dict[Atividade, str] = {
    Atividade.COMERCIO: "LCP 214/2025, Anexo XVIII (LC 123/2006, Anexo I)",
    Atividade.INDUSTRIA: "LCP 214/2025, Anexo XIX (LC 123/2006, Anexo II)",
    Atividade.LOCACAO_SERVICO_GERAL: "LCP 214/2025, Anexo XX (LC 123/2006, Anexo III)",
    Atividade.SERVICO_PAR_5C: "LCP 214/2025, Anexo XXI (LC 123/2006, Anexo IV)",
    Atividade.SERVICO_PAR_5I: "LCP 214/2025, Anexo XXII (LC 123/2006, Anexo V)",
    Atividade.MEI: "LCP 214/2025, Anexo XXIII (LC 123/2006, Anexo VII)",
}

TETOS_ISS_ATIVIDADES = frozenset({Atividade.LOCACAO_SERVICO_GERAL, Atividade.SERVICO_PAR_5C})


@dataclass(frozen=True)
class FaixaReceita:
    faixa: int  # 1-6
    limite_inferior: Decimal
    limite_superior: Decimal | None  # None só na 6ª Faixa em tese; aqui sempre 4_800_000.00
    aliquota_nominal: Decimal
    valor_deduzir: Decimal


@dataclass(frozen=True)
class PartilhaPercentual:
    irpj: Decimal
    csll: Decimal
    cbs: Decimal
    cpp: Decimal | None  # None só em SERVICO_PAR_5C (Anexo XXI)
    icms: Decimal | None  # só COMERCIO/INDUSTRIA, faixas 1-5
    iss: Decimal | None  # só Anexos de serviço, faixas 1-5
    ibs: Decimal | None  # faixas 1-5; None na 6ª (sublimite, art. 19 §4º)
    ipi: Decimal | None  # só INDUSTRIA


@dataclass(frozen=True)
class TetoIss:
    gatilho_aliquota_efetiva: Decimal
    limite_percentual: Decimal
    coef_irpj: Decimal
    coef_csll: Decimal
    coef_cbs: Decimal
    coef_cpp: Decimal | None  # None em SERVICO_PAR_5C
    coef_ibs: Decimal


@dataclass(frozen=True)
class ValorFixoMei:
    icms: Decimal | None  # None a partir de 2033
    iss: Decimal | None  # None a partir de 2033
    cbs: Decimal
    ibs: Decimal


@dataclass(frozen=True)
class ResultadoSimplesNacional:
    atividade: Atividade
    ano_operacao: int
    faixa: int | None  # None só para MEI
    aliquota_nominal: Decimal | None
    valor_deduzir: Decimal | None
    aliquota_efetiva: Decimal | None  # None só para MEI
    receita_bruta_acumulada_12_meses: Decimal | None
    receita_bruta_mes: Decimal
    partilha_percentual: dict[str, Decimal]  # tributo -> percentual efetivo (vazio p/ MEI)
    valores_devidos: dict[str, Decimal]  # tributo -> R$ devido no mês
    valor_total_das: Decimal
    teto_iss_aplicado: bool
    icms_iss_fora_do_das: bool
    dispositivo_legal_ref: str


def _chave_periodo_faixas(ano: int) -> int:
    """A Tabela 1 (faixas) tem só 2 versões: 2027-2028 e "a partir de 2029" —
    idênticas exceto a 6ª Faixa (alíquota nominal sobe ~0,10 p.p. e permanece
    assim para sempre)."""
    return 2027 if ano <= 2028 else 2029


def _chave_periodo_partilha(ano: int) -> int:
    """A Tabela 2 (partilha) muda todo ano até 2033, quando se torna
    permanente — `min(ano, 2033)` cobre qualquer ano futuro sem duplicar
    linha (Decisão 4 do DESIGN)."""
    if ano <= 2028:
        return 2027
    return min(ano, 2033)


# ---------------------------------------------------------------------------
# Tabela 1 — faixas de receita bruta, por Atividade e período
# ---------------------------------------------------------------------------

_FAIXAS: dict[Atividade, dict[int, list[FaixaReceita]]] = {
    Atividade.COMERCIO: {
        2027: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.00"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("7.30"), Decimal("5940.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("9.50"), Decimal("13860.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("10.70"), Decimal("22500.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("14.30"), Decimal("87300.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("18.90"), Decimal("378000.00")),
        ],
        2029: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.00"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("7.30"), Decimal("5940.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("9.50"), Decimal("13860.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("10.70"), Decimal("22500.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("14.30"), Decimal("87300.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("19.00"), Decimal("378000.00")),
        ],
    },
    Atividade.INDUSTRIA: {
        2027: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("7.80"), Decimal("5940.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("10.00"), Decimal("13860.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("11.20"), Decimal("22500.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("14.70"), Decimal("85500.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("29.90"), Decimal("720000.00")),
        ],
        2029: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("7.80"), Decimal("5940.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("10.00"), Decimal("13860.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("11.20"), Decimal("22500.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("14.70"), Decimal("85500.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("30.00"), Decimal("720000.00")),
        ],
    },
    Atividade.LOCACAO_SERVICO_GERAL: {
        2027: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("6.00"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("11.20"), Decimal("9360.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("13.50"), Decimal("17640.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("16.00"), Decimal("35640.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("21.00"), Decimal("125640.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("32.90"), Decimal("648000.00")),
        ],
        2029: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("6.00"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("11.20"), Decimal("9360.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("13.50"), Decimal("17640.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("16.00"), Decimal("35640.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("21.00"), Decimal("125640.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("33.00"), Decimal("648000.00")),
        ],
    },
    Atividade.SERVICO_PAR_5C: {
        2027: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("9.00"), Decimal("8100.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("10.20"), Decimal("12420.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("14.00"), Decimal("39780.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("22.00"), Decimal("183780.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("32.90"), Decimal("828000.00")),
        ],
        2029: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("4.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("9.00"), Decimal("8100.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("10.20"), Decimal("12420.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("14.00"), Decimal("39780.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("22.00"), Decimal("183780.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("33.00"), Decimal("828000.00")),
        ],
    },
    Atividade.SERVICO_PAR_5I: {
        2027: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("15.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("18.00"), Decimal("4500.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("19.50"), Decimal("9900.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("20.50"), Decimal("17100.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("23.00"), Decimal("62100.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("30.40"), Decimal("540000.00")),
        ],
        2029: [
            FaixaReceita(1, Decimal("0.00"), Decimal("180000.00"), _p("15.50"), Decimal("0.00")),
            FaixaReceita(2, Decimal("180000.01"), Decimal("360000.00"), _p("18.00"), Decimal("4500.00")),
            FaixaReceita(3, Decimal("360000.01"), Decimal("720000.00"), _p("19.50"), Decimal("9900.00")),
            FaixaReceita(4, Decimal("720000.01"), Decimal("1800000.00"), _p("20.50"), Decimal("17100.00")),
            FaixaReceita(5, Decimal("1800000.01"), Decimal("3600000.00"), _p("23.00"), Decimal("62100.00")),
            FaixaReceita(6, Decimal("3600000.01"), Decimal("4800000.00"), _p("30.50"), Decimal("540000.00")),
        ],
    },
}


# ---------------------------------------------------------------------------
# Tabela 2 — partilha percentual por Atividade, faixa, ano
# ---------------------------------------------------------------------------

_PARTILHA: dict[Atividade, dict[int, dict[int, PartilhaPercentual]]] = {
    Atividade.COMERCIO: {
        2027: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.33"), _p("41.50"), _p("34.00"), None, _p("0.17"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.33"), _p("41.50"), _p("34.00"), None, _p("0.17"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.33"), _p("42.00"), _p("33.50"), None, _p("0.17"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.33"), _p("42.00"), _p("33.50"), None, _p("0.17"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.33"), _p("42.00"), _p("33.50"), None, _p("0.17"), None),
            6: PartilhaPercentual(_p("13.58"), _p("10.06"), _p("34.02"), _p("42.34"), None, None, None, None),
        },
        2029: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("30.60"), None, _p("3.40"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("30.60"), None, _p("3.40"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("30.15"), None, _p("3.35"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("30.15"), None, _p("3.35"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("30.15"), None, _p("3.35"), None),
            6: PartilhaPercentual(_p("13.50"), _p("10.00"), _p("34.40"), _p("42.10"), None, None, None, None),
        },
        2030: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("27.20"), None, _p("6.80"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("27.20"), None, _p("6.80"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("26.80"), None, _p("6.70"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("26.80"), None, _p("6.70"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("26.80"), None, _p("6.70"), None),
            6: PartilhaPercentual(_p("13.50"), _p("10.00"), _p("34.40"), _p("42.10"), None, None, None, None),
        },
        2031: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("23.80"), None, _p("10.20"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("23.80"), None, _p("10.20"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("23.45"), None, _p("10.05"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("23.45"), None, _p("10.05"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("23.45"), None, _p("10.05"), None),
            6: PartilhaPercentual(_p("13.50"), _p("10.00"), _p("34.40"), _p("42.10"), None, None, None, None),
        },
        2032: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("20.40"), None, _p("13.60"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), _p("20.40"), None, _p("13.60"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("20.10"), None, _p("13.40"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("20.10"), None, _p("13.40"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), _p("20.10"), None, _p("13.40"), None),
            6: PartilhaPercentual(_p("13.50"), _p("10.00"), _p("34.40"), _p("42.10"), None, None, None, None),
        },
        2033: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), None, None, _p("34.00"), None),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("41.50"), None, None, _p("34.00"), None),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), None, None, _p("33.50"), None),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), None, None, _p("33.50"), None),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("15.50"), _p("42.00"), None, None, _p("33.50"), None),
            6: PartilhaPercentual(_p("13.50"), _p("10.00"), _p("34.40"), _p("42.10"), None, None, None, None),
        },
    },
    Atividade.INDUSTRIA: {
        2027: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("13.85"), _p("37.50"), _p("32.00"), None, _p("0.15"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("13.85"), _p("37.50"), _p("32.00"), None, _p("0.15"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("13.85"), _p("37.50"), _p("32.00"), None, _p("0.15"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("13.85"), _p("37.50"), _p("32.00"), None, _p("0.15"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("13.85"), _p("37.50"), _p("32.00"), None, _p("0.15"), _p("7.50")),
            6: PartilhaPercentual(_p("8.53"), _p("7.53"), _p("25.22"), _p("23.59"), None, None, None, _p("35.13")),
        },
        2029: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("28.80"), None, _p("3.20"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("28.80"), None, _p("3.20"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("28.80"), None, _p("3.20"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("28.80"), None, _p("3.20"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("28.80"), None, _p("3.20"), _p("7.50")),
            6: PartilhaPercentual(_p("8.50"), _p("7.50"), _p("25.50"), _p("23.50"), None, None, None, _p("35.00")),
        },
        2030: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("25.60"), None, _p("6.40"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("25.60"), None, _p("6.40"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("25.60"), None, _p("6.40"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("25.60"), None, _p("6.40"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("25.60"), None, _p("6.40"), _p("7.50")),
            6: PartilhaPercentual(_p("8.50"), _p("7.50"), _p("25.50"), _p("23.50"), None, None, None, _p("35.00")),
        },
        2031: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("22.40"), None, _p("9.60"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("22.40"), None, _p("9.60"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("22.40"), None, _p("9.60"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("22.40"), None, _p("9.60"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("22.40"), None, _p("9.60"), _p("7.50")),
            6: PartilhaPercentual(_p("8.50"), _p("7.50"), _p("25.50"), _p("23.50"), None, None, None, _p("35.00")),
        },
        2032: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("19.20"), None, _p("12.80"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("19.20"), None, _p("12.80"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("19.20"), None, _p("12.80"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("19.20"), None, _p("12.80"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), _p("19.20"), None, _p("12.80"), _p("7.50")),
            6: PartilhaPercentual(_p("8.50"), _p("7.50"), _p("25.50"), _p("23.50"), None, None, None, _p("35.00")),
        },
        2033: {
            1: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), None, None, _p("32.00"), _p("7.50")),
            2: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), None, None, _p("32.00"), _p("7.50")),
            3: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), None, None, _p("32.00"), _p("7.50")),
            4: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), None, None, _p("32.00"), _p("7.50")),
            5: PartilhaPercentual(_p("5.50"), _p("3.50"), _p("14.00"), _p("37.50"), None, None, _p("32.00"), _p("7.50")),
            6: PartilhaPercentual(_p("8.50"), _p("7.50"), _p("25.50"), _p("23.50"), None, None, None, _p("35.00")),
        },
    },
    Atividade.LOCACAO_SERVICO_GERAL: {
        2027: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.43"), _p("43.40"), None, _p("33.50"), _p("0.17"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.91"), _p("43.40"), None, _p("32.00"), _p("0.19"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.41"), _p("43.40"), None, _p("32.50"), _p("0.19"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.41"), _p("43.40"), None, _p("32.50"), _p("0.19"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.43"), _p("43.40"), None, _p("33.50"), _p("0.17"), None),
            6: PartilhaPercentual(_p("35.09"), _p("15.04"), _p("19.29"), _p("30.58"), None, None, None, None),
        },
        2029: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("30.15"), _p("3.35"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("17.10"), _p("43.40"), None, _p("28.80"), _p("3.20"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("29.25"), _p("3.25"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("29.25"), _p("3.25"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("30.15"), _p("3.35"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.00"), _p("19.50"), _p("30.50"), None, None, None, None),
        },
        2030: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("26.80"), _p("6.70"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("17.10"), _p("43.40"), None, _p("25.60"), _p("6.40"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("26.00"), _p("6.50"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("26.00"), _p("6.50"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("26.80"), _p("6.70"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.00"), _p("19.50"), _p("30.50"), None, None, None, None),
        },
        2031: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("23.45"), _p("10.05"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("17.10"), _p("43.40"), None, _p("22.40"), _p("9.60"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("22.75"), _p("9.75"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("22.75"), _p("9.75"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("23.45"), _p("10.05"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.00"), _p("19.50"), _p("30.50"), None, None, None, None),
        },
        2032: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("20.10"), _p("13.40"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("17.10"), _p("43.40"), None, _p("19.20"), _p("12.80"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("19.50"), _p("13.00"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, _p("19.50"), _p("13.00"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, _p("20.10"), _p("13.40"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.00"), _p("19.50"), _p("30.50"), None, None, None, None),
        },
        2033: {
            1: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, None, _p("33.50"), None),
            2: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("17.10"), _p("43.40"), None, None, _p("32.00"), None),
            3: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, None, _p("32.50"), None),
            4: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("16.60"), _p("43.40"), None, None, _p("32.50"), None),
            5: PartilhaPercentual(_p("4.00"), _p("3.50"), _p("15.60"), _p("43.40"), None, None, _p("33.50"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.00"), _p("19.50"), _p("30.50"), None, None, None, None),
        },
    },
    Atividade.SERVICO_PAR_5C: {
        2027: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.26"), None, None, _p("44.50"), _p("0.24"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("24.73"), None, None, _p("40.00"), _p("0.27"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("23.74"), None, None, _p("40.00"), _p("0.26"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("22.75"), None, None, _p("40.00"), _p("0.25"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("21.76"), None, None, _p("40.00"), _p("0.24"), None),
            6: PartilhaPercentual(_p("53.71"), _p("21.59"), _p("24.70"), None, None, None, None, None),
        },
        2029: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.50"), None, None, _p("40.05"), _p("4.45"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("25.00"), None, None, _p("36.00"), _p("4.00"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("24.00"), None, None, _p("36.00"), _p("4.00"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("23.00"), None, None, _p("36.00"), _p("4.00"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("22.00"), None, None, _p("36.00"), _p("4.00"), None),
            6: PartilhaPercentual(_p("53.50"), _p("21.50"), _p("25.00"), None, None, None, None, None),
        },
        2030: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.50"), None, None, _p("35.60"), _p("8.90"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("25.00"), None, None, _p("32.00"), _p("8.00"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("24.00"), None, None, _p("32.00"), _p("8.00"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("23.00"), None, None, _p("32.00"), _p("8.00"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("22.00"), None, None, _p("32.00"), _p("8.00"), None),
            6: PartilhaPercentual(_p("53.50"), _p("21.50"), _p("25.00"), None, None, None, None, None),
        },
        2031: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.50"), None, None, _p("31.15"), _p("13.35"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("25.00"), None, None, _p("28.00"), _p("12.00"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("24.00"), None, None, _p("28.00"), _p("12.00"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("23.00"), None, None, _p("28.00"), _p("12.00"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("22.00"), None, None, _p("28.00"), _p("12.00"), None),
            6: PartilhaPercentual(_p("53.50"), _p("21.50"), _p("25.00"), None, None, None, None, None),
        },
        2032: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.50"), None, None, _p("26.70"), _p("17.80"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("25.00"), None, None, _p("24.00"), _p("16.00"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("24.00"), None, None, _p("24.00"), _p("16.00"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("23.00"), None, None, _p("24.00"), _p("16.00"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("22.00"), None, None, _p("24.00"), _p("16.00"), None),
            6: PartilhaPercentual(_p("53.50"), _p("21.50"), _p("25.00"), None, None, None, None, None),
        },
        2033: {
            1: PartilhaPercentual(_p("18.80"), _p("15.20"), _p("21.50"), None, None, None, _p("44.50"), None),
            2: PartilhaPercentual(_p("19.80"), _p("15.20"), _p("25.00"), None, None, None, _p("40.00"), None),
            3: PartilhaPercentual(_p("20.80"), _p("15.20"), _p("24.00"), None, None, None, _p("40.00"), None),
            4: PartilhaPercentual(_p("17.80"), _p("19.20"), _p("23.00"), None, None, None, _p("40.00"), None),
            5: PartilhaPercentual(_p("18.80"), _p("19.20"), _p("22.00"), None, None, None, _p("40.00"), None),
            6: PartilhaPercentual(_p("53.50"), _p("21.50"), _p("25.00"), None, None, None, None, None),
        },
    },
    Atividade.SERVICO_PAR_5I: {
        2027: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("16.96"), _p("28.85"), None, _p("14.00"), _p("0.19"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("16.96"), _p("27.85"), None, _p("17.00"), _p("0.19"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("17.95"), _p("23.85"), None, _p("19.00"), _p("0.20"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("18.94"), _p("23.85"), None, _p("21.00"), _p("0.21"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("16.96"), _p("23.85"), None, _p("23.50"), _p("0.19"), None),
            6: PartilhaPercentual(_p("35.10"), _p("15.54"), _p("19.78"), _p("29.58"), None, None, None, None),
        },
        2029: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("17.15"), _p("28.85"), None, _p("12.60"), _p("1.40"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("17.15"), _p("27.85"), None, _p("15.30"), _p("1.70"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("18.15"), _p("23.85"), None, _p("17.10"), _p("1.90"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("19.15"), _p("23.85"), None, _p("18.90"), _p("2.10"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("17.15"), _p("23.85"), None, _p("21.15"), _p("2.35"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.50"), _p("20.00"), _p("29.50"), None, None, None, None),
        },
        2030: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("17.15"), _p("28.85"), None, _p("11.20"), _p("2.80"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("17.15"), _p("27.85"), None, _p("13.60"), _p("3.40"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("18.15"), _p("23.85"), None, _p("15.20"), _p("3.80"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("19.15"), _p("23.85"), None, _p("16.80"), _p("4.20"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("17.15"), _p("23.85"), None, _p("18.80"), _p("4.70"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.50"), _p("20.00"), _p("29.50"), None, None, None, None),
        },
        2031: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("17.15"), _p("28.85"), None, _p("9.80"), _p("4.20"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("17.15"), _p("27.85"), None, _p("11.90"), _p("5.10"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("18.15"), _p("23.85"), None, _p("13.30"), _p("5.70"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("19.15"), _p("23.85"), None, _p("14.70"), _p("6.30"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("17.15"), _p("23.85"), None, _p("16.45"), _p("7.05"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.50"), _p("20.00"), _p("29.50"), None, None, None, None),
        },
        2032: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("17.15"), _p("28.85"), None, _p("8.40"), _p("5.60"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("17.15"), _p("27.85"), None, _p("10.20"), _p("6.80"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("18.15"), _p("23.85"), None, _p("11.40"), _p("7.60"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("19.15"), _p("23.85"), None, _p("12.60"), _p("8.40"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("17.15"), _p("23.85"), None, _p("14.10"), _p("9.40"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.50"), _p("20.00"), _p("29.50"), None, None, None, None),
        },
        2033: {
            1: PartilhaPercentual(_p("25.00"), _p("15.00"), _p("17.15"), _p("28.85"), None, None, _p("14.00"), None),
            2: PartilhaPercentual(_p("23.00"), _p("15.00"), _p("17.15"), _p("27.85"), None, None, _p("17.00"), None),
            3: PartilhaPercentual(_p("24.00"), _p("15.00"), _p("18.15"), _p("23.85"), None, None, _p("19.00"), None),
            4: PartilhaPercentual(_p("21.00"), _p("15.00"), _p("19.15"), _p("23.85"), None, None, _p("21.00"), None),
            5: PartilhaPercentual(_p("23.00"), _p("12.50"), _p("17.15"), _p("23.85"), None, None, _p("23.50"), None),
            6: PartilhaPercentual(_p("35.00"), _p("15.50"), _p("20.00"), _p("29.50"), None, None, None, None),
        },
    },
}


# ---------------------------------------------------------------------------
# Teto de ISS (Anexos XX/XXI, 5ª Faixa) — coeficientes MUDAM todo ano
# ---------------------------------------------------------------------------

_TETO_ISS: dict[Atividade, dict[int, TetoIss]] = {
    Atividade.LOCACAO_SERVICO_GERAL: {
        2027: TetoIss(_p("14.92537"), _p("5.00"), _p("6.02"), _p("5.26"), _p("23.20"), _p("65.26"), _p("0.26")),
        2029: TetoIss(_p("14.92537"), _p("4.50"), _p("5.73"), _p("5.01"), _p("22.33"), _p("62.13"), _p("4.80")),
        2030: TetoIss(_p("14.92537"), _p("4.00"), _p("5.46"), _p("4.78"), _p("21.31"), _p("59.29"), _p("9.15")),
        2031: TetoIss(_p("14.92537"), _p("3.50"), _p("5.23"), _p("4.57"), _p("20.38"), _p("56.69"), _p("13.13")),
        2032: TetoIss(_p("14.92537"), _p("3.00"), _p("5.01"), _p("4.38"), _p("19.52"), _p("54.32"), _p("16.77")),
    },
    Atividade.SERVICO_PAR_5C: {
        2027: TetoIss(_p("12.5"), _p("5.00"), _p("31.33"), _p("32.00"), _p("36.27"), None, _p("0.40")),
        2029: TetoIss(_p("12.5"), _p("4.50"), _p("29.38"), _p("30.00"), _p("34.38"), None, _p("6.25")),
        2030: TetoIss(_p("12.5"), _p("4.00"), _p("27.65"), _p("28.24"), _p("32.35"), None, _p("11.76")),
        2031: TetoIss(_p("12.5"), _p("3.50"), _p("26.11"), _p("26.67"), _p("30.56"), None, _p("16.67")),
        2032: TetoIss(_p("12.5"), _p("3.00"), _p("24.74"), _p("25.26"), _p("28.95"), None, _p("21.05")),
    },
}


# ---------------------------------------------------------------------------
# Anexo XXIII (MEI) — valores fixos em R$
# ---------------------------------------------------------------------------

_MEI: dict[int, ValorFixoMei] = {
    2027: ValorFixoMei(Decimal("1.00"), Decimal("5.00"), Decimal("0.994"), Decimal("0.006")),
    2029: ValorFixoMei(Decimal("0.90"), Decimal("4.50"), Decimal("1.00"), Decimal("0.20")),
    2030: ValorFixoMei(Decimal("0.80"), Decimal("4.00"), Decimal("1.00"), Decimal("0.40")),
    2031: ValorFixoMei(Decimal("0.70"), Decimal("3.50"), Decimal("1.00"), Decimal("0.60")),
    2032: ValorFixoMei(Decimal("0.60"), Decimal("3.00"), Decimal("1.00"), Decimal("0.80")),
    2033: ValorFixoMei(None, None, Decimal("1.00"), Decimal("2.00")),
}


# ---------------------------------------------------------------------------
# Fórmula do art. 18, LC 123/2006
# ---------------------------------------------------------------------------


def calcular_aliquota_efetiva(
    rbt12: Decimal, aliquota_nominal: Decimal, valor_deduzir: Decimal
) -> Decimal:
    """LC 123/2006, art. 18, §1º-A: (RBT12 x Aliq - PD) / RBT12.

    Divisão por RBT12 confirmada via inspeção do HTML bruto de
    planalto.gov.br (formatação de fração — numerador sublinhado,
    denominador na mesma célula) — ver
    DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md.
    """
    return (rbt12 * aliquota_nominal - valor_deduzir) / rbt12


def calcular_percentual_por_tributo(
    aliquota_efetiva: Decimal, percentual_reparticao: Decimal
) -> Decimal:
    """LC 123/2006, art. 18, §1º-B: percentual efetivo do tributo = alíquota
    efetiva x percentual de repartição do Anexo."""
    return aliquota_efetiva * percentual_reparticao


def _buscar_faixa(atividade: Atividade, rbt12: Decimal, ano: int) -> FaixaReceita:
    faixas = _FAIXAS[atividade][_chave_periodo_faixas(ano)]
    for faixa in faixas:
        limite_sup = faixa.limite_superior
        if rbt12 >= faixa.limite_inferior and (limite_sup is None or rbt12 <= limite_sup):
            return faixa
    raise ValueError(
        f"receita_bruta_acumulada_12_meses={rbt12} excede o teto do Simples "
        "Nacional (R$4.800.000,00, 6ª Faixa) — fora da faixa de receita "
        "coberta por qualquer um dos 6 Anexos."
    )


def _partilha_por_tributo(
    percentuais: PartilhaPercentual, aliquota_efetiva: Decimal
) -> dict[str, Decimal]:
    resultado: dict[str, Decimal] = {}
    for tributo, percentual in (
        ("IRPJ", percentuais.irpj),
        ("CSLL", percentuais.csll),
        ("CBS", percentuais.cbs),
        ("CPP", percentuais.cpp),
        ("ICMS", percentuais.icms),
        ("ISS", percentuais.iss),
        ("IBS", percentuais.ibs),
        ("IPI", percentuais.ipi),
    ):
        if percentual is not None:
            resultado[tributo] = calcular_percentual_por_tributo(aliquota_efetiva, percentual)
    return resultado


def _valores_devidos(
    partilha_percentual: dict[str, Decimal], receita_bruta_mes: Decimal
) -> dict[str, Decimal]:
    return {
        tributo: (receita_bruta_mes * percentual).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        for tributo, percentual in partilha_percentual.items()
    }


def _calcular_percentual_simples(
    atividade: Atividade, rbt12: Decimal, receita_bruta_mes: Decimal, ano: int
) -> ResultadoSimplesNacional:
    faixa = _buscar_faixa(atividade, rbt12, ano)
    aliquota_efetiva = calcular_aliquota_efetiva(rbt12, faixa.aliquota_nominal, faixa.valor_deduzir)
    percentuais = _PARTILHA[atividade][_chave_periodo_partilha(ano)][faixa.faixa]
    partilha_percentual = _partilha_por_tributo(percentuais, aliquota_efetiva)
    valores_devidos = _valores_devidos(partilha_percentual, receita_bruta_mes)
    return ResultadoSimplesNacional(
        atividade=atividade,
        ano_operacao=ano,
        faixa=faixa.faixa,
        aliquota_nominal=faixa.aliquota_nominal,
        valor_deduzir=faixa.valor_deduzir,
        aliquota_efetiva=aliquota_efetiva,
        receita_bruta_acumulada_12_meses=rbt12,
        receita_bruta_mes=receita_bruta_mes,
        partilha_percentual=partilha_percentual,
        valores_devidos=valores_devidos,
        valor_total_das=sum(valores_devidos.values(), Decimal("0.00")),
        teto_iss_aplicado=False,
        icms_iss_fora_do_das=(faixa.faixa == 6),
        dispositivo_legal_ref=f"{ANEXO_REF[atividade]}, {faixa.faixa}ª Faixa; {FONTE_FORMULA}",
    )


def _calcular_percentual_com_teto_iss(
    atividade: Atividade, rbt12: Decimal, receita_bruta_mes: Decimal, ano: int
) -> ResultadoSimplesNacional:
    faixa = _buscar_faixa(atividade, rbt12, ano)
    aliquota_efetiva = calcular_aliquota_efetiva(rbt12, faixa.aliquota_nominal, faixa.valor_deduzir)
    percentuais = _PARTILHA[atividade][_chave_periodo_partilha(ano)][faixa.faixa]

    teto_iss_aplicado = False
    if faixa.faixa == 5:
        teto = _TETO_ISS[atividade].get(_chave_periodo_partilha(ano))
        if teto is not None and aliquota_efetiva > teto.gatilho_aliquota_efetiva:
            teto_iss_aplicado = True
            excedente = aliquota_efetiva - teto.limite_percentual
            partilha_percentual = {
                "IRPJ": excedente * teto.coef_irpj,
                "CSLL": excedente * teto.coef_csll,
                "CBS": excedente * teto.coef_cbs,
                "ISS": teto.limite_percentual,
                "IBS": excedente * teto.coef_ibs,
            }
            if teto.coef_cpp is not None:
                partilha_percentual["CPP"] = excedente * teto.coef_cpp
            valores_devidos = _valores_devidos(partilha_percentual, receita_bruta_mes)
            return ResultadoSimplesNacional(
                atividade=atividade,
                ano_operacao=ano,
                faixa=faixa.faixa,
                aliquota_nominal=faixa.aliquota_nominal,
                valor_deduzir=faixa.valor_deduzir,
                aliquota_efetiva=aliquota_efetiva,
                receita_bruta_acumulada_12_meses=rbt12,
                receita_bruta_mes=receita_bruta_mes,
                partilha_percentual=partilha_percentual,
                valores_devidos=valores_devidos,
                valor_total_das=sum(valores_devidos.values(), Decimal("0.00")),
                teto_iss_aplicado=True,
                icms_iss_fora_do_das=False,
                dispositivo_legal_ref=(
                    f"{ANEXO_REF[atividade]}, {faixa.faixa}ª Faixa, cláusula de teto de ISS; "
                    f"{FONTE_FORMULA}"
                ),
            )

    partilha_percentual = _partilha_por_tributo(percentuais, aliquota_efetiva)
    valores_devidos = _valores_devidos(partilha_percentual, receita_bruta_mes)
    return ResultadoSimplesNacional(
        atividade=atividade,
        ano_operacao=ano,
        faixa=faixa.faixa,
        aliquota_nominal=faixa.aliquota_nominal,
        valor_deduzir=faixa.valor_deduzir,
        aliquota_efetiva=aliquota_efetiva,
        receita_bruta_acumulada_12_meses=rbt12,
        receita_bruta_mes=receita_bruta_mes,
        partilha_percentual=partilha_percentual,
        valores_devidos=valores_devidos,
        valor_total_das=sum(valores_devidos.values(), Decimal("0.00")),
        teto_iss_aplicado=teto_iss_aplicado,
        icms_iss_fora_do_das=(faixa.faixa == 6),
        dispositivo_legal_ref=f"{ANEXO_REF[atividade]}, {faixa.faixa}ª Faixa; {FONTE_FORMULA}",
    )


def calcular_mei(receita_bruta_mes: Decimal, ano: int) -> ResultadoSimplesNacional:
    """Anexo XXIII — valores FIXOS em R$, nunca uma alíquota. `receita_bruta_
    mes` não afeta o valor devido (é sempre o mesmo valor fixo do ano); é
    mantida no resultado só para consistência de resposta."""
    valores = _MEI[_chave_periodo_partilha(ano)]
    valores_devidos: dict[str, Decimal] = {"CBS": valores.cbs, "IBS": valores.ibs}
    if valores.icms is not None:
        valores_devidos["ICMS"] = valores.icms
    if valores.iss is not None:
        valores_devidos["ISS"] = valores.iss
    return ResultadoSimplesNacional(
        atividade=Atividade.MEI,
        ano_operacao=ano,
        faixa=None,
        aliquota_nominal=None,
        valor_deduzir=None,
        aliquota_efetiva=None,
        receita_bruta_acumulada_12_meses=None,
        receita_bruta_mes=receita_bruta_mes,
        partilha_percentual={},
        valores_devidos=valores_devidos,
        valor_total_das=sum(valores_devidos.values(), Decimal("0.00")),
        teto_iss_aplicado=False,
        icms_iss_fora_do_das=False,
        dispositivo_legal_ref=ANEXO_REF[Atividade.MEI],
    )


def calcular_simples_nacional(
    atividade: Atividade,
    receita_bruta_acumulada_12_meses: Decimal | None,
    receita_bruta_mes: Decimal,
    ano_operacao: int,
) -> ResultadoSimplesNacional:
    """Ponto de entrada público — despacha para o caminho de cálculo certo
    conforme a `atividade` (Decisão 3 do DESIGN)."""
    if atividade is Atividade.MEI:
        return calcular_mei(receita_bruta_mes, ano_operacao)
    if receita_bruta_acumulada_12_meses is None:
        raise ValueError(
            "receita_bruta_acumulada_12_meses é obrigatória para toda "
            "atividade exceto MEI — sem ela não há como determinar a faixa."
        )
    if atividade in TETOS_ISS_ATIVIDADES:
        return _calcular_percentual_com_teto_iss(
            atividade, receita_bruta_acumulada_12_meses, receita_bruta_mes, ano_operacao
        )
    return _calcular_percentual_simples(
        atividade, receita_bruta_acumulada_12_meses, receita_bruta_mes, ano_operacao
    )
