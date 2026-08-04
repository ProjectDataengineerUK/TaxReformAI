# DEFINE: BIGQUERY_DATA_WAREHOUSE

> Espelhar `pareceres_audit_log` (Cloud SQL) num dataset BigQuery permanente, via sync
> incremental diário automático, para consultas analíticas sem competir com o tráfego
> transacional da API em produção.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BIGQUERY_DATA_WAREHOUSE |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O histórico de simulações/consultas gravado em `pareceres_audit_log` (Cloud SQL,
`taxreformai-pg`) não tem uma camada de consulta analítica adequada: rodar dashboards internos,
relatórios de cliente ou análise de negócio direto contra a instância `db-f1-micro` de produção
competiria por recursos com o tráfego transacional real da API.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Equipe interna (produto/negócio) | Consumidor de métricas agregadas de uso | Sem visibilidade de volume por tenant, NCMs/tributos mais consultados, sem escrever SQL ad-hoc contra a instância de produção |
| Cliente/tenant | Consumidor do próprio histórico | Sem forma analítica de consultar seu histórico de simulações fora do fluxo transacional síncrono da API |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Dataset e tabela BigQuery provisionados via Terraform, espelhando `pareceres_audit_log` (mesmas colunas, JSONB → `JSON` nativo do BigQuery) |
| **MUST** | Script de sync incremental (watermark por `created_at`/`id`), sem duplicar linhas em execuções repetidas |
| **MUST** | Sync respeita RLS — lê cada tenant via `sessao_do_tenant()` (mesmo mecanismo já auditado do resto do projeto), sem introduzir bypass de RLS novo |
| **SHOULD** | Cron diário do GitHub Actions dispara o sync automaticamente |
| **COULD** | Particionamento por data na tabela BigQuery (decisão adiada até o volume real ser medido) |

---

## Success Criteria

- [ ] `terraform apply` cria o dataset + tabela BigQuery reais, sem erro
- [ ] Uma execução do script de sync carrega 100% das linhas novas de `pareceres_audit_log`
      (todos os tenants) desde a última execução
- [ ] Rodar o script de sync duas vezes seguidas sem novas linhas no Cloud SQL produz ZERO linhas
      duplicadas no BigQuery
- [ ] Uma consulta SQL real no BigQuery confirma: `COUNT(*)` bate com `SELECT COUNT(*) FROM
      pareceres_audit_log` no Cloud SQL (mesmo tenant, mesma janela de tempo)
- [ ] O cron do GitHub Actions dispara pelo menos uma vez sem intervenção manual, confirmado por
      um `gh run list` real

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Provisionamento real | `infra/terraform/main.tf` com os novos recursos BigQuery | `terraform apply` via `workflow_dispatch` | Dataset `taxreformai_analytics` e tabela existem no GCP real, sem erro de permissão |
| AT-002 | Sync inicial (carga completa) | BigQuery vazio, `pareceres_audit_log` com linhas de múltiplos tenants | Script de sync roda pela primeira vez | Todas as linhas de todos os tenants aparecem no BigQuery, com os mesmos valores (inclusive campos mascarados de PII, sem reprocessamento) |
| AT-003 | Sync incremental (idempotência) | BigQuery já sincronizado até um watermark | Script roda de novo sem novas linhas no Cloud SQL | Zero linhas novas/duplicadas no BigQuery |
| AT-004 | Sync incremental (linha nova) | BigQuery sincronizado, uma nova simulação é registrada em `pareceres_audit_log` | Script roda novamente | Só a linha nova aparece no BigQuery, sem re-inserir as antigas |
| AT-005 | Isolamento por tenant respeitado | Múltiplos tenants com dados em `pareceres_audit_log` | Script sincroniza | Nenhuma linha atribuída ao tenant errado no BigQuery — o `tenant_id` de cada linha replicada bate com o de origem |
| AT-006 | Cron dispara sozinho | Workflow com `schedule: cron` configurado | Passa o horário agendado, sem clique manual | `gh run list` mostra uma execução com `event: schedule`, concluída com sucesso |
| AT-007 | Papel de leitura sem bypass de RLS | Nenhuma alteração de policy em `pareceres_audit_log` | Script de sync executa | Lê via `sessao_do_tenant()` iterando cada `tenant_id` de `tenants` — nenhuma policy nova, nenhum papel com `BYPASSRLS` |

