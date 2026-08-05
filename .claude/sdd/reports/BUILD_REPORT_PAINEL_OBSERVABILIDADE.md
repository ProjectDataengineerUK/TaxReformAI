# BUILD REPORT: PAINEL_OBSERVABILIDADE

> Relatório de implementação do painel de observabilidade

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PAINEL_OBSERVABILIDADE |
| **Date** | 2026-08-05 |
| **Author** | build-agent (sessão interativa) |
| **DEFINE** | [DEFINE_PAINEL_OBSERVABILIDADE.md](../features/DEFINE_PAINEL_OBSERVABILIDADE.md) |
| **DESIGN** | [DESIGN_PAINEL_OBSERVABILIDADE.md](../features/DESIGN_PAINEL_OBSERVABILIDADE.md) |
| **Status** | Complete (bloqueios documentados abaixo, mesma disciplina de toda feature de infraestrutura real deste projeto) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 9/9 |
| **Files Created** | 20 |
| **Files Modified** | 17 |
| **Lines of Code** | ~1.900 (novos) |
| **Tests Passing** | 494/494 backend (10 skipped, mesma limitação pré-existente de sandbox) + 34/34 frontend |
| **Agents Used** | 0 — construído diretamente nesta sessão, sem sub-agentes |

---

## Task Execution

| # | Task | Status | Notas |
|---|------|--------|-------|
| 1 | Migrações 016-019 | ✅ Complete | `uso_llm`, `custo_infra_diario`, `observabilidade_execucoes`, `pg_read_all_stats` |
| 2 | Pacote `observabilidade/` | ✅ Complete | `status.py` (7 regras), `custo.py`, `scorecard.yaml`, `execucoes.py` (não previsto no DESIGN, ver Deviations) |
| 3 | Instrumentação de uso de LLM | ✅ Complete | `registrador.py`, `cliente.py` (+`no_origem`), `dependencias.py`, 3 nós |
| 4 | Router da API | ✅ Complete | 3 endpoints + `api/schemas_observabilidade.py` (não previsto no DESIGN, ver Deviations) |
| 5 | Sync de custo de infra | ✅ Complete | Script + workflow + heartbeat no sync do BigQuery |
| 6 | Terraform | ✅ Complete | SA `taxreformai-cost-sync`, validado com `terraform validate` |
| 7 | Frontend `/painel` | ✅ Complete | 5 abas + link na navegação (não listado explicitamente no DESIGN) |
| 8 | Testes | ✅ Complete | 31 testes novos no backend, 8 no frontend |
| 9 | Validação final | ✅ Complete | ruff, pytest, vitest, `npm run build`, `terraform validate` — todos verdes |

---

## Files Created

