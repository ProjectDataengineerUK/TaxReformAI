from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.estado import State
from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def executar_consulta(state: State, deps: DependenciasOrquestracao) -> State:
    """Encadeia os 5 nós na ordem fixa do pipeline, sem depender de `langgraph`
    (não instalável neste sandbox — ver DESIGN de ORQUESTRACAO_MULTIAGENTE,
    Decision 1). `orquestracao.grafo.construir_grafo()` continua sendo a
    implementação via LangGraph para quando a lib estiver instalável — mesma
    interface pública (`State -> State`).

    `deps` é explícito e obrigatório (LLM_REAL_VERTEX_AI, Decision 1): nunca há
    um client real "implícito" que possa vazar para dentro de um teste."""
    state = no_classificador(state, deps)
    state = no_pesquisador_legal(state, deps)
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)
    state = no_sintetizador(state, deps)
    return state
