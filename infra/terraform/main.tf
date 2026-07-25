terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
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
