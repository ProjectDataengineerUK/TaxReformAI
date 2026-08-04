# DESIGN: FILA_ASSINCRONA_CELERY_REDIS

> Arquitetura e especificação técnica: upload de SKUs sempre assíncrono via Cloud Tasks,
> processado no mesmo serviço Cloud Run da API, com status em Postgres com RLS.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FILA_ASSINCRONA_CELERY_REDIS |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **DEFINE** | [DEFINE_FILA_ASSINCRONA_CELERY_REDIS.md](DEFINE_FILA_ASSINCRONA_CELERY_REDIS.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
Cliente                    API (Cloud Run, mesmo serviço de sempre)
  │                              │
  │ POST /v1/tax/skus/upload     │
  │──────────────────────────────►│ 1. Valida tamanho/linhas (mesmo teto atual, revisado)
  │                              │ 2. Upload do arquivo -> GCS staging bucket
  │                              │ 3. INSERT sku_upload_jobs (status=PENDENTE)
  │                              │ 4. Cria Cloud Task (OIDC token, aponta pro passo 5)
  │◄──────────────────────────────│ 202 Accepted { job_id }
  │                              │
  │                              │        ┌─────────────────────────┐
  │                              │◄───────┤ Cloud Tasks (fila)      │
  │                              │  HTTP  │ dispara com retry nativo │
  │                              │  +OIDC └─────────────────────────┘
  │                              │
  │                    POST /v1/tax/skus/upload/processar-tarefa (interno)
  │                              │ 5. Verifica token OIDC (SA + audience esperados)
  │                              │ 6. Baixa arquivo do GCS
  │                              │ 7. Loop: parsear_linha_csv + upsert_sku (já existentes)
  │                              │ 8. UPDATE sku_upload_jobs (status=CONCLUIDO/ERRO, resultado_json)
  │                              │
  │ GET /v1/tax/skus/upload/{id} │
  │──────────────────────────────►│ 9. SELECT sku_upload_jobs (RLS por tenant_id)
  │◄──────────────────────────────│ status + resultado (quando concluído)
```

**Components:**
- `api/routers/empresa_skus.py` — `upload_csv` modificado (sempre assíncrono) + novo endpoint
  `GET /upload/{job_id}`
- `api/routers/skus_tasks.py` (novo) — endpoint interno `processar-tarefa`, nunca chamado por
  cliente externo
- `api/tasks_cloud.py` (novo) — criação de Cloud Tasks + verificação de token OIDC
- `db/migrations/0XX_sku_upload_jobs.sql` — tabela nova com RLS
- `infra/terraform/main.tf` — Cloud Tasks queue, bucket GCS de staging, IAM

**Data Flow:** diagrama acima — unidirecional, cliente → API → Cloud Tasks → API (mesma) →
Postgres/GCS.

**Integration Points:** Cloud Tasks, GCS (staging), Cloud SQL (`sku_upload_jobs` +
`empresa_skus` já existente).

---

## Decisions

### Decision 1: Verificação manual do token OIDC no código da aplicação

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** O mesmo serviço Cloud Run que serve rotas públicas (protegidas por `X-API-Key`)
precisa também servir a rota interna que só o Cloud Tasks deve poder chamar. A proteção nativa do
Cloud Run (`--no-allow-unauthenticated`, que barra qualquer chamada sem IAM na borda) é
configurada por SERVIÇO inteiro, não por rota — não dá pra aplicar só na rota interna sem também
bloquear todo o tráfego público.

**Choice:** A rota `POST /v1/tax/skus/upload/processar-tarefa` verifica manualmente, no código
Python, o cabeçalho `Authorization: Bearer <token>` — usando `google.oauth2.id_token.verify_oauth2_token`
(biblioteca `google-auth`) para confirmar que o token é um JWT assinado pelo Google, com
`audience` igual à URL pública da própria API e `email` igual à SA configurada para gerar o token
do Cloud Tasks. Qualquer chamada sem esse cabeçalho válido devolve `401`.

**Rationale:** É o padrão documentado do GCP para proteger uma rota específica dentro de um
serviço Cloud Run majoritariamente público — a alternativa (IAM na borda) exigiria dividir a API
em dois serviços Cloud Run só por causa desta rota, contradizendo a Decisão de reusar o mesmo
serviço (ver Decision 2).

**Alternatives Rejected:**
1. `--no-allow-unauthenticated` no serviço inteiro — quebraria todas as rotas públicas
2. Segredo compartilhado num header customizado (não-OIDC) — mais fraco, exige gerenciar mais um
   secret, quando o Cloud Tasks já oferece OIDC nativamente sem custo extra

**Consequences:**
- Nova dependência: `google-auth` (adicionada a `requirements-api.txt`)
- **Marcado A-002 na DEFINE — precisa de verificação real no `/build`**: a sintaxe exata de
  `verify_oauth2_token` e a configuração exata do `oidc_token` na criação da task precisam ser
  testadas contra uma chamada REAL do Cloud Tasks antes de confiar nelas — não assumido como
  certo só pela documentação lida aqui

---

### Decision 2: Endpoint de processamento no MESMO serviço Cloud Run, não um serviço novo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Celery exigia um processo consumidor dedicado e persistente (worker). Cloud Tasks
funciona diferente: invoca uma URL HTTP quando a task está pronta — não precisa de um processo
escutando continuamente.

**Choice:** A rota de processamento vive no MESMO serviço Cloud Run da API (`taxreformai-api`),
como qualquer outra rota FastAPI.

**Rationale:** Zero infraestrutura de compute nova — o Cloud Run já escala sob demanda para
atender essa chamada, exatamente como atende qualquer outra requisição.

**Alternatives Rejected:**
1. Serviço Cloud Run dedicado ao processamento — desnecessário, mesma imagem/deploy já serve

**Consequences:**
- O timeout do serviço Cloud Run (compartilhado por TODAS as rotas) precisa acomodar o pior caso
  de processamento (50.000+ linhas) — ver Decision 3

---

### Decision 3: Timeout do Cloud Run aumentado para toda a API, sem particionamento nesta versão

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Processar 50.000+ linhas numa única chamada HTTP pode levar mais que o timeout
padrão do Cloud Run (300s). O Cloud Run permite configurar até 3600s (60 min) por serviço.

**Choice:** Aumentar `--timeout` do deploy da API para um valor generoso (ex: 1800s/30min) — o
suficiente para o pior caso esperado sem exigir particionamento em múltiplas Cloud Tasks. Manter
o `AT-006` (upload real de 50.000+ linhas) como a prova real desse número, e o particionamento
(`COULD` da DEFINE) como próximo passo SE o teste real mostrar que não é suficiente.

**Rationale:** YAGNI — não implementar a complexidade de particionamento (rastrear progresso
parcial, agregar múltiplos resultados) antes de confirmar que ela é necessária.

**Alternatives Rejected:**
1. Particionar desde já em lotes de N linhas por task — mais robusto, mas complexidade não
   comprovada como necessária ainda

**Consequences:**
- Se `AT-006` (medido no `/build`) revelar que 50.000+ linhas excede até os 30 min, o
  particionamento vira obrigatório antes do `/ship` — não é opcional se o teste real falhar

---

### Decision 4: `sku_upload_jobs` como tabela nova, seguindo o padrão de RLS já auditado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Sem Redis, o status do job precisa de um lugar para viver — persistente, consultável
via `GET`, isolado por tenant.

**Choice:** Nova tabela `sku_upload_jobs`, com `tenant_id`, `FORCE ROW LEVEL SECURITY` e a mesma
policy `USING (tenant_id = current_setting('app.tenant_id'))` já usada em `empresa_skus`/
`pareceres_audit_log`.

**Rationale:** Reusa um padrão já implementado, testado e auditado 3 vezes neste projeto — nenhum
mecanismo de isolamento novo para revisar.

**Alternatives Rejected:**
1. Redis como result backend — só fazia sentido com Celery, descartado junto (Decision do
   `/brainstorm`)

**Consequences:**
- Mais uma migração (`0XX_sku_upload_jobs.sql`) no histórico já extenso do projeto

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|--------------|
| 1 | `db/migrations/0XX_sku_upload_jobs.sql` | Create | Tabela + RLS + policy | None |
| 2 | `infra/terraform/main.tf` | Modify | Cloud Tasks queue, bucket GCS de staging (lifecycle 1 dia), IAM (`cloudtasks.enqueuer`, `run.invoker` self, storage no bucket novo) | None |
| 3 | `api/tasks_cloud.py` | Create | `criar_task_processamento`, `verificar_token_oidc` | 2 |
| 4 | `api/routers/skus_tasks.py` | Create | Endpoint interno `processar-tarefa` | 1, 3 |
| 5 | `api/routers/empresa_skus.py` | Modify | `upload_csv` sempre assíncrono, novo `GET /upload/{job_id}` | 1, 3 |
| 6 | `requirements-api.txt` | Modify | `google-cloud-tasks`, `google-auth` | None |
| 7 | `.github/workflows/deploy.yml` | Modify | `--timeout=1800` no deploy da API (Decision 3) | None |

---

## Code Patterns

### Migração — `sku_upload_jobs`

```sql
CREATE TABLE IF NOT EXISTS sku_upload_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'PENDENTE',
    gcs_uri_arquivo TEXT NOT NULL,
    resultado_json  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE sku_upload_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sku_upload_jobs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON sku_upload_jobs;
CREATE POLICY tenant_isolation ON sku_upload_jobs
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid);

