"""Resolve os Anexos de redução de 60% de CBS/IBS por NBS (Nomenclatura
Brasileira de Serviços) da LCP 214/2025: II (art. 129, Educação), III (art.
130, Saúde), X (art. 139, produções artísticas/culturais/audiovisuais — ainda
sem itens semeados, ver `db/migrations/011_anexos_reducao_percentual_nbs.sql`)
e XI (art. 142, soberania e segurança nacional/cibernética).

Irmão de `api/reducao.py`, mas com um mecanismo de condição estruturalmente
diferente (Decisão 3 do DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md): lá (Anexos
IV/V/VI), a condição de comprador faz a alíquota IR A ZERO a partir de um
PADRÃO de 60% (upgrade). Aqui, não existe padrão nenhum para os Anexos X e
XI — a alíquota GERAL da fase é o default, e 60% só nasce quando uma condição
declaratória (nacionalidade de conteúdo, ou comprador OU vendedor
qualificado) é satisfeita (gating). É por isso que existe uma situação nova,
`CONDICAO_NAO_SATISFEITA`, sem equivalente do lado NCM: tratá-la como
`APLICADA` com percentual zero contaminaria `ReducaoResumo.anexos_aplicados`
e `itens_com_reducao_aplicada` com itens que não receberam benefício algum.

Vocabulário SEPARADO do NCM em toda a cadeia (tabela, consulta, canonização)
— nunca cominglados (Achado crítico 4 do /define): um prefixo NBS truncado de
5 dígitos tem o MESMO comprimento que um prefixo NCM válido de 5 dígitos.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from api.nbs import digitos_nbs

logger = logging.getLogger("api.reducao_nbs")

SESSENTA_POR_CENTO = Decimal("0.6000")


class SituacaoReducaoNbs(StrEnum):
    APLICADA = "APLICADA"
    # Item bate com um Anexo/item NBS que EXIGE condição declaratória
    # (nacionalidade de conteúdo, ou comprador/vendedor qualificado), mas a
    # condição não foi informada ou é falsa — alíquota GERAL da fase se
    # aplica, e a resposta cita o que destravaria o benefício.
    CONDICAO_NAO_SATISFEITA = "CONDICAO_NAO_SATISFEITA"
    FORA_DO_ANEXO = "FORA_DO_ANEXO"
    NBS_NAO_RECONHECIDO = "NBS_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == MERCADORIA, ou nbs ausente


@dataclass(frozen=True)
class ConsultaReducaoNbs:
    """Espelha `ConsultaReducao` (NCM) — `disponivel` responde "consegui
    consultar?", nunca "achei alguma coisa?"."""

    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaReducaoNbs:
    """Nunca levanta — mesma disciplina de `api/reducao.py::consultar_com_seguranca`.

    `pool is None` (toda a suíte de testes e qualquer deploy sem Cloud SQL) é
    indisponibilidade, não ausência de dado. Lista vazia com pool presente é
    `disponivel=True`: nenhum item de serviço no payload tinha `nbs`
    preenchido, o que é diferente de não CONSEGUIR perguntar.
    """
    if pool is None:
        return ConsultaReducaoNbs(disponivel=False)
    if not prefixos:
        return ConsultaReducaoNbs(disponivel=True)

    try:
        from db.repositorio import buscar_reducao_nbs_por_prefixo

        with pool.connection() as conexao:
            return ConsultaReducaoNbs(
                disponivel=True,
                linhas=buscar_reducao_nbs_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar os Anexos de redução por NBS (II, III, X e "
            "XI) — a simulação segue com a alíquota geral da fase, declarado "
            "na resposta"
        )
        return ConsultaReducaoNbs(disponivel=False)


def formatar_item(item: int, sub_item: int) -> str:
    """Grafia canônica: "1", "1.1" — mesma convenção de `api/reducao.py::formatar_item`."""
    return f"{item}.{sub_item}" if sub_item else str(item)


@dataclass(frozen=True)
class ResolucaoReducaoNbs:
    situacao: SituacaoReducaoNbs
    anexo: str | None = None
    anexo_ordem: int | None = None
    item: str | None = None
    percentual_reducao: Decimal | None = None
    dispositivo_legal_ref: str | None = None
    # Preenchido sempre que a linha vencedora TEM alguma condição (satisfeita
    # ou não) — nunca só quando falta, para o auditor ver a fundamentação
    # inteira mesmo no caso feliz (mesma disciplina de
    # `dispositivo_legal_comprador` do lado NCM).
    condicao_pendente_ref: str | None = None
    # True só quando a condição existe E não foi satisfeita — espelha
    # `zero_por_comprador_disponivel`, com a polaridade invertida: aqui
    # "disponível" significa "poderia ter ganhado 60% e não ganhou".
    reducao_condicionada_disponivel: bool = False
    descricao: str | None = None
    descricao_contexto: str | None = None
    texto_nbs: str | None = None
    itens_correspondentes: tuple[tuple[str, str], ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoReducaoNbs.APLICADA

    @property
    def avaliada(self) -> bool:
        """Mesma disciplina de `ResolucaoReducao.avaliada` (NCM): só
        CONSULTA_INDISPONIVEL e NBS_NAO_RECONHECIDO significam "não sei"."""
        return self.situacao not in (
            SituacaoReducaoNbs.CONSULTA_INDISPONIVEL,
            SituacaoReducaoNbs.NBS_NAO_RECONHECIDO,
        )


def _condicao_satisfeita(
    linha: Any,
    comprador_tipo: str | None,
    conteudo_nacional_majoritario: bool | None,
    vendedor_capital_brasileiro_qualificado: bool | None,
) -> bool:
    """Nenhuma condição na linha → sempre satisfeita (Anexos II/III inteiros).

    Ver Decisão 4 do DESIGN — comprador OU vendedor, nunca os dois exigidos
    ao mesmo tempo. `ENTIDADE_CEBAS_SUS` NUNCA satisfaz o eixo comprador
    aqui: só `ORGAO_PUBLICO` tem base no art. 142, I (AT-012) — diferente de
    IV/V/VI, onde os dois tipos zeram a alíquota.
    """
    if linha.condicao_nacionalidade_ref is not None:
        return conteudo_nacional_majoritario is True

    tem_condicao_xi = (
        linha.condicao_comprador_ref is not None or linha.condicao_vendedor_ref is not None
    )
    if tem_condicao_xi:
        comprador_ok = (
            linha.condicao_comprador_ref is not None and comprador_tipo == "ORGAO_PUBLICO"
        )
        vendedor_ok = (
            linha.condicao_vendedor_ref is not None
            and vendedor_capital_brasileiro_qualificado is True
        )
        return comprador_ok or vendedor_ok

    return True


def _condicao_ref(linha: Any) -> str | None:
    return linha.condicao_nacionalidade_ref or linha.condicao_comprador_ref or linha.condicao_vendedor_ref


def resolver_item_nbs(
    natureza: str,
    nbs: str | None,
    consulta: ConsultaReducaoNbs,
    comprador_tipo: str | None = None,
    conteudo_nacional_majoritario: bool | None = None,
    vendedor_capital_brasileiro_qualificado: bool | None = None,
) -> ResolucaoReducaoNbs:
    """Função pura — mesma disciplina de `api/reducao.py::resolver_item`.

    Só itens de SERVIÇO com `nbs` preenchido entram nesta trilha: um item de
    MERCADORIA nunca a alcança, mesmo que carregue um `nbs` por engano — os
    Anexos II/III/X/XI só valem para serviços (AT-005, AT-013 tratam a
    minoria NCM desses Anexos, que fica inteiramente do lado da trilha NCM
    já shipada, sem nenhuma interferência deste módulo).
    """
    if natureza != "SERVICO" or not nbs:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.NAO_APLICAVEL)

    codigo = digitos_nbs(nbs)
    if codigo is None:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.NBS_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.CONSULTA_INDISPONIVEL)

    por_item: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_item[(linha.anexo, linha.item, linha.sub_item)].append(linha)

    if not por_item:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.FORA_DO_ANEXO)

    # Uma linha por item é o caso comum, mas o agrupamento tolera mais de uma
    # (ex. um item citando duas faixas de prefixo) elegendo a mais específica
    # dentro do próprio item antes do desempate entre itens diferentes.
    candidatas = [max(linhas, key=lambda linha: len(linha.prefixo)) for linhas in por_item.values()]
    vencedora = max(
        candidatas,
        key=lambda linha: (len(linha.prefixo), -linha.anexo_ordem, -linha.item, -linha.sub_item),
    )

    satisfeita = _condicao_satisfeita(
        vencedora,
        comprador_tipo,
        conteudo_nacional_majoritario,
        vendedor_capital_brasileiro_qualificado,
    )
    condicao_ref = _condicao_ref(vencedora)

    itens_correspondentes = tuple(
        (linha.anexo, formatar_item(linha.item, linha.sub_item))
        for linha in sorted(candidatas, key=lambda linha: (linha.anexo_ordem, linha.item, linha.sub_item))
    )

    return ResolucaoReducaoNbs(
        situacao=(
            SituacaoReducaoNbs.APLICADA if satisfeita else SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA
        ),
        anexo=vencedora.anexo,
        anexo_ordem=vencedora.anexo_ordem,
        item=formatar_item(vencedora.item, vencedora.sub_item),
        percentual_reducao=SESSENTA_POR_CENTO if satisfeita else None,
        dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
        condicao_pendente_ref=condicao_ref,
        reducao_condicionada_disponivel=condicao_ref is not None and not satisfeita,
        descricao=vencedora.descricao,
        descricao_contexto=vencedora.descricao_contexto,
        texto_nbs=vencedora.texto_nbs,
        itens_correspondentes=itens_correspondentes,
    )
