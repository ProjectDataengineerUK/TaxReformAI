from api.simulacao import calcular_simulacao_completa
from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.estado import State


def no_deterministico(state: State, deps: DependenciasOrquestracao) -> State:
    # AliquotaNaoDisponivelError/SkuNaoResolvidoError propagam sem serem
    # capturadas — o grafo deve interromper, nunca seguir para o
    # Sintetizador com dado inventado (AT-002), mesma disciplina de antes
    # da paridade com /simulador (COMPARATIVO_REGIME_ATUAL_IVA_DUAL).
    resultado = calcular_simulacao_completa(
        itens=state.itens,
        ano_operacao=state.ano_operacao,
        regime_apuracao=state.regime_apuracao,
        comprador_tipo=state.comprador_tipo,
        db_pool=deps.db_pool,
        tenant_id=state.tenant_id,
    )

    state.resultado_simulacao = resultado
    state.registrar_transicao(
        no="deterministico",
        resumo_input=f"{len(state.itens)} item(ns), ano={state.ano_operacao}",
        resumo_output=(
            f"valor_liquido={resultado.resumo_financeiro.valor_liquido_projetado_split_payment}, "
            f"fonte={resultado.fonte_legal_fase}"
        ),
    )
    return state
