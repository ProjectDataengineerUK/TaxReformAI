import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from api.auth import verificar_api_key
from api.db import get_db_pool
from api.empresa_skus import parsear_linha_csv
from api.schemas_empresa_skus import (
    LinhaUploadResultado,
    PayloadAtualizarSku,
    PayloadCriarSku,
    RespostaListaSkus,
    RespostaSku,
    RespostaUploadCsv,
)

router = APIRouter(prefix="/v1/tax/skus", tags=["empresa_skus"])

# Mesmo teto citado no plano Business do blueprint (contexto.md) — acima
# disso, volumes maiores ficam para a posição 11 do roadmap
# (FILA_ASSINCRONA_CELERY_REDIS, ainda não construída). Ver Constraint do
# DEFINE_API_EMPRESA_SKUS.md.
TETO_LINHAS_UPLOAD = 10_000

# Achado do security-reviewer antes do /ship: o teto de LINHAS só se aplica
# depois de ler e parsear o arquivo inteiro — um arquivo com poucas linhas
# mas campos enormes (ou uma única linha sem quebra) consumiria memória real
# antes de qualquer checagem. 5 MB é generoso para 10.000 linhas de um
# catálogo de SKUs e barra o caso patológico ANTES do parsing.
TAMANHO_MAXIMO_UPLOAD_BYTES = 5 * 1024 * 1024


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


@router.post("/upload", response_model=RespostaUploadCsv)
def upload_csv(
    arquivo: UploadFile,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaUploadCsv:
    """UPSERT por linha (reenviar a mesma planilha atualiza, não quebra) —
    decisão herdada do /brainstorm, reafirmada no /define. Cada linha válida
    tem sua PRÓPRIA transação (via upsert_sku/sessao_do_tenant): uma falha de
    banco no meio do arquivo não desfaz as linhas já commitadas antes dela
    (Decisão 4 do DESIGN)."""
    _exigir_db_pool(db_pool)

    bruto = arquivo.file.read(TAMANHO_MAXIMO_UPLOAD_BYTES + 1)
    if len(bruto) > TAMANHO_MAXIMO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Arquivo maior que o limite de {TAMANHO_MAXIMO_UPLOAD_BYTES} bytes "
                "desta versão síncrona. Nenhuma linha foi processada."
            ),
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
            detail=(
                f"Arquivo tem {len(linhas)} linhas, acima do limite de "
                f"{TETO_LINHAS_UPLOAD} desta versão síncrona. Nenhuma linha foi processada."
            ),
        )

    from db.repositorio import upsert_sku

    resultados: list[LinhaUploadResultado] = []
    criados = atualizados = erros = 0

    with db_pool.connection() as conexao:
        tenant_uuid = _resolver_tenant_ou_503(conexao, tenant_id)

        for numero, linha in enumerate(linhas, start=1):
            validada = parsear_linha_csv(numero, linha)
            if validada.erro:
                erros += 1
                resultados.append(
                    LinhaUploadResultado(
                        numero_linha=numero, codigo_sku=validada.codigo_sku,
                        situacao="ERRO", motivo=validada.erro,
                    )
                )
                continue

            _sku, foi_criado = upsert_sku(
                conexao, tenant_uuid, validada.codigo_sku, validada.descricao,
                validada.natureza, validada.ncm_code, validada.nbs_code,
            )
            if foi_criado:
                criados += 1
                situacao = "CRIADO"
            else:
                atualizados += 1
                situacao = "ATUALIZADO"
            resultados.append(
                LinhaUploadResultado(numero_linha=numero, codigo_sku=validada.codigo_sku, situacao=situacao)
            )

    return RespostaUploadCsv(
        total_linhas=len(linhas), criados=criados, atualizados=atualizados, erros=erros,
        resultados=resultados,
    )
