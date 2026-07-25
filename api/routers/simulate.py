from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verificar_api_key
from api.schemas_simulate import (
    AliquotasAplicadas,
    Compensacao,
    EscopoSimulacao,
    ItemDetalhado,
    PayloadSimulacao,
    RespostaSimulacao,
    ResumoFinanceiro,
)
from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.fases import fase_para
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed

router = APIRouter(prefix="/v1/tax", tags=["simulate"])


@router.post("/simulate", response_model=RespostaSimulacao)
def simular(
    payload: PayloadSimulacao, tenant_id: str = Depends(verificar_api_key)
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
    itens_detalhados: list[ItemDetalhado] = []
    valor_bruto_total = Decimal(0)
    total_cbs = Decimal(0)
    total_ibs = Decimal(0)
    total_is = Decimal(0)
    valor_liquido_total = Decimal(0)

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

    # Durante a transição os tributos do regime antigo continuam devidos e este
    # motor não os calcula. Declarar o escopo é o que separa uma projeção
    # honesta de um número que engana por omissão.
    escopo = EscopoSimulacao(
        tributos_incluidos=["CBS", "IBS", "IS"],
        tributos_nao_incluidos=["PIS", "COFINS", "IPI", "ICMS", "ISS"],
        advertencia=(
            "Projeção do IVA Dual isolado. Durante a transição (2026-2033) os tributos "
            "do regime antigo (PIS, COFINS, IPI, ICMS, ISS) continuam devidos e NÃO "
            "estão incluídos neste cálculo — o valor líquido não representa a carga "
            "tributária total da operação."
        ),
    )

    return RespostaSimulacao(
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
    )
