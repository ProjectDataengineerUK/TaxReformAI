from ingestion.chunking.chunk_models import Chunk
from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.estado import State


def no_pesquisador_legal(state: State, deps: DependenciasOrquestracao) -> State:
    # Assert, não fallback silencioso: achado da revisão de segurança de
    # LLM_REAL_VERTEX_AI — um `or state.texto_consulta` aqui falharia mudo se
    # este nó rodasse antes do classificador (ex: grafo reordenado no futuro),
    # vazando PII não mascarado para o embedder/Qdrant sem nenhum sinal.
    assert state.texto_mascarado is not None, "texto_mascarado precisa existir antes da busca legal"
    consulta_embutida = deps.embedder.embed_consulta(state.texto_mascarado)

    resultado = deps.qdrant_indexer.search_hybrid(
        dense_query=consulta_embutida.dense_vector,
        sparse_indices=consulta_embutida.sparse_indices,
        sparse_values=consulta_embutida.sparse_values,
        limit=5,
    )
    chunks = [Chunk.model_validate(ponto.payload) for ponto in resultado.points]

    state.chunks_legais = chunks
    state.registrar_transicao(
        no="pesquisador_legal",
        resumo_input=state.intencao or "",
        resumo_output=f"{len(chunks)} chunk(s) reais recuperados do Qdrant",
    )
    return state
