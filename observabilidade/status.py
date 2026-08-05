"""Deriva verde/amarelo/vermelho dos 6 recursos do caminho de requisição +
sync do BigQuery — Decision 1 do DESIGN_PAINEL_OBSERVABILIDADE.md.

Nenhuma função aqui exige role IAM nova para `taxreformai-runtime`: cada
sinal vem de uma fonte que a API já acessa hoje (Cloud SQL via
`pg_stat_activity`, Qdrant via as mesmas credenciais do pesquisador_legal,
Anthropic via `uso_llm`, Cloud Tasks via `sku_upload_jobs`, Frontend via
HTTP público, API por estar respondendo, sync do BigQuery via
`observabilidade_execucoes`).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from db.repositorio import sessao_do_tenant

NIVEL_VERDE = "verde"
NIVEL_AMARELO = "amarelo"
NIVEL_VERMELHO = "vermelho"


@dataclass
class StatusRecurso:
    recurso: str
    nivel: str
    detalhe: str


@dataclass
class StatusGeral:
    recursos: list[StatusRecurso]


def status_api() -> StatusRecurso:
    return StatusRecurso("API", NIVEL_VERDE, "respondendo")


def status_frontend(frontend_url: str | None) -> StatusRecurso:
    if not frontend_url:
        return StatusRecurso("Frontend", NIVEL_AMARELO, "URL do frontend não configurada")
    try:
        resposta = httpx.get(frontend_url, timeout=5.0)
    except httpx.HTTPError as exc:
        return StatusRecurso("Frontend", NIVEL_VERMELHO, f"inacessível: {exc}")
    if resposta.status_code == 200:
        return StatusRecurso("Frontend", NIVEL_VERDE, "200 OK")
    return StatusRecurso("Frontend", NIVEL_AMARELO, f"HTTP {resposta.status_code}")


def status_cloud_sql(
    conexao, limiar_amarelo: float = 0.7, limiar_vermelho: float = 0.9
) -> StatusRecurso:
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_stat_activity")
        ativos = cur.fetchone()[0]
        cur.execute("SHOW max_connections")
        maximo = int(cur.fetchone()[0])

    uso = ativos / maximo if maximo else 0.0
    detalhe = f"{ativos}/{maximo} conexões ({uso:.0%})"
    if uso >= limiar_vermelho:
        return StatusRecurso("Cloud SQL", NIVEL_VERMELHO, detalhe)
    if uso >= limiar_amarelo:
        return StatusRecurso("Cloud SQL", NIVEL_AMARELO, detalhe)
    return StatusRecurso("Cloud SQL", NIVEL_VERDE, detalhe)


def status_qdrant(
    qdrant_url: str | None, qdrant_api_key: str | None, collection: str
) -> StatusRecurso:
    if not qdrant_url:
        return StatusRecurso("Qdrant Cloud", NIVEL_AMARELO, "QDRANT_URL não configurada")
    try:
        resposta = httpx.get(
            f"{qdrant_url}/collections/{collection}",
            headers={"api-key": qdrant_api_key or ""},
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        return StatusRecurso("Qdrant Cloud", NIVEL_VERMELHO, f"inacessível: {exc}")
    if resposta.status_code == 200:
        return StatusRecurso("Qdrant Cloud", NIVEL_VERDE, "respondendo")
    return StatusRecurso("Qdrant Cloud", NIVEL_VERMELHO, f"HTTP {resposta.status_code}")


def status_anthropic(conexao, limite_amostra: int = 10) -> StatusRecurso:
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT sucesso FROM uso_llm ORDER BY created_at DESC LIMIT %s",
            (limite_amostra,),
        )
        linhas = [row[0] for row in cur.fetchall()]

    if not linhas:
        return StatusRecurso("API Claude direta", NIVEL_AMARELO, "sem chamadas recentes registradas")

    falhas = sum(1 for sucesso in linhas if not sucesso)
    detalhe = f"{falhas}/{len(linhas)} falhas nas últimas {len(linhas)} chamadas"
    if falhas >= 3:
        return StatusRecurso("API Claude direta", NIVEL_VERMELHO, detalhe)
    if falhas >= 1:
        return StatusRecurso("API Claude direta", NIVEL_AMARELO, detalhe)
    return StatusRecurso("API Claude direta", NIVEL_VERDE, "sem falhas recentes")


def status_cloud_tasks(
    conexao, limiar_amarelo_minutos: int = 5, limiar_vermelho_minutos: int = 20
) -> StatusRecurso:
    with conexao.cursor() as cur:
        cur.execute("SELECT id FROM tenants")
        tenant_ids = [linha[0] for linha in cur.fetchall()]

    agora = datetime.now(UTC)
    idade_maxima = timedelta(0)
    presos = 0
    for tenant_id in tenant_ids:
        with sessao_do_tenant(conexao, tenant_id) as cur:
            cur.execute("SELECT created_at FROM sku_upload_jobs WHERE status = 'PROCESSANDO'")
            for (created_at,) in cur.fetchall():
                idade = agora - created_at
                idade_maxima = max(idade_maxima, idade)
                if idade > timedelta(minutes=limiar_vermelho_minutos):
                    presos += 1

    if presos:
        return StatusRecurso(
            "Cloud Tasks", NIVEL_VERMELHO, f"{presos} job(s) preso(s) há mais de {limiar_vermelho_minutos}min"
        )
    if idade_maxima > timedelta(minutes=limiar_amarelo_minutos):
        minutos = int(idade_maxima.total_seconds() // 60)
        return StatusRecurso("Cloud Tasks", NIVEL_AMARELO, f"job em processamento há {minutos}min")
    return StatusRecurso("Cloud Tasks", NIVEL_VERDE, "fila normal")


def status_sync_bigquery(
    conexao, job: str = "sincronizar_bigquery", janela_horas: int = 30
) -> StatusRecurso:
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT executado_em, sucesso, detalhe FROM observabilidade_execucoes "
            "WHERE job = %s ORDER BY executado_em DESC LIMIT 1",
            (job,),
        )
        linha = cur.fetchone()

    if linha is None:
        return StatusRecurso("Sync BigQuery", NIVEL_AMARELO, "nunca rodou")

    executado_em, sucesso, detalhe = linha
    if not sucesso:
        return StatusRecurso(
            "Sync BigQuery", NIVEL_VERMELHO, f"última execução falhou: {detalhe or 'sem detalhe'}"
        )

    idade = datetime.now(UTC) - executado_em
    if idade > timedelta(hours=janela_horas):
        horas = int(idade.total_seconds() // 3600)
        return StatusRecurso("Sync BigQuery", NIVEL_AMARELO, f"atrasado — última execução há {horas}h")
    return StatusRecurso("Sync BigQuery", NIVEL_VERDE, detalhe or "OK")


def calcular_status(
    conexao,
    *,
    frontend_url: str | None,
    qdrant_url: str | None,
    qdrant_api_key: str | None,
    qdrant_collection: str,
) -> StatusGeral:
    return StatusGeral(
        recursos=[
            status_api(),
            status_frontend(frontend_url),
            status_cloud_sql(conexao),
            status_qdrant(qdrant_url, qdrant_api_key, qdrant_collection),
            status_anthropic(conexao),
            status_cloud_tasks(conexao),
            status_sync_bigquery(conexao),
        ]
    )
