from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from api.empresa_skus import validar_exclusividade
from api.nbs import digitos_nbs
from api.ncm import digitos_ncm

# Achado do security-reviewer antes do /ship: a rota de upload CSV já
# normalizava/validava ncm_code/nbs_code via parsear_linha_csv, mas o
# CRUD individual (POST/PATCH) aceitava qualquer string — um código
# malformado ficaria gravado, degradando em silêncio a resolução de
# /v1/tax/simulate mais tarde (contradiz "nunca estimar/nunca falhar em
# silêncio"). Os dois validators abaixo fecham essa lacuna: mesma
# canonização (8/9 dígitos) que o resto do projeto usa para NCM/NBS.


def _normalizar_ncm(v: str | None) -> str | None:
    if v is None:
        return None
    codigo = digitos_ncm(v)
    if codigo is None:
        raise ValueError(f"ncm_code {v!r} não tem 8 dígitos válidos")
    return codigo


def _normalizar_nbs(v: str | None) -> str | None:
    if v is None:
        return None
    codigo = digitos_nbs(v)
    if codigo is None:
        raise ValueError(f"nbs_code {v!r} não tem 9 dígitos válidos (classificador de topo '1')")
    return codigo


class NaturezaSku(StrEnum):
    MERCADORIA = "MERCADORIA"
    SERVICO = "SERVICO"


class PayloadCriarSku(BaseModel):
    tenant_id: str
    codigo_sku: str = Field(min_length=1, max_length=64)
    descricao: str = Field(min_length=1, max_length=500)
    natureza: NaturezaSku
    ncm_code: str | None = None
    nbs_code: str | None = None

    _norm_ncm = field_validator("ncm_code")(_normalizar_ncm)
    _norm_nbs = field_validator("nbs_code")(_normalizar_nbs)

    @model_validator(mode="after")
    def _exclusividade(self) -> "PayloadCriarSku":
        erro = validar_exclusividade(self.natureza.value, self.ncm_code, self.nbs_code)
        if erro:
            raise ValueError(erro)
        return self


class PayloadAtualizarSku(BaseModel):
    """Todos os campos opcionais (PATCH parcial) — o router funde os campos
    informados sobre o registro existente e revalida a exclusividade com o
    resultado final, nunca campo a campo isoladamente."""

    descricao: str | None = Field(default=None, min_length=1, max_length=500)
    natureza: NaturezaSku | None = None
    ncm_code: str | None = None
    nbs_code: str | None = None

    _norm_ncm = field_validator("ncm_code")(_normalizar_ncm)
    _norm_nbs = field_validator("nbs_code")(_normalizar_nbs)


class RespostaSku(BaseModel):
    id: str
    codigo_sku: str
    descricao: str
    natureza: str
    ncm_code: str | None
    nbs_code: str | None
    created_at: datetime


class RespostaListaSkus(BaseModel):
    itens: list[RespostaSku]
    total: int
    pagina: int
    tamanho_pagina: int


class LinhaUploadResultado(BaseModel):
    numero_linha: int
    codigo_sku: str | None
    situacao: str  # CRIADO | ATUALIZADO | ERRO
    motivo: str | None = None


class RespostaUploadCsv(BaseModel):
    total_linhas: int
    criados: int
    atualizados: int
    erros: int
    resultados: list[LinhaUploadResultado]


class RespostaJobCriado(BaseModel):
    """Resposta síncrona de `POST /upload` — sempre imediata, nunca carrega
    resultado (FILA_ASSINCRONA_CELERY_REDIS: upload sempre assíncrono)."""

    job_id: str
    status: str = "PENDENTE"


class RespostaJobStatus(BaseModel):
    """Resposta de `GET /upload/{job_id}` — `resultado` só preenchido quando
    `status` já é CONCLUIDO ou ERRO."""

    job_id: str
    status: str
    resultado: RespostaUploadCsv | None = None
