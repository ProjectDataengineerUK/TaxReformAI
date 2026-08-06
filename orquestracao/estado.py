from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas_simulate import CompradorTipo, ItemSimulacao, RespostaSimulacao
from ingestion.chunking.chunk_models import Chunk
from motor_calculo.regime_atual import RegimeApuracao


class TransicaoAuditavel(BaseModel):
    no: str
    resumo_input: str
    resumo_output: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class State(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    texto_consulta: str
    ano_operacao: int
    # Derivado da soma de itens (item.valor_unitario * item.quantidade) em
    # api/routers/query.py, nunca mais um campo manual do payload
    # (COMPARATIVO_REGIME_ATUAL_IVA_DUAL, Decision 2/6) — mantido aqui para
    # não tocar extrator_regras.py, que compara o valor extraído do texto
    # livre contra este total.
    valor_base: Decimal
    # Mesmo shape de item que PayloadSimulacao — paridade total de cálculo
    # com /simulador (Anexos de redução, IPI, regime atual por item).
    itens: list[ItemSimulacao] = []
    regime_apuracao: RegimeApuracao | None = None
    comprador_tipo: CompradorTipo | None = None
    # Tenant AUTENTICADO (de verificar_api_key), nunca de um campo do
    # payload — PayloadConsulta não declara tenant_id, diferente de
    # PayloadSimulacao (não há um segundo tenant "declarado" para conferir).
    tenant_id: str = ""

    texto_mascarado: str | None = None
    intencao: str | None = None
    chunks_legais: list[Chunk] = []
    payload_extraido: dict[str, Any] = {}
    # Renomeado de `resultado_calculo: ResultadoCalculo` — reaproveita
    # RespostaSimulacao (o mesmo schema que /simulador já devolve) em vez de
    # uma estrutura paralela, agora que o resultado é itemizado
    # (COMPARATIVO_REGIME_ATUAL_IVA_DUAL, Decision 2).
    resultado_simulacao: RespostaSimulacao | None = None
    parecer_final: str | None = None

    historico: list[TransicaoAuditavel] = []

    def registrar_transicao(self, no: str, resumo_input: str, resumo_output: str) -> None:
        self.historico.append(
            TransicaoAuditavel(no=no, resumo_input=resumo_input, resumo_output=resumo_output)
        )
