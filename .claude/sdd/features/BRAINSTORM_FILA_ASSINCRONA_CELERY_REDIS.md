# BRAINSTORM: FILA_ASSINCRONA_CELERY_REDIS

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FILA_ASSINCRONA_CELERY_REDIS |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Approaches Identified — Ready for Define |

---

## Initial Idea

**Raw Input:** 11ª e última posição restante da "primeira leva" do
`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`: "Fila assíncrona (Celery/Redis) para sustentar 50.000+
SKUs dos planos Business/Enterprise". **Nome da feature preservado do roadmap** mesmo após a
mudança de mecanismo (ver Revisão abaixo) — mesmo padrão já usado em `CLOUD_COMPOSER_PROVISIONAMENTO`
(nome preservado apesar do desvio de "provisionar permanentemente" para "ciclo efêmero").

**Context Gathered:**
- `api/routers/empresa_skus.py` (`API_EMPRESA_SKUS`) tem hoje um upload CSV **síncrono** com
  `TETO_LINHAS_UPLOAD = 10_000` e `TAMANHO_MAXIMO_UPLOAD_BYTES = 5MB`, com um comentário explícito
  no código apontando para esta posição do roadmap como o caminho para volumes maiores.
- `contexto.md` (persona "Grandes Varejistas e E-commerce: 50.000+ SKUs") prescreve literalmente
  "Celery + Memorystore (Redis)" — mas o projeto já desviou do blueprint literal antes quando a
  alternativa nativa do GCP resolve o mesmo problema mais barato (`BIGQUERY_DATA_WAREHOUSE`
  preferiu BigQuery serverless em vez de manter Composer rodando).
- Zero código, dependência ou infraestrutura de Celery/Redis/Cloud Tasks existe hoje — feature do
  zero.
- **Achado crítico deste `/brainstorm` (não visto na primeira rodada)**: Memorystore Redis não
  tem opção de IP público — exige VPC + Serverless VPC Access connector para o Cloud Run alcançá-lo.
  Nenhum recurso deste projeto usa VPC hoje (Cloud SQL com IP público sem redes autorizadas, Cloud
  Run sem VPC, Composer sem VPC customizada — todos deliberados, documentados nos comentários do
  `main.tf`). O custo real de Celery+Redis não é só o Redis (~US$35+/mês): soma o conector VPC
  (~US$8-10/mês mínimo) e um worker Cloud Run sempre ligado (`minInstances=1`, ~US$15-20/mês) —
  total realista ~US$60-70/mês, quase o dobro da estimativa inicial de ~US$35/mês.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `api/routers/empresa_skus.py` (modificar), `api/tasks_sku.py` (novo, endpoint interno), `infra/terraform/main.tf` | Reaproveita `parsear_linha_csv`/`upsert_sku` já existentes; o endpoint de processamento vive no MESMO serviço Cloud Run da API — nenhum worker/serviço novo |
| Relevant KB Domains | N/A (não é feature de IA/LLM) | — |
| IaC Impact | Cloud Tasks queue, bucket GCS de staging (lifecycle curto), migração Postgres nova (`sku_upload_jobs`) | Sem VPC, sem Redis, sem worker sempre ligado — todos recursos serverless ou já existentes |

---

## Discovery Questions & Answers

### Primeira rodada (mecanismo original: Celery + Redis)

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Cloud Tasks (serverless, sem Redis) vs. Celery+Memorystore Redis (literal do blueprint) | Celery + Memorystore Redis | Decisão inicial, **revertida** na segunda rodada (ver abaixo) |
| 2 | Onde os workers Celery rodam | Cloud Run com `minInstances>=1` | Descartado junto com a decisão 1 |
| 3 | Existe demanda real hoje ou é lacuna do blueprint sem cliente batendo no teto | Lacuna do blueprint, sem demanda ativa | **Continua válido** — reforça a escolha pelo caminho mais barato/simples na segunda rodada |
| 4 | Escopo: só upload de SKUs, ou fila genérica para uso futuro também | Só o upload de SKUs | **Continua válido** |
| 5 | Upload sempre assíncrono vs. híbrido | Sempre assíncrono | **Continua válido** |

### Segunda rodada (depois do achado de VPC/custo real, durante o `/design`)

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 6 | Com o custo real (~US$60-70/mês) e a introdução de VPC conhecidos, qual caminho seguir: aceitar Celery+Redis+VPC, ou reconsiderar Cloud Tasks? | **Reconsiderar Cloud Tasks** | Reverte a decisão 1 — Cloud Tasks + endpoint interno no mesmo serviço Cloud Run, sem VPC, sem Redis, sem worker separado |
| 7 | Sem Redis, onde fica o status do job (antes seria o result backend do Celery)? | Tabela nova no Postgres (`sku_upload_jobs`, com RLS por tenant) | Mais consistente com o resto do projeto (mesmo padrão de `empresa_skus`/`pareceres_audit_log`) do que depender de um result backend externo |

