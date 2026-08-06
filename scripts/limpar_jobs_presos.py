"""Marca como ERRO os jobs de sku_upload_jobs identificados como órfãos por
scripts/diagnosticar_jobs_presos.py — SIGKILL (OOM) no worker nunca aciona o
`except` do endpoint interno, deixando o registro preso em PROCESSANDO para
sempre (achado documentado desde FILA_ASSINCRONA_CELERY_REDIS).

Usa `atualizar_job_upload`, a MESMA função que a API usa — nunca SQL ad-hoc
— e escreve por RLS via `sessao_do_tenant`, então só marca o que pertence ao
`tenant_id` informado.

IDs e tenant fixados no momento da limpeza (2026-08-06), confirmados por uma
run real de diagnosticar_jobs_presos.yml antes deste script existir. Roda só
via workflow_dispatch (limpar_jobs_presos.yml), nunca local.
"""

import os
import sys
from uuid import UUID

import psycopg

from db.repositorio import atualizar_job_upload, buscar_job_upload

TENANT_ID = UUID("32decf79-ae72-43db-8ce3-86a2cec08640")
JOBS_ORFAOS = [
    UUID("df4900b9-8d59-4e90-87a6-64886450a13c"),
    UUID("3793a83c-91f8-4159-a4e3-0c68c2d5c6c5"),
]
MOTIVO = {
    "erro": "Job marcado manualmente como ERRO — órfão de SIGKILL (OOM) no "
    "worker, nunca processado até o fim. Limpeza via "
    "scripts/limpar_jobs_presos.py, 2026-08-06."
}


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

    for job_id in JOBS_ORFAOS:
        antes = buscar_job_upload(conexao, TENANT_ID, job_id)
        if antes is None:
            print(f"{job_id}: não encontrado para o tenant {TENANT_ID} — pulando.")
            continue
        if antes.status != "PROCESSANDO":
            print(f"{job_id}: status já é {antes.status!r} (não é mais PROCESSANDO) — pulando.")
            continue

        atualizar_job_upload(conexao, TENANT_ID, job_id, "ERRO", MOTIVO)
        conexao.commit()

        depois = buscar_job_upload(conexao, TENANT_ID, job_id)
        if depois is None or depois.status != "ERRO":
            print(f"FALHA: {job_id} não confirmou status ERRO após o UPDATE.", file=sys.stderr)
            sys.exit(1)
        print(f"{job_id}: PROCESSANDO -> ERRO confirmado.")

    conexao.close()
    print("\nLimpeza concluída.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