GRANT SELECT, INSERT, UPDATE ON sku_upload_jobs TO taxreformai_app;
```

### Terraform — Cloud Tasks queue + bucket de staging

```hcl
resource "google_project_service" "cloudtasks" {
  project            = var.project_id
  service            = "cloudtasks.googleapis.com"
  disable_on_destroy = false
}

resource "google_cloud_tasks_queue" "sku_upload" {
  project  = var.project_id
  name     = "sku-upload-processamento"
  location = var.region

  depends_on = [google_project_service.cloudtasks]
}

resource "google_storage_bucket" "sku_upload_staging" {
  project                     = var.project_id
  name                        = "${var.project_id}-sku-upload-staging"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition { age = 1 }
    action { type = "Delete" }
  }
}

resource "google_project_iam_member" "runtime_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.runtime_sa.email}"
}

# taxreformai-runtime precisa poder gerar um token OIDC EM NOME DELA MESMA
# para o Cloud Tasks anexar às chamadas — padrão comum quando quem enfileira
# e quem é invocado são a mesma SA.
resource "google_service_account_iam_member" "runtime_actas_self" {
  service_account_id = google_service_account.runtime_sa.name
  role                = "roles/iam.serviceAccountUser"
  member              = "serviceAccount:${google_service_account.runtime_sa.email}"
}

