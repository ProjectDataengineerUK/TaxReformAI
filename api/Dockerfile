# Build context: raiz do repositório (não api/), porque api/main.py importa
# pacotes irmãos (motor_calculo, orquestracao, ingestion) com import absoluto
# (ex: `from motor_calculo.engine import ...`). Rodar sempre como:
#   docker build -f api/Dockerfile -t <tag> .
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# requirements-api.txt, não requirements.txt: a imagem só precisa de
# fastapi/uvicorn/pydantic. O set completo traria fastembed (que arrasta
# onnxruntime), qdrant-client, lxml e pytest — nada disso é importado em
# runtime pela API (ver DESIGN, Decisão 2).
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

# Só os pacotes Python que api/ importa em runtime (ver imports reais em
# api/main.py e api/routers/*.py) — frontend/, tests/, dags/ ficam de fora.
# De ingestion/ só se usa chunking/chunk_models.py (Pydantic puro), mas copiar
# o pacote inteiro é mais simples e barato que recortá-lo.
COPY api/ ./api/
COPY motor_calculo/ ./motor_calculo/
COPY orquestracao/ ./orquestracao/
COPY ingestion/ ./ingestion/

EXPOSE 8080

# Cloud Run injeta a variável PORT (default 8080); mantemos 8080 fixo aqui
# porque é o valor padrão do Cloud Run e o que o workflow de deploy espera.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
