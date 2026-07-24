from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ingestion.chunking.chunk_models import Chunk
from motor_calculo.engine import ResultadoCalculo


class TransicaoAuditavel(BaseModel):
    no: str
    resumo_input: str
    resumo_output: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class State(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    texto_consulta: str
    ano_operacao: int
    valor_base: Decimal

    texto_mascarado: str | None = None
    intencao: str | None = None
    chunks_legais: list[Chunk] = []
    payload_extraido: dict[str, Any] = {}
    resultado_calculo: ResultadoCalculo | None = None
    parecer_final: str | None = None

    historico: list[TransicaoAuditavel] = []

    def registrar_transicao(self, no: str, resumo_input: str, resumo_output: str) -> None:
        self.historico.append(
            TransicaoAuditavel(no=no, resumo_input=resumo_input, resumo_output=resumo_output)
        )
