"""AT-001..AT-005 do DEFINE, via `TestClient` + pool fake.

Nenhum destes testes toca PostgreSQL: o fake responde exatamente como o driver
(tuplas na ordem do SELECT) e conta `execute`, que é como AT-004 ("1 query, não
N") vira asserção em vez de intenção. O SQL de verdade é `test_tipi_db.py`.
"""

from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app

CHAVE = "chave-teste-ipi"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"

# ncm_code, aliquota_percentual, nao_tributado, dispositivo_legal_ref — a
# mesma ordem e os mesmos tipos que o SELECT de `buscar_ipi_por_ncm` devolve.
TIPI_FAKE = {
    "2203.00.00": (Decimal("0.03250"), False, "Decreto 11.158/2022 (TIPI), 2203.00.00"),
    "8471.30.12": (Decimal("0.00000"), False, "Decreto 11.158/2022 (TIPI), 8471.30.12"),
    "0102.21.10": (None, True, "Decreto 11.158/2022 (TIPI), NT"),
}


class FakeCursor:
    """Só sabe responder duas coisas: o lookup da TIPI e o `resolver_tenant` do
    audit log, que compartilha este mesmo pool. Devolver None no segundo faz o
    audit log encerrar sozinho (tenant não cadastrado), sem poluir o espião."""

    def __init__(self, espiao):
        self._espiao = espiao
        self._linhas: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        if "aliquotas_ipi_tipi" not in sql:
            # INSERT ... RETURNING id do audit log: devolver algo plausível
            # mantém o log de teste limpo. O audit em si é `test_audit.py`.
            self._linhas = [(uuid4(),)]
            return
        self._espiao.queries_ipi.append((sql, params))
        self._linhas = [
            (codigo, *TIPI_FAKE[codigo]) for codigo in params[0] if codigo in TIPI_FAKE
        ]

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
    """Espião: guarda os argumentos de cada query CONTRA A TIPI, para provar 1
    query por request (AT-004) e zero query sem mercadoria (AT-005).

    Filtra pelo nome da tabela porque o audit log usa o mesmo pool no mesmo
    request — contar `connection()` cru mediria as duas coisas juntas. Que
    `consultar_ipi_com_seguranca` não abre conexão com lista vazia é provado à
    parte, em `test_ipi_resolucao.py`.
    """

    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.queries_ipi: list[tuple] = []

    @contextmanager
    def connection(self):
        if self.falhar:
            raise ConnectionError("Cloud SQL indisponível (simulado)")
        yield FakeConexao(self)

    @property
    def ncms_consultados(self) -> list[str]:
        assert len(self.queries_ipi) == 1, (
            f"esperado 1 query à TIPI, houve {len(self.queries_ipi)}"
        )
        return list(self.queries_ipi[0][1][0])


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


def _item(sku="P-1", ncm="22030000", valor="1000.00", natureza="MERCADORIA"):
    return {
        "sku": sku,
        "ncm": ncm,
        "quantidade": 1,
        "valor_unitario": valor,
        "uf_origem": "SP",
        "uf_destino": "RJ",
        "natureza": natureza,
    }


def _simular(client, itens):
    return client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": 2026,
            "operacao_tipo": "VENDA",
            "itens": itens,
        },
    )


# AT-001 — happy path -------------------------------------------------------


def test_at001_ncm_com_aliquota_soma_total_e_sai_de_tributos_nao_incluidos(client):
    resposta = _simular(client, [_item()])

    assert resposta.status_code == 200
    corpo = resposta.json()
    item = corpo["itens_regime_vigente"][0]

    assert item["ipi_situacao"] == "CALCULADO"
    assert item["ipi_percentual"] == "3.25000"
    assert item["fonte_legal_ipi"] == "Decreto 11.158/2022 (TIPI), 2203.00.00"
    # 3,25% de 1000,00
    assert corpo["regime_vigente"]["total_ipi"] == "32.50"
    assert corpo["regime_vigente"]["ipi_nao_resolvido"] == []
    assert "IPI" in corpo["escopo"]["tributos_incluidos"]
    assert "IPI" not in corpo["escopo"]["tributos_nao_incluidos"]
    assert "IPI" not in corpo["regime_vigente"]["tributos_nao_calculados"]


def test_at001_ncm_pontuado_no_payload_resolve_igual_ao_sem_pontuacao(client, pool):
    """`tests/test_api_simulate.py` manda `8471.30.12` e o smoke test do deploy
    manda `22030000` — as duas grafias precisam chegar canonizadas ao SQL."""
    resposta = _simular(client, [_item(ncm="8471.30.12")])

    assert resposta.status_code == 200
    assert pool.ncms_consultados == ["8471.30.12"]
    assert resposta.json()["itens_regime_vigente"][0]["ipi_situacao"] == "CALCULADO"


