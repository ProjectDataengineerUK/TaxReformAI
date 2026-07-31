"""A base de incidência do Imposto Seletivo contra PostgreSQL real — mesmo
padrão de `test_reducao_db.py`: pula sem `DATABASE_URL`, roda de verdade no
CI contra um container `postgres:16`.

O que só existe aqui: as CHECK constraints, a prova de não-sobreposição
entre categorias (Decisão 2 do DESIGN), o JOIN real, e a prova de que a
migração 013 não regride nenhuma tabela já shipada.
"""

from __future__ import annotations

import os

import pytest

from db.repositorio import buscar_incidencia_is_por_prefixo

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


def test_seed_carregou_6_categorias_e_24_prefixos(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia")
        assert cur.fetchone()[0] == 6
        cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia_ncm")
        assert cur.fetchone()[0] == 24


def test_inciso_vii_nunca_foi_inserido(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia WHERE inciso = 7")
        assert cur.fetchone()[0] == 0


def test_categorias_nao_se_sobrepoem(conexao):
    """A própria migração já prova isso via `DO $$` — este teste confirma o
    mesmo fato de novo, contra o estado final do banco, não só no momento
    da aplicação da migração."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM imposto_seletivo_incidencia_ncm a
            JOIN imposto_seletivo_incidencia_ncm b
              ON a.inciso <> b.inciso
             AND (b.prefixo LIKE a.prefixo || '%' OR a.prefixo LIKE b.prefixo || '%')
            """
        )
        assert cur.fetchone()[0] == 0


def test_buscar_incidencia_is_por_prefixo_traz_o_join_completo(conexao):
    linhas = buscar_incidencia_is_por_prefixo(conexao, ["870421"])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.inciso == 1
    assert linha.categoria == "Veículos"
    assert linha.dispositivo_legal_ref == "LCP 214/2025, art. 409, §1º, I, Anexo XVII"
    assert linha.condicao_embalagem_primaria_ref is None
    assert linha.excecao_uso_ref is not None


def test_buscar_incidencia_is_por_prefixo_traz_a_condicao_de_embalagem(conexao):
    linhas = buscar_incidencia_is_por_prefixo(conexao, ["2402"])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.categoria == "Produtos fumígenos"
    assert linha.condicao_embalagem_primaria_ref is not None


def test_excecao_do_codigo_8802_60_00_esta_marcada(conexao):
    linhas = buscar_incidencia_is_por_prefixo(conexao, ["88026000"])
    excecoes = [linha for linha in linhas if linha.excecao]
    assert len(excecoes) == 1


def test_lista_vazia_de_prefixos_nao_abre_query(conexao):
    assert buscar_incidencia_is_por_prefixo(conexao, []) == []


def test_nenhuma_tabela_anterior_regrediu(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM anexos_reducao")
        assert cur.fetchone()[0] == 321
        cur.execute("SELECT count(*) FROM anexos_reducao_ncm")
        assert cur.fetchone()[0] == 540
        cur.execute("SELECT count(*) FROM anexos_reducao_nbs")
        assert cur.fetchone()[0] == 91
        cur.execute("SELECT count(*) FROM anexos_reducao_nbs_prefixo")
        assert cur.fetchone()[0] == 90
