# DESIGN: API HTTP de Simulação (`/v1/tax/simulate` + endpoint conversacional)

> Technical design for implementing a API FastAPI que expõe o motor de cálculo (endpoint estruturado) e o grafo de orquestração (endpoint conversacional), com autenticação mínima via API key.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_HTTP_SIMULACAO |
| **Date** | 2026-07-23 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_API_HTTP_SIMULACAO.md](./DEFINE_API_HTTP_SIMULACAO.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    API HTTP DE SIMULAÇÃO (FastAPI) — MVP                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Cliente HTTP]                                                           │
│        │  X-API-Key header                                               │
│        ▼                                                                  │
│  [api.auth.verificar_api_key] ── 401 se ausente/inválida                 │
│        │                                                                   │
│        ├──► POST /v1/tax/simulate (estruturado, seção 8)                 │
│        │       │  api/routers/simulate.py                                │
│        │       ▼                                                          │
│        │   Para cada item: motor_calculo.TaxCalculatorEngine.calcular()  │
│        │       │  (fase resolvida 1x, erro upfront se não confirmada)    │
│        │       ▼                                                          │
│        │   resumo_financeiro + itens_detalhados                          │
│        │                                                                   │
│        └──► POST /v1/tax/query (conversacional)                          │
│                │  api/routers/query.py                                   │
│                ▼                                                          │
│            orquestracao.executor.executar_consulta(State)                │
│                │  (5 nós em sequência, sem depender de langgraph)        │
│                ▼                                                          │
│            parecer_final + resultado_calculo + histórico                 │
│                                                                             │
│  api/main.py: FastAPI app, roteadores + /healthz                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `api.config.ApiSettings` | Carrega o mapa `API_KEYS` (JSON) e o limite de itens da env var | Python `dataclass` + `functools.lru_cache` |
| `api.auth.verificar_api_key` | Dependency FastAPI — valida `X-API-Key`, resolve `tenant_id` | FastAPI `Depends` |
| `api.schemas_simulate` / `api.schemas_query` | Modelos Pydantic de request/response dos dois endpoints | `pydantic.BaseModel` |
| `api.routers.simulate` | `POST /v1/tax/simulate` — chama `motor_calculo` por item | FastAPI `APIRouter` |
| `api.routers.query` | `POST /v1/tax/query` — chama `orquestracao.executor` | FastAPI `APIRouter` |
| `orquestracao.executor` | **Novo** — promove o encadeamento sequencial dos 5 nós para produção | Python puro, reaproveita `orquestracao/nos/*` |
| `api.main` | App FastAPI, inclui os roteadores, expõe `/healthz` | `FastAPI` + `uvicorn` |

---

## Key Decisions

### Decision 1: `orquestracao/executor.py` — encadeamento sequencial promovido a produção

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** `langgraph` não é instalável neste sandbox (mesmo bloqueio do BUILD_REPORT de `ORQUESTRACAO_MULTIAGENTE`). A API precisa funcionar de ponta a ponta agora.

**Choice:** `executar_consulta(state: State) -> State` encadeia os 5 nós na mesma ordem que `orquestracao.grafo.construir_grafo()` define via `langgraph`, mas como chamadas Python diretas. `tests/test_grafo_integration.py` passa a importar essa função em vez de definir o helper localmente.

**Rationale:** A interface pública (`State → State`) é idêntica entre `executar_consulta()` e o que o grafo real produziria — quando `langgraph` estiver instalável, `api/routers/query.py` pode trocar para `construir_grafo().invoke(state)` sem mudar o contrato da API.

**Alternatives Rejected:**
1. A API importar `construir_grafo()` diretamente — rejeitado, deixaria o endpoint conversacional não-funcional neste sandbox.

**Consequences:**
- `orquestracao/` passa a ter duas formas de executar o mesmo pipeline (`grafo.py` via LangGraph, `executor.py` sequencial) — aceitável, ambas compartilham os mesmos nós, não há lógica de negócio duplicada

---

### Decision 2: Autenticação via dependency FastAPI simples, chaves em JSON de variável de ambiente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** Sem Postgres/schema de tenants no projeto ainda (DEFINE, Constraints). Precisa provar o mecanismo de autenticação sem essa infraestrutura.

**Choice:** Variável de ambiente `API_KEYS` contém um JSON (`{"chave-1": "tenant-a", "chave-2": "tenant-b"}`), carregado em `ApiSettings` via `lru_cache`. Uma dependency `verificar_api_key()` lê o header `X-API-Key`, resolve o `tenant_id` correspondente ou levanta `401`.

**Rationale:** Prova o mecanismo (header obrigatório, rejeição de chave inválida) sem inventar uma tabela de usuários que não existe.

**Alternatives Rejected:**
1. OAuth2/JWT completo — rejeitado, complexidade desproporcional para uma fase sem usuários reais.

