# DEFINE: PAINEL_OBSERVABILIDADE

> Painel dentro do frontend que dá visibilidade ao vivo da saúde da infraestrutura, do custo real
> (infra + token de LLM) e da maturidade/segurança do sistema — hoje só descobertos ad hoc, via
> workflows de diagnóstico disparados manualmente ou quando um usuário reporta um erro.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PAINEL_OBSERVABILIDADE |
| **Date** | 2026-08-05 |
| **Author** | define-agent (a partir de BRAINSTORM_PAINEL_OBSERVABILIDADE.md) |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O projeto opera com um único desenvolvedor/operador e nenhuma visibilidade proativa do próprio
estado: incidentes reais desta mesma sessão (pool de conexões do Cloud SQL esgotado sob carga,
guardrail do sintetizador truncando ~30% das respostas, `tenant_id` divergente causando 403) só
foram descobertos porque um usuário bateu neles em produção — nunca antes, via monitoramento
próprio. Hoje, "ver o estado real" exige disparar manualmente um workflow de diagnóstico
descartável (`diagnostico_cloud_run_logs.yml`) ou ler histórico em `CLAUDE.md`; não existe uma
visão viva, dentro do produto.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador único (Jonatas) | Desenvolve, opera e mantém toda a infraestrutura sozinho | Descobre degradação (pool esgotado, cron falhando, guardrail truncando) só quando um usuário reporta ou quando dispara diagnóstico manual — nenhum sinal proativo |
| Usuários da allowlist (`ALLOWED_EMAILS`) | Já usam `/simulador`/`/consulta` logados via Google | Não pediram isso diretamente, mas herdam visibilidade compartilhada (mesma allowlist, decisão do `/brainstorm`) — ganham transparência sobre custo/saúde do sistema que usam |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Diagrama dinâmico com status verde/amarelo/vermelho dos 6 recursos do caminho de requisição (Frontend, API, Cloud SQL, Qdrant, Anthropic API, Cloud Tasks) |
| **MUST** | Painel sentinela — mesma informação de status em formato tabular, incluindo o sync do BigQuery (único cron do projeto) |
| **MUST** | Registro de custo agregado por serviço (infra, via GCP Billing API) e por chamada real de LLM (token, via instrumentação própria), por dia/mês |
| **SHOULD** | Scorecard de maturidade (MLOps/DataOps/LLMOps, escala 1-5, framework citado) versionado no repositório |
| **SHOULD** | Scorecard de segurança (escala 1-5, OWASP Top 10 + NIST CSF) versionado no repositório |
| **COULD** | Lista curada de achados/oportunidades de FinOps (estático, com base em incidentes reais já documentados) + alertas simples por limiar sobre os dados de custo coletados |

---

## Success Criteria

