"""Endpoint interno de processamento — só o Cloud Tasks deve conseguir
chamar esta rota (FILA_ASSINCRONA_CELERY_REDIS, Decisão 1 do DESIGN).

Vive num router SEPARADO de `empresa_skus.py` (mesmo prefixo) porque é
maquinário interno, não uma rota CRUD pública — nunca documentado como parte
da API pública, mesmo estando no mesmo path prefix."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from api.db import get_db_pool
from api.tasks_cloud import verificar_token_oidc

router = APIRouter(prefix="/v1/tax/skus", tags=["skus_tasks_interno"])


class _PayloadTarefa(BaseModel):
    job_id: str
    tenant_id: str


@router.post("/upload/processar-tarefa", include_in_schema=False, status_code=status.HTTP_204_NO_CONTENT)
def processar_tarefa(
    payload: _PayloadTarefa,
    authorization: str | None = Header(default=None),
    db_pool=Depends(get_db_pool),
) -> None:
    if not verificar_token_oidc(authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token OIDC ausente ou inválido")
    if db_pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloud SQL não configurado")

    tenant_uuid = uuid.UUID(payload.tenant_id)
    job_uuid = uuid.UUID(payload.job_id)

    from api.empresa_skus import processar_linhas_upload
    from api.staging_gcs import baixar_do_staging
    from db.repositorio import atualizar_job_upload, buscar_job_upload

    with db_pool.connection() as conexao:
        job = buscar_job_upload(conexao, tenant_uuid, job_uuid)
        if job is None:
            # Job não encontrado sob o tenant informado — nada a fazer, mas
            # não é erro do Cloud Tasks (retry não ajudaria). 204 evita retry.
            return

        atualizar_job_upload(conexao, tenant_uuid, job_uuid, status="PROCESSANDO")

        try:
            bruto = baixar_do_staging(job.gcs_uri_arquivo)
            conteudo = bruto.decode("utf-8-sig")
            linhas = list(csv.DictReader(io.StringIO(conteudo)))
            resultado = processar_linhas_upload(conexao, tenant_uuid, linhas)
            atualizar_job_upload(
                conexao, tenant_uuid, job_uuid, status="CONCLUIDO", resultado_json=resultado.to_dict()
            )
        except Exception as exc:
            atualizar_job_upload(
                conexao, tenant_uuid, job_uuid, status="ERRO", resultado_json={"erro": str(exc)}
            )
            raise
