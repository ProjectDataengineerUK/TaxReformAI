"""Heartbeat de jobs agendados (`observabilidade_execucoes`) — sem tenant,
sem RLS (Decision 3 do DESIGN): é o mesmo job rodando pro sistema inteiro,
nunca por tenant. Usado por `scripts/sincronizar_bigquery.py` e
`scripts/sincronizar_custo_infra.py`, e lido por
`observabilidade/status.py::status_sync_bigquery`."""


def registrar_execucao(conexao, job: str, sucesso: bool, detalhe: str | None = None) -> None:
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO observabilidade_execucoes (job, sucesso, detalhe) VALUES (%s, %s, %s)",
            (job, sucesso, detalhe),
        )
    conexao.commit()
