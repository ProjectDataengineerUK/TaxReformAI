"""AT-001..AT-005 da Cesta Básica, via `TestClient` + pool fake.

Nenhum destes testes toca PostgreSQL: o fake responde exatamente como o driver
(tuplas na ordem do SELECT de `buscar_cesta_basica_por_prefixo`) e guarda os
argumentos de cada query, que é como "1 query por request" vira asserção em vez
de intenção. O SQL de verdade é `test_cesta_basica_db.py`.

O seed do fake é lido da migração 005 pelo mesmo carregador de
`test_cesta_basica_resolucao.py` — uma cópia dos 26 itens aqui seria uma
segunda fonte de verdade para dado legal transcrito à mão.
"""

from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app
from tests.test_cesta_basica_resolucao import SEED

CHAVE = "chave-teste-cesta"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"

# Mesma TIPI fake de `test_api_simulate_ipi.py`: a cerveja é o único NCM que
# resolve IPI aqui, então os itens da cesta básica caem em NCM_NAO_ENCONTRADO
# para o IPI — de propósito, para provar que os dois lookups são independentes.
TIPI_FAKE = {
    "2203.00.00": (Decimal("0.03250"), False, "Decreto 11.158/2022 (TIPI), 2203.00.00"),
}


class FakeCursor:
    def __init__(self, espiao):
        self._espiao = espiao
        self._linhas: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        if "cesta_basica_anexo_i_ncm" in sql:
            self._espiao.queries_cesta.append((sql, params))
            candidatos = set(params[0])
            self._linhas = [
                (
                    linha.item,
                    linha.prefixo,
                    linha.excecao,
                    linha.texto_ncm,
                    linha.alinea,
                    linha.descricao,
                    linha.dispositivo_legal_ref,
                )
                for linha in SEED
                if linha.prefixo in candidatos
            ]
        elif "aliquotas_ipi_tipi" in sql:
            self._espiao.queries_ipi.append((sql, params))
            self._linhas = [
                (codigo, *TIPI_FAKE[codigo]) for codigo in params[0] if codigo in TIPI_FAKE
            ]
        else:
            # INSERT ... RETURNING id do audit log, que usa o mesmo pool.
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
    """Espião com os dois lookups SEPARADOS: é assim que se prova que a falha
    de um tributo não apaga o outro (Integration Points do DESIGN)."""

    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.queries_cesta: list[tuple] = []
        self.queries_ipi: list[tuple] = []

    @contextmanager
    def connection(self):
        if self.falhar:
            raise ConnectionError("Cloud SQL indisponível (simulado)")
        yield FakeConexao(self)

    @property
    def prefixos_consultados(self) -> list[str]:
        assert len(self.queries_cesta) == 1, (
            f"esperado 1 query ao Anexo I, houve {len(self.queries_cesta)}"
        )
        return list(self.queries_cesta[0][1][0])


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


def _item(sku="P-1", ncm="04051000", valor="1000.00", natureza="MERCADORIA"):
    return {
        "sku": sku,
        "ncm": ncm,
        "quantidade": 1,
        "valor_unitario": valor,
        "uf_origem": "SP",
        "uf_destino": "RJ",
        "natureza": natureza,
    }


def _simular(client, itens, ano=2026):
    return client.post(
        "/v1/tax/simulate",
        headers={"X-API-Key": CHAVE},
        json={
            "tenant_id": TENANT,
            "ano_operacao": ano,
            "operacao_tipo": "VENDA",
            "itens": itens,
        },
    )


# AT-001 — happy path, correspondência exata --------------------------------


