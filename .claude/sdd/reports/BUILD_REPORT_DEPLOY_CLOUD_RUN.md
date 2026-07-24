# BUILD REPORT: Deploy Contínuo para Cloud Run

> Relatório de implementação do CD para Cloud Run (API FastAPI + frontend Next.js)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEPLOY_CLOUD_RUN |
| **Date** | 2026-07-24 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_DEPLOY_CLOUD_RUN.md](../features/DEFINE_DEPLOY_CLOUD_RUN.md) |
| **DESIGN** | [DESIGN_DEPLOY_CLOUD_RUN.md](../features/DESIGN_DEPLOY_CLOUD_RUN.md) |
| **Status** | Complete (código) — runbook de operador pendente |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 13/13 |
| **Files Created** | 6 novos, 7 modificados |
| **Lines of Code** | 342 novas (workflow + Dockerfiles + requirements) |
| **Tests Passing** | 73/73 pytest + 12/12 vitest |
| **Agents Used** | 0 (build direto — ver nota) |

> **Nota sobre agentes:** o DESIGN sugeria delegar a especialistas (@ci-cd-specialist, @gcp-data-architect etc.). O build foi feito diretamente porque o usuário não solicitou subagentes e o manifesto era pequeno e altamente acoplado (o workflow depende dos detalhes exatos dos dois Dockerfiles e do comportamento real da API). As convenções de cada especialidade foram aplicadas a partir dos padrões do próprio DESIGN.

---

## Task Execution

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `requirements-api.txt` | ✅ | Executado antes do build, a pedido do usuário |
| 2 | `requirements.txt` → `-r requirements-api.txt` | ✅ | Idem |
| 3 | `api/Dockerfile` | ✅ | Trazido do worktree **e ajustado** para `requirements-api.txt` |
| 4 | `.dockerignore` | ✅ | Trazido do worktree sem alteração |
| 5 | `frontend/Dockerfile` | ✅ | Trazido do worktree sem alteração |
| 6 | `frontend/next.config.mjs` | ✅ | `output: "standalone"` |
| 7 | `frontend/.dockerignore` | ✅ | Trazido do worktree sem alteração |
| 8 | `infra/terraform/main.tf` | ✅ | Já escrito; agora rastreado no working tree para commit |
| 9 | `.github/workflows/deploy.yml` | ✅ | **Novo** — 227 linhas, 16 steps |
| 10 | `CLAUDE.md` | ✅ | Seção "Deploy (Cloud Run)" + estrutura + contagem de testes |
| 11 | `.env.example` | ✅ | Documenta `API_KEYS` e o efeito do default de `FRONTEND_ORIGINS` |
| 12 | `api/routers/simulate.py` | ✅ | Validação de tenant → 403 (executado antes do build) |
| 13 | `tests/test_api_simulate.py` | ✅ | Fixture + teste novo de divergência de tenant |
| — | Merge e remoção do worktree | ✅ | Branch `worktree-agent-a99633d8eef6cb127` apagado, `.claude/worktrees/` removido |

---

## Files Created

| File | Lines | Verified | Notes |
|------|-------|----------|-------|
| `.github/workflows/deploy.yml` | 227 | ✅ | YAML parseado; todos os 13 blocos `run` passam em `bash -n`; smoke test executado de verdade |
| `api/Dockerfile` | 33 | ⚠️ | `docker` não existe neste sandbox — não buildado (ver Blockers) |
| `frontend/Dockerfile` | 44 | ⚠️ | Idem; mas a premissa dele (`.next/standalone/server.js`) foi verificada |
| `.dockerignore` | 19 | ✅ | Revisão de código |
| `frontend/.dockerignore` | 6 | ✅ | Revisão de código |
| `requirements-api.txt` | 13 | ✅ | `pytest`+`ruff` verdes com o `-r` em vigor |

---

## Verification Results

### Lint

```text
ruff check .            → All checks passed!
npm run lint (frontend) → ✔ No ESLint warnings or errors
```

**Status:** ✅ Pass

### Tests

