# BRAINSTORM: BIGQUERY_DATA_WAREHOUSE

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BIGQUERY_DATA_WAREHOUSE |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Approaches Identified — Ready for Define |

---

## Initial Idea

**Raw Input:** 10ª posição do `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`: "Provisionar BigQuery
para consultas analíticas em histórico de simulações (seção 5 do blueprint)".

**Context Gathered:**
- `contexto.md` (seção 5.1) menciona BigQuery como uma linha entre 5 motivações de infraestrutura
  do GCP — sem spec, sem detalhamento de schema ou pipeline.
- `pareceres_audit_log` (Cloud SQL, `SCHEMA_POSTGRESQL`) já grava toda simulação/consulta em
  produção desde 2026-07-27: `id`, `tenant_id`, `user_id`, `prompt_consulta`,
  `contexto_recuperado_ids` (JSONB), `payload_calculo_json` (JSONB), `resposta_parecer_md`,
  `created_at`. Escrita confirmada de 3 endpoints: `/v1/tax/simulate`,
  `/v1/tax/simulate-simples-nacional`, `/v1/tax/query`.
- `prompt_consulta`/`resposta_parecer_md` já passam por mascaramento de PII (`LLM_REAL_VERTEX_AI`)
  ANTES de chegar ao audit log — replicar essas colunas para o BigQuery não introduz um novo
  vetor de vazamento de PII.
- RLS (`FORCE ROW LEVEL SECURITY`) isola `pareceres_audit_log` por `tenant_id`; o papel de
  runtime da API (`taxreformai_app`) só enxerga o próprio tenant em cada sessão. Um sync que
  precisa ler TODOS os tenants exige o papel administrativo (`taxreformai_admin`, hoje só usado
  por migrações) ou um papel novo dedicado — decisão adiada para `/design`, porque exige
  verificar contra o Cloud SQL real se `taxreformai_admin` de fato ignora a RLS (nenhum papel
  tem `rolsuper=true` neste projeto, lição de `SCHEMA_POSTGRESQL`).
- Sessão imediatamente anterior (`CLOUD_COMPOSER_PROVISIONAMENTO`, shipada bloqueada) deixou uma
  lição fresca e cara: operar infraestrutura GCP real "sempre ligada" pode custar muito mais
  tempo/dinheiro do que o esperado. BigQuery tem perfil de custo estruturalmente diferente
  (paga por armazenamento/consulta, não por hora), mas essa suposição foi verificada nesta
  sessão, não assumida.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `infra/terraform/main.tf` (dataset/tabela), `scripts/sincronizar_bigquery.py`, `.github/workflows/sincronizar_bigquery.yml` | Segue o padrão de `scripts/verificar_*_producao.py` + workflow dedicado já usado em toda feature de infra real do projeto |
| Relevant KB Domains | N/A (não é feature de IA/LLM) | Schema derivado direto da tabela Postgres existente, não de amostras de treinamento |
| IaC Patterns | Terraform (já usado para GCS, Cloud SQL, Vertex AI, Composer — este último removido) | `google_bigquery_dataset` + `google_bigquery_table`, recurso PERMANENTE (ao contrário do Composer) |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Existe demanda real hoje, ou é só um item do blueprint sem stakeholder pedindo? | Há uma necessidade real | Justifica investir num MVP funcional, não só um "provisionar e provar que escreve" simbólico |
| 2 | Qual o caso de uso concreto? | As 3 opções apresentadas, juntas: dashboard interno de métricas de uso, relatório para cliente/tenant, e análise de negócio (pricing/roadmap) | Schema precisa suportar consulta por tenant E agregação cross-tenant; nenhum caso exige streaming |
| 3 | Frequência de atualização necessária? | Batch diário/periódico basta | Descarta streaming/CDC; ETL por sync incremental é suficiente |
| 4 | Mecanismo de ETL: cópia periódica vs. federated query ao vivo? | Cópia periódica (recomendado) | Evita carga analítica direta na instância `db-f1-micro` de produção, que já serve tráfego transacional real |
| 5 | Sync automático (cron) ou manual (workflow_dispatch), como todo outro script de infra do projeto? | Agendado (cron) desde o início | Primeiro gatilho automático de infraestrutura real do projeto — desvio deliberado do padrão "só workflow_dispatch" |

**Minimum Questions:** 3 — atendido (5 perguntas).

---

## Sample Data Inventory

> Não é uma feature de IA/LLM — não há necessidade de grounding por amostras de treinamento.
> O "dado de referência" aqui é a própria tabela de produção já existente.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Schema de referência | `db/migrations/001_schema_inicial.sql` (`pareceres_audit_log`) | 1 tabela, 8 colunas | Schema fonte real, já em produção desde 2026-07-27 |
| Dados reais de produção | Cloud SQL `taxreformai-pg`, tabela `pareceres_audit_log` | Volume não medido nesta sessão | Vai crescer 1 linha por chamada real a `/v1/tax/simulate`, `/v1/tax/simulate-simples-nacional` e `/v1/tax/query` — a verificar no `/design` |

