from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from api.ipi import SituacaoIpi
from motor_calculo.regime_atual import RegimeApuracao


class CompradorTipo(StrEnum):
    """Quem ADQUIRE, quando isso muda a alíquota.

    Só os dois tipos que a lei nomeia (arts. 144, II; 145, II; 146, § 1º) — não
    é uma taxonomia de clientes. Enum fechado, e não texto livre como
    `operacao_tipo`, porque este campo MUDA O NÚMERO: "orgao publico", "ÓRGÃO
    PÚBLICO" e "prefeitura" precisariam todos significar a mesma coisa — ou,
    pior, silenciosamente não significar nada.

    Informá-lo é DECLARATÓRIO: a simulação não verifica imunidade nem validade
    de CEBAS, e diz isso em `fonte_legal`. Mesma natureza de `bem_importado` e
    `regime_apuracao`.
    """

    ORGAO_PUBLICO = "ORGAO_PUBLICO"  # arts. 144 II "a" / 145 II "a" / 146 §1º I
    ENTIDADE_CEBAS_SUS = "ENTIDADE_CEBAS_SUS"  # arts. 144 II "b" / 145 II "b" / 146 §1º II


class ItemSimulacao(BaseModel):
    sku: str
    # ERA obrigatório (`str`) — mudança ADITIVA de tipo: todo payload que já
    # informa `ncm` continua funcionando idênticamente. `None` habilita a
    # resolução por `sku` cadastrado em `empresa_skus` (API_EMPRESA_SKUS) —
    # o valor explícito, quando presente, SEMPRE vence sobre o catálogo.
    ncm: str | None = None
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
    # Código NBS (Nomenclatura Brasileira de Serviços), vocabulário PRÓPRIO,
    # nunca comingle com `ncm` (Achado crítico 4 do /define de
    # ANEXOS_REDUCAO_PERCENTUAL_NBS): 9 dígitos, não 8. Só tem efeito em itens
    # `natureza="SERVICO"` — item de MERCADORIA com `nbs` preenchido por
    # engano nunca alcança a trilha de redução por NBS. `None` (default)
    # preserva o comportamento de todo payload existente antes deste campo.
    nbs: str | None = None
    # Declaratório, como `comprador_tipo`/`bem_importado`: a simulação NÃO
    # verifica nacionalidade de obra/produção. Só afeta itens cujo Anexo X
    # exija conteúdo nacional majoritário (art. 139, §§1º-3º da LCP
    # 214/2025) — ausente ou falso, a alíquota geral se aplica e a resposta
    # cita o que destravaria os 60%.
    conteudo_nacional_majoritario: bool | None = None
    # Declaratório: a simulação NÃO verifica composição societária real. Só
    # afeta itens de segurança da informação/cibernética do Anexo XI cuja
    # redução dependa de o vendedor ser sociedade com sócio brasileiro ≥20%
    # do capital social (art. 142, II da LCP 214/2025) — eixo INDEPENDENTE
    # do `comprador_tipo` (art. 142, I): qualquer um dos dois, satisfeito,
    # já concede os 60%.
    vendedor_capital_brasileiro_qualificado: bool | None = None
    # Declaratório: a simulação NÃO verifica a embalagem real do produto. Só
    # afeta itens cuja categoria do Anexo XVII (produtos fumígenos, bebidas
    # alcoólicas) exija embalagem primária destinada ao consumidor final
    # (LCP 214/2025, art. 409, §2º) para entrar na base de incidência do
    # Imposto Seletivo — ausente ou falso, a sujeição ao IS fica
    # NÃO CONFIRMADA (nunca presumida em nenhuma direção).
    embalagem_primaria_consumidor_final: bool | None = None


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
    # Mesmo contrato de `regime_apuracao`: None significa "não informado", nunca
    # um default. Vive no nível da OPERAÇÃO, não do item — não existe nota em
    # que dois itens tenham compradores diferentes, e por item seriam 100 cópias
    # do mesmo valor por payload.
    #
    # Efeito, e só ele: para um item cujo Anexo vencedor tenha condição de
    # comprador (IV, V, VI), o percentual aplicado passa de 60% para 100% e a
    # resposta cita OS DOIS dispositivos. Ausente, aplica-se 60% e a resposta
    # declara, no próprio item, que a alíquota seria zero para comprador
    # qualificado (`zero_por_comprador_disponivel`).
    comprador_tipo: CompradorTipo | None = None


