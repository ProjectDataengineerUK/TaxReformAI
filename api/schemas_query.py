from pydantic import BaseModel, Field

from api.schemas_simulate import CompradorTipo, ItemSimulacao, RespostaSimulacao
from motor_calculo.regime_atual import RegimeApuracao


class PayloadConsulta(BaseModel):
    texto_consulta: str = Field(min_length=1)
    ano_operacao: int
    # Mesmo shape de item que PayloadSimulacao (não um valor_base agregado
    # manual, removido nesta feature) — paridade total de cálculo com
    # /simulador, incluindo Anexos de redução e IPI por item
    # (COMPARATIVO_REGIME_ATUAL_IVA_DUAL, Decision 6). Mudança BREAKING:
    # quem chamava /v1/tax/query com valor_base direto precisa migrar para
    # itens (Assumption A-001 do DEFINE — sem cliente externo conhecido
    # além do próprio frontend do projeto).
    itens: list[ItemSimulacao] = Field(min_length=1, max_length=100)
    regime_apuracao: RegimeApuracao | None = None
    comprador_tipo: CompradorTipo | None = None


class TransicaoResposta(BaseModel):
    no: str
    resumo_output: str


class RespostaConsulta(BaseModel):
    parecer_final: str
    # Compõe o MESMO schema que /simulador devolve, em vez de duplicar
    # valor_liquido/fonte_legal como campos top-level próprios — o
    # componente de frontend ComparativoRegime.tsx serve as duas telas sem
    # adaptação de shape (Decision 6/8).
    resultado_simulacao: RespostaSimulacao
    historico: list[TransicaoResposta]
