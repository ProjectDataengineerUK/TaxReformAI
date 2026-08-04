"""AT-001 a AT-013 do DEFINE (CRUD + upload CSV), via `TestClient` + um pool
fake com armazenamento em memória — diferente das features anteriores (só
leitura), aqui o fake precisa simular INSERT/UPDATE/DELETE/upsert de verdade
para o CRUD fazer sentido, não só devolver linhas canônicas.

`TENANT` é uma string com CARA de UUID (mesma convenção das demais suítes
E2E deste projeto) — `resolver_tenant` resolve pelo caminho `UUID(identifi
cador)` direto, sem nunca consultar `tenants`, então o fake não precisa
simular essa tabela.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app

CHAVE = "chave-teste-empresa-skus"
TENANT = "e59c0413-1d3c-6f4e-aa44-345678901abc"


class FakeUniqueViolation(Exception):
    """Espelha o único contrato que o router de fato observa (`sqlstate` —
    ver api/routers/empresa_skus.py::criar), não o tipo concreto de
    `psycopg.errors.UniqueViolation`."""

    sqlstate = "23505"


class FakeCursor:
    def __init__(self, store: dict, jobs: dict):
        self._store = store
        self._jobs = jobs
        self._resultado: list[tuple] = []
        self._rowcount = 0
        self._tenant_atual: str | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        params = params or ()

        if "set_config" in s:
            self._tenant_atual = params[0]
            self._resultado = [(None,)]
        elif s.startswith("INSERT INTO empresa_skus") and "ON CONFLICT" in s:
            tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code = params
            chave = (tenant_id, codigo_sku)
            foi_criado = chave not in self._store
            antigo = self._store.get(chave)
            linha_id = antigo[0] if antigo else uuid.uuid4()
            created_at = antigo[7] if antigo else datetime.now(UTC)
            linha = (linha_id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at)
            self._store[chave] = linha
            self._resultado = [(*linha, foi_criado)]
        elif s.startswith("INSERT INTO empresa_skus"):
            tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code = params
            chave = (tenant_id, codigo_sku)
            if chave in self._store:
                raise FakeUniqueViolation(f"duplicate key {chave}")
            linha = (uuid.uuid4(), tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, datetime.now(UTC))
            self._store[chave] = linha
            self._resultado = [linha]
        elif s.startswith("SELECT count(*) FROM empresa_skus"):
            total = sum(1 for (t, _c) in self._store if t == self._tenant_atual)
            self._resultado = [(total,)]
        elif "FROM empresa_skus WHERE codigo_sku = ANY" in s:
            codigos = set(params[0])
            self._resultado = [
                linha for (t, c), linha in self._store.items()
                if t == self._tenant_atual and c in codigos
            ]
        elif s.startswith("SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at") and "WHERE codigo_sku = %s" in s:
            codigo_sku = params[0]
            linha = self._store.get((self._tenant_atual, codigo_sku))
            self._resultado = [linha] if linha else []
        elif s.startswith("SELECT id, tenant_id") and "ORDER BY created_at" in s:
            tamanho_pagina, offset = params
            linhas = sorted(
                (linha for (t, _c), linha in self._store.items() if t == self._tenant_atual),
                key=lambda linha: linha[7], reverse=True,
            )
            self._resultado = linhas[offset:offset + tamanho_pagina]
        elif s.startswith("UPDATE empresa_skus"):
            descricao, natureza, ncm_code, nbs_code, codigo_sku = params
            chave = (self._tenant_atual, codigo_sku)
            antigo = self._store.get(chave)
            if antigo is None:
                self._resultado = []
            else:
                nova = (antigo[0], antigo[1], codigo_sku, descricao, natureza, ncm_code, nbs_code, antigo[7])
                self._store[chave] = nova
                self._resultado = [nova]
        elif s.startswith("DELETE FROM empresa_skus"):
            codigo_sku = params[0]
            chave = (self._tenant_atual, codigo_sku)
            if chave in self._store:
                del self._store[chave]
                self._rowcount = 1
            else:
                self._rowcount = 0
        elif s.startswith("INSERT INTO sku_upload_jobs"):
            tenant_id, gcs_uri_arquivo = params
            job_id = uuid.uuid4()
            agora = datetime.now(UTC)
            linha = (job_id, tenant_id, "PENDENTE", gcs_uri_arquivo, None, agora, agora)
            self._jobs[str(job_id)] = linha
            self._resultado = [linha]
        elif s.startswith("SELECT id, tenant_id, status, gcs_uri_arquivo"):
            job_id = params[0]
            linha = self._jobs.get(str(job_id))
            self._resultado = [linha] if linha and linha[1] == self._tenant_atual else []
        elif s.startswith("UPDATE sku_upload_jobs"):
            import json as _json

            novo_status, resultado_json, job_id = params
            antigo = self._jobs.get(str(job_id))
            if antigo is not None:
                resultado_parseado = _json.loads(resultado_json) if resultado_json else None
                self._jobs[str(job_id)] = (
                    antigo[0], antigo[1], novo_status, antigo[3], resultado_parseado, antigo[5], datetime.now(UTC),
                )
        else:
            raise AssertionError(f"SQL não simulado pelo fake: {sql!r}")

    def fetchone(self):
        return self._resultado[0] if self._resultado else None

    def fetchall(self):
        return self._resultado

    @property
    def rowcount(self):
        return self._rowcount


class FakeConexao:
    def __init__(self, store: dict, jobs: dict):
        self._store = store
        self._jobs = jobs

    def cursor(self):
        return FakeCursor(self._store, self._jobs)

    def commit(self):
        pass

    def rollback(self):
        pass


class FakePool:
    def __init__(self):
        self.store: dict = {}
        self.jobs: dict = {}

    @contextmanager
    def connection(self):
        yield FakeConexao(self.store, self.jobs)


@pytest.fixture
def pool():
    return FakePool()


@pytest.fixture
def client(pool, monkeypatch):
    """FILA_ASSINCRONA_CELERY_REDIS: GCS (staging) e Cloud Tasks nunca são
    reais em teste — um dict em memória substitui o bucket, e o disparo da
    task vira um no-op (os testes que precisam do processamento chamam
    `/upload/processar-tarefa` diretamente, simulando o Cloud Tasks). A
    verificação de token OIDC é testada isoladamente em
    tests/test_fila_assincrona.py — aqui ela sempre "passa", para o teste
    focar no fluxo de dados, não na autenticação."""
    staging: dict[str, bytes] = {}

    def _fake_enviar(tenant_id: str, conteudo: bytes) -> str:
        uri = f"gs://fake-bucket/{tenant_id}/{len(staging)}.csv"
        staging[uri] = conteudo
        return uri

    def _fake_baixar(gcs_uri: str) -> bytes:
        return staging[gcs_uri]

    import api.routers.skus_tasks as skus_tasks_router_mod

    monkeypatch.setattr("api.staging_gcs.enviar_para_staging", _fake_enviar)
    monkeypatch.setattr("api.staging_gcs.baixar_do_staging", _fake_baixar)
    monkeypatch.setattr("api.tasks_cloud.criar_task_processamento", lambda job_id, tenant_id: None)
    monkeypatch.setattr(skus_tasks_router_mod, "verificar_token_oidc", lambda _auth: True)

    app.dependency_overrides[get_settings] = lambda: ApiSettings(api_keys_to_tenant={CHAVE: TENANT})
    app.dependency_overrides[get_db_pool] = lambda: pool
    yield TestClient(app)
    app.dependency_overrides.clear()


def _criar(client, codigo_sku="SKU-1", **extra):
    corpo = {
        "tenant_id": TENANT, "codigo_sku": codigo_sku, "descricao": "Produto",
        "natureza": "MERCADORIA", "ncm_code": "22030000",
    }
    corpo.update(extra)
    return client.post("/v1/tax/skus", headers={"X-API-Key": CHAVE}, json=corpo)


def test_tenant_id_divergente_do_payload_e_403(client):
    """Achado do security-reviewer antes do /ship: o router já fazia essa
    checagem (mesmo padrão de api/routers/simulate.py), mas não havia teste
    de regressão dedicado a ela."""
    resposta = _criar(client, tenant_id="outro-tenant-qualquer")
    assert resposta.status_code == 403


# AT-001/AT-002 — criação -------------------------------------------------


def test_at001_criar_sku_mercadoria(client):
    resposta = _criar(client)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["codigo_sku"] == "SKU-1"
    assert corpo["ncm_code"] == "22030000"


def test_at002_criar_sku_servico(client):
    resposta = _criar(client, codigo_sku="SKU-2", natureza="SERVICO", ncm_code=None, nbs_code="122010000")
    assert resposta.status_code == 201
    assert resposta.json()["nbs_code"] == "122010000"


# AT-003/AT-004 — exclusividade --------------------------------------------


def test_at003_ncm_e_nbs_juntos_e_422(client):
    resposta = _criar(client, nbs_code="122010000")
    assert resposta.status_code == 422


def test_at004_nem_ncm_nem_nbs_e_422(client):
    resposta = _criar(client, ncm_code=None)
    assert resposta.status_code == 422


# AT-005 — duplicata ---------------------------------------------------------


def test_at005_duplicata_e_409(client):
    _criar(client)
    resposta = _criar(client)
    assert resposta.status_code == 409


# AT-006 — listagem -----------------------------------------------------------


def test_at006_listagem_paginada(client):
    for i in range(3):
        _criar(client, codigo_sku=f"SKU-{i}")
    resposta = client.get("/v1/tax/skus", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 3
    assert len(corpo["itens"]) == 3


# AT-007 — consulta individual -----------------------------------------------


def test_at007_consultar_sku_inexistente_e_404(client):
    resposta = client.get("/v1/tax/skus/NAO-EXISTE", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 404


def test_consultar_sku_existente(client):
    _criar(client)
    resposta = client.get("/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 200
    assert resposta.json()["codigo_sku"] == "SKU-1"


# AT-008 — edição parcial -----------------------------------------------------


def test_at008_editar_parcial(client):
    _criar(client)
    resposta = client.patch(
        "/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE}, json={"descricao": "Nova descrição"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["descricao"] == "Nova descrição"
    assert corpo["ncm_code"] == "22030000"  # preservado


def test_editar_trocando_natureza_sem_codigo_novo_e_422(client):
    _criar(client)
    resposta = client.patch(
        "/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE}, json={"natureza": "SERVICO"}
    )
    assert resposta.status_code == 422


def test_editar_trocando_natureza_com_codigo_novo(client):
    _criar(client)
    resposta = client.patch(
        "/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE},
        json={"natureza": "SERVICO", "nbs_code": "122010000"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["natureza"] == "SERVICO"
    assert corpo["ncm_code"] is None
    assert corpo["nbs_code"] == "122010000"


# AT-009 — exclusão -------------------------------------------------------


def test_at009_excluir_e_consultar_depois_e_404(client):
    _criar(client)
    resposta = client.delete("/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 204
    resposta = client.get("/v1/tax/skus/SKU-1", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 404


# AT-010/AT-011/AT-012/AT-013 — upload CSV -----------------------------------


def _upload(client, conteudo: str):
    """FILA_ASSINCRONA_CELERY_REDIS: upload SEMPRE assíncrono — devolve só
    `202` + `job_id`. Nunca processa a planilha aqui."""
    return client.post(
        "/v1/tax/skus/upload", headers={"X-API-Key": CHAVE},
        files={"arquivo": ("skus.csv", conteudo, "text/csv")},
    )


def _upload_e_processar(client, conteudo: str):
    """Simula o ciclo completo: POST /upload (enfileira) -> POST
    /upload/processar-tarefa (o que o Cloud Tasks chamaria de verdade,
    aqui disparado diretamente pelo teste) -> GET /upload/{job_id}
    (resultado final). Devolve a resposta do GET, mesmo formato que os
    testes anteriores (síncronos) esperavam, só que agora sob `resultado`."""
    resposta_upload = _upload(client, conteudo)
    assert resposta_upload.status_code == 202
    job_id = resposta_upload.json()["job_id"]

    resposta_tarefa = client.post(
        "/v1/tax/skus/upload/processar-tarefa",
        json={"job_id": job_id, "tenant_id": TENANT},
        headers={"Authorization": "Bearer fake-token-de-teste"},
    )
    assert resposta_tarefa.status_code == 204

    return client.get(f"/v1/tax/skus/upload/{job_id}", headers={"X-API-Key": CHAVE})


def test_at010_upload_csv_valido(client):
    csv = (
        "codigo_sku,descricao,natureza,ncm_code,nbs_code\n"
        "SKU-A,Produto A,MERCADORIA,22030000,\n"
        "SKU-B,Produto B,MERCADORIA,22030000,\n"
        "SKU-C,Serviço C,SERVICO,,122010000\n"
    )
    resposta = _upload_e_processar(client, csv)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["resultado"]["criados"] == 3
    assert corpo["resultado"]["erros"] == 0


def test_at011_upload_csv_upsert(client):
    csv1 = "codigo_sku,descricao,natureza,ncm_code,nbs_code\nSKU-A,Original,MERCADORIA,22030000,\n"
    _upload_e_processar(client, csv1)
    csv2 = "codigo_sku,descricao,natureza,ncm_code,nbs_code\nSKU-A,Atualizado,MERCADORIA,99999999,\n"
    resposta = _upload_e_processar(client, csv2)
    corpo = resposta.json()
    assert corpo["resultado"]["atualizados"] == 1
    assert corpo["resultado"]["criados"] == 0
    assert corpo["resultado"]["resultados"][0]["situacao"] == "ATUALIZADO"


def test_at012_upload_csv_parcialmente_invalido(client):
    csv = (
        "codigo_sku,descricao,natureza,ncm_code,nbs_code\n"
        "SKU-A,Produto A,MERCADORIA,22030000,\n"
        "SKU-B,Produto B,MERCADORIA,22030000,\n"
        "SKU-C,Produto C,MERCADORIA,abc,\n"
    )
    resposta = _upload_e_processar(client, csv)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["resultado"]["criados"] == 2
    assert corpo["resultado"]["erros"] == 1
    assert corpo["resultado"]["resultados"][2]["situacao"] == "ERRO"
    assert corpo["resultado"]["resultados"][2]["motivo"] is not None


def test_upload_devolve_202_com_job_id(client):
    """Contrato novo (FILA_ASSINCRONA_CELERY_REDIS): a resposta imediata do
    POST nunca carrega resultado — só o job_id."""
    csv = "codigo_sku,descricao,natureza,ncm_code,nbs_code\nSKU-A,A,MERCADORIA,22030000,\n"
    resposta = _upload(client, csv)
    assert resposta.status_code == 202
    corpo = resposta.json()
    assert "job_id" in corpo
    assert "criados" not in corpo


def test_job_upload_de_outro_tenant_e_404(client):
    """AT-004 da DEFINE: isolamento de tenant no polling."""
    csv = "codigo_sku,descricao,natureza,ncm_code,nbs_code\nSKU-A,A,MERCADORIA,22030000,\n"
    resposta_upload = _upload(client, csv)
    job_id = resposta_upload.json()["job_id"]

    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={"outra-chave": "11111111-1111-1111-1111-111111111111"}
    )
    resposta = client.get(f"/v1/tax/skus/upload/{job_id}", headers={"X-API-Key": "outra-chave"})
    assert resposta.status_code == 404


def test_job_upload_id_malformado_e_404(client):
    resposta = client.get("/v1/tax/skus/upload/nao-e-um-uuid", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 404


def test_at013_upload_csv_acima_do_teto_e_422(client, monkeypatch):
    import api.routers.empresa_skus as router_mod

    monkeypatch.setattr(router_mod, "TETO_LINHAS_UPLOAD", 2)
    csv = (
        "codigo_sku,descricao,natureza,ncm_code,nbs_code\n"
        "SKU-A,A,MERCADORIA,22030000,\n"
        "SKU-B,B,MERCADORIA,22030000,\n"
        "SKU-C,C,MERCADORIA,22030000,\n"
    )
    resposta = _upload(client, csv)
    assert resposta.status_code == 422


# db_pool indisponível ---------------------------------------------------------


def test_db_pool_none_e_503():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(api_keys_to_tenant={CHAVE: TENANT})
    app.dependency_overrides[get_db_pool] = lambda: None
    try:
        client = TestClient(app)
        resposta = client.get("/v1/tax/skus", headers={"X-API-Key": CHAVE})
        assert resposta.status_code == 503
    finally:
        app.dependency_overrides.clear()
