from orquestracao.estado import State


def no_extrator_regras(state: State) -> State:
    # FAKE — sem Extrator de Regras real (LLM) configurado nesta feature.
    # Monta o payload no formato que motor_calculo.TaxCalculatorEngine.calcular() espera,
    # para que a forma do dado já esteja correta quando o Extrator real for conectado.
    state.payload_extraido = {
        "valor_base": state.valor_base,
        "ano_operacao": state.ano_operacao,
    }
    state.registrar_transicao(
        no="extrator_regras",
        resumo_input=f"{len(state.chunks_legais)} chunk(s) recebido(s)",
        resumo_output=f"payload={state.payload_extraido} [FAKE]",
    )
    return state
