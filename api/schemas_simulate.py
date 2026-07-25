from decimal import Decimal

from pydantic import BaseModel, Field

from motor_calculo.regime_atual import RegimeApuracao


class ItemSimulacao(BaseModel):
    sku: str
    ncm: str
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)
    uf_origem: str
    uf_destino: str
    # Só afeta o ICMS interestadual (Resolução do Senado 13/2012, 4% em vez de
    # 12%/7%). Default False é a maioria dos casos, não uma estimativa: a
    # alíquota de 4% só se aplica com este sinal explícito.
    bem_importado: bool = False


class PayloadSimulacao(BaseModel):
    tenant_id: str
    ano_operacao: int
    operacao_tipo: str
    itens: list[ItemSimulacao] = Field(min_length=1, max_length=100)
    # Opcional e SEM default de fato: None significa "não informado", não
    # "presume-se X". PIS/COFINS dependem do regime de apuração da empresa
    # (Lucro Real ~ não-cumulativo; Lucro Presumido/Simples ~ cumulativo em
    # regra geral) — advinhar teria a mesma falha que inventar uma alíquota da
    # reforma. Sem este campo, o PIS/COFINS simplesmente não é calculado, e o
    # escopo da resposta diz por quê.
    regime_apuracao: RegimeApuracao | None = None


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


class ItemRegimeVigente(BaseModel):
    """ICMS interestadual é calculado sempre — uf_origem/uf_destino são
    obrigatórios no payload. PIS/COFINS só quando `regime_apuracao` foi
    informado; None aqui significa "não calculado", não "zero"."""

    sku: str
    icms_interestadual_percentual: Decimal
    fonte_legal_icms: str
    pis_percentual: Decimal | None = None
    cofins_percentual: Decimal | None = None
    fonte_legal_pis: str | None = None
    fonte_legal_cofins: str | None = None


class RegimeVigenteResumo(BaseModel):
    regime_apuracao: str | None = None
    total_pis: Decimal | None = None
    total_cofins: Decimal | None = None
    total_icms_interestadual: Decimal
    # Sempre inclui IPI, ICMS_INTERNO, ISS (TRIBUTOS_INDISPONIVEIS); mais
    # PIS/COFINS quando regime_apuracao não foi informado no payload.
    tributos_nao_calculados: list[str]


class RespostaSimulacao(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    resumo_financeiro: ResumoFinanceiro
    itens_detalhados: list[ItemDetalhado]
    escopo: EscopoSimulacao
    compensacao: Compensacao
    regime_vigente: RegimeVigenteResumo
    itens_regime_vigente: list[ItemRegimeVigente]
