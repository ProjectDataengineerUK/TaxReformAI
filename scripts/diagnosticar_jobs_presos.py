"""Lista jobs de upload de SKUs presos em PROCESSANDO, com id/tenant/idade.

Complementa o agregado que `observabilidade/status.py::status_cloud_tasks`
já expõe no painel (`/v1/observabilidade/status`, aba Sentinela): o painel
só diz "há N job(s) preso(s)", este script diz QUAIS — para decidir uma
limpeza manual (marcar ERRO, excluir) sem precisar de acesso direto ao
Cloud SQL.

Só leitura — nunca faz UPDATE/DELETE. Roda via workflow_dispatch
(diagnosticar_jobs_presos.yml), mesma disciplina de todo outro script de
infraestrutura real deste projeto (nunca local).
"""

import os
import sys
from datetime import UTC, datetime

import psycopg

from db.repositorio import sessao_do_tenant

LIMIAR_PRESO_MINUTOS = 20


def main() -> None:
    app_dsn = os.environ.get("DATABASE_URL_APP")
    if not app_dsn:
        print("FALHA: DATABASE_URL_APP necessário.", file=sys.stderr)
        sys.exit(1)

    conexao = psycopg.connect(app_dsn)
    with conexao.cursor() as cur:
        cur.execute("SELECT current_user")
        papel = cur.fetchone()[0]
    print(f"Conectado como {papel!r}.\n")

    with conexao.cursor() as cur:
        cur.execute("SELECT id, slug FROM tenants ORDER BY slug")
        tenants = cur.fetchall()

    agora = datetime.now(UTC)
    achados = []
    for tenant_id, slug in tenants:
        with sessao_do_tenant(conexao, tenant_id) as cur:
            cur.execute(
                """
                SELECT id, gcs_uri_arquivo, created_at, updated_at
                FROM sku_upload_jobs
                WHERE status = 'PROCESSANDO'
                ORDER BY created_at
                """
            )
            for job_id, gcs_uri, created_at, updated_at in cur.fetchall():
                idade = agora - created_at
                achados.append((tenant_id, slug, job_id, gcs_uri, created_at, updated_at, idade))

    conexao.close()

    if not achados:
        print("Nenhum job em PROCESSANDO — fila normal.")
        return

    print(f"{len(achados)} job(s) em PROCESSANDO:\n")
    presos = 0
    for tenant_id, slug, job_id, gcs_uri, created_at, updated_at, idade in achados:
        minutos = int(idade.total_seconds() // 60)
        marcador = ""
        if idade.total_seconds() >= LIMIAR_PRESO_MINUTOS * 60:
            marcador = " <- PRESO (provável órfão de OOM/SIGKILL)"
            presos += 1
        print(f"  job_id       = {job_id}")
        print(f"  tenant       = {slug} ({tenant_id})")
        print(f"  arquivo      = {gcs_uri}")
        print(f"  criado_em    = {created_at.isoformat()}")
        print(f"  atualizado_em= {updated_at.isoformat()}")
        print(f"  idade        = {minutos}min{marcador}")
        print()

    print(f"Resumo: {presos}/{len(achados)} preso(s) há mais de {LIMIAR_PRESO_MINUTOS}min.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
