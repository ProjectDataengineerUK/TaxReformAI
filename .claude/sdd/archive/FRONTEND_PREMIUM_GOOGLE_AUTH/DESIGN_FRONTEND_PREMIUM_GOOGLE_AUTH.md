# DESIGN: FRONTEND_PREMIUM_GOOGLE_AUTH

> Arquitetura e especificação técnica para o gate de acesso via Google (Auth.js v5) e o redesign visual premium do frontend

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_PREMIUM_GOOGLE_AUTH |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
Navegador
   │
   │ 1. GET /simulador (sem sessão)
   ▼
┌─────────────────────────────────────────────────────────┐
│  Cloud Run: taxreformai-frontend (Next.js standalone)     │
│                                                             │
│  middleware.ts (roda em TODA rota, edge runtime)           │
│    matcher exclui: "/", "/login", "/api/auth/*", estáticos │
│    ├─ sem sessão válida → redirect 302 → /login             │
│    └─ com sessão válida → segue para a rota                 │
│                                                             │
│  /login (público)                                           │
│    └─ botão "Entrar com Google" → signIn("google")          │
│         │                                                    │
│         ▼                                                    │
│  /api/auth/[...nextauth] (Auth.js route handler, público)    │
│    ├─ redireciona pro OAuth consent do Google                │
│    ├─ callback do Google volta aqui                          │
│    ├─ callback signIn(): e-mail está em ALLOWED_EMAILS?      │
│    │     não → nega login (sem cookie, sem sessão)            │
│    │     sim → cria JWT de sessão (cookie httpOnly)           │
│    └─ redireciona pra rota original (ou /simulador)           │
│                                                             │
│  / (landing, público) → /simulador, /consulta (protegidas)  │
│    todas seguem chamando api/ com X-API-Key, SEM MUDANÇA     │
└─────────────────────────────────────────────────────────┘
                       │
                       │ X-API-Key (inalterado)
                       ▼
              Cloud Run: taxreformai-api (SEM MUDANÇA)
