# DESIGN: Frontend Next.js — Simulador Tributário

> Technical design for implementing a interface web (Next.js 14 App Router) que consome `/v1/tax/simulate` e `/v1/tax/query`, com API key gerenciada via `localStorage`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_SIMULADOR |
| **Date** | 2026-07-23 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_FRONTEND_SIMULADOR.md](./DEFINE_FRONTEND_SIMULADOR.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                  FRONTEND NEXT.JS — SIMULADOR TRIBUTÁRIO                   │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Browser]                                                                │
│      │                                                                     │
│      ▼                                                                     │
│  [app/layout.tsx] ── <ApiKeyBar/> (useApiKey → localStorage)              │
│      │                                                                     │
│      ├──► /simulador (Client Component)                                  │
│      │       │  <SimuladorForm/> (itens dinâmicos)                       │
│      │       │  useMutation → lib/api-client.ts                          │
│      │       ▼                                                            │
│      │   POST /v1/tax/simulate ──► [api/ — FastAPI, feature já shipada]  │
│      │       │                                                             │
│      │       ▼                                                            │
│      │   <ResultadoSimulacao/> ou <ErrorBanner/> (401/422)               │
│      │                                                                     │
│      └──► /consulta (Client Component)                                   │
│              │  <ConsultaForm/>                                          │
│              │  useMutation → lib/api-client.ts                          │
│              ▼                                                            │
│          POST /v1/tax/query ──► [api/ — FastAPI, feature já shipada]     │
│              │                                                             │
│              ▼                                                            │
│          <ParecerMarkdown/> + histórico, ou <ErrorBanner/> (401/422)     │
│                                                                             │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `hooks/useApiKey.ts` | Lê/escreve a API key no `localStorage`, expõe estado reativo | React hook custom |
| `components/ApiKeyBar.tsx` | Input persistente no layout, usa `useApiKey` | React + Shadcn `Input`/`Button` |
| `lib/api-client.ts` | `fetch` tipado, injeta `X-API-Key`, lança `ApiError` estruturado em 401/422 | TypeScript + `fetch` nativo |
| `lib/types.ts` | Tipos espelhando `api/schemas_simulate.py`/`schemas_query.py` | TypeScript |
| `app/simulador/page.tsx` + `components/SimuladorForm.tsx` + `components/ResultadoSimulacao.tsx` | Formulário estruturado + exibição de resultado | React + TanStack Query + Shadcn |
| `app/consulta/page.tsx` + `components/ConsultaForm.tsx` + `components/ParecerMarkdown.tsx` | Formulário conversacional + parecer renderizado | React + TanStack Query + `react-markdown` |
| `components/ErrorBanner.tsx` | Exibe `ApiError` (401/422) de forma legível, compartilhado pelas duas páginas | React + Shadcn |

---

## Key Decisions

### Decision 1: API key gerenciada via `localStorage`, sem sistema de auth real

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** O backend (`api/`) só tem autenticação via `X-API-Key` — não há login/sessão de usuário no projeto.

**Choice:** `useApiKey()` lê/escreve a chave em `localStorage` (`taxreform:api-key`), sem criptografia adicional. `ApiKeyBar` no layout raiz permite configurá-la.

**Rationale:** Espelha exatamente o mecanismo real do backend — nenhuma camada de autenticação fictícia.

**Alternatives Rejected:**
1. Simular login/sessão — rejeitado; inventaria um sistema de usuários que não existe no backend.

**Consequences:**
- Chave fica em texto plano no navegador — aceitável para esta fase (mesmo nível de segurança do backend, que já documenta isso como limitação em `API_HTTP_SIMULACAO`)

---

### Decision 2: TanStack Query (`useMutation`) para as chamadas de API

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** `contexto.md` (seção 5.2) já define TanStack Query como parte da stack — não é uma escolha em aberto, só a aplicação correta dela.

**Choice:** Cada submissão de formulário usa `useMutation`, chamando `lib/api-client.ts`. Estados `isPending`/`isError`/`error` do TanStack Query controlam a UI (loading, banner de erro).

**Rationale:** Evita `useEffect`+`fetch` manual e dá tratamento de erro/loading padronizado, exigido pelo DEFINE (Goal MUST — erros exibidos claramente).

**Consequences:**
- Nenhum trade-off relevante — é a aplicação direta de uma decisão de stack já tomada

---

### Decision 3: Erros HTTP como `ApiError` estruturado no cliente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** A UI precisa diferenciar 401 (auth) de 422 (regra de negócio/validação, ex. `AliquotaNaoDisponivelError`) para mostrar mensagens diferentes (AT-002 e AT-003 do DEFINE).

