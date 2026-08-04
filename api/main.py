import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.empresa_skus import router as empresa_skus_router
from api.routers.query import router as query_router
from api.routers.simulate import router as simulate_router
from api.routers.skus_tasks import router as skus_tasks_router

app = FastAPI(title="TaxReform AI API", version="0.1.0")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_frontend_origins = os.environ.get("FRONTEND_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulate_router)
app.include_router(query_router)
app.include_router(empresa_skus_router)
app.include_router(skus_tasks_router)


# /health, NÃO /healthz: o Google Front End intercepta o path exato `/healthz`
# em domínios *.run.app e devolve o próprio 404 em HTML — a requisição nunca
# chega no contêiner. Verificado contra o serviço real em 2026-07-25:
#   /foo     -> 404 {"detail":"Not Found"}   (FastAPI, chegou)
#   /health  -> 404 {"detail":"Not Found"}   (FastAPI, chegou)
#   /healthz -> 404 <!DOCTYPE html> ...      (Google, NÃO chegou)
#   /healthz/-> 307                          (a rota existia o tempo todo)
# Só aparece num deploy real; localmente e nos testes com TestClient passava.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
