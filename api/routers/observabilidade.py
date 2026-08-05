"""3 endpoints do painel de observabilidade — status ao vivo (cache 60s),
custo agregado, e scorecard de maturidade/segurança. Nenhum é tenant-scoped
(Decision 3 do DESIGN_PAINEL_OBSERVABILIDADE.md): dado operacional do
sistema inteiro, não dado de negócio por tenant. `verificar_api_key` só
autentica — o `tenant_id` devolvido nunca é usado além disso aqui, mesmo
padrão já usado por `consultar_piso_aliquota_ibs`."""

import functools
import os
import time
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verificar_api_key
from api.db import get_db_pool
from api.schemas_observabilidade import (
    CustoInfraPorServicoResposta,
    CustoPorModeloResposta,
    RecursoStatus,
    RespostaCusto,
    RespostaScorecard,
    RespostaStatus,
)
from observabilidade.custo import calcular_resumo_custo
from observabilidade.status import calcular_status

router = APIRouter(prefix="/v1/observabilidade", tags=["observabilidade"])

_CACHE_STATUS_SEGUNDOS = int(os.environ.get("OBSERVABILIDADE_STATUS_CACHE_SEGUNDOS", "60"))
_cache_status: dict = {"resposta": None, "expira_em": 0.0}


@router.get("/status", response_model=RespostaStatus)
def consultar_status(
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaStatus:
    agora = time.monotonic()
    if _cache_status["resposta"] is not None and agora < _cache_status["expira_em"]:
        return _cache_status["resposta"]

    if db_pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloud SQL não configurado")

    frontend_url = (os.environ.get("FRONTEND_ORIGINS", "").split(",")[0] or "").strip() or None
    qdrant_url = os.environ.get("QDRANT_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    qdrant_collection = os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria")

    with db_pool.connection() as conexao:
        geral = calcular_status(
            conexao,
            frontend_url=frontend_url,
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
            qdrant_collection=qdrant_collection,
        )

    resposta = RespostaStatus(
        recursos=[
            RecursoStatus(recurso=r.recurso, nivel=r.nivel, detalhe=r.detalhe) for r in geral.recursos
        ]
    )
    _cache_status["resposta"] = resposta
    _cache_status["expira_em"] = agora + _CACHE_STATUS_SEGUNDOS
    return resposta


@router.get("/custo", response_model=RespostaCusto)
def consultar_custo(
    periodo_dias: int = 30,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaCusto:
    if db_pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloud SQL não configurado")

    with db_pool.connection() as conexao:
        resumo = calcular_resumo_custo(conexao, periodo_dias=periodo_dias)

    return RespostaCusto(
        periodo_dias=resumo.periodo_dias,
        custo_token_total_usd=resumo.custo_token_total_usd,
        custo_por_modelo=[
            CustoPorModeloResposta(
                modelo=item.modelo,
                tokens_entrada=item.tokens_entrada,
                tokens_saida=item.tokens_saida,
                custo_usd=item.custo_usd,
            )
            for item in resumo.custo_por_modelo
        ],
        custo_infra_total_usd=resumo.custo_infra_total_usd,
        custo_infra_por_servico=[
            CustoInfraPorServicoResposta(servico=item.servico, custo_usd=item.custo_usd)
            for item in resumo.custo_infra_por_servico
        ],
        alertas_limiar=resumo.alertas_limiar,
    )


@functools.lru_cache
def _carregar_scorecard() -> dict:
    # Decision 5 do DESIGN: lido uma vez por processo — o arquivo vem
    # embutido na imagem (api/Dockerfile copia observabilidade/), só muda
    # com um novo deploy.
    import observabilidade

    caminho = Path(observabilidade.__file__).resolve().parent / "scorecard.yaml"
    with caminho.open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


@router.get("/scorecard", response_model=RespostaScorecard)
def consultar_scorecard(tenant_id: str = Depends(verificar_api_key)) -> RespostaScorecard:
    try:
        dados = _carregar_scorecard()
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"scorecard.yaml ausente ou malformado: {exc}",
        ) from exc
    return RespostaScorecard(**dados)