- [ ] Aba Diagrama/Sentinela carrega o status dos 6 recursos + sync do BigQuery em menos de 5s, sem nova chamada ao GCP dentro da janela de cache de 60s
- [ ] 100% das chamadas reais ao LLM (`ClienteVertexAI` ou `ClienteAnthropicDireto`) geram uma linha na tabela de uso de token — zero chamada "invisível" a partir do deploy desta feature
- [ ] Sync diário de custo de infra roda sem intervenção manual, com a mesma confiabilidade observável do sync do BigQuery já existente (idempotente, sem duplicata em rerun)
- [ ] Scorecard de maturidade tem pelo menos 1 entrada por eixo (MLOps, DataOps, LLMOps) e o de segurança pelo menos 1 nota composta, ambos citando o framework-base
- [ ] Nenhum e-mail fora de `ALLOWED_EMAILS` acessa a rota do painel — mesma garantia hoje provada em `frontend/middleware.ts`
- [ ] A gravação de uso de token nunca bloqueia nem falha uma resposta real ao usuário (best-effort, mesmo padrão de `api/audit.py::registrar_com_seguranca`, que nunca propaga exceção)

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — todos saudáveis | Os 6 recursos + sync do BigQuery estão saudáveis | Usuário abre a aba Diagrama | Todos aparecem verdes, com rótulo do recurso e sem nova chamada ao GCP se dentro da janela de cache |
| AT-002 | Recurso degradado | Cloud SQL com uso de connection pool acima do limiar definido | Status é consultado (ao vivo ou via cache expirado) | Cloud SQL aparece amarelo, com o motivo textual (ex: "pool de conexões acima de X%") |
| AT-003 | Token registrado | Uma consulta real chega ao nó `sintetizador` (Sonnet) | A chamada ao LLM retorna com sucesso | Uma linha nova aparece na tabela de uso de token: modelo, tokens de entrada/saída, nó de origem, tenant, timestamp |
| AT-004 | Falha na gravação de custo não derruba a resposta | A tabela de uso de token está indisponível (ex: Cloud SQL fora do ar) | Uma consulta real chama o LLM | O usuário recebe a resposta normalmente; a falha de gravação é só logada, nunca vira 5xx |
| AT-005 | Acesso negado | Um e-mail fora de `ALLOWED_EMAILS` está logado | Tenta acessar a rota do painel | É redirecionado para `/login`, mesma garantia do middleware já existente |
| AT-006 | Scorecard não é "calculado" | Aba Maturidade é aberta | Frontend busca os dados | Os valores vêm do YAML versionado no repositório — nenhuma consulta em tempo de request tenta "calcular" a nota |
| AT-007 | Sync de custo de infra é idempotente | O sync diário de billing já rodou hoje | O workflow roda de novo no mesmo dia (rerun manual) | Nenhuma duplicata — mesmo padrão de `staging+MERGE` já usado em `sincronizar_bigquery.py` |

---

## Out of Scope

- Tempo real via WebSocket/SSE — carregamento ao abrir a aba + botão de atualizar manual
- Drill-down de custo por requisição individual (só totais agregados por serviço/dia/mês)
- Tendência histórica de maturidade/segurança na v1 (fica disponível "de graça" depois via `git log` do YAML, mas não é renderizada agora)
- Allowlist separada para o painel — reusa `ALLOWED_EMAILS` como está
- Recomendações de FinOps geradas por IA/preditivas — só achados curados + alertas por limiar simples
- GCS, Artifact Registry e o serviço BigQuery em si como "recursos" próprios no diagrama — só entram indiretamente via status do sync
- Custo de Qdrant Cloud e da API Claude direta via GCP Billing API — nenhum dos dois é recurso GCP faturado ali (ver Constraints)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `taxreformai-runtime` hoje não tem nenhuma permissão de leitura de Monitoring/Run Admin/Billing | Precisa de role IAM nova em `infra/terraform/main.tf` — mesmo padrão de desvio documentado já usado por `roles/aiplatform.user` (primeira role de projeto dessa SA) |
| Technical | Nenhuma chamada real ao LLM registra token hoje | Precisa tocar `orquestracao/llm/cliente.py` (`ClienteVertexAI` e `ClienteAnthropicDireto`) + migração nova (`016_*`) |
| Technical | GCP Billing API não cobre Qdrant Cloud nem a API Claude direta (não são recursos GCP) | Custo desses dois fica fora do escopo de "infra via Billing API" — token da Claude já é coberto pela instrumentação própria; custo do Qdrant Cloud fica declarado como indisponível, nunca estimado |
| Resource | Sem orçamento adicional de infraestrutura combinado com o usuário | Preferir reaproveitar mecanismos já existentes (cron do BigQuery, endpoint de diagnóstico) a criar serviços novos |
| Timeline | Nenhum prazo explícito | — |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `api/routers/observabilidade.py` (novo) · `frontend/app/painel/` (novo, com abas) · `db/migrations/016_*` em diante · `.claude/observabilidade/scorecard.yaml` (novo) | Segue os padrões já existentes de router/página/migração do projeto |
| **KB Domains** | Nenhum domínio pronto do AgentSpec cobre "GCP Monitoring/Billing API + FinOps" com precisão — tratar como implementação direta, sem KB específica | `gcp-data-architect`/`database-reviewer` como referências parciais (BigQuery, Cloud SQL), não como fonte única |
| **IaC Impact** | New resources (role IAM nova para `taxreformai-runtime`) + Modify existing (`infra/terraform/main.tf`) | Triggers `/design` a decidir a role mínima exata (`roles/monitoring.viewer`, `roles/run.viewer`, `roles/billing.viewer` — candidatos, não decisão final) |

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| `ClienteVertexAI`/`ClienteAnthropicDireto` (chamadas reais) | In-process (Python) | Dezenas/dia hoje | Gravado na hora de cada chamada | `orquestracao/llm/` |
| GCP Billing API | API externa (GCP) | 1 snapshot/dia por serviço | Diário, via cron | `scripts/` (novo, mesmo padrão de `sincronizar_bigquery.py`) |
| Cloud Monitoring / Cloud Run Admin API | API externa (GCP) | Sob demanda, cache 60s | Ao vivo | `api/routers/observabilidade.py` |

