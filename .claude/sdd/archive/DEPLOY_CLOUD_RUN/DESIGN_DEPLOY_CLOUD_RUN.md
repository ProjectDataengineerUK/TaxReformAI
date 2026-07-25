# DESIGN: Deploy Contínuo para Cloud Run

> Especificação técnica para publicar `api/` e `frontend/` como serviços Cloud Run via `workflow_dispatch`, integrando e corrigindo o trabalho de CD já construído fora do SDD.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEPLOY_CLOUD_RUN |
| **Date** | 2026-07-24 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_DEPLOY_CLOUD_RUN.md](./DEFINE_DEPLOY_CLOUD_RUN.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  GitHub Actions — .github/workflows/deploy.yml (workflow_dispatch only)   │
│  inputs: target=api|frontend|both   confirm="DEPLOY"                      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ auth: secrets.GCP_DEPLOYER_SA_KEY
                                ▼
        ┌───────────────── STEP 0: resolver URLs existentes ─────────────────┐
        │  gcloud run services describe {api,frontend}  (tolera not-found)   │
        │  → API_URL_ATUAL, FRONTEND_URL_ATUAL (vazios no bootstrap)         │
        └───────────────────────────────┬───────────────────────────────────┘
                                        ▼
   ┌──────── STEP 1: API ────────┐              ┌────── STEP 2: FRONTEND ──────┐
   │ docker build -f api/        │              │ docker build -f frontend/    │
   │   Dockerfile .   (raiz)     │              │   Dockerfile frontend/       │
   │ requirements-api.txt        │              │ --build-arg                  │
   │                             │              │   NEXT_PUBLIC_API_BASE_URL=  │
   │ push → Artifact Registry    │              │   $API_URL  ◄────────────────┼──┐
   │   :$GITHUB_SHA  e  :latest  │              │ push → Artifact Registry     │  │
   │                             │              │                              │  │
   │ gcloud run deploy           │              │ gcloud run deploy            │  │
   │   --set-env-vars            │              │   taxreformai-frontend       │  │
   │     API_KEYS (^@^)          │              │                              │  │
   │     FRONTEND_ORIGINS=       │              │ → FRONTEND_URL               │  │
   │       $FRONTEND_URL_ATUAL   │              └───────────┬──────────────────┘  │
   │ → API_URL ──────────────────┼─────────────────────────────────────────────────┘
   └─────────────────────────────┘                          │
                                        ┌───────────────────▼───────────────────┐
                                        │ STEP 3: reconciliar CORS              │
                                        │ se FRONTEND_URL != FRONTEND_ORIGINS   │
                                        │ atual → gcloud run services update    │
                                        │ (só dispara no bootstrap / mudança)   │
                                        └───────────────────┬───────────────────┘
                                                            ▼
                                        ┌───────────────────────────────────────┐
                                        │ STEP 4: SMOKE TEST (falha o job)      │
                                        │  a) GET  /healthz            → 200    │
                                        │  b) POST /v1/tax/simulate    → 200    │
                                        │       com chave real de API_KEYS      │
                                        │  c) OPTIONS com Origin=frontend       │
                                        │       → access-control-allow-origin   │
                                        │  d) GET  frontend /          → 200    │
                                        └───────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `deploy.yml` | Orquestra build → push → deploy → smoke test | GitHub Actions, `workflow_dispatch` |
| `api/Dockerfile` | Imagem da API; build context = raiz do repo | `python:3.12-slim`, single-stage |
| `frontend/Dockerfile` | Imagem do frontend; build context = `frontend/` | `node:20-slim`, multi-stage (deps→builder→runner) |
| `requirements-api.txt` | **Novo** — dependências de runtime *só* da API | pip |
| Artifact Registry | Registro das imagens, tagueadas por SHA | `southamerica-east1-docker.pkg.dev/$PROJECT/taxreformai` |
| `taxreformai-api` | Serviço Cloud Run da API | Cloud Run, scale-to-zero |
| `taxreformai-frontend` | Serviço Cloud Run do frontend | Cloud Run, scale-to-zero |
| `taxreformai-deployer` | Identidade do CD, IAM escopado | GCP Service Account |

