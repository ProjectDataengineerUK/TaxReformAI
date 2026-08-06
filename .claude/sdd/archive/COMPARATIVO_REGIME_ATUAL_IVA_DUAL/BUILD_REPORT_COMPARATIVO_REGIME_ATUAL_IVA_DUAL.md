# BUILD REPORT: COMPARATIVO_REGIME_ATUAL_IVA_DUAL

> Implementation report

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMPARATIVO_REGIME_ATUAL_IVA_DUAL |
| **Date** | 2026-08-06 |
| **Author** | build-agent (direto, sem subagentes) |
| **DEFINE** | [DEFINE_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md](../features/DEFINE_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md) |
| **DESIGN** | [DESIGN_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md](../features/DESIGN_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md) |
| **Status** | Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 24/24 (manifesto completo) |
| **Files Created** | 4 |
| **Files Modified** | 20 |
| **Tests Passing (backend)** | 664/664 (+ 9 skipped, sem DATABASE_URL) |
| **Tests Passing (frontend)** | 39/39 |
| **Agents Used** | 0 (build direto) |

---

## Files Created

| File | Verified | Notes |
| ---- | -------- | ----- |
| `api/simulacao.py` | ✅ | Extração literal de `simular()` (~650 linhas), 2 substituições de exceção (HTTPException → domínio), campo novo `fonte_legal_fase` |
| `tests/test_simulacao.py` | ✅ | 8 testes unitários da função extraída, isolada de FastAPI |
| `frontend/components/ComparativoRegime.tsx` | ✅ | Tabela agregada + por item, compartilhada por `/simulador` e `/consulta` |
| `frontend/components/ComparativoRegime.test.tsx` | ✅ | 5 testes (totais, "não calculado", escopo, item, fonte legal) |

## Files Modified

| File | Notes |
| ---- | ----- |
| `api/schemas_simulate.py` | `RespostaSimulacao` ganha `fonte_legal_fase: str` |
| `api/routers/simulate.py` | ~700 linhas → casca fina (valida, chama `calcular_simulacao_completa`, audit log, responde) |
| `api/schemas_query.py` | `PayloadConsulta` perde `valor_base`, ganha `itens`/`regime_apuracao`/`comprador_tipo`; `RespostaConsulta` compõe `resultado_simulacao: RespostaSimulacao` |
| `api/routers/query.py` | `valor_base` derivado da soma dos itens; captura `SkuNaoResolvidoError`; monta `RespostaConsulta` com `resultado_simulacao` |
| `orquestracao/dependencias.py` | `DependenciasOrquestracao` ganha `db_pool`; `criar_dependencias_reais`/`criar_dependencias_fake` atualizados |
| `orquestracao/estado.py` | `State` ganha `itens`/`regime_apuracao`/`comprador_tipo`/`tenant_id`; `resultado_calculo` → `resultado_simulacao: RespostaSimulacao` |
| `orquestracao/nos/deterministico.py` | Reescrito — chama `calcular_simulacao_completa()`, assinatura ganha `deps` |
| `orquestracao/nos/sintetizador.py` | Guardrail reescrito para verificar totais AGREGADOS (bounded), nunca por item (Decision 5) |
| `orquestracao/executor.py` | `no_deterministico(state, deps)` — passa `deps` |
| `frontend/lib/types.ts` | `RegimeVigenteResumo`/`ItemRegimeVigente` novos; `RespostaSimulacao`/`PayloadConsulta`/`RespostaConsulta` redesenhados |
| `frontend/components/ResultadoSimulacao.tsx` | Renderiza `<ComparativoRegime />` |
| `frontend/components/ParecerMarkdown.tsx` | Renderiza `<ComparativoRegime resposta={resposta.resultado_simulacao} />` |
| `frontend/components/SimuladorForm.tsx` | Seletor de `natureza` por item + `regime_apuracao` por operação |
| `frontend/components/ConsultaForm.tsx` | Itemizado (mesmo padrão de `SimuladorForm`), `natureza`/`regime_apuracao` |
| `tests/test_api_simulate.py` | Sem alteração de conteúdo — só serviu de prova de não-regressão (AT-007) |
| `tests/test_nos.py` | Itens reais nos testes de `deterministico`/`sintetizador`; guardrail com ICMS interno |
| `tests/test_grafo_integration.py` | Itens reais nos 4 ATs; `resultado_simulacao` no lugar de `resultado_calculo` |
| `tests/test_api_query.py` | Payload itemizado; novo teste AT-003/AT-008 de paridade `/simulador` x `/consulta` |
| `tests/test_api_query_llm_real.py` | Payload itemizado; corrigido bug pré-existente não relacionado (`_ClienteQueEmpaca.gerar` sem `no_origem`) |
| `frontend/app/simulador/page.test.tsx` | Mocks com `regime_vigente`/`itens_regime_vigente`/`fonte_legal_fase`; `getAllByText` onde `ComparativoRegime` duplica conteúdo |
| `frontend/app/consulta/page.test.tsx` | Mock de `RespostaConsulta` com `resultado_simulacao` aninhado |

---

## Verification Results

### Lint Check

```text
ruff check .           -> All checks passed!
npx eslint .            -> (sem saída — limpo)
```

**Status:** ✅ Pass

### Type Check

```text
npx tsc --noEmit
  app/api/api-key/route.test.ts(21,32): error TS2345  <- pré-existente, não relacionado
  lib/api-client.test.ts(62,12): error TS18046         <- pré-existente, não relacionado
  lib/api-client.test.ts(63,12): error TS18046         <- pré-existente, não relacionado
```

