"""Resolve a base de incidência do Imposto Seletivo (LCP 214/2025, art. 409,
§§1º-2º, Anexo XVII) — NUNCA calcula valor de IS; `motor_calculo/
tabela_aliquotas.py` permanece a única fonte de `aliq_is`, intocado por este
módulo (Decisão 1 do DESIGN_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md).

Irmão de `api/reducao.py`, mas mais simples: as 6 categorias com código NCM
(veículos, aeronaves/embarcações, fumígenos, bebidas alcoólicas, bebidas
açucaradas, bens minerais) cobrem faixas disjuntas — provado pela migração
013 — então não há desempate ENTRE categorias, só DENTRO de uma (Decisão 2).
A condição de embalagem primária (fumígenos/bebidas alcoólicas, art. 409
§2º) usa o MESMO mecanismo de gating e o MESMO nome de situação
(`CONDICAO_NAO_SATISFEITA`) que `api/reducao_nbs.py` já usa para o Anexo X.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm

logger = logging.getLogger("api.imposto_seletivo")


class SituacaoImpostoSeletivo(StrEnum):
    SUJEITO = "SUJEITO"
    # Item bate com uma categoria que EXIGE condição declaratória (embalagem
    # primária), mas a condição não foi informada ou é falsa.
    CONDICAO_NAO_SATISFEITA = "CONDICAO_NAO_SATISFEITA"
    NAO_SUJEITO = "NAO_SUJEITO"
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaImpostoSeletivo:
    """Espelha `ConsultaReducao` — `disponivel` responde "consegui
    consultar?", nunca "achei alguma coisa?"."""

    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResolucaoImpostoSeletivo:
    situacao: SituacaoImpostoSeletivo
    categoria: str | None = None
    dispositivo_legal_ref: str | None = None
    # Não-nulo só nos incisos III/IV — citado SEMPRE que a categoria exige a
    # condição, informada ou não (mesma disciplina de `dispositivo_legal_
    # comprador` do lado NCM).
    condicao_embalagem_primaria_ref: str | None = None
    # Não-nulo só nos incisos I/II — SEMPRE citado quando a categoria casa,
    # porque a exceção de uso NUNCA é verificada por este projeto.
    excecao_uso_ref: str | None = None

    @property
    def aplicavel(self) -> bool:
        return self.situacao not in (
            SituacaoImpostoSeletivo.CONSULTA_INDISPONIVEL,
            SituacaoImpostoSeletivo.NCM_NAO_RECONHECIDO,
        )


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaImpostoSeletivo:
    """Nunca levanta — mesma disciplina de `api/reducao.py::consultar_com_seguranca`.

    `pool is None` (toda a suíte de testes e qualquer deploy sem Cloud SQL) é
    indisponibilidade, não ausência de dado. Lista vazia com pool presente é
    `disponivel=True`: nenhum item de mercadoria no payload, o que é
    diferente de não CONSEGUIR perguntar.
    """
    if pool is None:
        return ConsultaImpostoSeletivo(disponivel=False)
    if not prefixos:
        return ConsultaImpostoSeletivo(disponivel=True)

    try:
        from db.repositorio import buscar_incidencia_is_por_prefixo

        with pool.connection() as conexao:
            return ConsultaImpostoSeletivo(
                disponivel=True,
                linhas=buscar_incidencia_is_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar a base de incidência do Imposto Seletivo "
            "(Anexo XVII) — a simulação segue sem classificar o item, sem "
            "afetar CBS/IBS/IPI"
        )
        return ConsultaImpostoSeletivo(disponivel=False)


def resolver_item(
    natureza: str,
    ncm: str,
    consulta: ConsultaImpostoSeletivo,
    embalagem_primaria_consumidor_final: bool | None = None,
) -> ResolucaoImpostoSeletivo:
    """Função pura — mesma ordem de guardas de `api/reducao.py::resolver_item`.

    Só itens de MERCADORIA entram nesta trilha: a única categoria de serviço
    do Anexo XVII (concursos de prognósticos e fantasy sport, inciso VII) não
    tem código citável, então nunca haveria o que consultar para um item de
    serviço de qualquer forma.
    """
    if natureza != "MERCADORIA":
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.CONSULTA_INDISPONIVEL)

    # Agrupa por INCISO (categoria) — sem desempate entre categorias
    # (Decisão 2): faixas disjuntas, provado pela migração 013.
    por_inciso: dict[int, list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_inciso[linha.inciso].append(linha)

    if not por_inciso:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_SUJEITO)

    # Só uma categoria deveria ter candidatos (faixas disjuntas, provado pela
    # migração) — se mais de uma aparecer por algum dado inesperado, o menor
    # inciso vence de forma determinística, nunca um resultado aleatório.
    inciso_vencedor = min(por_inciso)
    vencedora = max(por_inciso[inciso_vencedor], key=lambda linha: len(linha.prefixo))

    if vencedora.excecao:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_SUJEITO)

    if (
        vencedora.condicao_embalagem_primaria_ref is not None
        and not embalagem_primaria_consumidor_final
    ):
        return ResolucaoImpostoSeletivo(
            situacao=SituacaoImpostoSeletivo.CONDICAO_NAO_SATISFEITA,
            categoria=vencedora.categoria,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            condicao_embalagem_primaria_ref=vencedora.condicao_embalagem_primaria_ref,
        )

    return ResolucaoImpostoSeletivo(
        situacao=SituacaoImpostoSeletivo.SUJEITO,
        categoria=vencedora.categoria,
        dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
        condicao_embalagem_primaria_ref=vencedora.condicao_embalagem_primaria_ref,
        excecao_uso_ref=vencedora.excecao_uso_ref,
    )