**Consequences:**
- Chaves não são hasheadas nem rotacionadas (Assumption A-002 do DEFINE) — aceitável para esta fase, não para produção real

---

### Decision 3: Payload/resposta do endpoint estruturado seguem a seção 8 exatamente; só o ano 2026 retorna sucesso

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** `TabelaAliquotasSeed` só tem a fase 2026 confirmada. O próprio exemplo da seção 8 do blueprint usa `ano_operacao: 2027` com alíquotas (8,80%/17,70%) que **não são confirmadas** em lei nesta fase do projeto.

**Choice:** Os campos e nomes do payload/resposta seguem a seção 8 exatamente (para integração futura com ERPs ficar direta), mas qualquer `ano_operacao` sem `RegraFiscal` confirmada — incluindo o `2027` do próprio exemplo do blueprint — retorna `422` com `AliquotaNaoDisponivelError`, nunca os números do exemplo ilustrativo.

**Rationale:** Consistente com toda a disciplina de auditabilidade já estabelecida nas features anteriores — nunca fabricar um dado legal não confirmado, mesmo que o próprio blueprint o sugira como exemplo.

**Alternatives Rejected:**
1. Popular `TabelaAliquotasSeed` com os números do exemplo da seção 8 só para o "exemplo funcionar" — rejeitado; esses números são ilustrativos no blueprint, não uma fonte legal verificada.

**Consequences:**
- O teste de happy path (AT-001) usa `ano_operacao=2026`, não o `2027` do exemplo literal do blueprint — documentado explicitamente para não causar confusão

---

### Decision 4: Verificação da alíquota feita uma vez por requisição, antes de iterar os itens

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** Todos os itens de uma mesma requisição compartilham o mesmo `ano_operacao` — não há necessidade de tentar calcular item por item se a fase toda não tem alíquota confirmada.

**Choice:** `simulate.py` resolve `TabelaAliquotasSeed().buscar(fase_para(ano_operacao))` uma única vez no início do handler. Se levantar `AliquotaNaoDisponivelError`, a requisição inteira falha com `422` antes de processar qualquer item.

**Rationale:** Evita processamento parcial (alguns itens calculados, outros não) e evita repetir a mesma checagem N vezes.

**Alternatives Rejected:**
1. Chamar `engine.calcular()` por item e deixar a exceção do primeiro item propagar — rejeitado; funcionalmente equivalente, mas menos claro sobre a intenção (falha atômica, não parcial).

**Consequences:**
- Resposta é sempre tudo-ou-nada: todos os itens simulados, ou nenhum

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `orquestracao/executor.py` | Create | `executar_consulta()` — encadeamento sequencial dos 5 nós, promovido a produção | @python-developer | None |
| 2 | `api/__init__.py` | Create | Marca o pacote | @python-developer | None |
| 3 | `api/config.py` | Create | `ApiSettings` (mapa de API keys, limite de itens) + `get_settings()` | @python-developer | None |
| 4 | `api/auth.py` | Create | `verificar_api_key()` — dependency FastAPI | @security-reviewer | 3 |
| 5 | `api/schemas_simulate.py` | Create | Modelos Pydantic do endpoint estruturado (payload/resposta da seção 8) | @python-developer | None |
| 6 | `api/schemas_query.py` | Create | Modelos Pydantic do endpoint conversacional | @python-developer | None |
| 7 | `api/routers/__init__.py` | Create | Marca o subpacote | @python-developer | None |
| 8 | `api/routers/simulate.py` | Create | `POST /v1/tax/simulate` — itera itens, chama `motor_calculo` | @python-developer | 4, 5 |
| 9 | `api/routers/query.py` | Create | `POST /v1/tax/query` — chama `orquestracao.executor` | @python-developer | 1, 4, 6 |
| 10 | `api/main.py` | Create | App FastAPI, inclui roteadores, `/healthz` | @python-developer | 8, 9 |
| 11 | `tests/test_grafo_integration.py` | Modify | Importa `executar_consulta` de `orquestracao.executor` em vez de helper local | @test-generator | 1 |
| 12 | `tests/test_api_simulate.py` | Create | AT-001 (happy path, ano 2026), auth (AT-002), limite de itens, ano 2027 sem alíquota | @test-generator | 8, 10 |
| 13 | `tests/test_api_query.py` | Create | Happy path conversacional, AT-002 (auth), AT-003 (ano sem alíquota) | @test-generator | 9, 10 |

