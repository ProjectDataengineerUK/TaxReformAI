import datetime

from ingestion.chunking.chunk_models import Chunk
from orquestracao.estado import State


def no_pesquisador_legal(state: State) -> State:
    # FAKE — sem Qdrant Cloud real disponível nesta feature (ver DEFINE, Constraints).
    # Retorna Chunks no schema real de ingestion/chunking/chunk_models.py, para que a
    # forma do dado já esteja correta quando a busca real for conectada.
    chunk_sintetico = Chunk(
        documento_id="LCP_214_2025",
        dispositivo="Art. 1, Inciso I",
        esfera="FEDERAL_CBS_IBS",
        data_vigencia_inicio=datetime.date(state.ano_operacao, 1, 1),
        texto="o Imposto sobre Bens e Serviços (IBS), de competência compartilhada entre "
        "Estados, Municípios e Distrito Federal",
        parent_texto="Ficam instituídos:",
        fonte_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
    )

    state.chunks_legais = [chunk_sintetico]
    state.registrar_transicao(
        no="pesquisador_legal",
        resumo_input=state.intencao or "",
        resumo_output=f"{len(state.chunks_legais)} chunk(s) retornado(s) [FAKE]",
    )
    return state