class AliquotasAplicadas(BaseModel):
    cbs_percentual: Decimal
    ibs_percentual: Decimal
    is_percentual: Decimal


class ItemCorrespondente(BaseModel):
    """Um item que também casou com o código. Qualificado pelo Anexo porque
    "item 5" sozinho é ambíguo entre 10 Anexos (todos têm um item 5)."""

    anexo: str
    item: str


class ReducaoItem(BaseModel):
    """Situação do item frente aos 10 Anexos de redução por NCM da LCP 214/2025.

    Redução a ZERO: I (art. 125, cesta básica), XII (art. 144, I, dispositivos
    médicos), XIII (art. 145, I, acessibilidade) e XV (art. 148,
    hortícolas/frutas/ovos). Redução de 60%: IV (art. 131, dispositivos
    médicos), V (art. 132, acessibilidade), VI (art. 133, § 1º, nutrição
    enteral/parenteral), VII (art. 135, alimentos), VIII (art. 136,
    higiene/limpeza) e IX (art. 138, insumos agropecuários).

    SEMPRE presente, inclusive quando não se aplica: seis coisas diferentes
    colapsariam num booleano `false` — fora dos Anexos, EXPRESSAMENTE excluído
    por um deles, NCM ilegível, consulta indisponível e item de serviço
    (Decisão 7 do Anexo I).

    `EXCLUIDA_EXPRESSAMENTE` é a informação mais valiosa desta feature: o produto
    está na posição citada pelo item, mas o próprio item o retira (foie gras no
    I/19, próteses dentárias do XII/5, `0306.11` no VII/1). NÃO é o mesmo
    que `FORA_DO_ANEXO`.

    Sucede o bloco `reducao_zero`, renomeado porque o mesmo bloco agora responde
    por uma cadeira de rodas a zero E por um sabão de toucador a 60% —
    `"reducao_zero": {"situacao": "APLICADA"}` num item cuja CBS não é zero é
    falso (Decisão 9).
    """

    situacao: str
    anexo: str | None = None  # "I" | "IV" | ... | "XV"
    item: str | None = None  # grafia do DOU: "5", "1.2"
    # 100.00 = alíquota reduzida a zero; 60.00 = restam 40% da alíquota da fase.
    percentual_reducao: Decimal | None = None
    # "LCP 214/2025, art. 144, Anexo XII, item 1.2"
    dispositivo_legal_ref: str | None = None
    # Preenchido em TODO item dos Anexos IV/V/VI: com `comprador_tipo` ausente é
    # o aviso de que a alíquota real seria zero; com ele presente é a
    # fundamentação do zero aplicado (arts. 144, II; 145, II; 146, § 2º).
    dispositivo_legal_comprador: str | None = None
    # True quando 60% foi aplicado MAS a alíquota seria zero se o comprador
    # fosse órgão público/entidade CEBAS e o payload tivesse informado.
    zero_por_comprador_disponivel: bool = False
    # Os dois campos abaixo são do vocabulário NBS (Anexos X/XI, feature
    # ANEXOS_REDUCAO_PERCENTUAL_NBS) — sempre `None`/`False` para itens
    # resolvidos pela trilha NCM, cujo mecanismo de condição é o inverso
    # (upgrade 60%→0%, não gating geral→60%; ver `zero_por_comprador_ref`
    # acima). Citado sempre que o item TEM condição — informada ou não.
    condicao_pendente_ref: str | None = None
    # True só quando a condição existe E não foi satisfeita — "poderia ter
    # ganhado 60% e não ganhou por falta de nacionalidade/comprador/vendedor
    # qualificado no payload".
    reducao_condicionada_disponivel: bool = False
    descricao: str | None = None  # texto literal do item no DOU
    # Descrição do item-pai, quando `item` é sub-item: sem ela, "Sem mecanismo
    # de propulsão" (XIII/2.1) seria a fundamentação inteira (Decisão 7).
    descricao_contexto: str | None = None
    ncm_correspondido: str | None = None  # grafia literal que casou: "9021.3", "06"
    # EXATO | PREFIXO | CAPITULO | EXCECAO — `CAPITULO` (prefixo de 2 dígitos) é
    # a mais ampla que existe e a ÚNICA cujo erro é tributo a MENOS: concede a
    # redução ao capítulo inteiro da NCM enquanto o texto do item restringe
    # (Capítulo 25 do Anexo IX/3 inclui cimento, mármore e gesso). Existe para
    # que o cliente possa filtrar "revisar manualmente" por máquina (Decisão 7).
    tipo_correspondencia: str | None = None
    # I/15 e I/25, I/4 e I/26, XII/1.2+1.3+14, 9 itens do Anexo IV em
    # `9018.90.99`; `item` é o vencedor do desempate, esta lista mostra todos,
    # para o auditor não perguntar por que não o outro. Nunca truncada.
    itens_correspondentes: list[ItemCorrespondente] = []
    # Itens que EXCLUEM expressamente este código, mesmo quando outro item o
    # inclui: o cogumelo é retirado do XV/2 e incluído pelo VII/14 (Decisão 8).
    itens_excluidos: list[ItemCorrespondente] = []
    # O que teria sido cobrado sem a redução — é assim que o controller demonstra
    # o benefício fiscal, que é o segundo pain point do DEFINE.
    cbs_percentual_sem_reducao: Decimal | None = None
    ibs_percentual_sem_reducao: Decimal | None = None
    valor_cbs_dispensado: Decimal | None = None
    valor_ibs_dispensado: Decimal | None = None
    # Por que a redução vale numa fase cuja alíquota é 0,9%/0,1% (Decisão 5 do
    # Anexo I; os arts. 131-138 e 144/145/148 estão no Título IV, então o art.
    # 348, III, "a" — "operações sujeitas a alíquota reduzida" — os alcança sem
    # ressalva, tanto para zero quanto para 60%).
    fonte_legal_transicao: str | None = None