**Total Files:** 13 (12 novos + 1 modificado)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3, 5, 6, 7, 8, 9, 10 | Especialista em FastAPI, Pydantic e integração entre módulos já existentes |
| @security-reviewer | 4 | Mecanismo de autenticação — revisão dedicada, mesma recomendação já registrada em `CLAUDE.md` após o bug de PII da feature anterior |
| @test-generator | 11, 12, 13 | Especialista em testes pytest + FastAPI `TestClient`, cobrindo os Acceptance Tests do DEFINE |
| @code-reviewer | (revisão final) | Revisão de qualidade geral |

---

## Code Patterns

### Pattern 1: `ApiSettings` e cache de configuração

```python
# api/config.py

import json
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ApiSettings:
    api_keys_to_tenant: dict[str, str]
    max_itens_por_requisicao: int = 100

    @classmethod
    def from_env(cls) -> "ApiSettings":
        raw = os.environ.get("API_KEYS", "{}")
        try:
            mapa = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                'API_KEYS deve ser um JSON válido: {"chave": "tenant_id"}'
            ) from exc
        return cls(api_keys_to_tenant=mapa)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings.from_env()
```

### Pattern 2: Dependency de autenticação

```python
# api/auth.py

from fastapi import Depends, Header, HTTPException, status

from api.config import ApiSettings, get_settings


def verificar_api_key(
    x_api_key: str = Header(...),
    settings: ApiSettings = Depends(get_settings),
) -> str:
    tenant_id = settings.api_keys_to_tenant.get(x_api_key)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        )
    return tenant_id
```

### Pattern 3: Schemas do endpoint estruturado (seção 8)

```python
# api/schemas_simulate.py

from decimal import Decimal

from pydantic import BaseModel, Field


class ItemSimulacao(BaseModel):
    sku: str
    ncm: str
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)
    uf_origem: str
    uf_destino: str


class PayloadSimulacao(BaseModel):
    tenant_id: str
    ano_operacao: int
    operacao_tipo: str
    itens: list[ItemSimulacao] = Field(min_length=1, max_length=100)


class AliquotasAplicadas(BaseModel):
    cbs_percentual: Decimal
    ibs_percentual: Decimal
    is_percentual: Decimal


class ItemDetalhado(BaseModel):
    sku: str
    ncm: str
    aliquotas_aplicadas: AliquotasAplicadas
    fundamentacao_legal: str


class ResumoFinanceiro(BaseModel):
    valor_bruto_total: Decimal
    total_cbs: Decimal
    total_ibs: Decimal
    total_is: Decimal
    valor_liquido_projetado_split_payment: Decimal


class RespostaSimulacao(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    resumo_financeiro: ResumoFinanceiro
    itens_detalhados: list[ItemDetalhado]
```

### Pattern 4: Router estruturado (verificação upfront + iteração)

```python
# api/routers/simulate.py

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verificar_api_key
from api.schemas_simulate import (
    AliquotasAplicadas,
    ItemDetalhado,
    PayloadSimulacao,
    RespostaSimulacao,
    ResumoFinanceiro,
)
from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.fases import fase_para
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed

router = APIRouter(prefix="/v1/tax", tags=["simulate"])


@router.post("/simulate", response_model=RespostaSimulacao)
def simular(
    payload: PayloadSimulacao, tenant_id: str = Depends(verificar_api_key)
) -> RespostaSimulacao:
    tabela = TabelaAliquotasSeed()
    try:
        regra = tabela.buscar(fase_para(payload.ano_operacao))
    except AliquotaNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    engine = TaxCalculatorEngine(tabela=tabela)
    itens_detalhados = []
    acumulado = {"bruto": Decimal("0"), "cbs": Decimal("0"), "ibs": Decimal("0"), "is": Decimal("0"), "liquido": Decimal("0")}

    for item in payload.itens:
        valor_base_item = item.valor_unitario * item.quantidade
        resultado = engine.calcular(valor_base=valor_base_item, ano_operacao=payload.ano_operacao)

        acumulado["bruto"] += valor_base_item
        acumulado["cbs"] += resultado.valor_cbs
        acumulado["ibs"] += resultado.valor_ibs
        acumulado["is"] += resultado.valor_is
        acumulado["liquido"] += resultado.valor_liquido

        itens_detalhados.append(
            ItemDetalhado(
                sku=item.sku,
                ncm=item.ncm,
                aliquotas_aplicadas=AliquotasAplicadas(
                    cbs_percentual=regra.aliq_cbs * 100,
                    ibs_percentual=regra.aliq_ibs * 100,
                    is_percentual=regra.aliq_is * 100,
                ),
                fundamentacao_legal=resultado.fonte_legal,
            )
        )

    return RespostaSimulacao(
        ano_operacao=payload.ano_operacao,
        resumo_financeiro=ResumoFinanceiro(
            valor_bruto_total=acumulado["bruto"],
            total_cbs=acumulado["cbs"],
            total_ibs=acumulado["ibs"],
            total_is=acumulado["is"],
            valor_liquido_projetado_split_payment=acumulado["liquido"],
        ),
        itens_detalhados=itens_detalhados,
    )
```

