from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from api.ipi import SituacaoIpi
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
    # Decide ICMS x ISS — bases mutuamente exclusivas no direito brasileiro.
    # Default MERCADORIA preserva o comportamento de todo payload existente
    # antes deste campo existir (só ICMS era calculado). `ncm` continua
    # obrigatório mesmo para SERVICO porque não é usado em nenhum cálculo
    # (só carregado para exibição em `ItemDetalhado`) — não há conflito
    # semântico em deixá-lo como está.
    natureza: Literal["MERCADORIA", "SERVICO"] = "MERCADORIA"


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


class CestaBasicaItem(BaseModel):
    """Situação do item frente ao Anexo I. SEMPRE presente, inclusive quando não
    se aplica: seis coisas diferentes colapsariam num booleano `false` — fora do
    Anexo, EXPRESSAMENTE excluído pelo Anexo, NCM ilegível, consulta
    indisponível e item de serviço (Decisão 7).

    `EXCLUIDA_EXPRESSAMENTE` é a informação mais valiosa desta feature: o produto
    está na posição citada pelo item, mas o próprio Anexo I o retira (foie gras
    no item 19, salmonídeos e atuns no item 20). NÃO é o mesmo que
    `FORA_DO_ANEXO`.
    """

    situacao: str
    item: int | None = None  # 1..26
    dispositivo_legal_ref: str | None = None  # "LCP 214/2025, art. 125, Anexo I, item 5"
    descricao: str | None = None  # texto literal do item no DOU
    ncm_correspondido: str | None = None  # grafia literal que casou: "02.07"
    tipo_correspondencia: str | None = None  # EXATO | PREFIXO | EXCECAO
    # Itens 15/25 e 4/26 citam códigos sobrepostos; `item` é o mais específico,
    # esta lista mostra todos, para o auditor não perguntar por que não o outro.
    itens_correspondentes: list[int] = []
    # O que teria sido cobrado sem a redução — é assim que o controller demonstra
    # o benefício da Cesta Básica, que é o segundo pain point do DEFINE.
    cbs_percentual_sem_reducao: Decimal | None = None
    ibs_percentual_sem_reducao: Decimal | None = None
    valor_cbs_dispensado: Decimal | None = None
    valor_ibs_dispensado: Decimal | None = None
    # Por que a redução vale numa fase cuja alíquota é 0,9%/0,1% (Decisão 5).
    fonte_legal_transicao: str | None = None


class ItemDetalhado(BaseModel):
    sku: str
    ncm: str
    aliquotas_aplicadas: AliquotasAplicadas
    fundamentacao_legal: str
    # Preenchido nos dois ramos do laço (mercadoria e serviço), nunca por
    # default do modelo — um default silencioso faria um item de mercadoria com
    # bug reportar "não se aplica".
    cesta_basica: CestaBasicaItem | None = None


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


class IpiNaoResolvido(BaseModel):
    """Enumera o que ficou de fora quando a resolução foi parcial (Decisão 5).
    Sem isto, `total_ipi = null` não diria QUAL item causou."""

    sku: str
    ncm: str
    situacao: str  # NCM_NAO_ENCONTRADO | CONSULTA_INDISPONIVEL


class ItemNaoAvaliado(BaseModel):
    """Sem isto, `total_cbs_dispensado = null` não diria QUAL item causou."""

    sku: str
    ncm: str
    situacao: str  # NCM_NAO_RECONHECIDO | CONSULTA_INDISPONIVEL


