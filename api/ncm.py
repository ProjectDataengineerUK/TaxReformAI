"""Canonização e hierarquia de códigos NCM/SH.

Vive aqui, e não dentro de `api/ipi.py` ou `api/reducao_zero.py`, porque as duas
features precisam da MESMA noção de "NCM válido". Duas definições fariam o mesmo
item aparecer resolvido para um tributo e "não reconhecido" para outro na mesma
resposta — bug indiagnosticável pelo cliente (ver Decisão 10).

Este módulo não conhece IPI nem os Anexos de redução a zero: é vocabulário do
domínio (a NCM/SH), não de feature.
"""

import re

_SO_DIGITOS = re.compile(r"\D")

# 2 = capítulo (Capítulo 6, Anexo XV item 4), 4 = posição (09.01), 5/6 =
# subposição (1902.1 / 1006.20), 7 = item (0210.99.1), 8 = subitem (0405.10.00).
# NÃO existe nível de 3 dígitos na NCM/SH: um prefixo de 3 seria transcrição
# errada que nunca casaria com nada — falso negativo mudo. Por isso é uma LISTA
# de comprimentos, não o intervalo 2..8.
# Espelhado pela CHECK `prefixo_comprimento_valido` (migração 007): o que a
# tabela aceita é exatamente o que esta função enxerga. Os dois mudam JUNTOS.
_COMPRIMENTOS_PREFIXO = (2, 4, 5, 6, 7, 8)


def digitos_ncm(bruto: str) -> str | None:
    """8 dígitos canônicos, ou None.

    `"0405.10.00"` e `"04051000"` são o MESMO código em duas grafias —
    canonizar não é fuzzy match, a função é injetiva: nenhum código de 8 dígitos
    vira outro código.

    Qualquer coisa que não tenha exatamente 8 dígitos devolve None. Códigos
    parciais (capítulo/posição) são cabeçalhos de categoria, não a mercadoria —
    e adivinhar qual subitem o cliente quis dizer é justamente o que nenhuma das
    duas features pode fazer.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")
    return digitos if len(digitos) == 8 else None


def prefixos_ncm(codigo: str) -> list[str]:
    """Os 6 prefixos hierárquicos de um código de 8 dígitos.

    É o que transforma "casar por prefixo" numa igualdade exata do lado do SQL
    (`WHERE prefixo = ANY(%s)`), preservando o índice e o mesmo idioma de
    `buscar_ipi_por_ncm` — ver Decisão 2. A alternativa (`LIKE`/`starts_with`
    com a coluna do lado curto) faria seq scan e moveria a definição de "o que
    conta como prefixo" para dentro de uma string SQL, onde a CHECK da migração
    007 não conseguiria espelhá-la.
    """
    return [codigo[:n] for n in _COMPRIMENTOS_PREFIXO]
