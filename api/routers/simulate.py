from fastapi import APIRouter, Depends, HTTPException, status

from api.audit import registrar_com_seguranca
from api.auth import verificar_api_key
from api.db import get_db_pool
from api.schemas_simples_nacional import (
    ItemPartilhaSimplesNacional,
    PayloadSimplesNacional,
    RespostaSimplesNacional,
)
from api.schemas_simulate import (
    PayloadSimulacao,
    PisoAliquotaIbsConsulta,
    RespostaSimulacao,
)
from api.simulacao import SkuNaoResolvidoError, calcular_simulacao_completa
from motor_calculo.fases import fase_para
from motor_calculo.piso_aliquota_ibs import piso_aliquota_ibs
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.simples_nacional import Atividade, calcular_simples_nacional

router = APIRouter(prefix="/v1/tax", tags=["simulate"])


@router.post("/simulate", response_model=RespostaSimulacao)
def simular(
    payload: PayloadSimulacao,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSimulacao:
    # A credencial é a autoridade sobre o tenant; o tenant_id do corpo existe
    # por exigência do contrato com ERPs (blueprint, seção 8.1). Sem esta
    # checagem, um cliente autenticado poderia simular declarando o tenant de
    # outro — inofensivo hoje (nada é persistido), mas uma falha real de
    # multi-tenancy assim que o schema PostgreSQL (seção 7) existir.
    # A mensagem não ecoa o tenant autenticado, para não vazar quem é o dono
    # da chave a quem apenas a possui.
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id do payload não corresponde à credencial autenticada",
        )

    # Toda a lógica de cálculo (Anexos de redução, IPI, regime atual por
    # item) vive em api/simulacao.py — reaproveitada por
    # orquestracao/nos/deterministico.py sem duplicação (COMPARATIVO_REGIME_
    # ATUAL_IVA_DUAL, Decision 1). As duas exceções de domínio nunca chegam
    # aqui como HTTPException — a tradução é responsabilidade de CADA
    # chamador.
    try:
        resposta = calcular_simulacao_completa(
            itens=payload.itens,
            ano_operacao=payload.ano_operacao,
            regime_apuracao=payload.regime_apuracao,
            comprador_tipo=payload.comprador_tipo,
            db_pool=db_pool,
            tenant_id=tenant_id,
        )
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except SkuNaoResolvidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    fase = fase_para(payload.ano_operacao)
    resumo = resposta.resumo_financeiro
    regime = resposta.regime_vigente
    # Sempre preenchido por calcular_simulacao_completa — nunca None na
    # prática, mas o schema declara Optional (histórico de antes da
    # generalização dos Anexos).
    reducao = resposta.reducao

    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=f"POST /v1/tax/simulate ano={payload.ano_operacao} "
        f"operacao={payload.operacao_tipo} itens={len(payload.itens)}",
        resposta_parecer_md=(
            f"CBS {resumo.total_cbs} + IBS {resumo.total_ibs} + IS {resumo.total_is} sobre "
            f"{resumo.valor_bruto_total} ({fase.value}). "
            f"IPI {regime.total_ipi if regime.total_ipi is not None else 'não resolvido'}. "
            f"Redução de CBS/IBS por NCM/NBS ({len(reducao.anexos_aplicados)} "
            f"Anexo(s) neste payload): {reducao.itens_com_reducao_aplicada} item(ns) "
            f"reduzido(s), CBS {reducao.total_cbs_dispensado} e IBS {reducao.total_ibs_dispensado} "
            "dispensados"
            + (
                f" (Anexos {', '.join(reducao.anexos_aplicados)})"
                if reducao.anexos_aplicados
                else ""
            )
            + (
                f", {reducao.itens_por_capitulo} por correspondência de capítulo"
                if reducao.itens_por_capitulo
                else ""
            )
            # Registra se o campo foi informado, e não só o resultado: é o que
            # permite, depois, medir quantos clientes usam a condição de
            # comprador dos arts. 144, II / 145, II / 146, § 2º.
            + f"; comprador_tipo={payload.comprador_tipo or 'não informado'}"
            + ". "
            f"{resposta.compensacao.fonte_legal or ''}"
        ),
        payload_calculo=payload.model_dump(mode="json"),
    )

    return resposta


