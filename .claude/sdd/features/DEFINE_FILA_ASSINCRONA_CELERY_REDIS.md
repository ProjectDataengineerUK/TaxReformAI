# DEFINE: FILA_ASSINCRONA_CELERY_REDIS

> Torna o upload de SKUs sempre assíncrono via Cloud Tasks (não Celery/Redis — ver Revisão),
> removendo o teto de 10.000 linhas/5MB da versão síncrona atual, para sustentar catálogos de
> 50.000+ SKUs, sem introduzir VPC nem infraestrutura sempre ligada.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FILA_ASSINCRONA_CELERY_REDIS |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

**Nota de revisão:** o nome da feature preserva o rótulo original do roadmap (`ROADMAP_SEQUENCIA_
AUDITORIA_2026-07.md`, posição 11), mas o mecanismo mudou de Celery+Redis para **Cloud Tasks**
depois que o `/brainstorm` (2ª rodada) descobriu que o Memorystore Redis exige VPC + Serverless
VPC Access connector — custo real ~US$60-70/mês e o primeiro recurso do projeto inteiro a sair da
disciplina "sem VPC" mantida em toda decisão de infraestrutura anterior. Ver
`BRAINSTORM_FILA_ASSINCRONA_CELERY_REDIS.md` para o histórico completo das duas rodadas.

---

## Problem Statement

`POST /v1/tax/skus/upload` processa o CSV de forma síncrona, com um teto de 10.000 linhas/5MB —
insuficiente para a persona de "Grandes Varejistas e E-commerce" (50.000+ SKUs) prevista no
blueprint, sem exceder o tempo de resposta HTTP razoável de uma requisição síncrona.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Tenant com catálogo grande (planos Business/Enterprise) | Consumidor de `/v1/tax/skus/upload` | Não consegue subir mais de 10.000 SKUs numa única chamada síncrona sem timeout |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `POST /v1/tax/skus/upload` devolve `202 Accepted` + `job_id` imediatamente, sempre — nunca processa a planilha na mesma requisição |
| **MUST** | Cloud Tasks dispara um endpoint interno no MESMO serviço Cloud Run da API, reaproveitando 100% de `parsear_linha_csv`/`upsert_sku` já existentes — nenhuma duplicação de lógica de negócio, nenhum serviço/worker novo |
| **MUST** | `GET /v1/tax/skus/upload/{job_id}` reporta status e resultado final, lendo de uma tabela nova (`sku_upload_jobs`) com RLS por tenant |
| **MUST** | Payload do arquivo trafega via staging em GCS, não embutido na mensagem da Cloud Task |
| **MUST** | O endpoint interno de processamento só aceita chamadas legítimas do Cloud Tasks (verificação de token/cabeçalho), nunca uma chamada externa direta |
| **SHOULD** | Teto de linhas/tamanho aumenta substancialmente (não mais 10.000/5MB) — valor exato decidido no `/design` |
| **COULD** | Particionar processamento em múltiplas Cloud Tasks (lotes), se um upload de 50.000+ linhas numa única chamada se aproximar do timeout do Cloud Run |

---

## Success Criteria

- [ ] Cloud Tasks queue e bucket GCS de staging provisionados via Terraform, reais, verificados —
      **sem VPC, sem Redis, sem worker dedicado**
- [ ] `POST /v1/tax/skus/upload` responde em menos de 1s com `202` + `job_id`, independente do
      tamanho do arquivo (dentro do novo teto)
- [ ] Um upload real de pelo menos 50.000 linhas processa com sucesso via fila, sem timeout HTTP
      em nenhuma etapa
- [ ] `GET /v1/tax/skus/upload/{job_id}` de um tenant nunca retorna dados de um job de outro
      tenant (mesmo com `job_id` correto adivinhado)
- [ ] Uma chamada HTTP direta (sem o cabeçalho/token do Cloud Tasks) ao endpoint interno de
      processamento é rejeitada
