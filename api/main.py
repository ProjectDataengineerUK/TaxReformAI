import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.query import router as query_router
from api.routers.simulate import router as simulate_router

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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
