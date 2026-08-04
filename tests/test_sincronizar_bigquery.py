"""Testes puros de scripts/sincronizar_bigquery.py — conversão de linha e
lógica de watermark, sem Cloud SQL nem BigQuery reais (esses só via
workflow_dispatch de sincronizar_bigquery.yml, mesma disciplina de todo
outro script de infraestrutura real deste projeto)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

pytest.importorskip("google.cloud.bigquery", reason="google-cloud-bigquery não instalado")

from scripts.sincronizar_bigquery import EPOCA, linha_para_bigquery, watermark_atual


def test_linha_para_bigquery_converte_uuids_para_string():
    id_ = uuid4()
    tenant_id = uuid4()
    user_id = uuid4()
    created_at = datetime(2026, 8, 4, 12, 0, 0, tzinfo=UTC)
    row = (id_, tenant_id, user_id, "texto", ["a", "b"], {"k": "v"}, "parecer", created_at)

    resultado = linha_para_bigquery(row)

    assert resultado["id"] == str(id_)
    assert resultado["tenant_id"] == str(tenant_id)
    assert resultado["user_id"] == str(user_id)
    assert resultado["created_at"] == created_at.isoformat()


def test_linha_para_bigquery_user_id_nulo_preservado():
    row = (
        uuid4(),
        uuid4(),
        None,
        "texto",
        [],
        {},
        "parecer",
        datetime(2026, 8, 4, tzinfo=UTC),
    )

    resultado = linha_para_bigquery(row)

    assert resultado["user_id"] is None


def test_linha_para_bigquery_preserva_json_como_objeto_nativo():
    row = (
        uuid4(),
        uuid4(),
        None,
        "texto",
        ["ctx1", "ctx2"],
        {"ncm": "12345678", "valor": "100.00"},
        "parecer",
        datetime(2026, 8, 4, tzinfo=UTC),
    )

    resultado = linha_para_bigquery(row)

    assert resultado["contexto_recuperado_ids"] == ["ctx1", "ctx2"]
    assert resultado["payload_calculo_json"] == {"ncm": "12345678", "valor": "100.00"}


class _LinhaFake:
    def __init__(self, wm):
        self.wm = wm


class _ResultadoFake:
    def __init__(self, wm):
        self._wm = wm

    def result(self):
        return [_LinhaFake(self._wm)]


class _ClienteFake:
    def __init__(self, wm):
        self._wm = wm

    def query(self, _query):
        return _ResultadoFake(self._wm)


def test_watermark_atual_usa_epoca_quando_tabela_vazia():
    cliente = _ClienteFake(wm=None)

    assert watermark_atual(cliente, "projeto-teste") == EPOCA


def test_watermark_atual_usa_max_created_at_quando_existente():
    esperado = datetime(2026, 8, 1, tzinfo=UTC)
    cliente = _ClienteFake(wm=esperado)

    assert watermark_atual(cliente, "projeto-teste") == esperado
