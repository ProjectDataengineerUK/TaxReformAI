"""Canonização e hierarquia de códigos NBS (Nomenclatura Brasileira de Serviços).

Vive separado de `api/ncm.py` porque o vocabulário NÃO é NCM com pontuação
diferente: 9 dígitos (não 8), com um classificador de topo fixo ("1", único
valor observado nos 90 códigos NBS dos Anexos II/III/X/XI) e truncamento
parcial observado numa fronteira que a NCM não tem (1 dígito dentro da
subposição).

Ver Decisão 2 do DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md.
"""

import re

_SO_DIGITOS = re.compile(r"\D")

# 5 = posição (C+PPPP), 6 = posição + 1º dígito da subposição (truncamento
# parcial, ex. "1.2201.1"), 7 = posição + subposição completa, 9 = código
# completo (C+PPPP+SS+II). NUNCA 8: nenhuma evidência de truncamento parcial
# do "item" nos 90 códigos observados — lista fechada, não intervalo, mesma
# razão de `_COMPRIMENTOS_PREFIXO` do NCM (api/ncm.py): um comprimento
# inventado casaria com nada, e um falso negativo mudo é pior que recusar.
_COMPRIMENTOS_PREFIXO_NBS = (5, 6, 7, 9)


def digitos_nbs(bruto: str) -> str | None:
    """9 dígitos canônicos começando em "1", ou None.

    Diferente de `digitos_ncm`, também valida o classificador de topo: a
    Assunção A-002 do DEFINE (todo código observado começa com "1") não está
    confirmada contra a fonte oficial do NBS (`nbs.economia.gov.br`,
    inacessível deste ambiente). Em vez de aceitar qualquer 1º dígito
    silenciosamente, a função recusa o que não bate com o único padrão
    observado — erra para o lado de "não reconhecido", nunca para o lado de
    um match não verificável.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")
    if len(digitos) != 9 or not digitos.startswith("1"):
        return None
    return digitos


def prefixos_nbs(codigo: str) -> list[str]:
    """Os 4 prefixos hierárquicos aceitos de um código NBS de 9 dígitos."""
    return [codigo[:n] for n in _COMPRIMENTOS_PREFIXO_NBS]
