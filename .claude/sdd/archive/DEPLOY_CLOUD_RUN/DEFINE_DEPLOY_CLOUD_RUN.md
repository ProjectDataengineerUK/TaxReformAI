# DEFINE: Deploy Contínuo para Cloud Run

> Publicar a API FastAPI e o frontend Next.js como serviços Cloud Run reais, via workflow manual no GitHub Actions, fechando o trabalho de CD já parcialmente construído fora do SDD.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEPLOY_CLOUD_RUN |
| **Date** | 2026-07-24 |
| **Author** | Jonatas Lima da Costa |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O projeto tem cinco componentes shipados e CI verde, mas **nada roda fora da máquina de desenvolvimento ou do runner de CI** — não existe nenhuma URL onde a API ou o frontend possam ser acessados. Pior: existe trabalho de CD **meio construído e não commitado** (Dockerfiles presos num worktree, Terraform de Artifact Registry escrito mas não aplicado, `deploy.yml` citado num comentário de código mas inexistente), e o state do Terraform já foi migrado para um backend GCS **sem que essa mudança esteja registrada no repositório**. Isso é dívida ativa: se o working tree se perder, o repo não descreve mais onde o state vive.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Jonatas (dev/owner) | Único desenvolvedor e operador | Não consegue demonstrar o produto para ninguém, nem validar o frontend contra a API num ambiente real; tem mudanças críticas de infra fora do controle de versão |
| Persona "Head de Tax" (blueprint §1.2) | Usuário-alvo do produto | Não pode sequer ver o simulador — não há URL pública para avaliar a ferramenta |
| Futuro integrador ERP (blueprint §8) | Consumidor da API | `POST /v1/tax/simulate` não tem endpoint acessível para integrar; o contrato existe só em `localhost` |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Trazer para o controle de versão todo o trabalho de CD já feito (Dockerfiles, `output: standalone`, `.dockerignore`, backend GCS + Artifact Registry + SA de deploy no Terraform) |
| **MUST** | API FastAPI rodando como serviço Cloud Run real, respondendo em `/healthz` e `/v1/tax/simulate` |
| **MUST** | Frontend Next.js rodando como serviço Cloud Run real, conseguindo chamar a API deployada sem erro de CORS |
| **MUST** | `.github/workflows/deploy.yml` disparado por `workflow_dispatch` (nunca automático no push), seguindo o precedente de guarda explícita já estabelecido por `terraform.yml` |
| **MUST** | Nenhuma credencial em texto no repositório — `API_KEYS` e chave da SA vêm de GitHub Secrets |
| **SHOULD** | Imagens tagueadas pelo SHA do commit (não só `latest`), permitindo identificar e reverter para uma revisão anterior |
| **SHOULD** | Smoke test automático pós-deploy no próprio workflow — falhar o job se o serviço subir quebrado |
| **COULD** | Deploy seletivo (só API, só frontend, ou ambos) como input do workflow |

---

## Success Criteria

