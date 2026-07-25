"""Tributos do regime VIGENTE — o que as empresas pagam hoje, à parte do IVA
Dual da reforma (CBS/IBS/IS, modelados em `regras_fiscais.py`).

Existe porque a simulação de 2026 sem isso era enganosa: um valor líquido de
R$ 99,00 sobre R$ 100,00 de CBS/IBS lido isoladamente parece o custo da
operação, mas o art. 348 da LCP 214/2025 torna esse valor compensável com o
PIS/COFINS do mesmo período — "compensável com o quê" só faz sentido se o
PIS/COFINS também estiver calculado.

Todas as alíquotas aqui foram lidas no texto oficial do Planalto/LexML, não de
memória — este projeto já teve dois incidentes por confiar em memória em vez
de conferir a fonte (o art. 474 da LCP 214, que trata de regime específico e
quase foi usado como redução geral de ICMS/ISS; o BGE-M3, que não existe no
fastembed). Cada `fonte_legal_*` aponta o artigo exato.

Escopo deliberadamente PARCIAL — ver `TRIBUTOS_INDISPONIVEIS` abaixo:

- PIS/COFINS: total. Alíquotas federais fixas por regime de apuração.
- ICMS interestadual: total. Fixado pela Resolução do Senado 22/1989 (+
  13/2012 para bens importados) — norma única, federal, pequena.
- IPI: indisponível. A tabela TIPI (decreto) é pública mas tem milhares de
  linhas por NCM — é dado tabular, não alíquota codificável, mesma classe de
  problema que SPED/IBPT (decisão registrada no CLAUDE.md em 2026-07-25).
- ICMS interno e ISS: indisponíveis. Dependem de legislação de 27 estados e
  milhares de municípios, com benefícios fiscais próprios. Não há norma única
  para citar — qualquer alíquota aqui seria estimativa disfarçada de cálculo.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar

TRIBUTOS_INDISPONIVEIS = ("IPI", "ICMS_INTERNO", "ISS")


class RegimeApuracao(StrEnum):
    NAO_CUMULATIVO = "NAO_CUMULATIVO"
    CUMULATIVO = "CUMULATIVO"


class RegimeIndisponivelError(Exception):
    def __init__(self, tributo: str):
        super().__init__(
            f"{tributo} não é calculado por este motor — depende de legislação "
            "estadual/municipal (27 UFs, milhares de municípios) ou de tabela "
            "TIPI por NCM, sem norma federal única para citar. Nenhum cálculo "
            "é retornado para evitar simular com dado estimado."
        )
        self.tributo = tributo


@dataclass(frozen=True)
class RegraPisCofins:
    regime: RegimeApuracao
    aliq_pis: Decimal
    aliq_cofins: Decimal
    fonte_legal_pis: str
    fonte_legal_cofins: str


class TabelaPisCofins:
    """Alíquotas federais de PIS/COFINS por regime de apuração — a mesma
    divisão que o próprio contribuinte declara ao Fisco (Lucro Real ~
    não-cumulativo; Lucro Presumido/Simples ~ cumulativo, em regra geral)."""

    _REGRAS: ClassVar[dict[RegimeApuracao, RegraPisCofins]] = {
        RegimeApuracao.NAO_CUMULATIVO: RegraPisCofins(
            regime=RegimeApuracao.NAO_CUMULATIVO,
            aliq_pis=Decimal("0.0165"),
            aliq_cofins=Decimal("0.076"),
            fonte_legal_pis="Lei 10.637/2002, art. 2º — 1,65% (um inteiro e sessenta "
            "e cinco centésimos por cento)",
            fonte_legal_cofins="Lei 10.833/2003, art. 2º — 7,6% (sete inteiros e seis "
            "décimos por cento)",
        ),
        RegimeApuracao.CUMULATIVO: RegraPisCofins(
            regime=RegimeApuracao.CUMULATIVO,
            aliq_pis=Decimal("0.0065"),
            aliq_cofins=Decimal("0.03"),
            fonte_legal_pis="Lei 9.715/1998, art. 8º, I — 0,65% (zero vírgula "
            "sessenta e cinco por cento)",
            fonte_legal_cofins="Lei 9.718/1998, art. 8º — 3% (elevada de 2% para "
            "3%, redação vigente)",
        ),
    }

    def buscar(self, regime: RegimeApuracao) -> RegraPisCofins:
        return self._REGRAS[regime]


# Regiões conforme a divisão da própria Resolução 22/1989 — note que o
# Espírito Santo entra como DESTINO beneficiado mesmo sendo Sudeste (é como o
# texto original está redigido, não erro de digitação nosso).
_REGIAO_SUL = frozenset({"PR", "SC", "RS"})
_REGIAO_SUDESTE = frozenset({"SP", "RJ", "MG", "ES"})
_REGIAO_NORTE = frozenset({"AC", "AP", "AM", "PA", "RO", "RR", "TO"})
_REGIAO_NORDESTE = frozenset({"AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"})
_REGIAO_CENTRO_OESTE = frozenset({"DF", "GO", "MT", "MS"})
_DESTINOS_ALIQUOTA_REDUZIDA = _REGIAO_NORTE | _REGIAO_NORDESTE | _REGIAO_CENTRO_OESTE | {"ES"}

FONTE_ICMS_GERAL = "Resolução do Senado Federal nº 22/1989, art. 1º, caput — 12%"
FONTE_ICMS_REDUZIDA = (
    "Resolução do Senado Federal nº 22/1989, art. 1º, parágrafo único, II "
    "(a partir de 1990) — 7%, para operações do Sul/Sudeste destinadas ao "
    "Norte/Nordeste/Centro-Oeste/ES"
)
FONTE_ICMS_IMPORTADO = (
    "Resolução do Senado Federal nº 13/2012, art. 1º, caput — 4%, para bens e "
    "mercadorias importados sem industrialização substancial no país ou com "
    "conteúdo de importação superior a 40%"
)


@dataclass(frozen=True)
class RegraIcmsInterestadual:
    aliquota: Decimal
    fonte_legal: str


def icms_interestadual(
    uf_origem: str, uf_destino: str, *, bem_importado: bool = False
) -> RegraIcmsInterestadual:
    """ICMS nas operações INTERESTADUAIS — ICMS interno (mesmo estado) não é
    coberto, ver módulo docstring.

    A prioridade entre as três alíquotas segue a ordem em que as normas se
    sobrepõem: a Resolução 13/2012 (bem importado) é mais específica que a
    22/1989 e prevalece quando aplicável; dentro da 22/1989, a regra reduzida
    (parágrafo único) é exceção à regra geral (caput).
    """
    uf_origem, uf_destino = uf_origem.upper(), uf_destino.upper()

    if bem_importado:
        return RegraIcmsInterestadual(Decimal("0.04"), FONTE_ICMS_IMPORTADO)

    if uf_origem in (_REGIAO_SUL | _REGIAO_SUDESTE) and uf_destino in _DESTINOS_ALIQUOTA_REDUZIDA:
        return RegraIcmsInterestadual(Decimal("0.07"), FONTE_ICMS_REDUZIDA)

    return RegraIcmsInterestadual(Decimal("0.12"), FONTE_ICMS_GERAL)
