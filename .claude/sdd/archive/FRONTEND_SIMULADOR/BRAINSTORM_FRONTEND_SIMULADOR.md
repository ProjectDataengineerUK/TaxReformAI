# BRAINSTORM: Frontend Next.js — Simulador Tributário

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_SIMULADOR |
| **Date** | 2026-07-23 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Depois de shipar `API_HTTP_SIMULACAO`, o usuário escolheu como próximo passo construir o frontend Next.js consumindo a API já existente, e pediu explicitamente para "deixar tudo montado" — priorizar entrega completa em vez de uma sequência longa de perguntas de escopo.

**Context Gathered:**
- `contexto.md` (seção 5.2) já define a stack: Next.js 14 (App Router) + TailwindCSS + Shadcn UI + TanStack Query.
- `contexto.md` (seção 9) associa recursos diferentes a cada plano (Professional/Business/Enterprise) — mas não há autenticação de usuário nem billing real no projeto ainda, só a API key simples de `API_HTTP_SIMULACAO`.
- A API já expõe dois casos de uso genuinamente diferentes: `/v1/tax/simulate` (estruturado, lista de itens NCM/quantidade/valor) e `/v1/tax/query` (conversacional, pergunta em texto livre).
- `node`/`npm` disponíveis neste sandbox (v22.22.1 / 9.2.0), com acesso real ao registro do npm — sem os blockers de dependência das features de ingestão/orquestração.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo diretório `frontend/` na raiz, paralelo a `api/`, `ingestion/`, `motor_calculo/`, `orquestracao/` | Quinto componente do projeto |
| Relevant KB Domains | typescript-reviewer, a11y-architect (Shadcn/Tailwind já tem boas bases de acessibilidade) | Padrões a consultar no /design |
| IaC Impact | Nenhum — roda local via `next dev`, sem deploy real nesta fase | |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | UI única sem gating por plano, cobrindo os dois endpoints, ou algo mais específico? | Usuário pediu para "deixar tudo montado" — interpretado como: construir uma UI funcional completa cobrindo ambos os endpoints, sem replicar o gating de planos (que exigiria auth/billing reais, fora de escopo) | Decisão tomada diretamente em vez de expandir em mais perguntas de escopo |

**Nota sobre o processo:** dado o pedido explícito do usuário para não alongar o ciclo de perguntas, as decisões de escopo abaixo foram tomadas diretamente pelo Claude, documentadas como decisões técnicas (não perguntas), seguindo o padrão já estabelecido nas features anteriores quando o usuário delega o julgamento técnico.

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Related code | `api/schemas_simulate.py`, `api/schemas_query.py` | 2 | Contratos de request/response já existentes — o frontend usa esses schemas como fonte de verdade para os formulários e tipos TypeScript |
| Output examples | Respostas reais capturadas durante o build de `API_HTTP_SIMULACAO` (`resumo_financeiro`, `parecer_final`, `historico`) | 2 | Usadas para desenhar os componentes de exibição de resultado |

---

## Approaches Explored

### Approach A: Duas páginas funcionais (estruturada + conversacional), API key via input local, sem autenticação real ⭐ Recomendada

**Description:** `frontend/` com Next.js 14 (App Router) + TailwindCSS + Shadcn UI + TanStack Query. Duas rotas principais: `/simulador` (formulário estruturado — lista de itens NCM/quantidade/valor, chama `/v1/tax/simulate`) e `/consulta` (pergunta em texto livre, chama `/v1/tax/query`). Um componente de configuração da API key (salva em `localStorage`, enviada como header `X-API-Key` em todas as chamadas via um client HTTP compartilhado).

**Pros:**
- Cobre os dois casos de uso reais da API já construída
- Não inventa autenticação/billing que não existem — usa o mecanismo real (API key) já implementado no backend
- Testável de ponta a ponta (Next.js roda localmente, sem blockers de dependência)

**Cons:**
- Sem gating de planos — qualquer usuário com uma API key vê as duas funcionalidades, independente do "plano" (mas não há planos reais implementados mesmo, então isso é consistente com o resto do projeto)

**Why Recommended:** É a única abordagem que reflete o que a API genuinamente oferece hoje, sem fingir ter infraestrutura de auth/billing que ainda não existe.

---

### Approach B: Replicar a segmentação de planos (Professional/Business/Enterprise) com telas diferentes por "plano"

**Description:** Construir três experiências de UI diferentes, simulando os recursos de cada plano da seção 9.

**Pros:**
- Mais fiel à visão de produto final

**Cons:**
- Exigiria simular autenticação/autorização por plano que não existe — inventaria uma camada de produto sobre uma API que não tem esse conceito, quebrando a mesma disciplina de "não fabricar o que não é real" mantida em todas as features anteriores