**Choice:** `lib/api-client.ts` lança uma classe `ApiError extends Error` com `status: number` e `detail: string`, parseada da resposta JSON de erro do FastAPI (`{"detail": "..."}` ou lista de erros de validação do Pydantic).

**Rationale:** Sem isso, cada componente teria que reimplementar o parsing do formato de erro do FastAPI.

**Alternatives Rejected:**
1. Deixar o erro cru do `fetch`/`Response` propagar — rejeitado; obrigaria cada chamador a saber o formato de erro do backend.

**Consequences:**
- Um único lugar (`api-client.ts`) conhece o formato de erro do FastAPI; componentes só leem `error.status`/`error.detail`

---

### Decision 4: Shadcn UI via CLI, com fallback para componentes Tailwind simples

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** O blueprint já decide Shadcn UI como parte da stack. Shadcn não é um pacote npm tradicional — é uma CLI (`npx shadcn@latest add ...`) que copia código-fonte de componentes para o projeto. Uma checagem rápida (`npx shadcn@latest --version`) não retornou dentro de 20s neste sandbox — inconclusivo (pode só ser lento na primeira resolução via `npx`, não necessariamente quebrado).

**Choice:** Durante o Build, tentar `npx shadcn@latest init` + `add button input label textarea card` com um timeout generoso (~90s). **Se falhar ou travar**, usar componentes Tailwind hand-rolled equivalentes (`components/ui/button.tsx` etc., estilizados para parecer com o padrão visual do Shadcn: bordas arredondadas, paleta neutra), documentado como fallback no Build Report.

**Rationale:** Tenta honrar a decisão de stack do blueprint sem bloquear a feature inteira caso a ferramenta não funcione bem neste ambiente específico.

**Alternatives Rejected:**
1. Pular Shadcn e usar só Tailwind puro desde já — rejeitado como primeira opção; só vira o plano B se o CLI genuinamente não funcionar.

**Consequences:**
- O File Manifest lista os componentes `ui/*` como "Create (via CLI ou fallback manual)" — o conteúdo exato depende do que a ferramenta gerar

---

### Decision 5: Testes com Vitest + Testing Library, não Playwright

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** O DEFINE pede verificação de comportamento (persistência de API key, exibição de erro, exibição de dados reais) — não uma suíte E2E de navegador completa.

**Choice:** `vitest` + `@testing-library/react` + `jsdom` para testes de hook/componente, mockando `lib/api-client.ts` diretamente (sem MSW). Verificação manual adicional com `next build` + `next dev` real durante o Build — mesmo espírito do `uvicorn`+`curl` já feito em `API_HTTP_SIMULACAO`.

**Alternatives Rejected:**
1. Playwright — rejeitado nesta fase; exigiria instalar um browser headless, desproporcional ao escopo funcional do DEFINE.

