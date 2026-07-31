"""AT-001, AT-005, AT-010, AT-011, AT-013, AT-014, AT-015 dos Anexos por NBS,
via `TestClient` + pool fake — mesmo padrão de `test_api_simulate_reducao.py`.

O fake responde exatamente como o driver (tuplas na ordem do SELECT de
`buscar_reducao_nbs_por_prefixo`), com os dois lookups (NCM e NBS) em
consultas SEPARADAS — é assim que se prova que os dois vocabulários nunca se
misturam (Achado crítico 4 do /define), e que a falha de um nunca contamina
o outro.
"""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app
from tests.test_reducao_nbs import SEED as SEED_NBS
from tests.test_reducao_resolucao import SEED as SEED_NCM

CHAVE = "chave-teste-reducao-nbs"
TENANT = "d48b9392-0c2b-5e3d-9933-234567890bcd"


class FakeCursor:
    def __init__(self, espiao):
        self._espiao = espiao
        self._linhas: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        if "anexos_reducao_nbs_prefixo" in sql:
            self._espiao.queries_nbs.append((sql, params))
            candidatos = set(params[0])
            self._linhas = [
                (
                    linha.anexo,
                    linha.anexo_ordem,
                    linha.percentual_reducao,
                    linha.item,
                    linha.sub_item,
                    linha.prefixo,
                    linha.texto_nbs,
                    linha.descricao,
                    linha.descricao_contexto,
                    linha.dispositivo_legal_ref,
                    linha.condicao_nacionalidade_ref,
                    linha.condicao_comprador_ref,
                    linha.condicao_vendedor_ref,
                )
                for linha in SEED_NBS
                if linha.prefixo in candidatos
            ]
        elif "anexos_reducao_ncm" in sql:
            self._espiao.queries_ncm.append((sql, params))
            candidatos = set(params[0])
            self._linhas = [
                (
                    linha.anexo,
                    linha.anexo_ordem,
                    linha.percentual_reducao,
                    linha.zero_por_comprador_ref,
                    linha.item,
                    linha.sub_item,
                    linha.prefixo,
                    linha.excecao,
                    linha.texto_ncm,
                    linha.alinea,
                    linha.descricao,
                    linha.descricao_contexto,
                    linha.dispositivo_legal_ref,
                )
                for linha in SEED_NCM
                if linha.prefixo in candidatos
            ]
        elif "aliquotas_ipi_tipi" in sql:
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
        self.queries_nbs: list[tuple] = []
        self.queries_ncm: list[tuple] = []

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


def _item_servico(sku="S-1", nbs=None, valor="1000.00", **extra):
    item = {
        "sku": sku,
        "ncm": "00000000",
        "quantidade": 1,
        "valor_unitario": valor,
        "uf_origem": "SP",
        "uf_destino": "SP",
        "natureza": "SERVICO",
    }
    if nbs is not None:
        item["nbs"] = nbs
    item.update(extra)
    return item


def _item_mercadoria(sku="P-1", ncm="04051000", valor="1000.00"):
    return {
        "sku": sku,
        "ncm": ncm,
        "quantidade": 1,
        "valor_unitario": valor,
        "uf_origem": "SP",
        "uf_destino": "RJ",
        "natureza": "MERCADORIA",
    }


def _simular(client, itens, ano=2026, comprador_tipo=None):
    corpo = {
        "tenant_id": TENANT,
        "ano_operacao": ano,
        "operacao_tipo": "VENDA",
        "itens": itens,
    }
    if comprador_tipo is not None:
        corpo["comprador_tipo"] = comprador_tipo
    return client.post("/v1/tax/simulate", headers={"X-API-Key": CHAVE}, json=corpo)


# AT-001 — happy path NBS ------------------------------------------------------


