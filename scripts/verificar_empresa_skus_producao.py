"""Prova que o papel de RUNTIME (taxreformai_app) consegue ESCREVER em
empresa_skus com RLS corretamente aplicado — primeira feature com CRUD de
escrita desde SCHEMA_POSTGRESQL (toda feature anterior só LIA tabela pública
de referência, sem tenant).

Cria um tenant de teste com DATABASE_URL (admin, mesmo padrão de
verificar_rls_producao.py — o papel de runtime não precisa criar tenants,
só operar sobre `empresa_skus`), depois conecta como taxreformai_app
(DATABASE_URL_APP) para exercitar create/get/list/update/upsert/delete via
db/repositorio.py — as MESMAS funções que a API usa, nunca SQL ad-hoc.

Roda só via migrar_banco.yml, workflow_dispatch com verificar_empresa_skus=sim.
"""

import os
import sys
import uuid

import psycopg

from db.repositorio import (
    atualizar_sku,
    buscar_sku,
    buscar_skus_por_codigo,
    criar_sku,
    excluir_sku,
    listar_skus,
    upsert_sku,
)

PAPEL_ESPERADO = "taxreformai_app"


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    admin_dsn = os.environ.get("DATABASE_URL")
    app_dsn = os.environ.get("DATABASE_URL_APP")
    if not admin_dsn or not app_dsn:
        _falhar("DATABASE_URL e DATABASE_URL_APP ambos necessários.")

    admin = psycopg.connect(admin_dsn)
    slug = f"_verificacao_skus_{uuid.uuid4().hex[:8]}"
    slug_b = f"_verificacao_skus_b_{uuid.uuid4().hex[:8]}"
    tenant_id = None
    tenant_id_b = None

    try:
        with admin.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (slug, nome) VALUES (%s, 'verificação SKUs') RETURNING id",
                (slug,),
            )
            tenant_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO tenants (slug, nome) VALUES (%s, 'verificação SKUs B') RETURNING id",
                (slug_b,),
            )
            tenant_id_b = cur.fetchone()[0]
        admin.commit()

        app_conn = psycopg.connect(app_dsn)
        with app_conn.cursor() as cur:
            cur.execute("SELECT current_user")
            papel = cur.fetchone()[0]
        print(f"Conectado como {papel!r}.")
        if papel != PAPEL_ESPERADO:
            _falhar(f"conectado como {papel!r}, esperado {PAPEL_ESPERADO!r}.")

        sku = criar_sku(
            app_conn, tenant_id, "VERIF-001", "Produto de verificação",
            "MERCADORIA", "22030000", None,
        )
        if sku.codigo_sku != "VERIF-001" or sku.ncm_code != "22030000":
            _falhar(f"criação de SKU MERCADORIA não retornou os dados esperados: {sku}")

        criar_sku(
            app_conn, tenant_id, "VERIF-002", "Serviço de verificação",
            "SERVICO", None, "120100000",
        )

        encontrado = buscar_sku(app_conn, tenant_id, "VERIF-001")
        if encontrado is None or encontrado.ncm_code != "22030000":
            _falhar("consulta não encontrou o SKU recém-criado com os dados esperados.")

        _itens, total = listar_skus(app_conn, tenant_id, 1, 50)
        if total != 2:
            _falhar(f"esperava 2 SKUs cadastrados, listagem reportou {total}.")

        atualizado = atualizar_sku(
            app_conn, tenant_id, "VERIF-001", "Produto atualizado",
            "MERCADORIA", "22030000", None,
        )
        if atualizado is None or atualizado.descricao != "Produto atualizado":
            _falhar("atualização (PATCH) não persistiu a nova descrição.")

        _sku1, foi_criado_1 = upsert_sku(
            app_conn, tenant_id, "VERIF-001", "Produto via upsert",
            "MERCADORIA", "22030000", None,
        )
        _sku3, foi_criado_3 = upsert_sku(
            app_conn, tenant_id, "VERIF-003", "Novo via upsert",
            "MERCADORIA", "22030000", None,
        )
        if foi_criado_1 or not foi_criado_3:
            _falhar(
                "upsert não distinguiu ATUALIZAÇÃO de CRIAÇÃO "
                f"(foi_criado_1={foi_criado_1}, esperado False; "
                f"foi_criado_3={foi_criado_3}, esperado True)."
            )

        lote = buscar_skus_por_codigo(
            app_conn, tenant_id, ["VERIF-001", "VERIF-002", "SKU-INEXISTENTE"]
        )
        if set(lote) != {"VERIF-001", "VERIF-002"}:
            _falhar(f"lookup em lote devolveu {set(lote)!r}, esperado VERIF-001/VERIF-002.")

        apagado = excluir_sku(app_conn, tenant_id, "VERIF-002")
        if not apagado or buscar_sku(app_conn, tenant_id, "VERIF-002") is not None:
            _falhar("exclusão não removeu o SKU (ou não confirmou remoção).")

        # Achado do security-reviewer antes do /ship: as verificações acima
        # provam que o CRUD FUNCIONA, mas não que o RLS ISOLA entre tenants —
        # mesma disciplina de verificar_rls_producao.py, aqui repetida contra
        # a tabela de escrita nova. O tenant B nunca deve enxergar, atualizar
        # ou apagar o que o tenant A criou.
        criar_sku(
            app_conn, tenant_id_b, "VERIF-B-1", "Produto do tenant B",
            "MERCADORIA", "22030000", None,
        )
        if buscar_sku(app_conn, tenant_id_b, "VERIF-001") is not None:
            _falhar("RLS falhou: tenant B enxergou um SKU criado pelo tenant A.")
        if excluir_sku(app_conn, tenant_id_b, "VERIF-001"):
            _falhar("RLS falhou: tenant B conseguiu EXCLUIR um SKU do tenant A.")
        if atualizar_sku(
            app_conn, tenant_id_b, "VERIF-001", "Hackeado", "MERCADORIA", "22030000", None
        ) is not None:
            _falhar("RLS falhou: tenant B conseguiu ATUALIZAR um SKU do tenant A.")
        _itens_b, total_b = listar_skus(app_conn, tenant_id_b, 1, 50)
        if total_b != 1 or _itens_b[0].codigo_sku != "VERIF-B-1":
            _falhar(f"RLS falhou: listagem do tenant B devolveu {total_b} item(ns), esperado 1 (só o próprio).")
        lote_cross_tenant = buscar_skus_por_codigo(app_conn, tenant_id_b, ["VERIF-001", "VERIF-003"])
        if lote_cross_tenant:
            _falhar(f"RLS falhou: lookup em lote do tenant B enxergou SKUs de A: {set(lote_cross_tenant)!r}.")
        if buscar_sku(app_conn, tenant_id, "VERIF-001") is None:
            _falhar("SKU do tenant A desapareceu depois das tentativas de escrita do tenant B.")

        app_conn.close()
        print(
            "EMPRESA_SKUS VERIFICADO CONTRA O CLOUD SQL REAL: o papel de runtime "
            "criou, consultou, listou, atualizou, upsertou (lote) e excluiu SKUs "
            "via db/repositorio.py, com RLS aplicado — incluindo isolamento "
            "comprovado entre dois tenants (leitura, escrita e exclusão)."
        )
    finally:
        with admin.cursor() as cur:
            if tenant_id is not None:
                cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
            if tenant_id_b is not None:
                cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id_b,))
        admin.commit()
        admin.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
