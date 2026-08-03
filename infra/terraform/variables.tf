variable "project_id" {
  description = "GCP project ID onde o bucket de raw storage sera provisionado"
  type        = string
}

variable "region" {
  description = "Regiao GCP, conforme blueprint (secao 5.1)"
  type        = string
  default     = "southamerica-east1"
}

variable "bucket_name" {
  description = "Nome do bucket GCS de raw storage (globalmente unico)"
  type        = string
}

# CLOUD_COMPOSER_PROVISIONAMENTO — a SA que roda o Terraform (GCP_SA_KEY, chave
# bootstrap que precede este próprio código, nunca modelada como recurso aqui)
# precisa de `composer.environments.create`, que não tinha até este achado real
# (1a tentativa de `terraform apply` falhou com 403 PERMISSION_DENIED). Extraída
# em runtime do `client_email` da própria chave JSON (terraform.yml), não
# hardcoded — funciona mesmo que a SA seja rotacionada no futuro.
variable "terraform_sa_email" {
  description = "E-mail da SA que executa o Terraform (extraído de GCP_SA_KEY em runtime)"
  type        = string
}

# CLOUD_COMPOSER_PROVISIONAMENTO — Settings.from_env() (ingestion/config.py)
# exige QDRANT_URL/QDRANT_API_KEY como env vars do PROCESSO da task; Airflow
# Variables (`airflow variables set`) não viram env var automaticamente, só
# são lidas via Variable.get() no código do DAG, que este projeto não usa.
# Só a via env_variables do software_config realmente funciona aqui.
variable "qdrant_url" {
  description = "URL do Qdrant Cloud (mesmo valor de QDRANT_URL nos GitHub Secrets)"
  type        = string
  sensitive   = true
}

variable "qdrant_api_key" {
  description = "API key do Qdrant Cloud (mesmo valor de QDRANT_API_KEY nos GitHub Secrets)"
  type        = string
  sensitive   = true
}
