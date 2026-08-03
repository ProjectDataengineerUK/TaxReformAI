import functools

from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def construir_grafo(deps: DependenciasOrquestracao):
    """Isolado numa função — `langgraph` pode não estar instalado no ambiente
    de teste (ver DESIGN, Decision 1). A lógica de negócio dos nós, importada
    acima, não depende de `langgraph` para ser testada.

    Nós do LangGraph recebem só `state`, então `deps` é capturado via
    `functools.partial` na construção do grafo (LLM_REAL_VERTEX_AI, Decision 1)
    — não executável/testável neste sandbox, só revisão de código, mesma
    situação já registrada para esta DAG desde ORQUESTRACAO_MULTIAGENTE."""
    from langgraph.graph import END, START, StateGraph

    from orquestracao.estado import State

    grafo = StateGraph(State)
    grafo.add_node("classificador", functools.partial(no_classificador, deps=deps))
    grafo.add_node("pesquisador_legal", functools.partial(no_pesquisador_legal, deps=deps))
    grafo.add_node("extrator_regras", functools.partial(no_extrator_regras, deps=deps))
    grafo.add_node("deterministico", no_deterministico)
    grafo.add_node("sintetizador", functools.partial(no_sintetizador, deps=deps))

    grafo.add_edge(START, "classificador")
    grafo.add_edge("classificador", "pesquisador_legal")
    grafo.add_edge("pesquisador_legal", "extrator_regras")
    grafo.add_edge("extrator_regras", "deterministico")
    grafo.add_edge("deterministico", "sintetizador")
    grafo.add_edge("sintetizador", END)

    return grafo.compile()
