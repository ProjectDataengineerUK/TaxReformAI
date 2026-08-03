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

# --- Cloud Composer (CLOUD_COMPOSER_PROVISIONAMENTO) — TEMPORÁRIO por desenho ---
# Ambiente Composer 3 custa de verdade ~US$300-400/mês rodando continuamente (achado
# do /brainstorm) — desproporcional a uma DAG de 2 tasks/semana
# (dags/ingestao_legal_dag.py). Ciclo de vida: adicionar estes 3 recursos, aplicar,
# verificar a DAG rodando de verdade (scripts/verificar_composer_producao.py +
# .github/workflows/verificar_composer_producao.yml), registrar a evidência, e então
# REMOVER estes 3 recursos deste arquivo num commit dedicado — o próximo
# `terraform apply` destrói o ambiente porque ele deixa de existir na configuração
# declarada. Nunca um recurso permanente.
#
# taxreform-ingestion (acima) reaproveitada como SA do ambiente — já existe, já tem
# acesso ao bucket, nunca teve consumidor real. Composer 3 não exige VPC customizada
# (diferente de Composer 1/2), mantendo a disciplina "sem VPC" já usada no Cloud SQL.

resource "google_project_service" "composer" {
  project            = var.project_id
  service            = "composer.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_iam_member" "ingestion_composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"

  depends_on = [google_project_service.composer]
}

# Achado real da 1a tentativa de apply: a SA de Terraform (GCP_SA_KEY) não tinha
# `composer.environments.create` — 403 PERMISSION_DENIED ao criar o ambiente.
# `roles/composer.admin` é a role padrão do Google para isso.
resource "google_project_iam_member" "terraform_composer_admin" {
  project = var.project_id
  role    = "roles/composer.admin"
  member  = "serviceAccount:${var.terraform_sa_email}"

  depends_on = [google_project_service.composer]
}

# 2o achado real da mesma tentativa: mesmo com composer.admin, o Terraform
# ainda precisa de actAs sobre a SA que vira a identidade de runtime do
# ambiente (taxreform-ingestion) — 403 "User not authorized to act as service
# account". Mesmo padrão já usado para deployer_actas_runtime (deploy.yml).
resource "google_service_account_iam_member" "terraform_actas_ingestion" {
  service_account_id = google_service_account.ingestion_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.terraform_sa_email}"
}

resource "google_composer_environment" "ingestao_legal" {
  project = var.project_id
  name    = "taxreformai-ingestao-legal"
  region  = var.region

  config {
    software_config {
      image_version = "composer-3-airflow-2"
      env_variables = {
        GCP_PROJECT_ID  = var.project_id
        GCS_BUCKET_NAME = var.bucket_name
        QDRANT_URL      = var.qdrant_url
        QDRANT_API_KEY  = var.qdrant_api_key
      }
      # Achados reais da 1a execução da DAG: "No module named 'ingestion'"
      # (o pacote em si nunca foi enviado, só o arquivo da DAG — corrigido
      # via upload separado em verificar_composer_producao.yml) e os
      # pacotes pip que ingestion/ usa (import lazy dentro de __init__),
      # nunca instalados no ambiente padrão do Composer.
      pypi_packages = {
        fastembed            = ""
        qdrant-client        = ""
        google-cloud-storage = ""
        beautifulsoup4       = ""
        httpx                = ""
      }
    }

    environment_size = "ENVIRONMENT_SIZE_MEDIUM"

    # Achado real: com ENVIRONMENT_SIZE_SMALL (worker default ~2GB), as 3
    # tentativas automáticas da DAG travaram no mesmo ponto (2 de 6 arquivos
    # do modelo intfloat/multilingual-e5-large baixados via fastembed, sem
    # nenhum erro logado) — sinal de kill silencioso por falta de memória.
    # Worker explícito com mais CPU/memória para o carregamento do modelo
    # em ONNX (~1-2GB só o peso, mais overhead do runtime Python/Celery).
    workloads_config {
      scheduler {
        cpu        = 1
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }
      web_server {
        cpu        = 1
        memory_gb  = 2
        storage_gb = 1
      }
      worker {
        cpu        = 2
        memory_gb  = 8
        storage_gb = 5
        min_count  = 1
        max_count  = 1
      }
    }

    node_config {
      service_account = google_service_account.ingestion_sa.email
    }
  }

  depends_on = [
    google_project_service.composer,
    google_project_iam_member.ingestion_composer_worker,
    google_project_iam_member.terraform_composer_admin,
    google_service_account_iam_member.terraform_actas_ingestion,
  ]
}

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