**Minimum Questions:** 3 — atendido (7 perguntas ao todo, 2 rodadas).

---

## Sample Data Inventory

> Não é feature de IA/LLM — não há necessidade de grounding por amostras de treinamento. O
> "dado de referência" é a lógica de parsing/validação já existente e testada.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Lógica de parsing reutilizável | `api/empresa_skus.py::parsear_linha_csv` | 1 função | Já testada em `tests/test_empresa_skus.py` — o endpoint de processamento reusa, não reimplementa |
| Lógica de escrita reutilizável | `db/repositorio.py::upsert_sku` | 1 função | Mesmo padrão — a task Cloud Tasks chama a função existente, dentro de `sessao_do_tenant` |
| Padrão de endpoint existente | `api/routers/empresa_skus.py::upload_csv` | 1 endpoint | Referência de validação de tamanho/linhas a preservar antes de enfileirar |
| Padrão de tabela com RLS | `db/migrations/001` (`pareceres_audit_log`), `002` (RLS) | 2 migrações | Modelo direto para `sku_upload_jobs` — mesma disciplina de `tenant_id` + `FORCE ROW LEVEL SECURITY` |

---

## Approaches Explored

### Approach A: Cloud Tasks + endpoint interno no mesmo serviço Cloud Run ⭐ Recomendado

**Description:** `POST /v1/tax/skus/upload` faz staging do arquivo num bucket GCS, cria a linha
do job em `sku_upload_jobs` (status `PENDENTE`) e enfileira uma Cloud Task apontando para um novo
endpoint interno (`POST /v1/tax/skus/upload/processar-tarefa`) no MESMO serviço Cloud Run da API
— autenticado via OIDC do próprio Cloud Tasks (padrão nativo GCP para invocar Cloud Run). O
Cloud Run escala sob demanda para atender essa chamada, processa o CSV inteiro (reusando
`parsear_linha_csv`/`upsert_sku`) e atualiza `sku_upload_jobs` para `CONCLUIDO`/`ERRO` ao final.
`GET /v1/tax/skus/upload/{job_id}` lê o status direto da tabela, com RLS garantindo isolamento
por tenant.

**Pros:**
- Zero infraestrutura nova de compute — reusa o serviço Cloud Run que já existe.
- Sem VPC, sem Redis, sem worker sempre ligado — mantém a disciplina "sem VPC" do projeto inteiro.
- Custo essencialmente marginal (Cloud Tasks cobra por execução, GCS por armazenamento
  temporário) — muito mais próximo do perfil do BigQuery (serverless) do que do Composer.
- Status do job em Postgres com RLS é mais auditável e consistente com o resto do projeto do que
  um result backend externo.

**Cons:**
- O endpoint interno precisa de proteção contra chamada externa direta (só o Cloud Tasks deve
  poder disparar essa rota) — exige verificação do token OIDC/cabeçalho do Cloud Tasks.
- Processar 50.000+ linhas numa única chamada HTTP pode se aproximar do timeout do Cloud Run
  (configurável até 60 min, mas ainda um limite) — a validar com um teste real (AT-005).

**Why Recommended:** Resolve o mesmo problema de negócio (não travar a requisição do cliente,
sustentar 50.000+ SKUs) com uma fração do custo e da complexidade operacional, sem introduzir o
primeiro recurso com VPC do projeto inteiro.

---

### Approach B: Celery + Memorystore Redis (rejeitada na 2ª rodada)

**Description:** Ver descrição completa na versão anterior deste documento (git history) —
worker Celery em serviço Cloud Run dedicado (`minInstances=1`), Redis como broker + result
backend, exigindo VPC + Serverless VPC Access connector.

**Pros:**
- Segue o blueprint literalmente.
- Celery tem funcionalidades mais maduras para casos futuros complexos (retry configurável,
  rate limiting, chains/chords) — não necessárias para o caso de uso atual.

**Cons:**
- Custo real ~US$60-70/mês (Redis + conector VPC + worker sempre ligado), quase o dobro da
  estimativa inicial.
- Introduz VPC no projeto pela primeira vez — desvio de uma disciplina de infraestrutura mantida
  deliberadamente em toda decisão anterior.
- Sem demanda real de cliente hoje que justifique essa complexidade adicional.

**Why Rejected:** Quando o custo/complexidade real ficou claro (achado deste `/brainstorm`, não
visível na estimativa inicial), a ausência de demanda real (pergunta 3, primeira rodada) deixou
de justificar a escolha mais cara e mais complexa.

---

## Data Engineering Context

