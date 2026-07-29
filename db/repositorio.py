"""Acesso a dados com isolamento de tenant garantido pelo banco.

O ponto central deste módulo é `sessao_do_tenant`: toda operação sobre dados de
cliente passa por uma transação que declarou `app.tenant_id`. A policy de RLS
(migração 002) usa essa variável, então esquecer de declará-la resulta em zero
linhas — nunca em linhas de outro tenant.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ParecerAuditado:
    tenant_id: UUID
    prompt_consulta: str
    resposta_parecer_md: str
    contexto_recuperado_ids: list[str]
    payload_calculo: dict[str, Any]
    user_id: UUID | None = None


@dataclass(frozen=True)
class AliquotaIpi:
    """Uma linha de `aliquotas_ipi_tipi` (migração 004).

    `aliquota_percentual` é NULL exatamente quando `nao_tributado` é true — a
    CHECK `aliquota_xor_nao_tributado` torna os dois mutuamente exclusivos no
    banco. "NT" é classificação tributária da própria TIPI, não alíquota 0%.
    """

    ncm_code: str
    aliquota_percentual: Decimal | None
    nao_tributado: bool
    dispositivo_legal_ref: str


def buscar_ipi_por_ncm(conexao, ncms: list[str]) -> dict[str, AliquotaIpi]:
    """Lookup em lote da TIPI. Sem RLS: como `anexos_reducao_zero`, é dado
    legal público, igual para todo tenant.

    UMA query para N códigos — `= ANY(%s)` com uma lista Python é o idioma
    nativo do psycopg para lote e usa `idx_aliquotas_ipi_ncm`. Um laço de
    `buscar_ipi(ncm)` seriam até 100 round-trips ao Cloud SQL por requisição.

    Propaga exceção de propósito: quem decide degradar é `api/ipi.py`, não este
    módulo (ver Decisão 6 do DESIGN). NCM ausente simplesmente não aparece no
    dicionário — o chamador distingue ausência de falha porque falha vira
    exceção, nunca um dicionário vazio.
    """
    if not ncms:
        return {}

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT ncm_code, aliquota_percentual, nao_tributado, dispositivo_legal_ref
            FROM aliquotas_ipi_tipi
            WHERE ncm_code = ANY(%s)
            """,
            (list(ncms),),
        )
        linhas = cur.fetchall()

    return {
        linha[0]: AliquotaIpi(
            ncm_code=linha[0],
            aliquota_percentual=linha[1],
            nao_tributado=linha[2],
            dispositivo_legal_ref=linha[3],
        )
        for linha in linhas
    }


@dataclass(frozen=True)
class PrefixoReducaoZero:
    """Uma linha de `anexos_reducao_zero_ncm` já com o item resolvido pelo JOIN.

    `excecao=True` significa que este prefixo EXCLUI a mercadoria do item — e
    exclui só DESTE item, nunca dos demais. A lei escreve a exclusão dentro do
    item ("9021.3 [...] exceto os produtos classificados nos códigos 9021.39.91
    e 9021.39.99"), então uma exceção global permitiria que uma exclusão do
    Anexo XV anulasse uma inclusão do Anexo XII sem que ninguém tivesse
    escrito isso.

    `anexo_ordem` vem da coluna, não de um mapa romano→número em Python: com
    dois lugares declarando a mesma verdade, o dia em que só um for atualizado
    produz uma ordem de desempate silenciosamente errada (Decisão 3).

    `descricao_contexto` é a descrição do item-pai quando esta linha pertence a
    um sub-item — sem ela, a resposta citaria "Sem mecanismo de propulsão"
    (Anexo XIII, item 2.1) como fundamentação legal de uma cadeira de rodas
    (Decisão 7).
    """

    anexo: str
    anexo_ordem: int
    item: int
    sub_item: int
    prefixo: str
    excecao: bool
    texto_ncm: str
    alinea: str | None
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str


