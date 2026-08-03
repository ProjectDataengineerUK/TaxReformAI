"""AT-014 a AT-017 do DEFINE_API_EMPRESA_SKUS.md — wiring de `/v1/tax/simulate`
com o catálogo `empresa_skus`. Mesmo padrão de `test_api_simulate_imposto_
seletivo.py`: `TestClient` + pool fake, domínio de falha isolado por tabela.
"""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app

CHAVE = "chave-teste-sku-resolution"
TENANT = "a19c0413-1d3c-6f4e-aa44-345678901fed"

# codigo_sku -> (ncm_code, nbs_code, natureza)
CATALOGO = {
    "SKU-CADASTRADO": ("22030000", None, "MERCADORIA"),
}


class FakeCursor:
    def __init__(self):
        self._linhas: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        if "empresa_skus" in sql and "ANY" in sql:
            codigos = set(params[0])
            self._linhas = [
                (uuid4(), TENANT, codigo, "Produto cadastrado", natureza, ncm, nbs, "2026-01-01")
                for codigo, (ncm, nbs, natureza) in CATALOGO.items()
                if codigo in codigos
            ]
        elif any(
            tabela in sql
            for tabela in (
                "anexos_reducao_ncm", "aliquotas_ipi_tipi", "anexos_reducao_nbs_prefixo",
                "imposto_seletivo_incidencia_ncm",
            )
        ):
            self._linhas = []
        else:
            self._linhas = [(uuid4(),)]

    def fetchall(self):
        return self._linhas

    def fetchone(self):
        return self._linhas[0] if self._linhas else None


class FakeConexao:
    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def rollback(self):
        pass


class FakePool:
    @contextmanager
    def connection(self):
        yield FakeConexao()


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: ApiSettings(api_keys_to_tenant={CHAVE: TENANT})
    app.dependency_overrides[get_db_pool] = FakePool
    yield TestClient(app)
    app.dependency_overrides.clear()


def _item(sku, **extra):
    item = {
        "sku": sku, "quantidade": 1, "valor_unitario": "1000.00",
        "uf_origem": "SP", "uf_destino": "SP", "natureza": "MERCADORIA",
    }
    item.update(extra)
    return item


def _simular(client, itens, ano=2026):
    corpo = {"tenant_id": TENANT, "ano_operacao": ano, "operacao_tipo": "VENDA", "itens": itens}
    return client.post("/v1/tax/simulate", headers={"X-API-Key": CHAVE}, json=corpo)


# AT-014 — resolve do catálogo -------------------------------------------------


def test_at014_resolve_ncm_do_catalogo_quando_ausente(client):
    resposta = _simular(client, [_item("SKU-CADASTRADO")])
    assert resposta.status_code == 200
    item_detalhado = resposta.json()["itens_detalhados"][0]
    assert item_detalhado["ncm"] == "22030000"
    assert item_detalhado["sku_resolvido_do_catalogo"] is True


# AT-015 — explícito sempre vence -----------------------------------------------


def test_at015_ncm_explicito_vence_sobre_catalogo(client):
    resposta = _simular(client, [_item("SKU-CADASTRADO", ncm="99999999")])
    assert resposta.status_code == 200
    item_detalhado = resposta.json()["itens_detalhados"][0]
    assert item_detalhado["ncm"] == "99999999"
    assert item_detalhado["sku_resolvido_do_catalogo"] is False


# AT-016 — SKU não cadastrado, sem ncm ------------------------------------------


def test_at016_sku_nao_cadastrado_sem_ncm_e_422(client):
    resposta = _simular(client, [_item("SKU-DESCONHECIDO")])
    assert resposta.status_code == 422
    assert "não cadastrado" in resposta.json()["detail"]


# AT-017 — zero regressão --------------------------------------------------------


def test_at017_payload_com_ncm_explicito_nao_consulta_catalogo(client):
    resposta = _simular(client, [_item("QUALQUER-SKU", ncm="22030000")])
    assert resposta.status_code == 200
    item_detalhado = resposta.json()["itens_detalhados"][0]
    assert item_detalhado["ncm"] == "22030000"
    assert item_detalhado["sku_resolvido_do_catalogo"] is False


def test_item_de_servico_sem_nbs_continua_sem_erro(client):
    """Preserva o comportamento pré-feature: nbs ausente em item de serviço
    NUNCA foi erro (resolver_item_nbs trata como NAO_APLICAVEL) — só ncm
    ausente em MERCADORIA é bloqueante (Decisão herdada do /build)."""
    resposta = _simular(
        client,
        [
            {
                "sku": "SERVICO-QUALQUER", "quantidade": 1, "valor_unitario": "100.00",
                "uf_origem": "SP", "uf_destino": "SP", "natureza": "SERVICO",
            }
        ],
    )
    assert resposta.status_code == 200
