import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from api.auth import verificar_api_key
from api.db import get_db_pool
from api.schemas_empresa_skus import (
    PayloadAtualizarSku,
    PayloadCriarSku,
    RespostaJobCriado,
    RespostaJobStatus,
    RespostaListaSkus,
    RespostaSku,
    RespostaUploadCsv,
)

router = APIRouter(prefix="/v1/tax/skus", tags=["empresa_skus"])

# FILA_ASSINCRONA_CELERY_REDIS: teto revisado para cima (era 10.000/5MB na
# versão síncrona) — upload agora sempre assíncrono, sustentando a persona de
# 50.000+ SKUs do blueprint (contexto.md) com folga real, não no limite exato.
TETO_LINHAS_UPLOAD = 100_000

# Achado do security-reviewer antes do /ship de API_EMPRESA_SKUS, ainda válido
# aqui: o teto de LINHAS só se aplica depois de ler e parsear o arquivo
# inteiro — um arquivo com poucas linhas mas campos enormes consumiria
# memória real antes de qualquer checagem. 20 MB é generoso para 100.000
# linhas de um catálogo de SKUs e barra o caso patológico ANTES do parsing.
TAMANHO_MAXIMO_UPLOAD_BYTES = 20 * 1024 * 1024


def _resolver_tenant_ou_503(conexao, tenant_identificador: str):
    from db.repositorio import resolver_tenant

    tenant_id = resolver_tenant(conexao, tenant_identificador)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant não resolvido — cadastro pendente de sincronização.",
        )
    return tenant_id


def _exigir_db_pool(db_pool):
    if db_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catálogo de SKUs indisponível — Cloud SQL não configurado neste ambiente.",
        )


def _para_resposta(sku) -> RespostaSku:
    return RespostaSku(
        id=str(sku.id),
        codigo_sku=sku.codigo_sku,
        descricao=sku.descricao,
        natureza=sku.natureza,
        ncm_code=sku.ncm_code,
        nbs_code=sku.nbs_code,
        created_at=sku.created_at,
    )


@router.post("", response_model=RespostaSku, status_code=status.HTTP_201_CREATED)
def criar(
    payload: PayloadCriarSku,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSku:
    _exigir_db_pool(db_pool)
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id do payload não corresponde à credencial autenticada",
        )

    from db.repositorio import criar_sku

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        try:
            sku = criar_sku(
                conexao, tenant_uuid, payload.codigo_sku, payload.descricao,
                payload.natureza.value, payload.ncm_code, payload.nbs_code,
            )
        except Exception as exc:
            # "23505" = unique_violation no padrão SQLSTATE do Postgres — checar
            # o atributo em vez de importar psycopg.errors.UniqueViolation evita
            # uma dependência rígida do driver só para tipar uma exceção (e o
            # SQLSTATE é garantido pelo protocolo, não uma peculiaridade do
            # psycopg). Qualquer OUTRA exceção sobe intocada.
            if getattr(exc, "sqlstate", None) != "23505":
                raise
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"codigo_sku {payload.codigo_sku!r} já cadastrado para este tenant.",
            ) from exc

    return _para_resposta(sku)


@router.get("", response_model=RespostaListaSkus)
def listar(
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=500),
) -> RespostaListaSkus:
    _exigir_db_pool(db_pool)

    from db.repositorio import listar_skus

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        itens, total = listar_skus(conexao, tenant_uuid, pagina, tamanho_pagina)

    return RespostaListaSkus(
        itens=[_para_resposta(s) for s in itens], total=total, pagina=pagina, tamanho_pagina=tamanho_pagina
    )


