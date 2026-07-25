from decimal import Decimal

from pydantic import BaseModel, Field


class ItemSimulacao(BaseModel):
    sku: str
    ncm: str
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)
    uf_origem: str
    uf_destino: str


class PayloadSimulacao(BaseModel):
    tenant_id: str
    ano_operacao: int
    operacao_tipo: str
    itens: list[ItemSimulacao] = Field(min_length=1, max_length=100)


class AliquotasAplicadas(BaseModel):
    cbs_percentual: Decimal
    ibs_percentual: Decimal
    is_percentual: Decimal


class ItemDetalhado(BaseModel):
    sku: str
    ncm: str
    aliquotas_aplicadas: AliquotasAplicadas
    fundamentacao_legal: str


class ResumoFinanceiro(BaseModel):
    valor_bruto_total: Decimal
    total_cbs: Decimal
    total_ibs: Decimal
    total_is: Decimal
    valor_liquido_projetado_split_payment: Decimal


class EscopoSimulacao(BaseModel):
    """Diz o que a simulação inclui e o que NÃO inclui.

    Sem isto a resposta engana por omissão. Durante a transição (2026-2033) as
    empresas continuam devendo PIS, COFINS, IPI, ICMS e ISS integralmente, e
    este motor calcula apenas os tributos novos. Um `valor_liquido` de 99,00
    sobre 100,00 lido por um departamento fiscal parece a carga da operação, e
    não é — é a projeção do IVA Dual isolado.
    """

    tributos_incluidos: list[str]
    tributos_nao_incluidos: list[str]
    advertencia: str


class Compensacao(BaseModel):
    """Em 2026 o recolhido de CBS/IBS é compensável, o que zera o custo efetivo
    para quem tem débitos suficientes. Omitir isso faz a simulação superestimar
    o impacto no caixa em 100% do valor exibido."""

    aplicavel: bool
    fonte_legal: str | None = None


class RespostaSimulacao(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    resumo_financeiro: ResumoFinanceiro
    itens_detalhados: list[ItemDetalhado]
    escopo: EscopoSimulacao
    compensacao: Compensacao