```text
pytest tests/ -q  → 73 passed, 1 warning in 1.17s
npm test          → Tests 12 passed (12)
```

**Status:** ✅ 85/85 Pass (73 pytest + 12 vitest)

### Build do frontend (premissa do Dockerfile)

```text
NEXT_PUBLIC_API_BASE_URL=https://taxreformai-api-teste.run.app npm run build

Route (app)                Size      First Load JS
┌ ○ /                      175 B     96.1 kB
├ ○ /consulta              37.3 kB   135 kB
└ ○ /simulador             3.63 kB   102 kB

.next/standalone/server.js  → 4566 bytes  ✅
```

Verificação adicional de que o `--build-arg` realmente funciona:

```text
grep -ro "taxreformai-api-teste.run.app" .next/static/ | wc -l  → 2
grep -ro "localhost:8000"                .next/static/ | wc -l  → 0
```

**Status:** ✅ A URL é inlinada nos dois bundles de página e o fallback `localhost:8000` desaparece — a premissa central da Decisão 1 está provada, não assumida.

### Smoke test — executado contra `uvicorn` real

O script do step "Smoke test" foi **extraído do YAML e executado**, não só revisado. A API roda sem infraestrutura nenhuma, então isso não viola a política de "infra real nunca roda local".

| Cenário | Configuração | Resultado esperado | Resultado obtido |
|---------|--------------|--------------------|------------------|
| Feliz | `API_KEYS` e `FRONTEND_ORIGINS` corretos | (a)(b)(c) passam | ✅ `OK healthz` / `OK simulate` / `OK cors` |
| **AT-004** | Serviço subiu **sem** `API_KEYS` | Reprovar com diagnóstico | ✅ `/healthz` devolveu **200**, e mesmo assim o script falhou: `FALHA: /v1/tax/simulate devolveu 401` — exit 1 |
| CORS obsoleta | `FRONTEND_ORIGINS` ≠ URL do frontend | Reprovar com diagnóstico | ✅ `FALHA CORS: recebido '', esperado '...XYZ.run.app'` — exit 1 |

O cenário AT-004 é a evidência mais importante do build: prova que `/healthz` sozinho seria um teste **inútil** aqui, exatamente como a Decisão 6 previa.

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | **Bug real no smoke test, encontrado ao executá-lo.** Com `set -euo pipefail`, quando a origem é recusada não existe header `access-control-allow-origin`; o `grep` sai 1, o `pipefail` propaga e o script morria **antes** de imprimir o diagnóstico. O job reprovava corretamente, mas sem dizer o porquê — o operador veria vermelho sem explicação | Adicionado `|| true` ao fim do pipeline, deixando `ACAO` vazio fluir para o `if`. Reverificado: agora imprime `FALHA CORS: recebido '', esperado '...'` |
| 2 | O `.dockerignore` da raiz exclui `*.md`, `infra/`, `tests/`, `dags/`, `frontend/` — precisava **não** excluir `requirements-api.txt` | Conferido: o padrão não captura o arquivo. Build da API teria o requirements disponível |
| 3 | Branch órfão `worktree-agent-a99633d8eef6cb127` sobrevivia à remoção do worktree | `git worktree unlock` → `remove --force` → `git branch -D`; `.claude/worktrees/` removido |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Step "Resolver URL da API" roda sempre, não só quando `target=frontend` | Simplifica o fluxo e dá a mensagem de erro clara ("deploy a API primeiro") num único lugar | Nenhum — `describe` é leitura barata |
| Adicionado step "Resumo" escrevendo em `$GITHUB_STEP_SUMMARY` | Não estava no DESIGN; o operador precisa das URLs em algum lugar visível após o deploy | Puramente aditivo |
| Smoke test deriva o `tenant_id` de `API_KEYS` via `jq` em vez de usar literal `"smoke"` | Consequência da correção de multi-tenancy (item 12): um `tenant_id` fixo passaria a receber 403 | O smoke test agora também exercita indiretamente a validação de tenant |
| Deploy usa `google-github-actions/auth@v2` + `setup-gcloud@v2` em vez do `echo` manual de `terraform.yml` | Actions oficiais cuidam de `gcloud auth configure-docker` e da limpeza da credencial | Menos código e menos risco de credencial esquecida no runner |

