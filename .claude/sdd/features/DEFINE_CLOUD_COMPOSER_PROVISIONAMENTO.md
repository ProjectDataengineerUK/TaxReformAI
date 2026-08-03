# DEFINE: Provisionamento Real do Cloud Composer

> Provisionar um ambiente Cloud Composer real, disparar `dags/ingestao_legal_dag.py` de verdade,
> registrar evidência de execução, e destruir o ambiente — ciclo efêmero, não infraestrutura
> permanente.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLOUD_COMPOSER_PROVISIONAMENTO |
| **Date** | 2026-08-03 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

`dags/ingestao_legal_dag.py` (shipado em `INGESTAO_TCU_E_ETL_AIRFLOW`) escreve a orquestração
real do Airflow/Cloud Composer para a ingestão legal (2 tasks paralelas — `ingest_planalto` e
`ingest_tcu`), mas nunca rodou contra um Cloud Composer de verdade: `apache-airflow` não instala
no sandbox de desenvolvimento, então a única validação até hoje foi revisão de código. O projeto
não tem prova real de que a DAG é descoberta pelo scheduler, executa as tasks corretamente, e
produz o mesmo resultado que `ingestion/pipeline.py` (CLI) já produz via `workflow_dispatch`.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Equipe de engenharia do projeto | Mantém `dags/ingestao_legal_dag.py` e decide sobre a orquestração de ingestão | Não sabe se a DAG shipada realmente funciona num Cloud Composer real — só tem revisão de código como garantia |
| Jonatas (dono do projeto) | Decide sobre custo de infraestrutura | Precisa da prova de execução real sem comprometer o projeto a um custo mensal recorrente desproporcional ao volume de trabalho (2 tasks/semana) |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Provisionar um ambiente Cloud Composer 3 real (preset Small) via Terraform |
| **MUST** | Reusar a SA `taxreform-ingestion` (já existente, já com acesso ao bucket GCS) como identidade do ambiente, adicionando `roles/composer.worker` |
| **MUST** | Copiar `dags/ingestao_legal_dag.py` para o ambiente e confirmar que o scheduler do Airflow a descobre |
| **MUST** | Disparar a DAG manualmente e confirmar que as 2 tasks (`ingest_planalto`, `ingest_tcu`) concluem com sucesso, com log real do Airflow como evidência |
| **MUST** | Confirmar que a reingestão é idempotente (não duplica pontos no Qdrant — mesmo mecanismo de `point_id` determinístico já provado em `PIPELINE_INGESTAO_LEGAL`) |
| **MUST** | Destruir o ambiente Composer ao final da verificação, registrando a evidência ANTES do destroy |
| **SHOULD** | Confirmar que a SA de Terraform (`GCP_SA_KEY`) já tem permissão para criar o ambiente, sem assumir |
| **COULD** | Nenhum item adicional — escopo deliberadamente restrito |

---

## Success Criteria

- [ ] `terraform apply` cria o ambiente Composer 3 (preset Small) sem erro
- [ ] `composer.googleapis.com` habilitada; `roles/composer.worker` concedido a `taxreform-ingestion`
- [ ] A DAG `ingestao_legal_taxreformai` aparece na UI/CLI do Airflow do ambiente (descoberta confirmada)
- [ ] As 2 tasks concluem com status `success`, log real capturado (não só "ambiente no ar")
- [ ] Contagem de pontos no Qdrant antes/depois da execução confirma que não houve duplicação (mesmo total, ou aumento só se havia conteúdo genuinamente novo)
- [ ] Evidência (logs, contagens) registrada no BUILD_REPORT antes do `terraform destroy`
- [ ] `terraform destroy` (ou remoção do recurso + reapply) remove o ambiente Composer ao final — nenhum recurso Composer permanece ativo depois do `/ship`

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Ambiente provisiona com sucesso | Terraform com o novo recurso `google_composer_environment` | `terraform apply` via `workflow_dispatch` | Ambiente Composer 3 (Small) criado, sem erro, `composer.googleapis.com` habilitada |
| AT-002 | DAG é descoberta pelo scheduler | Ambiente no ar, `dags/ingestao_legal_dag.py` copiada para o bucket de DAGs do ambiente | Consulta à UI/CLI do Airflow (`gcloud composer environments run ... dags list` ou equivalente) | `ingestao_legal_taxreformai` aparece listada, sem erro de import |
| AT-003 | Execução real das 2 tasks | DAG descoberta | Disparo manual (`gcloud composer environments run ... dags trigger` ou equivalente) | `ingest_planalto` e `ingest_tcu` concluem com status `success`, log real do Airflow confirma |
| AT-004 | Reingestão idempotente | Qdrant já tem os pontos de Planalto/TCU de execuções anteriores (via `ingestao.yml`) | A DAG reingere as mesmas 2 fontes | Contagem de pontos no Qdrant não duplica — mesmo total antes/depois (ou aumento só por conteúdo genuinamente novo, nunca por reingestão do mesmo dispositivo) |
| AT-005 | Ambiente destruído ao final | Evidência de AT-001 a AT-004 já registrada | `terraform destroy` (escopado ao recurso Composer) | Ambiente removido; `main.tf` não tem mais o recurso ativo; nenhuma cobrança contínua remanescente |
| AT-006 | SA de Terraform tem permissão suficiente | `GCP_SA_KEY` autentica `terraform.yml` | `terraform apply` tenta criar o ambiente | Sucesso sem erro de permissão — se faltar `composer.environments.create`, é um achado real a corrigir (não assumir de antemão) |