Confirmado pré-existente via `git stash` antes do build (os 3 mesmos erros já apareciam sem nenhuma mudança desta feature). Zero erro novo introduzido.

**Status:** ✅ Pass (com 3 erros pré-existentes documentados, fora do escopo)

### Tests — Backend

```text
664 passed, 9 skipped, 1 warning in ~6s
```

9 skipped = testes que exigem `DATABASE_URL` (schema/RLS), mesmo padrão de sempre — rodam de verdade no CI.

**Status:** ✅ 664/664 Pass

### Tests — Frontend

```text
Test Files  8 passed (8)
     Tests  39 passed (39)
```

**Status:** ✅ 39/39 Pass

### Build de produção (frontend)

```text
✓ Compiled successfully
✓ Generating static pages (9/9)
```

**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Guardrail do sintetizador checando `Decimal("0")` como substring — trivialmente presente em quase qualquer texto numérico, não protegendo contra nada | Guardrail passa a pular campos agregados iguais a zero, além de `None` — só valores reais/distinguíveis entram na verificação | +5m |
| 2 | `ComparativoRegime` duplica conteúdo (valor líquido, SKU, fundamentação) que já aparecia nos cards existentes de `ResultadoSimulacao`/`ParecerMarkdown`, quebrando `getByText` (múltiplos matches) nos testes existentes | 3 asserções trocadas para `getAllByText`/`.length` em vez de `getByText` único | +5m |
| 3 | Teste de paridade `/simulador` x `/consulta` (AT-003/AT-008) inicialmente usava um fake parecer ESTÁTICO (válido só para o payload de 1000,00 padrão do arquivo) — para um payload diferente, o guardrail rejeitava (503) e a asserção de paridade nunca executava de verdade, um teste que passava sem testar nada | Reescrito para construir o fake do Sonnet DINAMICAMENTE a partir dos números reais devolvidos por `/v1/tax/simulate`, garantindo que a asserção de paridade sempre execute | +10m |
| 4 | `_ClienteQueEmpaca.gerar()` em `tests/test_api_query_llm_real.py` não aceitava `no_origem` — 1 teste pré-existente falhando, sem relação com esta feature (achado ao rodar a suíte antes de qualquer mudança, para estabelecer baseline) | Corrigido oportunisticamente (assinatura ganhou `no_origem: str = "desconhecido"`) já que o arquivo estava sendo reescrito de qualquer forma | +2m |
| 5 | `google.auth` não instalado no sandbox, bloqueando toda a suíte de testes baseada em `TestClient` (import chain via `api.tasks_cloud`) | `pip install --target=` num diretório de scratchpad, mesmo padrão já documentado no CLAUDE.md para outras dependências não instaláveis via pip normal neste ambiente | +3m |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Nenhuma | O DESIGN foi seguido à risca — inclusive a investigação prévia da Assumption A-004 antes de escrever qualquer arquivo, como o próprio DESIGN determinou | — |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Comparação aparece no `/simulador` (happy path) | ✅ Pass | `frontend/app/simulador/page.test.tsx` — mock com `regime_vigente` real, `ComparativoRegime` renderiza os totais |
| AT-002 | Tributo não calculado é declarado, nunca omitido | ✅ Pass | `frontend/components/ComparativoRegime.test.tsx::declara tributo não calculado explicitamente`; `tests/test_simulacao.py::test_regime_vigente_pis_cofins_so_calculado_com_regime_apuracao` |
| AT-003 | `/consulta` itemizado calcula com paridade total | ✅ Pass | `tests/test_api_query.py::test_at003_at008_paridade_numerica_com_simulador_para_o_mesmo_payload` — compara byte a byte `resumo_financeiro`/`regime_vigente`/`fonte_legal_fase` dos dois endpoints |
| AT-004 | `valor_base` derivado corretamente | ✅ Pass | `tests/test_api_query.py::test_at004_valor_base_e_derivado_da_soma_dos_itens` |
| AT-005 | Sem regressão em `ano_operacao >= 2027` | ✅ Pass | `tests/test_api_simulate.py` (existente, sem mudança) + `tests/test_at003_ano_sem_aliquota_confirmada_retorna_422_nao_parecer_inventado` em `test_api_query.py` |
| AT-006 | Item de serviço aciona ISS, não ICMS | ✅ Pass | `tests/test_simulacao.py::test_regime_vigente_servico_aciona_iss_nunca_icms` |
| AT-007 | Extração da função compartilhada não muda resposta do `/simulador` | ✅ Pass | `tests/test_api_simulate.py` (7 testes pré-existentes, zero linha alterada) passa 100% depois da extração — mesma suíte, mesmo resultado |
| AT-008 | Comprador com condição especial funciona igual nos dois endpoints | ✅ Pass | Coberto pelo mesmo teste de paridade do AT-003 (a função compartilhada garante isso por construção — `comprador_tipo` é parâmetro do MESMO `calcular_simulacao_completa()`) |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] All tasks from manifest completed (24/24)
- [x] All verification checks pass (ruff, eslint, tsc — 3 erros pré-existentes documentados)
- [x] All tests pass (664 backend + 39 frontend)
- [x] No blocking issues
- [x] Acceptance tests verified (8/8)
- [x] Ready for /ship

---

## Next Step

`/ship .claude/sdd/features/DEFINE_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md`