---

## Key Decisions

### Decision 1: Resolver a dependência circular por ordenação + reconciliação, não por adivinhação

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `NEXT_PUBLIC_API_BASE_URL` é inlinada no bundle JS em **build time** (`frontend/lib/api-client.ts:11`), e `FRONTEND_ORIGINS` é lida em **runtime** pela API (`api/main.py:12`). Cada serviço precisa da URL do outro, e nenhuma existe antes do primeiro deploy (DEFINE A-003).

**Choice:** Um único job com 4 passos: (0) tentar ler ambas as URLs com `gcloud run services describe`, tolerando "not found"; (1) deployar a API com o `FRONTEND_ORIGINS` que se conseguiu resolver; (2) buildar o frontend com o `API_URL` — que a esta altura é sempre conhecido; (3) se a URL do frontend mudou (ou acabou de nascer), reconciliar `FRONTEND_ORIGINS` na API com um `gcloud run services update`.

**Rationale:** Em regime estável (2º deploy em diante), ambas as URLs já existem no passo 0, cada serviço é deployado exatamente uma vez e o passo 3 vira no-op. O custo do "2 passos" fica confinado ao bootstrap. Nada é adivinhado: toda URL vem de um `describe` real.

**Alternatives Rejected:**
1. **CORS por wildcard/regex** (`allow_origins=["*"]` ou regex `*.run.app`) — rejeitada por enfraquecer a segurança de uma API que carrega dados fiscais de clientes; `allow_origins=["*"]` combinado com header de autenticação é justamente o antipadrão que o `CORSMiddleware` existe para evitar. O DEFINE já sinalizava essa rejeição.
2. **Prever a URL do Cloud Run** (formato `https://SERVICE-PROJECTNUMBER.REGION.run.app`) — o formato é estável hoje mas não é contrato público; um deploy que silenciosamente aponta para uma URL errada reproduz exatamente a classe de bug de CORS de `FRONTEND_SIMULADOR`.
3. **Dois workflows manuais separados**, com o operador copiando URLs entre eles — transforma um passo automatizável em ritual manual propenso a erro.

**Consequences:**
- No bootstrap, o serviço da API ganha 2 revisões (a segunda só troca `FRONTEND_ORIGINS`). Aceitável e não recorrente.
- O passo 3 exige comparar o valor atual antes de atualizar, senão todo deploy cria uma revisão supérflua.
- **Resolve o receio do `@lru_cache` levantado no DEFINE:** no Cloud Run, qualquer mudança de env var cria uma revisão nova, ou seja, um container novo — o cache de `get_settings()` nasce limpo. Não é um problema real neste ambiente.

---

### Decision 2: A imagem da API instala apenas as dependências de runtime da API

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** O `api/Dockerfile` do worktree faz `pip install -r requirements.txt`, que traz `fastembed`, `qdrant-client`, `google-cloud-storage`, `lxml`, `beautifulsoup4`, `httpx`, `typer` e `pytest`. Rastreando os imports reais em runtime (`api/`, `orquestracao/`, `motor_calculo/`), o único acoplamento com `ingestion/` é `ingestion.chunking.chunk_models.Chunk` — um modelo Pydantic puro, num pacote cujos `__init__.py` estão todos vazios (0 bytes).

**Choice:** Criar `requirements-api.txt` com exatamente `fastapi`, `uvicorn` e `pydantic`. `requirements.txt` passa a começar com `-r requirements-api.txt` e mantém só o resto. O `api/Dockerfile` instala `requirements-api.txt`.

**Rationale:** `fastembed` arrasta `onnxruntime` (centenas de MB); `lxml` compila. Instalar isso numa imagem que nunca os importa infla a imagem, alonga o build — ameaçando o critério de <15 min — e amplia a superfície de ataque com bibliotecas que o serviço não usa. Incluir via `-r` mantém **uma única fonte de verdade**: é estruturalmente impossível a lista da API divergir do que o CI instala, então nenhum teste de anti-drift é necessário.

