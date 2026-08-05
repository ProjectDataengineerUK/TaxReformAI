# BRAINSTORM: FRONTEND_PREMIUM_GOOGLE_AUTH

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_PREMIUM_GOOGLE_AUTH |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Approaches Identified — Ready for Define |

---

## Initial Idea

**Raw Input:** Iniciativa nova, pedida diretamente pelo usuário (não é uma posição do
`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`): modernizar o visual do frontend para algo "premium" e
adicionar acesso restrito via login com Gmail/Google.

**Context Gathered:**
- Hoje NÃO existe autenticação de usuário no frontend — qualquer um acessa a UI livremente. A
  única "chave" é um campo de texto manual (`ApiKeyBar.tsx`) que grava a API key em
  `localStorage` (`useApiKey.ts`) e vira o header `X-API-Key` nas chamadas ao backend — isso é
  autenticação de TENANT/API, não de pessoa.
- Stack atual: Next.js 14.2 (App Router), React 18, Tailwind 3.4, componentes shadcn-style
  próprios em `components/ui/` (button, card, input, label, textarea), TanStack Query,
  react-markdown. Nenhuma dependência de auth, nenhuma animação, sem dark mode.
- Duas páginas hoje: `/simulador` (formulário estruturado) e `/consulta` (conversacional). Nenhuma
  landing page pública.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `frontend/app/` (novas rotas), `frontend/middleware.ts` (novo), `frontend/lib/auth.ts` (novo) | Tudo dentro de `frontend/`, nenhuma mudança em `api/` |
| Relevant KB Domains | N/A | Não é feature de IA/LLM |
| IaC Impact | Nenhum recurso GCP novo — Google OAuth Client ID/Secret é configurado no Google Cloud Console (console do MESMO projeto `taxreformai-dev`), não via Terraform | Credencial manual, mesma disciplina já estabelecida (usuário cria, nunca o agente) |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Login do Google substitui a API key ou só controla quem vê a UI? | Só controla quem VÊ a UI | Escopo fica restrito ao frontend — zero mudança no backend |
| 2 | Quem pode entrar: lista de e-mails ou domínio Workspace inteiro? | Lista específica de e-mails | Allowlist em variável de ambiente, mesmo padrão de `API_KEYS` |
| 3 | Direção visual do redesign | Dark-mode-first, "SaaS financeiro premium" (Linear/Stripe/Vercel) | Define a paleta e a linguagem visual a propor no `/design` |
| 4 | Escopo do redesign: só as 2 telas existentes, ou mais? | Inclui landing page de apresentação | Uma página pública nova, antes do login |
| 5 | Existe marca/paleta já definida? | Não, criar do zero | `/design` propõe uma paleta nova, coerente com o posicionamento B2B Enterprise |

**Minimum Questions:** 3 — atendido (5 perguntas).

---

## Sample Data Inventory

> Não é feature de IA/LLM — não há amostras de treinamento envolvidas. O usuário confirmou não
> ter marca/paleta pré-existente, então também não há referência visual de marca a seguir; o
> `/design` propõe uma identidade nova a partir de referências de mercado (Linear, Stripe
> Dashboard, Vercel), citadas pelo próprio usuário como direção.

---

## Approaches Explored

### Approach A: Auth.js (NextAuth v5) + Google, gate via middleware ⭐ Recomendado

**Description:** `Auth.js` (a evolução do NextAuth, com suporte nativo ao App Router do Next.js
14) com provider Google. Sessão via JWT — sem tabela nova no Postgres, sem adapter de banco. Um
`middleware.ts` intercepta toda rota protegida e redireciona para `/login` se não houver sessão
válida. Lista de e-mails permitidos numa variável de ambiente (JSON ou CSV), verificada no
callback `signIn` do Auth.js — um e-mail fora da lista tem o login recusado mesmo com uma conta
Google válida.

**Pros:**
- Zero mudança no backend — o modelo de API key continua exatamente como está.
- Zero infraestrutura nova além de um OAuth Client ID/Secret no Google Cloud Console (nenhum
  recurso Terraform, nenhum banco novo).
- `middleware.ts` protege TODAS as rotas de uma vez, num só lugar — não precisa lembrar de
  proteger cada página individualmente.

**Cons:**
- Sessão JWT expira e precisa de configuração explícita de duração — decisão a tomar no `/design`.
- O usuário precisa criar manualmente as credenciais OAuth no Google Cloud Console (passo humano,
  não automatizável por mim).

**Why Recommended:** Resolve o problema real (acesso restrito) com a menor superfície de mudança
possível — não introduz um sistema de usuários completo, não toca no backend, não duplica a
autenticação que já existe para a API.

---

### Approach B: Firebase Authentication + Google

