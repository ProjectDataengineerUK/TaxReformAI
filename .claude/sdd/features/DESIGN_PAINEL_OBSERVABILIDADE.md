# DESIGN: PAINEL_OBSERVABILIDADE

> Especificação técnica do painel de observabilidade dentro do frontend

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PAINEL_OBSERVABILIDADE |
| **Date** | 2026-08-05 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_PAINEL_OBSERVABILIDADE.md](./DEFINE_PAINEL_OBSERVABILIDADE.md) |
| **Status** | Ready for Build |

---

## Achados que mudam a arquitetura (resolução de A-001/A-002/A-003 do DEFINE)

Antes de desenhar, investiguei as 3 assumptions não validadas do `/define`. Duas mudam o desenho:

- **A-001 (Billing API por serviço) — parcialmente errada.** Não existe uma chamada de API "me dê
  o custo do Cloud Run hoje" em tempo real. O mecanismo real do GCP é **Billing Export para
  BigQuery** — um export diário (com algumas horas de atraso) que o usuário liga uma vez no
  Console (não é algo que Terraform ou o agente conseguem ligar por conta própria; é ação de
  administrador da conta de billing). Ver Decision 2.
- **A-002 (role IAM mínima) — a resposta certa é ZERO role nova para `taxreformai-runtime`.**
  Investigando fonte a fonte, os 6 recursos + o sync do BigQuery têm sinal de saúde **sem** tocar
  Cloud Monitoring/Run Admin API: Cloud SQL via `pg_stat_activity` (já autenticado), Qdrant via
  HTTP no mesmo `QDRANT_URL`/`QDRANT_API_KEY` já usados, Anthropic via nossa própria tabela de uso
  (que esta feature já cria), Cloud Tasks via `sku_upload_jobs` (já existe), Frontend via HTTP
  público (mesmo padrão do smoke test de `deploy.yml`), API via estar respondendo. Ver Decision 1.
- **A-003 (latência da instrumentação de token) — confirmada como risco real, mitigada por
  desenho.** A gravação de uso é best-effort e nunca bloqueia — mesmo padrão de
  `api/audit.py::registrar_com_seguranca`. Ver Decision 4.

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND — /painel                              │
│   Diagrama · Sentinela · Maturidade · Segurança · Custo & FinOps         │
│   (mesma sessão Google + ALLOWED_EMAILS de /simulador e /consulta)       │
└───────────────────────────────┬────────────────────────────────────────-┘
                                 │ X-API-Key (mesmo auto-fetch já existente)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    API — api/routers/observabilidade.py                  │
│                                                                            │
│  GET /v1/observabilidade/status   (cache 60s)                            │
│  GET /v1/observabilidade/custo                                           │
│  GET /v1/observabilidade/scorecard                                       │
└───┬──────────────┬───────────────┬──────────────┬────────────┬──────────┘
    │              │               │              │            │
    ▼              ▼               ▼              ▼            ▼
pg_stat_       Qdrant HTTP    tabela        tabela          scorecard.yaml
activity       (health)       uso_llm       sku_upload_jobs (versionado,
(Cloud SQL,    (mesmas cre-   (nova, esta   (já existe)     sem cálculo)
já conectado)  denciais já    feature)
               usadas)

                    tabela custo_infra_diario  ◄── sync diário
                    tabela observabilidade_execucoes (heartbeat)
                              ▲
                              │ INSERT/UPDATE (taxreformai_app)
                              │
        ┌─────────────────────┴──────────────────────┐
        │  scripts/sincronizar_custo_infra.py         │
        │  (novo workflow, cron diário — mesmo padrão │
        │  de sincronizar_bigquery.py)                │
        └─────────────────────┬──────────────────────┘
                               │ SELECT (taxreformai-cost-sync, SA nova,
                               │ bigquery.dataViewer escopado ao dataset)
                               ▼
              BigQuery — dataset de Billing Export
              (usuário liga manualmente no Console GCP,
               ver Decision 2 — passo fora do alcance do agente)

        ┌──────────────────────────────────────────────┐
        │  orquestracao/llm/cliente.py                  │
        │  gerar(modelo, mensagens, max_tokens,         │
        │        no_origem) → registra uso best-effort  │
        │  em uso_llm ANTES de retornar/relançar erro   │
        └────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `observabilidade/status.py` | Deriva verde/amarelo/vermelho dos 6 recursos + sync BigQuery a partir de fontes já acessíveis | Python puro + `psycopg`/`httpx` |
