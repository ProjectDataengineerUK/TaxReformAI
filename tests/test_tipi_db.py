"""`aliquotas_ipi_tipi` contra PostgreSQL real — mesmo padrão de
`test_schema_postgres.py`: pula sem `DATABASE_URL`, roda de verdade no CI.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from db.tipi import LinhaTipi, gravar_tipi

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado")

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL ausente — sem PostgreSQL para testar"
)

FONTE = "teste"


@pytest.fixture
def conexao():
    from db.migrador import aplicar_migracoes

    con = psycopg.connect(DATABASE_URL)
    aplicar_migracoes(con)
    yield con
    with con.cursor() as cur:
        cur.execute("DELETE FROM aliquotas_ipi_tipi WHERE dispositivo_legal_ref = %s", (FONTE,))
    con.commit()
    con.close()


def test_grava_e_le_linha_com_aliquota(conexao):
    gravar_tipi(
        conexao,
        [LinhaTipi("9999.99.01", "produto de teste", Decimal("0.0325"), False)],
        FONTE,
    )

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT descricao, aliquota_percentual, nao_tributado "
            "FROM aliquotas_ipi_tipi WHERE ncm_code = '9999.99.01'"
        )
        linha = cur.fetchone()

    assert linha == ("produto de teste", Decimal("0.03250"), False)


def test_grava_linha_nao_tributada_sem_aliquota(conexao):
    gravar_tipi(conexao, [LinhaTipi("9999.99.02", "isento", None, True)], FONTE)

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT aliquota_percentual, nao_tributado FROM aliquotas_ipi_tipi "
            "WHERE ncm_code = '9999.99.02'"
        )
        linha = cur.fetchone()

    assert linha == (None, True)


def test_constraint_rejeita_aliquota_e_nao_tributado_juntos(conexao):
    """A CHECK constraint é a garantia real, não a disciplina do código
    Python: se `gravar_tipi` algum dia tiver um bug e tentar gravar as duas
    coisas ao mesmo tempo, o banco recusa em vez de aceitar dado incoerente."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO aliquotas_ipi_tipi "
                "(ncm_code, descricao, aliquota_percentual, nao_tributado, dispositivo_legal_ref) "
                "VALUES ('9999.99.03', 'x', 0.05, true, %s)",
                (FONTE,),
            )
    conexao.rollback()


def test_reingestao_atualiza_em_vez_de_duplicar(conexao):
    """A TIPI é reeditada por ADE da RFB; rodar a ingestão de novo precisa
    atualizar a alíquota existente, não empilhar histórico."""
    gravar_tipi(conexao, [LinhaTipi("9999.99.04", "v1", Decimal("0.05"), False)], FONTE)
    gravar_tipi(conexao, [LinhaTipi("9999.99.04", "v2 atualizada", Decimal("0.10"), False)], FONTE)

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT count(*), descricao, aliquota_percentual FROM aliquotas_ipi_tipi "
            "WHERE ncm_code = '9999.99.04' GROUP BY descricao, aliquota_percentual"
        )
        linhas = cur.fetchall()

    assert linhas == [(1, "v2 atualizada", Decimal("0.10000"))]


def test_gravar_tipi_em_lote_maior_que_o_tamanho_do_lote(conexao):
    """Prova o caminho de múltiplos lotes (não só o de um lote só) contra o
    banco real — mesma preocupação que motivou TAMANHO_LOTE_UPSERT no Qdrant.

    O código varia o CAPÍTULO (2 primeiros dígitos), não o sufixo: um NCM
    real nunca passa de 10 caracteres (NNNN.NN.NN), e i:02d estourando de 99
    para 100 já quebraria o formato — foi exatamente o bug que reprovou o CI
    na primeira versão deste teste.
    """
    linhas = [
        LinhaTipi(f"{8800 + i // 100:04d}.{i % 100:02d}.01", f"item {i}", Decimal("0.01"), False)
        for i in range(250)
    ]
    gravados = gravar_tipi(conexao, linhas, FONTE, lote=100)

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM aliquotas_ipi_tipi WHERE dispositivo_legal_ref = %s", (FONTE,)
        )
        total = cur.fetchone()[0]

    assert gravados == 250
    assert total == 250


def test_lista_vazia_nao_toca_o_banco(conexao):
    assert gravar_tipi(conexao, [], FONTE) == 0