**Description:** Usar o Firebase Authentication (produto separado do Google, precisa de um
projeto Firebase próprio) como provedor de login, com o Google como método.

**Pros:**
- Interface pronta de gerenciamento de usuários no Console do Firebase.

**Cons:**
- Introduz um produto GCP-adjacente NOVO e separado (projeto Firebase), com sua própria conta/
  faturamento — mais uma peça de infraestrutura para gerenciar sem necessidade real, quando
  Auth.js resolve o mesmo problema sem ela.
- Redundante: o objetivo é só "restringir quem vê a UI por e-mail", não gerenciar um sistema de
  usuários completo com Firestore etc.

**Why Rejected:** Complexidade desproporcional ao problema — mesma lógica de YAGNI já aplicada
repetidamente neste projeto (preferir o caminho mais simples que resolve o problema real).

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Auth.js + Google, gate via middleware |
| **User Confirmation** | 2026-08-04, confirmado explicitamente após apresentação consolidada |
| **Reasoning** | Resolve o problema real com a menor superfície de mudança — sem tocar no backend, sem infraestrutura nova além de uma credencial OAuth |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Login do Google só controla acesso à UI, não substitui a API key | Escopo mínimo — resolve "acesso restrito" sem exigir mudança no backend | Login substituindo a API key por completo |
| 2 | Auth.js (NextAuth v5), não Firebase Authentication | Resolve o mesmo problema sem introduzir um produto GCP novo e separado | Firebase Authentication |
| 3 | Lista de e-mails específicos em env var, não domínio Workspace | Mais simples de configurar agora, fácil de auditar | Restrição por domínio inteiro |
| 4 | Sessão JWT, sem adapter de banco | Sem tabela nova no Postgres — menos infraestrutura | Sessão em banco (database adapter) |
| 5 | Escopo inclui landing page nova, além do redesign das 2 páginas existentes | Decisão explícita do usuário — o produto ainda não tinha nenhuma página de apresentação pública | Redesign restrito só às 2 páginas existentes |
| 6 | Paleta/identidade visual nova, criada do zero | Usuário confirmou não ter marca pré-existente | Seguir uma marca já definida |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Login substituindo a API key (backend aprender a validar token Google) | Fora do escopo confirmado pelo usuário — resolve um problema diferente do pedido | Sim, se a necessidade de autenticação por usuário (não por tenant) surgir de verdade |
| Firebase Authentication | Redundante com Auth.js para o problema real | Não avaliado como necessário |
| Restrição por domínio Google Workspace | Usuário escolheu lista de e-mails para começar | Sim, é uma troca de configuração simples no Auth.js depois |
| Sistema de gerenciamento de usuários (CRUD de quem tem acesso via UI) | Não pedido — a lista de e-mails em env var já resolve o caso de uso real | Sim, se o número de pessoas com acesso crescer muito |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Login vs. API key | ✅ | Confirmou "só controla quem vê a UI" | Não |
| Quem tem acesso + direção visual + escopo + marca | ✅ | Confirmou lista de e-mails, dark-mode-first, landing page nova, sem marca pré-existente | Não |
| Abordagem consolidada (Auth.js + Google + redesign) | ✅ | "Sim, seguir com essa abordagem" | Não |

**Minimum Validations:** 2 — atendido (3 validações).

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O frontend não tem nenhum controle de acesso por pessoa (qualquer um vê a UI) e o visual atual é
funcional mas não transmite a seriedade/qualidade esperada de um produto SaaS B2B Enterprise para
departamentos fiscais, controllers e CFOs.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Time interno/parceiros com acesso autorizado | Precisa logar com uma conta Google já confiável, sem criar mais uma senha |
| Qualquer visitante não autorizado | Hoje consegue ver a UI inteira sem nenhuma barreira |

### Success Criteria (Draft)
- [ ] Qualquer rota do frontend (exceto a landing page pública e `/login`) exige sessão válida do
      Google, real, verificado
- [ ] Um e-mail Google fora da lista permitida tem o login recusado, mesmo com conta válida
- [ ] Landing page, `/login`, `/simulador` e `/consulta` redesenhadas com a nova identidade visual
      (dark-mode-first)
- [ ] Nenhuma mudança no backend (`api/`) — o modelo de API key continua funcionando exatamente
      como está

### Constraints Identified
- Zero mudança em `api/` — só `frontend/`
- Credenciais OAuth do Google criadas manualmente pelo usuário, nunca pelo agente
- Sessão JWT, sem tabela nova no Postgres

### Out of Scope (Confirmed)
- Login substituindo a API key
- Firebase Authentication
- Restrição por domínio Google Workspace (fica para o futuro, se necessário)
- Sistema de gerenciamento de usuários via UI

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 3 |
| Duration | ~30min |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_FRONTEND_PREMIUM_GOOGLE_AUTH.md`