- [ ] `git status` limpo: zero arquivos de CD não commitados, worktree `agent-a99633d8eef6cb127` mergeado e removido
- [ ] 2 serviços Cloud Run ativos em `southamerica-east1` (`taxreformai-api`, `taxreformai-frontend`)
- [ ] `GET /healthz` do serviço da API retorna HTTP 200 em menos de 5s a partir de uma chamada externa
- [ ] `POST /v1/tax/simulate` com `X-API-Key` válido retorna HTTP 200 contra o serviço real; com chave inválida ou ausente retorna 401
- [ ] Uma requisição com header `Origin: <URL do frontend>` recebe `access-control-allow-origin` correspondente (o bug de CORS de `FRONTEND_SIMULADOR` não pode se repetir em produção)
- [ ] Workflow completo (build + push + deploy dos 2 serviços) termina em menos de 15 minutos
- [ ] 0 ocorrências de chave/segredo em `git grep` no repositório após o merge

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — deploy da API | Terraform de CD aplicado, secrets configurados | `deploy.yml` roda com `target=api` e confirmação válida | Imagem sobe no Artifact Registry taggeada com o SHA, serviço `taxreformai-api` atualiza e `/healthz` responde 200 |
| AT-002 | Happy path — deploy do frontend | API já deployada com URL conhecida | `deploy.yml` roda com `target=frontend` | Imagem é buildada com `NEXT_PUBLIC_API_BASE_URL` = URL real da API e o serviço responde 200 na raiz |
| AT-003 | CORS entre os dois serviços | Ambos os serviços deployados | Requisição para a API com `Origin: <URL do frontend>` | Resposta traz `access-control-allow-origin` com a URL do frontend, não o default `localhost:3000` |
| AT-004 | API sem `API_KEYS` configurada | Deploy feito sem o secret `API_KEYS` | `POST /v1/tax/simulate` com qualquer chave | Retorna 401 para tudo — o smoke test do workflow detecta isso e **falha o job**, em vez de deixar passar um serviço inutilizável |
| AT-005 | Guarda de confirmação | Workflow disparado com `action=deploy` sem digitar a confirmação exigida | Job roda | Nenhuma imagem é publicada e nenhum serviço é alterado; job falha explicitamente (mesmo padrão de `terraform.yml`) |
| AT-006 | Build da API é auto-contido | Repositório limpo | `docker build -f api/Dockerfile .` na raiz | Build conclui e o container importa `motor_calculo`, `orquestracao` e `ingestion` sem `ModuleNotFoundError` |
| AT-007 | Terraform reproduzível | Backend GCS commitado | `terraform init` + `plan` rodam no workflow `terraform.yml` | Init conecta no bucket de state remoto e o plan não mostra drift dos recursos já aplicados |

---

## Out of Scope

