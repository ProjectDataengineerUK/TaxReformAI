# BUILD REPORT: API HTTP de Simulação (`/v1/tax/simulate` + endpoint conversacional)

> Implementation report for API_HTTP_SIMULACAO

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_HTTP_SIMULACAO |
| **Date** | 2026-07-23 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_API_HTTP_SIMULACAO.md](../features/DEFINE_API_HTTP_SIMULACAO.md) |
| **DESIGN** | [DESIGN_API_HTTP_SIMULACAO.md](../features/DESIGN_API_HTTP_SIMULACAO.md) |
| **Status** | ✅ Complete — primeira feature testada com servidor HTTP real de ponta a ponta |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 13/13 (12 novos + 1 modificado) |
| **Files Created** | 12 |
| **Files Modified** | 1 (`tests/test_grafo_integration.py`) |
| **Lines of Code** | ~419 (Python) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 59/59 (13 novos + 46 pré-existentes, sem regressão) |
| **Agents Used** | 0 (execução direta) |

**Diferente das 3 features anteriores**: `FastAPI`/`uvicorn`/`httpx` já estavam disponíveis neste sandbox — nenhum blocker de dependência não instalável. Esta é a primeira feature verificada com um servidor HTTP real (`uvicorn`) respondendo a requisições `curl`, não só `TestClient`.

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `orquestracao/executor.py` | 20 | ✅ | Encadeamento sequencial promovido de `tests/test_grafo_integration.py` para produção |
| `api/__init__.py` | 0 | ✅ | |
| `api/config.py` | 26 | ✅ | `ApiSettings.from_env()` + `get_settings()` com `lru_cache` |
| `api/auth.py` | 16 | ✅ | **Corrigido durante o build** — header ausente inicialmente retornava 422 em vez de 401 (ver Issues) |
| `api/schemas_simulate.py` | 47 | ✅ | Schema idêntico ao exemplo da seção 8 do blueprint |
| `api/schemas_query.py` | 21 | ✅ | |
| `api/routers/__init__.py` | 0 | ✅ | |
| `api/routers/simulate.py` | 74 | ✅ | Verificação de alíquota uma vez por requisição, antes de iterar itens |
| `api/routers/query.py` | 38 | ✅ | |
| `api/main.py` | 13 | ✅ | Testado com `uvicorn` real + `curl` |
| `tests/test_api_simulate.py` | 89 | ✅ | 6/6 testes passam |
| `tests/test_api_query.py` | 75 | ✅ | 4/4 testes passam |

## Files Modified

| File | Change |
| ---- | ------ |
| `tests/test_grafo_integration.py` | Removido o helper local `executar_grafo_sequencial`; agora importa `executar_consulta` de `orquestracao.executor` (Decision 1 do DESIGN) |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass

### Type Check

Não configurado neste ciclo (mesmo padrão das features anteriores).

**Status:** ⏭️ Skipped

### Tests

```text
$ python3 -m pytest tests/ -q
59 passed, 1 warning in 0.97s
```

**Status:** ✅ 59/59 Pass (13 novos + 46 pré-existentes, sem regressão)

O único warning é uma `StarletteDeprecationWarning` sobre `httpx` com `TestClient` (específica da versão de FastAPI instalada neste sandbox) — não afeta o comportamento, apenas informativo.

### E2E Manual (servidor HTTP real)

```bash
$ API_KEYS='{"chave-e2e":"tenant-e2e"}' uvicorn api.main:app --port 8123 &
$ curl http://127.0.0.1:8123/healthz
{"status":"ok"}
$ curl -X POST http://127.0.0.1:8123/v1/tax/query -H "X-API-Key: chave-e2e" ... 
{"parecer_final":"...", "valor_liquido":"495.00", ...}
```

**Status:** ✅ Pass — servidor real, requisição HTTP real, não apenas `TestClient`

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|--------------|
| 1 | `HTTP_422_UNPROCESSABLE_ENTITY` deprecado nesta versão do FastAPI (`status.HTTP_422_UNPROCESSABLE_CONTENT` é o substituto) | Substituído nos dois routers | +2m |
| 2 | **Header `X-API-Key` ausente retornava 422 (validação nativa do FastAPI para parâmetro obrigatório), não 401 como o DEFINE exige** ("Requisições sem X-API-Key válida retornam 401 em ambos os endpoints") | `Header(...)` (obrigatório) trocado por `Header(None)` (opcional) + checagem explícita de `None` dentro da dependency — agora ausência e invalidez retornam 401 de forma consistente | +5m |
| 3 | Teste inicial comparava `"25000.0"` em vez de `"25000.00"` — erro de digitação no valor esperado, não um bug de código | Corrigido o valor esperado no teste | +1m |

---

## Deviations from Design

Nenhuma na arquitetura — as duas correções (Issues #1 e #2) são refinamentos dentro do que o DESIGN já especificava (Decision 2 — autenticação), não mudanças de abordagem.

---

## Blockers

Nenhum. Esta é a primeira das quatro features do projeto sem nenhum blocker de infraestrutura ou dependência não instalável.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path (estruturado) — payload da seção 8, ano 2026 | ✅ Pass | `test_at001_happy_path_ano_2026`: 200, `resumo_financeiro` e `itens_detalhados` corretos |
| AT-002 | Error case (auth) — sem `X-API-Key` ou chave inválida, ambos os endpoints | ✅ Pass (após correção do Issue #2) | `test_at002_sem_api_key_retorna_401` e `test_at002_api_key_invalida_retorna_401` em ambos os arquivos de teste |
| AT-003 | Edge case (conversacional) — ano sem alíquota confirmada | ✅ Pass | `test_at003_ano_sem_aliquota_confirmada_retorna_422_nao_parecer_inventado`: 422, sem `parecer_final` na resposta |

**Bônus verificado (não era Acceptance Test formal, mas decorre da Decision 3 do DESIGN):** o próprio exemplo `ano_operacao: 2027` da seção 8 do blueprint retorna `422` nesta implementação, em vez das alíquotas ilustrativas do exemplo — `test_ano_2027_do_exemplo_do_blueprint_retorna_422_nao_numeros_inventados` confirma isso explicitamente.

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| `POST /v1/tax/simulate` retorna `resumo_financeiro`/`itens_detalhados` no formato da seção 8 | ✅ | `test_at001_happy_path_ano_2026` + E2E manual |
| `POST /v1/tax/query` retorna `parecer_final`/`resultado_calculo`/histórico | ✅ | `test_happy_path_conversacional_ano_2026` + E2E manual |
| Requisição sem `X-API-Key` válida retorna 401 em ambos | ✅ | 4 testes dedicados (2 por endpoint: ausente + inválida) |
| `itens[]` acima de 100 retorna 422 | ✅ | `test_itens_acima_do_limite_retorna_422` |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados/modificados (13/13)
- [x] Lint (`ruff`) passa
- [x] Testes automatizados passam (59/59, sem regressão)
- [x] Verificado com servidor HTTP real (`uvicorn` + `curl`), não só `TestClient`
- [x] Um bug real de comportamento de auth (422 vs 401) encontrado e corrigido
- [x] Todos os Acceptance Tests verificados
- [x] Pronto para `/ship`

---

## Next Step

`/ship .claude/sdd/features/DEFINE_API_HTTP_SIMULACAO.md`
