terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {
    bucket = "taxreformai-dev-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "raw_legal_storage" {
  name                        = var.bucket_name
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

resource "google_service_account" "ingestion_sa" {
  project      = var.project_id
  account_id   = "taxreform-ingestion"
  display_name = "TaxReform AI - Pipeline de Ingestao Legal"
}

resource "google_storage_bucket_iam_member" "ingestion_sa_bucket_access" {
  bucket = google_storage_bucket.raw_legal_storage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# --- Cloud Composer (CLOUD_COMPOSER_PROVISIONAMENTO) — ciclo provisionar/verificar/destruir
# concluído em 2026-08-04. Removido de propósito: ver
# .claude/sdd/archive/CLOUD_COMPOSER_PROVISIONAMENTO/SHIPPED_2026-08-04.md para o
# histórico completo (5+ bugs reais corrigidos, achado final de bloqueio de
# memória/instabilidade do webserver). taxreform-ingestion (acima) permanece —
# reaproveitável se este ciclo for repetido no futuro.

output "bucket_url" {
  value = google_storage_bucket.raw_legal_storage.url
}

output "service_account_email" {
  value = google_service_account.ingestion_sa.email
}

# --- CD: Artifact Registry + service account de deploy (Cloud Run) ---
# Provisiona só a identidade e o repositorio de imagens usados pelo workflow
# .github/workflows/deploy.yml. Os servicos Cloud Run em si (taxreformai-api,
# taxreformai-frontend) sao criados/atualizados de forma imperativa pelo
# `gcloud run deploy` dentro do workflow (workflow_dispatch, nao disparado
# automaticamente), nao por este modulo Terraform.

resource "google_project_service" "artifactregistry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "docker_images" {
  project       = var.project_id
  location      = var.region
  repository_id = "taxreformai"
  format        = "DOCKER"
  description   = "Imagens Docker da API (FastAPI) e do frontend (Next.js) do TaxReform AI"

  depends_on = [google_project_service.artifactregistry]
}

resource "google_service_account" "deployer_sa" {
  project      = var.project_id
  account_id   = "taxreformai-deployer"
  display_name = "TaxReform AI - Deploy CD (Cloud Run + Artifact Registry)"
}

# Artifact Registry Writer, escopado só ao repositório de imagens (não ao projeto todo).
resource "google_artifact_registry_repository_iam_member" "deployer_ar_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.docker_images.location
  repository = google_artifact_registry_repository.docker_images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer_sa.email}"
}

# Cloud Run Admin precisa de escopo de projeto (os serviços ainda não existem
# para restringir a um recurso específico na primeira criação).
resource "google_project_iam_member" "deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer_sa.email}"

  depends_on = [google_project_service.run]
}

# deploy.yml verifica, depois do smoke test, que o audit log foi gravado de
# verdade — conecta ao Cloud SQL via Auth Proxy usando as mesmas credenciais
# que o resto do deploy (GCP_DEPLOYER_SA_KEY). Sem isto o passo falha com 403
# "Not authorized... missing permission cloudsql.instances.get" — descoberto
# no primeiro deploy real após ligar a API ao Cloud SQL (2026-07-26).
resource "google_project_iam_member" "deployer_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.deployer_sa.email}"

  depends_on = [google_project_service.sqladmin]
}

# Diagnóstico pós-deploy (LLM_REAL_VERTEX_AI): `gcloud logging read` contra o
# serviço da API exigiu esta role — sem ela, `PERMISSION_DENIED: Permission
# denied for all log views`, descoberto na primeira tentativa real de
# diagnosticar um 503 no smoke test. Só leitura (`roles/logging.viewer`),
# nenhuma escrita/exclusão de log.
resource "google_project_iam_member" "deployer_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.deployer_sa.email}"
}

# Identidade de RUNTIME dos serviços Cloud Run — deliberadamente sem role nenhuma.
# Nem a API nem o frontend acessam GCP em runtime: servem HTTP e leem env vars
# (API_KEYS, FRONTEND_ORIGINS). Sem esta SA, o `gcloud run deploy` cai na SA de
# compute padrão do projeto (Editor), e rodar os serviços como a própria SA de
# deploy seria pior ainda — ela tem roles/run.admin, então um contêiner
# comprometido poderia redeployar os serviços.
resource "google_service_account" "runtime_sa" {
  project      = var.project_id
  account_id   = "taxreformai-runtime"
  display_name = "TaxReform AI - Runtime dos servicos Cloud Run (sem permissoes)"
}

