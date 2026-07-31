"""AT-001 a AT-009 da base de incidência do Imposto Seletivo, via `TestClient`
+ pool fake — mesmo padrão de `test_api_simulate_reducao.py`.

O fake responde exatamente como o driver (tuplas na ordem do SELECT de
`buscar_incidencia_is_por_prefixo`), com domínio de falha SEPARADO das
consultas de IPI/redução NCM/redução NBS — é assim que se prova que uma
tabela sem GRANT aqui nunca afeta CBS/IBS/IPI (Decisão 1 do DESIGN).
"""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app
from tests.test_imposto_seletivo import SEED

CHAVE = "chave-teste-imposto-seletivo"
TENANT = "e59c0413-1d3c-6f4e-aa44-345678901cde"


class FakeCursor:
    def __init__(self, espiao):
        self._espiao = espiao
        self._linhas: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        if "imposto_seletivo_incidencia_ncm" in sql:
            self._espiao.queries_is.append((sql, params))
            candidatos = set(params[0])
            self._linhas = [
                (
                    linha.inciso,
                    linha.categoria,
                    linha.dispositivo_legal_ref,
                    linha.condicao_embalagem_primaria_ref,
                    linha.excecao_uso_ref,
                    linha.prefixo,
                    linha.excecao,
                    linha.texto_ncm,
                )
                for linha in SEED
                if linha.prefixo in candidatos
            ]
        elif "anexos_reducao_ncm" in sql or "aliquotas_ipi_tipi" in sql or "anexos_reducao_nbs_prefixo" in sql:
            self._linhas = []
        else:
            self._linhas = [(uuid4(),)]

    def fetchall(self):
        return self._linhas

    def fetchone(self):
        return self._linhas[0] if self._linhas else None


class FakeConexao:
    def __init__(self, espiao):
        self._espiao = espiao

    def cursor(self):
        return FakeCursor(self._espiao)

    def commit(self):
        pass

    def rollback(self):
        pass


class FakePool:
    def __init__(self):
        self.queries_is: list[tuple] = []

    @contextmanager
    def connection(self):
        yield FakeConexao(self)


@pytest.fixture
def pool():
    return FakePool()


@pytest.fixture
def client(pool):
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: pool
    yield TestClient(app)
    app.dependency_overrides.clear()


def _item(sku="P-1", ncm="04051000", valor="1000.00", **extra):
    item = {
        "sku": sku,
        "ncm": ncm,
        "quantidade": 1,
        "valor_unitario": valor,
        "uf_origem": "SP",
        "uf_destino": "SP",
        "natureza": "MERCADORIA",
    }
    item.update(extra)
    return item


def _simular(client, itens, ano=2026):
    corpo = {
        "tenant_id": TENANT,
        "ano_operacao": ano,
        "operacao_tipo": "VENDA",
        "itens": itens,
    }
    return client.post("/v1/tax/simulate", headers={"X-API-Key": CHAVE}, json=corpo)


# AT-001 — veículo sujeito ao IS ----------------------------------------------


def test_at001_veiculo_e_sujeito_ao_is(client):
    resposta = _simular(client, [_item(ncm="87042110")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    imposto = corpo["itens_detalhados"][0]["imposto_seletivo"]

    assert imposto["situacao"] == "SUJEITO"
    assert imposto["categoria"] == "Veículos"
    assert imposto["dispositivo_legal_ref"] == "LCP 214/2025, art. 409, §1º, I, Anexo XVII"
    assert imposto["excecao_uso_ref"] is not None
    # Nenhuma chave de valor/percentual existe no bloco (Decisão 1 do DESIGN).
    assert set(imposto.keys()) == {
        "situacao",
        "categoria",
        "dispositivo_legal_ref",
        "condicao_embalagem_primaria_ref",
        "excecao_uso_ref",
    }


# AT-003 — fumígeno, condição de embalagem primária ---------------------------


def test_at003_fumigeno_sem_embalagem_fica_condicao_nao_satisfeita(client):
    resposta = _simular(client, [_item(ncm="24022000")])
    imposto = resposta.json()["itens_detalhados"][0]["imposto_seletivo"]

    assert imposto["situacao"] == "CONDICAO_NAO_SATISFEITA"
    assert imposto["condicao_embalagem_primaria_ref"] is not None


def test_at003_fumigeno_com_embalagem_confirmada_e_sujeito(client):
    resposta = _simular(
        client, [_item(ncm="24022000", embalagem_primaria_consumidor_final=True)]
    )
    imposto = resposta.json()["itens_detalhados"][0]["imposto_seletivo"]
    assert imposto["situacao"] == "SUJEITO"


# AT-005 — fora da base --------------------------------------------------------


def test_at005_manteiga_fora_da_base_do_is(client):
    resposta = _simular(client, [_item(ncm="04051000")])
    imposto = resposta.json()["itens_detalhados"][0]["imposto_seletivo"]
    assert imposto["situacao"] == "NAO_SUJEITO"
    assert imposto["categoria"] is None


# Exceção de código — 8802.60.00 ----------------------------------------------


def test_aeronave_excluida_por_codigo_e_nao_sujeita(client):
    resposta = _simular(client, [_item(ncm="88026000")])
    imposto = resposta.json()["itens_detalhados"][0]["imposto_seletivo"]
    assert imposto["situacao"] == "NAO_SUJEITO"


# AT-008 — nenhum valor de IS é produzido -------------------------------------


def test_at008_total_is_nunca_e_afetado_pela_classificacao(client):
    corpo = _simular(client, [_item(ncm="87042110")]).json()
    # 2026 é TESTE_2026, aliq_is=0 na fase — inalterado por esta feature.
    assert corpo["resumo_financeiro"]["total_is"] == "0.00"


# AT-009 — zero regressão, payload de serviço ---------------------------------


def test_item_de_servico_recebe_nao_aplicavel(client):
    resposta = _simular(
        client,
        [
            {
                "sku": "S-1",
                "ncm": "00000000",
                "natureza": "SERVICO",
                "quantidade": 1,
                "valor_unitario": "100.00",
                "uf_origem": "SP",
                "uf_destino": "SP",
            }
        ],
    )
    imposto = resposta.json()["itens_detalhados"][0]["imposto_seletivo"]
    assert imposto["situacao"] == "NAO_APLICAVEL"


def test_consulta_do_is_e_separada_da_consulta_de_reducao(client, pool):
    _simular(client, [_item(ncm="87042110")])
    assert len(pool.queries_is) == 1
