from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def construir_grafo():
    """Isolado numa função — `langgraph` pode não estar instalado no ambiente
    de teste (ver DESIGN, Decision 1). A lógica de negócio dos nós, importada
    acima, não depende de `langgraph` para ser testada."""
    from langgraph.graph import END, START, StateGraph

    from orquestracao.estado import State

    grafo = StateGraph(State)
    grafo.add_node("classificador", no_classificador)
    grafo.add_node("pesquisador_legal", no_pesquisador_legal)
    grafo.add_node("extrator_regras", no_extrator_regras)
    grafo.add_node("deterministico", no_deterministico)
    grafo.add_node("sintetizador", no_sintetizador)

    grafo.add_edge(START, "classificador")
    grafo.add_edge("classificador", "pesquisador_legal")
    grafo.add_edge("pesquisador_legal", "extrator_regras")
    grafo.add_edge("extrator_regras", "deterministico")
    grafo.add_edge("deterministico", "sintetizador")
    grafo.add_edge("sintetizador", END)

    return grafo.compile()
