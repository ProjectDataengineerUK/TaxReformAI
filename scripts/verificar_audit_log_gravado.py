"""Confirma que o serviço deployado gravou o audit log de verdade, depois do
POST /v1/tax/simulate do smoke test em deploy.yml.

Verifica o SKU marcador em vez de "existe alguma linha": a tabela pode ter
lixo de execuções anteriores, e "existe alguma linha" seria uma prova fraca
de que ESTA execução do smoke test gravou algo.
"""

import os
import sys

import psycopg

from db.repositorio import resolver_tenant, sessao_do_tenant


def main(tenant_slug: str, sku_marcador: str) -> None:
    conexao = psycopg.connect(os.environ["DATABASE_URL"])

    tenant_id = resolver_tenant(conexao, tenant_slug)
    if tenant_id is None:
        print(
            f"FALHA: tenant {tenant_slug!r} não está cadastrado em `tenants` "
            "— rode migrar_banco.yml (scripts/popular_tenants.py) antes do deploy.",
            file=sys.stderr,
        )
        sys.exit(1)

    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            "SELECT id, created_at FROM pareceres_audit_log "
            "WHERE tenant_id = %s AND payload_calculo_json::text LIKE %s "
            "ORDER BY created_at DESC LIMIT 1",
            (str(tenant_id), f"%{sku_marcador}%"),
        )
        linha = cur.fetchone()

    conexao.close()

    if linha is None:
        print(
            f"FALHA: nenhum parecer com {sku_marcador!r} encontrado para o tenant "
            f"{tenant_slug!r}. A API respondeu ao smoke test mas não gravou audit log.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"OK audit log: parecer {linha[0]} gravado em {linha[1]}.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("uso: verificar_audit_log_gravado.py <tenant_slug> <sku_marcador>", file=sys.stderr)
        sys.exit(2)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