```

**Fronteira dura:** nada abaixo da linha "chamando `api/` com `X-API-Key`" muda. O login do
Google só decide se o navegador consegue RENDERIZAR a página que faz essa chamada — a chamada em
si continua idêntica ao que já existe hoje.

---

## Components

| Component | Responsibility |
|-----------|-----------------|
| `frontend/lib/auth.ts` | Configuração central do Auth.js v5 — provider Google, estratégia JWT, callback `signIn` que aplica a allowlist |
| `frontend/lib/auth-allowlist.ts` | Função pura `isEmailAllowed(email, allowlistEnv)` — parseia `ALLOWED_EMAILS` e compara sem diferenciar maiúsculas/minúsculas |
| `frontend/app/api/auth/[...nextauth]/route.ts` | Route handler do Auth.js (`GET`/`POST`) — todo o fluxo OAuth passa por aqui |
| `frontend/middleware.ts` | Gate de acesso — roda antes de qualquer rota protegida, redireciona para `/login` sem sessão |
| `frontend/app/login/page.tsx` | Página de login pública, único botão "Entrar com Google" |
| `frontend/components/SignOutButton.tsx` | Botão de logout, client component, chama `signOut()` |
| `frontend/app/page.tsx` | Landing page pública nova — apresentação do produto, CTA para `/login` |
| `frontend/app/layout.tsx` | Layout raiz redesenhado — nav com sessão, dark mode, `SessionProvider` |
| Redesign visual (`globals.css`, `tailwind.config.ts`, `components/ui/*`, `/simulador`, `/consulta`) | Paleta dark-mode-first nova, sem mudar a lógica de nenhuma tela |

---

## Decisions (Inline ADRs)

### Decision: Auth.js v5 (`next-auth@beta`), não v4

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** DEFINE marcou a compatibilidade do Auth.js v5 com Next.js 14.2 App Router como
assunção a validar (A-002) antes do build.

**Choice:** Usar `next-auth@beta` (Auth.js v5), que declara `next: "^14.2 || ^15"` como peer
dependency e foi desenhado nativamente para o App Router (route handler único, `middleware.ts`
com `auth()`, Server Components). A v4 exige um wrapper adicional (`getServerSession`) menos
natural no App Router.

**Rationale:** O projeto já está no App Router (Next.js 14.2.15) — v5 é o caminho reto, sem
adaptador. A resolução exata da versão beta é confirmada no `/build` via `npm install` real
(critério de sucesso do DEFINE, "`npm run build` passa sem erros").

**Alternatives Rejected:**
1. NextAuth v4 — exigiria padrão mais antigo (`getServerSession` em cada rota em vez de
   middleware central), mais código repetido.
2. Rolar OAuth manualmente (sem biblioteca) — reimplementaria PKCE/state/cookie assinado, risco
   de segurança desnecessário para um problema já resolvido por uma biblioteca madura.

**Consequences:**
- Depende de uma API ainda em beta (Auth.js v5) — mitigado por fixar a versão exata no
  `package.json` (sem `^` solto na major), não `latest`.

---

### Decision: Allowlist verificada no callback `signIn`, não no middleware

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Um e-mail Google fora da lista não pode ganhar sessão, mesmo com login Google
válido (AT-002 do DEFINE).

**Choice:** A checagem contra `ALLOWED_EMAILS` acontece dentro do callback `signIn(user, account,
profile)` do Auth.js, que roda ANTES de qualquer cookie/JWT ser emitido. Retornar `false` ali
recusa o login por completo — o usuário nunca chega a ter uma sessão para o middleware barrar
depois.

**Rationale:** Verificar no middleware DEPOIS de já existir uma sessão válida deixaria uma janela
onde um e-mail não autorizado teria, tecnicamente, uma sessão criada (só não conseguiria navegar)
— pior postura de segurança e mais superfície para bug. Recusar na origem é mais simples E mais
seguro.

**Alternatives Rejected:**
1. Checar no middleware — sessão chega a ser criada para e-mails não autorizados, só é barrada
   depois.

**Consequences:**
- A lógica de allowlist fica isolada em `lib/auth-allowlist.ts`, testável com `vitest` puro, sem
  precisar simular OAuth inteiro.

---

### Decision: `AUTH_TRUST_HOST=true` obrigatório no Cloud Run

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** O Cloud Run termina TLS na borda e repassa a requisição via `X-Forwarded-*` — o
Auth.js, por padrão, desconfia do host informado pela requisição (proteção contra host header
injection) e recusa gerar URLs de callback corretas nesse cenário.

**Choice:** Definir `AUTH_TRUST_HOST=true` como env var de runtime do serviço
`taxreformai-frontend`, confiando explicitamente no host que o Cloud Run informa.

**Rationale:** Mesma classe de achado real já visto neste projeto com o Cloud Run (delimitador de
`--set-env-vars`, memória compartilhada) — antecipar aqui em vez de descobrir só depois do 1º
deploy real.

**Alternatives Rejected:**
1. Fixar `AUTH_URL` com a URL exata do Cloud Run — funciona, mas quebra silenciosamente se a URL
   mudar (ex.: troca de domínio customizado no futuro); `AUTH_TRUST_HOST` é mais robusto.

**Consequences:**
- Nenhum recurso Terraform novo — é só mais uma env var no mesmo padrão de
  `NEXT_PUBLIC_API_BASE_URL`/`FRONTEND_ORIGINS` já existentes em `deploy.yml`.

---

### Decision: Redesign visual em cima da stack existente (Tailwind + shadcn-style), sem trocar base tecnológica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** BRAINSTORM já descartou trocar a stack — objetivo é elevar o visual, não reescrever
o frontend.

**Choice:** Paleta dark-mode-first via CSS custom properties em `globals.css` (mesmo mecanismo já
usado hoje para `--border`/`--background`/`--foreground`, só com valores novos + paleta de
destaque), Tailwind `darkMode: "class"` fixando `<html class="dark">` (dark-mode-first, sem
depender de preferência do SO), e os componentes `components/ui/*` recebem novos tokens de cor —
zero biblioteca de UI nova.

**Rationale:** Menor risco — a lógica de `/simulador` e `/consulta` (chamadas à API, formulários,
markdown) não muda uma linha; só a camada visual.

**Alternatives Rejected:**
1. Migrar para uma lib de componentes completa (ex.: shadcn/ui via CLI, Radix) — mudança maior de
   superfície sem necessidade real, os componentes atuais já seguem o padrão shadcn manualmente.

**Consequences:**
- Paleta e tipografia são propostas nesta sessão de design (sem marca pré-existente a seguir).

---

## Visual Direction (paleta proposta)

Referência: Linear/Stripe Dashboard/Vercel — fundo quase-preto, um acento saturado só, hierarquia
por contraste de texto, bordas sutis (1px, baixo contraste).

| Token CSS | Valor (HSL) | Uso |
|-----------|-------------|-----|
| `--background` | `224 24% 8%` | Fundo da aplicação (quase-preto azulado) |
| `--surface` | `222 22% 12%` | Cards, painéis |
| `--foreground` | `210 20% 96%` | Texto principal |
| `--muted-foreground` | `215 14% 62%` | Texto secundário |
| `--border` | `222 16% 20%` | Bordas de card/input |
| `--accent` | `160 84% 45%` | Cor de destaque única (verde-esmeralda — remete a "fiscal/financeiro", distinto do azul genérico de SaaS) |
| `--accent-foreground` | `224 24% 8%` | Texto sobre o accent |
| `--destructive` | `0 72% 55%` | Erros (`ErrorBanner`) |

Tipografia: manter a stack de sistema atual (sem custom font — evita mais uma dependência/CDN),
mas aumentar a escala de peso/tamanho no título da landing (`text-5xl font-bold tracking-tight`).

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|---------------|
| 1 | `frontend/package.json` | Modify | Adiciona `next-auth@beta` (versão fixa) | None |
| 2 | `frontend/lib/auth-allowlist.ts` | Create | `isEmailAllowed(email, allowlistEnv)` pura, testável | None |
| 3 | `frontend/lib/auth.ts` | Create | `NextAuth()` — provider Google, JWT, callback `signIn` usando (2) | 1, 2 |
| 4 | `frontend/app/api/auth/[...nextauth]/route.ts` | Create | Exporta `GET`/`POST` de (3) | 3 |
| 5 | `frontend/middleware.ts` | Create | `auth()` como middleware + matcher excluindo rotas públicas | 3 |
| 6 | `frontend/app/login/page.tsx` | Create | Página pública, botão "Entrar com Google" | 3, visual |
| 7 | `frontend/components/SignOutButton.tsx` | Create | Client component, `signOut()` | 3 |
| 8 | `frontend/app/globals.css` | Modify | Paleta dark-mode-first (tokens da tabela acima) | None |
| 9 | `frontend/tailwind.config.ts` | Modify | `darkMode: "class"`, novos tokens de cor | 8 |
| 10 | `frontend/app/layout.tsx` | Modify | `<html class="dark">`, `SessionProvider`, nav redesenhada com `SignOutButton` | 7, 8, 9 |
| 11 | `frontend/app/page.tsx` | Modify | Vira a landing page pública (marketing + CTA) | 8, 9 |
| 12 | `frontend/components/ui/button.tsx` | Modify | Variantes usando os novos tokens (`accent`) | 8, 9 |
| 13 | `frontend/components/ui/card.tsx` | Modify | Usa `--surface`/`--border` novos | 8, 9 |
| 14 | `frontend/app/simulador/page.tsx` | Modify | Só classes visuais — zero mudança de lógica | 8, 9 |
| 15 | `frontend/app/consulta/page.tsx` | Modify | Só classes visuais — zero mudança de lógica | 8, 9 |
| 16 | `frontend/components/ApiKeyBar.tsx` | Modify | Ajuste visual (fundo dark) | 8, 9 |
| 17 | `frontend/lib/auth-allowlist.test.ts` | Create | Testes `vitest` da allowlist | 2 |
| 18 | `.env.example` | Modify | Documenta `AUTH_SECRET`/`AUTH_GOOGLE_ID`/`AUTH_GOOGLE_SECRET`/`ALLOWED_EMAILS`/`AUTH_TRUST_HOST` | None |
| 19 | `.github/workflows/deploy.yml` | Modify | `--set-env-vars` no deploy do frontend, lendo os novos GitHub Secrets | None |

---

## Code Patterns

### `frontend/lib/auth-allowlist.ts`

```ts
export function isEmailAllowed(email: string | null | undefined, allowlistEnv: string | undefined): boolean {
  if (!email || !allowlistEnv) return false;
  const allowed = allowlistEnv
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);
  return allowed.includes(email.toLowerCase());
}
```

`ALLOWED_EMAILS` é CSV simples (mesmo espírito de `API_KEYS`, mas sem precisar de JSON — aqui é
só uma lista, não um mapa chave→valor).

### `frontend/lib/auth.ts`

```ts
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { isEmailAllowed } from "./auth-allowlist";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  callbacks: {
    async signIn({ user }) {
      return isEmailAllowed(user.email, process.env.ALLOWED_EMAILS);
    },
  },
});
```

### `frontend/app/api/auth/[...nextauth]/route.ts`

```ts
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
```

### `frontend/middleware.ts`

```ts
export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: ["/((?!api/auth|login|_next/static|_next/image|favicon.ico|$).*)"],
};
```

O padrão `|$` no matcher exclui explicitamente a rota raiz (`/`), que é a landing pública.

### `frontend/app/login/page.tsx` (esqueleto)

```tsx
import { signIn } from "@/lib/auth";

export default function LoginPage() {
  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <form
        action={async () => {
          "use server";
          await signIn("google", { redirectTo: "/simulador" });
        }}
      >
        <button type="submit" className="...">Entrar com Google</button>
      </form>
    </div>
  );
}
```

---

## Environment Variables (novas)

| Variável | Onde vive | Exemplo/local | Produção |
|----------|-----------|----------------|----------|
| `AUTH_SECRET` | Runtime, Cloud Run frontend | valor fictício local | GitHub Secret `AUTH_SECRET` — gerado pelo usuário (`openssl rand -base64 32`), nunca pelo agente |
| `AUTH_GOOGLE_ID` | Runtime, Cloud Run frontend | valor fictício local | GitHub Secret `GOOGLE_OAUTH_CLIENT_ID` — criado manualmente pelo usuário no Google Cloud Console |
| `AUTH_GOOGLE_SECRET` | Runtime, Cloud Run frontend | valor fictício local | GitHub Secret `GOOGLE_OAUTH_CLIENT_SECRET` — idem |
| `ALLOWED_EMAILS` | Runtime, Cloud Run frontend | `dev@local.test` | GitHub Secret `ALLOWED_EMAILS` — CSV de e-mails reais |
| `AUTH_TRUST_HOST` | Runtime, Cloud Run frontend | `true` | `true` (fixo, não é segredo) |

`AUTH_GOOGLE_ID`/`AUTH_GOOGLE_SECRET` seguem a convenção de autodetecção de provider do Auth.js v5
(`AUTH_<PROVIDER_EM_MAIÚSCULO>_ID`/`_SECRET`) — não precisam ser passados explicitamente pro
`Google()` no código.

**Credenciais que o agente NUNCA cria:** `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` (Google Cloud
Console) e `AUTH_SECRET` (valor aleatório) são criados pelo usuário e cadastrados manualmente nos
GitHub Secrets — mesma disciplina já estabelecida para toda credencial deste projeto.

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `isEmailAllowed` — case-insensitive, CSV com espaços, e-mail ausente, allowlist ausente | `vitest` |
| Unit (existentes) | `/simulador`, `/consulta`, `useApiKey`, `api-client` — garantir que o redesign visual não quebra nenhum teste existente | `vitest` (já existentes, rodar de novo) |
| Manual/Real | Fluxo OAuth completo (login com e-mail permitido, login recusado com e-mail fora da lista, logout, sessão expirada) | Só é testável de verdade contra o Google real, depois do deploy — igual a outras features deste projeto que dependem de infraestrutura real (Vertex AI, Cloud Tasks) |
| Build | `npm run build` do frontend | Confirma Auth.js v5 compila com Next.js 14.2 (valida A-002 do DEFINE) |

**Nota:** o fluxo OAuth real não é testável localmente sem credenciais Google reais — a
verificação end-to-end (AT-001 a AT-005) acontece contra o serviço deployado, mesma disciplina já
usada para toda feature que depende de um provedor externo real neste projeto.

---

## Quality Gate

```text
[x] Arquitetura clara (diagrama ASCII)
[x] Decisões documentadas com rationale (4 ADRs inline)
[x] File manifest completo (19 arquivos)
[x] Padrões de código prontos para copiar
[x] Estratégia de teste cobre os requisitos do DEFINE
[x] Sem dependência circular
```

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_FRONTEND_PREMIUM_GOOGLE_AUTH.md`
