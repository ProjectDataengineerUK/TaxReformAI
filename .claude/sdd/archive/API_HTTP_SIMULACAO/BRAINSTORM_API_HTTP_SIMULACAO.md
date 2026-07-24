# BRAINSTORM: API HTTP de Simulação (`/v1/tax/simulate` + endpoint conversacional)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_HTTP_SIMULACAO |
| **Date** | 2026-07-23 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Depois de shipar `MOTOR_DETERMINISTICO_CALCULO` e `ORQUESTRACAO_MULTIAGENTE`, o usuário escolheu como próximo passo (consultando `CLAUDE.md`) construir a API HTTP que expõe o grafo de orquestração — o componente que transforma os módulos Python isolados num serviço consumível.

**Context Gathered:**
- `contexto.md` (seção 8) já documenta um endpoint `/v1/tax/simulate` com payload estruturado (`tenant_id`, `ano_operacao`, lista de `itens[]` com `ncm`/`quantidade`/`valor_unitario`/`uf_origem`/`uf_destino`) — claramente pensado para integração com ERP, não para linguagem natural.
- `orquestracao/` (feature já shipada) espera `texto_consulta` — uma pergunta em texto livre, processada pelos 5 agentes.
- `langgraph` não é instalável neste sandbox (mesmo bloqueio já documentado no BUILD_REPORT de `ORQUESTRACAO_MULTIAGENTE`), mas `FastAPI`, `uvicorn` e `httpx` estão disponíveis — diferente das duas features anteriores, esta é totalmente testável de ponta a ponta.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo diretório `api/` na raiz, paralelo a `ingestion/`, `motor_calculo/`, `orquestracao/` | Quarto componente, mas é o primeiro que expõe os demais via HTTP |
| Relevant KB Domains | python-developer (FastAPI), security-reviewer (autenticação) | Padrões a consultar no /design |
| IaC Impact | Nenhum nesta fase — roda local via `uvicorn`, sem deploy real (Cloud Run fica para IaC futura) | |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | A API deve expor o endpoint estruturado da seção 8 (ERP), o conversacional (grafo), ou ambos? | Ambos | Dois casos de uso distintos: estruturado chama `motor_calculo` direto por item (sem os agentes de LLM); conversacional roda os 5 nós de `orquestracao/` |
| 2 | Autenticação/multi-tenancy deve ser real (Postgres) ou mínima, dado que não há schema de tenants ainda? | Mínima — API key simples, sem multi-tenancy real por trás | Evita depender de infraestrutura (Postgres) que ainda não existe no projeto |
| 3 | Como validar a API key, e qual o limite de itens por requisição síncrona? | Lista de chaves via variável de ambiente, cada uma mapeada a um `tenant_id` fixo em config; limite de ~100 itens — upload de 10.000 SKUs em lote é uma feature diferente (Celery/Redis, já fora de escopo desde o brainstorm de orquestração) | Evita reconstruir o caso de uso de "Business plan: upload de até 10.000 SKUs", que é assíncrono por natureza |
| 4 | Faz sentido promover o encadeamento sequencial dos 5 nós (hoje só um helper de teste em `orquestracao/`) para código de produção, em vez de esperar `langgraph` ficar instalável? | Sim | Resolve o blocker do `langgraph` por completo para esta feature — a API funciona de ponta a ponta agora |

**Minimum Questions:** 3 ✅ (4 perguntas, incluindo validação da abordagem)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `contexto.md`, seção 8 — payload de exemplo real do `/v1/tax/simulate` | 1 | Usado como contrato de schema do endpoint estruturado |
| Output examples | `contexto.md`, seção 8 — resposta de exemplo (`resumo_financeiro`, `itens_detalhados`) | 1 | Referência exata de formato de resposta |
| Related code | `motor_calculo/engine.py` (real), `orquestracao/nos/*.py` (fakes com schema fiel) | 5 | Reaproveitados diretamente pelos dois endpoints |

**Como as fontes serão usadas:**

- O payload/resposta da seção 8 vira o schema Pydantic exato do endpoint estruturado — não é preciso inventar formato novo
- Os nós já existentes de `orquestracao/` são reaproveitados sem modificação para o endpoint conversacional

---

## Approaches Explored

### Approach A: Dois endpoints FastAPI, reaproveitando tudo que já existe; executor sequencial promovido a produção ⭐ Recomendada

**Description:** `POST /v1/tax/simulate` (estruturado) chama `motor_calculo.engine.TaxCalculatorEngine` diretamente por item da lista, agregando um `resumo_financeiro`. `POST /v1/tax/query` (conversacional) roda os 5 nós de `orquestracao/` via um novo módulo `orquestracao/executor.py`, que promove o encadeamento sequencial (hoje só um helper de teste) para código de produção — sem depender de `langgraph`. Autenticação via API key simples (header `X-API-Key`, validada contra lista em variável de ambiente).

**Pros:**
- Testável de ponta a ponta neste sandbox (FastAPI/uvicorn/httpx disponíveis)
- Resolve o blocker do `langgraph` sem esperar instalação — a interface pública fica estável para trocar a implementação depois
- Reaproveita 100% do código já validado nas 3 features anteriores

**Cons:**
- O endpoint conversacional não usa o "grafo" real via LangGraph, só a versão sequencial — precisa ficar documentado que a troca é possível sem mudar a API pública

**Why Recommended:** É a única abordagem que entrega uma API funcional agora, sem bloquear em uma dependência externa não instalável.

---

### Approach B: Só o endpoint estruturado (seção 8), adiar o conversacional

**Description:** Construir apenas `/v1/tax/simulate`, deixando o endpoint conversacional para quando os LLMs reais estiverem conectados.

