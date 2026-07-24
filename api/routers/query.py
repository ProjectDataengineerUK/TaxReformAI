from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verificar_api_key
from api.schemas_query import PayloadConsulta, RespostaConsulta, TransicaoResposta
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.estado import State
from orquestracao.executor import executar_consulta

router = APIRouter(prefix="/v1/tax", tags=["query"])


@router.post("/query", response_model=RespostaConsulta)
def consultar(
    payload: PayloadConsulta, tenant_id: str = Depends(verificar_api_key)
) -> RespostaConsulta:
    state = State(
        texto_consulta=payload.texto_consulta,
        ano_operacao=payload.ano_operacao,
        valor_base=payload.valor_base,
    )
    try:
        state = executar_consulta(state)
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    assert state.resultado_calculo is not None
    assert state.parecer_final is not None

    return RespostaConsulta(
        parecer_final=state.parecer_final,
        valor_liquido=state.resultado_calculo.valor_liquido,
        fonte_legal=state.resultado_calculo.fonte_legal,
        historico=[
            TransicaoResposta(no=t.no, resumo_output=t.resumo_output) for t in state.historico
        ],
    )
