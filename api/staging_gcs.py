"""Staging do arquivo de upload de SKUs no GCS — a Cloud Task carrega só a
URI (string pequena), nunca o CSV inteiro embutido na mensagem
(FILA_ASSINCRONA_CELERY_REDIS, Decisão 4 herdada do /brainstorm original)."""

from __future__ import annotations

import os
import uuid


def _bucket_nome() -> str:
    return os.environ["SKU_UPLOAD_STAGING_BUCKET"]


def enviar_para_staging(tenant_id: str, conteudo: bytes) -> str:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(_bucket_nome())
    caminho = f"{tenant_id}/{uuid.uuid4().hex}.csv"
    blob = bucket.blob(caminho)
    blob.upload_from_string(conteudo, content_type="text/csv")
    return f"gs://{_bucket_nome()}/{caminho}"


def baixar_do_staging(gcs_uri: str) -> bytes:
    from google.cloud import storage

    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"URI de staging inválida: {gcs_uri!r}")
    sem_prefixo = gcs_uri.removeprefix("gs://")
    bucket_nome, _, caminho = sem_prefixo.partition("/")

    client = storage.Client()
    blob = client.bucket(bucket_nome).blob(caminho)
    return blob.download_as_bytes()