**Consequences:**
- Cobertura é de comportamento de componente, não de navegação real de ponta a ponta — aceitável dado o escopo

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `frontend/package.json` | Create | Dependências (`next`, `react`, `@tanstack/react-query`, `react-markdown`, `tailwindcss`, `vitest`, `@testing-library/react`) | @typescript-reviewer | None |
| 2 | `frontend/tsconfig.json` | Create | Configuração TypeScript | @typescript-reviewer | None |
| 3 | `frontend/next.config.mjs` | Create | Configuração Next.js mínima | @typescript-reviewer | None |
| 4 | `frontend/tailwind.config.ts` + `postcss.config.mjs` | Create | Configuração Tailwind | @typescript-reviewer | None |
| 5 | `frontend/app/globals.css` | Create | Diretivas Tailwind | @typescript-reviewer | 4 |
| 6 | `frontend/components/ui/*` (`button`, `input`, `label`, `textarea`, `card`) | Create | Primitivas Shadcn (via CLI) ou fallback Tailwind manual (Decision 4) | @typescript-reviewer | 4 |
| 7 | `frontend/lib/types.ts` | Create | Tipos espelhando os schemas Pydantic reais | @typescript-reviewer | None |
| 8 | `frontend/lib/api-client.ts` | Create | `fetch` tipado + `ApiError` | @typescript-reviewer | 7 |
| 9 | `frontend/hooks/useApiKey.ts` | Create | Hook de persistência em `localStorage` | @typescript-reviewer | None |
| 10 | `frontend/components/ApiKeyBar.tsx` | Create | Input de API key no layout | @typescript-reviewer | 6, 9 |
| 11 | `frontend/components/ErrorBanner.tsx` | Create | Exibição de `ApiError` | @typescript-reviewer | 6, 8 |
| 12 | `frontend/app/providers.tsx` | Create | `QueryClientProvider` (Client Component) | @typescript-reviewer | None |
| 13 | `frontend/app/layout.tsx` | Create | Layout raiz, inclui `ApiKeyBar` + `Providers` + navegação | @typescript-reviewer | 10, 12 |
| 14 | `frontend/app/page.tsx` | Create | Página inicial com links para `/simulador` e `/consulta` | @typescript-reviewer | 6 |
| 15 | `frontend/components/SimuladorForm.tsx` | Create | Formulário de itens dinâmico (NCM/quantidade/valor/UF) | @typescript-reviewer | 6, 7 |
| 16 | `frontend/components/ResultadoSimulacao.tsx` | Create | Exibe `resumo_financeiro`/`itens_detalhados` | @typescript-reviewer | 6, 7 |
| 17 | `frontend/app/simulador/page.tsx` | Create | Página `/simulador` — orquestra formulário + resultado + erro | @typescript-reviewer | 8, 11, 15, 16 |
| 18 | `frontend/components/ConsultaForm.tsx` | Create | Formulário de pergunta livre + ano/valor | @typescript-reviewer | 6, 7 |
| 19 | `frontend/components/ParecerMarkdown.tsx` | Create | Renderiza `parecer_final` + histórico | @typescript-reviewer | 7 |
| 20 | `frontend/app/consulta/page.tsx` | Create | Página `/consulta` — orquestra formulário + parecer + erro | @typescript-reviewer | 8, 11, 18, 19 |
| 21 | `frontend/vitest.config.ts` + `vitest.setup.ts` | Create | Configuração de testes | @test-generator | 1 |
| 22 | `frontend/hooks/useApiKey.test.ts` | Create | Testes do hook de persistência | @test-generator | 9, 21 |
| 23 | `frontend/lib/api-client.test.ts` | Create | Testes de `ApiError` (401/422 parseados corretamente) | @test-generator | 8, 21 |
| 24 | `frontend/app/simulador/page.test.tsx` | Create | AT-001 (happy path) + AT-002 (sem API key) | @test-generator | 17, 21 |
| 25 | `frontend/app/consulta/page.test.tsx` | Create | AT-003 (422 sem parecer inventado) + AT-002 | @test-generator | 20, 21 |

**Total Files:** 25 (mais os arquivos gerados pelo Shadcn CLI, cujo conteúdo exato não é hand-specified — ver Decision 4)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @typescript-reviewer | 1–20 | Especialista em TypeScript/React/Next.js — MUST BE USED para todo código TS/JS deste projeto |
| @test-generator | 21–25 | Especialista em testes, adaptado aqui para Vitest/Testing Library em vez de pytest |
| @a11y-architect | (revisão final dos componentes `ui/*` e formulários) | Recomendado no `CLAUDE.md`/routing do agentcode para componentes de design system |
| @code-reviewer | (revisão final) | Revisão de qualidade geral |

---

## Code Patterns

### Pattern 1: `useApiKey` hook

```typescript
// frontend/hooks/useApiKey.ts
"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "taxreform:api-key";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setApiKeyState(stored);
  }, []);

  const setApiKey = useCallback((value: string) => {
    window.localStorage.setItem(STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  return { apiKey, setApiKey };
}
```

### Pattern 2: `lib/api-client.ts` com `ApiError`

```typescript
// frontend/lib/api-client.ts

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function apiPost<TResponse>(
  path: string,
  body: unknown,
  apiKey: string,
): Promise<TResponse> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const detail =
      typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<TResponse>;
}
```

### Pattern 3: `lib/types.ts` (espelhando os schemas Pydantic reais)

