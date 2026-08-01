from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class AtividadeSimplesNacional(StrEnum):
    COMERCIO = "COMERCIO"
    INDUSTRIA = "INDUSTRIA"
    LOCACAO_SERVICO_GERAL = "LOCACAO_SERVICO_GERAL"
    SERVICO_PAR_5C = "SERVICO_PAR_5C"
    SERVICO_PAR_5I = "SERVICO_PAR_5I"
    MEI = "MEI"


class PayloadSimplesNacional(BaseModel):
    tenant_id: str
    ano_operacao: int
    atividade: AtividadeSimplesNacional
    # Obrigatória para toda atividade exceto MEI (validado no router, não no
    # schema — Pydantic não expressa "obrigatório condicional a outro campo"
    # sem um validator; a mensagem de erro do router é mais específica que a
    # de um validator genérico).
    receita_bruta_acumulada_12_meses: Decimal | None = Field(default=None, gt=0)
    receita_bruta_mes: Decimal = Field(gt=0)


class ItemPartilhaSimplesNacional(BaseModel):
    tributo: str  # "IRPJ" | "CSLL" | "CBS" | "CPP" | "ICMS" | "ISS" | "IBS" | "IPI"
    # None só para MEI, que não tem alíquota — o valor devido é fixo.
    percentual_efetivo: Decimal | None = None
    valor_devido: Decimal


class RespostaSimplesNacional(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    atividade: str
    faixa: int | None = None
    receita_bruta_acumulada_12_meses: Decimal | None = None
    receita_bruta_mes: Decimal
    aliquota_nominal: Decimal | None = None
    valor_deduzir: Decimal | None = None
    aliquota_efetiva: Decimal | None = None
    partilha: list[ItemPartilhaSimplesNacional]
    valor_total_das: Decimal
    teto_iss_aplicado: bool
    # True só na 6ª Faixa: LC 123/2006, art. 19, §4º — acima do sublimite de
    # R$3.600.000,00, ICMS/ISS (e o IBS que os substitui na reforma) são
    # recolhidos SEPARADAMENTE, fora do DAS, pelo regime geral.
    icms_iss_fora_do_das: bool
    dispositivo_legal_ref: str
    nota: str = (
        "O Simples Nacional é um regime SUBSTITUTIVO — este DAS unificado "
        "substitui IRPJ/CSLL/CBS/CPP/ICMS-ou-ISS/IBS, nunca se soma a eles. "
        "A opção pelo Simples e a atividade informada são DECLARATÓRIAS: "
        "esta simulação não verifica elegibilidade (atividade permitida, "
        "sublimites, impedimentos dos arts. 3º/17 da LC 123/2006)."
    )