def buscar_reducao_zero_por_prefixo(
    conexao, prefixos: list[str]
) -> list[PrefixoReducaoZero]:
    """Lookup em lote dos 4 Anexos de alíquota zero (I, XII, XIII e XV).

    Sem RLS: dado legal público, igual para todo tenant.

    UMA query para os prefixos de todos os itens do payload. Devolve tanto
    inclusões quanto exceções — uma exceção só é relevante quando ela própria é
    prefixo do código, então ela cai no mesmo `= ANY` e não precisa de segunda
    consulta.

    O `= ANY(%s)` com lista Python é o mesmo idioma de `buscar_ipi_por_ncm`, e é
    o que a Decisão 2 do Anexo I preserva ao expandir o prefixo do lado do
    Python: a coluna fica do lado curto da igualdade, o índice continua valendo
    e nenhum trecho de SQL precisa saber o que conta como prefixo.

    Propaga exceção de propósito: quem decide degradar é `api/reducao_zero.py`
    (mesma divisão da Decisão 6 do DESIGN de IPI_TIPI_MOTOR_CALCULO). Lista
    vazia de retorno significa "nenhum prefixo casou", nunca "falhou".
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT i.anexo, i.anexo_ordem, p.item, p.sub_item, p.prefixo, p.excecao,
                   p.texto_ncm, p.alinea, i.descricao, pai.descricao,
                   i.dispositivo_legal_ref
            FROM anexos_reducao_zero_ncm p
            JOIN anexos_reducao_zero i
              ON i.anexo = p.anexo AND i.item = p.item AND i.sub_item = p.sub_item
            LEFT JOIN anexos_reducao_zero pai
              ON pai.anexo = i.anexo AND pai.item = i.item
             AND pai.sub_item = 0 AND i.sub_item > 0
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoReducaoZero(*linha) for linha in cur.fetchall()]


@contextmanager
def sessao_do_tenant(conexao, tenant_id: UUID):
    """Transação com `app.tenant_id` declarado, para o RLS enxergar o tenant.

    O escopo é a transação (`is_local=true`): a variável não vaza para a próxima
    operação que reusar a mesma conexão de um pool. Sem isso, uma conexão
    devolvida ao pool carregaria o tenant do request anterior — vazamento entre
    clientes difícil de reproduzir e fácil de não notar.
    """
    try:
        with conexao.cursor() as cur:
            # set_config(), não `SET LOCAL app.tenant_id = %s`: SET é comando
            # utilitário do PostgreSQL e NÃO aceita parâmetro vinculado —
            # devolve `syntax error at or near "$1"`. Interpolar o UUID na
            # string seria injeção de SQL num ponto que decide isolamento entre
            # clientes. set_config é função e aceita parâmetro; o terceiro
            # argumento `true` é o is_local, equivalente ao LOCAL do SET.
            cur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
            yield cur
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise


def resolver_tenant(conexao, identificador: str) -> UUID | None:
    """Aceita UUID ou slug.

    A API em produção mapeia `API_KEYS` para strings livres ("taxreformai-dev")
    enquanto o schema exige UUID. Aceitar os dois permite migrar o secret sem
    derrubar o serviço no meio — ver Decisão 2 do DESIGN.
    """
    try:
        return UUID(identificador)
    except (ValueError, AttributeError):
        pass

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT id FROM tenants WHERE slug = %s AND ativo IS TRUE", (identificador,)
        )
        linha = cur.fetchone()
    return linha[0] if linha else None


def registrar_parecer(conexao, parecer: ParecerAuditado) -> UUID:
    """Grava na trilha de auditoria. É o que sustenta "simulação 100%
    auditável" — sem isto nenhuma resposta emitida pode ser reconstituída."""
    with sessao_do_tenant(conexao, parecer.tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO pareceres_audit_log (
                tenant_id, user_id, prompt_consulta,
                contexto_recuperado_ids, payload_calculo_json, resposta_parecer_md
            ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)
            RETURNING id
            """,
            (
                str(parecer.tenant_id),
                str(parecer.user_id) if parecer.user_id else None,
                parecer.prompt_consulta,
                json.dumps(parecer.contexto_recuperado_ids),
                json.dumps(parecer.payload_calculo, default=str),
                parecer.resposta_parecer_md,
            ),
        )
        return cur.fetchone()[0]
