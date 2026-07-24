import re

from orquestracao.estado import State

_CPF_RE = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}")


def mascarar_pii(texto: str) -> str:
    texto = _CNPJ_RE.sub("[CNPJ_MASCARADO]", texto)
    texto = _CPF_RE.sub("[CPF_MASCARADO]", texto)
    return texto


def no_classificador(state: State) -> State:
    texto_mascarado = mascarar_pii(state.texto_consulta)

    # Classificação de intenção FAKE — sem LLM configurado nesta feature (ver DEFINE, Constraints)
    intencao = "SIMULACAO_TRIBUTARIA"

    state.texto_mascarado = texto_mascarado
    state.intencao = intencao
    state.registrar_transicao(
        no="classificador",
        resumo_input=texto_mascarado[:50],
        resumo_output=f"intencao={intencao}, pii_mascarado={texto_mascarado != state.texto_consulta}",
    )
    return state