**Pros:**
- Menor escopo
- Evita expor um endpoint cujo "conteúdo" (Classificador/Pesquisador/Extrator) ainda é fake

**Cons:**
- Usuário pediu explicitamente os dois endpoints

---

### Approach C: Usar `construir_grafo()` (LangGraph) mesmo, aceitando que o endpoint conversacional não rode neste sandbox

**Description:** A API importaria `orquestracao.grafo.construir_grafo()` diretamente, sem promover um executor sequencial alternativo.

**Pros:**
- Usa a implementação "real" (LangGraph) sem duplicar lógica de encadeamento

**Cons:**
- O endpoint conversacional ficaria não-funcional e não-testável neste ambiente — pior do que a Approach A, que resolve isso sem esperar nada

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Dois endpoints, executor sequencial promovido a produção |
| **User Confirmation** | 2026-07-23 |
| **Reasoning** | Única abordagem que entrega uma API funcional e testável agora, sem depender de `langgraph` estar instalado |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Dois endpoints: `/v1/tax/simulate` (estruturado, seção 8) e `/v1/tax/query` (conversacional) | Usuário confirmou os dois casos de uso; são genuinamente diferentes (ERP com dados prontos vs. pergunta em texto livre) | Approach B (só estruturado) — rejeitada, usuário pediu ambos |
| 2 | `orquestracao/executor.py` novo, promovendo o encadeamento sequencial de teste para produção | Resolve o blocker do `langgraph` sem esperar instalação; interface pública da API não muda quando o LangGraph real for conectado depois | Approach C (usar `construir_grafo()` direto) — rejeitada, deixaria o endpoint conversacional não-funcional neste ambiente |
| 3 | Autenticação via API key simples (env var → `tenant_id` fixo em config), sem Postgres/multi-tenancy real | Não há schema de tenants no projeto ainda; prova o mecanismo de auth sem inventar infraestrutura fora de escopo | Multi-tenancy real via Postgres — rejeitada, exigiria uma feature de schema de banco antes desta |
| 4 | `itens[]` do endpoint estruturado limitado a ~100 por requisição síncrona | Upload de 10.000 SKUs (Business plan) é um caso de uso assíncrono, já identificado como fora de escopo desde o brainstorm de orquestração (Celery/Redis) | Sem limite — rejeitada, misturaria dois casos de uso (síncrono vs. lote assíncrono) numa única rota |
| 5 | Ambos os endpoints aplicam a mesma alíquota de fase (2026) independente de NCM/UF — limitação já existente, só exposta via HTTP agora | `TabelaAliquotasSeed` (feature `MOTOR_DETERMINISTICO_CALCULO`) só tem a fase 2026; não é uma nova limitação desta feature, é a mesma restrição já documentada | Fingir que a alíquota varia por NCM/UF nesta API — rejeitada, quebraria a garantia de auditabilidade (citar uma regra que não existe de verdade) |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Rate limiting | Não é um requisito desta fase — API ainda não tem tráfego real | Sim |
| Multi-tenancy real via Postgres | Exigiria uma feature de schema de banco antes desta (seção 7 do blueprint) | Sim, feature futura |
| Upload em lote assíncrono (Celery/Redis) | Caso de uso diferente (10.000 SKUs, processamento em segundo plano) — já descartado desde o brainstorm de orquestração | Sim, feature futura |
| Deploy real (Cloud Run) | Fora de escopo — esta feature só prova a API rodando localmente via `uvicorn` | Sim, quando a infraestrutura GCP da ingestão for resolvida |
| Autenticação OAuth/JWT completa | API key simples já prova o mecanismo sem a complexidade de um provedor de identidade | Sim, quando houver usuários reais/frontend |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Escopo dos dois endpoints + promoção do executor sequencial | ✅ | Usuário confirmou ("sim") | Não |
| Auth mínima (API key) + limite de `itens[]` | ✅ | Usuário confirmou ("sim") | Não |

**Minimum Validations:** 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O sistema precisa de uma API HTTP que exponha tanto o motor de cálculo (via endpoint estruturado para integração com ERP, seção 8 do blueprint) quanto o grafo de orquestração (via endpoint conversacional), com autenticação mínima — hoje `motor_calculo` e `orquestracao` são apenas bibliotecas Python, sem nenhuma forma de consumo externo.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| ERP (SAP/TOTVS), via integração HTTP | Precisa enviar uma lista de itens (NCM/quantidade/valor) e receber a simulação tributária agregada |
| Usuário final (indireto, via futuro frontend) | Precisa fazer uma pergunta em texto livre e receber um parecer com fundamentação legal |

### Success Criteria (Draft)
- [ ] `POST /v1/tax/simulate` aceita o payload exato da seção 8 e retorna `resumo_financeiro` + `itens_detalhados` no formato documentado
- [ ] `POST /v1/tax/query` aceita uma pergunta em texto livre e retorna `parecer_final` + `resultado_calculo` (quando aplicável) + histórico auditável
- [ ] Requisições sem `X-API-Key` válida retornam 401 em ambos os endpoints
- [ ] `itens[]` acima do limite (ex: 100) retornam 422 com mensagem clara

### Constraints Identified
- `langgraph` não instalável neste sandbox — endpoint conversacional usa o executor sequencial, não o grafo real
- `TabelaAliquotasSeed` só tem a fase 2026 — ambos os endpoints herdam essa limitação
- Sem Postgres/tenant real — auth é só uma lista de chaves em config

### Out of Scope (Confirmed)
- Multi-tenancy real / Postgres
- Rate limiting
- Upload em lote assíncrono (Celery/Redis)
- Conexão com Qdrant real ou LLMs reais — os fakes já existentes continuam sendo usados
- Deploy real (Cloud Run)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |
| Duration | 1 sessão de diálogo |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_API_HTTP_SIMULACAO.md`