### Pattern 5: `orquestracao/executor.py`

```python
# orquestracao/executor.py

from orquestracao.estado import State
from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def executar_consulta(state: State) -> State:
    """Encadeia os 5 nós na ordem fixa do pipeline, sem depender de `langgraph`
    (ver Decision 1). `orquestracao.grafo.construir_grafo()` continua sendo a
    implementação via LangGraph para quando a lib estiver instalável — mesma
    interface pública (`State -> State`)."""
    state = no_classificador(state)
    state = no_pesquisador_legal(state)
    state = no_extrator_regras(state)
    state = no_deterministico(state)
    state = no_sintetizador(state)
    return state
```

### Pattern 6: `api/main.py`

```python
# api/main.py

from fastapi import FastAPI

from api.routers.query import router as query_router
from api.routers.simulate import router as simulate_router

app = FastAPI(title="TaxReform AI API", version="0.1.0")
app.include_router(simulate_router)
app.include_router(query_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

---

## Data Flow

```text
Endpoint estruturado:
1. Cliente envia POST /v1/tax/simulate com X-API-Key + payload (seção 8)
2. verificar_api_key resolve tenant_id ou retorna 401
3. Resolve a RegraFiscal da fase uma única vez — 422 se não confirmada
4. Para cada item: calcula valor_base = valor_unitario * quantidade, chama TaxCalculatorEngine
5. Acumula resumo_financeiro; monta itens_detalhados com aliquotas_aplicadas (%) e fundamentacao_legal
6. Retorna 200 com RespostaSimulacao

Endpoint conversacional:
1. Cliente envia POST /v1/tax/query com X-API-Key + texto_consulta/ano_operacao/valor_base
2. verificar_api_key resolve tenant_id ou retorna 401
3. Monta State inicial, chama orquestracao.executor.executar_consulta(state)
4. Se AliquotaNaoDisponivelError: 422
5. Retorna 200 com parecer_final + resultado_calculo + histórico
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| `motor_calculo` | Import Python direto, in-process | N/A |
| `orquestracao` | Import Python direto, in-process | N/A |
| Cliente HTTP (ERP ou futuro frontend) | REST/JSON via FastAPI | Header `X-API-Key` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `verificar_api_key`, schemas (limite de itens) | Incluído em `tests/test_api_simulate.py` | pytest | Casos de borda de auth/validação |
| Integration | Ambos os endpoints via `fastapi.testclient.TestClient` | `tests/test_api_simulate.py`, `tests/test_api_query.py` | pytest + `TestClient` (usa `httpx` já disponível) | AT-001, AT-002, AT-003 |
| E2E | `uvicorn api.main:app` real + requisição HTTP manual | Manual | - | Happy path, quando quiser rodar localmente de verdade |

Testes usam `app.dependency_overrides[get_settings]` para injetar uma `ApiSettings` de teste com chaves conhecidas, em vez de depender de variáveis de ambiente reais.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `X-API-Key` ausente ou inválida | `401` via `verificar_api_key` | No |
| `AliquotaNaoDisponivelError` (qualquer endpoint) | `422` com a mensagem da exceção — nunca um número/parecer inventado | No |
| `itens[]` vazio ou acima de 100 | `422` automático do Pydantic (`Field(min_length=1, max_length=100)`) | No |
| `valor_unitario`/`quantidade` inválidos (≤0) | `422` automático do Pydantic (`Field(gt=0)`) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `API_KEYS` | string (JSON) | `"{}"` | Mapa de API key → `tenant_id`, ex: `{"chave-1": "tenant-a"}` |

---

## Security Considerations

- `API_KEYS` nunca deve ser commitado — só via variável de ambiente/secret manager, seguindo o mesmo padrão de `.env`/`.gitignore` já estabelecido em `ingestion/`
- Chaves não são hasheadas nesta fase (Assumption A-002 do DEFINE) — não usar este mecanismo além de MVP/demo interno
- Nenhum dado de PII é aceito diretamente pelo endpoint estruturado; o endpoint conversacional herda a máscara de PII já implementada em `orquestracao/nos/classificador.py`
- `tenant_id` do payload do endpoint estruturado **não** é usado para autorização real nesta fase — é só repassado; a autorização de fato vem do `X-API-Key` → `tenant_id` resolvido pela dependency. Isso deve ficar claro na documentação da API para não sugerir isolamento multi-tenant que não existe ainda

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Não implementado nesta feature — FastAPI/uvicorn já logam requisições HTTP por padrão |
| Metrics | N/A |
| Tracing | N/A |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-23 | design-agent | Versão inicial, a partir de DEFINE_API_HTTP_SIMULACAO.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_API_HTTP_SIMULACAO.md`