### Schema Contract (tabela de uso de token — nome a definir no `/design`)

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| id | UUID | PK | Não |
| tenant_id | UUID | NOT NULL, RLS (mesma disciplina do resto do schema) | Não |
| modelo | VARCHAR | NOT NULL | Não |
| no_origem | VARCHAR | NOT NULL (classificador / extrator_regras / sintetizador) | Não |
| tokens_entrada | INT | NOT NULL | Não |
| tokens_saida | INT | NOT NULL | Não |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | Não |

### Freshness SLAs

| Layer | Target | Measurement |
|-------|--------|-------------|
| Uso de token | Gravado na mesma operação da chamada real (best-effort, não bloqueante) | Comparação de timestamp com o `historico` do `state` |
| Custo de infra | Snapshot diário via cron | Comparação com a última execução do workflow |

### Completeness Metrics

- 100% das chamadas reais ao LLM devem gerar 1 linha na tabela de uso de token, mas a gravação em
  si nunca pode ser bloqueante (ver AT-004) — "completo quando possível, nunca à custa de derrubar
  a resposta ao usuário"

### Lineage Requirements

- Nenhuma exigência de lineage column-level — volume e criticidade não justificam

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|-------------------|------------|
| A-001 | GCP Billing API consegue segmentar custo por serviço individual (Cloud Run API vs Frontend vs Cloud SQL) com granularidade diária via consulta direta | Precisaria de Billing Export para BigQuery em vez de query direta — mais setup, outro recurso GCP novo | [ ] |
| A-002 | `taxreformai-runtime` pode receber uma role de leitura de Monitoring/Billing sem violar o princípio de privilégio mínimo já estabelecido no projeto | Precisaria de uma SA dedicada só para observabilidade, mesmo padrão de `taxreformai-bigquery-sync` | [ ] |
| A-003 | Instrumentar o registro de token não adiciona latência perceptível a `/v1/tax/query` | Precisaria mover a gravação para fora do caminho síncrono (ex: fire-and-forget real, não só try/except) | [ ] |

**Nota:** Validar A-001 e A-002 é o primeiro passo real do `/design` — ambos podem mudar a
arquitetura de coleta de custo de infra.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Específico, com incidentes reais desta sessão como evidência do problema |
| Users | 2 | Persona primária muito clara (operador único); persona secundária (allowlist) herda acesso mas não tem pain point próprio articulado |
| Goals | 3 | MUST/SHOULD/COULD priorizados, herdados diretamente do YAGNI do `/brainstorm` |
| Success | 3 | Critérios mensuráveis e testáveis, incluindo o caso de falha (AT-004) |
| Scope | 3 | Fora de escopo extremamente explícito, com motivo para cada corte |
| **Total** | **14/15** | Acima do mínimo de 12/15 — pronto para `/design` |

---

## Open Questions

Nenhuma bloqueante para `/design` — mas A-001 e A-002 (Billing API por serviço; role IAM mínima)
precisam ser investigadas logo no início do `/design`, antes de desenhar o schema/endpoint final
de custo de infra.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-05 | define-agent | Versão inicial, extraída de BRAINSTORM_PAINEL_OBSERVABILIDADE.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_PAINEL_OBSERVABILIDADE.md`
