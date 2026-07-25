from fastapi import APIRouter, Depends, HTTPException, status

from api.audit import registrar_com_seguranca
from api.auth import verificar_api_key
from api.db import get_db_pool
from api.schemas_query import PayloadConsulta, RespostaConsulta, TransicaoResposta
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.estado import State
from orquestracao.executor import executar_consulta

router = APIRouter(prefix="/v1/tax", tags=["query"])


@router.post("/query", response_model=RespostaConsulta)
def consultar(
    payload: PayloadConsulta,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
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

    resposta = RespostaConsulta(
        parecer_final=state.parecer_final,
        valor_liquido=state.resultado_calculo.valor_liquido,
        fonte_legal=state.resultado_calculo.fonte_legal,
        historico=[
            TransicaoResposta(no=t.no, resumo_output=t.resumo_output) for t in state.historico
        ],
    )

    # contexto_recuperado_ids fica vazio: a orquestração real ainda não busca
    # no Qdrant (4 dos 5 nós são fake, CLAUDE.md) — nada para citar de verdade
    # ainda. Registrar IDs inventados aqui seria a mesma classe de erro que
    # este projeto trata como inaceitável em alíquota: dado que parece real e
    # não é.
    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=payload.texto_consulta,
        resposta_parecer_md=resposta.parecer_final,
        payload_calculo={
            "ano_operacao": payload.ano_operacao,
            "valor_base": str(payload.valor_base),
            "valor_liquido": str(resposta.valor_liquido),
        },
    )

    return resposta