class CestaBasicaResumo(BaseModel):
    """Agregado da Cesta Básica Nacional no payload inteiro.

    Note que os totais são o que foi DISPENSADO (deixou de ser cobrado), não o
    que foi cobrado: `resumo_financeiro.total_cbs` já vem líquido das reduções.
    """

    consulta_disponivel: bool
    # Fato sobre o que a resposta de fato fez, não estimativa do que deveria ter
    # feito — por isso segue preenchido mesmo em avaliação parcial. O nome
    # carrega o "aplicada" para não ser lido como "elegíveis".
    itens_com_reducao_aplicada: int = 0
    # `None` quando QUALQUER item de mercadoria ficou sem avaliação — nunca um
    # total parcial com cara de total (Decisão 9). `0.00` é resposta legítima:
    # payload inteiro fora do Anexo.
    total_cbs_dispensado: Decimal | None = None
    total_ibs_dispensado: Decimal | None = None
    itens_nao_avaliados: list[ItemNaoAvaliado] = []
    fonte_legal: str = (
        "LCP 214/2025, art. 125 e Anexo I — Cesta Básica Nacional de Alimentos: "
        "alíquotas do IBS e da CBS reduzidas a zero. A correspondência é feita "
        "por NCM/SH; vários itens do Anexo I impõem condições adicionais em seu "
        "próprio texto (conformidade com legislação específica, tipo de produto) "
        "que esta simulação não verifica."
    )


class ItemRegimeVigente(BaseModel):
    """Exatamente um dos três blocos de ICMS/ISS é preenchido por item, nunca
    mais de um — são bases mutuamente exclusivas (mercadoria interestadual x
    mercadoria interna x serviço). `None` num bloco significa "não se aplica
    a este item", não "zero". PIS/COFINS só quando `regime_apuracao` foi
    informado no payload."""

    sku: str
    natureza: str

    # Mercadoria, uf_origem != uf_destino.
    icms_interestadual_percentual: Decimal | None = None
    fonte_legal_icms: str | None = None

    # Mercadoria, uf_origem == uf_destino. `fecp` só existe nos estados que
    # cobram o adicional (ex.: RJ +2%, SE +1%) — base legal própria,
    # distinta do ICMS, por isso citada à parte.
    icms_interno_percentual: Decimal | None = None
    fonte_legal_icms_interno: str | None = None
    icms_interno_fecp_percentual: Decimal | None = None
    fonte_legal_icms_interno_fecp: str | None = None

    # Serviço — piso/teto federais (LC 116/2003), não a alíquota municipal
    # exata (nenhuma norma única cobre os 5.570 municípios).
    iss_piso_percentual: Decimal | None = None
    iss_teto_percentual: Decimal | None = None
    fonte_legal_iss_piso: str | None = None
    fonte_legal_iss_teto: str | None = None

    pis_percentual: Decimal | None = None
    cofins_percentual: Decimal | None = None
    fonte_legal_pis: str | None = None
    fonte_legal_cofins: str | None = None

    # IPI (TIPI, Decreto 11.158/2022). `ipi_situacao` é sempre preenchido, nos
    # dois ramos do laço: quatro coisas diferentes colapsariam num só `null` de
    # `ipi_percentual` — NT, NCM desconhecido, consulta falha e item de serviço.
    # NT (`NAO_TRIBUTADO`) NÃO é alíquota 0%: é classificação tributária própria
    # da TIPI, preservada como coluna separada desde a migração 004.
    ipi_percentual: Decimal | None = None
    fonte_legal_ipi: str | None = None
    ipi_situacao: str = SituacaoIpi.NAO_APLICAVEL


class RegimeVigenteResumo(BaseModel):
    regime_apuracao: str | None = None
    total_pis: Decimal | None = None
    total_cofins: Decimal | None = None
    total_icms_interestadual: Decimal = Decimal(0)
    total_icms_interno: Decimal = Decimal(0)
    total_icms_interno_fecp: Decimal = Decimal(0)
    # Faixa, não valor único — ISS não tem alíquota municipal exata neste motor.
    total_iss_piso: Decimal = Decimal(0)
    total_iss_teto: Decimal = Decimal(0)
    # `None` quando QUALQUER item de mercadoria ficou sem resolver, ou quando
    # não há item de mercadoria — nunca um total parcial com cara de total
    # (Decisão 5). `Decimal("0.00")` é um total legítimo: payload todo NT.
    total_ipi: Decimal | None = None
    ipi_nao_resolvido: list[IpiNaoResolvido] = []
    # ICMS_INTERESTADUAL/ICMS_INTERNO/ISS quando nenhum item do payload
    # disparou aquele cálculo; IPI quando algum item de mercadoria ficou sem
    # resolver; PIS/COFINS quando regime_apuracao não foi informado.
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
    cesta_basica: CestaBasicaResumo | None = None
