# DESIGN: BIGQUERY_DATA_WAREHOUSE

> Arquitetura e especificação técnica para espelhar `pareceres_audit_log` num dataset BigQuery
> permanente, via sync incremental idempotente disparado por cron diário.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BIGQUERY_DATA_WAREHOUSE |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **DEFINE** | [DEFINE_BIGQUERY_DATA_WAREHOUSE.md](DEFINE_BIGQUERY_DATA_WAREHOUSE.md) |
| **Status** | ✅ Shipped (2026-08-04) — ver SHIPPED_2026-08-04.md |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Cloud SQL (taxreformai-pg) — pareceres_audit_log, RLS por tenant_id      │
│  (append-only: /v1/tax/simulate, /simulate-simples-nacional, /query)     │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ Cloud SQL Auth Proxy (mesmo padrão de
                                 │ migrar_banco.yml), taxreformai_admin
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  scripts/sincronizar_bigquery.py                                         │
│  1. SELECT MAX(created_at) FROM BigQuery.pareceres_historico (watermark) │
│  2. Para cada tenant em `tenants`:                                       │
│       sessao_do_tenant(tenant_id) → SELECT ... WHERE created_at > wm     │
│  3. Carrega linhas novas numa tabela de STAGING temporária no BigQuery   │
│  4. MERGE staging → pareceres_historico (dedup por `id`, idempotente)    │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ google-cloud-bigquery client
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  BigQuery — dataset taxreformai_analytics                                │
│  tabela pareceres_historico (espelho 1:1, JSONB → JSON nativo)           │
└──────────────────────────────────────────────────────────────────────────┘
                                 ▲
                    .github/workflows/sincronizar_bigquery.yml
                    Trigger duplo: schedule (cron diário) + workflow_dispatch
                    (a 1ª execução real é sempre manual, para verificar
                    antes de confiar no cron sozinho — Constraint da DEFINE)
