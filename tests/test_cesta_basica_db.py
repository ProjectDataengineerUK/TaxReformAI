"""Anexo I contra PostgreSQL real — mesmo padrão de `test_tipi_db.py`: pula sem
`DATABASE_URL`, roda de verdade no CI contra um container `postgres:16`.

O que só existe aqui, e não nos testes com fake: as duas CHECK constraints (que
são a garantia real contra erro de transcrição, e vivem no banco, não no
Python), o seed carregado pela migração de verdade, e a prova de que a migração
006 derrubou `regras_tributarias_cache`.
"""

from __future__ import annotations

import os

import pytest

from db.repositorio import buscar_cesta_basica_por_prefixo

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado")

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL ausente — sem PostgreSQL para testar"
)


@pytest.fixture
def conexao():
    from db.migrador import aplicar_migracoes

    con = psycopg.connect(DATABASE_URL)
    aplicar_migracoes(con)
    yield con
    con.rollback()
    con.close()


# Seed — contagens de fechamento do DESIGN -----------------------------------


def test_seed_carregou_os_26_itens(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM cesta_basica_anexo_i")
        total = cur.fetchone()[0]
        cur.execute("SELECT min(item), max(item) FROM cesta_basica_anexo_i")
        menor, maior = cur.fetchone()

    assert (total, menor, maior) == (26, 1, 26)


def test_seed_carregou_76_inclusoes_e_19_excecoes(conexao):
    """Contagem é teste de truncamento: uma migração cortada pela metade passa
    em toda constraint e falha aqui."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT excecao, count(*) FROM cesta_basica_anexo_i_ncm "
            "GROUP BY excecao ORDER BY excecao"
        )
        contagens = dict(cur.fetchall())

    assert contagens == {False: 76, True: 19}


def test_todo_item_cita_o_proprio_numero_no_dispositivo_legal(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM cesta_basica_anexo_i "
            "WHERE dispositivo_legal_ref <> "
            "  ('LCP 214/2025, art. 125, Anexo I, item ' || item::text)"
        )
        divergentes = cur.fetchone()[0]

    assert divergentes == 0


def test_comprimentos_de_prefixo_presentes_sao_de_4_a_8(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT length(prefixo) FROM cesta_basica_anexo_i_ncm ORDER BY 1"
        )
        comprimentos = [linha[0] for linha in cur.fetchall()]

    assert comprimentos == [4, 5, 6, 7, 8]


def test_toda_excecao_desce_de_uma_inclusao_do_mesmo_item(conexao):
    """Uma exceção órfã produziria EXCLUIDA_EXPRESSAMENTE citando um item que
    jamais incluiu aquele código."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT e.item, e.prefixo FROM cesta_basica_anexo_i_ncm e
            WHERE e.excecao IS TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM cesta_basica_anexo_i_ncm i
                  WHERE i.item = e.item AND i.excecao IS FALSE
                    AND e.prefixo LIKE i.prefixo || '%'
              )
            """
        )
        orfas = cur.fetchall()

    assert orfas == []


# CHECK constraints — a garantia mora no banco, não na disciplina do código ---


def test_check_recusa_prefixo_que_nao_bate_com_a_grafia_do_dou(conexao):
    """O erro mais provável desta feature: transcrever `0210.99.1` e digitar
    `02109910` no prefixo. Sem esta CHECK, viraria uma mercadoria a mais na
    cesta básica, descoberta por um cliente."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, texto_ncm) "
                "VALUES (19, '02109910', '0210.99.1')"
            )
    conexao.rollback()