def test_at001_ensino_tecnico_reduz_60_por_cento_via_nbs(client):
    resposta = _simular(client, [_item_servico(nbs="1.2202.00.00")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "APLICADA"
    assert reducao["anexo"] == "II"
    assert reducao["item"] == "4"
    assert reducao["percentual_reducao"] == "60.00"
    assert corpo["reducao"]["anexos_aplicados"] == ["II"]
    # 40% da alíquota da fase — 0,9% x 0,40 = 0,36%.
    assert corpo["itens_detalhados"][0]["aliquotas_aplicadas"]["cbs_percentual"] == "0.36"


# AT-010/AT-011 — Anexo XI, gating por comprador, de ponta a ponta -----------


def test_at010_sem_comprador_o_servico_de_seguranca_ti_paga_aliquota_geral(client):
    corpo = _simular(client, [_item_servico(nbs="1.1501.20.00")]).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "CONDICAO_NAO_SATISFEITA"
    assert reducao["percentual_reducao"] is None
    assert reducao["condicao_pendente_ref"] == "LCP 214/2025, art. 142, I"
    assert reducao["reducao_condicionada_disponivel"] is True
    # Alíquota geral da fase, não 60% — 0,9% cheio.
    assert corpo["itens_detalhados"][0]["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["reducao"]["anexos_aplicados"] == []


def test_at011_com_orgao_publico_o_mesmo_servico_ganha_60_por_cento(client):
    corpo = _simular(
        client, [_item_servico(nbs="1.1501.20.00")], comprador_tipo="ORGAO_PUBLICO"
    ).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "APLICADA"
    assert reducao["percentual_reducao"] == "60.00"
    assert corpo["reducao"]["anexos_aplicados"] == ["XI"]


# AT-013 — minoria NCM do Anexo XI nunca resolve "por acidente" --------------


def test_at013_carro_blindado_ncm_do_anexo_xi_nao_recebe_60_por_cento(client):
    """8710.00.00 (item 2.2 do Bloco 2, "Bens") é chave NCM, fora de escopo
    desta feature — nunca deve casar com nenhum dos 10 Anexos NCM já
    shipados nem com a trilha NBS nova."""
    corpo = _simular(client, [_item_mercadoria(ncm="87100000")]).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "FORA_DO_ANEXO"
    assert reducao["anexo"] is None


# AT-014 — zero regressão dos 10 Anexos NCM, mesmo payload com item NBS -----


def test_at014_payload_misto_nao_regride_a_reducao_ncm_ja_shipada(client):
    """Cadeira de rodas (Anexo XIII, NCM) e ensino técnico (Anexo II, NBS) no
    MESMO payload — cada trilha resolve o seu, sem interferência."""
    corpo = _simular(
        client,
        [
            _item_mercadoria(sku="P-1", ncm="87131000"),
            _item_servico(sku="S-1", nbs="1.2202.00.00"),
        ],
    ).json()

    reducao_mercadoria = corpo["itens_detalhados"][0]["reducao"]
    reducao_servico = corpo["itens_detalhados"][1]["reducao"]

    assert reducao_mercadoria["anexo"] == "XIII"
    assert reducao_servico["anexo"] == "II"
    assert sorted(corpo["reducao"]["anexos_aplicados"]) == ["II", "XIII"]


# AT-015 — campo nbs ausente é aditivo, nunca quebra o payload existente -----


def test_at015_item_de_servico_sem_nbs_nao_quebra_o_payload(client):
    resposta = _simular(client, [_item_servico(nbs=None)])
    assert resposta.status_code == 200
    reducao = resposta.json()["itens_detalhados"][0]["reducao"]
    assert reducao["situacao"] == "NAO_APLICAVEL"


def test_as_duas_consultas_sao_separadas_uma_por_requisicao(client, pool):
    _simular(
        client,
        [
            _item_mercadoria(sku="P-1", ncm="87131000"),
            _item_servico(sku="S-1", nbs="1.2202.00.00"),
        ],
    )
    assert len(pool.queries_nbs) == 1
    assert len(pool.queries_ncm) == 1
