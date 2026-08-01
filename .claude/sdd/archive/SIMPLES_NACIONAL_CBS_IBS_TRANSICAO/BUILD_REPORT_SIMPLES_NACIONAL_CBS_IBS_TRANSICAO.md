# BUILD REPORT: Integração de CBS/IBS à Partilha do Simples Nacional

> Implementation report for SIMPLES_NACIONAL_CBS_IBS_TRANSICAO (posição 17/17 do roadmap, última
> da "segunda leva")

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMPLES_NACIONAL_CBS_IBS_TRANSICAO |
| **Date** | 2026-08-01 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md](../features/DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md) |
| **DESIGN** | [DESIGN_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md](../features/DESIGN_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md) |
| **Status** | Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 5/5 (manifesto completo do DESIGN) |
| **Files Created** | 4 novos + 1 modificado |
| **Tests Passing** | 551/551 (+32 novos desta feature: 19 unit + 13 E2E), 5 skipped (sem `DATABASE_URL`, esperado) |
| **Lint** | `ruff check .` — limpo |
| **Desvios do DESIGN** | Nenhum — o `/design` já tinha absorvido o achado arquitetural principal (endpoint dedicado) antes do `/build` começar |
| **Infraestrutura tocada** | Nenhuma — segunda feature do projeto (depois do Anexo XVI) inteiramente Python puro |

---

## Task Execution

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `motor_calculo/simples_nacional.py` | ✅ Complete | 6 Anexos completos (faixas + partilha por ano até 2033 permanente), fórmula do art. 18, teto de ISS com coeficientes por ano, MEI — todos os números transcritos diretamente do PDF já verificado no `/define`/`/design` |
| 2 | `api/schemas_simples_nacional.py` | ✅ Complete | `PayloadSimplesNacional`/`RespostaSimplesNacional`/`ItemPartilhaSimplesNacional` |
| 3 | `api/routers/simulate.py` — novo endpoint | ✅ Complete | `POST /v1/tax/simulate-simples-nacional`, mesmo router, zero linha alterada no endpoint `/v1/tax/simulate` existente |
| 4 | `tests/test_simples_nacional.py` | ✅ Complete | 19 testes unitários, todos passando de primeira |
| 5 | `tests/test_api_simulate_simples_nacional.py` | ✅ Complete | 13 testes E2E (AT-001 a AT-012 do DEFINE + 1 extra), todos passando de primeira |

---

## Verificação de Fonte Primária Realizada no `/define`/`/design` (reafirmada aqui)

Nenhuma verificação de fonte primária NOVA foi necessária durante o `/build` — os 6 Anexos
(faixas, partilha por ano, fórmula do art. 18, coeficientes de teto de ISS) já tinham sido
transcritos e cross-checados no `/define`/`/design`, e a transcrição do módulo Python usou
diretamente os números já verificados (copiados dos blocos de dados do `/design`, não
re-derivados). Uma única verificação AD-HOC aconteceu durante o `/build`: a fórmula do art. 18
foi testada contra o texto legal citado no docstring da própria função
(`calcular_aliquota_efetiva`), confirmando que o código reproduz exatamente `(RBT12 x Aliq - PD)
/ RBT12`.

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `motor_calculo/simples_nacional.py` | 520 | ✅ | Maior módulo Python puro do projeto — 6 Anexos × até 6 faixas × até 7 pontos no tempo; testado contra 8 dos 12 acceptance tests do DEFINE isoladamente antes do wiring |
| `api/schemas_simples_nacional.py` | 58 | ✅ | Payload/resposta dedicados, sem nenhum campo herdado de `schemas_simulate.py` |
| `tests/test_simples_nacional.py` | 197 | ✅ | 19/19 passando — cobre os 6 Anexos, a fórmula do art. 18 isoladamente, teto de ISS (com/sem gatilho, 2 Anexos), MEI (incl. 2033+), 6ª Faixa, regime permanente (2033==2050), e os 2 erros de validação (RBT12 acima do teto; RBT12 ausente fora do MEI) |
| `tests/test_api_simulate_simples_nacional.py` | 210 | ✅ | 13/13 passando — E2E via `TestClient`, sem pool fake (endpoint não consulta banco; `db_pool=None` exercita o caminho gracioso já existente de `api/audit.py`) |