def test_check_recusa_prefixo_curto_demais_para_o_gerador_enxergar(conexao):
    """`prefixos_ncm` gera exatamente 4..8 dígitos: uma linha de 3 nunca casaria
    com nada — falso negativo permanente e mudo (Decisão 2)."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, texto_ncm) "
                "VALUES (19, '020', '020')"
            )
    conexao.rollback()


def test_check_recusa_item_fora_da_faixa_do_anexo(conexao):
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO cesta_basica_anexo_i (item, descricao, dispositivo_legal_ref) "
                "VALUES (27, 'item inventado', 'LCP 214/2025')"
            )
    conexao.rollback()


def test_prefixo_duplicado_no_mesmo_item_e_rejeitado(conexao):
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, excecao, texto_ncm) "
                "VALUES (5, '04051000', FALSE, '0405.10.00')"
            )
    conexao.rollback()


def test_prefixo_sem_item_existente_e_rejeitado(conexao):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, texto_ncm) "
                "VALUES (26, '99999999', '9999.99.99'), (99, '88888888', '8888.88.88')"
            )
    conexao.rollback()


# buscar_cesta_basica_por_prefixo — o lookup que /v1/tax/simulate faz ---------


class CursorEspiao:
    """Conta `execute` sobre a conexão real: "1 query, não N" precisa ser
    verificado contra o driver de verdade, não só contra um fake."""

    def __init__(self, conexao):
        self._conexao = conexao
        self.execucoes = 0

    def cursor(self):
        espiao = self

        class _Cursor:
            def __init__(self):
                self._cur = espiao._conexao.cursor()

            def __enter__(self):
                self._cur.__enter__()
                return self

            def __exit__(self, *args):
                return self._cur.__exit__(*args)

            def execute(self, sql, params=None):
                espiao.execucoes += 1
                return self._cur.execute(sql, params)

            def fetchall(self):
                return self._cur.fetchall()

        return _Cursor()


def test_lookup_devolve_inclusao_e_excecao_no_mesmo_lote(conexao):
    """Uma exceção só importa quando ela própria é prefixo do código, então cai
    no mesmo `= ANY` — sem segunda consulta (Decisão 3)."""
    from api.ncm import prefixos_ncm

    linhas = buscar_cesta_basica_por_prefixo(conexao, prefixos_ncm("02074300"))

    por_prefixo = {linha.prefixo: linha for linha in linhas}
    assert por_prefixo["0207"].excecao is False
    assert por_prefixo["0207"].item == 19
    assert por_prefixo["02074300"].excecao is True
    assert por_prefixo["02074300"].texto_ncm == "0207.43.00"


def test_lookup_traz_descricao_e_dispositivo_do_item_pelo_join(conexao):
    linhas = buscar_cesta_basica_por_prefixo(conexao, ["04051000"])

    assert len(linhas) == 1
    assert linhas[0].item == 5
    assert linhas[0].dispositivo_legal_ref == "LCP 214/2025, art. 125, Anexo I, item 5"
    assert linhas[0].descricao.startswith("Manteiga")
    assert linhas[0].alinea is None


def test_lookup_traz_a_alinea_dos_itens_19_e_20(conexao):
    linhas = buscar_cesta_basica_por_prefixo(conexao, ["0207", "0302"])

    assert {linha.item: linha.alinea for linha in linhas} == {19: "d", 20: "a"}


def test_prefixo_compartilhado_devolve_as_duas_linhas(conexao):
    """A sobreposição 4/26 precisa chegar inteira ao Python — é lá que o
    desempate acontece."""
    linhas = buscar_cesta_basica_por_prefixo(conexao, ["21069090"])

    assert sorted(linha.item for linha in linhas) == [4, 26]


def test_lote_de_prefixos_resolve_em_exatamente_uma_query(conexao):
    espiao = CursorEspiao(conexao)

    linhas = buscar_cesta_basica_por_prefixo(
        espiao, ["04051000", "0901", "0207", "02074300", "22030000"]
    )

    assert espiao.execucoes == 1
    assert {linha.item for linha in linhas} == {5, 8, 19}


def test_prefixo_inexistente_devolve_lista_vazia_nao_erro(conexao):
    assert buscar_cesta_basica_por_prefixo(conexao, ["99999999"]) == []


def test_lista_vazia_nao_abre_cursor(conexao):
    espiao = CursorEspiao(conexao)

    assert buscar_cesta_basica_por_prefixo(espiao, []) == []
    assert espiao.execucoes == 0


# Migração 006 — remoção do código morto -------------------------------------


def test_regras_tributarias_cache_nao_existe_mais(conexao):
    """Decisão 12: a tabela nunca teve linhas, nunca teve consumidor, e sua
    forma está errada para os regimes diferenciados reais. Manter uma tabela
    vazia convidaria alguém a populá-la do jeito errado."""
    with conexao.cursor() as cur:
        cur.execute("SELECT to_regclass('public.regras_tributarias_cache')")
        assert cur.fetchone()[0] is None


def test_as_duas_migracoes_novas_ficaram_registradas(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT versao FROM schema_migrations WHERE versao IN "
            "('005_cesta_basica_anexo_i.sql', '006_remover_regras_tributarias_cache.sql') "
            "ORDER BY versao"
        )
        versoes = [linha[0] for linha in cur.fetchall()]

    assert versoes == [
        "005_cesta_basica_anexo_i.sql",
        "006_remover_regras_tributarias_cache.sql",
    ]
