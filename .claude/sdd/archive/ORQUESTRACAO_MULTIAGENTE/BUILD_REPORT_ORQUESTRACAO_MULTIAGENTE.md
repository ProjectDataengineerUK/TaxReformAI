# BUILD REPORT: Orquestração Multi-Agente (LangGraph)

> Implementation report for ORQUESTRACAO_MULTIAGENTE

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ORQUESTRACAO_MULTIAGENTE |
| **Date** | 2026-07-23 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_ORQUESTRACAO_MULTIAGENTE.md](../features/DEFINE_ORQUESTRACAO_MULTIAGENTE.md) |
| **DESIGN** | [DESIGN_ORQUESTRACAO_MULTIAGENTE.md](../features/DESIGN_ORQUESTRACAO_MULTIAGENTE.md) |
| **Status** | Complete (lógica de negócio) / Blocked (grafo real via `langgraph`) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 11/11 |
| **Files Created** | 11 |
| **Lines of Code** | ~356 (Python) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 49/49 (12 novos desta feature + 37 pré-existentes, sem regressão) |
| **Agents Used** | 0 (execução direta) |

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `orquestracao/__init__.py` | 0 | ✅ | |
| `orquestracao/estado.py` | 37 | ✅ | `State` (Pydantic) + `TransicaoAuditavel`; reaproveita `Chunk` e `ResultadoCalculo` das features anteriores sem conflito de tipos |
| `orquestracao/nos/__init__.py` | 0 | ✅ | |
| `orquestracao/nos/classificador.py` | 28 | ✅ | PII real (regex) + intenção fake — **bug de vazamento de PII no histórico encontrado e corrigido durante o build** (ver Issues) |
| `orquestracao/nos/pesquisador_legal.py` | 28 | ✅ | Fake retornando `Chunk` real (schema de `ingestion/`) |
| `orquestracao/nos/extrator_regras.py` | 17 | ✅ | Fake, payload compatível com `TaxCalculatorEngine` |
| `orquestracao/nos/deterministico.py` | 22 | ✅ | Integração real com `motor_calculo.engine.TaxCalculatorEngine` |
| `orquestracao/nos/sintetizador.py` | 27 | ✅ | Fake, parecer Markdown citando `fonte_legal` |
| `orquestracao/grafo.py` | 30 | ✅ | Wiring via `langgraph`; import isolado dentro de `construir_grafo()` — módulo importa sem erro mesmo sem `langgraph` instalado (verificado manualmente) |
| `tests/test_nos.py` | 90 | ✅ | 9/9 testes unitários passam |
| `tests/test_grafo_integration.py` | 77 | ✅ | 3/3 testes passam — AT-001, AT-002, AT-003 |

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
$ python3 -m pytest tests/ -v
...
tests/test_grafo_integration.py::test_at001_happy_path_grafo_completo PASSED
tests/test_grafo_integration.py::test_at002_ano_sem_aliquota_confirmada_interrompe_sem_parecer_inventado PASSED
tests/test_grafo_integration.py::test_at003_cpf_mascarado_antes_de_qualquer_no_subsequente PASSED
tests/test_nos.py:: (9 casos) PASSED
... (37 testes das duas features anteriores, sem regressão)

