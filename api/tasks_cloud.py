"""Cloud Tasks — criação da task de processamento e verificação do token
OIDC que o Cloud Tasks anexa à chamada de volta (FILA_ASSINCRONA_CELERY_REDIS).

Decisão 1 do DESIGN: o mesmo serviço Cloud Run serve rotas públicas
(protegidas por X-API-Key) e a rota interna de processamento — a proteção
nativa do Cloud Run (--no-allow-unauthenticated) é por SERVIÇO inteiro, não
por rota, então a verificação do token acontece aqui, no código, não na
borda da plataforma.
"""

from __future__ import annotations

import json
import os

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

QUEUE = "sku-upload-processamento"


def _config() -> tuple[str, str, str, str]:
    project_id = os.environ["GCP_PROJECT_ID"]
    location = os.environ.get("GCP_REGION", "southamerica-east1")
    runtime_sa_email = os.environ["RUNTIME_SA_EMAIL"]
    api_base_url = os.environ["API_BASE_URL"]
    return project_id, location, runtime_sa_email, api_base_url


def criar_task_processamento(job_id: str, tenant_id: str) -> None:
    """`tenant_id` vai no corpo da task — a rota interna não tem API key para
    resolver o tenant sozinha, e ler o job sem tenant conhecido exigiria
    bypassar a RLS (rejeitado por desenho, ver Decisão 2 do DESIGN).

    Import de `tasks_v2` fica DENTRO da função — mesma disciplina de
    `api/db.py` para `psycopg_pool`: rotas que nunca enfileiram uma task
    (a maioria da API) não precisam de `google-cloud-tasks` instalado só
    para `api.main` importar."""
    from google.cloud import tasks_v2

    project_id, location, runtime_sa_email, api_base_url = _config()
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project_id, location, QUEUE)
    url = f"{api_base_url}/v1/tax/skus/upload/processar-tarefa"

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"job_id": job_id, "tenant_id": tenant_id}).encode(),
            "oidc_token": {
                "service_account_email": runtime_sa_email,
                "audience": api_base_url,
            },
        }
    }
    client.create_task(request={"parent": parent, "task": task})


def verificar_token_oidc(authorization_header: str | None) -> bool:
    """`False` para QUALQUER cabeçalho ausente/malformado/inválido — nunca
    levanta exceção, o router decide o 401. Nunca confia em nada além da
    assinatura verificada do Google mais o email exato da SA esperada."""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    _project_id, _location, runtime_sa_email, api_base_url = _config()
    token = authorization_header.removeprefix("Bearer ")
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=api_base_url)
    except ValueError:
        return False
    return claims.get("email") == runtime_sa_email and claims.get("email_verified", False)
