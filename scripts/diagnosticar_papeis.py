"""Diagnóstico temporário: por que 003_papel_da_aplicacao.sql falhou com
"permission denied to alter role" no Cloud SQL real (nunca falhou no
container postgres:16 do CI). Roda uma vez via migrar_banco.yml, depois é
removido."""

import os

import psycopg

conexao = psycopg.connect(os.environ["DATABASE_URL"])
with conexao.cursor() as cur:
    cur.execute(
        "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolinherit "
        "FROM pg_roles WHERE rolname IN "
        "('taxreformai_admin','taxreformai_app','postgres','cloudsqlsuperuser')"
    )
    for linha in cur.fetchall():
        print(linha)

    print("--- memberships de taxreformai_admin ---")
    cur.execute(
        "SELECT r.rolname AS grupo, m.admin_option "
        "FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.roleid "
        "WHERE m.member = 'taxreformai_admin'::regrole"
    )
    for linha in cur.fetchall():
        print(linha)

    print("--- memberships de taxreformai_app ---")
    cur.execute(
        "SELECT r.rolname AS grupo, m.admin_option "
        "FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.roleid "
        "WHERE m.member = 'taxreformai_app'::regrole"
    )
    for linha in cur.fetchall():
        print(linha)
conexao.close()