def test_at001_manteiga_zera_cbs_e_ibs_citando_o_item_5(client):
    resposta = _simular(client, [_item(ncm="04051000")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["cesta_basica"]["situacao"] == "APLICADA"
    assert detalhe["cesta_basica"]["item"] == 5
    assert (
        detalhe["cesta_basica"]["dispositivo_legal_ref"]
        == "LCP 214/2025, art. 125, Anexo I, item 5"
    )
    assert detalhe["cesta_basica"]["tipo_correspondencia"] == "EXATO"
    assert detalhe["cesta_basica"]["ncm_correspondido"] == "0405.10.00"
    # As alíquotas exibidas saem do resultado REDUZIDO, nunca da regra da fase.
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0"
    assert detalhe["aliquotas_aplicadas"]["ibs_percentual"] == "0"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"
    assert corpo["resumo_financeiro"]["total_ibs"] == "0.00"


def test_at001_o_beneficio_dispensado_e_quantificado_por_item_e_no_total(client):
    """O segundo pain point do DEFINE: o controller precisa demonstrar quanto a
    Cesta Básica economizou, não só que ela foi aplicada."""
    corpo = _simular(client, [_item(ncm="04051000")]).json()
    cesta = corpo["itens_detalhados"][0]["cesta_basica"]

    # 0,9% e 0,1% de 1000,00 — o que teria sido cobrado sem o art. 125.
    assert cesta["valor_cbs_dispensado"] == "9.00"
    assert cesta["valor_ibs_dispensado"] == "1.00"
    assert cesta["cbs_percentual_sem_reducao"] == "0.900"
    assert cesta["ibs_percentual_sem_reducao"] == "0.100"
    assert corpo["cesta_basica"]["total_cbs_dispensado"] == "9.00"
    assert corpo["cesta_basica"]["total_ibs_dispensado"] == "1.00"
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 1


def test_at001_a_fonte_da_transicao_explica_o_zero_numa_fase_de_0_9_por_cento(client):
    """"Por que zero se a alíquota de 2026 é 0,9%?" é a primeira pergunta do
    usuário, e a resposta é o art. 348, III, "a" (Decisão 5)."""
    cesta = _simular(client, [_item(ncm="04051000")]).json()["itens_detalhados"][0][
        "cesta_basica"
    ]

    assert "art. 348, III" in cesta["fonte_legal_transicao"]


def test_at001_liquido_do_split_payment_e_recomposto_sem_contradicao(client):
    """Em 2026 o IS não incide, então zerar CBS/IBS zera a carga do IVA Dual: o
    líquido volta a ser o bruto. Sem a recomposição, a resposta mostraria um
    líquido menor que o bruto sem nenhum tributo que o justificasse."""
    corpo = _simular(client, [_item(ncm="04051000", valor="1000.00")]).json()
    resumo = corpo["resumo_financeiro"]

    assert resumo["valor_bruto_total"] == "1000.00"
    assert resumo["valor_liquido_projetado_split_payment"] == "1000.00"


def test_ncm_pontuado_no_payload_resolve_igual_ao_sem_pontuacao(client):
    corpo = _simular(client, [_item(ncm="0405.10.00")]).json()

    assert corpo["itens_detalhados"][0]["cesta_basica"]["item"] == 5


# AT-002 — regressão: item fora do Anexo ------------------------------------


def test_at002_cerveja_segue_com_a_aliquota_geral_da_fase(client):
    """O NCM do smoke test atual. CBS 0,9% e IBS 0,1% idênticos ao que a API já
    devolvia antes desta feature — a prova de que nada regrediu."""
    corpo = _simular(client, [_item(sku="SMOKE-1", ncm="22030000", valor="100.00")]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["cesta_basica"]["situacao"] == "FORA_DO_ANEXO"
    assert detalhe["cesta_basica"]["item"] is None
    assert detalhe["cesta_basica"]["dispositivo_legal_ref"] is None
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert detalhe["aliquotas_aplicadas"]["ibs_percentual"] == "0.100"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.90"
    assert corpo["resumo_financeiro"]["total_ibs"] == "0.10"
    assert corpo["cesta_basica"]["total_cbs_dispensado"] == "0.00"
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 0


def test_payload_misto_reduz_so_o_item_da_cesta(client):
    corpo = _simular(
        client,
        [_item(sku="MANTEIGA", ncm="04051000"), _item(sku="CERVEJA", ncm="22030000")],
    ).json()

    situacoes = [d["cesta_basica"]["situacao"] for d in corpo["itens_detalhados"]]
    assert situacoes == ["APLICADA", "FORA_DO_ANEXO"]
    # Só a cerveja soma: 0,9% e 0,1% de 1000,00.
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["resumo_financeiro"]["total_ibs"] == "1.00"
    assert corpo["cesta_basica"]["total_cbs_dispensado"] == "9.00"


# AT-003 — prefixo puro ------------------------------------------------------


@pytest.mark.parametrize(
    ("ncm", "item", "texto"),
    [("09012100", 8, "09.01"), ("09032000", 23, "09.03"), ("10062010", 1, "1006.20")],
)
def test_at003_cafe_mate_e_arroz_resolvem_por_prefixo(client, ncm, item, texto):
    corpo = _simular(client, [_item(ncm=ncm)]).json()
    cesta = corpo["itens_detalhados"][0]["cesta_basica"]

    assert cesta["situacao"] == "APLICADA"
    assert cesta["item"] == item
    assert cesta["tipo_correspondencia"] == "PREFIXO"
    assert cesta["ncm_correspondido"] == texto
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"


# AT-004 — exceção do próprio Anexo -----------------------------------------


@pytest.mark.parametrize(
    ("ncm", "item", "texto"),
    [("02074300", 19, "0207.43.00"), ("03021100", 20, "0302.1")],
)
def test_at004_foie_gras_e_salmao_nunca_recebem_zero(client, ncm, item, texto):
    corpo = _simular(client, [_item(ncm=ncm)]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["cesta_basica"]["situacao"] == "EXCLUIDA_EXPRESSAMENTE"
    assert detalhe["cesta_basica"]["item"] == item
    assert detalhe["cesta_basica"]["ncm_correspondido"] == texto
    assert detalhe["cesta_basica"]["tipo_correspondencia"] == "EXCECAO"
    # Alíquota GERAL, não zero — a diferença que a feature existe para não errar.
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 0


# AT-005 — falso positivo de prefixo -----------------------------------------


def test_at005_arroz_com_casca_nao_entra_pela_vizinhanca_do_prefixo(client):
    corpo = _simular(client, [_item(ncm="10061010")]).json()

    assert corpo["itens_detalhados"][0]["cesta_basica"]["situacao"] == "FORA_DO_ANEXO"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"


# Sobreposições --------------------------------------------------------------


def test_sobreposicao_15_25_cita_o_item_25_e_lista_os_dois(client):
    cesta = _simular(client, [_item(ncm="19021900")]).json()["itens_detalhados"][0][
        "cesta_basica"
    ]

    assert cesta["item"] == 25
    assert cesta["itens_correspondentes"] == [15, 25]


def test_sobreposicao_4_26_cita_o_item_4_e_lista_os_dois(client):
    cesta = _simular(client, [_item(ncm="21069090")]).json()["itens_detalhados"][0][
        "cesta_basica"
    ]

    assert cesta["item"] == 4
    assert cesta["itens_correspondentes"] == [4, 26]


# Custo da consulta ----------------------------------------------------------


def test_n_ncms_distintos_resolvem_em_exatamente_uma_query(client, pool):
    itens = [
        _item(sku="A", ncm="04051000"),
        _item(sku="B", ncm="09012100"),
        _item(sku="C", ncm="22030000"),
    ]

    _simular(client, itens)

    assert len(pool.queries_cesta) == 1, "N NCMs distintos, 1 query — nunca N+1"
    # 3 códigos x 5 prefixos, deduplicados e ordenados.
    assert pool.prefixos_consultados == sorted(
        {
            *("0405", "04051", "040510", "0405100", "04051000"),
            *("0901", "09012", "090121", "0901210", "09012100"),
            *("2203", "22030", "220300", "2203000", "22030000"),
        }
    )


def test_ncms_repetidos_viram_um_unico_conjunto_de_prefixos(client, pool):
    itens = [_item(sku=f"P-{i}", ncm="04051000") for i in range(50)]

    corpo = _simular(client, itens).json()

    assert pool.prefixos_consultados == [
        "0405",
        "04051",
        "040510",
        "0405100",
        "04051000",
    ]
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 50
    assert corpo["cesta_basica"]["total_cbs_dispensado"] == "450.00"  # 50 x 9,00


def test_payload_so_de_servico_nao_consulta_o_anexo(client, pool):
    corpo = _simular(client, [_item(natureza="SERVICO")]).json()

    assert pool.queries_cesta == []
    assert corpo["itens_detalhados"][0]["cesta_basica"]["situacao"] == "NAO_APLICAVEL"


def test_payload_so_de_servico_tem_total_dispensado_zero_e_lista_vazia():
    """Sem item de mercadoria não há nada a avaliar, e "nada a avaliar" é uma
    avaliação COMPLETA: 0,00 dispensado é fato, não estimativa. O predicado é a
    lista de não avaliados, não o flag de disponibilidade — senão a mesma
    resposta viria `null` com a lista vazia (contradizendo a Decisão 9) só
    porque o pool era `None`, e `0.00` se o pool estivesse quebrado, já que sem
    prefixo a consultar nenhuma conexão é tentada."""
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: None
    try:
        corpo = _simular(TestClient(app), [_item(natureza="SERVICO")]).json()
    finally:
        app.dependency_overrides.clear()

    assert corpo["cesta_basica"]["total_cbs_dispensado"] == "0.00"
    assert corpo["cesta_basica"]["itens_nao_avaliados"] == []
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 0


def test_totais_nulos_sempre_vem_com_ao_menos_um_item_nomeado(client, pool):
    """A invariante da Decisão 9, verificada nos dois caminhos que produzem
    `null`: nunca "não sei o total" sem dizer por causa de qual item."""
    pool.falhar = True
    indisponivel = _simular(client, [_item(ncm="04051000")]).json()["cesta_basica"]

    pool.falhar = False
    ilegivel = _simular(client, [_item(ncm="0405")]).json()["cesta_basica"]

    for resumo in (indisponivel, ilegivel):
        assert resumo["total_cbs_dispensado"] is None
        assert resumo["itens_nao_avaliados"] != []


def test_os_dois_lookups_sao_independentes(client, pool):
    """Domínios de falha separados de propósito: uma tabela sem GRANT degrada só
    o seu tributo. Fundi-las numa "consulta de tributos" faria a falha de uma
    apagar a outra."""
    _simular(client, [_item(ncm="04051000")])

    assert len(pool.queries_cesta) == 1
    assert len(pool.queries_ipi) == 1


# Degradação — Decisão 8 -----------------------------------------------------


def test_falha_de_conexao_degrada_para_200_com_a_aliquota_geral(client, pool, caplog):
    """O modo de falha central: o banco fora do ar NÃO pode apagar CBS/IBS, que
    são o produto da simulação. Errar para cima é recuperável; para baixo, não."""
    pool.falhar = True

    resposta = _simular(client, [_item(ncm="04051000")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["cesta_basica"]["situacao"] == "CONSULTA_INDISPONIVEL"
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["cesta_basica"]["consulta_disponivel"] is False
    assert "Falha ao consultar a Cesta Básica" in caplog.text


def test_indisponibilidade_anula_os_totais_e_nomeia_os_itens(client, pool):
    """Decisão 9: um total parcial é indistinguível de um total completo, e este
    número vai para a diretoria."""
    pool.falhar = True

    corpo = _simular(client, [_item(sku="P-1", ncm="04051000")]).json()

    assert corpo["cesta_basica"]["total_cbs_dispensado"] is None
    assert corpo["cesta_basica"]["total_ibs_dispensado"] is None
    assert corpo["cesta_basica"]["itens_nao_avaliados"] == [
        {"sku": "P-1", "ncm": "04051000", "situacao": "CONSULTA_INDISPONIVEL"}
    ]
    assert "SUPERESTIMADOS" in corpo["escopo"]["advertencia"]


def test_um_ncm_ilegivel_anula_os_totais_mas_preserva_as_reducoes_aplicadas(client):
    """`itens_com_reducao_aplicada` continua preenchido: é fato sobre o que a
    resposta fez, não estimativa do que deveria ter feito."""
    corpo = _simular(
        client, [_item(sku="OK", ncm="04051000"), _item(sku="RUIM", ncm="0405")]
    ).json()

    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"  # só o item ruim soma
    assert corpo["cesta_basica"]["itens_com_reducao_aplicada"] == 1
    assert corpo["cesta_basica"]["total_cbs_dispensado"] is None
    assert [e["sku"] for e in corpo["cesta_basica"]["itens_nao_avaliados"]] == ["RUIM"]


def test_sem_pool_nenhum_a_feature_e_aditiva_e_nada_muda(pool):
    """A prova de que a feature é aditiva: é o estado de toda a suíte anterior e
    de qualquer deploy sem Cloud SQL — 200, alíquota geral, nada some."""
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: None
    try:
        corpo = _simular(TestClient(app), [_item(ncm="04051000")]).json()
    finally:
        app.dependency_overrides.clear()

    assert corpo["itens_detalhados"][0]["cesta_basica"]["situacao"] == "CONSULTA_INDISPONIVEL"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["cesta_basica"]["total_cbs_dispensado"] is None


def test_nenhum_codigo_de_erro_novo_e_introduzido(client, pool):
    """A redução é aditiva: nenhum modo de falha dela justifica invalidar
    CBS/IBS nem devolver 4xx/5xx."""
    pool.falhar = True

    for ncm in ("04051000", "02074300", "0405", "99999999"):
        assert _simular(client, [_item(ncm=ncm)]).status_code == 200


# Escopo e advertência -------------------------------------------------------


def test_advertencia_declara_a_reducao_aplicada_e_a_condicao_nao_verificada(client):
    """A correspondência por NCM é necessária, nem sempre suficiente: vários
    itens do Anexo exigem condições que o payload não carrega."""
    corpo = _simular(client, [_item(ncm="04051000")]).json()

    assert "art. 125" in corpo["escopo"]["advertencia"]
    assert "condições adicionais" in corpo["escopo"]["advertencia"]
    assert "não verifica" in corpo["cesta_basica"]["fonte_legal"]


def test_payload_sem_item_da_cesta_diz_isso_em_vez_de_omitir(client):
    corpo = _simular(client, [_item(ncm="22030000")]).json()

    assert "Nenhum item do payload corresponde" in corpo["escopo"]["advertencia"]


def test_fase_recusada_nem_chega_a_avaliar_a_cesta(client, pool):
    """2027 devolve 422 antes do laço pela CBS pendente do art. 347 — a redução
    não muda esse caminho."""
    resposta = _simular(client, [_item(ncm="04051000")], ano=2027)

    assert resposta.status_code == 422
    assert pool.queries_cesta == []