@router.get("/{codigo_sku}", response_model=RespostaSku)
def consultar(
    codigo_sku: str,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSku:
    _exigir_db_pool(db_pool)

    from db.repositorio import buscar_sku

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        sku = buscar_sku(conexao, tenant_uuid, codigo_sku)

    # RLS já garante que um SKU de outro tenant nunca aparece na consulta —
    # "não encontrado" e "pertence a outro tenant" são indistinguíveis por
    # desenho, nunca 403 (não confirma nem nega existência cross-tenant).
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU não encontrado")

    return _para_resposta(sku)


@router.patch("/{codigo_sku}", response_model=RespostaSku)
def atualizar(
    codigo_sku: str,
    payload: PayloadAtualizarSku,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSku:
    _exigir_db_pool(db_pool)

    from api.empresa_skus import validar_exclusividade
    from db.repositorio import atualizar_sku, buscar_sku

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        existente = buscar_sku(conexao, tenant_uuid, codigo_sku)
        if existente is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU não encontrado")

        descricao = payload.descricao if payload.descricao is not None else existente.descricao
        if payload.natureza is not None:
            # Trocar de natureza invalida o código da natureza ANTERIOR — não
            # faz sentido herdar um ncm_code ao virar SERVICO, nem um
            # nbs_code ao virar MERCADORIA. O cliente PRECISA enviar o
            # código novo junto da troca; se esquecer, a validação abaixo
            # falha com mensagem clara, em vez de herdar um código stale.
            natureza = payload.natureza.value
            ncm_code = payload.ncm_code
            nbs_code = payload.nbs_code
        else:
            natureza = existente.natureza
            ncm_code = payload.ncm_code if payload.ncm_code is not None else existente.ncm_code
            nbs_code = payload.nbs_code if payload.nbs_code is not None else existente.nbs_code

        erro = validar_exclusividade(natureza, ncm_code, nbs_code)
        if erro:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=erro)

        sku = atualizar_sku(conexao, tenant_uuid, codigo_sku, descricao, natureza, ncm_code, nbs_code)

    return _para_resposta(sku)


@router.delete("/{codigo_sku}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    codigo_sku: str,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> None:
    _exigir_db_pool(db_pool)

    from db.repositorio import excluir_sku

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        apagado = excluir_sku(conexao, tenant_uuid, codigo_sku)

    if not apagado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU não encontrado")


@router.post("/upload", response_model=RespostaJobCriado, status_code=status.HTTP_202_ACCEPTED)
def upload_csv(
    arquivo: UploadFile,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaJobCriado:
    """FILA_ASSINCRONA_CELERY_REDIS: SEMPRE assíncrono, um só caminho de
    código (Decisão do /brainstorm) — nunca processa a planilha na mesma
    requisição, mesmo para arquivos pequenos. UPSERT por linha continua
    valendo (herdado de API_EMPRESA_SKUS), só que agora dentro da task."""
    _exigir_db_pool(db_pool)

    bruto = arquivo.file.read(TAMANHO_MAXIMO_UPLOAD_BYTES + 1)
    if len(bruto) > TAMANHO_MAXIMO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Arquivo maior que o limite de {TAMANHO_MAXIMO_UPLOAD_BYTES} bytes. Nenhuma linha foi processada.",
        )
    try:
        conteudo = bruto.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Arquivo não está em UTF-8 (com ou sem BOM): {exc}",
        ) from exc

    leitor = csv.DictReader(io.StringIO(conteudo))
    linhas = list(leitor)

    if len(linhas) > TETO_LINHAS_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Arquivo tem {len(linhas)} linhas, acima do limite de {TETO_LINHAS_UPLOAD}. Nenhuma linha foi processada.",
        )

    from api.staging_gcs import enviar_para_staging
    from api.tasks_cloud import criar_task_processamento
    from db.repositorio import criar_job_upload

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        gcs_uri = enviar_para_staging(str(tenant_uuid), bruto)
        job = criar_job_upload(conexao, tenant_uuid, gcs_uri)

    criar_task_processamento(str(job.id), str(tenant_uuid))

    return RespostaJobCriado(job_id=str(job.id))


@router.get("/upload/{job_id}", response_model=RespostaJobStatus)
def consultar_job_upload(
    job_id: str,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaJobStatus:
    """RLS garante que um `job_id` de outro tenant nunca é visível aqui —
    mesma disciplina de `consultar` (SKU individual). `job_id` malformado
    também vira 404 — nunca 500 nem 422 que confirme/negue formato."""
    _exigir_db_pool(db_pool)

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de upload não encontrado") from None

    from db.repositorio import buscar_job_upload

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)
        job = buscar_job_upload(conexao, tenant_uuid, job_uuid)

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de upload não encontrado")

    resultado = RespostaUploadCsv(**job.resultado_json) if job.resultado_json else None
    return RespostaJobStatus(job_id=str(job.id), status=job.status, resultado=resultado)