class ImpostoSeletivoItem(BaseModel):
    """Situação do item frente à base de incidência do Imposto Seletivo (IS —
    LCP 214/2025, art. 409, §§1º-2º, Anexo XVII).

    NUNCA um valor monetário ou percentual: o IS não tem alíquota fixada
    (lei ordinária ainda inexistente) e este model não tem NENHUM campo para
    isso, por desenho — não um campo `None`, o campo simplesmente não
    existe, para que nenhuma versão futura o preencha com `aliq_is` da fase
    por engano (mesma disciplina da Decisão 1/3 de
    ANEXO_XVI_PISO_ALIQUOTA_PROPRIA).

    `CONDICAO_NAO_SATISFEITA` cobre os incisos III/IV (fumígenos, bebidas
    alcoólicas): a sujeição depende de embalagem primária destinada ao
    consumidor final (art. 409, §2º), que o cliente precisa declarar.

    `excecao_uso_ref` é citado sempre que a categoria vencedora (incisos I/II
    — veículos, aeronaves/embarcações) tem ressalva por finalidade de uso
    operacional das Forças Armadas/Segurança Pública — ressalva que esta
    simulação NUNCA verifica, só declara.
    """

    situacao: str
    categoria: str | None = None  # "Veículos", "Bens minerais", etc.
    dispositivo_legal_ref: str | None = None
    condicao_embalagem_primaria_ref: str | None = None
    excecao_uso_ref: str | None = None


