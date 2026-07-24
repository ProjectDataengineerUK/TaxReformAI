# DEFINE: Frontend Next.js — Simulador Tributário

> Interface web (Next.js) que consome a API já existente (`/v1/tax/simulate` e `/v1/tax/query`), com configuração de API key via input local.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FRONTEND_SIMULADOR |
| **Date** | 2026-07-23 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O sistema precisa de uma interface web que permita a um usuário configurar sua API key e usar os dois modos de simulação tributária já expostos pela API (estruturado e conversacional) — hoje esses recursos só são acessíveis via chamadas HTTP diretas (`curl`/Postman), sem nenhuma UI.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Head de Tax / Controller | Usuário do produto | Precisa simular tributos por NCM/item sem escrever requisições HTTP manualmente |
| CFO | Usuário do produto | Precisa fazer perguntas em linguagem natural e ler o parecer, sem lidar com JSON bruto |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Componente de configuração de API key, persistida em `localStorage`, enviada como header `X-API-Key` em todas as chamadas |
| **MUST** | Página `/simulador` — formulário estruturado (adicionar/remover itens com NCM/quantidade/valor/UF origem-destino), envia para `/v1/tax/simulate`, exibe `resumo_financeiro` e `itens_detalhados` |
| **MUST** | Página `/consulta` — campo de texto livre + ano/valor, envia para `/v1/tax/query`, exibe `parecer_final` (Markdown) + histórico auditável |
| **MUST** | Erros da API (401, 422) exibidos como mensagem clara na UI, nunca como tela quebrada ou dado inventado |
| **SHOULD** | Tipos TypeScript derivados dos schemas Pydantic reais (`api/schemas_simulate.py`/`schemas_query.py`), não inventados |
| **COULD** | Navegação simples entre as duas páginas (layout compartilhado) |

---

## Success Criteria

- [ ] Usuário configura a API key uma vez e ela persiste entre reloads da página (via `localStorage`)
- [ ] Formulário `/simulador` permite adicionar/remover itens e exibe corretamente `resumo_financeiro`/`itens_detalhados` da resposta real da API
- [ ] Página `/consulta` exibe `parecer_final` renderizado como Markdown + histórico auditável
- [ ] Erro 401 (sem API key/key inválida) e 422 (alíquota não confirmada) aparecem como mensagens legíveis na UI, não como exceção não tratada

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path (estruturado) | API key válida configurada, 1 item preenchido no formulário | Usuário envia `/simulador` | UI exibe `resumo_financeiro` e `itens_detalhados` retornados pela API real |
| AT-002 | Error case (auth) | Nenhuma API key configurada | Usuário tenta enviar qualquer um dos dois formulários | UI exibe mensagem de erro clara referente ao 401, sem quebrar |
| AT-003 | Edge case (conversacional, alíquota indisponível) | Pergunta com `ano_operacao=2028` | Usuário envia `/consulta` | UI exibe o erro 422 da API de forma legível, sem inventar um parecer |

---

## Out of Scope

- Autenticação real de usuário (login/senha) / billing — só API key manual
- Gating de UI por plano (Professional/Business/Enterprise)
- Upload de planilha de SKUs em lote — depende de endpoint assíncrono não construído
- Deploy real (Vercel/Cloud Run) — só `next dev` local nesta fase
- Design visual customizado além do padrão do Shadcn UI

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Backend (`api/`) já validado e não deve ser modificado | Frontend só consome, não reimplementa lógica de cálculo |
| Technical | Sem autenticação real de usuário | API key manual via `localStorage` é o único mecanismo de auth do frontend |
| Scope | Sem gating de planos | Toda funcionalidade fica visível para qualquer usuário com uma API key |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `frontend/` na raiz do repositório, paralelo a `api/`, `ingestion/`, `motor_calculo/`, `orquestracao/` | Quinto componente do projeto |
| **KB Domains** | typescript-reviewer, a11y-architect | Padrões a consultar na fase de Design |
| **IaC Impact** | Nenhum nesta fase | Roda local via `next dev`; deploy real fica para depois |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A API backend (`api/main.py`) roda em `localhost` durante o desenvolvimento do frontend, numa porta configurável | Se a URL da API mudar, precisaria de uma variável de ambiente de configuração no frontend | [ ] |
| A-002 | Node.js/npm neste sandbox são suficientes para `next dev` e os testes do frontend rodarem sem instalação adicional bloqueada | Se algum pacote não puder ser instalado, seguiria o mesmo padrão de isolamento já usado nas features anteriores (documentar como blocker) | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro — falta de UI para os recursos já existentes na API |
| Users | 2 | Duas personas de negócio identificadas, mas ainda sem dados reais de uso |
| Goals | 3 | MUST/SHOULD/COULD explícitos, herdados do brainstorm |
| Success | 3 | Critérios mensuráveis e testáveis (persistência, exibição de dados reais, tratamento de erro) |
| Scope | 3 | Out of scope extremamente explícito |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma — pronto para Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-23 | define-agent | Versão inicial, extraída de BRAINSTORM_FRONTEND_SIMULADOR.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_FRONTEND_SIMULADOR.md`
