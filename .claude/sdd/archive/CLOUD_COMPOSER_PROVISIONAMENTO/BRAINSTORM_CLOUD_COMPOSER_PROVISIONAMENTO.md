# BRAINSTORM: Provisionamento Real do Cloud Composer

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 7 de 11** da "primeira leva" (ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLOUD_COMPOSER_PROVISIONAMENTO |
| **Date** | 2026-08-03 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 7 de 11 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** `dags/ingestao_legal_dag.py` (shipado em `INGESTAO_TCU_E_ETL_AIRFLOW`) escreve a
orquestração real do Airflow/Cloud Composer (TaskFlow API, 2 tasks — `ingest_planalto` e
`ingest_tcu`, paralelas, schedule `@weekly`) mas nunca rodou contra um Cloud Composer real:
`apache-airflow` não instala neste sandbox de desenvolvimento (`externally-managed-environment`),
então a DAG só foi validada por revisão de código até agora.

**Context Gathered (nesta sessão):**

- `dags/ingestao_legal_dag.py` (113 linhas): 2 `@task` (`ingest_planalto`, `ingest_tcu`), cada uma
  uma chamada fina a `executar_pipeline()` (já testada isoladamente com fakes em
  `tests/test_pipeline_integration.py`/`tests/test_resolucao_pipeline_integration.py`). Sem
  dependência entre as tasks — o Airflow as roda em paralelo automaticamente.
- `ingestion/config.py::Settings.from_env()` já lista as env vars obrigatórias
  (`GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `QDRANT_URL`, `QDRANT_API_KEY`) e opcionais — mesmo
  conjunto que `ingestao.yml` (o workflow atual que roda a pipeline via CLI, sem Composer) já
  usa via GitHub Secrets.
- `infra/terraform/main.tf` já tem `google_service_account.ingestion_sa` (`taxreform-ingestion`,
  criada em `PIPELINE_INGESTAO_LEGAL`) com `roles/storage.objectAdmin` escopado ao bucket
  `taxreformai-dev-legal-docs` — criada exatamente para "o que roda a pipeline de ingestão",
  hoje sem consumidor real (o workflow `ingestao.yml` usa outra identidade). Candidata natural a
  virar a SA do ambiente Composer, em vez de criar uma terceira SA.
- `terraform.yml` autentica com `GCP_SA_KEY` (SA de Terraform, diferente de `GCP_DEPLOYER_SA_KEY`
  do `deploy.yml`) — precisa de `composer.environments.create` (via `roles/composer.admin` ou
  equivalente) para criar o ambiente; não confirmado nesta sessão se essa SA já tem escopo
  suficiente (provavelmente sim, é a identidade "administrativa" do Terraform deste projeto, mas
  o `/build` deve validar, não assumir).
- **Achado de custo real, via pesquisa nesta sessão**: Cloud Composer 3 cobra por DCU
  (Data Compute Unit), não por "tier fixo" — mas o piso TEÓRICO (~US$39/mês para um ambiente
  "Small") diverge bastante de relatos de custo REAL rodando continuamente (~US$300-400/mês),
  porque o scheduler/webserver/banco de metadados do Airflow ficam sempre ativos,
  independentemente de quantas tasks rodam. É uma ordem de grandeza diferente de tudo que este
  projeto já provisionou (Cloud Run escala a zero; Cloud SQL `db-f1-micro`; GCS é centavos).
- **Achado de arquitetura, via pesquisa nesta sessão**: Composer 3 (diferente de Composer 1/2)
  NÃO exige uma VPC customizada — usa rede gerenciada pelo Google por padrão, o que mantém o
  padrão já estabelecido neste projeto de evitar complexidade de VPC (mesma decisão já tomada
  para o Cloud SQL, com IP público sem redes autorizadas).
- **Achado de política, via pesquisa nesta sessão**: desde abril de 2025, novos ambientes Cloud
  Composer exigem uma service account explícita (não usam mais a SA padrão do Compute Engine) —
  reforça a necessidade de decidir entre reusar `taxreform-ingestion` ou criar uma nova.
- **Decisão do usuário, nesta sessão**: dado o custo real (~US$300-400/mês se deixado rodando
  continuamente, contra ~2 tasks/semana de trabalho real), o ambiente deve ser **provisionado,
  verificado, e destruído** na mesma sessão — não uma feature "provisionar e deixar no ar
  permanentemente". A evidência da execução real (logs do Airflow mostrando as 2 tasks
  concluídas, dados novos no Qdrant se houver) fica registrada no BUILD_REPORT/SHIPPED antes do
  `terraform destroy`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Custo do ambiente | ~US$300-400/mês rodando continuamente; a DAG roda 2 tasks/semana | Ciclo de vida "provisionar → verificar → destruir" na mesma sessão, não um recurso Terraform permanente no `main.tf` — ou, se permanecer no `main.tf`, o `/build` deve terminar com um `terraform destroy` explícito, documentado |
| SA do ambiente | `taxreform-ingestion` já existe, já tem acesso ao bucket GCS, sem consumidor real hoje | Reusar, em vez de criar uma nova — só precisa ganhar `roles/composer.worker` |
| Rede | Composer 3 não exige VPC customizada | Mantém o padrão "sem VPC" já estabelecido para Cloud SQL — não é um novo tipo de complexidade de rede |
| SA de Terraform | `GCP_SA_KEY` precisa de `composer.environments.create` | `/build` deve verificar (não assumir) que a SA de Terraform já tem escopo suficiente; se não tiver, é um achado real a corrigir |
| API a habilitar | `composer.googleapis.com` | Novo `google_project_service`, mesmo padrão já usado para `aiplatform.googleapis.com`/`sqladmin.googleapis.com` |
| Env vars da DAG | `GCP_PROJECT_ID`/`GCS_BUCKET_NAME`/`QDRANT_URL`/`QDRANT_API_KEY` (já em GitHub Secrets) | Precisam virar `env_variables` do `software_config` do ambiente Composer (Terraform) — mesmos valores, novo destino |
| Verificação real | DAG nunca rodou contra Airflow de verdade | Critério de sucesso não pode ser só "o `terraform apply` funcionou" — precisa da DAG disparada manualmente (ou aguardar o schedule) e as 2 tasks concluídas com sucesso, evidenciado por log real do Airflow |
| Relevant KB Domains | airflow-specialist, gcp-data-architect | `dags/ingestao_legal_dag.py` já foi escrito seguindo TaskFlow API; esta feature é sobre infraestrutura/execução real, não sobre reescrever a DAG |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Prosseguir com a posição 7 (Cloud Composer) dado o custo contínuo, bem diferente do resto da infra do projeto? | "Seguir com /brainstorm normalmente" | Autorizado a continuar |
| 2 | Dado o achado mais preciso de custo real (~US$300-400/mês, não ~US$39), manter o plano original (deixar rodando) ou provisionar/verificar/destruir? | "Provisionar, verificar a DAG, depois destruir" | Decisão central da feature: ciclo de vida efêmero, não uma feature de infraestrutura permanente |
| 3 | A DAG já existe e já foi revisada (`INGESTAO_TCU_E_ETL_AIRFLOW`) — o escopo desta feature é só infraestrutura/execução real, sem reescrever a DAG? | Confirmado pelo contexto já levantado — `dags/ingestao_legal_dag.py` não muda | Escopo restrito a Terraform + verificação, não a lógica das tasks |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| DAG já escrita | `dags/ingestao_legal_dag.py` | 1 DAG, 2 tasks | Não muda nesta feature |
| Fontes já ingeridas (para detectar re-ingestão) | Qdrant `legislacao_tributaria` | 6866 pontos (Planalto + CGIBS + RFB + TCU) | A DAG reingerindo Planalto/TCU deve ser idempotente (mesmo `point_id` determinístico) — não deve duplicar |
| Evidência de execução real | Nenhuma ainda | 0 | Este é o objetivo central da feature: gerar essa evidência pela primeira vez |

---

## Approaches Explored

### Approach A: Provisionar → verificar → destruir, evidência registrada antes do destroy ⭐ Recomendada

**What:** Terraform cria o ambiente Composer (via `terraform.yml`, `workflow_dispatch`,
`action=apply`), o DAG é copiado para o bucket de DAGs do ambiente, disparado manualmente (via
`gcloud composer environments run` ou pela UI do Airflow), os logs das 2 tasks são capturados
como evidência real, e o ambiente é destruído (`terraform destroy` ou removendo o recurso do
`main.tf` e reaplicando) na mesma sessão.

**Pros:**
- Custo real de poucas horas (provisionamento + verificação), não meses
- Ainda entrega o que a posição 7 do roadmap pede: prova real de que a DAG roda num Cloud
  Composer de verdade, não só revisão de código
- Consistente com a decisão do usuário nesta sessão

**Cons:**
- Não deixa uma "orquestração real e permanente" — se o produto precisar de ingestão agendada
  de verdade no futuro, será preciso reprovisionar (aceito: a ingestão continua rodando via
  `ingestao.yml`/`workflow_dispatch` manual, que já funciona e já está em produção)
- Ambiente Composer leva ~20-30 min para subir e para destruir — a sessão de build precisa
  reservar esse tempo

**Why Recommended:** Entrega a prova de execução real que a posição 7 pede, sem comprometer o
projeto a um custo mensal recorrente de centenas de dólares por uma DAG que roda 2 tasks/semana.

### Approach B: Provisionar e deixar permanentemente (plano original do roadmap)

**What:** `google_composer_environment` vira um recurso permanente do `main.tf`, como o Cloud
SQL ou o Cloud Run.

**Pros:**
- Ingestão agendada de verdade, sem depender de disparo manual do `ingestao.yml`

**Cons:**
- ~US$300-400/mês recorrentes por uma DAG que processa 2 fontes, atualizadas raramente (LCP
  214/2025 e a Resolução TCU não mudam com frequência) — desproporcional ao valor entregue hoje
- Rejeitado explicitamente pelo usuário nesta sessão, à luz do achado de custo real

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — provisionar, verificar, destruir, evidência registrada |
| **User Confirmation** | Confirmado nesta sessão após o achado de custo real (~US$300-400/mês) |
| **Reasoning** | Prova a execução real sem compromisso financeiro recorrente desproporcional ao uso |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Ciclo de vida efêmero (provisionar → verificar → destruir), não um recurso permanente | Custo real (~US$300-400/mês) desproporcional a uma DAG de 2 tasks/semana | Deixar rodando permanentemente — rejeitado pelo usuário nesta sessão |
| 2 | Reusar `taxreform-ingestion` (SA já existente) como identidade do ambiente Composer | Já existe, já tem acesso ao bucket GCS, sem consumidor real hoje — evita criar uma terceira SA para a mesma função | Criar uma SA nova dedicada — rejeitado, duplicaria uma identidade que já existe para exatamente este propósito |
| 3 | Sem VPC customizada | Composer 3 não exige — mantém o padrão "sem VPC" já estabelecido para Cloud SQL | Provisionar uma VPC dedicada — rejeitado, complexidade desnecessária que a própria plataforma já resolve |
| 4 | `dags/ingestao_legal_dag.py` não muda nesta feature | Já escrita e revisada em `INGESTAO_TCU_E_ETL_AIRFLOW`; esta feature é sobre infraestrutura/execução, não lógica de negócio | Reescrever a DAG "por precaução" — rejeitado, sem necessidade demonstrada |
| 5 | Ambiente "Small" (o menor preset disponível) | Suficiente para 2 tasks/semana, minimiza custo durante a janela de verificação | Ambiente maior — rejeitado, sem necessidade |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Orquestração agendada permanente via Composer | Custo desproporcional ao volume de trabalho (2 tasks/semana); `ingestao.yml` já cobre a necessidade real de disparo manual | Sim, se o volume de fontes/frequência de atualização justificar no futuro |
| Adicionar novas fontes de ingestão à DAG | Fora de escopo — esta feature é sobre PROVAR que a DAG existente roda, não expandir o que ela ingere | Sim, como feature própria futura |
| VPC dedicada / rede privada | Composer 3 não exige; sem requisito de isolamento de rede levantado | Sim, se um requisito de compliance futuro exigir |
| Monitoramento/alerting do Airflow | Nenhum requisito de observabilidade levantado; ambiente é efêmero | Sim, se o ambiente se tornar permanente no futuro |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Prosseguir dado o custo recorrente do Composer | ✅ | Confirmado | Mantido |
| Achado de custo real mais preciso (~US$300-400/mês) muda a decisão? | ✅ | Sim — mudou de "deixar rodando" para "provisionar/verificar/destruir" | Escopo ajustado para ciclo de vida efêmero |

**Minimum Validations:** 2 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
`dags/ingestao_legal_dag.py` orquestra a ingestão real de 2 fontes legais (Planalto, TCU) via
TaskFlow API do Airflow, mas nunca rodou contra um Cloud Composer real — `apache-airflow` não
instala no sandbox de desenvolvimento, então a única validação até agora foi revisão de código.

### Success Criteria (Draft)
- [ ] Terraform provisiona um ambiente Cloud Composer 3 (preset Small), reusando a SA
      `taxreform-ingestion` com `roles/composer.worker` adicionado
- [ ] `composer.googleapis.com` habilitada; SA de Terraform confirmada (não assumida) com
      permissão para criar o ambiente
- [ ] `dags/ingestao_legal_dag.py` copiada para o ambiente e disparada manualmente
- [ ] As 2 tasks (`ingest_planalto`, `ingest_tcu`) concluídas com sucesso, evidenciado por log
      real do Airflow (não só "o ambiente subiu")
- [ ] Confirmado que a reingestão é idempotente (não duplica pontos no Qdrant — mesmo
      `point_id` determinístico já testado em `PIPELINE_INGESTAO_LEGAL`)
- [ ] Evidência da execução real registrada no BUILD_REPORT/SHIPPED (logs, contagem de pontos
      antes/depois) ANTES do `terraform destroy`
- [ ] Ambiente destruído ao final da verificação — `main.tf` não fica com um recurso Composer
      permanente após o `/ship` (ou, se ficar declarado por algum motivo, um passo explícito de
      destroy documentado)

### Constraints Identified
- Custo real ~US$300-400/mês se deixado rodando — só aceitável pela janela curta de verificação
- Ambiente leva ~20-30 min para provisionar e para destruir — sessão de build precisa reservar
  esse tempo
- `dags/ingestao_legal_dag.py` não muda nesta feature

### Out of Scope (Confirmed)
- Orquestração agendada permanente (deixar o Composer rodando após o ship)
- Novas fontes de ingestão
- VPC dedicada
- Monitoramento/alerting do Airflow

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 2 de 2 |
| Duration | Sessão contínua (após o ship de `LLM_REAL_VERTEX_AI`) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_CLOUD_COMPOSER_PROVISIONAMENTO.md`
