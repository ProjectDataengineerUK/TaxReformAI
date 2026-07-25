"""Testes do schema contra PostgreSQL REAL.

São pulados quando não há banco (`DATABASE_URL` ausente ou `psycopg` não
instalado), o que é o caso deste sandbox. No CI o job sobe um container de
serviço `postgres` e eles rodam de verdade.

SQLite não serviria: não tem RLS, não tem JSONB, e trata NUMERIC como float —
os três pontos que estes testes existem para verificar. Um teste que passa
contra o banco errado dá confiança falsa, que é pior que nenhuma cobertura.
"""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import UUID

import pytest

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
    # Limpa entre testes: RLS impede DELETE sem tenant declarado, então as
    # tabelas com policy precisam de TRUNCATE, que não passa por policy.
    with con.cursor() as cur:
        cur.execute(
            "TRUNCATE pareceres_audit_log, empresa_skus, "
            "regras_tributarias_cache, tenants CASCADE"
        )
    con.commit()
    con.close()


@pytest.fixture
def dois_tenants(conexao) -> tuple[UUID, UUID]:
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO tenants (slug, nome) VALUES ('acme', 'Acme') RETURNING id"
        )
        a = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO tenants (slug, nome) VALUES ('globex', 'Globex') RETURNING id"
        )
        b = cur.fetchone()[0]
    conexao.commit()
    return a, b


# --- Asserção 1 do DESIGN: RLS isola tenants ---


def test_rls_esconde_linhas_de_outro_tenant_mesmo_sem_where(conexao, dois_tenants):
    """A garantia inteira da Decisão 4. Um SELECT sem WHERE — o erro que a
    aplicação vai cometer mais cedo ou mais tarde — não pode vazar dados."""
    from db.repositorio import ParecerAuditado, registrar_parecer, sessao_do_tenant

    acme, globex = dois_tenants
    for tenant, texto in ((acme, "consulta da Acme"), (globex, "consulta da Globex")):
        registrar_parecer(
            conexao,
            ParecerAuditado(
                tenant_id=tenant,
                prompt_consulta=texto,
                resposta_parecer_md="parecer",
                contexto_recuperado_ids=[],
                payload_calculo={},
            ),
        )

    with sessao_do_tenant(conexao, acme) as cur:
        cur.execute("SELECT prompt_consulta FROM pareceres_audit_log")
        visiveis = [linha[0] for linha in cur.fetchall()]

    assert visiveis == ["consulta da Acme"]


def test_sem_tenant_declarado_nada_e_visivel(conexao, dois_tenants):
    """Padrão seguro: conexão que não declarou o tenant não enxerga nada, em
    vez de enxergar tudo."""
    from db.repositorio import ParecerAuditado, registrar_parecer

    acme, _ = dois_tenants
    registrar_parecer(
        conexao,
        ParecerAuditado(
            tenant_id=acme,
            prompt_consulta="x",
            resposta_parecer_md="y",
            contexto_recuperado_ids=[],
            payload_calculo={},
        ),
    )

    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM pareceres_audit_log")
        total = cur.fetchone()[0]
    conexao.commit()

    assert total == 0


def test_nao_da_para_gravar_no_tenant_de_outro(conexao, dois_tenants):
    """WITH CHECK: declarar um tenant e inserir com outro tenant_id é violação,
    não gravação silenciosa no lugar errado."""
    from db.repositorio import sessao_do_tenant

    acme, globex = dois_tenants
    with pytest.raises(psycopg.errors.Error):
        with sessao_do_tenant(conexao, acme) as cur:
            cur.execute(
                "INSERT INTO pareceres_audit_log "
                "(tenant_id, prompt_consulta, resposta_parecer_md) VALUES (%s, 'x', 'y')",
                (str(globex),),
            )


# --- Asserção 2: alíquota NULL é aceita ---


