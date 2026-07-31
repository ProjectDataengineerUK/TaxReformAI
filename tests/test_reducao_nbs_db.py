"""Os Anexos de redução por NBS contra PostgreSQL real — mesmo padrão de
`test_reducao_db.py`: pula sem `DATABASE_URL`, roda de verdade no CI contra um
container `postgres:16`.

O que só existe aqui, e não nos testes com fake: as CHECK constraints (a
completude documentada do item 29/Anexo III, o comprimento de prefixo, a
citação do próprio item), o JOIN real com o catálogo, e a prova de que a
extensão do catálogo não regrediu os 10 Anexos NCM já shipados.
"""

from __future__ import annotations

import os

import pytest

from db.repositorio import buscar_reducao_nbs_por_prefixo

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


def test_seed_carregou_44_itens_e_43_prefixos(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT anexo, count(*) FROM anexos_reducao_nbs GROUP BY anexo ORDER BY anexo"
        )
        itens = dict(cur.fetchall())
        cur.execute(
            "SELECT anexo, count(*) FROM anexos_reducao_nbs_prefixo GROUP BY anexo ORDER BY anexo"
        )
        prefixos = dict(cur.fetchall())

    assert itens == {"II": 8, "III": 30, "XI": 6}  # XI inclui o cabeçalho (item 1)
    assert prefixos == {"II": 8, "III": 30, "XI": 5}


def test_catalogo_ganhou_os_4_anexos_novos_sem_perder_os_10_ja_existentes(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM anexos_reducao_catalogo")
        assert cur.fetchone()[0] == 14

        cur.execute(
            "SELECT anexo, anexo_ordem, percentual_reducao FROM anexos_reducao_catalogo "
            "WHERE anexo IN ('II','III','X','XI') ORDER BY anexo_ordem"
        )
        novos = cur.fetchall()

    assert novos == [
        ("II", 2, 0.6),
        ("III", 3, 0.6),
        ("X", 10, 0.6),
        ("XI", 11, 0.6),
    ]


def test_anexo_x_esta_no_catalogo_mas_sem_nenhum_item_ainda(conexao):
    """Gap documentado (Decisão 5 do DESIGN) — verificado contra o banco real,
    não só inferido do Python."""
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM anexos_reducao_nbs WHERE anexo = 'X'")
        assert cur.fetchone()[0] == 0


def test_os_10_anexos_ncm_sobreviveram_a_extensao_do_catalogo(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM anexos_reducao")
        assert cur.fetchone()[0] == 321
        cur.execute("SELECT count(*) FROM anexos_reducao_ncm")
        assert cur.fetchone()[0] == 540


def test_buscar_reducao_nbs_por_prefixo_traz_o_join_completo(conexao):
    linhas = buscar_reducao_nbs_por_prefixo(conexao, ["122020000"])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.anexo == "II"
    assert linha.anexo_ordem == 2
    assert float(linha.percentual_reducao) == 0.6
    assert linha.dispositivo_legal_ref == "LCP 214/2025, art. 129, Anexo II, item 4"
    assert linha.condicao_comprador_ref is None


def test_buscar_reducao_nbs_por_prefixo_traz_a_condicao_do_anexo_xi(conexao):
    linhas = buscar_reducao_nbs_por_prefixo(conexao, ["115012000"])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.anexo == "XI"
    assert linha.condicao_comprador_ref == "LCP 214/2025, art. 142, I"
    assert linha.condicao_vendedor_ref == "LCP 214/2025, art. 142, II"
    assert linha.descricao_contexto == "Serviços"


def test_lista_vazia_de_prefixos_nao_abre_query(conexao):
    assert buscar_reducao_nbs_por_prefixo(conexao, []) == []


def test_item_29_do_anexo_iii_tem_prefixo_completado_e_texto_literal_preservado_no_banco(conexao):
    """Decisão 6 do DESIGN: `texto_nbs` guarda a grafia literal da fonte
    ("1.2301.99.0", anomalia de 1 dígito); `prefixo` é completado para bater
    com o grupo que compartilha "1.2301.99.00"."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT prefixo, texto_nbs FROM anexos_reducao_nbs_prefixo "
            "WHERE anexo = 'III' AND item = 29"
        )
        prefixo, texto = cur.fetchone()

    assert prefixo == "123019900"
    assert texto == "1.2301.99.0"