```typescript
// frontend/lib/types.ts
// Espelha api/schemas_simulate.py e api/schemas_query.py — mesmos nomes de campo

export interface ItemSimulacao {
  sku: string;
  ncm: string;
  quantidade: number;
  valor_unitario: string; // Decimal serializado como string pelo FastAPI/Pydantic
  uf_origem: string;
  uf_destino: string;
}

export interface PayloadSimulacao {
  tenant_id: string;
  ano_operacao: number;
  operacao_tipo: string;
  itens: ItemSimulacao[];
}

export interface RespostaSimulacao {
  status: string;
  ano_operacao: number;
  resumo_financeiro: {
    valor_bruto_total: string;
    total_cbs: string;
    total_ibs: string;
    total_is: string;
    valor_liquido_projetado_split_payment: string;
  };
  itens_detalhados: Array<{
    sku: string;
    ncm: string;
    aliquotas_aplicadas: { cbs_percentual: string; ibs_percentual: string; is_percentual: string };
    fundamentacao_legal: string;
  }>;
}

export interface PayloadConsulta {
  texto_consulta: string;
  ano_operacao: number;
  valor_base: string;
}

export interface RespostaConsulta {
  parecer_final: string;
  valor_liquido: string;
  fonte_legal: string;
  historico: Array<{ no: string; resumo_output: string }>;
}
```

### Pattern 4: `app/providers.tsx`

```typescript
// frontend/app/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

### Pattern 5: Uso de `useMutation` numa página (padrão para `/simulador` e `/consulta`)

```typescript
// frontend/app/simulador/page.tsx (trecho ilustrativo)
"use client";

import { useMutation } from "@tanstack/react-query";
import { apiPost, ApiError } from "@/lib/api-client";
import type { PayloadSimulacao, RespostaSimulacao } from "@/lib/types";
import { useApiKey } from "@/hooks/useApiKey";

export default function SimuladorPage() {
  const { apiKey } = useApiKey();
  const mutation = useMutation<RespostaSimulacao, ApiError, PayloadSimulacao>({
    mutationFn: (payload) => apiPost("/v1/tax/simulate", payload, apiKey),
  });

  // <SimuladorForm onSubmit={(payload) => mutation.mutate(payload)} />
  // {mutation.isError && <ErrorBanner error={mutation.error} />}
  // {mutation.isSuccess && <ResultadoSimulacao resposta={mutation.data} />}
}
```

---

## Data Flow

```text
1. Usuário abre o app, configura a API key em <ApiKeyBar/> (persiste em localStorage)
2. Usuário navega para /simulador ou /consulta
3. Preenche o formulário, envia
4. useMutation chama lib/api-client.ts (apiPost), que injeta X-API-Key e faz o POST
5. Se erro (401/422): ApiError é lançado, capturado por useMutation, exibido via ErrorBanner
6. Se sucesso: resposta tipada exibida via ResultadoSimulacao ou ParecerMarkdown
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| `api/` (FastAPI, feature `API_HTTP_SIMULACAO`) | REST/JSON via `fetch` | Header `X-API-Key`, lido do `localStorage` |
| Shadcn CLI (`npx shadcn@latest`) | Ferramenta de build, não runtime | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `useApiKey`, `api-client` (parsing de `ApiError`) | `hooks/useApiKey.test.ts`, `lib/api-client.test.ts` | Vitest + jsdom | Casos de borda de persistência/erro |
| Integration (componente) | Páginas `/simulador` e `/consulta`, `lib/api-client` mockado | `app/simulador/page.test.tsx`, `app/consulta/page.test.tsx` | Vitest + Testing Library | AT-001, AT-002, AT-003 |
| E2E | `next dev` real + requisição manual contra o backend real (`api/`) | Manual | - | Happy path, verificação visual |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `ApiError` com `status=401` | `ErrorBanner` exibe "API key inválida ou ausente — configure-a acima" | No |
| `ApiError` com `status=422` | `ErrorBanner` exibe o `detail` retornado pelo backend (ex.: mensagem de `AliquotaNaoDisponivelError`) | No |
| Falha de rede (backend fora do ar) | `ErrorBanner` genérico — "Não foi possível conectar à API" | No (usuário reenviaria manualmente) |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `NEXT_PUBLIC_API_BASE_URL` | string | `http://localhost:8000` | URL base da API FastAPI |

---

## Security Considerations

- API key fica em `localStorage` em texto plano — mesma limitação já documentada no backend (`API_HTTP_SIMULACAO`); não usar além de MVP/demo interno
- Nenhum dado de PII é processado no frontend além do que o próprio usuário digita no campo de texto livre — a máscara de PII já acontece no backend (`orquestracao/nos/classificador.py`)
- `NEXT_PUBLIC_*` env vars são expostas no bundle do cliente — nunca colocar a API key ou segredos nelas, só a URL base (pública por natureza)

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Não implementado nesta feature — erros aparecem na UI via `ErrorBanner`, não há telemetria |
| Metrics | N/A |
| Tracing | N/A |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-23 | design-agent | Versão inicial, a partir de DEFINE_FRONTEND_SIMULADOR.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_FRONTEND_SIMULADOR.md`