**Alternatives Rejected:**
1. **Manter `requirements.txt` inteiro** — mais simples, mas paga o custo em cada build e contradiz o critério de tempo.
2. **Duas listas independentes e um teste de drift** — o teste seria uma solução para um problema que o `-r` simplesmente não permite existir.
3. **Cortar o import de `ingestion` na orquestração** (duplicando `Chunk`) — trocaria uma dependência de 3 linhas de Pydantic por duplicação de modelo de dados. Não compensa.

**Consequences:**
- Um import novo em `api/`/`orquestracao/` que exija biblioteca nova precisa entrar em `requirements-api.txt`, não só em `requirements.txt`. Se esquecido, o container quebra no runtime — e o smoke test (Decisão 6) é justamente o que pega isso antes de o deploy ser considerado bom.
- `pytest` some da imagem de produção, como deve ser.

---

### Decision 3: `API_KEYS` como env var do Cloud Run, com delimitador alternativo do gcloud

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `api/config.py:14` espera `API_KEYS` como um JSON `{"chave": "tenant_id"}`. `gcloud run deploy --set-env-vars` usa vírgula como separador entre variáveis, e um JSON com mais de uma chave **contém vírgulas** — o valor seria truncado silenciosamente.

**Choice:** Passar via GitHub Secret `API_KEYS` usando a sintaxe de delimitador customizado do gcloud: `--set-env-vars ^@^API_KEYS={...}@FRONTEND_ORIGINS=...`.

**Rationale:** Consistente com a política já vigente no projeto ("credenciais reais vivem em GitHub Secrets"), sem introduzir infraestrutura nova. O delimitador `^@^` é a solução oficial do gcloud para valores que contêm vírgula.

**Alternatives Rejected:**
1. **Secret Manager + `--set-secrets`** — tecnicamente a resposta correta (env vars do Cloud Run são legíveis por qualquer principal com `run.viewer`), mas exige recurso Terraform novo + binding IAM + habilitar a API. **Registrado como follow-up recomendado**, não como escopo desta feature.
2. **Base64 do JSON** — evita a vírgula mas exige mudar `api/config.py`, ou seja, alterar código de aplicação numa feature que se propôs a ser 100% de infraestrutura.

**Consequences:**
- Quem tiver `roles/run.viewer` no projeto consegue ler as chaves de API. Num projeto de dev de um único operador, risco aceito e **documentado explicitamente**.
- A migração para Secret Manager depois é local: muda o flag do gcloud, não o código.

---

### Decision 4: Identidade de deploy dedicada, com chave gerada fora do Terraform

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `terraform.yml` autentica com `secrets.GCP_SA_KEY`, uma SA privilegiada o bastante para criar buckets, SAs e bindings IAM. O Terraform já escrito cria `taxreformai-deployer` com IAM deliberadamente escopado (AR writer *só no repositório* de imagens, `run.admin`, `serviceAccountUser` *só em si mesma*).

**Choice:** `deploy.yml` autentica com um secret novo, `GCP_DEPLOYER_SA_KEY`, gerado manualmente pelo operador após o `terraform apply`. O recurso `google_service_account_key` **não** entra no Terraform.

**Rationale:** Respeita a intenção de menor privilégio já embutida no Terraform — um workflow de deploy não deve carregar credencial capaz de destruir o bucket de ingestão. Manter a chave fora do Terraform evita que a chave privada seja gravada no `tfstate` (que agora vive num bucket GCS).

**Alternatives Rejected:**
1. **Reusar `GCP_SA_KEY`** — zero passos manuais, mas descarta a modelagem de menor privilégio que já está escrita e paga.
2. **`google_service_account_key` no Terraform** — automatiza, mas grava chave privada em texto no state.
3. **Workload Identity Federation** — a resposta certa a longo prazo (elimina chaves de vida longa), mas exige pool + provider + bindings; desproporcional para fechar esta feature. **Follow-up recomendado.**