def test_aliquota_nula_e_aceita_e_volta_como_none(conexao):
    """Contra o blueprint, que declara NOT NULL. A CBS de 2027-2028 não tem
    número fixado em lei (art. 347) — se NOT NULL sobrevivesse, gravar a fase
    2027 exigiria inventar um percentual."""
    from db.repositorio import buscar_regra_cache

    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO regras_tributarias_cache
                (ncm_code, ano_vigencia, aliquota_ibs, aliquota_cbs, aliquota_is,
                 fonte_legal_ibs, fonte_legal_cbs, dispositivo_legal_ref, confirmado_em_lei)
            VALUES ('22030000', 2027, 0.001, NULL, NULL,
                    'LCP 214/2025, art. 344', 'LCP 214/2025, art. 347', 'LCP 214/2025', FALSE)
            """
        )
    conexao.commit()

    regra = buscar_regra_cache(conexao, "22030000", 2027)

    assert regra is not None
    assert regra.aliquota_ibs == Decimal("0.00100")
    assert regra.aliquota_cbs is None
    assert regra.tributos_indisponiveis() == ["CBS", "IS"]
    assert "art. 347" in regra.fonte_legal_cbs


# --- Asserção 3: migrações idempotentes e ordenadas ---


def test_migracoes_rodam_uma_vez_so(conexao):
    from db.migrador import aplicar_migracoes, listar_migracoes

    assert aplicar_migracoes(conexao) == [], "fixture já aplicou tudo"

    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        registradas = cur.fetchone()[0]
    conexao.commit()

    assert registradas == len(listar_migracoes())


def test_migracoes_ordenam_pelo_prefixo_numerico():
    """`glob` não garante ordem; aplicar 002 (RLS) antes de 001 (tabelas)
    falharia só em algumas máquinas."""
    from db.migrador import listar_migracoes

    versoes = [m.versao for m in listar_migracoes()]

    assert versoes == sorted(versoes)
    assert versoes[0].startswith("001")


# --- Asserção 4: NUMERIC preserva precisão ---


def test_numeric_preserva_aliquota_sem_virar_float(conexao):
    """0,0009 arredondado é erro de cálculo tributário, não detalhe."""
    from db.repositorio import buscar_regra_cache

    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO regras_tributarias_cache
                (ncm_code, ano_vigencia, aliquota_cbs, dispositivo_legal_ref)
            VALUES ('99999999', 2026, 0.00090, 'teste de precisão')
            """
        )
    conexao.commit()

    regra = buscar_regra_cache(conexao, "99999999", 2026)

    assert isinstance(regra.aliquota_cbs, Decimal)
    assert regra.aliquota_cbs == Decimal("0.00090")


# --- Asserção 5: JSONB do audit log ---


def test_audit_log_preserva_jsonb(conexao, dois_tenants):
    from db.repositorio import ParecerAuditado, registrar_parecer, sessao_do_tenant

    acme, _ = dois_tenants
    payload = {"ano": 2026, "itens": [{"sku": "A-1", "valor": "100.00"}]}
    contexto = ["chunk-1", "chunk-2"]

    registrar_parecer(
        conexao,
        ParecerAuditado(
            tenant_id=acme,
            prompt_consulta="quanto de CBS?",
            resposta_parecer_md="**parecer**",
            contexto_recuperado_ids=contexto,
            payload_calculo=payload,
        ),
    )

    with sessao_do_tenant(conexao, acme) as cur:
        cur.execute(
            "SELECT payload_calculo_json, contexto_recuperado_ids FROM pareceres_audit_log"
        )
        gravado, ids = cur.fetchone()

    assert gravado == payload
    assert ids == contexto


# --- Decisão 2: resolução de tenant por UUID ou slug ---


def test_resolver_tenant_aceita_uuid_e_slug(conexao, dois_tenants):
    """A transição do secret API_KEYS depende disso: a API em produção manda
    slug, o schema exige UUID, e o serviço não pode cair no meio."""
    from db.repositorio import resolver_tenant

    acme, _ = dois_tenants

    assert resolver_tenant(conexao, str(acme)) == acme
    assert resolver_tenant(conexao, "acme") == acme
    assert resolver_tenant(conexao, "inexistente") is None


def test_tenant_inativo_nao_resolve(conexao, dois_tenants):
    from db.repositorio import resolver_tenant

    acme, _ = dois_tenants
    with conexao.cursor() as cur:
        cur.execute("UPDATE tenants SET ativo = FALSE WHERE id = %s", (str(acme),))
    conexao.commit()

    assert resolver_tenant(conexao, "acme") is None


def test_sku_duplicado_no_mesmo_tenant_e_rejeitado(conexao, dois_tenants):
    """Mesmo SKU repetido dentro do tenant é ambiguidade na simulação."""
    from db.repositorio import sessao_do_tenant

    acme, _ = dois_tenants
    with sessao_do_tenant(conexao, acme) as cur:
        cur.execute(
            "INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, ncm_code) "
            "VALUES (%s, 'SKU-1', 'Produto', '22030000')",
            (str(acme),),
        )

    with pytest.raises(psycopg.errors.UniqueViolation):
        with sessao_do_tenant(conexao, acme) as cur:
            cur.execute(
                "INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, ncm_code) "
                "VALUES (%s, 'SKU-1', 'Outro', '99999999')",
                (str(acme),),
            )


def test_mesmo_sku_em_tenants_diferentes_e_permitido(conexao, dois_tenants):
    """Clientes diferentes usam os mesmos códigos internos o tempo todo."""
    from db.repositorio import sessao_do_tenant

    acme, globex = dois_tenants
    for tenant in (acme, globex):
        with sessao_do_tenant(conexao, tenant) as cur:
            cur.execute(
                "INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, ncm_code) "
                "VALUES (%s, 'SKU-COMUM', 'Produto', '22030000')",
                (str(tenant),),
            )

    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM empresa_skus")
    conexao.commit()