| `observabilidade/custo.py` | Agrega custo de token (real) + custo de infra (espelhado) + achados FinOps por limiar | Python puro |
| `observabilidade/scorecard.yaml` | Scorecard de maturidade (MLOps/DataOps/LLMOps) e segurança, versionado, editado manualmente | YAML |
| `orquestracao/llm/registrador.py` | Grava uso de cada chamada real ao LLM — best-effort, nunca propaga exceção | Python puro (`psycopg`) |
| `api/routers/observabilidade.py` | 3 endpoints REST, mesma auth `X-API-Key` das rotas de negócio | FastAPI |
| `scripts/sincronizar_custo_infra.py` | Lê Billing Export do BigQuery, faz upsert do agregado diário em Cloud SQL | Python + `google-cloud-bigquery` |
| `frontend/app/painel/` | 5 abas, mesma proteção de sessão do `/simulador` | Next.js (App Router) |

---

## Key Decisions

### Decision 1: Status dos recursos sem nenhuma role IAM nova

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-05 |

**Context:** O `/define` assumiu (A-002) que seria preciso conceder `roles/monitoring.viewer`
e/ou `roles/run.viewer` a `taxreformai-runtime` para ler status ao vivo do Cloud Run/Cloud SQL.

**Choice:** Nenhuma role nova. Cada recurso deriva status de uma fonte que a API já acessa:

| Recurso | Fonte do sinal | Regra |
|---------|-----------------|-------|
| API (Cloud Run) | Trivial — está respondendo agora | Sempre verde se o endpoint responde |
| Frontend (Cloud Run) | `GET` HTTP público na URL do frontend, mesmo padrão do smoke test de `deploy.yml` | 200 = verde; timeout/erro = vermelho |
| Cloud SQL | `SELECT count(*) FROM pg_stat_activity` vs `SHOW max_connections` | <70% = verde, 70-90% = amarelo, >90% = vermelho (mesma classe de sinal que já causou `PoolTimeout` real em `FILA_ASSINCRONA_CELERY_REDIS`) |
| Qdrant Cloud | `GET` no endpoint de health da coleção, mesmas `QDRANT_URL`/`QDRANT_API_KEY` já injetadas | 200 rápido = verde; latência alta = amarelo; erro = vermelho |
| API Claude direta | Taxa de sucesso das últimas N linhas de `uso_llm` (esta feature cria) | 0 falhas recentes = verde; alguma falha = amarelo; falhas em sequência = vermelho |
| Cloud Tasks | Idade média dos jobs `PROCESSANDO` em `sku_upload_jobs` (já existe) | Dentro do esperado = verde; acima = amarelo; job preso muito além do esperado = vermelho (mesmo padrão do achado real de jobs órfãos em `FILA_ASSINCRONA_CELERY_REDIS`) |
| Sync BigQuery (cron) | Última linha de `observabilidade_execucoes` (nova, heartbeat) | Rodou na janela esperada = verde; atrasado = amarelo; última execução falhou = vermelho |

**Rationale:** Cada um desses sinais já é mais preciso para o propósito específico do que a
métrica genérica equivalente do Cloud Monitoring seria (ex: `pg_stat_activity` reflete o que
realmente esgotou antes, não uma métrica agregada por minuto). E elimina a necessidade de tocar
IAM de projeto para a SA de runtime, que já teve seu único desvio documentado (`aiplatform.user`).

**Alternatives Rejected:**
1. `roles/monitoring.viewer` + `roles/run.viewer` no runtime — rejeitado: mais permissão do que o
   necessário, quando as fontes diretas já respondem com mais precisão.
2. Cloud Tasks Admin API (`roles/cloudtasks.viewer`) para ver profundidade de fila — rejeitado:
   `sku_upload_jobs` já é o dado que a própria API escreve, mais direto que reconsultar o GCP.

**Consequences:**
- Ganho: zero mudança de IAM para o caminho de leitura ao vivo, zero risco de escopo excessivo.
- Trade-off: o sinal de Cloud SQL exige uma migração extra (`pg_read_all_stats`, ver Pattern 1
  abaixo) porque `taxreformai_app` só vê suas próprias linhas em `pg_stat_activity` por padrão.

---

### Decision 2: Custo de infra via Billing Export → BigQuery → Cloud SQL (não Billing API direta)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-05 |

**Context:** A-001 do `/define` assumia uma consulta direta à Billing API por serviço/dia. Essa
API não existe com essa granularidade — o mecanismo real e documentado do GCP para isso é o
export detalhado de billing para um dataset BigQuery.

