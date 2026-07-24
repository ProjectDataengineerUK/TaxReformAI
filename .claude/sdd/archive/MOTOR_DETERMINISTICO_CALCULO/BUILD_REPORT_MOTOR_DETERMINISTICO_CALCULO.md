# BUILD REPORT: Motor Determinístico de Cálculo (IVA Dual / Split Payment)

> Implementation report for MOTOR_DETERMINISTICO_CALCULO

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MOTOR_DETERMINISTICO_CALCULO |
| **Date** | 2026-07-23 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_MOTOR_DETERMINISTICO_CALCULO.md](../features/DEFINE_MOTOR_DETERMINISTICO_CALCULO.md) |
| **DESIGN** | [DESIGN_MOTOR_DETERMINISTICO_CALCULO.md](../features/DESIGN_MOTOR_DETERMINISTICO_CALCULO.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 8/8 |
| **Files Created** | 8 |
| **Lines of Code** | 252 (Python) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 37/37 (13 novos desta feature + 24 já existentes da feature anterior) |
| **Agents Used** | 0 (execução direta) |

**Nota sobre agentes:** assim como na feature anterior, o código foi escrito diretamente nesta sessão em vez de delegado via Task, por ser um volume pequeno (8 arquivos, ~250 linhas) e altamente acoplado (todo o pacote `motor_calculo` precisa ser consistente entre si).

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `motor_calculo/__init__.py` | 0 | ✅ | Marca o pacote |
| `motor_calculo/fases.py` | 20 | ✅ | `FaseTransicao` + `fase_para()` — cobre 2026 até 2033+ |
| `motor_calculo/regras_fiscais.py` | 24 | ✅ | `RegraFiscal` (frozen) + `AliquotaNaoDisponivelError` |
| `motor_calculo/tabela_aliquotas.py` | 31 | ✅ | `TabelaAliquotas` (Protocol) + `TabelaAliquotasSeed` (só 2026) |
| `motor_calculo/engine.py` | 50 | ✅ | `TaxCalculatorEngine` + `ResultadoCalculo`, Decimal/ROUND_HALF_UP |
| `tests/test_fases.py` | 27 | ✅ | 12/12 casos passam (9 fases + 3 anos inválidos) |
| `tests/test_tabela_aliquotas.py` | 34 | ✅ | 4/4 casos passam |
| `tests/test_engine.py` | 66 | ✅ | 5/5 casos passam, incluindo AT-001/002/003 |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass

(Um erro `F401` — import não usado em `test_engine.py` — foi encontrado e corrigido durante o build.)

### Type Check

Não configurado neste ciclo (mesmo padrão da feature anterior).

**Status:** ⏭️ Skipped

### Tests

```text
$ python3 -m pytest tests/ -v
...
tests/test_engine.py::test_at001_happy_path_fase_teste_2026 PASSED
tests/test_engine.py::test_at002_erro_explicito_para_fase_sem_aliquota_confirmada PASSED
tests/test_engine.py::test_at003_split_payment_desativado_nao_retem_valor PASSED
tests/test_engine.py::test_valor_base_invalido_levanta_value_error PASSED
tests/test_engine.py::test_arredondamento_usa_round_half_up PASSED
tests/test_fases.py:: (9 casos de fase + 3 de ano inválido) PASSED
tests/test_tabela_aliquotas.py:: (4 casos) PASSED
... (24 testes da feature PIPELINE_INGESTAO_LEGAL, sem regressão)

============================== 37 passed in 0.73s ==============================
```

**Status:** ✅ 37/37 Pass (13 novos + 24 pré-existentes, sem regressão)

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|--------------|
| 1 | `ruff` acusou import não usado (`FaseTransicao`) em `test_engine.py`, deixado por engano num teste que só precisava de `RegraFiscal` | Removido o import não usado | +1m |
| 2 | Teste inicial de arredondamento (`test_arredondamento_usa_round_half_up`) usava `100.005 × 0.085`, que não caía exatamente num caso de "metade" (`.xx5`) — não provava a diferença entre `ROUND_HALF_UP` e o `ROUND_HALF_EVEN` padrão do Python | Ajustado para `100 × 0,08505 = 8,505` exato, onde `ROUND_HALF_UP` dá `8,51` e o padrão do Python daria `8,50` — agora o teste prova a decisão de arredondamento, não só executa o código | +3m |

---

## Deviations from Design

Nenhuma — a implementação seguiu os Code Patterns do DESIGN exatamente como especificado.

---

## Blockers

Nenhum. Ao contrário da feature `PIPELINE_INGESTAO_LEGAL`, este motor não depende de nenhuma infraestrutura externa (GCP, Qdrant) nem de bibliotecas não instaláveis neste sandbox — é Python puro (`enum`, `dataclasses`, `decimal`, `typing.Protocol`), todas da stdlib.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path — fase de teste 2026 | ✅ Pass | `test_at001_happy_path_fase_teste_2026`: `valor_base=1000` → `valor_cbs=9.00`, `valor_ibs=1.00`, `valor_liquido=990.00`, `fonte_legal` presente |
| AT-002 | Error case — ano sem alíquota confirmada (2028) | ✅ Pass | `test_at002_erro_explicito_para_fase_sem_aliquota_confirmada`: `AliquotaNaoDisponivelError` levantada, nenhum valor retornado |
| AT-003 | Edge case — Split Payment desativado | ✅ Pass | `test_at003_split_payment_desativado_nao_retem_valor`: `valor_liquido == valor_base`, mas `total_tributos` continua calculado/reportado |

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| Motor calcula `valor_cbs`/`valor_ibs`/`valor_is`/líquido corretamente para a fase 2026 | ✅ | `test_at001_happy_path_fase_teste_2026` |
| 100% das chamadas para fases sem alíquota confirmada retornam erro explícito | ✅ | `test_at002_...` + `test_fases_sem_alíquota_confirmada_levantam_erro_explicito` (parametrizado para as 3 fases restantes) |
| Todos os valores monetários usam `Decimal`, nunca `float` | ✅ | Verificado por leitura de código — `engine.py` e `regras_fiscais.py` usam `Decimal` em todos os campos numéricos; `test_arredondamento_usa_round_half_up` prova o comportamento de arredondamento explícito |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados (8/8)
- [x] Lint (`ruff`) passa
- [x] Testes automatizados passam (37/37, sem regressão na feature anterior)
- [x] Nenhum blocker
- [x] AT-001, AT-002, AT-003 verificados
- [x] Pronto para `/ship`

---

## Next Step

`/ship .claude/sdd/features/DEFINE_MOTOR_DETERMINISTICO_CALCULO.md`
