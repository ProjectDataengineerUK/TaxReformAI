# DESIGN: Provisionamento Real do Cloud Composer

> Technical design for implementing CLOUD_COMPOSER_PROVISIONAMENTO (posição 7 do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLOUD_COMPOSER_PROVISIONAMENTO |
| **Date** | 2026-08-03 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_CLOUD_COMPOSER_PROVISIONAMENTO.md](./DEFINE_CLOUD_COMPOSER_PROVISIONAMENTO.md) |
| **Status** | ✅ Shipped (2026-08-04) — ver SHIPPED_2026-08-04.md |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  FASE 1 — Provisionar (terraform.yml, workflow_dispatch, action=apply)   │
│                                                                            │
│  infra/terraform/main.tf ganha (TEMPORARIAMENTE):                        │
│    google_project_service.composer                                       │
│    google_composer_environment.ingestao_legal (preset SMALL)             │
│    google_project_iam_member.ingestion_composer_worker                   │
│         (taxreform-ingestion ganha roles/composer.worker)                │
│                                                                            │
│  `terraform apply` → ambiente Composer 3 real sobe (~20-30 min)          │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FASE 2 — Verificar (verificar_composer_producao.yml, workflow_dispatch) │
│                                                                            │
│  [1] scripts/verificar_composer_producao.py --antes                     │
│        conta pontos no Qdrant (LCP_214_2025 + TCU_RES_388_2026)          │
│  [2] gcloud composer environments storage dags import                    │
│        (copia dags/ingestao_legal_dag.py para o bucket de DAGs)         │
│  [3] gcloud composer environments run ... dags -- list                  │
│        (confirma que "ingestao_legal_taxreformai" foi descoberta)       │
│  [4] gcloud composer environments run ... dags -- trigger               │
│        (dispara a DAG manualmente, sem esperar o schedule @weekly)      │
│  [5] loop de polling: dags -- list_dag_runs até status success/failed   │
│  [6] scripts/verificar_composer_producao.py --depois                    │
│        conta pontos de novo, compara com --antes (idempotência)         │
│  [7] Evidência (logs + contagens) impressa no step summary              │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FASE 3 — Destruir (terraform.yml, workflow_dispatch, action=apply)      │
│                                                                            │
│  Remove os 3 recursos de main.tf (commit dedicado) → `terraform apply`  │
│  destrói o ambiente Composer (Terraform vê os recursos como removidos)  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `google_composer_environment.ingestao_legal` | Ambiente Composer 3 (Small), temporário | Terraform, `hashicorp/google` provider |
| `google_project_iam_member.ingestion_composer_worker` | Concede `roles/composer.worker` a `taxreform-ingestion` | Terraform |
| `.github/workflows/verificar_composer_producao.yml` | Orquestra upload da DAG, disparo, polling, verificação de idempotência | GitHub Actions, `gcloud` CLI |
| `scripts/verificar_composer_producao.py` | Conta pontos no Qdrant por `documento_id`, antes/depois | Python, `qdrant-client` (já em `requirements.txt`) |

---

## Key Decisions

### Decision 1: Recurso Terraform TEMPORÁRIO — adiciona, aplica, verifica, remove, reaplica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** O ambiente Composer custa de verdade ~US$300-400/mês rodando continuamente
(achado do `/brainstorm`), desproporcional a uma DAG de 2 tasks/semana. O usuário decidiu
explicitamente por um ciclo de vida efêmero, não uma feature de infraestrutura permanente.

**Choice:** O recurso `google_composer_environment` (mais a API e o IAM que ele exige) é
adicionado a `infra/terraform/main.tf` normalmente, aplicado via `terraform.yml`
(`workflow_dispatch`, `action=apply`), verificado, e então REMOVIDO do arquivo num commit
dedicado — o próximo `terraform apply` (mesmo workflow, mesma ação) destrói o recurso porque ele
não existe mais na configuração declarada.

