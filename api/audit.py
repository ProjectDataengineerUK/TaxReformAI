"""Grava na trilha de auditoria sem nunca derrubar a resposta ao cliente.

Uma falha ao gravar (banco fora do ar, tenant não cadastrado, timeout) não
pode impedir a entrega de um cálculo tributário correto — mas também não pode
ficar muda: `logger.exception` vai para o stdout do contêiner, que o Cloud Run
encaminha para o Cloud Logging automaticamente. Silêncio total seria pior:
ninguém saberia que a auditoria parou de funcionar até precisar dela.
"""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("api.audit")


def registrar_com_seguranca(
    pool: Any,
    tenant_identificador: str,
    *,
    prompt_consulta: str,
    resposta_parecer_md: str,
    payload_calculo: dict,
    contexto_recuperado_ids: list[str] | None = None,
) -> None:
    if pool is None:
        # Sem DB_INSTANCE_CONNECTION_NAME no ambiente (todo teste, deploys
        # antes do Cloud SQL existir). Não é erro — é o estado esperado até
        # aqui, e já era o comportamento do serviço antes desta feature.
        return

    from db.repositorio import ParecerAuditado, registrar_parecer, resolver_tenant

    try:
        with pool.connection() as conexao:
            tenant_id: UUID | None = resolver_tenant(conexao, tenant_identificador)
            if tenant_id is None:
                logger.warning(
                    "Audit log não gravado: tenant %r não está cadastrado em "
                    "`tenants` (esperado durante a migração do secret API_KEYS "
                    "de slug para UUID).",
                    tenant_identificador,
                )
                return

            registrar_parecer(
                conexao,
                ParecerAuditado(
                    tenant_id=tenant_id,
                    prompt_consulta=prompt_consulta,
                    resposta_parecer_md=resposta_parecer_md,
                    contexto_recuperado_ids=contexto_recuperado_ids or [],
                    payload_calculo=payload_calculo,
                ),
            )
    except Exception:
        logger.exception("Falha ao gravar audit log — resposta ao cliente segue normalmente")
