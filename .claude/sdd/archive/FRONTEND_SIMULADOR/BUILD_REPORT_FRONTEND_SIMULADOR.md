# BUILD REPORT: Frontend Next.js — Simulador Tributário

> Implementation report for FRONTEND_SIMULADOR

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_SIMULADOR |
| **Date** | 2026-07-23 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_FRONTEND_SIMULADOR.md](../features/DEFINE_FRONTEND_SIMULADOR.md) |
| **DESIGN** | [DESIGN_FRONTEND_SIMULADOR.md](../features/DESIGN_FRONTEND_SIMULADOR.md) |
| **Status** | ✅ Complete — inclui uma correção de bug real no backend (`API_HTTP_SIMULACAO`), fora do escopo original desta feature |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 25/25 (Shadcn CLI substituído pelo fallback previsto na Decision 4) |
| **Files Created** | 31 |
| **Files Modified** | 1 (`api/main.py` — fora do manifest original, ver Issues) |
| **Lines of Code** | ~1.087 (TypeScript/TSX/config) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12/12 novos (frontend) + 59/59 pré-existentes (backend, sem regressão) |
| **Agents Used** | 0 (execução direta) |

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `frontend/package.json` | 37 | ✅ | `npm install` bem-sucedido (307 pacotes) |
| `frontend/tsconfig.json`, `next.config.mjs`, `tailwind.config.ts`, `postcss.config.mjs` | 50 | ✅ | `npx tsc --noEmit` sem erros |
| `frontend/app/globals.css` | 14 | ✅ | |
| `frontend/lib/cn.ts` | 6 | ✅ | Helper `clsx`+`tailwind-merge` |
| `frontend/components/ui/{button,input,label,textarea,card}.tsx` | 111 | ✅ | **Fallback da Decision 4** — Shadcn CLI é uma versão nova baseada em templates/presets de projeto inteiro, incompatível com o Next.js já montado à mão; escritos manualmente no mesmo estilo visual |
| `frontend/lib/types.ts` | 63 | ✅ | Espelha `api/schemas_simulate.py`/`schemas_query.py` |
| `frontend/lib/api-client.ts` | 48 | ✅ | `ApiError` com `status`/`detail` |
| `frontend/hooks/useApiKey.ts` | 21 | ✅ | 3/3 testes passam |
| `frontend/components/ApiKeyBar.tsx` | 36 | ✅ | Corrigido durante o build (ver Issues) |
| `frontend/components/ErrorBanner.tsx` | 21 | ✅ | |
| `frontend/app/providers.tsx`, `app/layout.tsx`, `app/page.tsx` | 77 | ✅ | Build de produção gera as 3 rotas estaticamente |
| `frontend/components/SimuladorForm.tsx`, `ResultadoSimulacao.tsx`, `app/simulador/page.tsx` | 207 | ✅ | 2/2 testes passam (AT-001, AT-002) |
| `frontend/components/ConsultaForm.tsx`, `ParecerMarkdown.tsx`, `app/consulta/page.tsx` | 118 | ✅ | 3/3 testes passam (AT-002, AT-003, happy path) |
| `frontend/vitest.config.ts`, `vitest.setup.ts` | 18 | ✅ | |
| `frontend/hooks/useApiKey.test.ts`, `lib/api-client.test.ts`, `app/simulador/page.test.tsx`, `app/consulta/page.test.tsx` | 260 | ✅ | 12/12 testes passam |

## Files Modified (fora do manifest original)

| File | Change | Reason |
| ---- | ------ | ------ |
| `api/main.py` | Adicionado `CORSMiddleware` (origens via `FRONTEND_ORIGINS`, default `localhost:3000`) | **Bug real descoberto durante a verificação E2E** — ver Issues #2 |

---

## Verification Results

### Lint / Type Check

```text
$ npx tsc --noEmit
(sem output — sem erros)

$ ruff check .   # backend, após a mudança em api/main.py
All checks passed!
```

**Status:** ✅ Pass

### Build de Produção

```text
$ npm run build
✓ Compiled successfully
✓ Generating static pages (6/6)

Route (app)                              Size     First Load JS
┌ ○ /                                    175 B          96.1 kB
├ ○ /consulta                            38.1 kB         136 kB
└ ○ /simulador                           4.42 kB         103 kB
```

**Status:** ✅ Pass

### Tests

```text
$ npx vitest run
 ✓ lib/api-client.test.ts (4 tests)
 ✓ hooks/useApiKey.test.ts (3 tests)
 ✓ app/simulador/page.test.tsx (2 tests)
 ✓ app/consulta/page.test.tsx (3 tests)
 Test Files  4 passed (4) | Tests 12 passed (12)

$ python3 -m pytest tests/ -q   # backend, sem regressão após CORS
59 passed, 1 warning in 1.00s
```

**Status:** ✅ 12/12 (frontend, novos) + 59/59 (backend, pré-existentes)

### E2E Manual