**Choice:** Pipeline de 3 saltos, reaproveitando o padrão já validado de `sincronizar_bigquery.py`
(idempotente via staging+MERGE), só que na direção oposta (BigQuery → Cloud SQL):

1. **Passo manual do usuário** (fora do alcance do agente, mesma disciplina de toda credencial):
   habilitar "Cloud Billing export to BigQuery" (detailed usage cost) no Console, escolhendo um
   dataset (ex: `billing_export`).
2. **SA nova dedicada**, `taxreformai-cost-sync` (mesmo padrão de `taxreformai-bigquery-sync`, não
   reaproveita `GCP_SA_KEY`): `roles/bigquery.dataViewer` escopado ao dataset de billing export +
   `roles/cloudsql.client` (para o Cloud SQL Auth Proxy, mesmo binário/versão já usado em
   `sincronizar_bigquery.yml`).
3. **`scripts/sincronizar_custo_infra.py`**: consulta o dataset de billing export (agrega por
   `service.description` e `usage_start_time::date`), faz upsert em `custo_infra_diario` via
   staging+MERGE pela chave `(servico, data)`, autentica no Postgres como `taxreformai_app` (não
   `taxreformai_admin` — este job só escreve em 2 tabelas novas, privilégio mínimo real, diferente
   do sync do BigQuery que precisa iterar todos os tenants via `sessao_do_tenant`).

**Rationale:** Reaproveita infraestrutura e disciplina já provadas (SA dedicada, proxy, upsert
idempotente) em vez de inventar um mecanismo novo. O atraso de algumas horas do billing export é
aceitável — o `/define` já definiu a granularidade como diária, nunca em tempo real.

**Alternatives Rejected:**
1. Consultar a Billing API "Cloud Catalog" a cada request — rejeitado: essa API dá **preço de
   lista** por SKU, não gasto real incorrido; não serve para o que foi pedido.
2. Job escrever direto em BigQuery e o painel consultar BigQuery a cada request — rejeitado: exige
   dar à API (não só ao job de sync) uma credencial de leitura do BigQuery, ampliando a superfície
   de permissão do caminho de request; espelhar em Cloud SQL mantém a API lendo só de onde já lê.

**Consequences:**
- Ganho: mesma disciplina de idempotência/privilégio mínimo já provada no projeto.
- Trade-off real: **esta feature fica parcialmente bloqueada até o usuário habilitar o export no
  Console** — documentado explicitamente, mesma classe de bloqueio já aceita em
  `LLM_REAL_VERTEX_AI` (quota) e `FRONTEND_PREMIUM_GOOGLE_AUTH` (OAuth Client) — build entrega o
  mecanismo, verificação real fica pendente da ação do usuário.
- Custo de Qdrant Cloud e da API Claude direta **não aparecem aqui** — não são recursos GCP
  faturados nesse export (token da Claude já vem de `uso_llm`; Qdrant Cloud fica
  explicitamente "indisponível", nunca estimado — mesma disciplina de nunca inventar número).

---

### Decision 3: Sem `tenant_id` na tabela de uso de LLM (simplificação em relação ao DEFINE)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-05 |

**Context:** O rascunho de schema do `/define` incluía `tenant_id NOT NULL` com RLS, "mesma
disciplina do resto do schema". Mas isso exigiria threading de `tenant_id` até dentro de
`ClienteLLM.gerar()` (hoje uma função sem estado de request), tocando `State`,
`DependenciasOrquestracao` e os 3 nós que chamam o LLM.

**Choice:** Tabela de uso de LLM **sem** `tenant_id`, sem RLS. É dado operacional agregado
(quanto o sistema gastou, não quanto CADA tenant gastou), e o próprio `/define` já colocou
"drill-down por requisição individual" fora de escopo — não existe hoje nenhuma tela que precise
de custo POR tenant.

**Rationale:** Elimina uma cadeia de mudanças (State → DependenciasOrquestracao → 3 nós) para um
dado que a v1 do painel nunca exibe segmentado por tenant. Se um dia for preciso, é uma migração
aditiva (`ALTER TABLE ADD COLUMN tenant_id`), não uma reescrita.

**Alternatives Rejected:**
1. Threading completo de `tenant_id` (rascunho original do `/define`) — rejeitado: complexidade
   real sem consumidor no MVP.

