from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verificar_api_key
from api.schemas_simulate import (
    AliquotasAplicadas,
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
    tabela = TabelaAliquotasSeed()
    try:
        regra = tabela.buscar(fase_para(payload.ano_operacao))
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    engine = TaxCalculatorEngine(tabela=tabela)
    itens_detalhados: list[ItemDetalhado] = []
    valor_bruto_total = Decimal("0")
    total_cbs = Decimal("0")
    total_ibs = Decimal("0")
    total_is = Decimal("0")
    valor_liquido_total = Decimal("0")

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
    )
