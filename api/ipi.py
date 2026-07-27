"""Resolve IPI por NCM sem nunca derrubar a simulação.

Gêmeo de leitura de `api/audit.py`: mesma garantia de não propagação, mesma
razão. A diferença crítica é que aqui a degradação é DECLARADA na resposta —
o audit log falha em silêncio porque o cliente não o vê; o IPI, não. Cada
situação tem nome próprio (`SituacaoIpi`), então o ERP distingue "este NCM não
existe na TIPI" de "não consegui consultar" e sabe se vale reprocessar.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

logger = logging.getLogger("api.ipi")

_SO_DIGITOS = re.compile(r"\D")


class SituacaoIpi(StrEnum):
    CALCULADO = "CALCULADO"
    NAO_TRIBUTADO = "NAO_TRIBUTADO"  # "NT" na TIPI — NÃO é alíquota 0%
    NCM_NAO_ENCONTRADO = "NCM_NAO_ENCONTRADO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


def normalizar_ncm(bruto: str) -> str | None:
    """`"22030000"` e `"2203.00.00"` são o MESMO código em duas grafias — a
    tabela guarda o pontuado (formato do PDF oficial), ERPs e o próprio smoke
    test do deploy mandam só dígitos. Canonizar não é fuzzy match: a função é
    injetiva, nenhum código de 8 dígitos vira outro código (ver Decisão 4).

    Qualquer coisa que não tenha exatamente 8 dígitos devolve None — códigos
    parciais (capítulo/posição) são cabeçalhos de categoria sem alíquota
    própria, e adivinhar por prefixo é justamente o que o DEFINE proíbe.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")
    if len(digitos) != 8:
        return None
    return f"{digitos[:4]}.{digitos[4:6]}.{digitos[6:8]}"


@dataclass(frozen=True)
class ConsultaIpi:
    """`disponivel` responde "consegui consultar?", nunca "achei alguma coisa?".
    Um lote em que nenhum NCM existe na TIPI é `disponivel=True` com `por_ncm`
    vazio — situação diferente do banco fora do ar."""

    disponivel: bool
    por_ncm: dict[str, Any] = field(default_factory=dict)


def consultar_ipi_com_seguranca(pool: Any, ncms: list[str]) -> ConsultaIpi:
    """`disponivel=False` significa "não consegui consultar", nunca "não existe"
    — apagar essa diferença devolvendo `{}` seria o erro que a Decisão 6 evita.

    `pool is None` (todo teste, e qualquer deploy antes do Cloud SQL) cai no
    mesmo caminho: é indisponibilidade, não ausência de dado. Import tardio de
    `db.repositorio` pelo mesmo motivo de `api/audit.py`: `api.main` precisa
    importar sem `psycopg` instalado.

    Lista vazia com pool presente é `disponivel=True`: não há NADA a perguntar,
    o que é diferente de não CONSEGUIR perguntar. Tratá-la como indisponível
    faria um payload cujos NCMs são todos irreconhecíveis (ex.: só códigos de
    posição) reportar CONSULTA_INDISPONIVEL — acusando o banco de um problema
    que está no payload, e mandando o cliente reprocessar em vão. Nenhuma
    conexão é aberta nos dois casos.
    """
    if pool is None:
        return ConsultaIpi(disponivel=False)

    if not ncms:
        return ConsultaIpi(disponivel=True)

    try:
        from db.repositorio import buscar_ipi_por_ncm

        with pool.connection() as conexao:
            return ConsultaIpi(disponivel=True, por_ncm=buscar_ipi_por_ncm(conexao, ncms))
    except Exception:
        logger.exception(
            "Falha ao consultar IPI/TIPI — a simulação segue sem IPI, declarado na resposta"
        )
        return ConsultaIpi(disponivel=False)


@dataclass(frozen=True)
class ResolucaoIpi:
    situacao: SituacaoIpi
    valor: Decimal = Decimal(0)  # só somável quando `resolvido`
    percentual: Decimal | None = None  # em pontos percentuais, ex. Decimal("3.250")
    fonte_legal: str | None = None

    @property
    def resolvido(self) -> bool:
        """NT conta como resolvido: sabemos a resposta jurídica (não tributado),
        ela só não vira valor."""
        return self.situacao in (SituacaoIpi.CALCULADO, SituacaoIpi.NAO_TRIBUTADO)


def resolver_item(
    natureza: str, ncm: str, valor_base: Decimal, consulta: ConsultaIpi
) -> ResolucaoIpi:
    """Função pura — os cenários AT-001..AT-003 são testáveis sem banco e sem
    HTTP.

    A ordem das guardas importa e é deliberada:

    1. Serviço nunca paga IPI — nem chega a perguntar se a consulta funcionou.
    2. NCM que não canoniza para 8 dígitos é NCM_NAO_ENCONTRADO mesmo com o
       banco fora do ar: é uma propriedade do código informado, não do banco.
       Nenhuma TIPI conteria "2203" (posição, cabeçalho de categoria), então
       CONSULTA_INDISPONIVEL aqui mandaria o cliente reprocessar algo que
       jamais mudaria de resposta.
    3. Só então a disponibilidade da consulta importa.
    """
    if natureza == "SERVICO":
        return ResolucaoIpi(SituacaoIpi.NAO_APLICAVEL)

    codigo = normalizar_ncm(ncm)
    if codigo is None:
        return ResolucaoIpi(SituacaoIpi.NCM_NAO_ENCONTRADO)

    if not consulta.disponivel:
        return ResolucaoIpi(SituacaoIpi.CONSULTA_INDISPONIVEL)

    linha = consulta.por_ncm.get(codigo)
    if linha is None:
        return ResolucaoIpi(SituacaoIpi.NCM_NAO_ENCONTRADO)

    if linha.nao_tributado:
        return ResolucaoIpi(SituacaoIpi.NAO_TRIBUTADO, fonte_legal=linha.dispositivo_legal_ref)

    # Mesma disciplina de arredondamento do engine e de PIS/COFINS/ICMS no
    # router: ROUND_HALF_UP em centavos. A tabela guarda fração (0.03250),
    # a resposta expõe pontos percentuais (3.250) — convenção de `regime_atual`.
    return ResolucaoIpi(
        situacao=SituacaoIpi.CALCULADO,
        valor=(valor_base * linha.aliquota_percentual).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        percentual=linha.aliquota_percentual * 100,
        fonte_legal=linha.dispositivo_legal_ref,
    )