---

## Out of Scope

- Deixar o ambiente Composer rodando permanentemente após esta feature (decisão explícita do usuário, dado o custo real ~US$300-400/mês)
- Reescrever ou expandir `dags/ingestao_legal_dag.py` (novas fontes, novas tasks)
- VPC dedicada / rede privada para o ambiente
- Monitoramento/alerting do Airflow
- Qualquer mudança em `ingestion/pipeline.py`, `ingestion/config.py`, ou nos scrapers/parsers já shipados

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Custo | Ambiente Composer 3 custa de verdade ~US$300-400/mês se deixado rodando continuamente (achado de pesquisa desta sessão — bem acima do piso teórico de ~US$39/mês por DCU) | Ciclo de vida efêmero: provisionar, verificar, destruir na mesma sessão — nunca um recurso permanente sem essa disciplina |
| Tempo | Provisionar e destruir um ambiente Composer leva ~20-30 minutos cada operação | A sessão de build precisa reservar esse tempo; não é uma operação instantânea como `gcloud run deploy` |
| Técnico | `apache-airflow` não instala neste sandbox de desenvolvimento | Mesma situação já aceita em `INGESTAO_TCU_E_ETL_AIRFLOW` — a DAG em si não é testável localmente; toda verificação desta feature é contra o ambiente real |
| Política do projeto | Infraestrutura real nunca roda local | Toda ação (provisionar, disparar a DAG, destruir) via `workflow_dispatch`, nunca `gcloud` local |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `infra/terraform/main.tf` (temporário, removido ao final) + possível novo script/workflow para disparar a DAG e capturar evidência | Segue o padrão já usado por `scripts/verificar_*_producao.py` para outras features, adaptado à CLI do Composer/Airflow em vez de SQL |
| **KB Domains** | airflow-specialist, gcp-data-architect | `airflow-specialist` para confirmar a forma correta de disparar/inspecionar a DAG via `gcloud composer`; `gcp-data-architect` para o recurso Terraform |
| **IaC Impact** | Novos recursos temporários: `google_project_service.composer` + `google_composer_environment` + `google_project_iam_member` (`roles/composer.worker` para `taxreform-ingestion`) — todos destinados a ser destruídos ao final desta feature | Primeira feature do projeto com um recurso Terraform explicitamente TEMPORÁRIO por desenho, não permanente |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `GCP_SA_KEY` (SA de Terraform) já tem permissão para criar ambientes Composer (`composer.environments.create`) | Precisaria de um `google_project_iam_member` adicional para essa SA antes do `apply` funcionar | [ ] A validar no `/build` — Success Criteria/AT-006 cobre isso explicitamente |
| A-002 | Reusar `taxreform-ingestion` como SA do ambiente Composer funciona sem conflito com seu uso atual (bucket GCS) | Precisaria criar uma SA nova dedicada | [ ] A validar no `/build` |
| A-003 | Composer 3 não exige VPC customizada (confirmado via pesquisa nesta sessão) | Precisaria provisionar rede — mudança de escopo maior | [x] Confirmado via documentação/pesquisa nesta sessão |
| A-004 | O tempo de sessão disponível é suficiente para provisionar (~20-30min) + verificar + destruir (~20-30min) sem interrupção | Precisaria retomar em uma sessão seguinte, com o ambiente ainda cobrando enquanto isso | [ ] Risco aceito — se a sessão for interrompida com o ambiente no ar, o `/ship`/BUILD_REPORT deve deixar isso extremamente claro como blocker de custo, não como pendência comum |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro: DAG existe, nunca rodou contra infraestrutura real, único caminho de validação até agora é revisão de código |
| Users | 2 | Usuários internos (equipe de engenharia, dono do projeto) — não há usuário final externo desta feature de infraestrutura |
| Goals | 3 | Priorizados, cada um mapeado a uma ação concreta (Terraform, disparo da DAG, destroy) |
| Success | 3 | Critérios testáveis e sequenciais (provisiona → descobre → executa → idempotente → evidência → destrói) |
| Scope | 3 | Out of Scope explícito, incluindo a decisão central (não permanente) com justificativa de custo |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma bloqueante para `/design`. A-001/A-002/A-004 ficam para validação durante `/build`, não
são bloqueantes de requisitos.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-03 | define-agent | Initial version, extraído de BRAINSTORM_CLOUD_COMPOSER_PROVISIONAMENTO.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_CLOUD_COMPOSER_PROVISIONAMENTO.md`
