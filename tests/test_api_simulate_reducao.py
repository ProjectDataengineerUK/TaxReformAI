"""AT-001..AT-013 dos 10 Anexos de redução por NCM, via `TestClient` + pool fake.

Nenhum destes testes toca PostgreSQL: o fake responde exatamente como o driver
(tuplas na ordem do SELECT de `buscar_reducao_por_prefixo`) e guarda os
argumentos de cada query, que é como "1 query por request" vira asserção em vez
de intenção. O SQL de verdade é `test_reducao_db.py`.

O seed do fake é lido das migrações 005, 008, 009 e 010 pelo mesmo carregador de
`test_reducao_resolucao.py` — uma cópia dos 321 itens aqui seria uma segunda
fonte de verdade para dado legal transcrito à mão.
"""

from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings, get_settings
from api.db import get_db_pool
from api.main import app
from tests.test_reducao_resolucao import SEED

CHAVE = "chave-teste-reducao"
TENANT = "c39a8281-9b1a-4d2c-8822-123456789abc"

# Mesma TIPI fake de `test_api_simulate_ipi.py`: a cerveja é o único NCM que
# resolve IPI aqui, então os itens dos Anexos caem em NCM_NAO_ENCONTRADO para o
# IPI — de propósito, para provar que os dois lookups são independentes.
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
        if "anexos_reducao_ncm" in sql:
            self._espiao.queries_reducao.append((sql, params))
            candidatos = set(params[0])
            # A ordem é a do SELECT de `buscar_reducao_por_prefixo`, e o
            # dataclass é construído posicionalmente lá — trocar um campo de
            # lugar aqui sem trocar no repositório faz o teste mentir.
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
        self.queries_reducao: list[tuple] = []
        self.queries_ipi: list[tuple] = []

    @contextmanager
    def connection(self):
        if self.falhar:
            raise ConnectionError("Cloud SQL indisponível (simulado)")
        yield FakeConexao(self)

    @property
    def prefixos_consultados(self) -> list[str]:
        assert len(self.queries_reducao) == 1, (
            f"esperado 1 query aos Anexos, houve {len(self.queries_reducao)}"
        )
        return list(self.queries_reducao[0][1][0])


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


def _simular(client, itens, ano=2026, comprador_tipo=None):
    corpo = {
        "tenant_id": TENANT,
        "ano_operacao": ano,
        "operacao_tipo": "VENDA",
        "itens": itens,
    }
    # Só entra no payload quando informado: a ausência da CHAVE é o que prova
    # que o contrato é aditivo, não a presença de um `null`.
    if comprador_tipo is not None:
        corpo["comprador_tipo"] = comprador_tipo
    return client.post(
        "/v1/tax/simulate", headers={"X-API-Key": CHAVE}, json=corpo
    )


# AT-001 — happy path num Anexo NOVO, com sub-item ---------------------------


