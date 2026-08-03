from dataclasses import dataclass, field
from typing import Protocol

MODELO_HAIKU = "claude-haiku-4-5@20251001"
MODELO_SONNET = "claude-sonnet-5"


class LLMIndisponivelError(Exception):
    """Levantada quando a chamada ao Vertex AI falha (rede, auth, timeout, 5xx,
    ou resposta sem bloco de texto). Propaga sem ser capturada pelos nós —
    mesma disciplina de `AliquotaNaoDisponivelError` em `no_deterministico`."""


class ClienteLLM(Protocol):
    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str: ...


class ClienteVertexAI:
    """Real — chama Claude via Vertex AI (Agent Platform). Endpoint `global`
    (Decision 2 do DESIGN): recomendado pela Anthropic, sem premium de preço,
    sem exigir região específica — elimina o conflito com `southamerica-east1`
    (região padrão do resto da infraestrutura deste projeto)."""

    def __init__(self, project_id: str, region: str = "global"):
        from anthropic import AnthropicVertex

        self._client = AnthropicVertex(project_id=project_id, region=region)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        try:
            resposta = self._client.messages.create(
                model=modelo, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            raise LLMIndisponivelError(f"Vertex AI indisponível: {exc}") from exc

        bloco_texto = next((b for b in resposta.content if b.type == "text"), None)
        if bloco_texto is None:
            raise LLMIndisponivelError("Resposta do Vertex AI sem bloco de texto")
        return bloco_texto.text


@dataclass
class ClienteLLMFake:
    """Usado apenas em tests/ — nunca gera custo real. Grava cada chamada para
    permitir assertions de segurança (ex: PII nunca chega em texto plano)."""

    respostas_por_modelo: dict[str, str] = field(default_factory=dict)
    chamadas: list[dict] = field(default_factory=list)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        self.chamadas.append({"modelo": modelo, "mensagens": mensagens, "max_tokens": max_tokens})
        return self.respostas_por_modelo.get(modelo, "resposta fake")
