from decimal import Decimal

from pydantic import BaseModel, Field


class PayloadConsulta(BaseModel):
    texto_consulta: str = Field(min_length=1)
    ano_operacao: int
    valor_base: Decimal = Field(gt=0)


class TransicaoResposta(BaseModel):
    no: str
    resumo_output: str


class RespostaConsulta(BaseModel):
    parecer_final: str
    valor_liquido: Decimal
    fonte_legal: str
    historico: list[TransicaoResposta]