```text
$ npm run dev -- --port 3123    → GET /, /simulador, /consulta = 200
$ uvicorn api.main:app --port 8000 (FRONTEND_ORIGINS=http://localhost:3123)
$ curl -X OPTIONS .../v1/tax/query -H "Origin: http://localhost:3123" ...
  → access-control-allow-origin: http://localhost:3123 (após a correção do Issue #2)
```

**Status:** ✅ Pass, com uma limitação — ver "Blockers" abaixo

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|--------------|
| 1 | Shadcn CLI (`npx shadcn@latest init`) é uma versão reformulada baseada em templates de projeto inteiro (`--template`, `--preset`), incompatível com scaffolding manual de um Next.js já existente | Acionado o fallback já previsto na Decision 4 — componentes `ui/*` escritos manualmente com Tailwind, seguindo a mesma convenção visual (bordas arredondadas, paleta neutra) | +10m |
| 2 | **Bug real e crítico**: o backend (`api/main.py`, feature `API_HTTP_SIMULACAO` já shipada) não tinha `CORSMiddleware`. Verificado com `curl -X OPTIONS` simulando um preflight de navegador: retornava `405` sem nenhum header `Access-Control-Allow-*`. Isso significa que a UI, rodando num navegador real, teria **toda chamada à API bloqueada** — um problema que nenhum teste automatizado (que mocka `apiPost`) nem verificação via `curl` direto (que não aplica CORS) detectaria | Adicionado `CORSMiddleware` em `api/main.py`, com origens configuráveis via `FRONTEND_ORIGINS` (default `localhost:3000`). Reverificado com `curl -X OPTIONS` simulando o preflight — agora retorna `200` com os headers corretos. Suite de testes do backend (59 testes) re-executada sem regressão | +15m |
| 3 | `ApiKeyBar`: o campo de input não refletia a chave já salva no `localStorage` ao carregar a página — o estado local (`draft`) capturava o valor de `apiKey` só na primeira renderização, antes do hook terminar de ler o `localStorage` (efeito assíncrono) | Adicionado um `useEffect` sincronizando `draft` sempre que `apiKey` mudar | +3m |
| 4 | `@vitejs/plugin-react`, referenciado em `vitest.config.ts`, não estava listado em `package.json` | Adicionado e reinstalado (`npm install`) | +2m |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Componentes `ui/*` escritos manualmente em vez de gerados pelo Shadcn CLI | Fallback já previsto explicitamente na Decision 4 do DESIGN — a versão do CLI disponível não é compatível com o cenário de "adicionar a um projeto Next.js já existente" | Nenhum — visualmente equivalente, mesma API de componentes |
| `api/main.py` modificado (CORS) | Não estava no File Manifest original — descoberto como bug real durante a verificação E2E desta feature | Necessário para a feature funcionar de verdade num navegador; documentado explicitamente aqui e deve ser mencionado no `/ship` |

---

## Blockers

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| Verificação em navegador real não pôde ser feita — extensão Claude in Chrome não está conectada neste ambiente (`tabs_context_mcp` retornou "Browser extension is not connected") | Rodar `npm run dev` localmente e testar manualmente no navegador do usuário, especialmente o fluxo de configurar API key → simular → ver resultado | Usuário |
| Nenhum dos dois backends reais (`ingestion`/Qdrant, LLMs) está conectado — o frontend consome corretamente a API, mas os dados exibidos em `/consulta` continuam vindo dos fakes de `orquestracao/` | Já documentado nas features anteriores; sem impacto novo nesta feature | — |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path (estruturado) — exibe `resumo_financeiro`/`itens_detalhados` reais | ✅ Pass | `app/simulador/page.test.tsx` |
| AT-002 | Error case (auth) — 401 exibido claramente em ambas as páginas | ✅ Pass | Testado em `simulador` e `consulta` |
| AT-003 | Edge case (conversacional) — 422 exibido sem parecer inventado | ✅ Pass | `app/consulta/page.test.tsx` — confirma ausência de "Parecer de Simulação" na tela de erro |

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| API key configurada persiste entre reloads | ✅ | `useApiKey.test.ts` (3 testes) |
| `/simulador` exibe `resumo_financeiro`/`itens_detalhados` reais | ✅ | Teste + build de produção |
| `/consulta` exibe `parecer_final` (Markdown) + histórico | ✅ | Teste + `react-markdown` renderiza `## Parecer de Simulação Tributária` corretamente |
| Erros 401/422 exibidos como mensagem clara | ✅ | `ErrorBanner` testado nos dois fluxos |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados (25/25, com fallback documentado no lugar do Shadcn CLI)
- [x] `tsc --noEmit` sem erros
- [x] `npm run build` (produção) bem-sucedido
- [x] Testes automatizados passam (12/12 novos + 59/59 backend sem regressão)
- [x] Um bug crítico de CORS no backend encontrado e corrigido
- [x] Todos os Acceptance Tests verificados
- [ ] Verificação em navegador real — bloqueada pela extensão não conectada neste ambiente

---

## Next Step

`/ship .claude/sdd/features/DEFINE_FRONTEND_SIMULADOR.md` — mencionar explicitamente a correção de CORS em `api/main.py` como parte desta feature, já que tecnicamente altera uma feature já shipada (`API_HTTP_SIMULACAO`).