- [ ] Reenviar a mesma planilha duas vezes continua fazendo UPSERT por linha, não duplica SKUs

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Provisionamento real | `infra/terraform/main.tf` com Cloud Tasks queue + bucket de staging + migração `sku_upload_jobs` | `terraform apply`/`migrar_banco.yml` via `workflow_dispatch` | Recursos existem no GCP/Cloud SQL reais, sem erro de permissão — nenhum recurso de VPC/Redis |
| AT-002 | Upload sempre assíncrono | API real, arquivo pequeno (10 linhas) | `POST /v1/tax/skus/upload` | Resposta `202` com `job_id`, sem os resultados por linha no corpo |
| AT-003 | Processamento real via Cloud Tasks | Job enfileirado (AT-002) | Cloud Tasks dispara o endpoint interno | `GET /v1/tax/skus/upload/{job_id}` eventualmente reporta `CONCLUIDO`, com `criados`/`atualizados`/`erros` batendo com o arquivo enviado |
| AT-004 | Isolamento de tenant no polling | Job de um tenant A concluído | Tenant B tenta `GET /v1/tax/skus/upload/{job_id}` de A | `404`/`403` — nunca vaza o resultado de A |
| AT-005 | Endpoint interno protegido | Nenhum cabeçalho/token do Cloud Tasks | Chamada HTTP direta ao endpoint de processamento | `401`/`403` — nunca processa uma chamada não autenticada como Cloud Tasks |
| AT-006 | Volume real de 50.000+ linhas | Arquivo real gerado com 50.000+ linhas válidas | Upload completo via fila | Processa com sucesso, sem timeout HTTP, `criados` bate com o total de linhas válidas |
| AT-007 | UPSERT preservado | SKU já existe (de um upload anterior) | Reenviar a mesma planilha | `atualizados` incrementa, `criados` não — nenhum SKU duplicado |
| AT-008 | Erro de linha não trava o job | Arquivo com linhas inválidas misturadas com válidas | Endpoint interno processa | Job conclui com `erros > 0` mas as linhas válidas foram commitadas |

---

## Out of Scope

- Celery + Memorystore Redis (rejeitado no `/brainstorm`, 2ª rodada — custo real e introdução de
  VPC)
- Worker Cloud Run dedicado
- Fila assíncrona genérica para outros fluxos além do upload de SKUs
- Caminho síncrono preservado para uploads pequenos
- Particionamento em lotes/múltiplas Cloud Tasks por upload (fica como **COULD**, só se AT-006
  revelar risco real de timeout)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Técnico | Cloud Tasks invoca o endpoint interno via HTTP com um token OIDC assinado pelo Google — o endpoint precisa verificar esse token, não confiar em "veio do IP certo" ou algo mais fraco | Define o mecanismo real de proteção do endpoint interno (AT-005) |
| Técnico | O processamento inteiro do arquivo acontece numa ÚNICA chamada HTTP disparada pelo Cloud Tasks — sujeito ao timeout configurado do serviço Cloud Run | `/design` decide o timeout necessário; `/build` mede o tempo real com um arquivo de 50.000+ linhas (AT-006) antes de confiar no valor escolhido |
| Custo | Cloud Tasks cobra por execução (praticamente zero no volume esperado), bucket GCS cobra por armazenamento (mitigado por lifecycle curto) — nenhum componente cobrado por hora/sempre ligado | Mantém a disciplina de custo já estabelecida desde `BIGQUERY_DATA_WAREHOUSE` |
| Segurança | `sku_upload_jobs` precisa de RLS — mesma disciplina de `pareceres_audit_log`/`empresa_skus` | Migração nova segue o padrão já auditado, não inventa um mecanismo de isolamento diferente |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `api/routers/empresa_skus.py` (modificar), novo endpoint interno no mesmo router ou um novo `api/routers/skus_tasks.py`, `infra/terraform/main.tf`, `db/migrations/0XX_sku_upload_jobs.sql` | Endpoint de processamento reusa o MESMO serviço/imagem Cloud Run da API — nenhum Dockerfile novo |
| **KB Domains** | N/A | Não é feature de IA/LLM |
| **IaC Impact** | Novos recursos: Cloud Tasks queue, bucket GCS de staging (lifecycle curto, ex: expira em 1 dia), permissão IAM para o Cloud Tasks invocar o Cloud Run da API | Sem VPC, sem Redis, sem worker — todos os recursos são serverless ou reaproveitam o que já existe |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| `sku_upload_jobs` (nova) | Postgres, escrita pelo endpoint interno | 1 linha por upload | Tempo real (criada no enqueue, atualizada ao concluir) | API |