**Rationale:** Reusa o `terraform.yml` já existente (guardas de confirmação, autenticação, plan
antes de apply) sem criar um workflow novo só para "destroy" — Terraform já trata "recurso
removido do arquivo" como "destruir na próxima apply" nativamente. Mesmo padrão que o projeto já
usa para colunas/tabelas de banco (ex.: migração 006 removeu `regras_tributarias_cache`).

**Alternatives Rejected:**
1. `terraform destroy -target=...` direto — rejeitado: exigiria um novo input/modo no
   `terraform.yml` só para esta feature, mais frágil que o padrão já estabelecido de "remover do
   arquivo e reaplicar" (que já é auditável via `git log`, sem flag especial).
2. Deixar o recurso declarado no `main.tf` para sempre, mas destruído manualmente via `gcloud`
   fora do Terraform — rejeitado: quebraria a disciplina "infraestrutura real só via Terraform"
   já estabelecida no projeto, e o state do Terraform ficaria dessincronizado da realidade.

**Consequences:**
- O histórico do `git log` de `infra/terraform/main.tf` mostra claramente dois commits: "adiciona
  Composer" e "remove Composer (verificado, destruído)" — rastreável.
- Se uma sessão futura precisar de Composer de novo, é só reverter/reaplicar o commit de adição
  (o código do recurso não se perde, só sai do estado ativo).

---

### Decision 2: Reusar `taxreform-ingestion` como SA do ambiente, não criar uma nova

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** Desde abril de 2025, novos ambientes Composer exigem uma SA explícita (não usam
mais a SA padrão do Compute Engine). `taxreform-ingestion` já existe desde
`PIPELINE_INGESTAO_LEGAL`, já tem `roles/storage.objectAdmin` escopado ao bucket de raw storage,
e nunca teve um consumidor real (o `ingestao.yml` atual usa outra identidade, a de deploy).

**Choice:** `google_composer_environment.ingestao_legal.config.node_config.service_account`
aponta para `google_service_account.ingestion_sa.email` (já existente), e um novo
`google_project_iam_member` concede `roles/composer.worker` a essa mesma SA.

**Rationale:** É exatamente a identidade que este projeto já criou para "o que roda a pipeline
de ingestão" — criar uma terceira SA para a mesma função duplicaria superfície de credenciais
sem ganho de isolamento (mesmo raciocínio já aplicado em `LLM_REAL_VERTEX_AI` Decision 5, para
`taxreformai-runtime`).

**Alternatives Rejected:**
1. Nova SA dedicada só ao Composer — rejeitada por duplicar uma identidade já existente para a
   mesma função, sem necessidade demonstrada de isolamento adicional.

**Consequences:**
- `taxreform-ingestion` acumula uma segunda role (`composer.worker`, além de
  `storage.objectAdmin`) — ainda escopada à função "rodar a ingestão", não um alargamento de
  escopo para algo não relacionado.

---

### Decision 3: Sem VPC customizada — rede gerenciada padrão do Composer 3

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** Composer 1/2 historicamente exigiam configuração de rede (VPC, ranges de IP) mais
complexa. O projeto já tem uma política deliberada de evitar VPC (Cloud SQL usa IP público sem
redes autorizadas, ver `SCHEMA_POSTGRESQL`).

**Choice:** `google_composer_environment` não declara nenhum bloco de rede customizada — usa o
padrão gerenciado do Composer 3.

**Rationale:** Pesquisa confirmou que Composer 3 não exige mais uma VPC customizada para
configuração básica — mantém a disciplina "sem VPC" já estabelecida, sem esforço extra.

**Alternatives Rejected:**
1. VPC dedicada — rejeitada, sem requisito de isolamento de rede levantado.

**Consequences:**
- Se um requisito de compliance futuro exigir rede privada, será uma mudança de escopo maior
  (fora desta feature).

---