| File | Linhas | Verificado | Notas |
|------|--------|------------|-------|
| `db/migrations/016_observabilidade_uso_llm.sql` | 25 | ✅ sintaxe | Sem tenant_id/RLS (Decision 3) |
| `db/migrations/017_observabilidade_custo_infra.sql` | 19 | ✅ sintaxe | `UNIQUE(servico,data)` para upsert |
| `db/migrations/018_observabilidade_execucoes.sql` | 18 | ✅ sintaxe | Heartbeat |
| `db/migrations/019_pg_read_all_stats.sql` | 16 | ✅ sintaxe | `GRANT` de papel predefinido, não atributo de superusuário |
| `observabilidade/__init__.py` | 0 | ✅ | — |
| `observabilidade/status.py` | 182 | ✅ testado (18 testes) | 7 regras, zero IAM novo |
| `observabilidade/custo.py` | 128 | ✅ testado (7 testes) | Agregação + limiares FinOps |
| `observabilidade/execucoes.py` | 12 | ✅ | Não estava no manifesto do DESIGN — extraído para evitar duplicar SQL entre os 2 scripts de sync |
| `observabilidade/scorecard.yaml` | 68 | ✅ parse | Notas reais, com justificativa e framework citado |
| `orquestracao/llm/registrador.py` | 76 | ✅ testado (6 testes) | Best-effort, AT-004 |
| `api/schemas_observabilidade.py` | 38 | ✅ | Não estava no manifesto — natural dado o padrão `schemas_*.py` já usado no projeto |
| `api/routers/observabilidade.py` | 124 | ✅ importa e monta | 3 endpoints |
| `scripts/sincronizar_custo_infra.py` | 138 | ✅ sintaxe | Testável de verdade só via workflow (BigQuery real) |
| `.github/workflows/sincronizar_custo_infra.yml` | 62 | ✅ YAML válido | Espelha `sincronizar_bigquery.yml` |
| `frontend/app/painel/page.tsx` | 60 | ✅ build | Shell com 5 abas |
| `frontend/app/painel/status-shared.ts` | 32 | ✅ | Hook + mapas de cor compartilhados |
| `frontend/app/painel/scorecard-shared.ts` | 19 | ✅ | Hook do scorecard |
| `frontend/app/painel/DiagramaTab.tsx` | 108 | ✅ testado | SVG dinâmico, cor por status ao vivo |
| `frontend/app/painel/SentinelaTab.tsx` | 48 | ✅ testado | Tabela |
| `frontend/app/painel/MaturidadeTab.tsx` | 32 | ✅ testado | 3 cards |
| `frontend/app/painel/SegurancaTab.tsx` | 32 | ✅ testado | Nota composta + por função |
| `frontend/app/painel/CustoFinOpsTab.tsx` | 90 | ✅ testado | Custo + achados |
| `frontend/app/painel/painel.test.tsx` | 122 | ✅ 6/6 | Achou e corrigiu 1 bug real (ver Issues) |
| `tests/test_observabilidade_status.py` | 195 | ✅ 18/18 | |
| `tests/test_observabilidade_custo.py` | 92 | ✅ 7/7 | |
| `tests/test_registrador_uso_llm.py` | 100 | ✅ 6/6 | |

---

## Files Modified

| File | Mudança |
|------|---------|
| `orquestracao/llm/cliente.py` | `gerar()` ganha `no_origem`; ambos clientes reais gravam uso nos 2 caminhos |
| `orquestracao/dependencias.py` | `criar_dependencias_reais` recebe `db_pool`, injeta o registrador |
| `orquestracao/nos/classificador.py`, `extrator_regras.py`, `sintetizador.py` | Passam `no_origem` |
| `api/dependencias_orquestracao.py` | Passa `get_db_pool()` para `criar_dependencias_reais` |
| `api/main.py` | Registra o router novo |
| `api/Dockerfile` | `COPY observabilidade/` |
| `requirements-api.txt` | `httpx`, `PyYAML` |
| `scripts/sincronizar_bigquery.py` | Grava heartbeat (sucesso e falha) |
| `infra/terraform/main.tf`, `variables.tf` | SA `taxreformai-cost-sync` + `data source` do dataset de billing export |
| `frontend/lib/api-client.ts` | `apiGet` novo (endpoints de observabilidade são GET) |
| `frontend/lib/types.ts` | Tipos das 3 respostas novas |
| `frontend/app/layout.tsx` | Link "Observabilidade" na navegação |
| `tests/test_nos.py` | 3 asserções novas confirmando `no_origem` correto por nó |
| `frontend/lib/api-client.test.ts` | 2 testes novos para `apiGet` |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```
**Status:** ✅ Pass

### Terraform

```text
$ terraform fmt -check -diff   # sem saída
$ terraform validate
Success! The configuration is valid.
```
**Status:** ✅ Pass — confirma também que **nenhuma role nova foi adicionada a `taxreformai-runtime`** (Decision 1)

### Tests (backend)

```text
$ python3 -m pytest tests/ -q [ignorando os 13 módulos que já falham na coleção por
  google.auth ausente no sandbox local — limitação pré-existente, confirmada
  idêntica antes desta feature]
494 passed, 10 skipped in 7.04s
```
**Status:** ✅ 494/494 Pass

### Tests (frontend)

```text
$ npx vitest run
Test Files  7 passed (7)
     Tests  34 passed (34)