class ItemDetalhado(BaseModel):
    sku: str
    # ERA obrigatório (`str`) — segue `ItemSimulacao.ncm`: o valor aqui é o
    # EFETIVO usado no cálculo (payload explícito OU catálogo), `None` só
    # para item de serviço que nunca teve ncm (nem antes desta feature fazia
    # sentido, só era exigido por acidente de schema).
    ncm: str | None
    aliquotas_aplicadas: AliquotasAplicadas
    fundamentacao_legal: str
    # Preenchido nos dois ramos do laço (mercadoria e serviço), nunca por
    # default do modelo — um default silencioso faria um item de mercadoria com
    # bug reportar "não se aplica".
    reducao: ReducaoItem | None = None
    # Idem — tributo DIFERENTE (Imposto Seletivo, não CBS/IBS), por isso um
    # bloco próprio, nunca misturado com `reducao`.
    imposto_seletivo: ImpostoSeletivoItem | None = None
    # True só quando o ncm/nbs USADO no cálculo veio do catálogo
    # (empresa_skus), não do payload — metadado técnico de origem, não
    # fundamentação jurídica (por isso booleano, não um bloco com
    # dispositivo_legal_ref como reducao/imposto_seletivo). Preenchido nos
    # DOIS ramos, nunca por default silencioso do modelo.
    sku_resolvido_do_catalogo: bool = False


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