### Schema Contract
| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `id` | UUID | PK, é o `job_id` exposto na API | Não |
| `tenant_id` | UUID | NOT NULL, RLS | Não |
| `status` | TEXT/enum | `PENDENTE`/`PROCESSANDO`/`CONCLUIDO`/`ERRO` | Não |
| `gcs_uri_arquivo` | TEXT | NOT NULL | Não |
| `resultado_json` | JSONB | NULL até concluir — mesmo formato de `RespostaUploadCsv` | Não |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL | Não |

### Freshness SLAs
Não aplicável — não é um data warehouse, é status transacional de um job.

### Completeness Metrics
- Todo `job_id` criado em `POST /upload` deve eventualmente chegar a `CONCLUIDO` ou `ERRO` — nunca
  ficar `PROCESSANDO` indefinidamente (a validar com um teste real, se o Cloud Tasks retry
  automático mascarar uma falha silenciosa)

### Lineage Requirements
Não aplicável.

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Processar 50.000+ linhas numa única chamada HTTP síncrona (dentro do timeout configurável do Cloud Run, até 60 min) é suficiente, sem precisar particionar em múltiplas Cloud Tasks | Precisaria implementar o particionamento (COULD do Goals) | [ ] A medir no `/build` com um arquivo real de 50.000+ linhas (AT-006) |
| A-002 | A verificação do token OIDC do Cloud Tasks no endpoint interno é um mecanismo padrão e bem documentado do GCP (Cloud Run + Cloud Tasks), não uma configuração exótica | Precisaria de um mecanismo de autenticação alternativo | [ ] A confirmar no `/design` contra a documentação/Terraform provider atual, e no `/build` contra uma chamada real |
| A-003 | O volume real de uploads simultâneos é baixo o suficiente para não precisar de configuração especial de concorrência da fila Cloud Tasks | Se muitos tenants fizerem upload ao mesmo tempo, pode ser necessário limitar taxa de despacho | [ ] Não validado — fora de escopo até haver sinal real de uso concorrente |

**Note:** A-001 e A-002 são as mais críticas. Ambas exigem verificação contra infraestrutura real
antes do `/ship` — mesma disciplina de "diagnosticar antes de confiar" já estabelecida no projeto.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro, específico, com o teto exato e a persona que o motiva |
| Users | 3 | Persona concreta, com dor específica |
| Goals | 3 | MUST/SHOULD/COULD priorizados, decisões técnicas (staging GCS, proteção do endpoint) já resolvidas |
| Success | 3 | Critérios com números e comandos verificáveis |
| Scope | 2 | Out of Scope claro, mas A-001/A-002 são lacunas técnicas reais que só o `/design`/`/build` fecham |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** — atendido.

---

## Open Questions

Nenhuma bloqueante. Duas ficam para verificação real:

1. A-001 — tempo real de processamento de 50.000+ linhas numa única chamada, antes de decidir se
   o particionamento em lotes é necessário.
2. A-002 — confirmar a sintaxe exata do Terraform/gcloud para a autenticação OIDC do Cloud Tasks
   contra o Cloud Run, no início do `/design`, antes de desenhar o resto do file manifest.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-04 | (sessão direta) | Versão inicial, mecanismo Celery+Redis |
| 2.0 | 2026-08-04 | (sessão direta) | Reescrita completa: mecanismo trocado para Cloud Tasks após achado real de VPC/custo no `/brainstorm` (2ª rodada) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_FILA_ASSINCRONA_CELERY_REDIS.md`
