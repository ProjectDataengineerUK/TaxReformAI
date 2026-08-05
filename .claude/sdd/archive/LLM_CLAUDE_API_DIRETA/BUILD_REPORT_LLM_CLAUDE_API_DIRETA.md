# BUILD REPORT: LLM_CLAUDE_API_DIRETA

> Implementation report for LLM_CLAUDE_API_DIRETA

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_CLAUDE_API_DIRETA |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **DEFINE** | [DEFINE_LLM_CLAUDE_API_DIRETA.md](../features/DEFINE_LLM_CLAUDE_API_DIRETA.md) |
| **DESIGN** | [DESIGN_LLM_CLAUDE_API_DIRETA.md](../features/DESIGN_LLM_CLAUDE_API_DIRETA.md) |
| **Status** | Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 7/7 (manifesto completo do DESIGN) |
| **Files Created** | 1 (`tests/test_dependencias.py`) |
| **Files Modified** | 6 |
| **Build Time** | ~25min |
| **Tests Passing** | 634/641 (7 skip por `DATABASE_URL` ausente, esperado) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `orquestracao/llm/cliente.py` — `_extrair_texto`, mapa de tradução, `ClienteAnthropicDireto` | ✅ Complete | `ClienteVertexAI` refatorado para reusar `_extrair_texto`, comportamento idêntico |
| 2 | `orquestracao/config.py` — `llm_provider`/`anthropic_api_key`, `GCP_PROJECT_ID` condicional | ✅ Complete | — |
| 3 | `orquestracao/dependencias.py` — seleção de provider em `criar_dependencias_reais` | ✅ Complete | — |
| 4 | `.env.example` | ✅ Complete | — |
| 5 | `.github/workflows/deploy.yml` | ✅ Complete | `LLM_PROVIDER=direto` fixo (não é segredo), `ANTHROPIC_API_KEY` via secret novo |
| 6 | `tests/test_llm_cliente.py` | ✅ Complete | 5 testes novos para `ClienteAnthropicDireto` |
| 7 | `tests/test_dependencias.py` | ✅ Complete | 5 testes novos — seleção de provider + `from_env` condicional |

---

## Files Created

| File | Lines | Notes |
| ---- | ----- | ----- |
| `tests/test_dependencias.py` | 71 | 5 testes: seleção de provider (2) + `from_env` condicional (3) |

---

## Verification Results

### Lint Check

```text
ruff check .
All checks passed!
```

**Status:** ✅ Pass

### Type Check

N/A — projeto não usa `mypy` (mesma situação de toda feature Python anterior deste projeto).

**Status:** ⏭️ Skipped (não configurado)

### Tests

```text
tests/test_llm_cliente.py ..........          (10 passed, 5 novos)
tests/test_dependencias.py .....               (5 passed, novo arquivo)
tests/test_nos.py, test_grafo_integration.py, test_api_query.py  (todos passed, sem regressão)

634 passed, 7 skipped, 1 warning in 8.38s   (suíte completa, PYTHONPATH com anthropic real instalado)
```

**Status:** ✅ 634/641 Pass (7 skips são os testes de `db/` que já pulavam antes desta feature,
sem `DATABASE_URL` — não relacionados)

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `anthropic` não estava instalado neste sandbox (mesma situação já documentada em `LLM_REAL_VERTEX_AI`) | Reinstalado via `pip install --target=<scratchpad>` para rodar os testes reais com `PYTHONPATH` apontando pro diretório isolado — mesmo contorno de PEP 668 já usado antes, não persistido no ambiente global | +3m |

---

## Deviations from Design

Nenhuma. O achado real de tradução de modelo e o helper `_extrair_texto` já tinham sido
antecipados e documentados como Decisions no próprio `/design` — o `/build` seguiu o DESIGN sem
desvio.

---

## Blockers

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Provider direto é o default | ✅ Pass | `test_criar_dependencias_reais_usa_api_direta_por_default` |
| AT-002 | Provider Vertex continua funcionando | ✅ Pass | `test_criar_dependencias_reais_usa_vertex_quando_configurado` |
| AT-003 | Chamada real via API direta | ✅ Pass (unitário/mock) | `test_cliente_anthropic_direto_extrai_texto_do_bloco_de_resposta` — chamada HTTP real contra `api.anthropic.com` só verificável pós-deploy, com `ANTHROPIC_API_KEY` real |
| AT-004 | Erro da API direta vira `LLMIndisponivelError` | ✅ Pass | `test_cliente_anthropic_direto_erro_de_rede_vira_llm_indisponivel_error`, `test_cliente_anthropic_direto_resposta_sem_bloco_de_texto_levanta_erro` |
| AT-005 | `POST /v1/tax/query` em produção | ⏳ Pendente | Só verificável contra infraestrutura real, pós-deploy — mesma disciplina de `LLM_REAL_VERTEX_AI`; requer `ANTHROPIC_API_KEY` real cadastrada no GitHub Secrets primeiro |
| AT-006 | Nenhum nó muda | ✅ Pass | `git diff --stat -- orquestracao/nos/` vazio, confirmado |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] Todos os arquivos do manifesto criados/modificados
- [x] `ruff check .` limpo
- [x] Type check N/A (não configurado no projeto)
- [x] 634/641 testes passam (7 skips pré-existentes, não relacionados)
- [x] Nenhum bloqueio
- [x] AT-001, AT-002, AT-003, AT-004, AT-006 verificados; AT-005 pendente de deploy real
- [x] Pronto para `/ship`

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_LLM_CLAUDE_API_DIRETA.md`

**Nota para o usuário antes do deploy real:** esta feature só chama a API Claude de verdade
depois que o GitHub Secret `ANTHROPIC_API_KEY` for cadastrado manualmente (nunca pelo agente),
com uma chave criada em console.anthropic.com. Sem ela, `LLM_PROVIDER=direto` (o default) faria
`OrquestracaoSettings.from_env()` levantar `RuntimeError` no boot do serviço — falha ruidosa, não
um 503 silencioso por request.