---

### Approach C: Só a página conversacional (mais alinhada ao "diferencial de IA" do produto), adiar o formulário estruturado

**Description:** Construir só `/consulta`, já que é o caso de uso mais distintivo do produto (RAG + IA).

**Pros:**
- Menor escopo

**Cons:**
- Usuário pediu para "deixar tudo montado" — cortar o endpoint estruturado contradiria isso, e ele já está pronto e testado no backend

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Duas páginas funcionais, API key via input local |
| **User Confirmation** | Pendente — apresentado nesta sessão para validação final antes do /define |
| **Reasoning** | Reflete a API real sem inventar infraestrutura de auth/billing inexistente |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Duas rotas (`/simulador` estruturado, `/consulta` conversacional), sem gating por plano | Reflete os dois endpoints reais da API; gating por plano exigiria auth/billing que não existem | Approach B (telas por plano) — rejeitada, fabricaria infraestrutura inexistente |
| 2 | API key configurada via input simples, salva em `localStorage` | Espelha o mecanismo de auth real do backend (`X-API-Key`), sem simular login | Login/sessão simulados — rejeitado, inventaria um sistema de usuários que não existe |
| 3 | Stack exatamente como a seção 5.2 do blueprint já define (Next.js 14 App Router + Tailwind + Shadcn + TanStack Query) | Já é uma decisão de arquitetura tomada no blueprint, não uma escolha em aberto | N/A — não há alternativa a explorar aqui |
| 4 | Tipos TypeScript e formulários derivados diretamente dos schemas Pydantic já existentes (`api/schemas_simulate.py`/`schemas_query.py`) | Evita desalinhamento entre o contrato real da API e o que o frontend espera | Inventar um contrato novo no frontend sem checar contra o backend real — rejeitado, é exatamente o tipo de erro que os testes das features anteriores evitaram |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Autenticação real de usuário (login/senha) | Não existe backend para isso (sem Postgres/tenant real) | Sim, quando o schema de usuários existir |
| Gating de UI por plano (Professional/Business/Enterprise) | Não há conceito de "plano do usuário logado" sem autenticação real | Sim, junto com a autenticação |
| Upload de planilha de SKUs em lote (recurso do plano Business) | Depende do endpoint assíncrono (Celery/Redis) já descartado em features anteriores | Sim, quando essa API existir |
| Deploy real (Vercel/Cloud Run) | Fora de escopo — só `next dev` local nesta fase | Sim |
| Dark mode / customização visual avançada | Não é um requisito funcional — Shadcn já vem com bom padrão visual default | Sim, se necessário |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Escopo (UI única, sem gating de plano) | ✅ | Usuário pediu "deixa tudo montado" — decisão tomada diretamente pelo Claude, a confirmar nesta mensagem | Pendente confirmação final |

**Minimum Validations:** 1 de 2 — a segunda validação é a confirmação desta síntese antes do `/define`, pedida explicitamente abaixo.

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O sistema precisa de uma interface web que permita a um usuário configurar sua API key e usar os dois modos de simulação tributária já expostos pela API (estruturado e conversacional) — hoje esses recursos só são acessíveis via chamadas HTTP diretas (`curl`/Postman), sem nenhuma UI.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Head de Tax / Controller (usuário do produto) | Precisa simular tributos sem escrever requisições HTTP manualmente |
| CFO (usuário do produto) | Precisa fazer perguntas em linguagem natural e ler o parecer, sem lidar com JSON bruto |

### Success Criteria (Draft)
- [ ] Usuário consegue configurar a API key uma vez e ela persiste entre sessões (via `localStorage`)
- [ ] Formulário estruturado (`/simulador`) permite adicionar/remover itens e envia para `/v1/tax/simulate`, exibindo `resumo_financeiro` e `itens_detalhados`
- [ ] Página conversacional (`/consulta`) envia para `/v1/tax/query` e exibe `parecer_final` (renderizado como Markdown) + histórico auditável
- [ ] Erros da API (401 sem key válida, 422 sem alíquota confirmada) são exibidos de forma clara na UI, não como uma tela quebrada

### Constraints Identified
- Sem autenticação real de usuário — só API key manual
- Sem gating de planos
- Backend já validado (`api/`) — o frontend não deve reimplementar nenhuma lógica de cálculo, só consumir a API

### Out of Scope (Confirmed)
- Autenticação real de usuário / billing
- Gating de UI por plano
- Upload de planilha em lote
- Deploy real
- Design visual customizado além do padrão Shadcn

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 1 (mais decisões tomadas diretamente a pedido do usuário) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 1 de 2 (pendente confirmação final) |
| Duration | 1 sessão de diálogo |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_FRONTEND_SIMULADOR.md` (após confirmação da síntese acima)