---

## Blockers

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| `docker` não está disponível neste sandbox | AT-006 (build real das imagens) não pôde ser exercitado localmente. A verificação real acontece no primeiro run do `deploy.yml`. **Não foi simulado nem presumido bem-sucedido** | Runner do GitHub Actions |
| `pip install -r requirements.txt` não verificável aqui | `lxml`/`qdrant-client`/`fastembed` não instalam neste sandbox (bloqueio já conhecido do projeto). A sintaxe `-r` é padrão do pip e o caminho é relativo ao próprio arquivo, mas a confirmação vem do CI | CI (`ci.yml`) |
| Recursos de CD possivelmente não aplicados (DEFINE A-002) | Rodar `terraform.yml` com `action=plan` — barato, não cria nada | Operador |
| Secrets `GCP_DEPLOYER_SA_KEY` e `API_KEYS` não existem | Runbook do DESIGN, passos 2-5 | Operador |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Deploy da API | ⏳ Pendente | Requer runbook + primeiro deploy real |
| AT-002 | Deploy do frontend | ⏳ Pendente | Idem. A parte verificável (build standalone + inline da URL) está ✅ |
| AT-003 | CORS entre os serviços | ✅ Lógica verificada | Asserção (c) exercitada contra `uvicorn` real, nos dois sentidos (acerto e erro) |
| AT-004 | API sem `API_KEYS` reprova o job | ✅ **Verificado** | `/healthz` = 200 no serviço quebrado; smoke test falhou com exit 1 e diagnóstico |
| AT-005 | Guarda de confirmação | ✅ Código verificado | Step condicional `if: inputs.confirm != 'DEPLOY'` como primeiro step, antes de `checkout` e de qualquer auth |
| AT-006 | Build da imagem da API | ⏳ Bloqueado | `docker` ausente no sandbox — ver Blockers |
| AT-007 | `terraform init`/`plan` sem drift | ⏳ Pendente | Requer rodar `terraform.yml` |

**3 de 7 verificados**, 1 bloqueado por ambiente, 3 dependem do runbook do operador. Nenhum foi marcado como aprovado sem evidência.

---

## Final Status

### Overall: ✅ COMPLETE (código) — aguardando runbook do operador

**Completion Checklist:**

- [x] Todas as 13 tarefas do manifesto concluídas
- [x] Lint passa (ruff + eslint)
- [x] Testes passam (73 pytest + 12 vitest)
- [x] Worktree mergeado e removido; nenhum arquivo de CD fora do controle de versão
- [x] Smoke test exercitado de verdade, incluindo seus modos de falha
- [ ] Acceptance tests completos — 3/7 verificados, o resto depende de infraestrutura real
- [ ] Pronto para `/ship` — **ainda não**: shipar antes do primeiro deploy real repetiria o padrão de `PIPELINE_INGESTAO_LEGAL` (feature arquivada com critério de sucesso central nunca verificado)

---

## Recomendação

**Não shipar ainda.** O projeto já tem uma feature arquivada cujo critério de sucesso principal (busca híbrida E2E) segue pendente desde 2026-07-24 por ter sido shipada antes da verificação real. Aqui a distância até a verificação é curta e o caminho é conhecido: executar o runbook (4 passos de operador) e rodar `deploy.yml` uma vez. Se o smoke test passar contra os serviços reais, AT-001/002/006 fecham de uma vez e o `/ship` passa a ser honesto.

Ordem sugerida: `terraform.yml action=plan` → `apply` → chave da SA → secrets → `deploy.yml target=both confirm=DEPLOY` → `/ship`.

---

## Next Step

**Após o runbook e o primeiro deploy verde:** `/ship .claude/sdd/features/DEFINE_DEPLOY_CLOUD_RUN.md`

---

## Revisão pós-build (2026-07-24, mesma data)

