from dataclasses import dataclass, field
from typing import Protocol

from orquestracao.llm.registrador import REGISTRADOR_NULO, RegistradorUsoLLM

MODELO_HAIKU = "claude-haiku-4-5@20251001"
MODELO_SONNET = "claude-sonnet-5"

# Contorno ao bloqueio real de quota do Vertex AI (LLM_REAL_VERTEX_AI,
# 429 RESOURCE_EXHAUSTED sem previsão): a API direta da Anthropic não
# reconhece o formato Model Garden do Vertex. MODELO_SONNET já é idêntico nos
# dois formatos, por isso não precisa de entrada aqui.
_MAPA_MODELO_PARA_API_DIRETA = {
    MODELO_HAIKU: "claude-haiku-4-5-20251001",
}


class LLMIndisponivelError(Exception):
    """Levantada quando a chamada ao provider de LLM falha (rede, auth, timeout,
    5xx, ou resposta sem bloco de texto). Propaga sem ser capturada pelos nós —
    mesma disciplina de `AliquotaNaoDisponivelError` em `no_deterministico`."""


class ClienteLLM(Protocol):
    def gerar(
        self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido"
    ) -> str: ...


def _extrair_texto(resposta, nome_provider: str) -> str:
    bloco_texto = next((b for b in resposta.content if b.type == "text"), None)
    if bloco_texto is None:
        raise LLMIndisponivelError(f"Resposta d{nome_provider} sem bloco de texto")
    return bloco_texto.text


class ClienteVertexAI:
    """Real — chama Claude via Vertex AI (Agent Platform). Endpoint `global`
    (Decision 2 do DESIGN): recomendado pela Anthropic, sem premium de preço,
    sem exigir região específica — elimina o conflito com `southamerica-east1`
    (região padrão do resto da infraestrutura deste projeto)."""

    def __init__(self, project_id: str, region: str = "global", registrador: RegistradorUsoLLM = REGISTRADOR_NULO):
        from anthropic import AnthropicVertex

        self._client = AnthropicVertex(project_id=project_id, region=region)
        self._registrador = registrador

    def gerar(
        self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido"
    ) -> str:
        try:
            resposta = self._client.messages.create(
                model=modelo, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            self._registrador.registrar(no_origem, modelo, 0, 0, sucesso=False, erro_detalhe=str(exc)[:200])
            raise LLMIndisponivelError(f"Vertex AI indisponível: {exc}") from exc

        texto = _extrair_texto(resposta, "o Vertex AI")
        self._registrador.registrar(
            no_origem, modelo, resposta.usage.input_tokens, resposta.usage.output_tokens, sucesso=True
        )
        return texto


class ClienteAnthropicDireto:
    """Real — chama Claude via API direta da Anthropic (console.anthropic.com).
    Contorno ao bloqueio real de quota do Vertex AI Model Garden
    (`LLM_REAL_VERTEX_AI`, 429 RESOURCE_EXHAUSTED sem previsão). Traduz o ID de
    modelo do formato Vertex para o formato da API direta — os nós continuam
    importando MODELO_HAIKU/MODELO_SONNET sem saber qual provider está ativo."""

    def __init__(self, api_key: str, registrador: RegistradorUsoLLM = REGISTRADOR_NULO):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._registrador = registrador

    def gerar(
        self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido"
    ) -> str:
        modelo_real = _MAPA_MODELO_PARA_API_DIRETA.get(modelo, modelo)
        try:
            resposta = self._client.messages.create(
                model=modelo_real, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            self._registrador.registrar(no_origem, modelo, 0, 0, sucesso=False, erro_detalhe=str(exc)[:200])
            raise LLMIndisponivelError(f"API Claude direta indisponível: {exc}") from exc

        texto = _extrair_texto(resposta, "a API Claude direta")
        self._registrador.registrar(
            no_origem, modelo, resposta.usage.input_tokens, resposta.usage.output_tokens, sucesso=True
        )
        return texto


@dataclass
class ClienteLLMFake:
    """Usado apenas em tests/ — nunca gera custo real. Grava cada chamada para
    permitir assertions de segurança (ex: PII nunca chega em texto plano)."""

    respostas_por_modelo: dict[str, str] = field(default_factory=dict)
    chamadas: list[dict] = field(default_factory=list)

    def gerar(
        self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido"
    ) -> str:
        self.chamadas.append(
            {"modelo": modelo, "mensagens": mensagens, "max_tokens": max_tokens, "no_origem": no_origem}
        )
        return self.respostas_por_modelo.get(modelo, "resposta fake")
