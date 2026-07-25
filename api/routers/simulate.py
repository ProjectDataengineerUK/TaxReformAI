from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.audit import registrar_com_seguranca
from api.auth import verificar_api_key
from api.db import get_db_pool
from api.schemas_simulate import (
    AliquotasAplicadas,
    Compensacao,
    EscopoSimulacao,
    ItemDetalhado,
    ItemRegimeVigente,
    PayloadSimulacao,
    RegimeVigenteResumo,
    RespostaSimulacao,
    ResumoFinanceiro,
)
from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.fases import fase_para
from motor_calculo.regime_atual import (
    TRIBUTOS_INDISPONIVEIS,
    TabelaPisCofins,
    icms_interestadual,
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

    for item in payload.itens:
        valor_base_item = item.valor_unitario * item.quantidade
        resultado = engine.calcular(valor_base=valor_base_item, ano_operacao=payload.ano_operacao)

        valor_bruto_total += valor_base_item
        total_cbs += resultado.valor_cbs
        total_ibs += resultado.valor_ibs
        total_is += resultado.valor_is
        valor_liquido_total += resultado.valor_liquido

        itens_detalhados.append(
            ItemDetalhado(
                sku=item.sku,
                ncm=item.ncm,
                aliquotas_aplicadas=AliquotasAplicadas(
                    cbs_percentual=regra.aliq_cbs * 100,
                    ibs_percentual=regra.aliq_ibs * 100,
                    is_percentual=regra.aliq_is * 100,
                ),
                fundamentacao_legal=resultado.fonte_legal,
            )
        )

        icms = icms_interestadual(
            item.uf_origem, item.uf_destino, bem_importado=item.bem_importado
        )
        total_icms_interestadual += (icms.aliquota * valor_base_item).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        item_regime = ItemRegimeVigente(
            sku=item.sku,
            icms_interestadual_percentual=icms.aliquota * 100,
            fonte_legal_icms=icms.fonte_legal,
        )
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
        itens_regime_vigente.append(item_regime)

    # Durante a transição os tributos do regime antigo continuam devidos. O
    # escopo é dinâmico porque PIS/COFINS entram quando regime_apuracao é
    # informado — declarar um escopo fixo voltaria a esconder o que a
    # resposta de fato contém.
    tributos_incluidos = ["CBS", "IBS", "IS", "ICMS_INTERESTADUAL"]
    tributos_nao_calculados = list(TRIBUTOS_INDISPONIVEIS)
    if regra_pis_cofins is not None:
        tributos_incluidos.extend(["PIS", "COFINS"])
    else:
        tributos_nao_calculados = ["PIS", "COFINS", *tributos_nao_calculados]

    escopo = EscopoSimulacao(
        tributos_incluidos=tributos_incluidos,
        tributos_nao_incluidos=tributos_nao_calculados,
        advertencia=(
            "Projeção do IVA Dual (CBS/IBS/IS) mais o regime vigente calculável sem "
            "dado externo (PIS/COFINS quando regime_apuracao é informado; ICMS "
            "interestadual). NÃO inclui IPI (tabela TIPI por NCM), ICMS interno nem "
            "ISS — dependem de legislação estadual/municipal ou tabela sem norma "
            "federal única para citar; o valor líquido não representa a carga "
            "tributária total da operação."
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
            tributos_nao_calculados=tributos_nao_calculados,
        ),
        itens_regime_vigente=itens_regime_vigente,
    )

    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=f"POST /v1/tax/simulate ano={payload.ano_operacao} "
        f"operacao={payload.operacao_tipo} itens={len(payload.itens)}",
        resposta_parecer_md=(
            f"CBS {total_cbs} + IBS {total_ibs} + IS {total_is} sobre "
            f"{valor_bruto_total} ({fase.value}). {resposta.compensacao.fonte_legal or ''}"
        ),
        payload_calculo=payload.model_dump(mode="json"),
    )

    return resposta