class ReducaoResumo(BaseModel):
    """Agregado dos 10 Anexos de redução por NCM no payload inteiro.

    Note que os totais são o que foi DISPENSADO (deixou de ser cobrado), não o
    que foi cobrado: `resumo_financeiro.total_cbs` já vem líquido das reduções.
    Com 60%, o dispensado é a DIFERENÇA — o cliente continua devendo 40%.
    """

    consulta_disponivel: bool
    # Fato sobre o que a resposta de fato fez, não estimativa do que deveria ter
    # feito — por isso segue preenchido mesmo em avaliação parcial. O nome
    # carrega o "aplicada" para não ser lido como "elegíveis".
    itens_com_reducao_aplicada: int = 0
    # Quais Anexos de fato moveram o número neste payload — ["I", "VII", "XV"].
    # Ordem do CATÁLOGO (a da lei), não alfabética do rótulo romano.
    anexos_aplicados: list[str] = []
    # Quantos itens tiveram a redução concedida por correspondência de CAPÍTULO
    # (prefixo de 2 dígitos) — a única classe cujo erro é tributo a MENOS. Existe
    # para o ERP conseguir programar "revisar manualmente estes" em vez de
    # precisar ler um aviso em prosa (Decisão 7).
    itens_por_capitulo: int = 0
    # `None` quando QUALQUER item de mercadoria ficou sem avaliação — nunca um
    # total parcial com cara de total (Decisão 9). `0.00` é resposta legítima:
    # payload inteiro fora dos Anexos.
    total_cbs_dispensado: Decimal | None = None
    total_ibs_dispensado: Decimal | None = None
    itens_nao_avaliados: list[ItemNaoAvaliado] = []
    fonte_legal: str = (
        "LCP 214/2025 — reduções de alíquota do IBS e da CBS por NCM/SH. "
        "REDUZIDAS A ZERO: art. 125 e Anexo I (Cesta Básica Nacional de "
        "Alimentos), art. 144, I e Anexo XII (dispositivos médicos), art. 145, "
        "I e Anexo XIII (dispositivos de acessibilidade) e art. 148 e Anexo XV "
        "(produtos hortícolas, frutas e ovos). REDUZIDAS EM 60%: art. 131 e "
        "Anexo IV (dispositivos médicos), art. 132 e Anexo V (dispositivos de "
        "acessibilidade), art. 133, § 1º e Anexo VI (composições para nutrição "
        "enteral e parenteral), art. 135 e Anexo VII (alimentos destinados ao "
        "consumo humano), art. 136 e Anexo VIII (produtos de higiene pessoal e "
        "limpeza) e art. 138 e Anexo IX (insumos agropecuários e aquícolas). "
        "A correspondência é feita por NCM/SH; vários itens impõem condições "
        "adicionais em seu próprio texto (requisitos da Anvisa nos Anexos IV e "
        "XII, norma de órgão competente nos V e XIII, compromisso CMED no VI, "
        "registro no MAPA e conformidade com legislação específica no IX, "
        "destinação e tipo de produto no XV, legislação específica no I) que "
        "esta simulação NÃO verifica. Os itens 22 a 34 do Anexo IX NÃO são "
        "resolvidos: os itens 22 a 33 têm chave NBS (vocabulário de serviço, "
        "fora desta tabela) e o item 34 não cita chave nenhuma. "
        "`comprador_tipo` é DECLARATÓRIO — a simulação não verifica imunidade "
        "nem validade de CEBAS; ela aplica a redução a zero dos arts. 144, II, "
        "145, II e 146, § 2º porque o cliente afirmou a qualidade do "
        "adquirente. As listas dos Anexos IV, V, VI e IX são revisadas a cada "
        "120 dias por ato conjunto do Ministério da Fazenda e do Comitê Gestor "
        "do IBS (arts. 131, § 2º; 132, § 2º; 134; 138, § 10) e esta tabela não "
        "tem dimensão temporal."
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


class PisoAliquotaIbs(BaseModel):
    """Piso do art. 371/Anexo XVI — NUNCA uma alíquota absoluta. Deliberadamente
    SEM nenhum campo de alíquota mínima em R$/percentual final: o percentual
    aqui multiplica a alíquota de referência do IBS da esfera federativa
    (Estado, Distrito Federal ou Município), uma grandeza calculada a partir
    de execução fiscal real (LCP 214/2025, art. 370) que este simulador NÃO
    calcula — ver `motor_calculo/piso_aliquota_ibs.py`. Um campo `None` por
    padrão convidaria alguém a preenchê-lo depois com a alíquota errada; a
    ausência do campo em si é a garantia."""

    ano_operacao: int
    limite_inferior_percentual: Decimal
    dispositivo_legal_ref: str
    nota: str = (
        "Este percentual multiplica a alíquota de referência do IBS da "
        "respectiva esfera federativa (Estado, Distrito Federal ou "
        "Município) — uma grandeza calculada a partir de execução fiscal "
        "real (LCP 214/2025, art. 370), que este simulador NÃO calcula. "
        "Este campo não produz nenhuma alíquota mínima absoluta."
    )


class PisoAliquotaIbsConsulta(BaseModel):
    """Resposta de `GET /v1/tax/piso-aliquota-ibs/{ano_operacao}`.

    Existe porque `/v1/tax/simulate` 422 para QUALQUER `ano_operacao >= 2029`
    hoje (`TabelaAliquotasSeed` não tem `RegraFiscal` para
    `TRANSICAO_ICMS_ISS_2029_2032` nem `REGIME_PLENO_2033` — CBS/IBS de
    referência ainda não fixados) — exatamente a janela inteira em que o
    piso do Anexo XVI se aplica (2029-2077). `RespostaSimulacao.piso_
    aliquota_ibs` nunca é alcançável em nenhuma resposta de sucesso hoje;
    este endpoint é o único jeito de consultar o dado agora, independente do
    bloqueio de CBS/IBS. Ver Decisão 4 do DESIGN_ANEXO_XVI_PISO_ALIQUOTA_
    PROPRIA.md."""

    ano_operacao: int
    aplicavel: bool
    limite_inferior_percentual: Decimal | None = None
    dispositivo_legal_ref: str | None = None
    nota: str


class RespostaSimulacao(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    resumo_financeiro: ResumoFinanceiro
    itens_detalhados: list[ItemDetalhado]
    escopo: EscopoSimulacao
    compensacao: Compensacao
    regime_vigente: RegimeVigenteResumo
    itens_regime_vigente: list[ItemRegimeVigente]
    reducao: ReducaoResumo | None = None
    # Bloco informativo a nível de REQUISIÇÃO (não por item — o art. 371 não
    # menciona produto, serviço, NCM nem NBS), populado só a partir de
    # `ano_operacao`. `None` quando o ano está fora de [2029, 2077]: o regime
    # deste piso simplesmente não vigora fora dessa janela, não é "não
    # encontrado".
    piso_aliquota_ibs: PisoAliquotaIbs | None = None