### Decision 4: Verificação de idempotência via contagem de pontos no Qdrant, por `documento_id`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** A DAG reingere Planalto (`LCP_214_2025`) e TCU (`TCU_RES_388_2026`), fontes já
indexadas via `ingestao.yml`. O `point_id` é determinístico
(`uuid5(namespace, f"{documento_id}:{dispositivo}")`, ver `Chunk.qdrant_point_id()`), então uma
reingestão correta deve SOBRESCREVER os pontos existentes, nunca duplicá-los — mas isso nunca foi
provado contra uma execução real via Airflow, só via `pipeline.py` (CLI).

**Choice:** `scripts/verificar_composer_producao.py` usa `client.count(collection_name=...,
count_filter=Filter(must=[FieldCondition(key="documento_id", match=MatchValue(value=doc_id))]),
exact=True).count` — mesmo padrão já usado em `scripts/verificar_busca_hibrida.py` — chamado
ANTES de disparar a DAG e DEPOIS de ela concluir, para os dois `documento_id` que ela processa.

**Rationale:** Reusa uma chamada Qdrant já validada em produção (`verificar_busca_hibrida.py`),
sem inventar um novo mecanismo de verificação.

**Alternatives Rejected:**
1. Comparar hash do conteúdo — rejeitado, complexidade desnecessária; contagem exata por
   `documento_id` já detecta duplicação (contagem aumenta) ou perda (contagem diminui).

**Consequences:**
- Se as contagens baterem exatamente (mesmo total antes/depois), a idempotência está provada.
- Se aumentarem, é evidência de um bug real de duplicação — a feature não pode ser considerada
  bem-sucedida mesmo que a DAG tenha "rodado com status success".

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `infra/terraform/main.tf` | Modify (temporário) | `google_project_service.composer` + `google_composer_environment.ingestao_legal` + `google_project_iam_member.ingestion_composer_worker` | @python-developer | None |
| 2 | `scripts/verificar_composer_producao.py` | Create | Conta pontos no Qdrant por `documento_id`, modo `--antes`/`--depois` | @python-developer | None |
| 3 | `.github/workflows/verificar_composer_producao.yml` | Create | Orquestra upload da DAG, disparo, polling, chama o script de contagem | @python-developer | 1, 2 |
| 4 | `infra/terraform/main.tf` | Modify (remove) | Remove os 3 recursos da posição 1 — commit dedicado, após evidência coletada | @python-developer | 3 (só depois da verificação) |
| 5 | `CLAUDE.md` | Modify | Nova linha da feature, evidência real, nota de que o ambiente foi destruído | @doc-updater | 1-4 |

**Total Files:** 5 (3 novos/modificados + 1 reversão + docs)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3, 4 | Terraform HCL + script Python + workflow YAML, seguindo os padrões já estabelecidos do projeto |
| @doc-updater | 5 | Atualização de `CLAUDE.md` |

---

## Code Patterns

### Pattern 1: Recurso Terraform do ambiente Composer (Small, sem VPC)

```hcl
# infra/terraform/main.tf (trecho a adicionar — TEMPORÁRIO, ver Decision 1)

resource "google_project_service" "composer" {
  project            = var.project_id
  service            = "composer.googleapis.com"
  disable_on_destroy = false
}

# taxreform-ingestion (já existe, PIPELINE_INGESTAO_LEGAL) precisa desta role
# além de roles/storage.objectAdmin que já tem no bucket.
resource "google_project_iam_member" "ingestion_composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"

  depends_on = [google_project_service.composer]
}

resource "google_composer_environment" "ingestao_legal" {
  project = var.project_id
  name    = "taxreformai-ingestao-legal"
  region  = var.region

  config {
    software_config {
      image_version = "composer-3-airflow-2"
      env_variables = {
        GCP_PROJECT_ID  = var.project_id
        GCS_BUCKET_NAME = var.bucket_name
        # QDRANT_URL/QDRANT_API_KEY chegam como Airflow Variables via
        # `gcloud composer environments run ... variables -- set`, não aqui —
        # evita segredo em texto plano no state do Terraform.
      }
    }

    environment_size = "ENVIRONMENT_SIZE_SMALL"

    node_config {
      service_account = google_service_account.ingestion_sa.email
    }
  }

  depends_on = [
    google_project_service.composer,
    google_project_iam_member.ingestion_composer_worker,
  ]
}
```