Varredura das partes que o build original **não** cobriu: `.github/workflows/ingestao.yml` e
`scripts/verificar_busca_hibrida.py` (escritos fora do manifesto, nunca revisados) e os dois
Dockerfiles (marcados ⚠️ por ausência de `docker`). Quatro defeitos reais encontrados — três
deles quebrariam a **primeira execução real e cobrável** na nuvem.

| # | Defeito | Onde | Como quebraria | Correção |
|---|---------|------|----------------|----------|
| 1 | `qdrant_point_id()` devolvia hexdigest sha256 de 64 chars. O Qdrant só aceita inteiro sem sinal **ou UUID** — qualquer outra string é rejeitada com 400 | `ingestion/chunking/chunk_models.py:18` | Todo `upsert` falharia. O pipeline baixaria o BGE-M3 (~2GB), raspa, parseia, chunka e embeda — e morreria na última etapa | `uuid.uuid5` sobre a mesma chave `documento_id:dispositivo`, preservando determinismo e idempotência da reingestão. Namespace fixo documentado como imutável |
| 2 | App `typer` com um único `@app.command()` e sem callback é achatado: o nome do comando não é aceito | `ingestion/pipeline.py:111` | `python -m ingestion.pipeline run --url ...` (`ingestao.yml:70`) falharia com *unexpected extra argument (run)* | `@app.callback()` força modo multi-comando. **Não verificado empiricamente** — `typer` não instala neste sandbox; inferido do comportamento documentado do Typer. A correção é segura nos dois casos |
| 3 | `COPY --from=builder /app/public ./public` sobre diretório inexistente | `frontend/Dockerfile:37` | `docker build` do frontend abortaria — AT-002/AT-006 | Criado `frontend/public/.gitkeep` (convenção Next.js, mantém o COPY válido e serve assets futuros) |
| 4 | `main.tf` fora do `terraform fmt`; `terraform validate` nunca executado | `infra/terraform/main.tf` | Ruído de diff; erros de tipo só apareceriam no `apply` do operador | `terraform fmt` aplicado; `terraform init -backend=false` + `validate` → **Success**. Estático, sem contato com GCP |

### Por que o teste existente não pegou o defeito 1

`test_pontos_qdrant_tem_id_deterministico_e_unico` afirmava apenas que os ids eram determinísticos
e únicos — propriedades que um hexdigest sha256 satisfaz perfeitamente. O teste estava certo e
inútil ao mesmo tempo. Adicionado `test_point_id_e_uuid_valido`, que **falha** contra a
implementação antiga.

### Verificações adicionais (nenhum defeito)

- Cadeia de imports da imagem da API: só `api`, `motor_calculo`, `orquestracao`, `ingestion` —
  os quatro são copiados. `langgraph` aparece em `orquestracao/grafo.py:12` mas **dentro de
  função**; a API usa `executor.py`, então `requirements-api.txt` (fastapi/uvicorn/pydantic)
  basta. Todos os 12 `__init__.py` estão vazios — nenhum import pesado escondido.
- Contextos de build batem com os Dockerfiles: API usa `.` (raiz) com `-f api/Dockerfile`;
  frontend usa `frontend/`. `package-lock.json` existe (`npm ci` não falha).
- `scripts/verificar_busca_hibrida.py` conferido contra o código real: `embed_consulta`,
  `search_hybrid(dense_query, sparse_indices, sparse_values, limit)`, nomes de vetor
  `"dense"`/`"sparse"` e campos de payload `texto`/`dispositivo` — todos batem.
- Os 4 workflows parseiam como YAML; os 13 blocos `run` passam em `bash -n`.

### Estado após a revisão

```text
ruff check .   → All checks passed!
pytest tests/  → 74 passed          (73 + 1 regressão nova)
npm run lint   → No ESLint warnings or errors
npm test       → 12 passed
npm run build  → .next/standalone/server.js (4566 bytes) + public/ presente
terraform validate → Success!
```

**AT-006 continua bloqueado** (sem `docker` no sandbox), mas o defeito 3 mostra que a revisão de
código dos Dockerfiles no build original passou por cima de uma falha certa. Os demais
acceptance tests seguem dependendo do runbook do operador.