**Consequences:**
- **Passo manual obrigatório do operador**, uma única vez (comando exato no Runbook abaixo).
- Chave de vida longa em GitHub Secrets — mesma postura já adotada para `GCP_SA_KEY`, sem regressão de segurança.

---

### Decision 5: `workflow_dispatch` com guarda de confirmação, espelhando `terraform.yml`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** Deploy cria recursos cobráveis. O projeto já tem um precedente explícito: `terraform.yml` exige digitar `APPLY` num campo separado.

**Choice:** `workflow_dispatch` com dois inputs: `target` (`api` | `frontend` | `both`, default `both`) e `confirm` (precisa ser exatamente `DEPLOY`). Nenhum gatilho por push.

**Rationale:** Consistência com o padrão de guarda que o projeto já escolheu — um operador aprende uma convenção, não duas. `target` atende ao goal COULD de deploy seletivo com custo quase zero.

**Alternatives Rejected:**
1. **Deploy automático no push para `main`** — explicitamente fora de escopo no DEFINE.
2. **GitHub Environments com required reviewers** — mais robusto, mas aprovação por outra pessoa não faz sentido num projeto de um operador só.

**Consequences:**
- Deploy é sempre um ato deliberado.
- `target=frontend` isolado depende de a API já existir; o passo 0 resolve a URL, e se não existir, o job falha com mensagem clara em vez de buildar um frontend apontando para `localhost`.

---

### Decision 6: Smoke test que reprova o job, cobrindo os dois defaults perigosos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `api/main.py:12` cai para `localhost:3000` se `FRONTEND_ORIGINS` faltar, e `api/config.py:14` cai para `{}` se `API_KEYS` faltar. Nos dois casos o serviço sobe, `/healthz` responde 200 e **tudo que importa está quebrado** (AT-004).

**Choice:** Quatro asserções obrigatórias após o deploy, cada uma capaz de reprovar o job: (a) `GET /healthz` = 200; (b) `POST /v1/tax/simulate` com uma chave real extraída de `API_KEYS` e `ano_operacao: 2026` = 200; (c) requisição com `Origin: $FRONTEND_URL` devolve `access-control-allow-origin` igual a essa origem; (d) `GET /` do frontend = 200.

**Rationale:** `/healthz` sozinho é um teste inútil aqui — ele passa exatamente nos dois cenários de falha que mais preocupam. (b) prova que `API_KEYS` chegou; (c) prova que `FRONTEND_ORIGINS` chegou e é a URL certa. `ano_operacao: 2026` é obrigatório porque é a única fase com alíquota confirmada — 2027+ retorna 422 por decisão de design do motor.

**Alternatives Rejected:**
1. **Só `/healthz`** — passa nos dois modos de falha. Pior que nada, porque dá falsa confiança.
2. **Rodar a suíte pytest contra o serviço deployado** — os 72 testes usam fakes e foram escritos para rodar in-process; não são um teste de fumaça de rede.

**Consequences:**
- O smoke test precisa de uma chave de API válida dentro do runner — já disponível, já que o workflow injeta `API_KEYS`.
- Uma falha de smoke test deixa a revisão nova **já recebendo tráfego** (o `gcloud run deploy` já promoveu). Rollback é manual via tag de SHA — coerente com "rollback automatizado" estar fora de escopo.

---

### Decision 7: Tag dupla — `$GITHUB_SHA` e `latest`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** Goal SHOULD do DEFINE: identificar e reverter para uma revisão anterior.

**Choice:** Toda imagem sobe com duas tags; o `gcloud run deploy` referencia **sempre a tag de SHA**, nunca `latest`.

**Rationale:** Deployar por SHA torna a revisão do Cloud Run rastreável até um commit exato. `latest` fica só como conveniência para inspeção manual.

**Consequences:** Rollback vira um `gcloud run deploy --image ...:<sha-antigo>` — manual, mas trivial e sempre disponível.