---

## Out of Scope

- Modelagem dimensional (star schema, tabelas fato/dimensão) — schema é espelho 1:1
- Dashboard ou ferramenta de BI (Looker Studio, etc.) — consumo fica para feature futura
- Streaming/CDC — freshness diária confirmada como suficiente
- Particionamento/lifecycle avançado da tabela BigQuery — decisão adiada para quando o volume
  real for medido no `/design`/`/build`
- Alterar a policy de RLS de `pareceres_audit_log` — o sync usa o mecanismo já existente
  (`sessao_do_tenant`, loop por tenant), não introduz bypass novo

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Técnico | RLS (`FORCE ROW LEVEL SECURITY`) em `pareceres_audit_log`; NENHUM papel no Cloud SQL tem `BYPASSRLS` (confirmado contra a instância real em `SCHEMA_POSTGRESQL`) | Sync não pode fazer um `SELECT *` cross-tenant direto — precisa iterar por tenant via `sessao_do_tenant()`, união dos resultados |
| Técnico | Instância Cloud SQL é `db-f1-micro`, já serve tráfego real de produção | Sync deve ser leve (batch diário, não contínuo) para não competir por recursos |
| Segurança | `prompt_consulta`/`resposta_parecer_md` já passam por mascaramento de PII antes da gravação no audit log | Sync replica os campos como estão — nenhum reprocessamento, nenhuma reintrodução de PII |
| Custo | BigQuery é serverless (armazenamento + consulta) — perfil de custo oposto ao Cloud Composer, que acabou de ser destruído nesta mesma sessão por custo desproporcional | Dataset/tabela podem ser recursos PERMANENTES no Terraform, sem ciclo efêmero |
| Processo | Primeiro `schedule: cron` do projeto — todo outro workflow de infraestrutura real é `workflow_dispatch`-only | `/design` deve incluir uma guarda equivalente (ex: um "dry-run" ou confirmação na primeira execução manual) antes de confiar no cron sozinho |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `infra/terraform/main.tf` (recursos), `scripts/sincronizar_bigquery.py` (script), `.github/workflows/sincronizar_bigquery.yml` (orquestração) | Segue o padrão de toda feature de infra real do projeto |
| **KB Domains** | N/A | Não é feature de IA/LLM |
| **IaC Impact** | Novos recursos: `google_bigquery_dataset`, `google_bigquery_table`, `google_project_service` (bigquery.googleapis.com), papel/IAM para a SA que roda o sync | Recursos PERMANENTES (diferente do Composer) |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| `pareceres_audit_log` (Cloud SQL `taxreformai-pg`) | Postgres 16, append-only | Não medido nesta sessão — medir no `/design` com uma consulta real de `COUNT(*)` | Escrita síncrona a cada chamada de `/v1/tax/simulate`, `/v1/tax/simulate-simples-nacional`, `/v1/tax/query` |