def test_aliquota_zero_explicita_da_tipi_e_calculado_nao_indisponivel(client):
    """0% escrito na TIPI é conhecimento, não ausência: situação CALCULADO com
    total 0,00, distinta de NT e de NCM ausente."""
    corpo = _simular(client, [_item(ncm="84713012")]).json()

    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "CALCULADO"
    assert corpo["itens_regime_vigente"][0]["ipi_percentual"] == "0.00000"
    assert corpo["regime_vigente"]["total_ipi"] == "0.00"


# AT-002 — NT ---------------------------------------------------------------


def test_at002_nao_tributado_e_declarado_e_nao_bloqueia_o_total(client):
    corpo = _simular(client, [_item(ncm="22030000"), _item(sku="P-2", ncm="01022110")]).json()

    nt = corpo["itens_regime_vigente"][1]
    assert nt["ipi_situacao"] == "NAO_TRIBUTADO"
    assert nt["ipi_percentual"] is None, "NT não é 0%, é ausência de tributação"
    assert nt["fonte_legal_ipi"] == "Decreto 11.158/2022 (TIPI), NT"
    # NT é resolvido: contribui 0,00 e não impede o total do payload.
    assert corpo["regime_vigente"]["total_ipi"] == "32.50"
    assert corpo["regime_vigente"]["ipi_nao_resolvido"] == []
    assert "IPI" in corpo["escopo"]["tributos_incluidos"]


def test_payload_inteiramente_nt_tem_total_zero_que_e_um_total_legitimo(client):
    corpo = _simular(client, [_item(ncm="01022110")]).json()

    assert corpo["regime_vigente"]["total_ipi"] == "0.00"
    assert "IPI" in corpo["escopo"]["tributos_incluidos"]


# AT-003 — NCM ausente ------------------------------------------------------


def test_at003_ncm_ausente_falha_so_o_item_e_a_resposta_segue_200(client):
    resposta = _simular(client, [_item(sku="DESCONHECIDO", ncm="99999999")])

    assert resposta.status_code == 200, "um NCM desconhecido não invalida o payload"
    corpo = resposta.json()

    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "NCM_NAO_ENCONTRADO"
    assert corpo["itens_regime_vigente"][0]["ipi_percentual"] is None
    assert corpo["regime_vigente"]["ipi_nao_resolvido"] == [
        {"sku": "DESCONHECIDO", "ncm": "99999999", "situacao": "NCM_NAO_ENCONTRADO"}
    ]
    assert corpo["regime_vigente"]["total_ipi"] is None
    assert "IPI" in corpo["escopo"]["tributos_nao_incluidos"]


def test_at003_um_item_nao_resolvido_zera_o_total_mas_preserva_os_demais(client):
    """Um total parcial é indistinguível de um total completo na tela de um
    departamento fiscal. O valor por item resolvido continua visível — nada é
    descartado, só não é somado (Decisão 5)."""
    corpo = _simular(
        client, [_item(sku="OK", ncm="22030000"), _item(sku="RUIM", ncm="99999999")]
    ).json()

    assert corpo["itens_regime_vigente"][0]["ipi_percentual"] == "3.25000"
    assert corpo["regime_vigente"]["total_ipi"] is None
    assert [e["sku"] for e in corpo["regime_vigente"]["ipi_nao_resolvido"]] == ["RUIM"]
    assert "Isto NÃO significa alíquota zero" in corpo["escopo"]["advertencia"]


def test_ncm_parcial_nao_vira_busca_por_prefixo(client, pool):
    """`2203` (posição) é cabeçalho de categoria, não um NCM: não pode virar
    "o primeiro código que começa com 2203" nem chegar ao SQL."""
    corpo = _simular(client, [_item(ncm="2203")]).json()

    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "NCM_NAO_ENCONTRADO"
    assert pool.queries_ipi == [], "código irreconhecível não consulta o banco"


# AT-004 — lote sem N+1 -----------------------------------------------------