**Como será usado:**
- O schema da tabela BigQuery é um espelho 1:1 do schema Postgres existente — não há desenho de
  schema novo, só tradução de tipos (JSONB → JSON nativo do BigQuery).

---

## Approaches Explored

### Approach A: Espelho por sync periódico (cópia) ⭐ Recomendado

**Description:** Terraform provisiona um dataset BigQuery permanente com uma tabela espelhando
`pareceres_audit_log` (mesmas colunas, JSONB vira `JSON` nativo do BigQuery). Um script Python
(`scripts/sincronizar_bigquery.py`) lê incrementalmente as linhas novas (watermark por
`created_at`/`id`) do Cloud SQL e carrega no BigQuery via `google-cloud-bigquery`. Um workflow do
GitHub Actions com `schedule: cron` roda esse script diariamente.

**Pros:**
- Zero carga analítica na instância `db-f1-micro` de produção — o BigQuery absorve todo o peso
  de consultas de dashboard/relatório.
- Dado replicado é imutável e append-only (audit log nunca é editado), o que torna o sync
  incremental simples e idempotente por natureza (nunca precisa de UPDATE/DELETE no destino).
- Segue o padrão já validado do projeto (script + workflow dedicado + Terraform), reduzindo risco
  de achados de infraestrutura totalmente novos.

**Cons:**
- Dado no BigQuery tem até 1 dia de atraso (aceitável, confirmado pelo usuário).
- Introduz o primeiro cron do projeto — mais um ponto de operação a monitorar (falha silenciosa
  de um cron não tem o mesmo sinal visual de um `workflow_dispatch` que alguém clicou e está
  observando).

**Why Recommended:** Atende às 3 necessidades reais descritas (dashboard, relatório, análise) sem
competir por recursos com o tráfego transacional, e sem reintroduzir o padrão de infraestrutura
"sempre ligada e cara" que acabou de causar o bloqueio de `CLOUD_COMPOSER_PROVISIONAMENTO`.

---

### Approach B: Federated query ao vivo (sem cópia)

**Description:** BigQuery consulta o Cloud SQL diretamente via `EXTERNAL_QUERY` (BigQuery
Connection do tipo Cloud SQL), sem nenhuma cópia de dado — cada query analítica lê o Postgres em
tempo real.

**Pros:**
- Dado sempre atual, zero pipeline de sincronização, zero cron.
- Menos infraestrutura nova (só uma "connection", não um dataset+tabela+script+workflow).

**Cons:**
- Cada consulta analítica (dashboard, relatório) bate direto na instância `db-f1-micro` que serve
  a API em produção — risco real de competir por recursos com tráfego transacional, justamente a
  mesma classe de problema (infraestrutura pequena sobrecarregada) que apareceu no worker do
  Composer nesta mesma sessão.
- Rejeitada explicitamente pelo usuário na fase de discovery.

---

## Data Engineering Context

### Source Systems
| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| `pareceres_audit_log` (Cloud SQL `taxreformai-pg`) | Postgres 16, tabela append-only | Não medido nesta sessão — a verificar no `/design` | Tempo real (escrita síncrona a cada chamada da API) |

### Data Flow Sketch
```text
[API: /v1/tax/simulate, /v1/tax/simulate-simples-nacional, /v1/tax/query]
   → [pareceres_audit_log, Cloud SQL]
   → [scripts/sincronizar_bigquery.py, cron diário via GitHub Actions]
   → [BigQuery: dataset taxreformai_analytics, tabela pareceres_historico]
   → [Consumidor: SQL ad-hoc / dashboard / relatório — fora do escopo desta feature]
```

