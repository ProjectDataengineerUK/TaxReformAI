"""Piso da alíquota própria de Estados/Municípios para o IBS (LCP 214/2025,
art. 371, Anexo XVI) — de 2029 a 2077, o percentual mínimo (em proporção da
alíquota de referência da respectiva esfera federativa) que um ente pode
fixar para sua fatia do IBS.

Vive aqui, não em `tabela_aliquotas.py` (indexado por `FaseTransicao`, um
agrupamento de 4 fases): o Anexo XVI muda TODO ANO dentro do que hoje é uma
única fase (`REGIME_PLENO_2033`, 2033 em diante) — encaixá-lo ali quebraria
`FaseTransicao` em 49 sub-fases por um problema que não pede isso.

NÃO calcula nenhuma alíquota absoluta: o percentual multiplica a "alíquota
de referência da respectiva esfera federativa" (art. 371, §1º), uma
grandeza CALCULADA a partir de execução fiscal real (art. 370) que este
projeto não ingere e não tem como ingerir — mesma classe de limitação já
aceita para ICMS interno/ISS ("não existe agregador federal"). Por isso
`PisoAliquotaIbs` não tem nenhum campo de alíquota absoluta, por desenho:
ver Decisão 3 do DESIGN_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md.
"""

from dataclasses import dataclass
from decimal import Decimal

FONTE_LEGAL = "LCP 214/2025, art. 371, §1º, Anexo XVI"

# 49 entradas, 2029-2077, lidas e conferidas contra DUAS fontes independentes
# (Senado + Câmara dos Deputados) no /define. Chave é o ANO, não a UF/Município
# — o percentual é nacional e uniforme; só a alíquota de referência que ele
# multiplica varia por esfera federativa (e essa não está aqui, ver acima).
_TABELA_PISO: dict[int, Decimal] = {
    2029: Decimal("81.0"), 2030: Decimal("81.0"), 2031: Decimal("81.0"),
    2032: Decimal("81.0"), 2033: Decimal("90.5"), 2034: Decimal("88.6"),
    2035: Decimal("86.7"), 2036: Decimal("84.8"), 2037: Decimal("82.9"),
    2038: Decimal("81.0"), 2039: Decimal("79.1"), 2040: Decimal("77.2"),
    2041: Decimal("75.3"), 2042: Decimal("73.4"), 2043: Decimal("71.5"),
    2044: Decimal("69.6"), 2045: Decimal("67.7"), 2046: Decimal("65.8"),
    2047: Decimal("63.9"), 2048: Decimal("62.0"), 2049: Decimal("60.1"),
    2050: Decimal("58.2"), 2051: Decimal("56.3"), 2052: Decimal("54.4"),
    2053: Decimal("52.5"), 2054: Decimal("50.6"), 2055: Decimal("48.7"),
    2056: Decimal("46.8"), 2057: Decimal("44.9"), 2058: Decimal("43.0"),
    2059: Decimal("41.1"), 2060: Decimal("39.2"), 2061: Decimal("37.3"),
    2062: Decimal("35.4"), 2063: Decimal("33.5"), 2064: Decimal("31.6"),
    2065: Decimal("29.7"), 2066: Decimal("27.8"), 2067: Decimal("25.9"),
    2068: Decimal("24.0"), 2069: Decimal("22.1"), 2070: Decimal("20.2"),
    2071: Decimal("18.3"), 2072: Decimal("16.4"), 2073: Decimal("14.5"),
    2074: Decimal("12.6"), 2075: Decimal("10.7"), 2076: Decimal("8.8"),
    2077: Decimal("6.9"),
}


@dataclass(frozen=True)
class PisoAliquotaIbs:
    ano_operacao: int
    limite_inferior_percentual: Decimal
    dispositivo_legal_ref: str


def piso_aliquota_ibs(ano: int) -> PisoAliquotaIbs | None:
    """None fora de [2029, 2077] — o art. 371 delimita essa janela no caput
    ("De 2029 a 2077"), então fora dela o regime deste piso simplesmente NÃO
    VIGORA (não é "não encontrado": é "não se aplica a este ano")."""
    percentual = _TABELA_PISO.get(ano)
    if percentual is None:
        return None
    return PisoAliquotaIbs(
        ano_operacao=ano,
        limite_inferior_percentual=percentual,
        dispositivo_legal_ref=FONTE_LEGAL,
    )
