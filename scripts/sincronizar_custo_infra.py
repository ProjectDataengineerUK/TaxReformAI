"""Sincroniza custo de infra (GCP Billing Export -> Cloud SQL), diariamente.

Direção OPOSTA de scripts/sincronizar_bigquery.py: lê do BigQuery (dataset de
Billing Export, habilitado manualmente pelo usuário no Console — Decision 2
do DESIGN_PAINEL_OBSERVABILIDADE.md, não existe API que dê custo real por
serviço/dia diretamente) e escreve em `custo_infra_diario` (Cloud SQL).

Autentica no Postgres como `taxreformai_app`, não `taxreformai_admin`: este
job só escreve em 2 tabelas próprias (custo_infra_diario,
observabilidade_execucoes), sem precisar iterar tenants — privilégio mínimo
real, diferente de sincronizar_bigquery.py.

`INSERT ... ON CONFLICT DO UPDATE` é o upsert idempotente aqui — Postgres já
tem UPSERT nativo, dispensando o padrão staging+MERGE que o BigQuery exige
do lado de lá.

Roda via .github/workflows/sincronizar_custo_infra.yml (schedule +
workflow_dispatch) — nunca localmente, mesma disciplina de todo outro
script de infraestrutura real deste projeto.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import UTC, datetime, timedelta

import psycopg
from google.cloud import bigquery

logger = logging.getLogger(__name__)

LOOKBACK_DIAS = 7  # cobre revisões tardias que o próprio billing export documenta como possíveis


def _tabela_billing_export(client: bigquery.Client, project_id: str, dataset: str) -> str:
    """O nome exato da tabela de export detalhado inclui o ID da conta de
    billing (`gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`), que varia por
    conta — descoberto por prefixo em vez de fixado, para não exigir mais um
    valor manual do usuário além do nome do dataset."""
    for tabela in client.list_tables(f"{project_id}.{dataset}"):
        if tabela.table_id.startswith("gcp_billing_export_v1_"):
            return tabela.table_id
    raise RuntimeError(
        f"Nenhuma tabela 'gcp_billing_export_v1_*' encontrada em {project_id}.{dataset} — "
        "o export detalhado de billing precisa ser habilitado no Console GCP primeiro."
    )


def buscar_custo_por_servico(
    client: bigquery.Client, project_id: str, dataset: str, dias: int = LOOKBACK_DIAS
) -> list[tuple[str, str, float]]:
    tabela = _tabela_billing_export(client, project_id, dataset)
    data_inicio = (datetime.now(UTC) - timedelta(days=dias)).date()

    query = f"""
        SELECT
          service.description AS servico,
          DATE(usage_start_time) AS data,
          SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)) AS custo_usd
        FROM `{project_id}.{dataset}.{tabela}`
        WHERE DATE(usage_start_time) >= @data_inicio
        GROUP BY servico, data
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("data_inicio", "DATE", data_inicio)]
    )
    resultado = client.query(query, job_config=job_config).result()
    return [(linha.servico, linha.data.isoformat(), float(linha.custo_usd)) for linha in resultado]


def upsert_custo_infra(conexao, linhas: list[tuple[str, str, float]]) -> None:
    with conexao.cursor() as cur:
        for servico, data, custo_usd in linhas:
            cur.execute(
                """
                INSERT INTO custo_infra_diario (servico, data, custo_usd, sincronizado_em)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (servico, data)
                DO UPDATE SET custo_usd = EXCLUDED.custo_usd, sincronizado_em = NOW()
                """,
                (servico, data, custo_usd),
            )
    conexao.commit()


def _heartbeat(dsn: str, sucesso: bool, detalhe: str) -> None:
    from observabilidade.execucoes import registrar_execucao

    try:
        conexao = psycopg.connect(dsn)
        try:
            registrar_execucao(conexao, "sincronizar_custo_infra", sucesso, detalhe)
        finally:
            conexao.close()
    except Exception:
        logger.exception("Falha ao gravar heartbeat em observabilidade_execucoes")


def _sincronizar(project_id: str, dataset: str, dsn: str) -> str:
    client = bigquery.Client(project=project_id)
    linhas = buscar_custo_por_servico(client, project_id, dataset)

    if not linhas:
        print("Nenhum custo encontrado na janela consultada.")
        return "Nenhum custo encontrado na janela consultada."

    # Data Quality Gate (DESIGN): nenhuma linha com custo negativo — um valor
    # negativo aqui seria sinal de erro na query de créditos, não um desconto
    # legítimo maior que o custo bruto (isso já é raro e mereceria revisão
    # manual, não upsert silencioso).
    negativos = [linha for linha in linhas if linha[2] < 0]
    if negativos:
        raise ValueError(f"{len(negativos)} linha(s) com custo_usd negativo — abortando sync")

    conexao = psycopg.connect(dsn)
    try:
        upsert_custo_infra(conexao, linhas)
    finally:
        conexao.close()

    print(f"OK: {len(linhas)} linha(s) de custo sincronizada(s).")
    return f"{len(linhas)} linha(s) de custo sincronizada(s)."


def main() -> None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    dataset = os.environ.get("BILLING_EXPORT_DATASET")
    dsn = os.environ.get("DATABASE_URL")
    if not project_id or not dataset or not dsn:
        print(
            "FALHA: GCP_PROJECT_ID, BILLING_EXPORT_DATASET e DATABASE_URL são obrigatórios.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        detalhe = _sincronizar(project_id, dataset, dsn)
    except Exception as exc:
        _heartbeat(dsn, sucesso=False, detalhe=str(exc)[:500])
        raise
    _heartbeat(dsn, sucesso=True, detalhe=detalhe)


if __name__ == "__main__":
    main()
