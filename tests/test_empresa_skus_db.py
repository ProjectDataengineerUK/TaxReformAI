"""CRUD de `empresa_skus` contra PostgreSQL REAL, via `db/repositorio.py` —
mesmas funções que a API usa, nunca SQL ad-hoc. Primeira feature com RLS de
ESCRITA testada ponta a ponta (as duas asserções pré-existentes em
`test_schema_postgres.py` só provam a UNIQUE constraint em SQL cru).

Pula sem `DATABASE_URL`, roda de verdade no CI contra um container `postgres:16`
com o papel NÃO-superusuário (RLS é ignorado por superusuário — ver
`test_schema_postgres.py` para o porquê).
"""

from __future__ import annotations

import os
from uuid import UUID

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado")

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL ausente — sem PostgreSQL para testar"
)

PAPEL_APP = "taxreformai_app_teste_skus"
SENHA_APP = "senha-de-teste"


def _preparar_papel_da_aplicacao(admin) -> str:
    with admin.cursor() as cur:
        cur.execute(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{PAPEL_APP}') THEN
                    CREATE ROLE {PAPEL_APP} LOGIN PASSWORD '{SENHA_APP}';
                END IF;
            END $$
            """
        )
        cur.execute(f"GRANT USAGE ON SCHEMA public TO {PAPEL_APP}")
        cur.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            f"IN SCHEMA public TO {PAPEL_APP}"
        )
    admin.commit()
    return DATABASE_URL.replace("postgres:postgres@", f"{PAPEL_APP}:{SENHA_APP}@")


@pytest.fixture
def conexao():
    from db.migrador import aplicar_migracoes

    admin = psycopg.connect(DATABASE_URL)
    aplicar_migracoes(admin)
    url_app = _preparar_papel_da_aplicacao(admin)
    admin.close()

    con = psycopg.connect(url_app)
    yield con
    con.close()
    admin = psycopg.connect(DATABASE_URL)
    with admin.cursor() as cur:
        cur.execute("TRUNCATE pareceres_audit_log, empresa_skus, tenants CASCADE")
    admin.commit()
    admin.close()


@pytest.fixture
def dois_tenants(conexao) -> tuple[UUID, UUID]:
    with conexao.cursor() as cur:
        cur.execute("INSERT INTO tenants (slug, nome) VALUES ('acme', 'Acme') RETURNING id")
        a = cur.fetchone()[0]
        cur.execute("INSERT INTO tenants (slug, nome) VALUES ('globex', 'Globex') RETURNING id")
        b = cur.fetchone()[0]
    conexao.commit()
    return a, b


def test_criar_sku_mercadoria(conexao, dois_tenants):
    from db.repositorio import criar_sku

    acme, _ = dois_tenants
    sku = criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    assert sku.codigo_sku == "SKU-1"
    assert sku.ncm_code == "22030000"
    assert sku.nbs_code is None


def test_criar_sku_servico(conexao, dois_tenants):
    from db.repositorio import criar_sku

    acme, _ = dois_tenants
    sku = criar_sku(conexao, acme, "SKU-2", "Serviço", "SERVICO", None, "122010000")
    assert sku.nbs_code == "122010000"
    assert sku.ncm_code is None


def test_check_constraint_rejeita_exclusividade_violada(conexao, dois_tenants):
    """CHECK da migração 014 — prova no BANCO, não só na validação da API."""
    from db.repositorio import sessao_do_tenant

    acme, _ = dois_tenants
    with pytest.raises(psycopg.errors.CheckViolation):
        with sessao_do_tenant(conexao, acme) as cur:
            cur.execute(
                "INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code) "
                "VALUES (%s, 'SKU-X', 'x', 'MERCADORIA', '22030000', '122010000')",
                (str(acme),),
            )


def test_criar_sku_duplicado_levanta_unique_violation(conexao, dois_tenants):
    from db.repositorio import criar_sku

    acme, _ = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    with pytest.raises(psycopg.errors.UniqueViolation):
        criar_sku(conexao, acme, "SKU-1", "Outro", "MERCADORIA", "99999999", None)


def test_buscar_sku_de_outro_tenant_e_none(conexao, dois_tenants):
    """RLS de ESCRITA: um SKU criado por A é invisível para B — sem `WHERE
    tenant_id=` explícito em `buscar_sku`, o isolamento vem inteiramente da
    policy."""
    from db.repositorio import buscar_sku, criar_sku

    acme, globex = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    assert buscar_sku(conexao, globex, "SKU-1") is None
    assert buscar_sku(conexao, acme, "SKU-1") is not None


def test_listar_skus_isolado_por_tenant(conexao, dois_tenants):
    from db.repositorio import criar_sku, listar_skus

    acme, globex = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "P1", "MERCADORIA", "22030000", None)
    criar_sku(conexao, acme, "SKU-2", "P2", "MERCADORIA", "22030000", None)
    criar_sku(conexao, globex, "SKU-3", "P3", "MERCADORIA", "22030000", None)

    itens_acme, total_acme = listar_skus(conexao, acme, 1, 50)
    assert total_acme == 2
    assert {i.codigo_sku for i in itens_acme} == {"SKU-1", "SKU-2"}

    _itens_globex, total_globex = listar_skus(conexao, globex, 1, 50)
    assert total_globex == 1


def test_listar_skus_paginacao(conexao, dois_tenants):
    from db.repositorio import criar_sku, listar_skus

    acme, _ = dois_tenants
    for i in range(5):
        criar_sku(conexao, acme, f"SKU-{i}", f"P{i}", "MERCADORIA", "22030000", None)

    pagina1, total = listar_skus(conexao, acme, 1, 2)
    pagina2, _ = listar_skus(conexao, acme, 2, 2)
    assert total == 5
    assert len(pagina1) == 2
    assert len(pagina2) == 2
    assert {i.codigo_sku for i in pagina1}.isdisjoint({i.codigo_sku for i in pagina2})


def test_atualizar_sku(conexao, dois_tenants):
    from db.repositorio import atualizar_sku, criar_sku

    acme, _ = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    atualizado = atualizar_sku(conexao, acme, "SKU-1", "Produto novo", "MERCADORIA", "22030000", None)
    assert atualizado.descricao == "Produto novo"


def test_atualizar_sku_de_outro_tenant_nao_afeta_nada(conexao, dois_tenants):
    from db.repositorio import atualizar_sku, buscar_sku, criar_sku

    acme, globex = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    resultado = atualizar_sku(conexao, globex, "SKU-1", "Hackeado", "MERCADORIA", "22030000", None)
    assert resultado is None
    assert buscar_sku(conexao, acme, "SKU-1").descricao == "Produto"


def test_excluir_sku(conexao, dois_tenants):
    from db.repositorio import buscar_sku, criar_sku, excluir_sku

    acme, _ = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    assert excluir_sku(conexao, acme, "SKU-1") is True
    assert buscar_sku(conexao, acme, "SKU-1") is None
    assert excluir_sku(conexao, acme, "SKU-1") is False


def test_excluir_sku_de_outro_tenant_nao_remove(conexao, dois_tenants):
    from db.repositorio import buscar_sku, criar_sku, excluir_sku

    acme, globex = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    assert excluir_sku(conexao, globex, "SKU-1") is False
    assert buscar_sku(conexao, acme, "SKU-1") is not None


def test_upsert_sku_distingue_criacao_de_atualizacao(conexao, dois_tenants):
    from db.repositorio import upsert_sku

    acme, _ = dois_tenants
    _sku1, foi_criado_1 = upsert_sku(conexao, acme, "SKU-1", "Produto", "MERCADORIA", "22030000", None)
    _sku2, foi_criado_2 = upsert_sku(conexao, acme, "SKU-1", "Produto atualizado", "MERCADORIA", "99999999", None)
    assert foi_criado_1 is True
    assert foi_criado_2 is False
    assert _sku2.descricao == "Produto atualizado"
    assert _sku2.ncm_code == "99999999"


def test_buscar_skus_por_codigo_em_lote_isolado_por_tenant(conexao, dois_tenants):
    from db.repositorio import buscar_skus_por_codigo, criar_sku

    acme, globex = dois_tenants
    criar_sku(conexao, acme, "SKU-1", "P1", "MERCADORIA", "22030000", None)
    criar_sku(conexao, globex, "SKU-2", "P2", "MERCADORIA", "99999999", None)

    lote = buscar_skus_por_codigo(conexao, acme, ["SKU-1", "SKU-2"])
    assert set(lote) == {"SKU-1"}


def test_nenhuma_tabela_anterior_regrediu(conexao, dois_tenants):
    """Mesma disciplina de toda feature anterior — confirma que a migração
    014 não afetou contagens de tabelas já shipadas."""
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM anexos_reducao")
        assert cur.fetchone()[0] == 321
        cur.execute("SELECT count(*) FROM anexos_reducao_ncm")
        assert cur.fetchone()[0] == 540
        cur.execute("SELECT count(*) FROM anexos_reducao_nbs")
        assert cur.fetchone()[0] == 91
        cur.execute("SELECT count(*) FROM anexos_reducao_nbs_prefixo")
        assert cur.fetchone()[0] == 90
        cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia")
        assert cur.fetchone()[0] == 6
        cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia_ncm")
        assert cur.fetchone()[0] == 24
