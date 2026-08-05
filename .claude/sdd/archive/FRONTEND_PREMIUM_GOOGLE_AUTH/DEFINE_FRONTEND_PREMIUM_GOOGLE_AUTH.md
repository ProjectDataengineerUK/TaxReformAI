# DEFINE: FRONTEND_PREMIUM_GOOGLE_AUTH

> Restringir o acesso ao frontend a uma lista de e-mails Google via Auth.js e redesenhar a UI com uma identidade visual premium dark-mode-first

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_PREMIUM_GOOGLE_AUTH |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## Problem Statement

O frontend do TaxReformAI (`frontend/`) não tem nenhum controle de acesso por pessoa — qualquer
um com a URL pública vê a UI inteira, sem login. Além disso, o visual atual é funcional mas
genérico (Tailwind puro, sem dark mode, sem identidade visual), o que não transmite a seriedade
esperada por um produto SaaS B2B Enterprise vendido a departamentos fiscais, controllers e CFOs.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Time interno/parceiros autorizados | Usam o simulador e o modo conversacional para testar/demonstrar o produto | Hoje não têm nenhuma barreira de acesso pessoal — qualquer link vazado expõe a UI inteira a qualquer pessoa |
| Visitante não autorizado | N/A (não deveria ter acesso) | Hoje consegue ver e usar a UI completa sem nenhuma credencial pessoal |
| Prospect/lead (visitante da landing page) | Avalia o produto antes de pedir acesso | Hoje não existe nenhuma página de apresentação pública — só as telas internas |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Toda rota da aplicação (exceto landing page pública e `/login`) exige sessão Google válida |
| **MUST** | Só e-mails da allowlist (variável de ambiente) completam o login com sucesso |
| **MUST** | Zero mudança em `api/` — o modelo de API key continua exatamente como está |
| **SHOULD** | Landing page pública nova, dark-mode-first, com a identidade visual premium |
| **SHOULD** | `/simulador` e `/consulta` redesenhadas com a mesma identidade visual |
| **COULD** | Página `/login` com a mesma linguagem visual da landing page |

---

## Success Criteria

- [ ] Acessar `/simulador` ou `/consulta` sem sessão redireciona para `/login` (100% das vezes, verificado real via `middleware.ts`)
- [ ] Login com um e-mail Google fora da allowlist é recusado (nunca autentica, mesmo com conta Google válida)
- [ ] Login com um e-mail da allowlist autentica com sucesso e mantém sessão entre navegações
- [ ] Landing page acessível sem login, em `/`
- [ ] Nenhum endpoint de `api/` modificado (confirmado por diff/revisão — zero linhas alteradas em `api/`)
- [ ] `npm run build` do frontend passa sem erros após o redesign

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Acesso sem sessão é bloqueado | Usuário sem sessão ativa | Acessa `/simulador` diretamente pela URL | É redirecionado para `/login` |
| AT-002 | E-mail fora da allowlist é recusado | Conta Google válida, e-mail NÃO está na allowlist | Completa o fluxo OAuth do Google | Login é recusado, usuário não ganha sessão |
| AT-003 | E-mail da allowlist entra com sucesso | Conta Google válida, e-mail ESTÁ na allowlist | Completa o fluxo OAuth do Google | Sessão criada, redirecionado para `/simulador` (ou página protegida original) |
| AT-004 | Landing page é pública | Usuário sem sessão | Acessa `/` | Landing page carrega normalmente, sem redirecionamento |
| AT-005 | Sessão expira | Sessão JWT expirada | Acessa qualquer rota protegida | Redirecionado para `/login` de novo |
| AT-006 | Backend não muda | Qualquer estado | Chamada direta a `api/v1/tax/simulate` com `X-API-Key` válida | Continua respondendo exatamente como hoje, sem exigir token Google |

---

## Out of Scope

- Login do Google substituindo a API key (backend continua validando só `X-API-Key`)
- Firebase Authentication (avaliado no `/brainstorm`, rejeitado por redundância)
- Restrição por domínio Google Workspace inteiro (só lista de e-mails específicos, por ora)
- Sistema de gerenciamento de usuários via UI (a allowlist é editada manualmente na env var)
- Qualquer mudança em `api/` (rotas, auth, schemas)
- Multi-idioma, app mobile

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Zero mudança em `api/` | Todo trabalho fica isolado em `frontend/` |
| Technical | Sessão JWT, sem tabela nova no Postgres | Sem adapter de banco no Auth.js |
| Process | Credenciais OAuth (Client ID/Secret) do Google Cloud Console são criadas manualmente pelo usuário | Mesma disciplina de credenciais já estabelecida no projeto — nunca geradas pelo agente |
| Design | Identidade visual criada do zero (sem marca pré-existente) | `/design` propõe paleta/tipografia nova |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `frontend/` (App Router: `app/`, `middleware.ts`, `lib/auth.ts`, `app/login/`, novas rotas de landing) | Nenhum arquivo fora de `frontend/` |
| **KB Domains** | N/A | Não é feature de dados/IA |
| **IaC Impact** | Nenhum recurso Terraform novo — só uma env var nova (`NEXTAUTH_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAILS`) no serviço Cloud Run do frontend, mesmo padrão de `NEXT_PUBLIC_API_BASE_URL`/`FRONTEND_ORIGINS` já existentes em `deploy.yml` | Requer atualizar `deploy.yml` para passar as novas env vars |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O usuário cria manualmente o OAuth Client ID/Secret no Google Cloud Console do projeto `taxreformai-dev` antes do deploy | Login não funciona em produção até a credencial existir | [ ] |
| A-002 | Auth.js v5 (`next-auth@beta`) é compatível com Next.js 14.2 App Router sem downgrade | Precisaria reavaliar biblioteca de auth | [ ] |
| A-003 | A lista de e-mails permitidos é pequena (dezenas, não milhares) | Uma env var JSON/CSV continua sendo prática | [ ] |

**Note:** A-002 deve ser validada no `/design` antes de comprometer a arquitetura.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro e específico: sem controle de acesso + visual genérico, ambos com impacto identificado |
| Users | 3 | 3 personas identificadas, cada uma com dor específica |
| Goals | 3 | Priorizados MUST/SHOULD/COULD, todos testáveis |
| Success | 3 | Critérios verificáveis, incluindo "zero mudança em `api/`" como critério negativo checável |
| Scope | 3 | Out of Scope explícito, herdado diretamente das decisões já validadas no `/brainstorm` |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15** — atendido.

---

## Open Questions

None - ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-04 | (sessão direta) | Versão inicial, extraída do BRAINSTORM já validado |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_FRONTEND_PREMIUM_GOOGLE_AUTH.md`