---

## File Manifest

> **Itens 1, 2, 12 e 13 já foram executados** antes do `/build`, a pedido do usuário (ver Revision History 1.1).

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `requirements-api.txt` | ✅ Create | Deps de runtime só da API (`fastapi`, `uvicorn`, `pydantic`) | @python-developer | None |
| 2 | `requirements.txt` | ✅ Modify | Passa a começar com `-r requirements-api.txt`; remove as 3 linhas movidas | @python-developer | 1 |
| 3 | `api/Dockerfile` | Create (do worktree, ajustado) | Imagem da API; troca `requirements.txt` → `requirements-api.txt` | @python-developer | 1 |
| 4 | `.dockerignore` | Create (do worktree) | Enxuga o contexto de build da raiz | @python-developer | None |
| 5 | `frontend/Dockerfile` | Create (do worktree, sem alteração) | Imagem multi-stage do Next.js standalone | @typescript-reviewer | 6 |
| 6 | `frontend/next.config.mjs` | Modify (do worktree) | `output: "standalone"` | @typescript-reviewer | None |
| 7 | `frontend/.dockerignore` | Create (do worktree) | Exclui `node_modules`/`.next` do contexto | @typescript-reviewer | None |
| 8 | `infra/terraform/main.tf` | Modify (já escrito, commitar) | Backend GCS + Artifact Registry + SA de deploy + IAM | @gcp-data-architect | None |
| 9 | `.github/workflows/deploy.yml` | Create | O CD em si | @ci-cd-specialist | 3, 5, 8 |
| 10 | `CLAUDE.md` | Modify | Documenta o CD, as URLs, os secrets novos e o runbook | (general) | 9 |
| 11 | `.env.example` | Modify | Registra `API_KEYS` e `FRONTEND_ORIGINS` como config de deploy | (general) | None |
| 12 | `api/routers/simulate.py` | ✅ Modify | Valida `payload.tenant_id` contra a credencial → 403 (ver Security Considerations) | @security-reviewer | None |
| 13 | `tests/test_api_simulate.py` | ✅ Modify | Fixture mapeia a chave para o tenant do blueprint; novo teste de divergência → 403 | @security-reviewer | 12 |

**Total Files:** 13 (4 novos de código, 1 workflow novo, 4 movidos do worktree, 2 de documentação, 2 de correção de multi-tenancy)

**Pré-requisito não-arquivo:** merge do worktree `agent-a99633d8eef6cb127` e remoção dele (`git worktree remove`), mais o `terraform apply` e a geração da chave da SA (Runbook).

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @ci-cd-specialist | 9 | Workflow multi-step com auth GCP, guardas e smoke test é exatamente o domínio dele |
| @gcp-data-architect | 8 | Artifact Registry, Cloud Run e IAM escopado no GCP |
| @python-developer | 1, 2, 3, 4 | Separação de dependências e imagem Python |
| @typescript-reviewer | 5, 6, 7 | Build standalone do Next.js e contexto Docker do frontend |
| @security-reviewer | revisão de 8, 9 | Manuseio de `API_KEYS`, chave de SA e escopo IAM — CLAUDE.md marca este agente como "já relevante" |
| (general) | 10, 11 | Documentação |

---

## Code Patterns

### Pattern 1: Resolver URL de serviço tolerando inexistência (passo 0)

```bash
resolver_url() {  # $1 = nome do serviço
  gcloud run services describe "$1" \
    --region="$REGION" --format='value(status.url)' 2>/dev/null || true
}
API_URL=$(resolver_url taxreformai-api)
FRONTEND_URL=$(resolver_url taxreformai-frontend)
```

### Pattern 2: Deploy da API com env vars que contêm vírgula (Decisão 3)

