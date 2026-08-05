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

# BIGQUERY_DATA_WAREHOUSE — a SA que roda o Terraform (GCP_SA_KEY) não tinha
# `bigquery.datasets.create` (achado real da 1a tentativa de apply, 403
# PERMISSION_DENIED). Extraída em runtime do `client_email` da própria chave
# JSON (terraform.yml), não hardcoded — mesmo mecanismo já usado por
# CLOUD_COMPOSER_PROVISIONAMENTO (removido junto com os recursos do Composer,
# reintroduzido aqui para este novo uso legítimo).
variable "terraform_sa_email" {
  description = "E-mail da SA que executa o Terraform (extraído de GCP_SA_KEY em runtime)"
  type        = string
}

# PAINEL_OBSERVABILIDADE — o Billing Export é habilitado manualmente pelo
# usuário no Console GCP (ação fora do alcance do Terraform — não existe
# recurso `google_bigquery_dataset` aqui, só um `data` source lendo o que já
# existe). Reaproveita `taxreformai_analytics` (já existente desde
# BIGQUERY_DATA_WAREHOUSE), não um dataset dedicado — decisão explícita do
# usuário: `taxreformai-cost-sync` ganha leitura também de
# `pareceres_historico`, aceito porque é SA interna sem exposição externa.
# Mesmo nome usado em BILLING_EXPORT_DATASET no workflow.
variable "billing_export_dataset" {
  description = "Dataset BigQuery do Billing Export — reaproveita taxreformai_analytics, criado manualmente no Console GCP"
  type        = string
  default     = "taxreformai_analytics"
}