# Escopado só na SA de runtime: permite ao deployer fazer
# `gcloud run deploy --service-account=taxreformai-runtime@...`.
resource "google_service_account_iam_member" "deployer_actas_runtime" {
  service_account_id = google_service_account.runtime_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer_sa.email}"
}

output "runtime_service_account_email" {
  value = google_service_account.runtime_sa.email
}

output "deployer_service_account_email" {
  value = google_service_account.deployer_sa.email
}

output "artifact_registry_repository" {
  value = "${google_artifact_registry_repository.docker_images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_images.repository_id}"
}

# --- Cloud SQL (PostgreSQL 16) — schema da seção 7 ---
# Instância mínima: o produto ainda não tem tráfego, e subir tamanho é operação
# online. Começar grande seria pagar por capacidade ociosa.

resource "google_project_service" "sqladmin" {
  project            = var.project_id
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_sql_database_instance" "principal" {
  project          = var.project_id
  name             = "taxreformai-pg"
  region           = var.region
  database_version = "POSTGRES_16"

  # Protege contra `terraform destroy` acidental levar junto a base de dados de
  # clientes e a trilha de auditoria. Desligar exige edição explícita aqui.
  deletion_protection = true

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false # exige tier maior; ZONAL + backup diário basta por ora
      start_time                     = "06:00"
    }

    ip_configuration {
      # IP público SEM redes autorizadas. Parece contraditório, mas é o modelo
      # padrão e seguro para Cloud Run: sem entradas em authorized_networks,
      # nenhuma origem da internet abre conexão TCP direta. O acesso acontece
      # pelo conector do Cloud SQL (socket unix /cloudsql/<connection_name>),
      # que autentica por IAM e trafega pela rede do Google.
      #
      # A alternativa (IP privado ou PSC) exigiria VPC + Serverless VPC Access
      # ou endpoint PSC — custo e complexidade extras, e o conector nativo do
      # Cloud Run não fala com PSC puro. Adicionar qualquer CIDR em
      # authorized_networks aqui expõe a instância à internet.
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    database_flags {
      # Log de conexões ajuda a auditar quem acessou a base tributária.
      name  = "log_connections"
      value = "on"
    }
  }

  depends_on = [google_project_service.sqladmin]
}

resource "google_sql_database" "taxreformai" {
  project  = var.project_id
  name     = "taxreformai"
  instance = google_sql_database_instance.principal.name
}

# Dois usuários, com privilégios diferentes — a lição mais cara do build do
# schema. Superusuários do PostgreSQL IGNORAM Row-Level Security por completo;
# se a aplicação conectasse com o papel administrativo, todo o isolamento entre
# tenants viraria decoração, sem erro nenhum. O papel da aplicação é criado e
# rebaixado pela migração 003.

resource "random_password" "pg_admin" {
  length  = 32
  special = false # evita escaping em URL de conexão
}

resource "random_password" "pg_app" {
  length  = 32
  special = false
}

resource "google_sql_user" "admin" {
  project  = var.project_id
  name     = "taxreformai_admin"
  instance = google_sql_database_instance.principal.name
  password = random_password.pg_admin.result
}

resource "google_sql_user" "app" {
  project  = var.project_id
  name     = "taxreformai_app"
  instance = google_sql_database_instance.principal.name
  password = random_password.pg_app.result
}

# Senhas no Secret Manager, nunca em variável de ambiente do Terraform nem no
# state em texto plano acessível a quem só precisa deployar.
resource "google_secret_manager_secret" "pg_app_password" {
  project   = var.project_id
  secret_id = "taxreformai-pg-app-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "pg_app_password" {
  secret      = google_secret_manager_secret.pg_app_password.id
  secret_data = random_password.pg_app.result
}

resource "google_secret_manager_secret" "pg_admin_password" {
  project   = var.project_id
  secret_id = "taxreformai-pg-admin-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "pg_admin_password" {
  secret      = google_secret_manager_secret.pg_admin_password.id
  secret_data = random_password.pg_admin.result
}

# A SA de runtime foi criada deliberadamente sem role nenhuma. Conectar ao
# Cloud SQL exige exatamente duas: cliente do SQL e leitura do próprio segredo.
# Continua sendo o mínimo — não ganha acesso a mais nada no projeto.
resource "google_project_iam_member" "runtime_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_le_senha_app" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pg_app_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime_sa.email}"
}

