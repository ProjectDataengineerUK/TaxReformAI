"""Tributos do regime VIGENTE — o que as empresas pagam hoje, à parte do IVA
Dual da reforma (CBS/IBS/IS, modelados em `regras_fiscais.py`).

Existe porque a simulação de 2026 sem isso era enganosa: um valor líquido de
R$ 99,00 sobre R$ 100,00 de CBS/IBS lido isoladamente parece o custo da
operação, mas o art. 348 da LCP 214/2025 torna esse valor compensável com o
PIS/COFINS do mesmo período — "compensável com o quê" só faz sentido se o
PIS/COFINS também estiver calculado.

Todas as alíquotas aqui foram lidas no texto oficial do Planalto/LexML/portais
de cada SEFAZ estadual, não de memória — este projeto já teve dois incidentes
por confiar em memória em vez de conferir a fonte (o art. 474 da LCP 214, que
trata de regime específico e quase foi usado como redução geral de ICMS/ISS; o
BGE-M3, que não existe no fastembed). Cada `fonte_legal_*` aponta o artigo
exato.

Escopo deliberadamente PARCIAL — ver `TRIBUTOS_INDISPONIVEIS` abaixo:

- PIS/COFINS: total. Alíquotas federais fixas por regime de apuração.
- ICMS interestadual: total. Fixado pela Resolução do Senado 22/1989 (+
  13/2012 para bens importados) — norma única, federal, pequena.
- ICMS interno: total, para a alíquota GERAL/modal de cada UF (27 estados +
  DF, cada um com seu próprio RICMS/lei — verificado individualmente em
  2026-07-27, não existe agregador federal tipo CONFAZ para isso). NÃO cobre
  alíquotas específicas por mercadoria (cada estado tem centenas de exceções
  por NCM/CEST), e para essas não há hoje fonte única citável.
- ISS: parcial. LC 116/2003 dá um piso (2%, art. 8º-A) e um teto (5%, art.
  8º) federais, cobrindo TODOS os 5.570 municípios — mas não a alíquota exata
  de nenhum município individual, que só a lei municipal define.
- IPI: fora DESTE módulo, mas não indisponível ao produto. A TIPI (Decreto
  11.158/2022) foi ingerida na tabela `aliquotas_ipi_tipi` (migração 004,
  9231 códigos NCM, cada linha com seu `dispositivo_legal_ref`), e o IPI é
  resolvido em `api/ipi.py` a partir do NCM do item. Aqui ele continua
  ausente só porque este módulo é Python puro, sem I/O — a premissa antiga
  ("dado tabular sem alíquota única para citar") foi refutada na prática.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar

# Vazia desde 2026-07-27: o IPI saiu porque ganhou FONTE DE DADO real
# (`aliquotas_ipi_tipi` + `api/ipi.py`), não porque virou estimativa. A
# constante permanece como ponto de extensão para o próximo tributo que seja
# estruturalmente incalculável — é consumida por `api/routers/simulate.py`,
# que soma a ela os tributos que faltaram por conteúdo do payload.
TRIBUTOS_INDISPONIVEIS: tuple[str, ...] = ()


class RegimeApuracao(StrEnum):
    NAO_CUMULATIVO = "NAO_CUMULATIVO"
    CUMULATIVO = "CUMULATIVO"


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


@dataclass(frozen=True)
class RegraIcmsInterno:
    """Alíquota GERAL/modal do ICMS interno (mesma UF de origem e destino).

    Não cobre alíquotas específicas por mercadoria — cada estado tem centenas
    de exceções por NCM/CEST (cesta básica, combustíveis, energia etc.), e não
    existe hoje uma fonte única e citável que as consolide (ao contrário da
    TIPI, que é um decreto federal só e por isso pôde ser ingerida na
    `aliquotas_ipi_tipi`; aqui seriam 27 regulamentos). `aliquota` é só
    o ICMS propriamente dito; `fecp`, quando existe, é um adicional distinto
    (Fundo Estadual de Combate à Pobreza), com base legal própria — mantido
    separado porque juridicamente não é a mesma alíquota do ICMS, mesmo que a
    carga tributária "efetiva" some os dois.
    """

    uf: str
    aliquota: Decimal
    fonte_legal: str
    fecp: Decimal | None = None
    fonte_legal_fecp: str | None = None


# Uma verificação por estado, contra o RICMS/lei de cada um — não existe
# agregador federal (tipo CONFAZ) para a alíquota geral interna, confirmado
# em 2026-07-27. Cada fonte_legal aponta o artigo (ou, quando só a lei
# instituidora foi localizável e não o artigo do RICMS/decreto, a própria lei
# — caso do Maranhão) e a data de vigência quando a alíquota mudou
# recentemente.
_TABELA_ICMS_INTERNO: dict[str, RegraIcmsInterno] = {
    "AC": RegraIcmsInterno(
        uf="AC",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 17, I, do RICMS/AC, com redação dada pela Lei "
        "Complementar 481/2024 — 20%, vigente desde 01/04/2025 (antes, 19%)",
    ),
    "AL": RegraIcmsInterno(
        uf="AL",
        aliquota=Decimal("0.205"),
        fonte_legal="Art. 17 da Lei 5.900/1996, com redação dada pela Lei "
        "9.776/2025 — 20,5%, vigente desde 01/04/2026 (antes, 19%)",
    ),
    "AP": RegraIcmsInterno(
        uf="AP",
        aliquota=Decimal("0.18"),
        fonte_legal="Art. 25, III, 'i', do Anexo I do RICMS/AP — 18%",
    ),
    "AM": RegraIcmsInterno(
        uf="AM",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 12, I, 'b', da Lei Complementar 19/1997, com "
        "redação dada pela Lei Complementar 242/2022 — 20%, vigente desde "
        "29/03/2023 (antes, 18%)",
    ),
    "BA": RegraIcmsInterno(
        uf="BA",
        aliquota=Decimal("0.205"),
        fonte_legal="Art. 15, I, 'a', da Lei 7.014/1996 — 20,5%",
    ),
    "CE": RegraIcmsInterno(
        uf="CE",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 45, I, 'd', do RICMS/CE, com base na Lei "
        "18.305/2023 — 20%, vigente desde 01/01/2024 (antes, 18%)",
    ),
    "DF": RegraIcmsInterno(
        uf="DF",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 46 do RICMS/DF (Decreto 18.955/1997), com base na "
        "Lei 1.254/1996 — 20%, vigente desde 01/01/2024 (antes, 18%)",
    ),
    "ES": RegraIcmsInterno(
        uf="ES",
        aliquota=Decimal("0.17"),
        fonte_legal="Art. 71, I, 'a', do RICMS/ES — 17%",
    ),
    "GO": RegraIcmsInterno(
        uf="GO",
        aliquota=Decimal("0.19"),
        fonte_legal="Art. 20, I, do RCTE/GO (Decreto 4.852/1997), com base "
        "no art. 27, I, da Lei 11.651/1991 — 19%",
    ),
    "MA": RegraIcmsInterno(
        uf="MA",
        aliquota=Decimal("0.23"),
        fonte_legal="Lei 12.426/2024, que alterou o RICMS/MA (Decreto "
        "19.714/2003) — 23%, vigente desde 23/02/2025 (antes, 22%). Artigo "
        "específico do RICMS não localizado em fonte primária — citada a "
        "lei alteradora",
    ),
    "MT": RegraIcmsInterno(
        uf="MT",
        aliquota=Decimal("0.17"),
        fonte_legal="Art. 95, I, 'a', do RICMS/MT — 17%",
    ),
    "MS": RegraIcmsInterno(
        uf="MS",
        aliquota=Decimal("0.17"),
        fonte_legal="Art. 41, III, 'a', do RICMS/MS — 17%",
    ),
    "MG": RegraIcmsInterno(
        uf="MG",
        aliquota=Decimal("0.18"),
        fonte_legal="Art. 42, I, 'e', do RICMS/MG — 18%",
    ),
    "PA": RegraIcmsInterno(
        uf="PA",
        aliquota=Decimal("0.19"),
        fonte_legal="Art. 20, VII, do RICMS/PA — 19%",
    ),
    "PB": RegraIcmsInterno(
        uf="PB",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 13, IV, do RICMS/PB (Decreto 18.930/1997), com "
        "base na Lei 12.788/2023 — 20%, vigente desde 01/01/2024 (antes, "
        "18%)",
    ),
    "PR": RegraIcmsInterno(
        uf="PR",
        aliquota=Decimal("0.195"),
        fonte_legal="Art. 17, V, do RICMS/PR — 19,5%",
    ),
    "PE": RegraIcmsInterno(
        uf="PE",
        aliquota=Decimal("0.205"),
        fonte_legal="Art. 15, VII, da Lei 15.730/2016, com redação dada "
        "pela Lei 18.305/2023 — 20,5%, vigente desde 01/01/2024 (antes, "
        "18%)",
    ),
    "PI": RegraIcmsInterno(
        uf="PI",
        aliquota=Decimal("0.225"),
        fonte_legal="Art. 21, I, 'c', do RICMS/PI, com base na Lei "
        "8.558/2024 — 22,5%, vigente desde 01/04/2025 (antes, 21%)",
    ),
    "RJ": RegraIcmsInterno(
        uf="RJ",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 14, I, da Lei 2.657/1996 — 20%",
        fecp=Decimal("0.02"),
        fonte_legal_fecp="Art. 2º, I a IV, da Lei Complementar Estadual "
        "210/2023 — adicional de 2% ao Fundo Estadual de Combate à Pobreza "
        "e às Desigualdades Sociais (FECP)",
    ),
    "RN": RegraIcmsInterno(
        uf="RN",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 29 do RICMS/RN (2022), com base na Lei "
        "11.999/2024 — 20%, vigente desde 20/03/2025 (antes, 18%)",
    ),
    "RS": RegraIcmsInterno(
        uf="RS",
        aliquota=Decimal("0.17"),
        fonte_legal="Art. 27, X, do RICMS/RS — 17%",
    ),
    "RO": RegraIcmsInterno(
        uf="RO",
        aliquota=Decimal("0.195"),
        fonte_legal="Art. 27, I, 'c', da Lei 688/1996 — 19,5%, vigente "
        "desde 12/01/2024 (antes, 17,5%)",
    ),
    "RR": RegraIcmsInterno(
        uf="RR",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 46, I, 'd', do RICMS/RR, com base na Lei "
        "1.767/2022 — 20%, vigente desde 30/03/2023 (antes, 17%)",
    ),
    "SC": RegraIcmsInterno(
        uf="SC",
        aliquota=Decimal("0.17"),
        fonte_legal="Art. 26, I, do RICMS/SC — 17%",
    ),
    "SP": RegraIcmsInterno(
        uf="SP",
        aliquota=Decimal("0.18"),
        fonte_legal="Art. 52, I, do RICMS/SP (Decreto 45.490/2000) — 18%",
    ),
    "SE": RegraIcmsInterno(
        uf="SE",
        aliquota=Decimal("0.19"),
        fonte_legal="Art. 40, I, do RICMS/SE, com base na Lei 9.176/2023 — "
        "19%, vigente desde 01/04/2023",
        fecp=Decimal("0.01"),
        fonte_legal_fecp="Art. 2º-A da Lei 4.731/2002 — adicional de 1% ao "
        "Fundo Estadual de Combate e Erradicação da Pobreza",
    ),
    "TO": RegraIcmsInterno(
        uf="TO",
        aliquota=Decimal("0.20"),
        fonte_legal="Art. 27, II, da Lei 1.287/2001, com redação dada pela "
        "Lei 4.141/2023 — 20%, vigente desde 01/04/2023 (antes, 18%)",
    ),
}


def icms_interno(uf: str) -> RegraIcmsInterno:
    """Alíquota geral/modal do ICMS interno para a UF informada.

    Só a regra geral — quando a operação tem alíquota específica (cesta
    básica, combustíveis etc.), esta função não se aplica; o chamador decide
    isso fora daqui, o mesmo desenho de `icms_interestadual`.
    """
    uf = uf.upper()
    try:
        return _TABELA_ICMS_INTERNO[uf]
    except KeyError:
        raise ValueError(
            f"UF desconhecida: {uf!r} — esperado um dos 26 estados + DF"
        ) from None


FONTE_ISS_PISO = (
    "Lei Complementar 116/2003, art. 8º-A, caput — piso de 2% (dois por "
    "cento), instituído pela LC 157/2016"
)
FONTE_ISS_TETO = "Lei Complementar 116/2003, art. 8º, II — teto de 5% (cinco por cento)"


@dataclass(frozen=True)
class FaixaIss:
    """Piso e teto federais do ISS — NÃO a alíquota exata de nenhum
    município. A LC 116/2003 limita a faixa em que os 5.570 municípios podem
    legislar, mas a alíquota efetiva de cada um só está na lei municipal
    respectiva, fora do escopo deste motor — são 5.570 normas distintas, sem
    consolidação federal que se possa citar."""

    piso: Decimal
    teto: Decimal
    fonte_legal_piso: str
    fonte_legal_teto: str


def iss_faixa() -> FaixaIss:
    return FaixaIss(
        piso=Decimal("0.02"),
        teto=Decimal("0.05"),
        fonte_legal_piso=FONTE_ISS_PISO,
        fonte_legal_teto=FONTE_ISS_TETO,
    )
