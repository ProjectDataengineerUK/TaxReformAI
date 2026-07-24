from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed
from orquestracao.estado import State


def no_deterministico(state: State) -> State:
    engine = TaxCalculatorEngine(tabela=TabelaAliquotasSeed())

    # AliquotaNaoDisponivelError propaga sem ser capturada — o grafo deve
    # interromper, nunca seguir para o Sintetizador com dado inventado (AT-002)
    resultado = engine.calcular(
        valor_base=state.payload_extraido["valor_base"],
        ano_operacao=state.payload_extraido["ano_operacao"],
    )

    state.resultado_calculo = resultado
    state.registrar_transicao(
        no="deterministico",
        resumo_input=f"valor_base={state.valor_base}, ano={state.ano_operacao}",
        resumo_output=f"valor_liquido={resultado.valor_liquido}, fonte={resultado.fonte_legal}",
    )
    return state