@router.get("/piso-aliquota-ibs/{ano_operacao}", response_model=PisoAliquotaIbsConsulta)
def consultar_piso_aliquota_ibs(
    ano_operacao: int,
    tenant_id: str = Depends(verificar_api_key),
) -> PisoAliquotaIbsConsulta:
    """Consulta isolada do piso do art. 371/Anexo XVI, independente de
    `/v1/tax/simulate`.

    Existe porque `/v1/tax/simulate` recusa (422) QUALQUER `ano_operacao >=
    2029` hoje — CBS/IBS de referência para as fases `TRANSICAO_ICMS_ISS_
    2029_2032` e `REGIME_PLENO_2033` não estão em `TabelaAliquotasSeed`
    (mesmo bloqueio estrutural do "achado 12"). Isso cobre EXATAMENTE a
    janela em que o piso do Anexo XVI se aplica (2029-2077): o campo
    `RespostaSimulacao.piso_aliquota_ibs` nunca seria alcançável em nenhuma
    resposta de sucesso hoje. Este endpoint não depende do motor de cálculo
    do IVA Dual — só do ano.

    `tenant_id` não é usado no corpo (o dado não tem dimensão de tenant,
    é lei pública igual para todos) — a dependência existe só pelo
    efeito colateral de autenticação, mesmo padrão do resto da API.
    """
    piso = piso_aliquota_ibs(ano_operacao)

    if piso is None:
        return PisoAliquotaIbsConsulta(
            ano_operacao=ano_operacao,
            aplicavel=False,
            nota=(
                "O regime do art. 371 da LCP 214/2025 só vigora de 2029 a "
                f"2077 — {ano_operacao} está fora dessa janela. Isto é "
                "'não se aplica', nunca 'não encontrado'."
            ),
        )

    return PisoAliquotaIbsConsulta(
        ano_operacao=piso.ano_operacao,
        aplicavel=True,
        limite_inferior_percentual=piso.limite_inferior_percentual,
        dispositivo_legal_ref=piso.dispositivo_legal_ref,
        nota=(
            "Este percentual multiplica a alíquota de referência do IBS da "
            "respectiva esfera federativa (Estado, Distrito Federal ou "
            "Município) — uma grandeza calculada a partir de execução "
            "fiscal real (LCP 214/2025, art. 370), que este simulador NÃO "
            "calcula. Este campo não produz nenhuma alíquota mínima "
            "absoluta."
        ),
    )


@router.post("/simulate-simples-nacional", response_model=RespostaSimplesNacional)
def simular_simples_nacional(
    payload: PayloadSimplesNacional,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSimplesNacional:
    """Integração de CBS/IBS à partilha do Simples Nacional (LCP 214/2025,
    Anexos XVIII-XXIII) — endpoint DEDICADO, independente de `/v1/tax/
    simulate`.

    Nunca passa por `fase_para`/`TabelaAliquotasSeed`/`engine.py`: o Simples
    Nacional é um regime SUBSTITUTIVO, não uma redução sobre o IVA Dual do
    regime geral, e `/v1/tax/simulate` já recusa (422) toda `ano_operacao`
    diferente de 2026 — exatamente a janela que esta feature precisa
    (2027-2033). Ver Decisão 1 do DESIGN_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md.
    """
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id do payload não corresponde à credencial autenticada",
        )
    if payload.ano_operacao < 2027:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "A integração de CBS/IBS à partilha do Simples Nacional "
                "(LCP 214/2025, Anexos XVIII-XXIII) só vale a partir de "
                f"2027 — {payload.ano_operacao} está fora dessa janela."
            ),
        )
    atividade = Atividade(payload.atividade.value)
    if atividade is not Atividade.MEI and payload.receita_bruta_acumulada_12_meses is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="receita_bruta_acumulada_12_meses é obrigatória para toda "
            "atividade exceto MEI.",
        )

    try:
        resultado = calcular_simples_nacional(
            atividade,
            payload.receita_bruta_acumulada_12_meses,
            payload.receita_bruta_mes,
            payload.ano_operacao,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    resposta = RespostaSimplesNacional(
        ano_operacao=resultado.ano_operacao,
        atividade=resultado.atividade.value,
        faixa=resultado.faixa,
        receita_bruta_acumulada_12_meses=resultado.receita_bruta_acumulada_12_meses,
        receita_bruta_mes=resultado.receita_bruta_mes,
        aliquota_nominal=resultado.aliquota_nominal,
        valor_deduzir=resultado.valor_deduzir,
        aliquota_efetiva=resultado.aliquota_efetiva,
        partilha=[
            ItemPartilhaSimplesNacional(
                tributo=tributo,
                percentual_efetivo=resultado.partilha_percentual.get(tributo),
                valor_devido=valor,
            )
            for tributo, valor in resultado.valores_devidos.items()
        ],
        valor_total_das=resultado.valor_total_das,
        teto_iss_aplicado=resultado.teto_iss_aplicado,
        icms_iss_fora_do_das=resultado.icms_iss_fora_do_das,
        dispositivo_legal_ref=resultado.dispositivo_legal_ref,
    )

    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=(
            f"POST /v1/tax/simulate-simples-nacional ano={payload.ano_operacao} "
            f"atividade={payload.atividade} receita_mes={payload.receita_bruta_mes}"
        ),
        resposta_parecer_md=(
            f"DAS total: {resultado.valor_total_das} "
            f"(faixa={resultado.faixa}, alíquota efetiva="
            f"{resultado.aliquota_efetiva})."
        ),
        payload_calculo=payload.model_dump(mode="json"),
    )

    return resposta