```bash
# ^@^ troca o separador de "," para "@", permitindo JSON no valor.
ORIGINS="${FRONTEND_URL:-http://localhost:3000}"
gcloud run deploy taxreformai-api \
  --image="${IMAGE_REPO}/api:${GITHUB_SHA}" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars="^@^API_KEYS=${API_KEYS}@FRONTEND_ORIGINS=${ORIGINS}"

API_URL=$(gcloud run services describe taxreformai-api \
  --region="$REGION" --format='value(status.url)')
```

### Pattern 3: Reconciliar CORS sem gerar revisão supérflua (passo 3)

```bash
ATUAL=$(gcloud run services describe taxreformai-api --region="$REGION" --format=json \
  | jq -r '.spec.template.spec.containers[0].env[]? | select(.name=="FRONTEND_ORIGINS") | .value')

if [ "$ATUAL" != "$FRONTEND_URL" ]; then
  echo "CORS desatualizado ('$ATUAL' != '$FRONTEND_URL') — reconciliando."
  gcloud run services update taxreformai-api --region="$REGION" \
    --update-env-vars="FRONTEND_ORIGINS=${FRONTEND_URL}"
else
  echo "CORS já correto — nenhuma revisão nova."
fi
```

### Pattern 4: Smoke test que reprova o job (Decisão 6)

```bash
set -euo pipefail

# (a) health
curl -fsS --max-time 20 "${API_URL}/healthz" > /dev/null
echo "OK healthz"

# (b) chave real precisa funcionar — pega detectar API_KEYS ausente/truncada
CHAVE=$(echo "$API_KEYS" | jq -r 'keys[0]')
HTTP=$(curl -sS -o /tmp/sim.json -w '%{http_code}' --max-time 30 \
  -X POST "${API_URL}/v1/tax/simulate" \
  -H "X-API-Key: ${CHAVE}" -H 'Content-Type: application/json' \
  -d '{"tenant_id":"smoke","ano_operacao":2026,"operacao_tipo":"VENDA",
       "itens":[{"sku":"SMOKE-1","ncm":"22030000","quantidade":1,
                 "valor_unitario":"100.00","uf_origem":"SP","uf_destino":"RJ"}]}')
[ "$HTTP" = "200" ] || { echo "FALHA: simulate devolveu $HTTP"; cat /tmp/sim.json; exit 1; }
echo "OK simulate"

# (c) CORS precisa refletir a URL real do frontend, não o default localhost
ACAO=$(curl -sS -D - -o /dev/null --max-time 20 \
  -X OPTIONS "${API_URL}/v1/tax/simulate" \
  -H "Origin: ${FRONTEND_URL}" \
  -H 'Access-Control-Request-Method: POST' \
  | grep -i '^access-control-allow-origin:' | tr -d '\r' | awk '{print $2}')
[ "$ACAO" = "$FRONTEND_URL" ] || { echo "FALHA CORS: '$ACAO' != '$FRONTEND_URL'"; exit 1; }
echo "OK cors"

# (d) frontend responde
curl -fsS --max-time 30 "${FRONTEND_URL}/" > /dev/null
echo "OK frontend"
```

### Pattern 5: `requirements.txt` com fonte única de verdade (Decisão 2)

```text
# requirements-api.txt — runtime da API (usado por api/Dockerfile)
fastapi>=0.115
uvicorn>=0.30
pydantic>=2.7
```

```text
# requirements.txt — set completo de dev/CI; inclui o da API por referência
-r requirements-api.txt

httpx>=0.27
beautifulsoup4>=4.12
lxml>=5.0
qdrant-client>=1.10
google-cloud-storage>=2.16
fastembed>=0.3
typer>=0.12
pytest>=8.0
```

---

## Runbook (passos de operador, fora do código)

