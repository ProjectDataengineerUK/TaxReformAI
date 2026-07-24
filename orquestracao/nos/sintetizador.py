from orquestracao.estado import State


def no_sintetizador(state: State) -> State:
    # FAKE — sem Sintetizador de Pareceres real (LLM) configurado nesta feature.
    resultado = state.resultado_calculo
    assert resultado is not None, "no_sintetizador requer resultado_calculo já preenchido"

    parecer = (
        f"## Parecer de Simulação Tributária\n\n"
        f"Para a operação de valor base R$ {resultado.valor_base}, na fase correspondente "
        f"ao ano {state.ano_operacao}, apuram-se:\n\n"
        f"- CBS: R$ {resultado.valor_cbs}\n"
        f"- IBS: R$ {resultado.valor_ibs}\n"
        f"- IS: R$ {resultado.valor_is}\n"
        f"- Total de tributos: R$ {resultado.total_tributos}\n"
        f"- Valor líquido: R$ {resultado.valor_liquido}\n\n"
        f"**Fundamentação legal:** {resultado.fonte_legal}"
    )

    state.parecer_final = parecer
    state.registrar_transicao(
        no="sintetizador",
        resumo_input=f"valor_liquido={resultado.valor_liquido}",
        resumo_output="parecer Markdown gerado [FAKE]",
    )
    return state
