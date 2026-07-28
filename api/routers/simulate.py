from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.audit import registrar_com_seguranca
from api.auth import verificar_api_key
from api.cesta_basica import consultar_com_seguranca
from api.cesta_basica import resolver_item as resolver_cesta_basica
from api.db import get_db_pool
from api.ipi import consultar_ipi_com_seguranca, normalizar_ncm, resolver_item
from api.ncm import digitos_ncm, prefixos_ncm
from api.schemas_simulate import (
    AliquotasAplicadas,
    CestaBasicaItem,
    CestaBasicaResumo,
    Compensacao,
    EscopoSimulacao,
    IpiNaoResolvido,
    ItemDetalhado,
    ItemNaoAvaliado,
    ItemRegimeVigente,
    PayloadSimulacao,
    RegimeVigenteResumo,
    RespostaSimulacao,
    ResumoFinanceiro,
)
from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.fases import fase_para
from motor_calculo.reducoes import aplicar_reducao_a_zero
from motor_calculo.regime_atual import (
    TRIBUTOS_INDISPONIVEIS,
    TabelaPisCofins,
    icms_interestadual,
    icms_interno,
    iss_faixa,
)
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed

router = APIRouter(prefix="/v1/tax", tags=["simulate"])


@router.post("/simulate", response_model=RespostaSimulacao)
def simular(
    payload: PayloadSimulacao,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSimulacao:
    # A credencial é a autoridade sobre o tenant; o tenant_id do corpo existe
    # por exigência do contrato com ERPs (blueprint, seção 8.1). Sem esta
    # checagem, um cliente autenticado poderia simular declarando o tenant de
    # outro — inofensivo hoje (nada é persistido), mas uma falha real de
    # multi-tenancy assim que o schema PostgreSQL (seção 7) existir.
    # A mensagem não ecoa o tenant autenticado, para não vazar quem é o dono
    # da chave a quem apenas a possui.
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id do payload não corresponde à credencial autenticada",
        )

    tabela = TabelaAliquotasSeed()
    fase = fase_para(payload.ano_operacao)
    try:
        regra = tabela.buscar(fase)
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    # Uma fase pode existir na tabela e ainda assim ser parcialmente conhecida
    # (2027-2028: IBS fixado pelo art. 344, CBS pendente pelo art. 347). O
    # engine também recusa, mas aqui a recusa vem antes do laço — `regra` é lida
    # adiante para montar `aliquotas_aplicadas`, e `None * 100` estouraria.
    indisponiveis = regra.tributos_indisponiveis()
    if indisponiveis:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(
                AliquotaNaoDisponivelError(fase, tributos=indisponiveis, regra=regra)
            ),
        )

    engine = TaxCalculatorEngine(tabela=tabela)
    tabela_pis_cofins = TabelaPisCofins()
    regra_pis_cofins = (
        tabela_pis_cofins.buscar(payload.regime_apuracao)
        if payload.regime_apuracao is not None
        else None
    )

    itens_detalhados: list[ItemDetalhado] = []
    itens_regime_vigente: list[ItemRegimeVigente] = []
    valor_bruto_total = Decimal(0)
    total_cbs = Decimal(0)
    total_ibs = Decimal(0)
    total_is = Decimal(0)
    valor_liquido_total = Decimal(0)
    total_pis = Decimal(0) if regra_pis_cofins else None
    total_cofins = Decimal(0) if regra_pis_cofins else None
    total_icms_interestadual = Decimal(0)
    total_icms_interno = Decimal(0)
    total_icms_interno_fecp = Decimal(0)
    total_iss_piso = Decimal(0)
    total_iss_teto = Decimal(0)
    # Acumula o que de fato apareceu em algum item, para o escopo declarar só
    # o que a resposta realmente contém — mesma razão de `regra_pis_cofins`
    # ser opcional em vez de assumido.
    tributos_regime_vigente_incluidos: set[str] = set()

    # UMA consulta por requisição, antes do laço — não uma por item (Decisão 7).
    # `set` cobre NCMs repetidos (100 itens do mesmo SKU = 1 código); `sorted`
    # deixa a query determinística e comparável em teste. Payload só de
    # serviços não abre conexão nenhuma.
    ncms_consultar = sorted(
        {
            codigo
            for item in payload.itens
            if item.natureza == "MERCADORIA" and (codigo := normalizar_ncm(item.ncm))
        }
    )
    consulta_ipi = consultar_ipi_com_seguranca(db_pool, ncms_consultar)

    # Segunda consulta, de domínio de falha SEPARADO da TIPI de propósito: uma
    # tabela sem GRANT degrada só o seu tributo. Cada código de 8 dígitos vira 5
    # prefixos candidatos (Decisão 2); `set` cobre códigos repetidos e prefixos
    # comuns entre itens diferentes (100 itens do mesmo capítulo compartilham o
    # prefixo de 4); `sorted` deixa a query determinística e comparável em teste.
    # Payload só de serviços não abre conexão nenhuma.
    prefixos_consultar = sorted(
        {
            prefixo
            for item in payload.itens
            if item.natureza == "MERCADORIA" and (codigo := digitos_ncm(item.ncm))
            for prefixo in prefixos_ncm(codigo)
        }
    )
    consulta_cesta = consultar_com_seguranca(db_pool, prefixos_consultar)

    total_ipi: Decimal | None = Decimal(0)
    itens_mercadoria = 0
    ipi_nao_resolvido: list[IpiNaoResolvido] = []

    total_cbs_dispensado = Decimal(0)
    total_ibs_dispensado = Decimal(0)
    itens_com_reducao = 0
    itens_nao_avaliados: list[ItemNaoAvaliado] = []

    for item in payload.itens:
        valor_base_item = item.valor_unitario * item.quantidade
        resultado = engine.calcular(valor_base=valor_base_item, ano_operacao=payload.ano_operacao)

        # `cesta_basica` é preenchida nos DOIS ramos (mercadoria e serviço),
        # nunca por default do modelo — mesma disciplina do `ipi_situacao`.
        resolucao_cesta = resolver_cesta_basica(item.natureza, item.ncm, consulta_cesta)
        cesta_basica_item = CestaBasicaItem(
            situacao=resolucao_cesta.situacao.value,
            item=resolucao_cesta.item,
            dispositivo_legal_ref=resolucao_cesta.dispositivo_legal_ref,
            descricao=resolucao_cesta.descricao,
            ncm_correspondido=resolucao_cesta.texto_ncm,
            tipo_correspondencia=resolucao_cesta.tipo_correspondencia,
            itens_correspondentes=list(resolucao_cesta.itens_correspondentes),
        )

        if resolucao_cesta.aplicada:
            cbs_dispensado, ibs_dispensado = resultado.valor_cbs, resultado.valor_ibs
            resultado = aplicar_reducao_a_zero(resultado)
            total_cbs_dispensado += cbs_dispensado
            total_ibs_dispensado += ibs_dispensado
            itens_com_reducao += 1
            cesta_basica_item = cesta_basica_item.model_copy(
                update={
                    "cbs_percentual_sem_reducao": regra.aliq_cbs * 100,
                    "ibs_percentual_sem_reducao": regra.aliq_ibs * 100,
                    "valor_cbs_dispensado": cbs_dispensado,
                    "valor_ibs_dispensado": ibs_dispensado,
                    "fonte_legal_transicao": regra.fonte_legal_reducoes,
                }
            )
        elif item.natureza == "MERCADORIA" and not resolucao_cesta.avaliada:
            itens_nao_avaliados.append(
                ItemNaoAvaliado(
                    sku=item.sku, ncm=item.ncm, situacao=resolucao_cesta.situacao.value
                )
            )

        valor_bruto_total += valor_base_item
        # Os totais saem do `resultado` JÁ REDUZIDO, nunca de `regra` — senão a
        # resposta se contradiria (item com cbs_percentual 0 somando 0,9%).
        total_cbs += resultado.valor_cbs
        total_ibs += resultado.valor_ibs
        total_is += resultado.valor_is
        valor_liquido_total += resultado.valor_liquido

        itens_detalhados.append(
            ItemDetalhado(
                sku=item.sku,
                ncm=item.ncm,
                aliquotas_aplicadas=AliquotasAplicadas(
                    cbs_percentual=(
                        Decimal(0) if resolucao_cesta.aplicada else regra.aliq_cbs * 100
                    ),
                    ibs_percentual=(
                        Decimal(0) if resolucao_cesta.aplicada else regra.aliq_ibs * 100
                    ),
                    is_percentual=regra.aliq_is * 100,
                ),
                fundamentacao_legal=resultado.fonte_legal,
                cesta_basica=cesta_basica_item,
            )
        )

        item_regime = ItemRegimeVigente(sku=item.sku, natureza=item.natureza)

        if item.natureza == "SERVICO":
            # ICMS e ISS são bases mutuamente exclusivas — um item de serviço
            # nunca paga ICMS neste motor. Só piso/teto: LC 116/2003 não fixa
            # a alíquota exata de nenhum dos 5.570 municípios.
            faixa = iss_faixa()
            total_iss_piso += (valor_base_item * faixa.piso).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_iss_teto += (valor_base_item * faixa.teto).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            item_regime = item_regime.model_copy(
                update={
                    "iss_piso_percentual": faixa.piso * 100,
                    "iss_teto_percentual": faixa.teto * 100,
                    "fonte_legal_iss_piso": faixa.fonte_legal_piso,
                    "fonte_legal_iss_teto": faixa.fonte_legal_teto,
                }
            )
            tributos_regime_vigente_incluidos.add("ISS")
        elif item.uf_origem.upper() == item.uf_destino.upper():
            # Mesma UF de origem e destino: operação INTERNA, não
            # interestadual — a Resolução do Senado 22/1989 rege só o
            # deslocamento entre estados diferentes. Usar `icms_interestadual`
            # aqui seria citar a norma errada para a operação.
            icms_int = icms_interno(item.uf_origem)
            total_icms_interno += (icms_int.aliquota * valor_base_item).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            update = {
                "icms_interno_percentual": icms_int.aliquota * 100,
                "fonte_legal_icms_interno": icms_int.fonte_legal,
            }
            if icms_int.fecp is not None:
                total_icms_interno_fecp += (icms_int.fecp * valor_base_item).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                update["icms_interno_fecp_percentual"] = icms_int.fecp * 100
                update["fonte_legal_icms_interno_fecp"] = icms_int.fonte_legal_fecp
            item_regime = item_regime.model_copy(update=update)
            tributos_regime_vigente_incluidos.add("ICMS_INTERNO")
        else:
            icms = icms_interestadual(
                item.uf_origem, item.uf_destino, bem_importado=item.bem_importado
            )
            total_icms_interestadual += (icms.aliquota * valor_base_item).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            item_regime = item_regime.model_copy(
                update={
                    "icms_interestadual_percentual": icms.aliquota * 100,
                    "fonte_legal_icms": icms.fonte_legal,
                }
            )
            tributos_regime_vigente_incluidos.add("ICMS_INTERESTADUAL")

        if regra_pis_cofins is not None:
            # Mesma disciplina de arredondamento do engine (ROUND_HALF_UP,
            # centavos) — inconsistência aqui seria erro de cálculo silencioso
            # num sistema financeiro, mesmo que pequeno por item.
            valor_pis_item = (valor_base_item * regra_pis_cofins.aliq_pis).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            valor_cofins_item = (valor_base_item * regra_pis_cofins.aliq_cofins).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_pis += valor_pis_item
            total_cofins += valor_cofins_item
            item_regime = item_regime.model_copy(
                update={
                    "pis_percentual": regra_pis_cofins.aliq_pis * 100,
                    "cofins_percentual": regra_pis_cofins.aliq_cofins * 100,
                    "fonte_legal_pis": regra_pis_cofins.fonte_legal_pis,
                    "fonte_legal_cofins": regra_pis_cofins.fonte_legal_cofins,
                }
            )

        # `ipi_situacao` é preenchido nos DOIS ramos (mercadoria e serviço),
        # nunca por default do modelo: um default silencioso faria um item de
        # mercadoria com bug reportar NAO_APLICAVEL — afirmação jurídica falsa
        # emitida sem ninguém perceber (Decisão 3).
        resolucao = resolver_item(item.natureza, item.ncm, valor_base_item, consulta_ipi)
        item_regime = item_regime.model_copy(
            update={
                "ipi_situacao": resolucao.situacao.value,
                "ipi_percentual": resolucao.percentual,
                "fonte_legal_ipi": resolucao.fonte_legal,
            }
        )
        if item.natureza == "MERCADORIA":
            itens_mercadoria += 1
            if resolucao.resolvido:
                total_ipi += resolucao.valor
            else:
                ipi_nao_resolvido.append(
                    IpiNaoResolvido(
                        sku=item.sku, ncm=item.ncm, situacao=resolucao.situacao.value
                    )
                )

        itens_regime_vigente.append(item_regime)

    # Um único predicado governa total, escopo e advertência — duas noções de
    # "resolvido" divergiriam no primeiro refactor. Sem item de mercadoria não
    # há total de IPI a afirmar (não é zero: é "não se aplica a este payload").
    ipi_completo = itens_mercadoria > 0 and not ipi_nao_resolvido
    if ipi_completo:
        tributos_regime_vigente_incluidos.add("IPI")
        # Em centavos mesmo quando a soma é zero: um payload inteiramente NT
        # devolveria `0` cru, e "0" tem cara de campo não preenchido enquanto
        # "0.00" tem cara do total que de fato é (Decisão 5).
        total_ipi = total_ipi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        total_ipi = None

    # Um único predicado governa os dois totais dispensados e a advertência
    # (Decisão 9): um total parcial é indistinguível de um total completo na
    # tela de um departamento fiscal, e este número tem uso comercial direto
    # ("quanto a cesta básica economizou"). `itens_com_reducao_aplicada` segue
    # preenchido porque é fato sobre o que a resposta fez, não estimativa.
    #
    # O predicado é a LISTA vazia, não `consulta_cesta.disponivel and ...` como
    # o Pattern 7 escreve: os dois são equivalentes sempre que existe ao menos
    # um item de mercadoria (se a consulta caiu, TODOS eles entram na lista),
    # e divergem só no payload sem mercadoria nenhuma — onde a versão do padrão
    # devolveria `total = null` com `itens_nao_avaliados` VAZIO, quebrando a
    # própria invariante que a Decisão 9 enuncia ("null ∧ lista não vazia") e
    # deixando o cliente sem saber qual item faltou (resposta: nenhum). Pior,
    # ela daria respostas diferentes para o mesmo payload de serviços conforme
    # o pool fosse `None` (null) ou estivesse quebrado (0,00), já que sem
    # prefixo a consultar nenhuma conexão chega a ser tentada.
    # `consulta_disponivel` continua no resumo para quem quiser o outro fato.
    avaliacao_completa = not itens_nao_avaliados
    resumo_cesta = CestaBasicaResumo(
        consulta_disponivel=consulta_cesta.disponivel,
        itens_com_reducao_aplicada=itens_com_reducao,
        # Em centavos mesmo quando a soma é zero, pela mesma razão do total_ipi:
        # "0" tem cara de campo não preenchido, "0.00" tem cara do total que é.
        total_cbs_dispensado=(
            total_cbs_dispensado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if avaliacao_completa
            else None
        ),
        total_ibs_dispensado=(
            total_ibs_dispensado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if avaliacao_completa
            else None
        ),
        itens_nao_avaliados=itens_nao_avaliados,
    )

    # Degradar não é silenciar: quando a avaliação foi parcial, a advertência
    # diz explicitamente que CBS/IBS podem estar SUPERESTIMADOS — a direção do
    # erro importa e é o que torna esta degradação aceitável (Decisão 8).
    if not avaliacao_completa:
        situacoes_cesta = sorted({entrada.situacao for entrada in itens_nao_avaliados})
        motivo = (
            f"{len(itens_nao_avaliados)} item(ns) de mercadoria sem avaliação "
            f"({', '.join(situacoes_cesta)})"
        )
        advertencia_cesta = (
            "A Cesta Básica Nacional (LCP 214/2025, art. 125, Anexo I) NÃO pôde ser "
            f"verificada integralmente: {motivo} — CBS/IBS desses itens seguem com a "
            "alíquota geral da fase e podem estar SUPERESTIMADOS; ver "
            "cesta_basica.itens_nao_avaliados."
        )
    elif itens_com_reducao:
        advertencia_cesta = (
            f"Aplica alíquota zero de CBS/IBS a {itens_com_reducao} item(ns) da Cesta "
            "Básica Nacional (LCP 214/2025, art. 125, Anexo I; transição pelo art. "
            "348, III, 'a'), com o item do Anexo citado em cada um. A correspondência "
            "é por NCM/SH e não verifica as condições adicionais que o texto de "
            "vários itens exige."
        )
    else:
        advertencia_cesta = (
            "Nenhum item do payload corresponde à Cesta Básica Nacional "
            "(LCP 214/2025, art. 125, Anexo I)."
        )

    # Durante a transição os tributos do regime antigo continuam devidos. O
    # escopo é dinâmico: ICMS_INTERESTADUAL/ICMS_INTERNO/ISS dependem de quais
    # naturezas/UFs apareceram nos itens (mutuamente exclusivos por item), IPI
    # de todos os itens de mercadoria terem tido o NCM resolvido na TIPI, e
    # PIS/COFINS de `regime_apuracao` ter sido informado — declarar um escopo
    # fixo voltaria a esconder o que a resposta de fato contém.
    # `TRIBUTOS_INDISPONIVEIS` está vazia hoje (o IPI saiu quando ganhou fonte
    # de dado) e continua somada aqui como ponto de extensão.
    tributos_incluidos = ["CBS", "IBS", "IS", *sorted(tributos_regime_vigente_incluidos)]
    tributos_nao_calculados = sorted(
        set(TRIBUTOS_INDISPONIVEIS)
        | (
            {"ICMS_INTERESTADUAL", "ICMS_INTERNO", "ISS", "IPI"}
            - tributos_regime_vigente_incluidos
        )
    )
    if regra_pis_cofins is not None:
        tributos_incluidos.extend(["PIS", "COFINS"])
    else:
        tributos_nao_calculados = sorted([*tributos_nao_calculados, "PIS", "COFINS"])

    # A frase do IPI é condicional e nunca promete 0%: quando falta resolver,
    # diz quantos itens ficaram de fora e por qual situação, e `ipi_nao_resolvido`
    # nomeia cada um.
    if ipi_completo:
        advertencia_ipi = (
            "Inclui IPI da TIPI (Decreto 11.158/2022) para os "
            f"{itens_mercadoria} item(ns) de natureza=MERCADORIA, resolvido por NCM "
            "com o dispositivo legal de cada linha citado no item."
        )
    elif itens_mercadoria == 0:
        advertencia_ipi = (
            "NÃO inclui IPI: nenhum item de natureza=MERCADORIA no payload (o IPI "
            "não incide sobre serviços)."
        )
    else:
        situacoes = sorted({entrada.situacao for entrada in ipi_nao_resolvido})
        advertencia_ipi = (
            f"NÃO inclui IPI: {len(ipi_nao_resolvido)} de {itens_mercadoria} item(ns) "
            f"de mercadoria não teve o IPI resolvido ({', '.join(situacoes)}) — ver "
            "regime_vigente.ipi_nao_resolvido. Isto NÃO significa alíquota zero."
        )

    escopo = EscopoSimulacao(
        tributos_incluidos=tributos_incluidos,
        tributos_nao_incluidos=tributos_nao_calculados,
        advertencia=(
            "Projeção do IVA Dual (CBS/IBS/IS) mais o regime vigente calculável sem "
            "dado externo: PIS/COFINS quando regime_apuracao é informado; ICMS "
            "interestadual ou interno conforme uf_origem/uf_destino de cada item; "
            "ISS (só piso 2%/teto 5% da LC 116/2003, não a alíquota municipal "
            f"exata) para itens com natureza=SERVICO. {advertencia_ipi} "
            f"{advertencia_cesta} O valor "
            "líquido não representa a carga tributária total da operação."
        ),
    )

    resposta = RespostaSimulacao(
        ano_operacao=payload.ano_operacao,
        resumo_financeiro=ResumoFinanceiro(
            valor_bruto_total=valor_bruto_total,
            total_cbs=total_cbs,
            total_ibs=total_ibs,
            total_is=total_is,
            valor_liquido_projetado_split_payment=valor_liquido_total,
        ),
        itens_detalhados=itens_detalhados,
        escopo=escopo,
        compensacao=Compensacao(
            aplicavel=regra.compensavel,
            fonte_legal=regra.fonte_legal_compensacao,
        ),
        regime_vigente=RegimeVigenteResumo(
            regime_apuracao=payload.regime_apuracao,
            total_pis=total_pis,
            total_cofins=total_cofins,
            total_icms_interestadual=total_icms_interestadual,
            total_icms_interno=total_icms_interno,
            total_icms_interno_fecp=total_icms_interno_fecp,
            total_iss_piso=total_iss_piso,
            total_iss_teto=total_iss_teto,
            total_ipi=total_ipi,
            ipi_nao_resolvido=ipi_nao_resolvido,
            tributos_nao_calculados=tributos_nao_calculados,
        ),
        itens_regime_vigente=itens_regime_vigente,
        cesta_basica=resumo_cesta,
    )

    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=f"POST /v1/tax/simulate ano={payload.ano_operacao} "
        f"operacao={payload.operacao_tipo} itens={len(payload.itens)}",
        resposta_parecer_md=(
            f"CBS {total_cbs} + IBS {total_ibs} + IS {total_is} sobre "
            f"{valor_bruto_total} ({fase.value}). "
            f"IPI {total_ipi if total_ipi is not None else 'não resolvido'}. "
            f"Cesta Básica (art. 125): {itens_com_reducao} item(ns) com alíquota "
            "zero de CBS/IBS. "
            f"{resposta.compensacao.fonte_legal or ''}"
        ),
        payload_calculo=payload.model_dump(mode="json"),
    )

    return resposta