# --- Vertex AI (Claude via Agent Platform) — LLM_REAL_VERTEX_AI ---
# Primeira role de PROJETO concedida à SA de runtime desde que ela foi criada
# deliberadamente sem nenhuma (ver comentário acima de `runtime_sa`). Desvio
# intencional, não descuido: `roles/aiplatform.user` não tem equivalente
# restrito a um recurso específico para modelos de publisher do Model Garden,
# diferente de `cloudsql.client` (que já é, em si, escopado à instância via
# IAM condicional implícito do produto). A chamada ao Vertex AI usa o
# endpoint `global` (Decision 2 do DESIGN de LLM_REAL_VERTEX_AI) — não fixa
# região, então nenhuma variável de região é necessária aqui.

resource "google_project_service" "aiplatform" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_iam_member" "runtime_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runtime_sa.email}"

  depends_on = [google_project_service.aiplatform]
}

# A verificação pós-deploy (deploy.yml) só faz SELECT em pareceres_audit_log
# dentro da sessão do próprio tenant — não precisa do papel admin, então lê a
# senha do app, não a do admin. Least privilege: a SA de deploy nunca ganha
# acesso à credencial que pode alterar schema.
resource "google_secret_manager_secret_iam_member" "deployer_le_senha_app" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pg_app_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.deployer_sa.email}"
}

output "cloudsql_connection_name" {
  value = google_sql_database_instance.principal.connection_name
}

# --- BigQuery (BIGQUERY_DATA_WAREHOUSE) — espelho de pareceres_audit_log ---
# Recurso PERMANENTE, ao contrário do Composer: BigQuery cobra por
# armazenamento/consulta, não por hora rodando — perfil de custo seguro para
# manter sempre provisionado.

resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

# Achado real da 1a tentativa de apply: a SA de Terraform (GCP_SA_KEY) não
# tinha `bigquery.datasets.create` — 403 PERMISSION_DENIED ao criar o
# dataset. `roles/bigquery.dataEditor` no nível do PROJETO é o mínimo que
# concede criação de dataset (não existe um papel escopado a "ainda não
# existe" para o próprio dataset que ele vai criar).
resource "google_project_iam_member" "terraform_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${var.terraform_sa_email}"

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_dataset" "analytics" {
  project     = var.project_id
  dataset_id  = "taxreformai_analytics"
  location    = var.region
  description = "Espelho de pareceres_audit_log (Cloud SQL) para consultas analiticas — BIGQUERY_DATA_WAREHOUSE"

  depends_on = [google_project_service.bigquery, google_project_iam_member.terraform_bigquery_data_editor]
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

# SA dedicada e mínima (Decisão 1 do DESIGN) — NÃO reaproveita GCP_SA_KEY. É a
# primeira feature em que uma credencial ADMIN do Postgres (que ignora RLS por
# FORCE ROW LEVEL SECURITY não se aplicar a GRANT, só à ausência de policy
# permissiva) é usada por um job automático, sem clique humano (cron). Dar essa
# credencial à SA mais poderosa do projeto ampliaria o raio de dano de um
# comprometimento do cron muito além do necessário.
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

# Só a senha do ADMIN (taxreformai_admin) — o sync precisa ler TODOS os
# tenants via loop de sessao_do_tenant() (Decisão 2 do DESIGN), o que o papel
# de runtime (taxreformai_app) não permite numa única sessão.
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

# Sem equivalente escopado a dataset — rodar qualquer job de load/query no
# BigQuery exige este papel no nível do projeto.
resource "google_project_iam_member" "bigquery_sync_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.bigquery_sync_sa.email}"
}

output "bigquery_sync_service_account_email" {
  value = google_service_account.bigquery_sync_sa.email
}

# --- SA dedicada: sincronizar_custo_infra.py (PAINEL_OBSERVABILIDADE) ---
# Direção OPOSTA de taxreformai-bigquery-sync: LÊ o dataset de Billing Export
# (fora do controle do Terraform, ver variables.tf) e ESCREVE em
# custo_infra_diario/observabilidade_execucoes (Cloud SQL). Autentica como
# taxreformai_app, não taxreformai_admin — este job só grava em 2 tabelas
# próprias, sem precisar iterar tenants (Decision 2/3 do DESIGN), privilégio
# real mais mínimo do que o do sync do BigQuery.
resource "google_service_account" "cost_sync_sa" {
  project      = var.project_id
  account_id   = "taxreformai-cost-sync"
  display_name = "TaxReform AI - Sync Billing Export -> Cloud SQL (cron diario)"
}