============================== 49 passed in 0.81s ==============================
```

**Status:** ✅ 49/49 Pass (12 novos + 37 pré-existentes, sem regressão)

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|--------------|
| 1 | `langgraph` não instalável neste sandbox (`externally-managed-environment`, mesmo bloqueio já visto com `qdrant-client`/`fastembed`/`typer`) | Aplicado o mesmo padrão da feature de ingestão: import de `langgraph` isolado dentro de `construir_grafo()`; verificado manualmente que `orquestracao/grafo.py` importa sem erro mesmo sem a lib instalada | +5m |
| 2 | **`no_classificador` vazava o texto original (com PII) para o histórico auditável**, via `resumo_input=state.texto_consulta[:50]` — bug estava presente tanto no código quanto no próprio Pattern 2 do DESIGN, copiado ao pé da letra | `test_at003_cpf_mascarado_antes_de_qualquer_no_subsequente` pegou o bug (verifica que o CPF não aparece em nenhuma entrada do histórico). Corrigido para `resumo_input=texto_mascarado[:50]` — tanto no código quanto no DESIGN, para não repetir o erro se o padrão for reaproveitado depois | +5m |
| 3 | Pydantic `State` precisou de `arbitrary_types_allowed=True` para aceitar `ResultadoCalculo` (dataclass de `motor_calculo`) como campo | Adicionado `model_config = ConfigDict(arbitrary_types_allowed=True)`; testado manualmente antes de escrever os testes formais — funcionou sem problema | +2m |

---

## Deviations from Design

Nenhuma na arquitetura — só a correção de bug descrita no Issue #2, que também foi replicada no próprio arquivo DESIGN para manter o documento como referência correta.

---

## Blockers

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| `langgraph` não instalável neste sandbox | Instalar `langgraph` (idealmente numa venv/pipx) num ambiente com controle do usuário, depois rodar `orquestracao.grafo.construir_grafo()` manualmente para o teste E2E real | Usuário |
| Nenhum LLM real conectado (Classificador-intenção, Pesquisador Legal, Extrator, Sintetizador continuam fakes) | Feature futura, quando houver credenciais Claude/Vertex AI — fora de escopo desta feature por decisão do DEFINE | Usuário / feature futura |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path — grafo completo para consulta sintética | ✅ Pass | `test_at001_happy_path_grafo_completo`: 5 nós executam em ordem, `resultado_calculo` real (`valor_liquido=2475.00`), `parecer_final` presente |
| AT-002 | Error case — ano sem alíquota confirmada | ✅ Pass | `test_at002_...`: `AliquotaNaoDisponivelError` propaga do nó Determinístico; `resultado_calculo` e `parecer_final` permanecem `None` |
| AT-003 | Edge case — CPF mascarado antes de nós subsequentes | ✅ Pass (após correção do bug do Issue #2) | `test_at003_...`: CPF não aparece em `texto_mascarado` nem em nenhuma entrada do `historico` |

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| Grafo executa os 5 nós em ordem para 1 consulta sintética, sem exceções | ✅ | `test_at001_happy_path_grafo_completo` |
| CPF/CNPJ mascarados antes de chegar aos demais nós | ✅ | `test_at003_...` (após correção) + `test_mascarar_pii_cpf`/`test_mascarar_pii_cnpj` |
| Resultado do nó Determinístico bate com chamada direta ao `TaxCalculatorEngine` | ✅ | `test_no_deterministico_integra_de_verdade_com_motor_calculo` — mesmos valores que os testes de `motor_calculo` já validam |
| Estado final permite reconstruir o que cada nó recebeu/retornou | ✅ | `historico` verificado em `test_at001_...` (ordem exata dos 5 nós) e `test_at003_...` (conteúdo sem PII) |

---

## Final Status

### Overall: ✅ COMPLETE (lógica de negócio) — 🔄 grafo real (`langgraph`) aguardando instalação num ambiente com controle do usuário

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados (11/11)
- [x] Lint (`ruff`) passa
- [x] Testes automatizados passam (49/49, sem regressão)
- [x] Um bug real de vazamento de PII encontrado por teste e corrigido (código + DESIGN)
- [x] AT-001, AT-002, AT-003 verificados
- [ ] `construir_grafo()` real via `langgraph` instalado — bloqueado neste sandbox

---

## Next Step

`/ship .claude/sdd/features/DEFINE_ORQUESTRACAO_MULTIAGENTE.md` — considerar se o `langgraph` não instalável deve ser tratado como blocker que impede o ship (como na feature de ingestão) ou se a lógica de negócio 100% testada já é suficiente, dado que o wiring real é uma camada fina e isolada.