**Consequences:**
- Ganho: mudança mecânica e pequena em `orquestracao/llm/cliente.py` (só `no_origem` novo).
- Trade-off: se o produto pedir "custo por cliente" no futuro, é uma feature nova, não algo que já
  vem de graça desta.

---

### Decision 4: Registro de uso é best-effort, nunca bloqueia a resposta ao usuário

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-05 |

**Context:** AT-004 do `/define` exige que a gravação de uso de token nunca derrube
`/v1/tax/query`, mesmo se a tabela/Cloud SQL estiver indisponível.

**Choice:** `RegistradorUsoLLM.registrar(...)` captura QUALQUER exceção internamente e só loga —
nunca propaga. Chamado de dentro de `ClienteVertexAI.gerar()`/`ClienteAnthropicDireto.gerar()`,
tanto no caminho de sucesso (com `tokens_entrada`/`tokens_saida` reais da resposta da Anthropic)
quanto no caminho de erro (antes de relançar `LLMIndisponivelError`, com `sucesso=False`).

**Rationale:** Mesmo padrão já estabelecido em `api/audit.py::registrar_com_seguranca` — "audit
log que NUNCA propaga exceção". Reaproveita a disciplina, não inventa uma nova.

**Alternatives Rejected:**
1. Gravação síncrona que pode lançar — rejeitado: violaria AT-004 diretamente.
2. Fila assíncrona real (Cloud Tasks, como o upload de SKUs) — rejeitado: complexidade
   desproporcional para um INSERT de poucas colunas; best-effort síncrono com try/except já resolve
   o requisito real (nunca bloquear), sem inventar infraestrutura nova.

**Consequences:**
- Ganho: simplicidade, reaproveita padrão já testado no projeto.
- Trade-off aceito: em caso raro de falha simultânea da gravação, aquela chamada específica fica
  sem registro de custo — aceitável, é telemetria, não dado de negócio auditável.

---

### Decision 5: Scorecard de maturidade/segurança é YAML lido, nunca calculado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-05 |

**Context:** Já validado no `/brainstorm` — maturidade e segurança são avaliação humana contra um
framework, não uma métrica computável a partir de logs.

**Choice:** `observabilidade/scorecard.yaml`, versionado no repositório, com 4 seções (`mlops`,
`dataops`, `llmops`, `seguranca`) mais `finops_achados` (lista curada, estática). O endpoint
`GET /v1/observabilidade/scorecard` só lê e serve o arquivo — parseado uma vez, cacheado em
memória do processo (invalida só em novo deploy, já que o arquivo vem embutido na imagem).

**Rationale:** Consistente com a decisão do `/brainstorm`: histórico de evolução do score vem "de
graça" via `git log` do arquivo, sem precisar de tabela nem endpoint de escrita.