### Schema Contract
| Column | Type (Postgres → BigQuery) | Constraints | PII? |
|--------|------|-------------|------|
| `id` | `UUID` → `STRING` | Chave primária de origem, usada como watermark secundário | Não |
| `tenant_id` | `UUID` → `STRING` | NOT NULL | Não (identificador de cliente, não de pessoa) |
| `user_id` | `UUID` → `STRING`, nullable | Pode ser NULL (não existe conceito de usuário autenticado) | Não |
| `prompt_consulta` | `TEXT` → `STRING` | Já mascarado de PII antes da gravação (`LLM_REAL_VERTEX_AI`) | Mascarado, não bruto |
| `contexto_recuperado_ids` | `JSONB` → `JSON` | Default `[]` | Não |
| `payload_calculo_json` | `JSONB` → `JSON` | Default `{}` | Não (dados de simulação: NCM, valores, UF — não PII de pessoa física) |
| `resposta_parecer_md` | `TEXT` → `STRING` | NOT NULL | Mascarado, não bruto (mesma disciplina de `prompt_consulta`) |
| `created_at` | `TIMESTAMPTZ` → `TIMESTAMP` | NOT NULL, watermark primário do sync incremental | Não |

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| Tabela BigQuery | Sincronizada com até 24h de atraso do Cloud SQL | Comparar `MAX(created_at)` nos dois lados após uma execução do cron |

### Completeness Metrics
- 100% das linhas de `pareceres_audit_log` (todos os tenants) devem existir no BigQuery após um
  sync completo — verificado por `COUNT(*)` batendo dos dois lados
- Zero linhas duplicadas em execuções repetidas do sync sem dado novo

### Lineage Requirements
- Nenhum requisito de lineage column-level nesta feature — é um espelho 1:1, não uma
  transformação

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `taxreformai_admin` tem `SELECT` suficiente em `tenants` e `pareceres_audit_log` (é o papel usado pelas migrações, dono/privilégio amplo de objeto) | Precisaria de um papel novo dedicado, ou GRANT adicional | [ ] A validar no `/build` contra o Cloud SQL real |
| A-002 | O volume de linhas em `pareceres_audit_log` é pequeno o suficiente para um sync diário simples (sem paginação/streaming) resolver dentro do tempo de execução do GitHub Actions (padrão 6h de limite, folga enorme) | Se o volume crescer muito, o sync pode precisar de paginação por lote | [ ] A medir no `/design` com uma consulta real de `COUNT(*)` |
| A-003 | O `google-cloud-bigquery` client Python consegue rodar no ambiente do GitHub Actions runner sem restrição de rede (mesmo padrão de `qdrant-client`/`google-cloud-storage` já usados em outros workflows) | Improvável dar errado — é um cliente HTTP padrão do Google | [ ] A confirmar no `/build` |

**Note:** A-001 e A-002 são as assunções mais críticas — ambas resolvidas por uma consulta real
de diagnóstico no início do `/build`, mesmo padrão de "diagnosticar antes de construir" já
estabelecido no projeto.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro, específico: instância de produção não deve receber carga analítica; motivação real confirmada com o usuário (3 casos de uso) |
| Users | 3 | Dois personas concretos (equipe interna, cliente/tenant), cada um com dor específica |
| Goals | 3 | MUST/SHOULD/COULD priorizados, com decisão técnica explícita sobre RLS (não adiada) |
| Success | 3 | Critérios com números e comandos verificáveis (`terraform apply`, `COUNT(*)`, `gh run list`) |
| Scope | 2 | Out of Scope claro, mas volume real de dados (A-002) ainda não medido — pequena lacuna que só o `/design`/`/build` resolve com uma consulta real |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** — atendido.

---

## Open Questions

Nenhuma bloqueante. Duas ficam para verificação real no `/design`/`/build` (não bloqueiam o
`/design` em si, mas devem ser as primeiras ações do `/build`):

1. Volume real de `pareceres_audit_log` (A-002) — uma consulta `SELECT COUNT(*)` real antes de
   desenhar a estratégia de paginação do sync.
2. Confirmar que `taxreformai_admin` de fato consegue `SELECT` em `tenants`/`pareceres_audit_log`
   sob o mecanismo `sessao_do_tenant()` sem erro de permissão (A-001).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-04 | (sessão direta) | Versão inicial, extraída do BRAINSTORM |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_BIGQUERY_DATA_WAREHOUSE.md`