```
**Status:** ✅ 34/34 Pass

### Build (frontend)

```text
$ npm run build
✓ Compiled successfully
├ ƒ /painel    9.78 kB   108 kB
```
**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `BLE001` (blind except) disparava em `except Exception as exc:` mas não em `except Exception:` puro — inconsistência aparente do ruff | Investigado: o padrão já usado em `api/audit.py`/`api/ipi.py` não captura a variável e usa `logger.exception`; ajustado `observabilidade/status.py` para capturar `httpx.HTTPError` (mais específico, correto de qualquer forma) e os 2 scripts de sync para usar `logging.exception` em vez de `print` | +5min |
| 2 | `DTZ011`/`UP017` (uso de `date.today()`/`timezone.utc` em vez das formas modernas) | Convertido para `datetime.now(UTC).date()` / `datetime.now(UTC)` | +2min |
| 3 | **Achado real de teste**: `painel.test.tsx` quebrava com `TypeError: Cannot read properties of undefined (reading 'find')` no `DiagramaTab` ao testar as abas Maturidade/Segurança | Causa real: a aba Diagrama (inicial) sempre dispara `/status` antes do clique de troca de aba — um mock de `apiGet` que devolve o scorecard para QUALQUER path quebra o `DiagramaTab` ainda montado. Corrigido roteando o mock por `path` nos testes afetados | +8min |
| 4 | Ambiguidade de teste: duas notas "3/5" no fixture de scorecard tornavam `getByText("3/5")` ambíguo | Corrigido variando as notas do fixture (2/3/4), não o componente | +2min |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `observabilidade/execucoes.py` (novo, não estava no manifesto) | O heartbeat (`registrar_execucao`) é usado por 2 scripts (`sincronizar_bigquery.py` e `sincronizar_custo_infra.py`) — extraído para não duplicar o SQL | Nenhum, é uma extração natural |
| `api/schemas_observabilidade.py` (novo, não estava no manifesto) | Todo outro router do projeto separa schemas Pydantic num arquivo próprio (`schemas_simulate.py`, `schemas_query.py` etc.) — seguido o padrão já estabelecido em vez de inline no router | Nenhum, consistência com o resto do código |
| Link "Observabilidade" em `frontend/app/layout.tsx` (não estava no manifesto) | Sem isto, `/painel` existiria mas seria inalcançável pela navegação normal | Nenhum, correção de um gap óbvio do manifesto |
| `frontend/app/painel/status-shared.ts` e `scorecard-shared.ts` (não estavam no manifesto, que listava só os 5 arquivos de aba + page.tsx) | Múltiplas abas precisam do mesmo `useQuery`/mapa de cores — hooks compartilhados evitam duplicar a chamada e a paleta verde/amarelo/vermelho em 3 arquivos | Nenhum |
| Um único `painel.test.tsx` cobrindo as 5 abas, em vez de `*.test.tsx` por aba (item 33 do manifesto) | As 5 abas compartilham o mesmo shell (`page.tsx`) e a troca de aba é o comportamento mais importante de testar em conjunto — arquivos separados duplicariam o setup (`QueryClientProvider`+`ApiKeyProvider`+seed de `localStorage`) sem ganho real de isolamento | Nenhum — mesma cobertura, menos duplicação |

---

## Blockers (documentados, não bloqueiam o /ship — mesma disciplina de `LLM_REAL_VERTEX_AI`/`FRONTEND_PREMIUM_GOOGLE_AUTH`)

| Blocker | Ação necessária | Owner |
|---------|-------------------|-------|
| Custo de infra fica vazio até o Billing Export existir | Usuário precisa habilitar "Cloud Billing export to BigQuery" no Console GCP, criando o dataset (`billing_export` por padrão) | Usuário |
| `taxreformai-cost-sync` (SA nova) não tem credencial cadastrada | Depois de `terraform apply`, usuário precisa gerar a chave da SA e cadastrar como `GCP_COST_SYNC_SA_KEY` no GitHub — nunca o agente, mesma disciplina de toda credencial já estabelecida (inclusive sob insistência direta em `BIGQUERY_DATA_WAREHOUSE`) | Usuário |
| `taxreformai_app` precisa da migração 019 aplicada (`pg_read_all_stats`) antes do status de Cloud SQL funcionar corretamente | Rodar `migrar_banco.yml` | Deploy real |
| `terraform apply` do bloco de `taxreformai-cost-sync` só funciona DEPOIS do dataset de billing export existir (é um `data` source, não `resource`) | Ordem: habilitar export no Console → `terraform apply` → cadastrar `GCP_COST_SYNC_SA_KEY` → disparar `sincronizar_custo_infra.yml` | Usuário + deploy real |
| Verificação end-to-end contra infraestrutura real pendente (mesma classe de toda feature deste projeto: `/build` prova localmente o que dá para provar sem infra; a prova final é `migrar_banco.yml`/`deploy.yml` reais) | Rodar as migrações, redeployar a API (novo router + `observabilidade/` na imagem) e o frontend (`/painel` novo), depois testar o painel de verdade logado | Próximo deploy |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Diagrama/Sentinela carrega em <5s, cache 60s | ✅ Pass (unit) | `test_observabilidade_status.py` cobre as 7 regras; cache testado por inspeção de código (`_cache_status`); tempo real de carregamento só verificável em produção |
| AT-002 | 100% das chamadas reais geram linha em `uso_llm` | ✅ Pass (unit) | `cliente.py` grava nos 2 caminhos (sucesso/erro) antes de retornar/relançar — `test_nos.py` confirma `no_origem` correto por nó |
| AT-003 | Sync de custo de infra idempotente | ⏳ Pendente de infra real | `ON CONFLICT DO UPDATE` é upsert nativo do Postgres, testável de verdade só contra Cloud SQL real |
| AT-004 | Gravação de uso nunca bloqueia a resposta | ✅ Pass | `test_registrador_uso_llm.py`: `test_conexao_indisponivel_nao_propaga`, `test_erro_dentro_do_cursor_tambem_nao_propaga` |
| AT-005 | Acesso negado fora da allowlist | ✅ Pass (por construção) | `frontend/middleware.ts` já protege `/((?!api/auth\|login\|_next/static\|_next/image\|favicon.ico\|$).*)`  — `/painel` cai automaticamente nessa proteção, sem mudança necessária |
| AT-006 | Scorecard nunca "calculado" | ✅ Pass | `consultar_scorecard` só lê `scorecard.yaml`, `functools.lru_cache` — nenhuma lógica de cálculo no caminho |
| AT-007 | Sync de custo de infra idempotente (upsert) | ⏳ Pendente de infra real | Mesma nota do AT-003 |

---

## Final Status

### Overall: ✅ COMPLETE (bloqueios de infraestrutura real documentados, mesma disciplina já aplicada a `LLM_REAL_VERTEX_AI`, `FRONTEND_PREMIUM_GOOGLE_AUTH`, `BIGQUERY_DATA_WAREHOUSE`)

**Completion Checklist:**

- [x] Todos os arquivos do manifesto criados (mais 5 adições justificadas, ver Deviations)
- [x] Todas as verificações passam (ruff, terraform validate)
- [x] Todos os testes passam (494 backend + 34 frontend)
- [x] Sem bloqueios de código — só de infraestrutura real (Billing Export manual, credencial da SA nova, migração 019)
- [x] Acceptance tests verificados no nível possível sem infra real (5/7 diretos, 2/7 pendentes de deploy real)
- [ ] Pronto para `/ship` — recomendado após o próximo deploy real confirmar o painel funcionando ponta a ponta

---

## Next Step

**Pendências antes do deploy real:**
1. Usuário habilita Billing Export → BigQuery no Console GCP
2. `terraform apply` (cria `taxreformai-cost-sync` + a IAM binding no dataset)
3. Usuário gera e cadastra `GCP_COST_SYNC_SA_KEY` no GitHub
4. `migrar_banco.yml` (aplica as migrações 016-019)
5. `deploy.yml` target=both (API com o router novo + `observabilidade/` na imagem; frontend com `/painel`)
6. `sincronizar_custo_infra.yml` (primeira execução manual)

**Depois disso:** `/ship .claude/sdd/features/DEFINE_PAINEL_OBSERVABILIDADE.md`