Não aplicável — esta feature não é um pipeline de dados analíticos, é infraestrutura de
processamento assíncrono de requisições HTTP.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Cloud Tasks + endpoint interno no mesmo serviço Cloud Run |
| **User Confirmation** | 2026-08-04, confirmado explicitamente após o achado de VPC/custo real e a reformulação |
| **Reasoning** | Resolve o mesmo problema sem VPC, sem Redis, sem worker sempre ligado — custo e complexidade muito menores, sem demanda real que justifique o caminho mais caro |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Cloud Tasks, não Celery+Redis | Achado real de VPC/custo (~US$60-70/mês vs. ~poucos dólares) mudou a decisão inicial | Celery + Memorystore Redis |
| 2 | Endpoint de processamento no MESMO serviço Cloud Run da API, sem worker separado | Cloud Tasks invoca via HTTP — não precisa de um processo consumidor dedicado como o Celery exigia | Serviço Cloud Run dedicado ao worker |
| 3 | Status do job em tabela Postgres nova (`sku_upload_jobs`), com RLS | Mais consistente com o resto do projeto do que um result backend externo; sem Redis, é a opção natural | Redis como result backend (só fazia sentido com Celery) |
| 4 | Payload do arquivo via staging em GCS, task carrega só a URI | Mesma razão da rodada anterior — evita mensagens grandes na fila | Embutir o CSV na mensagem da task |
| 5 | Upload sempre assíncrono, um só caminho de código | Decisão da primeira rodada, ainda válida independente do mecanismo | Híbrido sync/async |
| 6 | Escopo restrito só ao upload de SKUs | YAGNI — sem demanda real por uma fila genérica ainda | Fila genérica para uso futuro |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Celery + Memorystore Redis | Custo/complexidade real (VPC) descoberto tarde demais para justificar sem demanda ativa | Sim, se um caso de uso futuro precisar de recursos que só o Celery oferece (chains/chords, rate limiting fino) |
| Worker Cloud Run dedicado, sempre ligado | Desnecessário sem Celery — Cloud Tasks invoca o serviço já existente | Não aplicável nesta arquitetura |
| Fila assíncrona genérica para outros fluxos | Nenhum outro consumidor real identificado agora | Sim — Cloud Tasks, uma vez configurado, é reaproveitável para outras filas |
| Caminho síncrono preservado para uploads pequenos | Simplicidade de 1 caminho de código venceu | Não — decisão explícita |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Mecanismo original (Celery+Redis vs Cloud Tasks) | ✅ | Confirmou Celery+Redis inicialmente | Sim — revertido na 2ª rodada |
| Achado de VPC/custo real durante o `/design` | ✅ | Pediu "melhor abordagem" — recomendação direta dada | Sim — mudou para Cloud Tasks |
| Nova arquitetura consolidada (Cloud Tasks + endpoint interno + tabela de jobs) | ✅ | "Sim, seguir com essa abordagem" | Não |

**Minimum Validations:** 2 — atendido (3 validações, 2 rodadas).

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O upload de catálogo de SKUs (`POST /v1/tax/skus/upload`) processa arquivos de forma síncrona,
com um teto de 10.000 linhas — insuficiente para a persona de "Grandes Varejistas e E-commerce"
(50.000+ SKUs) prevista no blueprint, sem exceder o tempo de resposta HTTP razoável de uma
requisição síncrona.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Tenant com catálogo grande (planos Business/Enterprise) | Não consegue subir mais de 10.000 SKUs numa única chamada síncrona |

### Success Criteria (Draft)
- [ ] Cloud Tasks queue e bucket GCS de staging provisionados via Terraform, reais, verificados
- [ ] `POST /v1/tax/skus/upload` devolve `202` + `job_id` imediatamente, para qualquer tamanho
      de arquivo dentro do novo teto
- [ ] `GET /v1/tax/skus/upload/{job_id}` reporta status e resultado final, respeitando isolamento
      de tenant via RLS
- [ ] Endpoint interno de processamento só aceita chamadas do Cloud Tasks (nunca de fora)
- [ ] Um upload real de 50.000+ linhas processa com sucesso via fila, sem timeout HTTP

### Constraints Identified
- Reaproveitar `parsear_linha_csv`/`upsert_sku` já existentes — nenhuma duplicação de lógica
- `sku_upload_jobs` precisa de RLS — mesma disciplina de isolamento já auditada no resto do projeto
- Sem VPC, sem Redis — mantém a disciplina de infraestrutura já estabelecida no projeto
- Payload do arquivo via staging em GCS, task carrega só a URI

### Out of Scope (Confirmed)
- Celery + Memorystore Redis
- Fila assíncrona genérica para outros fluxos além do upload de SKUs
- Caminho síncrono preservado para uploads pequenos
- Worker Cloud Run dedicado

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 7 (2 rodadas) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 3 |
| Duration | ~50min (incluindo a reformulação) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_FILA_ASSINCRONA_CELERY_REDIS.md`
