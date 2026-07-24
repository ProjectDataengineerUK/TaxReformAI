# DEFINE: API HTTP de Simulação (`/v1/tax/simulate` + endpoint conversacional)

> API FastAPI que expõe o motor de cálculo (endpoint estruturado para ERPs) e o grafo de orquestração (endpoint conversacional), com autenticação mínima via API key.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_HTTP_SIMULACAO |
| **Date** | 2026-07-23 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O sistema precisa de uma API HTTP que exponha tanto o motor de cálculo (via endpoint estruturado para integração com ERP, seção 8 do blueprint) quanto o grafo de orquestração (via endpoint conversacional), com autenticação mínima — hoje `motor_calculo` e `orquestracao` são apenas bibliotecas Python, sem nenhuma forma de consumo externo.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| ERP (SAP/TOTVS), via integração HTTP | Sistema externo consumidor | Precisa enviar uma lista de itens (NCM/quantidade/valor) e receber a simulação tributária agregada, sem acessar Python diretamente |
| Usuário final (indireto, via futuro frontend) | Consumidor indireto do produto | Precisa fazer uma pergunta em texto livre e receber um parecer com fundamentação legal |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `POST /v1/tax/simulate` aceita o payload exato da seção 8 (`tenant_id`, `ano_operacao`, `itens[]`), chama `motor_calculo` por item, retorna `resumo_financeiro` + `itens_detalhados` |
| **MUST** | `POST /v1/tax/query` aceita `texto_consulta` + `ano_operacao` + `valor_base`, roda os 5 nós via novo `orquestracao/executor.py` (sequencial, sem depender de `langgraph`), retorna `parecer_final` + `resultado_calculo` + histórico auditável |
| **MUST** | Autenticação via header `X-API-Key`, validada contra lista em variável de ambiente mapeada a um `tenant_id` fixo — 401 se ausente/inválida |
| **MUST** | `itens[]` limitado a 100 por requisição — 422 com mensagem clara se exceder |
| **SHOULD** | Documentação automática OpenAPI/Swagger (nativa do FastAPI) refletindo os schemas reais dos dois endpoints |
| **COULD** | Endpoint de health-check (`/healthz`) para verificação manual |

---

## Success Criteria

- [ ] `POST /v1/tax/simulate` com payload da seção 8 retorna 200 com `resumo_financeiro`/`itens_detalhados` no formato documentado
- [ ] `POST /v1/tax/query` com pergunta sintética retorna `parecer_final` + `resultado_calculo` + histórico auditável
- [ ] Requisição sem `X-API-Key` válida retorna 401 em ambos os endpoints
- [ ] `itens[]` com mais de 100 elementos retorna 422

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path (estruturado) | Payload válido da seção 8 + `X-API-Key` válida | `POST /v1/tax/simulate` | 200, com `resumo_financeiro`/`itens_detalhados` batendo com `TaxCalculatorEngine` chamado diretamente para os mesmos itens |
| AT-002 | Error case (auth) | Requisição sem `X-API-Key` ou com chave inválida | `POST` em qualquer um dos dois endpoints | 401, sem processar o corpo da requisição |
| AT-003 | Edge case (conversacional + alíquota indisponível) | Pergunta com `ano_operacao=2028` (sem alíquota confirmada na `TabelaAliquotasSeed`) | `POST /v1/tax/query` | Erro HTTP claro (ex.: 422/409) — nunca um `parecer_final` com número inventado |

---

## Out of Scope

- Multi-tenancy real / Postgres — `tenant_id` vem de config estática, não de banco
- Rate limiting
- Upload em lote assíncrono (Celery/Redis) — caso de uso do plano Business (10.000 SKUs), feature diferente
- Conexão com Qdrant real ou LLMs reais — os fakes já existentes em `orquestracao/` continuam sendo usados
- Deploy real (Cloud Run) — fica para uma feature de IaC futura

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `langgraph` não instalável neste sandbox | Endpoint conversacional usa `orquestracao/executor.py` (sequencial), não `construir_grafo()` |
| Technical | `TabelaAliquotasSeed` só tem a fase 2026 confirmada | Ambos os endpoints herdam a limitação — anos/fases sem alíquota confirmada retornam erro explícito, nunca um número estimado |
| Scope | Sem Postgres/tenant real | Autenticação é uma lista estática de chaves em config/variável de ambiente |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `api/` na raiz do repositório, paralelo a `ingestion/`, `motor_calculo/`, `orquestracao/` | Quarto componente — o primeiro que expõe os demais via HTTP |
| **KB Domains** | python-developer (FastAPI), security-reviewer (mecanismo de autenticação) | Padrões a consultar na fase de Design |
| **IaC Impact** | Nenhum nesta fase | API roda localmente via `uvicorn`; deploy real fica para depois |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Um limite de 100 itens é suficiente para provar o endpoint síncrono sem se confundir com o caso de uso de lote (10.000 SKUs) | Ajuste de configuração simples se o número real precisar mudar | [ ] |
| A-002 | Uma lista estática de API keys em variável de ambiente é aceitável nesta fase (sem hashing, sem rotação) | Antes de produção real, precisaria de hashing e rotação de chaves | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro — falta de forma de consumo externo para componentes já existentes |
| Users | 2 | ERP é um consumidor concreto; usuário final ainda é indireto (sem frontend) |
| Goals | 3 | MUST/SHOULD/COULD explícitos, herdados do brainstorm |
| Success | 3 | Critérios mensuráveis e testáveis via HTTP (códigos de status, schemas) |
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
| 1.0 | 2026-07-23 | define-agent | Versão inicial, extraída de BRAINSTORM_API_HTTP_SIMULACAO.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_API_HTTP_SIMULACAO.md`