def test_at004_n_ncms_distintos_resolvem_em_exatamente_uma_query(client, pool):
    itens = [
        _item(sku="A", ncm="22030000"),
        _item(sku="B", ncm="84713012"),
        _item(sku="C", ncm="01022110"),
    ]

    corpo = _simular(client, itens).json()

    assert len(pool.queries_ipi) == 1, "N NCMs distintos, 1 query — nunca N+1"
    assert pool.ncms_consultados == ["0102.21.10", "2203.00.00", "8471.30.12"]
    assert [i["ipi_situacao"] for i in corpo["itens_regime_vigente"]] == [
        "CALCULADO",
        "CALCULADO",
        "NAO_TRIBUTADO",
    ]


def test_ncms_repetidos_viram_um_unico_codigo_na_query(client, pool):
    """`A-002` do DEFINE: 100 itens do mesmo SKU não podem virar 100 elementos
    na lista do `= ANY(%s)`."""
    itens = [_item(sku=f"P-{i}", ncm="22030000") for i in range(50)]

    corpo = _simular(client, itens).json()

    assert pool.ncms_consultados == ["2203.00.00"]
    assert corpo["regime_vigente"]["total_ipi"] == "1625.00"  # 50 x 32,50


# AT-005 — exclusão mútua com serviço ---------------------------------------


def test_at005_payload_so_de_servico_nao_abre_conexao(client, pool):
    corpo = _simular(client, [_item(natureza="SERVICO")]).json()

    assert pool.queries_ipi == []
    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "NAO_APLICAVEL"
    assert corpo["itens_regime_vigente"][0]["ipi_percentual"] is None


def test_payload_so_de_servico_nao_afirma_total_ipi_zero(client):
    """Sem item de mercadoria não existe total de IPI a afirmar — `0.00` diria
    "esta operação não deve IPI" com aparência de cálculo."""
    corpo = _simular(client, [_item(natureza="SERVICO")]).json()

    assert corpo["regime_vigente"]["total_ipi"] is None
    assert "IPI" in corpo["escopo"]["tributos_nao_incluidos"]
    assert "nenhum item de natureza=MERCADORIA" in corpo["escopo"]["advertencia"]


def test_item_de_servico_nao_entra_em_ipi_nao_resolvido(client):
    """NAO_APLICAVEL não é uma falha de resolução — misturá-lo com
    NCM_NAO_ENCONTRADO bloquearia o total de um payload perfeitamente
    resolvido."""
    corpo = _simular(
        client, [_item(sku="MERC", ncm="22030000"), _item(sku="SERV", natureza="SERVICO")]
    ).json()

    assert corpo["regime_vigente"]["ipi_nao_resolvido"] == []
    assert corpo["regime_vigente"]["total_ipi"] == "32.50"


# Degradação do banco — Decisão 2 -------------------------------------------


def test_falha_de_conexao_degrada_para_200_nunca_5xx(client, pool, caplog):
    """O modo de falha mais importante: o Cloud SQL fora do ar não pode
    derrubar CBS/IBS/IS/PIS/COFINS/ICMS, que são Python puro sem I/O."""
    pool.falhar = True

    resposta = _simular(client, [_item()])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "CONSULTA_INDISPONIVEL"
    assert corpo["regime_vigente"]["total_ipi"] is None
    assert "IPI" in corpo["escopo"]["tributos_nao_incluidos"]
    # O resto da simulação segue intacto.
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["itens_regime_vigente"][0]["icms_interestadual_percentual"] == "12.00"
    assert "Falha ao consultar IPI/TIPI" in caplog.text


def test_indisponibilidade_e_declarada_com_situacao_propria_e_o_item_listado(client, pool):
    """Degradar não é silenciar: o cliente distingue "não existe" de "não
    consegui consultar" e sabe que vale reprocessar."""
    pool.falhar = True

    corpo = _simular(client, [_item(sku="P-1")]).json()

    assert corpo["regime_vigente"]["ipi_nao_resolvido"] == [
        {"sku": "P-1", "ncm": "22030000", "situacao": "CONSULTA_INDISPONIVEL"}
    ]
    assert "CONSULTA_INDISPONIVEL" in corpo["escopo"]["advertencia"]


def test_sem_pool_nenhum_a_feature_e_aditiva_e_nada_muda(pool):
    """Prova de que a feature não muda o comportamento de quem não tem banco —
    o estado de toda a suíte anterior e de qualquer deploy sem Cloud SQL."""
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: None
    try:
        corpo = _simular(TestClient(app), [_item()]).json()
    finally:
        app.dependency_overrides.clear()

    assert corpo["itens_regime_vigente"][0]["ipi_situacao"] == "CONSULTA_INDISPONIVEL"
    assert corpo["regime_vigente"]["total_ipi"] is None
    assert "IPI" in corpo["escopo"]["tributos_nao_incluidos"]