```

**Components:**
- `scripts/sincronizar_bigquery.py` — script Python, mesmo padrão de `scripts/verificar_*_producao.py`
- `.github/workflows/sincronizar_bigquery.yml` — orquestração, conecta ao Cloud SQL via proxy
- `infra/terraform/main.tf` — dataset, tabela, SA dedicada e suas 4 permissões mínimas

**Data Flow:** ver diagrama acima — unidirecional, Cloud SQL → BigQuery, nunca o contrário.

**Integration Points:** Cloud SQL (`taxreformai-pg`), BigQuery, Secret Manager (senha do
`taxreformai_admin`, já existe desde `SCHEMA_POSTGRESQL`).

---

## Decisions

### Decision 1: SA dedicada e mínima, NÃO reaproveitar `GCP_SA_KEY`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** `migrar_banco.yml` reaproveita `GCP_SA_KEY` (a SA do Terraform, com
`roles/cloudsql.admin` + `roles/secretmanager.admin`) para ler a senha do `taxreformai_admin` —
justificado ali porque migração de schema é uma operação administrativa rara, sempre disparada
manualmente com confirmação explícita (`confirm: "MIGRAR"`).

**Choice:** Criar uma SA nova e dedicada (`taxreformai-bigquery-sync`), com só 4 permissões
mínimas: `roles/cloudsql.client` (projeto), `roles/secretmanager.secretAccessor` (escopado só ao
secret `taxreformai-pg-admin-password`), `roles/bigquery.dataEditor` (escopado só ao dataset
`taxreformai_analytics`) e `roles/bigquery.jobUser` (projeto — não existe equivalente escopado a
dataset para rodar jobs de load/query no BigQuery).

**Rationale:** Esta é a primeira feature do projeto em que uma credencial ADMIN do Postgres
(`taxreformai_admin`, que ignora RLS por não ter policy alguma restringindo o dono/superusuário
via GRANT — só o `FORCE ROW LEVEL SECURITY` da própria tabela limita, não o papel) é usada por um
job que roda **automaticamente, sem clique humano** (cron). Dar essa credencial à SA mais
poderosa do projeto (que também cria/destrói toda a infraestrutura via Terraform) ampliaria o
raio de dano de qualquer comprometimento do cron muito além do necessário.

**Alternatives Rejected:**
1. Reaproveitar `GCP_SA_KEY` — rejeitado: blast radius desproporcional para um job não supervisionado
2. Reaproveitar `taxreformai-deployer` — rejeitado: já tem acesso à senha do papel `app` (não
   `admin`) e a permissões de deploy; misturar propósitos quebra o princípio de uma SA por função
   já estabelecido (`ingestion_sa`, `deployer_sa`, `runtime_sa`)

**Consequences:**
- Mais um recurso `google_service_account` no Terraform, mais um secret novo no GitHub
  (`GCP_BIGQUERY_SYNC_SA_KEY`)
- Isolamento real: um comprometimento do cron do BigQuery nunca alcança `cloudsql.admin` nem
  poder de destruir infraestrutura

---

### Decision 2: Sync por loop de tenant (`sessao_do_tenant`), sem tocar a policy de RLS

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** `pareceres_audit_log` tem `FORCE ROW LEVEL SECURITY` e nenhum papel no Cloud SQL
tem `BYPASSRLS` (confirmado contra a instância real em `SCHEMA_POSTGRESQL`) — um `SELECT *`
direto do papel admin devolve zero linhas sem `app.tenant_id` declarado.

**Choice:** O script itera cada `tenant_id` de `tenants` (tabela sem RLS) e, para cada um, abre
`sessao_do_tenant(conexao, tenant_id)` — o MESMO context manager já usado por toda a API e pelos
scripts de verificação — para ler as linhas daquele tenant.

**Rationale:** Reusa o mecanismo de segurança já auditado, sem criar uma segunda forma de acessar
dado cross-tenant (que precisaria de sua própria revisão de segurança). O custo é N transações em
vez de uma, mas N é pequeno (número de tenants, não de linhas) e o sync é batch diário, não
latência-sensível.

**Alternatives Rejected:**
1. Nova policy de RLS permitindo um papel "service" ver tudo — rejeitado: reabre a superfície de
   segurança mais crítica do projeto (a mesma que `SCHEMA_POSTGRESQL` provou contra produção) só
   para um caso de uso interno
2. Conceder `BYPASSRLS` a `taxreformai_admin` — rejeitado: impossível na prática (Cloud SQL nunca
   concede esse bit a papel nenhum, confirmado em `SCHEMA_POSTGRESQL`) e indesejável mesmo se
   fosse possível

**Consequences:**
- O script precisa de uma consulta prévia (`SELECT id FROM tenants`) e um loop — mais código que
  um único `SELECT`, mas zero risco novo de RLS

---

### Decision 3: Idempotência via staging + `MERGE`, não via janela de watermark isolada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** AT-003/AT-004 da DEFINE exigem ZERO duplicação mesmo em reexecuções — um filtro só
por `created_at > watermark` tem uma janela de risco teórica (duas linhas com o MESMO
`created_at` exato, uma já sincronizada e outra não, TIMESTAMP sem microssegundo suficiente para
desempatar).

**Choice:** Cada execução carrega as linhas candidatas (filtradas por watermark, só como
otimização de volume) numa tabela de STAGING temporária do BigQuery, depois executa um `MERGE
INTO pareceres_historico USING staging ON pareceres_historico.id = staging.id WHEN NOT MATCHED
THEN INSERT` — a deduplicação real acontece pela chave primária (`id`, UUID), não pelo
watermark.

**Rationale:** `id` é a chave natural de origem (UUID gerado pelo Postgres, único por definição)
— usá-la como chave de `MERGE` torna o sync idempotente por construção, independente de qualquer
imprecisão de timestamp. O watermark continua existindo só para não reler o histórico inteiro a
cada execução (otimização de custo/volume, não de correção).

**Alternatives Rejected:**
1. `INSERT` direto filtrado só por watermark — rejeitado: risco teórico de duplicata em empates
   de `created_at`, que o AT-003 exige eliminar, não só minimizar
2. Streaming insert do BigQuery — rejeitado: BigQuery streaming insert não garante deduplicação
   forte (é best-effort, documentado pelo próprio Google), incompatível com o requisito de zero
   duplicação

**Consequences:**
- Uma tabela de staging temporária por execução (criada e destruída dentro do próprio script)
- Um `MERGE` a mais por execução — custo desprezível no volume esperado (batch diário)

---

### Decision 4: Trigger duplo (`schedule` + `workflow_dispatch`) no mesmo workflow

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** A DEFINE exige uma guarda antes de confiar no cron sozinho (primeiro gatilho
automático de infra real do projeto) — mas também exige que o cron dispare sem intervenção
manual (AT-006).

**Choice:** Um único arquivo de workflow com `on: schedule: - cron: "..."` E `workflow_dispatch:`
juntos — a primeira execução real (que prova AT-002 a AT-005) é disparada manualmente pelo
`/build`; a partir daí, o cron assume sozinho.

**Rationale:** Evita duplicar a lógica do sync em dois workflows separados (um "manual" e um
"automático") — é o mesmo código, só a origem do disparo muda. `workflow_dispatch` continua
disponível para sempre, para reexecuções ad-hoc ou depuração, sem exigir uma segunda cópia do
arquivo.

**Alternatives Rejected:**
1. Só `schedule`, sem `workflow_dispatch` — rejeitado: impossível verificar manualmente antes de
   confiar no cron, e sem via de reexecução ad-hoc se o cron falhar
2. Dois workflows separados (um manual de "primeira verificação", outro só-cron permanente) —
   rejeitado: duplicação de código sem benefício real

**Consequences:**
- O workflow não tem a guarda de confirmação textual (`confirm: "MIGRAR"`) que todo outro
  workflow de infra real do projeto tem, porque o `schedule:` não pode ser gated por um input —
  mitigado pelo escopo mínimo da SA (Decision 1): mesmo que dispare por engano, só consegue LER
  o Postgres e ESCREVER no dataset de analytics, nunca alterar schema nem infra

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|--------------|
| 1 | `infra/terraform/main.tf` | Modify | Dataset, tabela, SA dedicada + 4 IAM grants mínimos | None |
| 2 | `scripts/sincronizar_bigquery.py` | Create | Sync incremental idempotente Cloud SQL → BigQuery | 1 |
| 3 | `.github/workflows/sincronizar_bigquery.yml` | Create | Orquestração (proxy + script), trigger duplo | 1, 2 |
| 4 | `requirements.txt` | Modify | Adiciona `google-cloud-bigquery` | None |

---

## Code Patterns

### Terraform — dataset, tabela e SA dedicada

```hcl
resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "analytics" {
  project     = var.project_id
  dataset_id  = "taxreformai_analytics"
  location    = var.region
  description = "Espelho de pareceres_audit_log (Cloud SQL) para consultas analiticas — BIGQUERY_DATA_WAREHOUSE"

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_table" "pareceres_historico" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "pareceres_historico"

  schema = jsonencode([
    { name = "id", type = "STRING", mode = "REQUIRED" },
    { name = "tenant_id", type = "STRING", mode = "REQUIRED" },
    { name = "user_id", type = "STRING", mode = "NULLABLE" },
    { name = "prompt_consulta", type = "STRING", mode = "REQUIRED" },
    { name = "contexto_recuperado_ids", type = "JSON", mode = "NULLABLE" },
    { name = "payload_calculo_json", type = "JSON", mode = "NULLABLE" },
    { name = "resposta_parecer_md", type = "STRING", mode = "REQUIRED" },
    { name = "created_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_service_account" "bigquery_sync_sa" {
  project      = var.project_id
  account_id   = "taxreformai-bigquery-sync"
  display_name = "TaxReform AI - Sync Cloud SQL -> BigQuery (cron diario)"
}

resource "google_project_iam_member" "bigquery_sync_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.bigquery_sync_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "bigquery_sync_le_senha_admin" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pg_admin_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.bigquery_sync_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "bigquery_sync_data_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.bigquery_sync_sa.email}"
}

resource "google_project_iam_member" "bigquery_sync_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.bigquery_sync_sa.email}"
}
```

### Python — `scripts/sincronizar_bigquery.py` (esqueleto)

```python
"""Sincroniza pareceres_audit_log (Cloud SQL) -> BigQuery, incrementalmente.

Le o watermark (MAX(created_at) ja presente no BigQuery), busca linhas novas
de TODOS os tenants (via sessao_do_tenant, sem bypass de RLS — Decision 2 do
DESIGN) e faz MERGE por `id` numa tabela de staging (Decision 3 — garante
idempotencia mesmo em empate exato de created_at).

Roda via .github/workflows/sincronizar_bigquery.yml (schedule + workflow_dispatch).
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import psycopg
from google.cloud import bigquery

from db.repositorio import sessao_do_tenant

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_ID = "taxreformai_analytics"
TABLE_ID = "pareceres_historico"


def _watermark(client: bigquery.Client) -> datetime:
    query = f"SELECT MAX(created_at) AS wm FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"
    linha = next(iter(client.query(query).result()))
    return linha.wm or datetime(1970, 1, 1, tzinfo=timezone.utc)


def _linhas_novas(conexao, watermark: datetime) -> list[dict]:
    linhas = []
    with conexao.cursor() as cur:
        cur.execute("SELECT id FROM tenants")
        tenant_ids = [row[0] for row in cur.fetchall()]

    for tenant_id in tenant_ids:
        with sessao_do_tenant(conexao, tenant_id) as cur:
            cur.execute(
                """
                SELECT id, tenant_id, user_id, prompt_consulta,
                       contexto_recuperado_ids, payload_calculo_json,
                       resposta_parecer_md, created_at
                FROM pareceres_audit_log
                WHERE created_at > %s
                """,
                (watermark,),
            )
            for row in cur.fetchall():
                linhas.append(_para_linha_bigquery(row))
    return linhas


def main() -> None:
    dsn = os.environ["DATABASE_URL"]  # taxreformai_admin — ver Decision 1
    conexao = psycopg.connect(dsn)
    client = bigquery.Client(project=PROJECT_ID)

    watermark = _watermark(client)
    linhas = _linhas_novas(conexao, watermark)

    if not linhas:
        print("Nenhuma linha nova desde o ultimo sync.")
        return

    staging_id = f"staging_{uuid.uuid4().hex[:8]}"
    staging_ref = f"{PROJECT_ID}.{DATASET_ID}.{staging_id}"
    tabela_destino = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")

    client.create_table(bigquery.Table(staging_ref, schema=tabela_destino.schema))
    try:
        client.load_table_from_json(linhas, staging_ref).result()
        client.query(f"""
            MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` T
            USING `{staging_ref}` S
            ON T.id = S.id
            WHEN NOT MATCHED THEN INSERT ROW
        """).result()
        print(f"OK: {len(linhas)} linha(s) sincronizada(s).")
    finally:
        client.delete_table(staging_ref, not_found_ok=True)


if __name__ == "__main__":
    main()
```

### GitHub Actions — `.github/workflows/sincronizar_bigquery.yml` (esqueleto)

```yaml
name: Sincronizar BigQuery

on:
  schedule:
    - cron: "0 6 * * *"  # 06:00 UTC = 03:00 BRT, fora do horario comercial
  workflow_dispatch: {}

env:
  PYTHONPATH: ${{ github.workspace }}
  INSTANCE_CONNECTION_NAME: taxreformai-dev:southamerica-east1:taxreformai-pg
  GCP_PROJECT_ID: taxreformai-dev

jobs:
  sincronizar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements.txt

      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_BIGQUERY_SYNC_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2

      - name: Ler senha do admin no Secret Manager
        run: |
          echo "PG_ADMIN_PASSWORD=$(gcloud secrets versions access latest --secret=taxreformai-pg-admin-password --project=$GCP_PROJECT_ID)" >> "$GITHUB_ENV"

      # Mesmo padrao exato de migrar_banco.yml (proxy real, sem local execution)
      - name: Baixar Cloud SQL Auth Proxy
        run: |
          curl -sSL -o cloud-sql-proxy \
            https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.23.0/cloud-sql-proxy.linux.amd64
          chmod +x cloud-sql-proxy

      - name: Iniciar o proxy em background
        run: |
          ./cloud-sql-proxy --port 5432 "$INSTANCE_CONNECTION_NAME" &
          for _ in $(seq 1 30); do
            (echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null && break
            sleep 1
          done

      - name: Sincronizar
        env:
          DATABASE_URL: postgresql://taxreformai_admin:${{ env.PG_ADMIN_PASSWORD }}@127.0.0.1:5432/taxreformai
        run: python scripts/sincronizar_bigquery.py
```

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `_para_linha_bigquery` (conversão de tipos, incl. JSONB → JSON), lógica de watermark | pytest, fakes (sem Cloud SQL/BigQuery reais) |
| Integration | Loop multi-tenant respeitando RLS (contra Postgres real do CI, mesmo container `postgres:16` já usado por outros testes) | pytest + fixture de banco |
| E2E real | Sync completo contra Cloud SQL + BigQuery reais, idempotência provada por 2 execuções seguidas | `workflow_dispatch` manual de `sincronizar_bigquery.yml`, antes de confiar no cron |

---

## Next Step

`/build .claude/sdd/features/DESIGN_BIGQUERY_DATA_WAREHOUSE.md`