| # | Passo | Comando | Quando |
|---|-------|---------|--------|
| 1 | Confirmar estado do Terraform (valida DEFINE A-002) | Rodar `terraform.yml` com `action=plan` | Antes de tudo — barato, não cria nada |
| 2 | Aplicar os recursos de CD | Rodar `terraform.yml` com `action=apply` + `APPLY` | Após o merge do #8 |
| 3 | Gerar a chave da SA de deploy | `gcloud iam service-accounts keys create key.json --iam-account=taxreformai-deployer@<PROJECT>.iam.gserviceaccount.com` | Após o passo 2 |
| 4 | Cadastrar secrets no GitHub | `GCP_DEPLOYER_SA_KEY` (conteúdo de `key.json`), `API_KEYS` (JSON `{"chave":"tenant"}`) | Após o passo 3 |
| 5 | Apagar a chave local | `rm key.json` | Imediatamente após o passo 4 |
| 6 | Primeiro deploy (bootstrap) | Rodar `deploy.yml` com `target=both`, `confirm=DEPLOY` | Fim |

> Os passos 3 e 5 rodam na máquina do operador porque são operações de **credencial**, não de infraestrutura — nenhum recurso GCP é criado ou alterado localmente, o que mantém a política de "infra real nunca roda local" intacta. Sugestão: executar com o prefixo `!` na sessão para que a saída caia direto na conversa.

---

## Data Flow

