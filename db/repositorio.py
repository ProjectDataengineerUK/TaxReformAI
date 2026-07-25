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
class RegraTributariaCache:
    ncm_code: str
    ano_vigencia: int
    dispositivo_legal_ref: str
    aliquota_cbs: Decimal | None = None
    aliquota_ibs: Decimal | None = None
    aliquota_is: Decimal | None = None
    fonte_legal_cbs: str | None = None
    fonte_legal_ibs: str | None = None
    fonte_legal_is: str | None = None
    confirmado_em_lei: bool = False
    regime_especial: str = "GERAL"

    def tributos_indisponiveis(self) -> list[str]:
        """Mesma semântica de `RegraFiscal.tributos_indisponiveis()`. NULL aqui
        significa "a lei não fixou", não "ninguém preencheu"."""
        return [
            nome
            for nome, valor in (
                ("CBS", self.aliquota_cbs),
                ("IBS", self.aliquota_ibs),
                ("IS", self.aliquota_is),
            )
            if valor is None
        ]


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


def buscar_regra_cache(
    conexao, ncm_code: str, ano_vigencia: int, regime_especial: str = "GERAL"
) -> RegraTributariaCache | None:
    """Sem RLS: regra tributária é dado legal público, igual para todo tenant."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT ncm_code, ano_vigencia, dispositivo_legal_ref,
                   aliquota_cbs, aliquota_ibs, aliquota_is,
                   fonte_legal_cbs, fonte_legal_ibs, fonte_legal_is,
                   confirmado_em_lei, regime_especial
            FROM regras_tributarias_cache
            WHERE ncm_code = %s AND ano_vigencia = %s AND regime_especial = %s
            """,
            (ncm_code, ano_vigencia, regime_especial),
        )
        linha = cur.fetchone()

    if linha is None:
        return None
    return RegraTributariaCache(
        ncm_code=linha[0],
        ano_vigencia=linha[1],
        dispositivo_legal_ref=linha[2],
        aliquota_cbs=linha[3],
        aliquota_ibs=linha[4],
        aliquota_is=linha[5],
        fonte_legal_cbs=linha[6],
        fonte_legal_ibs=linha[7],
        fonte_legal_is=linha[8],
        confirmado_em_lei=linha[9],
        regime_especial=linha[10],
    )