- **Cloud Composer** — provisionar o Airflow real continua pendente (bloqueia a verificação E2E da busca híbrida desde `PIPELINE_INGESTAO_LEGAL`); é uma decisão de custo separada e independente deste CD
- **Cloud SQL / PostgreSQL (blueprint §7)** — multi-tenancy real e audit log são a próxima feature, não esta
- **Celery + Redis/Memorystore (blueprint §5.2)** — nenhum processamento assíncrono nesta feature
- **Deploy automático no push para `main`** — deliberadamente `workflow_dispatch` apenas; deploy que cria recursos cobráveis exige ação humana explícita neste projeto
- **Domínio customizado, HTTPS próprio, CDN** — as URLs `*.run.app` geradas pelo Cloud Run bastam
- **Tuning de autoscaling, min instances, budget alerts** — defaults do Cloud Run (scale-to-zero) são adequados para dev
- **Conectar LLMs reais (Vertex AI)** — os 4 nós fake da orquestração continuam fake; o serviço deployado vai expor exatamente o comportamento atual
- **Rollback automatizado** — tagueamento por SHA torna o rollback *possível* manualmente; automatizá-lo fica para depois

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Política | **Infraestrutura real nunca roda local** (`CLAUDE.md`) | Todo build/push/deploy acontece dentro do GitHub Actions; nenhum `gcloud run deploy` ou `docker push` da máquina de dev |
| Técnico | `NEXT_PUBLIC_API_BASE_URL` é lida em **build time** e embutida no bundle JS; `FRONTEND_ORIGINS` é lida em **runtime** pela API | Dependência circular entre os dois serviços — resolver isso é a principal decisão do DESIGN (ver A-003) |
| Técnico | `api/main.py` tem default `FRONTEND_ORIGINS=localhost:3000` | Um deploy que esqueça essa variável gera um frontend visualmente funcional e completamente quebrado nas chamadas — exatamente a classe de bug já encontrada em `FRONTEND_SIMULADOR` |
| Técnico | `ApiSettings.from_env()` default `API_KEYS="{}"` (`api/config.py:14`) | Sem o secret, a API sobe "saudável" e 401a **tudo** — o smoke test precisa detectar isso (AT-004) |
| ~~Técnico~~ | ~~O `@lru_cache` em `get_settings()` impediria corrigir `API_KEYS` sem nova revisão~~ | **Descartada no DESIGN (Decisão 1):** no Cloud Run, toda mudança de env var cria uma revisão nova — container novo, cache limpo. Não é um problema neste ambiente |
| Técnico | `api/main.py` importa `motor_calculo`/`orquestracao`/`ingestion` com import absoluto | Build context da imagem da API precisa ser a raiz do repo, não `api/` |
| Técnico | Terraform state já migrado para `gs://taxreformai-dev-tfstate` | A mudança precisa ser commitada antes de qualquer novo `terraform apply`, senão o CI reinicializa contra state local vazio e tenta recriar o bucket existente |
| Escopo | Feature já ~70% construída fora do SDD | Ciclo curto (`/define` → `/design` → `/build`); o DESIGN deve **validar e integrar** o que existe, não redesenhar do zero |
| Recurso | Projeto GCP único (`taxreformai-dev`), sem separação dev/prod | Deploy vai para o mesmo projeto onde o bucket de ingestão já vive |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `.github/workflows/deploy.yml` (novo), `api/Dockerfile` + `frontend/Dockerfile` + `.dockerignore` (existem no worktree), `infra/terraform/main.tf` (modificado, não commitado), `frontend/next.config.mjs` (modificado no worktree) | Nenhum código de aplicação muda; a feature é 100% infra/entrega |
| **KB Domains** | `gcp/` (Cloud Run, Artifact Registry), `ci-cd/` | Consultar padrões de deploy serverless e least-privilege IAM |
| **IaC Impact** | **New resources** — `google_artifact_registry_repository.docker_images`, `google_service_account.deployer_sa`, 3 bindings IAM, 2 `google_project_service`; + `backend "gcs"` | Já **escritos** em `infra/terraform/main.tf`, mas **não commitados e presumidamente não aplicados** (A-002) |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O bucket `taxreformai-dev-tfstate` existe e a SA atual tem acesso | `terraform init` falha no CI; seria preciso criar o bucket antes (chicken-and-egg do backend) | [x] Evidência forte: `infra/terraform/.terraform/terraform.tfstate` registra backend `gcs` inicializado com sucesso e `terraform.tfstate` local está zerado (comportamento pós-migração) |
| A-002 | Os recursos de CD (Artifact Registry, SA de deploy, IAM) **ainda não foram aplicados** | Se já existirem, o `plan` acusa "no changes" e pulamos direto para os secrets — cenário mais fácil, não mais difícil | [ ] Só verificável rodando `terraform.yml` com `action=plan`; não checável localmente por política |
| A-003 | A URL do serviço Cloud Run não é conhecida antes do primeiro deploy | Confirmado pela mecânica do Cloud Run (URL inclui hash do projeto). Obriga o deploy a ser em 2 passos ou a fazer um segundo `gcloud run services update` para fechar o CORS | [x] Assumido como verdadeiro; o DESIGN precisa resolver explicitamente |
| A-004 | `requirements.txt` é suficiente para a API rodar em container | Se faltar dependência (já aconteceu: `fastapi`/`uvicorn` faltavam e o CI mascarou por estarem instalados globalmente), o container quebra só em runtime, não no build | [ ] O smoke test de AT-001 é justamente o que valida isso |
| A-005 | A conta GCP tem quota e billing ativos para Cloud Run em `southamerica-east1` | Deploy falha com erro de quota; exigiria mudar de região | [ ] Bucket GCS já foi criado no projeto, então billing está ativo |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Dor concreta e verificável: dívida não commitada + zero URLs acessíveis |
| Users | 3 | Owner é o usuário imediato; personas do blueprint são as beneficiárias diretas de existir uma URL |
| Goals | 3 | MUSTs não-negociáveis e priorizados; o "trazer para o controle de versão" é o mais crítico |
| Success | 3 | Todos mensuráveis (2 serviços, 200 OK, <15min, <5s, 0 segredos) |
| Scope | 2 | Fronteiras explícitas e generosas, mas o ponto exato onde o smoke test para (AT-004) pode precisar de ajuste no DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma bloqueante para o DESIGN. Uma decisão foi deliberadamente empurrada para lá:

- **Como quebrar a dependência circular API ↔ frontend** (constraint técnica + A-003). As opções aparentes são (a) deploy em 2 fases com um `gcloud run services update` final para injetar `FRONTEND_ORIGINS`, (b) deployar a API primeiro, ler a URL via `gcloud run services describe`, e usá-la como `--build-arg` do frontend, ou (c) permitir origem por wildcard/regex no CORS. A opção (c) enfraquece a segurança e provavelmente deve ser rejeitada — a decisão é do DESIGN.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | define-agent | Versão inicial — ciclo curto sobre feature já ~70% construída fora do SDD |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_DEPLOY_CLOUD_RUN.md`