```text
1. Operador dispara deploy.yml (target, confirm=DEPLOY)
   │
   ▼
2. Guarda de confirmação valida o input  ──falha──→ job aborta, nada é publicado
   │
   ▼
3. Auth no GCP com GCP_DEPLOYER_SA_KEY → resolve URLs existentes
   │
   ▼
4. Build + push da imagem da API (:$SHA, :latest) → Artifact Registry
   │
   ▼
5. gcloud run deploy taxreformai-api  → API_URL
   │
   ▼
6. Build do frontend com --build-arg NEXT_PUBLIC_API_BASE_URL=$API_URL → push → deploy → FRONTEND_URL
   │
   ▼
7. Reconcilia FRONTEND_ORIGINS na API se necessário
   │
   ▼
8. Smoke test (a,b,c,d)  ──falha──→ job vermelho; revisão nova continua servindo tráfego (rollback manual por SHA)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Artifact Registry | `docker push` via `gcloud auth configure-docker` | Chave da SA `taxreformai-deployer` |
| Cloud Run Admin API | `gcloud run deploy` / `describe` / `update` | Mesma SA (`roles/run.admin`) |
| GCS (backend do Terraform) | `terraform init` | `GCP_SA_KEY` (workflow existente, inalterado) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Regressão | Os 72 testes existentes continuam passando | `tests/` | pytest | 100% (nenhum código de aplicação muda) |
| Build local de imagem | AT-006: a imagem da API importa os pacotes irmãos | `api/Dockerfile` | `docker build` + `docker run ... python -c "import api.main"` | Ambas as imagens buildam |
| Smoke E2E | AT-001..AT-004: serviços reais no ar | `deploy.yml` | curl + jq | 4 asserções obrigatórias |
| Guarda | AT-005: sem confirmação, nada acontece | `deploy.yml` | Execução manual do workflow | 1 caso |
| Infra | AT-007: `init` + `plan` sem drift | `infra/terraform/` | `terraform.yml` (`action=plan`) | Plan limpo |

> **Nota:** AT-006 é verificável localmente porque `docker build` não toca em infraestrutura GCP — não conflita com a política do projeto. Se o Docker não estiver disponível no sandbox, o build no runner do `deploy.yml` é a verificação real e isso deve ser registrado no BUILD_REPORT em vez de fingido.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `confirm` != `DEPLOY` | Falha explícita antes de qualquer efeito colateral | Não |
| `target=frontend` mas API não existe | Falha com mensagem clara ("deploy a API primeiro") em vez de buildar contra `localhost` | Não |
| Build da imagem falha | Job falha; nenhum `gcloud run deploy` é executado | Não |
| Push para Artifact Registry falha | Job falha; provável IAM/repo ausente → aponta para o Runbook passo 2 | Não |
| Smoke test (b) falha com 401 | `API_KEYS` ausente ou truncada — job vermelho com o corpo da resposta no log | Não |
| Smoke test (c) diverge | `FRONTEND_ORIGINS` errada — job vermelho mostrando esperado vs. obtido | Não |
| `gcloud run deploy` falha por quota/billing | Job falha com o erro do gcloud (valida DEFINE A-005) | Não |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `REGION` | string | `southamerica-east1` | Região, conforme blueprint §5.1 |
| `SERVICE_API` | string | `taxreformai-api` | Nome do serviço Cloud Run da API |
| `SERVICE_FRONTEND` | string | `taxreformai-frontend` | Nome do serviço Cloud Run do frontend |
| `IMAGE_REPO` | string | `${REGION}-docker.pkg.dev/${PROJECT}/taxreformai` | Repositório de imagens |
| `target` (input) | choice | `both` | `api` \| `frontend` \| `both` |
| `confirm` (input) | string | `""` | Precisa ser exatamente `DEPLOY` |

**Secrets do GitHub necessários:**

| Secret | Status | Uso |
|--------|--------|-----|
| `GCP_PROJECT_ID` | Já existe | Nome do projeto e caminho das imagens |
| `GCP_SA_KEY` | Já existe | Só `terraform.yml` (inalterado) |
| `GCP_DEPLOYER_SA_KEY` | **Novo** | Auth do `deploy.yml` |
| `API_KEYS` | **Novo** | Env var de runtime da API |

---

## Security Considerations

- **`--allow-unauthenticated` nos dois serviços** é intencional: a API tem sua própria auth via `X-API-Key`, e o frontend é público por natureza. A consequência é que a superfície de auth da API passa a ser exposta à internet — o que torna a revisão do @security-reviewer um passo recomendado antes do primeiro deploy real.
- **`API_KEYS` como env var** é legível por qualquer principal com `roles/run.viewer` (Decisão 3). Risco aceito e registrado; Secret Manager é o follow-up.
- **Menor privilégio preservado:** a SA de deploy escreve só no repositório de imagens `taxreformai`, não no bucket de ingestão (Decisão 4).
- **Chave de vida longa** em GitHub Secrets; WIF é o follow-up que a elimina.
- **Nenhum segredo em imagem:** `.dockerignore` exclui `.env`; `API_KEYS` só existe como env var de runtime, nunca em camada de imagem.
- **`NEXT_PUBLIC_API_BASE_URL` é pública por definição** — vai inlinada no bundle JS. É só uma URL, não um segredo; registrado para evitar que alguém coloque algo sensível num `NEXT_PUBLIC_*` no futuro.
- **Isolamento multi-tenant — corrigido nesta feature.** `api/routers/simulate.py` recebia `tenant_id` do payload **e** da autenticação sem conferir se batem, permitindo que um cliente autenticado simulasse declarando o tenant de outro. Originalmente eu havia classificado isso como fora de escopo (sem persistência, nada vaza hoje); o usuário determinou corrigir antes do build. A rota agora retorna **403** quando divergem, com mensagem que não ecoa o tenant autenticado — para não revelar o dono da chave a quem apenas a possui. Coberto por `test_tenant_id_do_payload_diferente_da_credencial_retorna_403`. `POST /v1/tax/query` não é afetado: `PayloadConsulta` não carrega `tenant_id`.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Cloud Run Logs (stdout do uvicorn e do Next.js), sem configuração adicional |
| Metrics | Métricas nativas do Cloud Run (latência, contagem, instâncias) |
| Tracing | Nenhum — fora de escopo |
| Deploy audit | Cada revisão do Cloud Run carrega a tag de SHA, rastreável até o commit |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | design-agent | Versão inicial — integra o trabalho pré-existente do worktree e corrige o conjunto de dependências da imagem da API |
| 1.1 | 2026-07-24 | design-agent | A pedido do usuário, executados antes do `/build`: split de `requirements-api.txt` (itens 1-2) e correção do isolamento multi-tenant em `simulate.py` (itens 12-13, antes classificada fora de escopo). Restrição do `@lru_cache` marcada como descartada no DEFINE. 73 testes passando, ruff limpo |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_DEPLOY_CLOUD_RUN.md`