**Consequences:**
- Ganho: zero infraestrutura de escrita para esta aba.
- Trade-off: atualizar o score é uma ação manual (editar o YAML + PR), não parte do fluxo
  automático — aceito, é o comportamento pedido.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/016_observabilidade_uso_llm.sql` | Create | Tabela `uso_llm` + GRANT (SELECT+INSERT) a `taxreformai_app` | @database-reviewer | None |
| 2 | `db/migrations/017_observabilidade_custo_infra.sql` | Create | Tabela `custo_infra_diario` (UNIQUE servico+data) + GRANT | @database-reviewer | None |
| 3 | `db/migrations/018_observabilidade_execucoes.sql` | Create | Tabela `observabilidade_execucoes` (heartbeat) + GRANT | @database-reviewer | None |
| 4 | `db/migrations/019_pg_read_all_stats.sql` | Create | `GRANT pg_read_all_stats TO taxreformai_app` — sem isso só vê as próprias conexões em `pg_stat_activity` | @database-reviewer | None |
| 5 | `observabilidade/__init__.py` | Create | Pacote novo, mesmo nível de `motor_calculo/`/`orquestracao/` | @python-developer | None |
| 6 | `observabilidade/scorecard.yaml` | Create | Dado versionado: maturidade + segurança + achados FinOps | (manual, conteúdo definido no `/build`) | None |
| 7 | `observabilidade/status.py` | Create | `calcular_status()` — as 7 regras da Decision 1 | @python-developer | 4 |
| 8 | `observabilidade/custo.py` | Create | Agregação de `uso_llm` + `custo_infra_diario` + limiares FinOps | @python-developer | 1, 2 |
| 9 | `orquestracao/llm/registrador.py` | Create | `RegistradorUsoLLM` Protocol + implementação real (best-effort) | @python-developer | 1 |
| 10 | `orquestracao/llm/cliente.py` | Modify | `gerar()` ganha `no_origem: str`; grava uso via registrador nos 2 caminhos (sucesso/erro) | @python-developer | 9 |
| 11 | `orquestracao/dependencias.py` | Modify | `DependenciasOrquestracao` ganha `registrador_uso_llm`; fábricas real/fake atualizadas | @python-developer | 9 |
| 12 | `orquestracao/nos/classificador.py` | Modify | Passa `no_origem="classificador"` | @python-developer | 10 |
| 13 | `orquestracao/nos/extrator_regras.py` | Modify | Passa `no_origem="extrator_regras"` | @python-developer | 10 |
| 14 | `orquestracao/nos/sintetizador.py` | Modify | Passa `no_origem="sintetizador"` | @python-developer | 10 |
| 15 | `api/routers/observabilidade.py` | Create | 3 endpoints (`/status` cache 60s, `/custo`, `/scorecard`) | @python-developer | 7, 8 |
| 16 | `api/main.py` | Modify | Registra o router novo | @python-developer | 15 |
| 17 | `api/Dockerfile` | Modify | `COPY observabilidade/` | @python-developer | 5 |
| 18 | `scripts/sincronizar_custo_infra.py` | Create | Lê billing export do BigQuery, upsert em `custo_infra_diario`, grava heartbeat | @gcp-data-architect | 2, 3 |
| 19 | `scripts/sincronizar_bigquery.py` | Modify | Grava heartbeat em `observabilidade_execucoes` ao final (sucesso e falha) | @python-developer | 3 |
| 20 | `.github/workflows/sincronizar_custo_infra.yml` | Create | Cron diário + `workflow_dispatch`, mesmo padrão de `sincronizar_bigquery.yml` | (manual, mesmo padrão de workflow já existente) | 18 |
| 21 | `infra/terraform/main.tf` | Modify | SA `taxreformai-cost-sync` + `bigquery.dataViewer` (escopado) + `cloudsql.client`; **nenhuma role nova para `taxreformai-runtime`** | (manual, segue padrão de `taxreformai-bigquery-sync`) | None |
| 22 | `frontend/app/painel/page.tsx` | Create | Shell com 5 abas | @typescript-reviewer | None |
| 23 | `frontend/app/painel/DiagramaTab.tsx` | Create | SVG dinâmico (mesmo layout da Fig. 01 do Artifact estático, cor por status) | @typescript-reviewer | 15 |
| 24 | `frontend/app/painel/SentinelaTab.tsx` | Create | Mesma fonte de `/status`, apresentação em lista/tabela | @typescript-reviewer | 15 |
| 25 | `frontend/app/painel/MaturidadeTab.tsx` | Create | Renderiza `mlops`/`dataops`/`llmops` de `/scorecard` | @typescript-reviewer | 15 |
| 26 | `frontend/app/painel/SegurancaTab.tsx` | Create | Renderiza `seguranca` de `/scorecard` | @typescript-reviewer | 15 |
| 27 | `frontend/app/painel/CustoFinOpsTab.tsx` | Create | Renderiza `/custo` (totais + achados FinOps) | @typescript-reviewer | 15 |
| 28 | `frontend/lib/types.ts` | Modify | Tipos das 3 respostas novas | @typescript-reviewer | None |
| 29 | `tests/test_observabilidade_status.py` | Create | Cobre as 7 regras de status (fakes de cada fonte) | @test-generator | 7 |
| 30 | `tests/test_observabilidade_custo.py` | Create | Agregação + limiares FinOps | @test-generator | 8 |
| 31 | `tests/test_registrador_uso_llm.py` | Create | Nunca propaga exceção (AT-004), grava sucesso e falha | @test-generator | 9 |
| 32 | `tests/test_nos.py` | Modify | Ajusta chamadas de `gerar()` com `no_origem` novo | @test-generator | 10 |
| 33 | `frontend/app/painel/*.test.tsx` | Create | Smoke test de cada aba (renderiza com fetch mockado) | @typescript-reviewer | 22-27 |

**Total Files:** 33 (14 novos no backend, 6 novos no frontend, 4 migrações, 1 workflow, 5 testes novos, resto modificações pequenas e mecânicas)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|-----------------|------------------|
| @database-reviewer | 1, 2, 3, 4 | Migrações novas, GRANTs, `pg_read_all_stats` — mesma disciplina de privilégio mínimo já auditada no schema |
| @python-developer | 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19 | Módulos Python novos + modificações mecânicas em `orquestracao/`/`api/` seguindo padrões já existentes |
| @gcp-data-architect | 18 | Único arquivo que fala com BigQuery Billing Export — mesma classe de trabalho de `sincronizar_bigquery.py` |
| @typescript-reviewer | 22-28, 33 | Toda a superfície nova do frontend + tipos |
| @test-generator | 29, 30, 31, 32 | Testes novos e ajuste dos existentes |
| (manual, usuário) | 6 (conteúdo), 20 (secrets), 21 (SA key) | Mesma disciplina de todo credential/scorecard humano já estabelecida — agente não gera segredo nem julga a nota de maturidade sozinho |

---

## Code Patterns

### Pattern 1: Cloud SQL — conexões ativas vs `max_connections`

```python
# observabilidade/status.py — usa a MESMA pool de conexão já injetada via api/db.py,
# não abre conexão nova. Requer db/migrations/019 (GRANT pg_read_all_stats).

def status_cloud_sql(conexao) -> ResourceStatus:
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_stat_activity")
        ativos = cur.fetchone()[0]
        cur.execute("SHOW max_connections")
        maximo = int(cur.fetchone()[0])

    uso_percentual = ativos / maximo
    if uso_percentual >= 0.9:
        return ResourceStatus(nivel="vermelho", detalhe=f"{ativos}/{maximo} conexões ({uso_percentual:.0%})")
    if uso_percentual >= 0.7:
        return ResourceStatus(nivel="amarelo", detalhe=f"{ativos}/{maximo} conexões ({uso_percentual:.0%})")
    return ResourceStatus(nivel="verde", detalhe=f"{ativos}/{maximo} conexões")
```

### Pattern 2: Registrador de uso — best-effort, nunca propaga (mesmo molde de `api/audit.py`)

```python
# orquestracao/llm/registrador.py

class RegistradorUsoLLM(Protocol):
    def registrar(
        self, no_origem: str, modelo: str, tokens_entrada: int, tokens_saida: int, sucesso: bool,
        erro_detalhe: str | None = None,
    ) -> None: ...


class RegistradorUsoLLMPostgres:
    def __init__(self, db_pool):
        self._db_pool = db_pool

    def registrar(self, no_origem, modelo, tokens_entrada, tokens_saida, sucesso, erro_detalhe=None) -> None:
        try:
            with self._db_pool.connection() as conexao, conexao.cursor() as cur:
                cur.execute(
                    "INSERT INTO uso_llm (no_origem, modelo, tokens_entrada, tokens_saida, sucesso, erro_detalhe) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (no_origem, modelo, tokens_entrada, tokens_saida, sucesso, erro_detalhe),
                )
        except Exception:  # noqa: BLE001 — nunca propaga, mesma disciplina de registrar_com_seguranca
            logging.getLogger(__name__).warning("Falha ao registrar uso de LLM (no_origem=%s)", no_origem)
```

### Pattern 3: `gerar()` com `no_origem` — grava nos dois caminhos

```python
# orquestracao/llm/cliente.py (ClienteAnthropicDireto, mesma forma em ClienteVertexAI)

def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024, no_origem: str = "desconhecido") -> str:
    modelo_real = _MAPA_MODELO_PARA_API_DIRETA.get(modelo, modelo)
    try:
        resposta = self._client.messages.create(model=modelo_real, max_tokens=max_tokens, messages=mensagens)
    except Exception as exc:
        self._registrador.registrar(no_origem, modelo, 0, 0, sucesso=False, erro_detalhe=str(exc)[:200])
        raise LLMIndisponivelError(f"API Claude direta indisponível: {exc}") from exc

    texto = _extrair_texto(resposta, "a API Claude direta")
    self._registrador.registrar(
        no_origem, modelo, resposta.usage.input_tokens, resposta.usage.output_tokens, sucesso=True,
    )
    return texto
```

### Pattern 4: Migração — tabela de custo de infra (upsert por `servico`+`data`)

```sql
-- db/migrations/017_observabilidade_custo_infra.sql
CREATE TABLE custo_infra_diario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    servico VARCHAR NOT NULL,
    data DATE NOT NULL,
    custo_usd NUMERIC(12, 4) NOT NULL,
    sincronizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (servico, data)
);

GRANT SELECT, INSERT, UPDATE ON custo_infra_diario TO taxreformai_app;
```

### Pattern 5: `scorecard.yaml` — schema

```yaml
# observabilidade/scorecard.yaml
mlops:
  framework: "Google MLOps Maturity Model (níveis 0-4, mapeados para 1-5)"
  nota: 3
  justificativa: "Pipeline determinístico versionado e testado; falta model registry formal para os prompts/modelos usados"
seguranca:
  framework: "OWASP Top 10 + NIST CSF (Identify/Protect/Detect/Respond/Recover)"
  nota: 4
  por_funcao:
    Identify: 4
    Protect: 4
    Detect: 3
    Respond: 3
    Recover: 3
  justificativa: "RLS provado contra produção, mascaramento de PII, guardrail de síntese — falta Detect/Respond automatizado (esta feature ajuda)"
finops_achados:
  - achado: "Cloud SQL db-f1-micro esgotou connection pool sob carga real de 55.000 linhas"
    fonte: "FILA_ASSINCRONA_CELERY_REDIS, achado real não corrigido"
    oportunidade: "Upgrade de tier ou pool externo (pgbouncer) antes de reabrir a meta de 50.000+ linhas"
  - achado: "Cloud Composer custava US$300-400/mês para uma DAG de 2 tasks/semana"
    fonte: "CLOUD_COMPOSER_PROVISIONAMENTO, decisão já tomada (ambiente destruído)"
    oportunidade: "Já resolvido — mantido aqui como precedente de decisão FinOps"
```

---

## Data Flow

```text
1. Chamada real ao LLM (classificador/extrator_regras/sintetizador)
   │
   ▼
2. ClienteVertexAI/ClienteAnthropicDireto.gerar(..., no_origem=X)
   │  sucesso → grava tokens reais da resposta
   │  falha   → grava sucesso=False, relança LLMIndisponivelError normalmente
   ▼
3. Linha em uso_llm (best-effort, nunca bloqueia o request original)

--- em paralelo, diário ---

4. sincronizar_custo_infra.py lê billing export (BigQuery)
   │
   ▼
5. Upsert em custo_infra_diario (staging+MERGE por servico+data)
   │
   ▼
6. Heartbeat em observabilidade_execucoes

--- a cada abertura do painel ---

7. Frontend chama GET /v1/observabilidade/status (cache 60s no processo da API)
   │
   ▼
8. observabilidade/status.py roda as 7 checagens (Decision 1) e devolve o agregado
   │
   ▼
9. Frontend pinta o diagrama/sentinela com as cores
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-------------------|--------------------|-------------------|
| Cloud SQL (`pg_stat_activity`) | SQL via pool já existente | Já autenticado (`taxreformai_app`) |
| Qdrant Cloud | HTTP (health/collection info) | `QDRANT_URL`/`QDRANT_API_KEY` já injetados |
| BigQuery (billing export) | `google-cloud-bigquery` | SA nova `taxreformai-cost-sync`, `roles/bigquery.dataViewer` escopado ao dataset |
| GCP Billing Export | Configuração manual no Console (1x) | Fora do alcance do agente — decisão de administrador de billing |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|------------------|
| Unit | `observabilidade/status.py` (7 regras) | `tests/test_observabilidade_status.py` | pytest, fakes de cada fonte (sem Cloud SQL/Qdrant reais) | Todas as 7 regras, incl. limites (69%/70%/90%) |
| Unit | `observabilidade/custo.py` | `tests/test_observabilidade_custo.py` | pytest | Agregação + limiares FinOps |
| Unit | `RegistradorUsoLLM` | `tests/test_registrador_uso_llm.py` | pytest | AT-004 — nunca propaga exceção mesmo com DB indisponível (mock que lança) |
| Integration | `gerar()` com `no_origem` | `tests/test_nos.py` (ajustado) | pytest, `ClienteLLMFake` | Sucesso e falha gravam com `no_origem` correto |
| Frontend | Cada aba renderiza com fetch mockado | `frontend/app/painel/*.test.tsx` | Vitest + Testing Library | Smoke test das 5 abas |
| E2E | Pendente de infraestrutura real | Manual, mesma disciplina de `migrar_banco.yml`/`deploy.yml` | `verificar_*_producao.py` novo (Build decide se cabe) | Status real contra Cloud SQL/Qdrant de produção |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|----------------------|--------|
| Falha ao gravar uso de LLM | Log + segue (Decision 4) | Não |
| Fonte de status indisponível (ex: Qdrant fora do ar) | Aquele recurso específico vira "vermelho" com o motivo — nunca derruba os outros 5 | Não |
| Billing export ainda não habilitado pelo usuário | `sincronizar_custo_infra.py` falha ruidosamente (é um workflow manual, não caminho de usuário) | Não — mesma disciplina de "falha ruidosa em CI, nunca silenciosa" já usada em `verificar_ipi_producao.py` |
| `scorecard.yaml` ausente/malformado no deploy | 503 explícito no endpoint, nunca 200 com dado vazio fingindo ser real | Não |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `OBSERVABILIDADE_STATUS_CACHE_SEGUNDOS` | int | `60` | Janela de cache em memória do endpoint `/status` |
| `OBSERVABILIDADE_CLOUDSQL_LIMIAR_AMARELO` | float | `0.7` | % de `max_connections` que vira amarelo |
| `OBSERVABILIDADE_CLOUDSQL_LIMIAR_VERMELHO` | float | `0.9` | % de `max_connections` que vira vermelho |
| `BILLING_EXPORT_DATASET` | string | (obrigatório no workflow novo) | Nome do dataset BigQuery escolhido pelo usuário no Console |

---

## Security Considerations

- Painel atrás da mesma sessão Google + `ALLOWED_EMAILS` de `/simulador`/`/consulta` — nenhuma
  allowlist nova (decisão do `/brainstorm`), mas nenhum dado novo aqui é mais sensível do que
  custo/status operacional (não expõe segredos, chaves, nem dado de tenant).
- `uso_llm`/`custo_infra_diario`/`observabilidade_execucoes` **sem RLS** — são dados agregados do
  sistema inteiro, não de um tenant (Decision 3); não há vazamento cross-tenant possível porque
  não há dimensão de tenant nessas tabelas.
- `erro_detalhe` em `uso_llm` grava só a mensagem de exceção do cliente LLM (já sem PII, porque
  ocorre depois do mascaramento do `classificador`) — truncada a 200 chars, nunca o payload bruto.
- `taxreformai-cost-sync` (SA nova) segue o mesmo princípio já estabelecido: escopo mínimo,
  credencial gerada e cadastrada manualmente pelo usuário, nunca pelo agente.

---

## Observability

| Aspect | Implementation |
|--------|-------------------|
| Logging | `logging.getLogger(__name__)` nos pontos de falha best-effort (registrador, status) — mesmo padrão do resto do projeto |
| Metrics | O próprio painel É a camada de métricas — sem ferramenta externa nova |
| Tracing | Fora de escopo (não pedido, YAGNI) |

---

## Pipeline Architecture — sync de custo de infra

### DAG Diagram

```text
[GCP Billing Export] ──(diário, atraso de horas)──→ [Dataset BigQuery]
                                                            │
                                                     query agregada
                                                            │
                                                            ▼
                                                [staging temporário]
                                                            │
                                                    MERGE por (servico, data)
                                                            │
                                                            ▼
                                              [custo_infra_diario, Cloud SQL]
                                                            │
                                                      heartbeat
                                                            │
                                                            ▼
                                          [observabilidade_execucoes]
```

### Incremental Strategy

| Model | Strategy | Key Column | Lookback |
|-------|----------|--------------|-----------|
| `custo_infra_diario` | `unique_key` (MERGE) | `(servico, data)` | 7 dias (para cobrir revisões tardias do billing export, que o GCP documenta como possíveis) |

### Data Quality Gates

| Gate | Tool | Threshold | Action on Failure |
|------|------|-----------|-----------------------|
| Nenhuma linha com `custo_usd < 0` | Assert no próprio script | 0 negativos | Aborta o sync, loga, heartbeat com `sucesso=False` |
| Dataset de billing export acessível | Try/except na primeira query | — | Aborta ruidosamente (mesma disciplina de `verificar_ipi_producao.py`) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|------------|
| 1.0 | 2026-08-05 | design-agent | Versão inicial — resolve A-001/A-002/A-003 do DEFINE, corrige a suposição de Billing API direta e elimina necessidade de role IAM nova para o runtime |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_PAINEL_OBSERVABILIDADE.md`

**Pendências que não bloqueiam o `/build` mas bloqueiam a verificação real end-to-end:**
1. Usuário precisa habilitar Billing Export → BigQuery no Console GCP (Decision 2) antes do sync
   de custo de infra rodar de verdade.
2. Usuário precisa gerar e cadastrar a chave da SA `taxreformai-cost-sync` como GitHub Secret,
   depois que o Terraform criar a SA (mesma disciplina de toda credencial já estabelecida).