resource "google_storage_bucket_iam_member" "runtime_sku_staging_admin" {
  bucket = google_storage_bucket.sku_upload_staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime_sa.email}"
}
```

### Python — criação da task + verificação do token (esqueleto)

```python
# api/tasks_cloud.py
import json
import os

from google.auth.transport import requests as google_requests
from google.cloud import tasks_v2
from google.oauth2 import id_token

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("GCP_REGION", "southamerica-east1")
QUEUE = "sku-upload-processamento"
RUNTIME_SA_EMAIL = os.environ["RUNTIME_SA_EMAIL"]
API_BASE_URL = os.environ["API_BASE_URL"]  # URL pública do próprio serviço


def criar_task_processamento(job_id: str) -> None:
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT_ID, LOCATION, QUEUE)
    url = f"{API_BASE_URL}/v1/tax/skus/upload/processar-tarefa"

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"job_id": job_id}).encode(),
            "oidc_token": {
                "service_account_email": RUNTIME_SA_EMAIL,
                "audience": API_BASE_URL,
            },
        }
    }
    client.create_task(request={"parent": parent, "task": task})


def verificar_token_oidc(authorization_header: str | None) -> bool:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    token = authorization_header.removeprefix("Bearer ")
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=API_BASE_URL)
    except ValueError:
        return False
    return claims.get("email") == RUNTIME_SA_EMAIL and claims.get("email_verified", False)
```

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `verificar_token_oidc` (fakes de token válido/inválido/ausente), lógica de status da tabela | pytest, fakes |
| Integration | `sku_upload_jobs` + RLS contra Postgres real do CI (mesmo container `postgres:16`) | pytest + fixture de banco |
| E2E real | Upload real end-to-end (enqueue → Cloud Tasks → processamento → polling), incluindo AT-005 (rejeição sem token) e AT-006 (50.000+ linhas) | `workflow_dispatch` manual, mesma disciplina de infraestrutura real do projeto |

---

## Next Step

`/build .claude/sdd/features/DESIGN_FILA_ASSINCRONA_CELERY_REDIS.md`
