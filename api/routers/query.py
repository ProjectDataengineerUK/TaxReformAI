from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.audit import registrar_com_seguranca
from api.auth import verificar_api_key
from api.db import get_db_pool
from api.dependencias_orquestracao import get_dependencias_orquestracao
from api.schemas_query import PayloadConsulta, RespostaConsulta, TransicaoResposta
from api.simulacao import SkuNaoResolvidoError
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.estado import State
from orquestracao.executor import ConsultaForaDeEscopoError, executar_consulta
from orquestracao.llm.cliente import LLMIndisponivelError
from orquestracao.nos.sintetizador import LLMRespostaInconsistenteError

router = APIRouter(prefix="/v1/tax", tags=["query"])


@router.post("/query", response_model=RespostaConsulta)
def consultar(
    payload: PayloadConsulta,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
    deps: DependenciasOrquestracao = Depends(get_dependencias_orquestracao),
) -> RespostaConsulta:
    # valor_base é DERIVADO da soma dos itens, nunca mais um campo manual do
    # payload (COMPARATIVO_REGIME_ATUAL_IVA_DUAL, Decision 2/6) — elimina o
    # risco de divergência entre um total digitado e a soma real dos itens.
    # `state.valor_base` continua existindo só para não tocar
    # extrator_regras.py, que compara o valor extraído do texto livre contra
    # este total.
    valor_base = sum(
        (item.valor_unitario * item.quantidade for item in payload.itens), Decimal(0)
    )

    state = State(
        texto_consulta=payload.texto_consulta,
        ano_operacao=payload.ano_operacao,
        valor_base=valor_base,
        itens=payload.itens,
        regime_apuracao=payload.regime_apuracao,
        comprador_tipo=payload.comprador_tipo,
        tenant_id=tenant_id,
    )
    try:
        state = executar_consulta(state, deps)
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except SkuNaoResolvidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except ConsultaForaDeEscopoError as exc:
        # Achado real: sem isto, uma pergunta sem nenhuma relação com
        # tributos (ex: receita de bolo) gerava um parecer de simulação
        # fabricado a partir de valor_base/ano_operacao que sobravam no
        # payload — nunca 200 com um cálculo que a pergunta não pediu.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (LLMIndisponivelError, LLMRespostaInconsistenteError) as exc:
        # Nunca 200 com dado fabricado: Vertex AI indisponível ou uma síntese
        # que não reproduz o valor calculado (guardrail do sintetizador,
        # LLM_REAL_VERTEX_AI Decision 4) viram erro explícito, não silêncio.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    assert state.resultado_simulacao is not None
    assert state.parecer_final is not None

    resposta = RespostaConsulta(
        parecer_final=state.parecer_final,
        resultado_simulacao=state.resultado_simulacao,
        historico=[
            TransicaoResposta(no=t.no, resumo_output=t.resumo_output) for t in state.historico
        ],
    )

    # `texto_mascarado`, nunca `payload.texto_consulta` — achado da revisão de
    # segurança de LLM_REAL_VERTEX_AI: o audit log persistia o texto BRUTO em
    # Cloud SQL mesmo quando o mascaramento de PII já rodava corretamente
    # antes de qualquer chamada ao Vertex AI, reintroduzindo o CPF/CNPJ em
    # texto plano no ponto de armazenamento durável. `state.texto_mascarado`
    # sempre existe aqui — `classificador` é o primeiro nó do pipeline fixo.
    assert state.texto_mascarado is not None
    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=state.texto_mascarado,
        resposta_parecer_md=resposta.parecer_final,
        payload_calculo={
            "ano_operacao": payload.ano_operacao,
            "valor_base": str(valor_base),
            "valor_liquido": str(
                resposta.resultado_simulacao.resumo_financeiro.valor_liquido_projetado_split_payment
            ),
        },
        contexto_recuperado_ids=[chunk.qdrant_point_id() for chunk in state.chunks_legais],
    )

    return resposta