### Pattern 2: Script de contagem por `documento_id` (idempotência)

```python
# scripts/verificar_composer_producao.py
import argparse
import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

DOCUMENTOS = ["LCP_214_2025", "TCU_RES_388_2026"]


def contar_pontos(client: QdrantClient, collection: str, documento_id: str) -> int:
    filtro = Filter(must=[FieldCondition(key="documento_id", match=MatchValue(value=documento_id))])
    return client.count(collection_name=collection, count_filter=filtro, exact=True).count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("momento", choices=["antes", "depois"])
    args = parser.parse_args()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria")

    contagens = {doc: contar_pontos(client, collection, doc) for doc in DOCUMENTOS}
    for doc, total in contagens.items():
        print(f"{args.momento}:{doc}={total}")

    if args.momento == "antes":
        with open("/tmp/contagens_antes.txt", "w") as f:
            for doc, total in contagens.items():
                f.write(f"{doc}={total}\n")
    else:
        antes = {}
        with open("/tmp/contagens_antes.txt") as f:
            for linha in f:
                doc, total = linha.strip().split("=")
                antes[doc] = int(total)

        divergiu = False
        for doc, total in contagens.items():
            if total != antes.get(doc):
                print(f"FALHA: {doc} tinha {antes.get(doc)} pontos antes, {total} depois — "
                      "reingestão NÃO é idempotente (duplicação ou perda).")
                divergiu = True
        if divergiu:
            sys.exit(1)
        print("OK idempotência confirmada — contagens idênticas antes/depois.")


if __name__ == "__main__":
    main()
```

### Pattern 3: Workflow de verificação (upload, disparo, polling)

```yaml
# .github/workflows/verificar_composer_producao.yml (trecho central)
- name: Contar pontos ANTES
  env:
    QDRANT_URL: ${{ secrets.QDRANT_URL }}
    QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
  run: python scripts/verificar_composer_producao.py antes

- name: Copiar a DAG para o ambiente
  run: |
    gcloud composer environments storage dags import \
      --environment=taxreformai-ingestao-legal --location="$REGION" \
      --source=dags/ingestao_legal_dag.py

- name: Confirmar que a DAG foi descoberta
  run: |
    gcloud composer environments run taxreformai-ingestao-legal --location="$REGION" \
      dags -- list | grep -q ingestao_legal_taxreformai

- name: Disparar a DAG manualmente
  run: |
    gcloud composer environments run taxreformai-ingestao-legal --location="$REGION" \
      dags -- trigger ingestao_legal_taxreformai

- name: Aguardar conclusão (polling)
  run: |
    for _ in $(seq 1 60); do
      STATUS=$(gcloud composer environments run taxreformai-ingestao-legal --location="$REGION" \
        dags -- list_dag_runs -d ingestao_legal_taxreformai --output=json \
        | python3 -c "import json,sys; runs=json.load(sys.stdin); print(runs[0]['state'] if runs else 'none')")
      echo "status=$STATUS"
      [ "$STATUS" = "success" ] && break
      [ "$STATUS" = "failed" ] && { echo "FALHA: DAG terminou com status failed"; exit 1; }
      sleep 30
    done
    [ "$STATUS" = "success" ] || { echo "FALHA: timeout aguardando conclusão"; exit 1; }

- name: Contar pontos DEPOIS e comparar
  env:
    QDRANT_URL: ${{ secrets.QDRANT_URL }}
    QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
  run: python scripts/verificar_composer_producao.py depois
```

---

## Data Flow

