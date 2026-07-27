"""`aliquotas_ipi_tipi` contra PostgreSQL real — mesmo padrão de
`test_schema_postgres.py`: pula sem `DATABASE_URL`, roda de verdade no CI.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from db.repositorio import buscar_ipi_por_ncm
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


# buscar_ipi_por_ncm — o lookup que /v1/tax/simulate faz -------------------


class CursorEspiao:
    """Conta `execute` sobre a conexão real: AT-004 ("1 query, não N") precisa
    ser verificado contra o driver de verdade, não só contra um fake — é lá que
    um laço acidental viraria 100 round-trips ao Cloud SQL."""

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


@pytest.fixture
def tipi_gravada(conexao):
    gravar_tipi(
        conexao,
        [
            LinhaTipi("9999.99.10", "com alíquota", Decimal("0.0325"), False),
            LinhaTipi("9999.99.11", "não tributado", None, True),
            LinhaTipi("9999.99.12", "zero explícito", Decimal(0), False),
        ],
        FONTE,
    )
    return conexao


def test_lote_misto_resolve_presentes_e_omite_ausente(tipi_gravada):
    """NCM ausente simplesmente não aparece no dicionário — é assim que
    `api/ipi.py` distingue ausência (dicionário sem a chave) de falha
    (exceção), a distinção que a Decisão 6 existe para preservar."""
    resultado = buscar_ipi_por_ncm(
        tipi_gravada, ["9999.99.10", "9999.99.11", "0000.00.00"]
    )

    assert set(resultado) == {"9999.99.10", "9999.99.11"}
    assert resultado["9999.99.10"].aliquota_percentual == Decimal("0.03250")
    assert resultado["9999.99.10"].nao_tributado is False
    assert resultado["9999.99.10"].dispositivo_legal_ref == FONTE


def test_nao_tributado_vem_com_aliquota_nula_do_banco(tipi_gravada):
    """A CHECK `aliquota_xor_nao_tributado` garante isso no schema; aqui se
    prova que o lookup preserva a distinção em vez de achatar NT em 0%."""
    linha = buscar_ipi_por_ncm(tipi_gravada, ["9999.99.11"])["9999.99.11"]

    assert linha.nao_tributado is True
    assert linha.aliquota_percentual is None


def test_zero_explicito_e_distinto_de_nao_tributado(tipi_gravada):
    linha = buscar_ipi_por_ncm(tipi_gravada, ["9999.99.12"])["9999.99.12"]

    assert linha.nao_tributado is False
    assert linha.aliquota_percentual == Decimal("0.00000")


def test_tipo_decimal_preservado_sem_virar_float(tipi_gravada):
    """NUMERIC(7,5) precisa chegar como Decimal: um float aqui reintroduziria
    erro de arredondamento binário num cálculo tributário."""
    linha = buscar_ipi_por_ncm(tipi_gravada, ["9999.99.10"])["9999.99.10"]

    assert isinstance(linha.aliquota_percentual, Decimal)


def test_n_ncms_distintos_em_exatamente_uma_query(tipi_gravada):
    espiao = CursorEspiao(tipi_gravada)

    resultado = buscar_ipi_por_ncm(espiao, ["9999.99.10", "9999.99.11", "9999.99.12"])

    assert espiao.execucoes == 1
    assert len(resultado) == 3


def test_lista_vazia_nao_abre_cursor(tipi_gravada):
    espiao = CursorEspiao(tipi_gravada)

    assert buscar_ipi_por_ncm(espiao, []) == {}
    assert espiao.execucoes == 0
