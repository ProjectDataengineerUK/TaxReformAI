from decimal import Decimal

from pydantic import BaseModel


class PayloadConsulta(BaseModel):
    texto_consulta: str
    ano_operacao: int
    valor_base: Decimal


class TransicaoResposta(BaseModel):
    no: str
    resumo_output: str


class RespostaConsulta(BaseModel):
    parecer_final: str
    valor_liquido: Decimal
    fonte_legal: str
    historico: list[TransicaoResposta]
