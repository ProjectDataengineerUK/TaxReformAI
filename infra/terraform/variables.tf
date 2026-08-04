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