```text
1. terraform.yml (apply) cria o ambiente Composer real (~20-30 min)
   │
   ▼
2. verificar_composer_producao.yml:
   a. Conta pontos no Qdrant ANTES (LCP_214_2025, TCU_RES_388_2026)
   b. Copia dags/ingestao_legal_dag.py para o bucket de DAGs do ambiente
   c. Confirma que o scheduler descobriu a DAG (sem erro de import)
   d. Dispara a DAG manualmente
   e. Polling até status success/failed (timeout ~30 min)
   f. Conta pontos no Qdrant DEPOIS, compara com ANTES
   │
   ▼
3. Evidência (logs do Airflow + contagens antes/depois) registrada no BUILD_REPORT
   │
   ▼
4. infra/terraform/main.tf remove os 3 recursos Composer (commit dedicado)
   │
   ▼
5. terraform.yml (apply de novo) destrói o ambiente — Terraform vê os
   recursos como removidos da configuração declarada
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|------------------|
| Cloud Composer (Airflow gerenciado) | `gcloud composer environments ...` CLI | SA de Terraform (`GCP_SA_KEY`) para provisionar; SA `taxreform-ingestion` como identidade de runtime do ambiente |
| Qdrant Cloud | `qdrant-client` (já usado em `scripts/verificar_busca_hibrida.py`) | `QDRANT_URL`/`QDRANT_API_KEY` (já em GitHub Secrets) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `contar_pontos()` | Nenhum teste novo — função é um wrapper fino sobre `qdrant_client.count()`, mesmo padrão não-testado unitariamente de `verificar_busca_hibrida.py` | - | N/A — script de verificação, não código de produção |
| E2E real | Provisionamento + descoberta + execução + idempotência | `verificar_composer_producao.yml` | `gcloud`, `qdrant-client` | 100% — é o objetivo central da feature |

Não há testes `pytest` novos: `dags/ingestao_legal_dag.py` já é coberto por revisão de código
(decisão aceita em `INGESTAO_TCU_E_ETL_AIRFLOW`) e por testes de `ingestion/pipeline.py` via
fakes; esta feature verifica a INFRAESTRUTURA, não a lógica de negócio.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `terraform apply` falha ao criar o ambiente (permissão insuficiente da SA de Terraform) | Erro explícito do próprio `terraform apply` — achado real a corrigir (AT-006 do DEFINE), não assumido de antemão | Não automaticamente — requer diagnóstico |
| DAG não descoberta (erro de import) | `grep -q` falha, step reprova o workflow com o log de erro do Airflow visível | Não — precisa corrigir a DAG antes de tentar de novo |
| DAG falha (`status=failed`) | Workflow reprova explicitamente, log real do Airflow disponível para diagnóstico | Não automaticamente |
| Timeout no polling (~30 min sem success/failed) | Workflow reprova explicitamente — não assume sucesso silencioso | Não |
| Contagem diverge (duplicação/perda) | Script sai com código 1, workflow reprova — feature NÃO é considerada verificada mesmo com DAG "success" | Não |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `QDRANT_COLLECTION_NAME` | string | `legislacao_tributaria` | Reuso da mesma env var já usada em `ingestion/config.py` |

---

## Security Considerations

- `taxreform-ingestion` ganha `roles/composer.worker` além de `storage.objectAdmin` — ambas
  escopadas à função "rodar a pipeline de ingestão", sem alargamento para algo não relacionado.
- Segredos do Qdrant (`QDRANT_URL`/`QDRANT_API_KEY`) não entram no `env_variables` do Terraform
  (que fica no state) — são lidos como Airflow Variables/env vars de runtime pela própria task,
  já que `ingestion/config.py::Settings.from_env()` já sabe ler de variáveis de ambiente do
  processo que executa a task.
- Nenhuma superfície nova de rede pública (sem VPC customizada, sem novo endpoint exposto).

---

## Observability

| Aspect | Implementation |
|--------|-------------------|
| Logging | Log real do Airflow (via `gcloud composer environments run ... dags -- list_dag_runs` e a UI do ambiente durante a janela em que ele existe) — capturado no BUILD_REPORT antes do destroy, já que não existe mais depois |
| Métricas | Nenhuma — ambiente efêmero, sem necessidade de dashboard permanente |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-03 | design-agent | Initial version, extraído de DEFINE_CLOUD_COMPOSER_PROVISIONAMENTO.md |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_CLOUD_COMPOSER_PROVISIONAMENTO.md`
