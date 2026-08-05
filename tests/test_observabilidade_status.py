"""As 7 regras de status (Decision 1 do DESIGN_PAINEL_OBSERVABILIDADE.md) —
cada uma testada isoladamente, com fakes, sem Cloud SQL/Qdrant reais."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from observabilidade.status import (
    NIVEL_AMARELO,
    NIVEL_VERDE,
    NIVEL_VERMELHO,
    status_anthropic,
    status_cloud_sql,
    status_cloud_tasks,
    status_frontend,
    status_qdrant,
    status_sync_bigquery,
)


class FakeCursor:
    def __init__(self, respostas: list):
        self._respostas = list(respostas)
        self._ultima: list = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self._ultima = self._respostas.pop(0) if self._respostas else []

    def fetchone(self):
        return self._ultima[0] if self._ultima else None

    def fetchall(self):
        return self._ultima


class FakeConexao:
    def __init__(self, respostas: list):
        self._respostas = respostas

    def cursor(self):
        return FakeCursor(self._respostas)


# --- status_frontend ---


def test_frontend_verde_quando_200(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: httpx.Response(200, request=httpx.Request("GET", "x")))
    resultado = status_frontend("https://frontend.exemplo")
    assert resultado.nivel == NIVEL_VERDE


def test_frontend_amarelo_sem_url_configurada():
    resultado = status_frontend(None)
    assert resultado.nivel == NIVEL_AMARELO


def test_frontend_vermelho_quando_inacessivel(monkeypatch):
    def _explode(*_a, **_k):
        raise httpx.ConnectError("recusado")

    monkeypatch.setattr(httpx, "get", _explode)
    resultado = status_frontend("https://frontend.exemplo")
    assert resultado.nivel == NIVEL_VERMELHO


# --- status_cloud_sql ---


def test_cloud_sql_verde_uso_baixo():
    conexao = FakeConexao(respostas=[[(10,)], [("100",)]])
    resultado = status_cloud_sql(conexao)
    assert resultado.nivel == NIVEL_VERDE


def test_cloud_sql_amarelo_no_limiar_de_70_por_cento():
    conexao = FakeConexao(respostas=[[(70,)], [("100",)]])
    resultado = status_cloud_sql(conexao)
    assert resultado.nivel == NIVEL_AMARELO


def test_cloud_sql_vermelho_no_limiar_de_90_por_cento():
    conexao = FakeConexao(respostas=[[(90,)], [("100",)]])
    resultado = status_cloud_sql(conexao)
    assert resultado.nivel == NIVEL_VERMELHO


# --- status_qdrant ---


def test_qdrant_verde_quando_200(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: httpx.Response(200, request=httpx.Request("GET", "x")))
    resultado = status_qdrant("https://qdrant.exemplo", "chave", "legislacao_tributaria")
    assert resultado.nivel == NIVEL_VERDE


def test_qdrant_amarelo_sem_url_configurada():
    resultado = status_qdrant(None, None, "legislacao_tributaria")
    assert resultado.nivel == NIVEL_AMARELO


def test_qdrant_vermelho_quando_inacessivel(monkeypatch):
    def _explode(*_a, **_k):
        raise httpx.ConnectError("recusado")

    monkeypatch.setattr(httpx, "get", _explode)
    resultado = status_qdrant("https://qdrant.exemplo", "chave", "legislacao_tributaria")
    assert resultado.nivel == NIVEL_VERMELHO


# --- status_anthropic ---


def test_anthropic_verde_sem_falhas():
    conexao = FakeConexao(respostas=[[(True,), (True,), (True,)]])
    resultado = status_anthropic(conexao)
    assert resultado.nivel == NIVEL_VERDE


def test_anthropic_amarelo_sem_chamadas_registradas():
    conexao = FakeConexao(respostas=[[]])
    resultado = status_anthropic(conexao)
    assert resultado.nivel == NIVEL_AMARELO


def test_anthropic_vermelho_com_falhas_em_sequencia():
    conexao = FakeConexao(respostas=[[(False,), (False,), (False,), (True,)]])
    resultado = status_anthropic(conexao)
    assert resultado.nivel == NIVEL_VERMELHO


# --- status_cloud_tasks ---


def test_cloud_tasks_verde_fila_vazia(monkeypatch):
    tenant_id = uuid4()
    conexao = FakeConexao(respostas=[[(tenant_id,)]])

    @contextmanager
    def fake_sessao(_conexao, _tenant_id):
        yield FakeCursor([[]])

    monkeypatch.setattr("observabilidade.status.sessao_do_tenant", fake_sessao)

    resultado = status_cloud_tasks(conexao)
    assert resultado.nivel == NIVEL_VERDE


def test_cloud_tasks_vermelho_job_preso(monkeypatch):
    tenant_id = uuid4()
    conexao = FakeConexao(respostas=[[(tenant_id,)]])
    criado_em = datetime.now(UTC) - timedelta(minutes=30)

    @contextmanager
    def fake_sessao(_conexao, _tenant_id):
        yield FakeCursor([[(criado_em,)]])

    monkeypatch.setattr("observabilidade.status.sessao_do_tenant", fake_sessao)

    resultado = status_cloud_tasks(conexao)
    assert resultado.nivel == NIVEL_VERMELHO


# --- status_sync_bigquery ---


def test_sync_bigquery_amarelo_nunca_rodou():
    conexao = FakeConexao(respostas=[[]])
    resultado = status_sync_bigquery(conexao)
    assert resultado.nivel == NIVEL_AMARELO


def test_sync_bigquery_vermelho_ultima_execucao_falhou():
    conexao = FakeConexao(
        respostas=[[(datetime.now(UTC), False, "erro de conexão")]]
    )
    resultado = status_sync_bigquery(conexao)
    assert resultado.nivel == NIVEL_VERMELHO


def test_sync_bigquery_verde_execucao_recente_com_sucesso():
    conexao = FakeConexao(respostas=[[(datetime.now(UTC), True, "82 linhas")]])
    resultado = status_sync_bigquery(conexao)
    assert resultado.nivel == NIVEL_VERDE


def test_sync_bigquery_amarelo_atrasado():
    executado_em = datetime.now(UTC) - timedelta(hours=40)
    conexao = FakeConexao(respostas=[[(executado_em, True, "82 linhas")]])
    resultado = status_sync_bigquery(conexao)
    assert resultado.nivel == NIVEL_AMARELO