## Files Modified

| File | Change | Verified |
|------|--------|----------|
| `api/routers/simulate.py` | +3 imports, +1 endpoint (`simular_simples_nacional`) — zero linha do endpoint `/v1/tax/simulate` existente tocada | ✅ |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass (2 rodadas: RUF002 em `motor_calculo/simples_nacional.py` por caracteres
Unicode `×`/`−` em docstrings, corrigido para ASCII `x`/`-`; FURB157 em
`tests/test_simples_nacional.py`, corrigido via `ruff check --fix`)

### Tests

```text
$ python3 -m pytest tests/ -q
551 passed, 5 skipped, 1 warning in 6.59s
```

**Status:** ✅ 551/551 Pass (32 novos desta feature: 19 em `test_simples_nacional.py`, 13 em
`test_api_simulate_simples_nacional.py`)

### Sanidade manual adicional (além dos testes automatizados)

Rodadas ad-hoc via `python3 -c` antes de escrever os testes formais, confirmando os 6 Anexos, a
fórmula do art. 18, o teto de ISS (Anexos XX/XXI, com e sem gatilho), o MEI (2027-2028 e 2033+),
a 6ª Faixa e a equivalência 2033==2050 — todas bateram com os números do `/design` na primeira
tentativa.

---

## Issues Encontrados Durante o Build

Nenhum achado arquitetural novo — o `/design` já tinha absorvido a mudança estrutural principal
(endpoint dedicado, em vez de campos novos em `/v1/tax/simulate`, ver Decisão 1 do DESIGN) antes
do `/build` começar. Dois ajustes de lint mecânicos (caracteres Unicode em docstring; formatação
verbosa de `Decimal`), sem impacto em lógica.

---

## Deviations from Design

Nenhum.

---

## Blockers

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path — Comércio, 1ª Faixa, 2027 | ✅ Pass | `test_at001_*` (2 arquivos) |
| AT-002 | Indústria com IPI, 2033+ (regime permanente) | ✅ Pass | `test_at002_*` (2 arquivos) |
| AT-003 | Serviço Anexo IV (XXI) sem CPP | ✅ Pass | `test_at003_*`/`test_nunca_tem_cpp` (todos os 6 anos testados) |
| AT-004 | Teto de ISS acionado | ✅ Pass | `test_at004_*`/`test_teto_iss_acionado` (2 Anexos, coeficientes exatos verificados) |
| AT-005 | Teto de ISS NÃO acionado | ✅ Pass | `test_at005_*`/`test_teto_iss_nao_acionado` |
| AT-006 | MEI — valor fixo | ✅ Pass | `test_at006_*` |
| AT-007 | MEI 2033+ sem ICMS/ISS | ✅ Pass | `test_at007_*` |
| AT-008 | 6ª Faixa sem ICMS/ISS/IBS | ✅ Pass | `test_at008_*`/`test_sexta_faixa_icms_iss_fora_do_das` — `icms_iss_fora_do_das=True` |
| AT-009 | `/v1/tax/simulate` (regime geral) inalterado | ✅ Pass | `test_at009_*` — endpoint existente sem campos novos |
| AT-010 | RBT12 ausente fora do MEI | ✅ Pass | `test_at010_*`/`test_rbt12_obrigatoria_fora_do_mei` — 422/`ValueError` |
| AT-011 | Ano fora da janela (< 2027) | ✅ Pass | `test_at011_*` — 422 |
| AT-012 | Zero regressão | ✅ Pass | 551/551 testes, incluindo os 519 já existentes |

**12/12 Acceptance Tests do DEFINE verificados.**

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] Todos os 5 arquivos do manifesto criados/modificados
- [x] `ruff check .` limpo
- [x] 551/551 testes passando (5 skip esperados)
- [x] Zero regressão em qualquer feature anterior
- [x] 12/12 Acceptance Tests do DEFINE verificados
- [x] `motor_calculo/engine.py`/`tabela_aliquotas.py` confirmadamente intocados
- [x] `/v1/tax/simulate` (endpoint existente) confirmadamente sem nenhuma linha alterada
- [x] Nenhuma superfície de infraestrutura nova (sem migração, sem `GRANT`, sem workflow modificado)

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`
