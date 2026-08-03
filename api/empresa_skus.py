"""Resolução de SKU->NCM/NBS sem nunca derrubar /v1/tax/simulate, mesma
disciplina de api/ipi.py. `db_pool is None` aqui É indisponibilidade (nunca
"não cadastrado") — ver Decisão 2 do DESIGN_API_EMPRESA_SKUS.md.

Também concentra a validação de exclusividade natureza/ncm_code/nbs_code e o
parsing de linha de CSV, reaproveitados pelo CRUD (schemas) e pelo upload em
lote — uma única fonte da regra, nunca duplicada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.nbs import digitos_nbs
from api.ncm import digitos_ncm

logger = logging.getLogger("api.empresa_skus")


class SituacaoResolucaoSku(StrEnum):
    NAO_NECESSARIO = "NAO_NECESSARIO"
    RESOLVIDO_CATALOGO = "RESOLVIDO_CATALOGO"
    NAO_CADASTRADO = "NAO_CADASTRADO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"


@dataclass(frozen=True)
class ConsultaSkus:
    disponivel: bool
    por_codigo: dict[str, Any] = field(default_factory=dict)


def consultar_skus_com_seguranca(
    pool: Any, tenant_identificador: str, codigos_sku: list[str]
) -> ConsultaSkus:
    if pool is None:
        return ConsultaSkus(disponivel=False)
    if not codigos_sku:
        return ConsultaSkus(disponivel=True)
    try:
        from db.repositorio import buscar_skus_por_codigo, resolver_tenant

        with pool.connection() as conexao:
            tenant_id = resolver_tenant(conexao, tenant_identificador)
            if tenant_id is None:
                return ConsultaSkus(disponivel=False)
            return ConsultaSkus(
                disponivel=True,
                por_codigo=buscar_skus_por_codigo(conexao, tenant_id, codigos_sku),
            )
    except Exception:
        logger.exception("Falha ao consultar catálogo de SKUs — declarado na resposta")
        return ConsultaSkus(disponivel=False)


@dataclass(frozen=True)
class ResolucaoSku:
    situacao: SituacaoResolucaoSku
    ncm_efetivo: str | None
    nbs_efetivo: str | None


def resolver_ncm_nbs_do_item(
    natureza: str,
    ncm_payload: str | None,
    nbs_payload: str | None,
    sku: str,
    consulta: ConsultaSkus,
) -> ResolucaoSku:
    """Explícito SEMPRE vence — o catálogo só preenche quando ambos vierem
    ausentes (decisão herdada do /brainstorm, reafirmada no /define)."""
    if (natureza == "MERCADORIA" and ncm_payload) or (natureza == "SERVICO" and nbs_payload):
        return ResolucaoSku(SituacaoResolucaoSku.NAO_NECESSARIO, ncm_payload, nbs_payload)

    if not consulta.disponivel:
        return ResolucaoSku(SituacaoResolucaoSku.CONSULTA_INDISPONIVEL, ncm_payload, nbs_payload)

    registro = consulta.por_codigo.get(sku)
    if registro is None:
        return ResolucaoSku(SituacaoResolucaoSku.NAO_CADASTRADO, ncm_payload, nbs_payload)

    return ResolucaoSku(
        SituacaoResolucaoSku.RESOLVIDO_CATALOGO,
        ncm_payload or registro.ncm_code,
        nbs_payload or registro.nbs_code,
    )


def validar_exclusividade(natureza: str, ncm_code: str | None, nbs_code: str | None) -> str | None:
    """Devolve a mensagem de erro, ou None se válido. Reaproveitada pelo schema
    Pydantic (criação/edição) E pelo parser de CSV (linha a linha) — uma única
    fonte da regra, nunca duplicada."""
    if natureza == "MERCADORIA":
        if not ncm_code or nbs_code:
            return "natureza=MERCADORIA exige ncm_code preenchido e nbs_code ausente"
    elif natureza == "SERVICO":
        if not nbs_code or ncm_code:
            return "natureza=SERVICO exige nbs_code preenchido e ncm_code ausente"
    return None


@dataclass(frozen=True)
class LinhaCsvValidada:
    numero_linha: int
    codigo_sku: str | None
    descricao: str | None
    natureza: str | None
    ncm_code: str | None
    nbs_code: str | None
    erro: str | None


def parsear_linha_csv(numero_linha: int, linha: dict[str, str]) -> LinhaCsvValidada:
    codigo_sku = (linha.get("codigo_sku") or "").strip()
    descricao = (linha.get("descricao") or "").strip()
    natureza = (linha.get("natureza") or "").strip().upper()
    ncm_bruto = (linha.get("ncm_code") or "").strip()
    nbs_bruto = (linha.get("nbs_code") or "").strip()

    if not codigo_sku or not descricao:
        return LinhaCsvValidada(
            numero_linha, codigo_sku or None, None, None, None, None,
            "codigo_sku e descricao são obrigatórios",
        )
    if natureza not in ("MERCADORIA", "SERVICO"):
        return LinhaCsvValidada(
            numero_linha, codigo_sku, descricao, None, None, None,
            "natureza deve ser MERCADORIA ou SERVICO",
        )

    ncm_code = digitos_ncm(ncm_bruto) if ncm_bruto else None
    nbs_code = digitos_nbs(nbs_bruto) if nbs_bruto else None
    if ncm_bruto and ncm_code is None:
        return LinhaCsvValidada(
            numero_linha, codigo_sku, descricao, natureza, None, None,
            f"ncm_code {ncm_bruto!r} não tem 8 dígitos válidos",
        )
    if nbs_bruto and nbs_code is None:
        return LinhaCsvValidada(
            numero_linha, codigo_sku, descricao, natureza, None, None,
            f"nbs_code {nbs_bruto!r} inválido",
        )

    erro = validar_exclusividade(natureza, ncm_code, nbs_code)
    if erro:
        return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, ncm_code, nbs_code, erro)

    return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, ncm_code, nbs_code, None)
