from pydantic import BaseModel


class RecursoStatus(BaseModel):
    recurso: str
    nivel: str
    detalhe: str


class RespostaStatus(BaseModel):
    recursos: list[RecursoStatus]


class CustoPorModeloResposta(BaseModel):
    modelo: str
    tokens_entrada: int
    tokens_saida: int
    custo_usd: float


class CustoInfraPorServicoResposta(BaseModel):
    servico: str
    custo_usd: float


class RespostaCusto(BaseModel):
    periodo_dias: int
    custo_token_total_usd: float
    custo_por_modelo: list[CustoPorModeloResposta]
    custo_infra_total_usd: float
    custo_infra_por_servico: list[CustoInfraPorServicoResposta]
    alertas_limiar: list[str]


class RespostaScorecard(BaseModel):
    mlops: dict
    dataops: dict
    llmops: dict
    seguranca: dict
    finops_achados: list[dict]
