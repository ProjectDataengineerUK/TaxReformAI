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

# Service Account User escopado só na própria SA de deploy (não no projeto):
# necessário para o `gcloud run deploy --service-account=taxreformai-deployer@...`
# rodar o serviço Cloud Run usando essa identidade.
resource "google_service_account_iam_member" "deployer_sa_user_self" {
  service_account_id = google_service_account.deployer_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer_sa.email}"
}

output "deployer_service_account_email" {
  value = google_service_account.deployer_sa.email
}

output "artifact_registry_repository" {
  value = "${google_artifact_registry_repository.docker_images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_images.repository_id}"
}
