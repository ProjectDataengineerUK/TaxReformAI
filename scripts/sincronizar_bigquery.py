"""Sincroniza pareceres_audit_log (Cloud SQL) -> BigQuery, incrementalmente.

Lê o watermark (MAX(created_at) já presente no BigQuery), busca linhas novas
de TODOS os tenants (via sessao_do_tenant, sem bypass de RLS — Decisão 2 do
DESIGN_BIGQUERY_DATA_WAREHOUSE.md) e faz MERGE por `id` numa tabela de
staging (Decisão 3 — garante idempotência mesmo em empate exato de
created_at, não só pela janela do watermark).

Roda via .github/workflows/sincronizar_bigquery.yml (schedule +
workflow_dispatch) — nunca localmente, mesma disciplina de todo outro
script de infraestrutura real deste projeto.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from google.cloud import bigquery

from db.repositorio import sessao_do_tenant

DATASET_ID = "taxreformai_analytics"
TABLE_ID = "pareceres_historico"
EPOCA = datetime(1970, 1, 1, tzinfo=UTC)


def linha_para_bigquery(row: tuple[Any, ...]) -> dict[str, Any]:
    """Converte uma linha de `pareceres_audit_log` (tupla do cursor) no dict
    que o BigQuery espera. Ordem das colunas fixada pela query em
    `buscar_linhas_novas` — mudar uma exige mudar a outra."""
    (
        id_,
        tenant_id,
        user_id,
        prompt_consulta,
        contexto_recuperado_ids,
        payload_calculo_json,
        resposta_parecer_md,
        created_at,
    ) = row
    return {
        "id": str(id_),
        "tenant_id": str(tenant_id),
        "user_id": str(user_id) if user_id is not None else None,
        "prompt_consulta": prompt_consulta,
        "contexto_recuperado_ids": contexto_recuperado_ids,
        "payload_calculo_json": payload_calculo_json,
        "resposta_parecer_md": resposta_parecer_md,
        "created_at": created_at.isoformat(),
    }


def watermark_atual(client: bigquery.Client, project_id: str) -> datetime:
    """`None` (tabela vazia) vira a época — sincroniza tudo desde o início."""
    query = f"SELECT MAX(created_at) AS wm FROM `{project_id}.{DATASET_ID}.{TABLE_ID}`"
    linha = next(iter(client.query(query).result()))
    return linha.wm or EPOCA


def buscar_linhas_novas(conexao, watermark: datetime) -> list[dict[str, Any]]:
    """Itera cada tenant via `sessao_do_tenant` — nenhum papel do Cloud SQL
    tem BYPASSRLS (confirmado contra a instância real em SCHEMA_POSTGRESQL),
    então não existe um único SELECT cross-tenant possível."""
    with conexao.cursor() as cur:
        cur.execute("SELECT id FROM tenants")
        tenant_ids = [linha[0] for linha in cur.fetchall()]

    linhas: list[dict[str, Any]] = []
    for tenant_id in tenant_ids:
        with sessao_do_tenant(conexao, tenant_id) as cur:
            cur.execute(
                """
                SELECT id, tenant_id, user_id, prompt_consulta,
                       contexto_recuperado_ids, payload_calculo_json,
                       resposta_parecer_md, created_at
                FROM pareceres_audit_log
                WHERE created_at > %s
                ORDER BY created_at
                """,
                (watermark,),
            )
            linhas.extend(linha_para_bigquery(row) for row in cur.fetchall())
    return linhas


def carregar_via_merge(client: bigquery.Client, project_id: str, linhas: list[dict[str, Any]]) -> None:
    """Staging + MERGE por `id`, não INSERT direto filtrado só por watermark:
    garante idempotência mesmo se duas linhas tiverem o MESMO created_at
    exato — o watermark é otimização de volume, não a chave de dedup real."""
    staging_id = f"staging_{uuid.uuid4().hex[:8]}"
    staging_ref = f"{project_id}.{DATASET_ID}.{staging_id}"
    tabela_destino = client.get_table(f"{project_id}.{DATASET_ID}.{TABLE_ID}")

    client.create_table(bigquery.Table(staging_ref, schema=tabela_destino.schema))
    try:
        # .result() bloqueia até o job terminar e levanta
        # google.api_core.exceptions.GoogleAPICallError se falhar — sem
        # verificação extra de "errors", o próprio SDK já falha alto.
        client.load_table_from_json(linhas, staging_ref).result()

        client.query(
            f"""
            MERGE `{project_id}.{DATASET_ID}.{TABLE_ID}` T
            USING `{staging_ref}` S
            ON T.id = S.id
            WHEN NOT MATCHED THEN INSERT ROW
            """
        ).result()
    finally:
        client.delete_table(staging_ref, not_found_ok=True)


def main() -> None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    dsn = os.environ.get("DATABASE_URL")
    if not project_id or not dsn:
        print("FALHA: GCP_PROJECT_ID e DATABASE_URL são obrigatórios.", file=sys.stderr)
        sys.exit(1)

    client = bigquery.Client(project=project_id)
    conexao = psycopg.connect(dsn)

    try:
        watermark = watermark_atual(client, project_id)
        linhas = buscar_linhas_novas(conexao, watermark)
    finally:
        conexao.close()

    if not linhas:
        print("Nenhuma linha nova desde o último sync.")
        return

    carregar_via_merge(client, project_id, linhas)
    print(f"OK: {len(linhas)} linha(s) sincronizada(s).")


if __name__ == "__main__":
    main()