resource "google_project_iam_member" "cost_sync_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cost_sync_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cost_sync_le_senha_app" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pg_app_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cost_sync_sa.email}"
}

# `data`, não `resource`: o dataset de Billing Export é criado pelo GCP
# quando o usuário habilita o export no Console — Terraform nunca é dono
# dele. `terraform apply` deste bloco só funciona DEPOIS desse passo manual
# (Decision 2 do DESIGN_PAINEL_OBSERVABILIDADE.md); antes disso, falha alto
# com "dataset not found", nunca em silêncio.
data "google_bigquery_dataset" "billing_export" {
  project    = var.project_id
  dataset_id = var.billing_export_dataset
}

resource "google_bigquery_dataset_iam_member" "cost_sync_data_viewer" {
  project    = var.project_id
  dataset_id = data.google_bigquery_dataset.billing_export.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.cost_sync_sa.email}"
}

# Sem equivalente escopado a dataset — rodar uma query no BigQuery exige
# este papel no nível do projeto, mesmo achado já documentado no sync do
# BigQuery (bigquery_sync_job_user).
resource "google_project_iam_member" "cost_sync_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.cost_sync_sa.email}"
}

output "cost_sync_service_account_email" {
  value = google_service_account.cost_sync_sa.email
}

# --- Cloud Tasks (FILA_ASSINCRONA_CELERY_REDIS) — upload assíncrono de SKUs ---
# Nome do roadmap preservado (posição 11); mecanismo real é Cloud Tasks, não
# Celery/Redis — rejeitado no /brainstorm por exigir VPC + Serverless VPC
# Access connector (custo real ~US$60-70/mês e o primeiro recurso do projeto
# a sair da disciplina "sem VPC"). Cloud Tasks + o próprio serviço Cloud Run
# da API resolvem o mesmo problema sem VPC, sem Redis, sem worker sempre
# ligado — recursos serverless, reaproveitando taxreformai-runtime (já usado
# para rodar a API) em vez de criar uma SA nova.

resource "google_project_service" "cloudtasks" {
  project            = var.project_id
  service            = "cloudtasks.googleapis.com"
  disable_on_destroy = false
}

# Achado real da 1a tentativa de apply: a SA de Terraform (GCP_SA_KEY) não
# tinha `cloudtasks.queues.create` — 403 PERMISSION_DENIED ao criar a fila.
# `roles/cloudtasks.admin` é a role padrão do Google para isso.
resource "google_project_iam_member" "terraform_cloudtasks_admin" {
  project = var.project_id
  role    = "roles/cloudtasks.admin"
  member  = "serviceAccount:${var.terraform_sa_email}"

  depends_on = [google_project_service.cloudtasks]
}

resource "google_cloud_tasks_queue" "sku_upload" {
  project  = var.project_id
  name     = "sku-upload-processamento"
  location = var.region

  depends_on = [google_project_service.cloudtasks, google_project_iam_member.terraform_cloudtasks_admin]
}

# force_destroy=true: bucket de STAGING temporário (lifecycle de 1 dia), não
# um data lake — diferente do bucket de ingestão legal (force_destroy=false).
resource "google_storage_bucket" "sku_upload_staging" {
  project                     = var.project_id
  name                        = "${var.project_id}-sku-upload-staging"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_project_iam_member" "runtime_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.runtime_sa.email}"
}

# taxreformai-runtime precisa poder gerar um token OIDC EM NOME DELA MESMA
# para o Cloud Tasks anexar às chamadas de volta — padrão comum quando quem
# enfileira e quem é invocado são a mesma SA (Decisão 1 do DESIGN, achado
# ainda não verificado contra um `terraform apply` real — ver A-002 da
# DEFINE_FILA_ASSINCRONA_CELERY_REDIS.md).
resource "google_service_account_iam_member" "runtime_actas_self" {
  service_account_id = google_service_account.runtime_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.runtime_sa.email}"
}

resource "google_storage_bucket_iam_member" "runtime_sku_staging_admin" {
  bucket = google_storage_bucket.sku_upload_staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime_sa.email}"
}

output "sku_upload_staging_bucket" {
  value = google_storage_bucket.sku_upload_staging.name
}