def test_at001_cadeira_de_rodas_zera_cbs_e_ibs_citando_o_item_2_1_do_xiii(client):
    resposta = _simular(client, [_item(ncm="87131000")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "APLICADA"
    assert detalhe["reducao"]["anexo"] == "XIII"
    assert detalhe["reducao"]["item"] == "2.1"
    assert (
        detalhe["reducao"]["dispositivo_legal_ref"]
        == "LCP 214/2025, art. 145, Anexo XIII, item 2.1"
    )
    assert detalhe["reducao"]["tipo_correspondencia"] == "EXATO"
    assert detalhe["reducao"]["ncm_correspondido"] == "8713.10.00"
    # As alíquotas exibidas saem do resultado REDUZIDO, nunca da regra da fase.
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0"
    assert detalhe["aliquotas_aplicadas"]["ibs_percentual"] == "0"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"
    assert corpo["resumo_financeiro"]["total_ibs"] == "0.00"
    assert corpo["reducao"]["anexos_aplicados"] == ["XIII"]


def test_at001_o_sub_item_vem_com_o_cabecalho_que_lhe_da_sentido(client):
    """`"descricao": "Sem mecanismo de propulsão"` sozinho passaria em qualquer
    teste automatizado e seria inútil para o humano que precisa da
    fundamentação (Decisão 7)."""
    reducao = _simular(client, [_item(ncm="87131000")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert reducao["descricao"] == "Sem mecanismo de propulsão"
    assert reducao["descricao_contexto"].startswith("CADEIRA DE RODAS")


def test_item_sem_pai_nao_traz_contexto(client):
    reducao = _simular(client, [_item(ncm="90221200")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert reducao["anexo"] == "XII" and reducao["item"] == "6"
    assert reducao["descricao_contexto"] is None


def test_at001_o_beneficio_dispensado_e_quantificado_por_item_e_no_total(client):
    """O segundo pain point do DEFINE: o controller precisa demonstrar quanto o
    Anexo economizou, não só que ele foi aplicado."""
    corpo = _simular(client, [_item(ncm="87131000")]).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    # 0,9% e 0,1% de 1000,00 — o que teria sido cobrado sem o art. 145.
    assert reducao["valor_cbs_dispensado"] == "9.00"
    assert reducao["valor_ibs_dispensado"] == "1.00"
    assert reducao["cbs_percentual_sem_reducao"] == "0.900"
    assert reducao["ibs_percentual_sem_reducao"] == "0.100"
    assert corpo["reducao"]["total_cbs_dispensado"] == "9.00"
    assert corpo["reducao"]["total_ibs_dispensado"] == "1.00"
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 1


def test_at001_a_fonte_da_transicao_explica_o_zero_numa_fase_de_0_9_por_cento(client):
    """"Por que zero se a alíquota de 2026 é 0,9%?" é a primeira pergunta do
    usuário, e a resposta é o art. 348, III, "a" — que alcança os arts.
    144/145/148 sem ressalva, por estarem no Título IV (regimes diferenciados)."""
    reducao = _simular(client, [_item(ncm="87131000")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert "art. 348, III" in reducao["fonte_legal_transicao"]


def test_at001_liquido_do_split_payment_e_recomposto_sem_contradicao(client):
    """Em 2026 o IS não incide, então zerar CBS/IBS zera a carga do IVA Dual: o
    líquido volta a ser o bruto. Sem a recomposição, a resposta mostraria um
    líquido menor que o bruto sem nenhum tributo que o justificasse."""
    corpo = _simular(client, [_item(ncm="87131000", valor="1000.00")]).json()
    resumo = corpo["resumo_financeiro"]

    assert resumo["valor_bruto_total"] == "1000.00"
    assert resumo["valor_liquido_projetado_split_payment"] == "1000.00"


def test_ncm_pontuado_no_payload_resolve_igual_ao_sem_pontuacao(client):
    corpo = _simular(client, [_item(ncm="8713.10.00")]).json()

    assert corpo["itens_detalhados"][0]["reducao"]["item"] == "2.1"


# AT-002 — regressão: o Anexo I resolve EXATAMENTE como já resolvia ----------


def test_at002_manteiga_zera_cbs_e_ibs_citando_o_item_5_do_anexo_i(client):
    """Guard-rail da Decisão 8: em relação ao teste já shipado, só mudam o NOME
    do bloco (`cesta_basica` → `reducao_zero`) e o TIPO de `item` (int → str).
    Todo VALOR asserido aqui é o mesmo de antes — situação, dispositivo,
    correspondência, percentuais e totais."""
    corpo = _simular(client, [_item(ncm="04051000")]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "APLICADA"
    assert detalhe["reducao"]["item"] == "5"
    assert (
        detalhe["reducao"]["dispositivo_legal_ref"]
        == "LCP 214/2025, art. 125, Anexo I, item 5"
    )
    assert detalhe["reducao"]["tipo_correspondencia"] == "EXATO"
    assert detalhe["reducao"]["ncm_correspondido"] == "0405.10.00"
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0"
    assert detalhe["aliquotas_aplicadas"]["ibs_percentual"] == "0"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"
    assert corpo["resumo_financeiro"]["total_ibs"] == "0.00"
    assert corpo["reducao"]["total_cbs_dispensado"] == "9.00"
    assert corpo["reducao"]["total_ibs_dispensado"] == "1.00"
    assert corpo["reducao"]["anexos_aplicados"] == ["I"]


@pytest.mark.parametrize(
    ("ncm", "item", "texto"),
    [("09012100", "8", "09.01"), ("09032000", "23", "09.03"), ("10062010", "1", "1006.20")],
)
def test_at002_cafe_mate_e_arroz_do_anexo_i_seguem_resolvendo_por_prefixo(
    client, ncm, item, texto
):
    corpo = _simular(client, [_item(ncm=ncm)]).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "APLICADA"
    assert (reducao["anexo"], reducao["item"]) == ("I", item)
    assert reducao["tipo_correspondencia"] == "PREFIXO"
    assert reducao["ncm_correspondido"] == texto
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"


@pytest.mark.parametrize(
    ("ncm", "item", "texto"),
    [("02074300", "19", "0207.43.00"), ("03021100", "20", "0302.1")],
)
def test_at002_foie_gras_e_salmao_seguem_sem_receber_zero(client, ncm, item, texto):
    corpo = _simular(client, [_item(ncm=ncm)]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "EXCLUIDA_EXPRESSAMENTE"
    assert (detalhe["reducao"]["anexo"], detalhe["reducao"]["item"]) == (
        "I",
        item,
    )
    assert detalhe["reducao"]["ncm_correspondido"] == texto
    assert detalhe["reducao"]["tipo_correspondencia"] == "EXCECAO"
    # Alíquota GERAL, não zero — a diferença que a feature existe para não errar.
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 0


def test_at012_sobreposicoes_do_anexo_i_citam_os_mesmos_itens_de_antes(client):
    """Os dois desempates já shipados, agora com a chave de SEIS componentes —
    mesmos vencedores, mesmos percentuais.

    O que mudou: `2106.90.90` também é citado por 8 itens do Anexo VI a 60%, que
    entram em `itens_correspondentes`. O vencedor não muda porque o componente 2
    (maior redução) põe o Anexo I à frente antes de qualquer ordinal.
    """
    massa = _simular(client, [_item(ncm="19021900")]).json()["itens_detalhados"][0][
        "reducao"
    ]
    formula = _simular(client, [_item(ncm="21069090")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert massa["item"] == "25"
    assert massa["percentual_reducao"] == "100.00"
    assert massa["itens_correspondentes"] == [
        {"anexo": "I", "item": "15"},
        {"anexo": "I", "item": "25"},
    ]
    assert formula["item"] == "4"
    assert formula["percentual_reducao"] == "100.00"
    assert formula["itens_correspondentes"][:2] == [
        {"anexo": "I", "item": "4"},
        {"anexo": "I", "item": "26"},
    ]
    assert len([i for i in formula["itens_correspondentes"] if i["anexo"] == "VI"]) == 8


# AT-013 — item fora dos DEZ Anexos ------------------------------------------


def test_at003_cerveja_segue_com_a_aliquota_geral_da_fase(client):
    """O NCM do smoke test atual. CBS 0,9% e IBS 0,1% idênticos ao que a API já
    devolvia — a prova de que nada regrediu."""
    corpo = _simular(client, [_item(sku="SMOKE-1", ncm="22030000", valor="100.00")]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "FORA_DO_ANEXO"
    assert detalhe["reducao"]["anexo"] is None
    assert detalhe["reducao"]["item"] is None
    assert detalhe["reducao"]["dispositivo_legal_ref"] is None
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert detalhe["aliquotas_aplicadas"]["ibs_percentual"] == "0.100"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.90"
    assert corpo["resumo_financeiro"]["total_ibs"] == "0.10"
    assert corpo["reducao"]["total_cbs_dispensado"] == "0.00"
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 0
    assert corpo["reducao"]["anexos_aplicados"] == []


def test_payload_misto_reduz_so_os_itens_dos_anexos_e_lista_quais(client):
    corpo = _simular(
        client,
        [
            _item(sku="MANTEIGA", ncm="04051000"),
            _item(sku="FLORES", ncm="06031100"),
            _item(sku="CERVEJA", ncm="22030000"),
        ],
    ).json()

    situacoes = [d["reducao"]["situacao"] for d in corpo["itens_detalhados"]]
    assert situacoes == ["APLICADA", "APLICADA", "FORA_DO_ANEXO"]
    # Só a cerveja soma: 0,9% e 0,1% de 1000,00.
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["resumo_financeiro"]["total_ibs"] == "1.00"
    assert corpo["reducao"]["total_cbs_dispensado"] == "18.00"
    # Ordem da lei, não alfabética do rótulo romano.
    assert corpo["reducao"]["anexos_aplicados"] == ["I", "XV"]


def test_anexos_aplicados_sai_na_ordem_da_lei_e_nao_alfabetica(client):
    """'XII' < 'XV' < 'XIII' como texto — ordenar rótulo romano por string está
    errado, e este payload é o que exibe a diferença."""
    corpo = _simular(
        client,
        [
            _item(sku="CADEIRA", ncm="87131000"),  # XIII
            _item(sku="FLORES", ncm="06031100"),  # XV
            _item(sku="TOMOGRAFO", ncm="90221200"),  # XII
        ],
    ).json()

    assert corpo["reducao"]["anexos_aplicados"] == ["XII", "XIII", "XV"]


# AT-004 e AT-005 — prefixo puro e o capítulo de 2 dígitos -------------------


def test_at004_raizes_e_tuberculos_resolvem_pelo_prefixo_de_4_do_anexo_xv(client):
    reducao = _simular(client, [_item(ncm="07141000")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert reducao["situacao"] == "APLICADA"
    assert (reducao["anexo"], reducao["item"]) == ("XV", "5")
    assert reducao["tipo_correspondencia"] == "PREFIXO"
    assert reducao["ncm_correspondido"] == "07.14"


def test_at005_capitulo_6_resolve_pelo_prefixo_de_dois_digitos(client):
    """O caso que prova a Decisão 4 ponta a ponta pela API: se
    `_COMPRIMENTOS_PREFIXO` não tivesse ganhado o 2, o prefixo '06' jamais seria
    gerado e este item cairia em FORA_DO_ANEXO — silenciosamente."""
    corpo = _simular(client, [_item(ncm="06031100")]).json()
    reducao = corpo["itens_detalhados"][0]["reducao"]

    assert reducao["situacao"] == "APLICADA"
    assert (reducao["anexo"], reducao["item"]) == ("XV", "4")
    assert reducao["ncm_correspondido"] == "06"
    assert reducao["tipo_correspondencia"] == "CAPITULO"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"
    assert corpo["reducao"]["total_cbs_dispensado"] == "9.00"


# AT-006 e AT-007 — exceções operantes dos Anexos novos ----------------------


def test_at006_protese_dentaria_nunca_recebe_zero(client):
    corpo = _simular(client, [_item(ncm="90213991")]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "EXCLUIDA_EXPRESSAMENTE"
    assert (detalhe["reducao"]["anexo"], detalhe["reducao"]["item"]) == ("XII", "5")
    assert detalhe["reducao"]["ncm_correspondido"] == "9021.39.91"
    assert detalhe["reducao"]["tipo_correspondencia"] == "EXCECAO"
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 0


def test_trufa_excluida_do_zero_recebe_60_por_cento_via_anexo_vii(client):
    """`0710.80.00` (trufa) é excluída expressamente do zero do Anexo XV/2
    ("exceto os cogumelos e trufas..."), mas a remissão do Anexo VII/14 só
    cede ao Anexo XV quando ele REALMENTE cobre o código — como não cobre
    (está no "exceto"), o VII/14 se aplica de verdade, mesmo mecanismo já
    sancionado para o cogumelo (0709.51.00)."""
    corpo = _simular(client, [_item(ncm="07108000")]).json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "APLICADA"
    assert (detalhe["reducao"]["anexo"], detalhe["reducao"]["item"]) == ("VII", "14")
    assert detalhe["reducao"]["percentual_reducao"] == "60.00"
    assert detalhe["reducao"]["tipo_correspondencia"] == "CAPITULO"
    assert {"anexo": "XV", "item": "2"} in detalhe["reducao"]["itens_excluidos"]


def test_at008_o_exceto_descritivo_do_item_1_3_nao_bloqueia_a_reducao(client):
    corpo = _simular(client, [_item(ncm="90181980")]).json()

    assert corpo["itens_detalhados"][0]["reducao"]["situacao"] == "APLICADA"
    assert corpo["resumo_financeiro"]["total_cbs"] == "0.00"


# AT-009 — desempate de 3 vias ------------------------------------------------


def test_at009_o_codigo_de_tres_itens_cita_o_1_2_e_lista_os_tres(client):
    reducao = _simular(client, [_item(ncm="90181980")]).json()["itens_detalhados"][0][
        "reducao"
    ]

    assert (reducao["anexo"], reducao["item"]) == ("XII", "1.2")
    assert reducao["itens_correspondentes"] == [
        {"anexo": "XII", "item": "1.2"},
        {"anexo": "XII", "item": "1.3"},
        {"anexo": "XII", "item": "14"},
    ]


# AT-010 — falso positivo de prefixo -----------------------------------------


@pytest.mark.parametrize("ncm", ["90223000", "87032310", "72083900"])
def test_at010_vizinho_de_prefixo_nao_entra_pela_vizinhanca(client, ncm):
    corpo = _simular(client, [_item(ncm=ncm)]).json()

    assert corpo["itens_detalhados"][0]["reducao"]["situacao"] == "FORA_DO_ANEXO"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"


# Custo da consulta ----------------------------------------------------------


def test_n_ncms_distintos_resolvem_em_exatamente_uma_query(client, pool):
    itens = [
        _item(sku="A", ncm="04051000"),
        _item(sku="B", ncm="87131000"),
        _item(sku="C", ncm="22030000"),
    ]

    _simular(client, itens)

    assert len(pool.queries_reducao) == 1, "N NCMs distintos, 1 query — nunca N+1"
    # 3 códigos x 6 prefixos (o de 2 dígitos entrou), deduplicados e ordenados.
    assert pool.prefixos_consultados == sorted(
        {
            *("04", "0405", "04051", "040510", "0405100", "04051000"),
            *("87", "8713", "87131", "871310", "8713100", "87131000"),
            *("22", "2203", "22030", "220300", "2203000", "22030000"),
        }
    )


def test_ncms_repetidos_viram_um_unico_conjunto_de_prefixos(client, pool):
    itens = [_item(sku=f"P-{i}", ncm="87131000") for i in range(50)]

    corpo = _simular(client, itens).json()

    assert pool.prefixos_consultados == [
        "87",
        "8713",
        "87131",
        "871310",
        "8713100",
        "87131000",
    ]
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 50
    assert corpo["reducao"]["total_cbs_dispensado"] == "450.00"  # 50 x 9,00


def test_payload_so_de_servico_nao_consulta_os_anexos(client, pool):
    corpo = _simular(client, [_item(natureza="SERVICO")]).json()

    assert pool.queries_reducao == []
    assert corpo["itens_detalhados"][0]["reducao"]["situacao"] == "NAO_APLICAVEL"


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

    assert corpo["reducao"]["total_cbs_dispensado"] == "0.00"
    assert corpo["reducao"]["itens_nao_avaliados"] == []
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 0


def test_totais_nulos_sempre_vem_com_ao_menos_um_item_nomeado(client, pool):
    """A invariante da Decisão 9, verificada nos dois caminhos que produzem
    `null`: nunca "não sei o total" sem dizer por causa de qual item."""
    pool.falhar = True
    indisponivel = _simular(client, [_item(ncm="87131000")]).json()["reducao"]

    pool.falhar = False
    ilegivel = _simular(client, [_item(ncm="0405")]).json()["reducao"]

    for resumo in (indisponivel, ilegivel):
        assert resumo["total_cbs_dispensado"] is None
        assert resumo["itens_nao_avaliados"] != []


def test_os_dois_lookups_sao_independentes(client, pool):
    """Domínios de falha separados de propósito: uma tabela sem GRANT degrada só
    o seu tributo. Fundi-las numa "consulta de tributos" faria a falha de uma
    apagar a outra."""
    _simular(client, [_item(ncm="87131000")])

    assert len(pool.queries_reducao) == 1
    assert len(pool.queries_ipi) == 1


# Degradação — Decisão 8 do Anexo I, inalterada ------------------------------


def test_falha_de_conexao_degrada_para_200_com_a_aliquota_geral(client, pool, caplog):
    """O modo de falha central: o banco fora do ar NÃO pode apagar CBS/IBS, que
    são o produto da simulação. Errar para cima é recuperável; para baixo, não.
    É também o que acontece durante a janela do rename (Decisão 13)."""
    pool.falhar = True

    resposta = _simular(client, [_item(ncm="87131000")])

    assert resposta.status_code == 200
    corpo = resposta.json()
    detalhe = corpo["itens_detalhados"][0]

    assert detalhe["reducao"]["situacao"] == "CONSULTA_INDISPONIVEL"
    assert detalhe["aliquotas_aplicadas"]["cbs_percentual"] == "0.900"
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["reducao"]["consulta_disponivel"] is False
    assert "Falha ao consultar os Anexos de redução" in caplog.text


def test_indisponibilidade_anula_os_totais_e_nomeia_os_itens(client, pool):
    """Decisão 9: um total parcial é indistinguível de um total completo, e este
    número vai para a diretoria."""
    pool.falhar = True

    corpo = _simular(client, [_item(sku="P-1", ncm="87131000")]).json()

    assert corpo["reducao"]["total_cbs_dispensado"] is None
    assert corpo["reducao"]["total_ibs_dispensado"] is None
    assert corpo["reducao"]["itens_nao_avaliados"] == [
        {"sku": "P-1", "ncm": "87131000", "situacao": "CONSULTA_INDISPONIVEL"}
    ]
    assert "SUPERESTIMADOS" in corpo["escopo"]["advertencia"]


def test_um_ncm_ilegivel_anula_os_totais_mas_preserva_as_reducoes_aplicadas(client):
    """`itens_com_reducao_aplicada` continua preenchido: é fato sobre o que a
    resposta fez, não estimativa do que deveria ter feito."""
    corpo = _simular(
        client, [_item(sku="OK", ncm="87131000"), _item(sku="RUIM", ncm="0405")]
    ).json()

    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"  # só o item ruim soma
    assert corpo["reducao"]["itens_com_reducao_aplicada"] == 1
    assert corpo["reducao"]["total_cbs_dispensado"] is None
    assert [e["sku"] for e in corpo["reducao"]["itens_nao_avaliados"]] == ["RUIM"]


def test_sem_pool_nenhum_a_feature_e_aditiva_e_nada_muda(pool):
    """A prova de que a feature é aditiva: é o estado de toda a suíte anterior e
    de qualquer deploy sem Cloud SQL — 200, alíquota geral, nada some."""
    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        api_keys_to_tenant={CHAVE: TENANT}
    )
    app.dependency_overrides[get_db_pool] = lambda: None
    try:
        corpo = _simular(TestClient(app), [_item(ncm="87131000")]).json()
    finally:
        app.dependency_overrides.clear()

    assert (
        corpo["itens_detalhados"][0]["reducao"]["situacao"] == "CONSULTA_INDISPONIVEL"
    )
    assert corpo["resumo_financeiro"]["total_cbs"] == "9.00"
    assert corpo["reducao"]["total_cbs_dispensado"] is None


def test_nenhum_codigo_de_erro_novo_e_introduzido(client, pool):
    """A redução é aditiva: nenhum modo de falha dela justifica invalidar
    CBS/IBS nem devolver 4xx/5xx."""
    pool.falhar = True

    for ncm in ("87131000", "90213991", "06031100", "0405", "99999999"):
        assert _simular(client, [_item(ncm=ncm)]).status_code == 200


# Escopo e advertência -------------------------------------------------------


def test_advertencia_declara_a_reducao_aplicada_e_a_condicao_nao_verificada(client):
    """A correspondência por NCM é necessária, nem sempre suficiente: vários
    itens exigem condições que o payload não carrega (Anvisa nos Anexos XII e
    XIII, destinação no XV, legislação específica no I)."""
    corpo = _simular(client, [_item(ncm="06031100")]).json()

    assert "art. 348, III" in corpo["escopo"]["advertencia"]
    assert "XV" in corpo["escopo"]["advertencia"]
    assert "condições adicionais" in corpo["escopo"]["advertencia"]
    assert "não verifica" in corpo["reducao"]["fonte_legal"]
    assert "art. 148" in corpo["reducao"]["fonte_legal"]


def test_payload_sem_item_de_anexo_diz_isso_em_vez_de_omitir(client):
    corpo = _simular(client, [_item(ncm="22030000")]).json()

    assert "Nenhum item do payload corresponde" in corpo["escopo"]["advertencia"]


def test_fase_recusada_nem_chega_a_avaliar_os_anexos(client, pool):
    """2027 devolve 422 antes do laço pela CBS pendente do art. 347 — a redução
    não muda esse caminho."""
    resposta = _simular(client, [_item(ncm="87131000")], ano=2027)

    assert resposta.status_code == 422
    assert pool.queries_reducao == []