### Key Data Questions Explored
| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Volume esperado? | Não medido — depende do uso real da API em produção | `/design` deve incluir uma consulta real de contagem de linhas antes de dimensionar o sync |
| 2 | Freshness SLA? | Batch diário | Cron simples, sem streaming/CDC |
| 3 | Quem consome? | Equipe interna (dashboard/análise) e, indiretamente, clientes via relatório | Schema espelho (sem modelagem dimensional) é suficiente para MVP — BI/dashboard fica fora de escopo |

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Espelho por sync periódico (cópia), cron diário |
| **User Confirmation** | 2026-08-04, confirmado explicitamente após apresentação consolidada |
| **Reasoning** | Atende as 3 necessidades reais sem competir com tráfego transacional na instância pequena de produção; mantém a disciplina de custo do projeto ao usar um serviço serverless (BigQuery) em vez de reintroduzir infraestrutura "sempre ligada" |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Sync por cópia periódica, não federated query | Evita carga analítica na instância `db-f1-micro` de produção | Federated query (Approach B) |
| 2 | Cron diário via GitHub Actions `schedule:`, não `workflow_dispatch` manual | Garante frescor sem depender de alguém lembrar de rodar; decisão explícita do usuário, mesmo sendo o primeiro gatilho automático de infra real do projeto | Manter só `workflow_dispatch`, mesmo padrão de todo outro script de infra do projeto |
| 3 | Schema espelho 1:1 (sem modelagem dimensional/star schema) | YAGNI — nenhum dos 3 casos de uso reais pede um data mart formal ainda; BigQuery suporta consulta nativa em colunas `JSON`, então nem os campos JSONB precisam de parsing antecipado | Star schema com tabelas fato/dimensão desde já |
| 4 | Dataset/tabela BigQuery via Terraform, recurso PERMANENTE | Perfil de custo do BigQuery (armazenamento + consulta, não por hora) o torna seguro para manter sempre provisionado, ao contrário do Cloud Composer | Ciclo efêmero provisionar/verificar/destruir (padrão usado em `CLOUD_COMPOSER_PROVISIONAMENTO`) — não se aplica aqui porque o perfil de custo é outro |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Modelagem dimensional (star schema, tabelas fato/dimensão) | Nenhum dos 3 casos de uso reais foi especificado com detalhe suficiente para justificar o desenho agora; BigQuery consulta `JSON` nativamente, então a extração de campos estruturados pode esperar um dashboard real | Sim — é a extensão natural quando um consumidor específico (dashboard, BI tool) existir |
| Dashboard/BI tool (Looker Studio, etc.) | Fora do escopo desta feature — o roadmap pede "provisionar BigQuery para consultas analíticas", não construir a camada de consumo | Sim, feature futura separada |
| Streaming/CDC (Datastream, Debezium) | Nenhum caso de uso exige freshness sub-diária | Sim, se a necessidade mudar |
| Retenção/particionamento avançado (lifecycle rules, partition por data) | Não avaliado ainda — volume de dado real desconhecido nesta sessão | Sim, decisão do `/design` uma vez que o volume real seja medido |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Motivação/demanda real | ✅ | Confirmou 3 casos de uso reais (dashboard, relatório, análise de negócio) | Não |
| Mecanismo de ETL + automação | ✅ | Confirmou sync periódico + cron diário | Não |
| Abordagem consolidada (espelho 1:1, Terraform permanente) | ✅ | "Sim, seguir com essa abordagem" | Não |

**Minimum Validations:** 2 — atendido (3 validações).

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O histórico de simulações/consultas gravado em `pareceres_audit_log` (Cloud SQL) não tem uma
camada de consulta analítica adequada para dashboards internos, relatórios de cliente e análise
de negócio — consultar diretamente a instância de produção competiria com o tráfego
transacional real da API.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Equipe interna (produto/negócio) | Sem visibilidade agregada de uso (volume por tenant, NCMs mais consultados, tributos/Anexos mais usados) sem escrever SQL ad-hoc contra produção |
| Cliente/tenant | Sem uma forma analítica de consultar seu próprio histórico de simulações fora do fluxo transacional da API |

### Success Criteria (Draft)
- [ ] Dataset e tabela BigQuery provisionados via Terraform, real, verificado contra o GCP
- [ ] Script de sync lê incrementalmente `pareceres_audit_log` e carrega no BigQuery sem
      duplicar linhas em execuções repetidas (idempotência)
- [ ] Cron diário do GitHub Actions dispara o sync automaticamente, verificado com pelo menos
      uma execução real bem-sucedida
- [ ] Uma consulta SQL real contra o BigQuery confirma que os dados sincronizados batem com o
      Cloud SQL de origem (contagem de linhas, amostra de conteúdo)

### Constraints Identified
- Não pode adicionar carga de consulta analítica à instância `db-f1-micro` de produção
- Não pode introduzir vazamento de PII — os campos já mascarados (`prompt_consulta`,
  `resposta_parecer_md`) devem chegar ao BigQuery do mesmo jeito que estão no Postgres, sem
  reprocessamento
- Papel de leitura do script precisa de acesso cross-tenant (bypassa RLS) — decisão de qual
  papel usar/criar fica para o `/design`, verificada contra o Cloud SQL real no `/build`

### Out of Scope (Confirmed)
- Modelagem dimensional / star schema
- Dashboard ou ferramenta de BI (Looker Studio, etc.)
- Streaming/CDC
- Particionamento/lifecycle avançado (decisão adiada, não removida — pode entrar no `/design`
  se o volume real justificar)

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

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_BIGQUERY_DATA_WAREHOUSE.md`
