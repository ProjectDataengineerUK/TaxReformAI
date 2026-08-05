# BRAINSTORM: PAINEL_OBSERVABILIDADE

> Sessão exploratória para esclarecer intenção e abordagem antes da captura de requisitos

## Metadata

| Atributo | Valor |
|----------|-------|
| **Feature** | PAINEL_OBSERVABILIDADE |
| **Data** | 2026-08-05 |
| **Autor** | brainstorm-agent (sessão interativa) |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input (usuário):** "Depois pode me entregar este painel dentro do front acrescentando mais
abas. Preciso que implemente um painel de observabilidade. Onde terá um desenho de arquitetura
dinâmico. Mostrando cada recurso criado em verde funcionando em amarelo atenção em vermelho. Um
painel sentinela. Mostrando o status de cada processo e recursos com a mesma dinâmica. Outra aba
mostrando maturidade do sistema. Calcular a maturidade MLOps DataOps e LLMOps escala de 1 a 5.
Registrar o nível de segurança do sistema. E registrar o custo de cada serviço. Inclusive token. E
oportunidades de FinOps."

**Contexto Gathered:**
- O pedido veio logo depois de eu publicar um Artifact estático (`Fig. 01/02/03` + tabela de
  estado real dos componentes) — o painel pedido é a versão **viva, dentro do produto** dessa
  mesma informação, mais 3 dimensões novas (maturidade, segurança, custo/FinOps) que o Artifact
  estático não cobria.
- O frontend já tem precedente direto para "informação que só quem está logado vê": login Google
  + `ALLOWED_EMAILS` (`FRONTEND_PREMIUM_GOOGLE_AUTH`) e o auto-fetch de credencial server-side
  (`app/api/api-key/route.ts`, `FRONTEND_PREMIUM_GOOGLE_AUTH` + sessão desta mesma conversa).
- O projeto já tem DOIS padrões de "olhar infraestrutura real de fora": (1) leitura ao vivo via
  `diagnostico_cloud_run_logs.yml` (Cloud Logging, sob demanda); (2) sync periódico via cron
  (`sincronizar_bigquery.py`, único workflow do projeto com `schedule: cron`). O painel reusa os
  dois, cada um para o tipo de dado certo (ver Approach A abaixo).
- Nenhuma chamada real ao LLM registra tokens hoje — nem em `orquestracao/llm/cliente.py` nem em
  `pareceres_audit_log`. Custo de token exige instrumentação nova, não é dado que já existe em
  algum lugar esperando ser lido.
- `taxreformai-runtime` (a SA de runtime da API) tem hoje só `roles/cloudsql.client` +
  `roles/aiplatform.user` (concedida em `LLM_REAL_VERTEX_AI`) — zero permissão de leitura de
  Monitoring/Billing/Run Admin. Isso é uma role NOVA a conceder, mesmo padrão de desvio já
  documentado (`roles/aiplatform.user` foi a primeira role de projeto dessa SA).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Likely Location (API) | `api/routers/observabilidade.py` (novo), reaproveitando `api/dependencias_orquestracao.py`/`api/db.py` como padrão de `Depends` | Router novo, mesmo padrão dos demais |
| Likely Location (frontend) | `frontend/app/painel/` (nova área, com sub-rotas por aba) ou tabs dentro de uma única rota | A decidir no `/design` — depende de quanto cada aba pesa |
| Likely Location (dados) | `db/migrations/016_*.sql` em diante (próxima migração livre) | Tabelas novas: uso de token por chamada, snapshot de custo de infra, scorecard de maturidade/segurança (ou este último fica só em YAML versionado, ver Approach A) |
| IaC Patterns | `infra/terraform/main.tf` já gerencia roles da `taxreformai-runtime` | Nova role (`roles/monitoring.viewer` e/ou `roles/run.viewer`, `roles/billing.viewer` — a confirmar no `/design` qual é a mínima necessária) entra ali, mesmo padrão de `LLM_REAL_VERTEX_AI` |
| Relevant patterns a reusar | `diagnostico_cloud_run_logs.yml` (leitura ao vivo, read-only, descartável) e `sincronizar_bigquery.py` (sync periódico, idempotente via staging+MERGE) | Ambos os mecanismos already-proven, não greenfield |

---

## Discovery Questions & Answers

| # | Pergunta | Resposta | Impacto |
|---|----------|----------|---------|
| 1 | Entregar tudo de uma vez ou faseado? | (a) Tudo junto — uma feature grande, um `/design`/`/build` | Escopo único, mas com YAGNI aplicado internamente (ver abaixo) para não inflar o MVP |
| 2 | Framework para maturidade/segurança? | (c) Framework reconhecido + nota de onde a prática do projeto diverge | Scorecard cita a fonte (Google MLOps MM, DataKitchen DataOps MM, OWASP Top 10 + NIST CSF) e não finge ser uma certificação externa |
| 3 | Como rastrear custo de infra e de token? | (c) Híbrido — infra via GCP Billing API, token via instrumentação própria (única fonte confiável hoje) | Dois mecanismos de coleta distintos, unificados só na apresentação |
| 4 (samples) | Tem exemplo/referência para grounding? | (c) Nenhum — construir do zero com base nos padrões já existentes no projeto | Sem few-shot externo; usa `diagnostico_cloud_run_logs.yml` e `pareceres_audit_log` como referência de padrão de código |
| 5 | Quem pode ver o painel? | (a) Toda a allowlist atual (`ALLOWED_EMAILS`) — sem camada de permissão nova | Sem `OBSERVABILITY_ALLOWED_EMAILS` nem role separada; mesma proteção de sessão que já protege `/simulador`/`/consulta` |

**Mínimo de perguntas:** 5 (acima do mínimo de 3)

---

## Sample Data Inventory

| Tipo | Localização | Notas |
|------|-------------|-------|
| Amostras externas | N/A | Usuário confirmou: nenhuma — construir do zero |
| Padrão de código a reusar | `.github/workflows/diagnostico_cloud_run_logs.yml` | Leitura ao vivo, read-only, via `gcloud logging read` — vira a base do endpoint de status ao vivo |
| Padrão de código a reusar | `scripts/sincronizar_bigquery.py` | Sync periódico idempotente (staging+MERGE) — vira a base do sync de custo de infra |
| Dado real já existente | `db/migrations/002`/`003` (RLS, papel de runtime) | Referência de como conceder role nova a `taxreformai-runtime` sem violar o princípio de privilégio mínimo já estabelecido |

---

## Approaches Explored

### Approach A: Três velocidades diferentes por natureza do dado ⭐ Recomendado

**Descrição:** Cada aba usa a fonte de dado certa para o que ela é, em vez de forçar tudo pelo
mesmo mecanismo:

1. **Diagrama dinâmico + Sentinela** — endpoint novo na API (`GET /v1/observabilidade/status`)
   consulta ao vivo Cloud Monitoring/Cloud Run Admin API (cache de ~60s no processo, para não
   estourar cota do GCP a cada abertura de aba). Verde/amarelo/vermelho refletem o agora.
2. **Custo + token** — duas fontes:
   - Token: `ClienteVertexAI`/`ClienteAnthropicDireto` passam a gravar cada chamada real (modelo,
     tokens de entrada/saída) numa tabela nova do Cloud SQL — única fonte confiável, porque nem
     GCP Billing nem Anthropic Console cobrem o custo por chamada com granularidade suficiente.
   - Infra: sync periódico da GCP Billing API (mesmo padrão de `sincronizar_bigquery.py`,
     cron diário), grava snapshot por serviço.
3. **Maturidade + Segurança** — não são recalculadas a cada request (não existe "cálculo" real
   para isso). Viram um **scorecard versionado no repositório** (YAML), atualizado manualmente
   (ou como parte do `/ship` de cada feature futura), que o painel só lê e renderiza. Histórico de
   evolução do score fica "de graça" via `git log` do arquivo — não precisa de tabela nem de
   endpoint de escrita.

**Prós:**
- Cada dado tem a frescor que faz sentido (status = agora; custo = diário; maturidade = quando
  alguém revisa) em vez de forçar tudo a ser "ao vivo" ou tudo a ser "snapshot".
- Reaproveita 2 mecanismos já provados no projeto, não inventa um terceiro do zero.
- Maturidade/segurança ficam auditáveis e versionadas (um PR que muda o score é rastreável),
  nunca uma caixa-preta "a IA calculou".

**Contras:**
- São 3 mecanismos de coleta diferentes para construir e manter, não um só.

**Por que Recomendado:** É a única abordagem que não finge que maturidade/segurança são métricas
computáveis — e é a que menos infraestrutura nova inventa, reaproveitando os 2 padrões que o
projeto já validou em produção.

---

### Approach B: Tudo como snapshot periódico

**Descrição:** Um job de cron único (5-15min) recalcula status, custo, e um "score" de
maturidade/segurança, grava tudo num snapshot que o painel só lê.

**Por que não recomendado:** Um "sentinela" com minutos de atraso é pior que um sentinela que
apura ao vivo. E forçar maturidade/segurança a serem "recalculadas por cron" finge que existe uma
fórmula automática para algo que é avaliação humana contra um framework.

---

### Approach C: Tudo ao vivo, a cada carregamento da página

**Descrição:** Toda abertura do painel dispara todas as consultas (GCP, billing, Anthropic) na
hora, sem cache nem snapshot.

**Por que não recomendado:** Caro (rate limit real do GCP/Anthropic a cada F5), lento de carregar,
e maturidade/segurança de novo não têm "cálculo ao vivo" que faça sentido — viraria um spinner de
loading para uma decisão humana disfarçada de métrica.

---

## Simplificação (YAGNI)

| Aba | Entra no MVP | Fica de fora (motivo) |
|-----|--------------|------------------------|
| Diagrama dinâmico | Frontend, API, Cloud SQL, Qdrant, Anthropic API, Cloud Tasks — os 6 recursos já mapeados na Fig. 01 do Artifact estático | GCS, Artifact Registry, BigQuery em si — não estão no caminho de uma requisição real |
| Sentinela | Mesmos 6 recursos + status do sync do BigQuery (é um cron que já teve histórico de risco de falha silenciosa) | Histórico de incidentes — só o status atual |
| Maturidade | Score atual (1-5) por eixo — MLOps/DataOps/LLMOps — com framework citado + nota de divergência | Gráfico de tendência ao longo do tempo (fica "de graça" depois, via `git log` do YAML, mas não entra na v1) |
| Segurança | Score atual + framework (OWASP Top 10 + NIST CSF) + notas | Tendência histórica — mesma razão acima |
| Custo + token | Totais agregados por serviço, por dia/mês | Custo por requisição individual (drill-down) — fica para depois |
| FinOps | Lista curada: achados reais já documentados no projeto (ex: Cloud SQL `db-f1-micro` esgotou sob carga real em `FILA_ASSINCRONA_CELERY_REDIS`; Cloud Composer destruído por custo desproporcional) + alertas simples por limiar (ex: "gasto subiu X% na semana") | Recomendação preditiva/gerada por IA — nada de "sugestão automática de otimização" |
| Transversal | Sem tempo real (WebSocket/SSE) — carrega ao abrir a aba + botão de atualizar manual, cache de 60s no backend para o status ao vivo | — |
| Acesso | Mesma `ALLOWED_EMAILS` de hoje, sem allowlist nova | — |

---

## Regras de Status (verde / amarelo / vermelho)

| Recurso | Verde | Amarelo | Vermelho |
|---------|-------|---------|----------|
| Cloud Run — API/Frontend | Servindo, sem 5xx recente | 5xx esporádico | Serviço fora do ar / 5xx sustentado |
| Cloud SQL | Conectando normalmente | Uso de connection pool alto (já observado: `PoolTimeout` real no `db-f1-micro`, ver `FILA_ASSINCRONA_CELERY_REDIS`) | Falha de conexão |
| Qdrant Cloud | Busca respondendo | Latência alta | Inacessível |
| Anthropic API | Chamadas OK | Taxa de erro elevada | `LLMIndisponivelError` em sequência |
| Cloud Tasks | Fila normal | Fila crescendo | Tarefas falhando repetidamente |
| Sync BigQuery (cron) | Rodou na janela esperada | Atrasado | Última execução falhou |

---

## Frameworks para Maturidade e Segurança

| Eixo | Framework-base | Adaptação |
|------|-----------------|-----------|
| MLOps | Google MLOps Maturity Model (níveis 0-4) | Mapeado para escala 1-5 |
| DataOps | DataOps Maturity Model (DataKitchen) | Já nativamente 1-5, usado direto |
| LLMOps | Não existe framework consolidado de mercado ainda | Composto próprio do projeto (versionamento de prompt, guardrails, observabilidade de custo, avaliação), documentado explicitamente como não-padrão |
| Segurança | OWASP Top 10 (categorias) + NIST CSF (funções: Identify/Protect/Detect/Respond/Recover) como esqueleto | Nota 1-5 por categoria + nota composta; nenhum dos dois frameworks dá uma nota 1-5 nativamente, então a régua em si é do projeto |

---

## Draft Requirements (para /define)

1. Endpoint `GET /v1/observabilidade/status` — status ao vivo (cache ~60s) dos 6 recursos +
   BigQuery sync, com o mapeamento verde/amarelo/vermelho acima.
2. Instrumentação de token: `ClienteVertexAI.gerar()`/`ClienteAnthropicDireto.gerar()` passam a
   registrar cada chamada real (modelo, tokens entrada/saída, timestamp, node de origem) numa
   tabela nova (`migrations/016_*`).
3. Script de sync de custo de infra (GCP Billing API), mesmo padrão de `sincronizar_bigquery.py`
   — cron diário, grava snapshot por serviço.
4. Scorecard de maturidade/segurança como YAML versionado no repo (ex:
   `.claude/observabilidade/scorecard.yaml`), com schema documentado; endpoint que só lê e serve
   esse arquivo.
5. Nova role IAM para `taxreformai-runtime` (mínimo necessário — a confirmar exatamente qual no
   `/design`: candidatos `roles/monitoring.viewer`, `roles/run.viewer`, `roles/billing.viewer` em
   nível de projeto), em `infra/terraform/main.tf`, seguindo o mesmo padrão de desvio documentado
   já usado por `roles/aiplatform.user`.
6. Frontend: nova área com abas (Diagrama, Sentinela, Maturidade, Segurança, Custo/FinOps), atrás
   da mesma sessão Google + `ALLOWED_EMAILS` que já protege `/simulador`/`/consulta`.
7. Lista curada de achados FinOps (estático, versionado) + alertas por limiar simples sobre os
   dados de custo já coletados.

**Fora de escopo explícito (YAGNI):** tempo real via WebSocket, drill-down de custo por
requisição, tendência histórica de maturidade/segurança na v1, allowlist separada para o painel,
recomendações de FinOps geradas por IA/preditivas.

---

## Next Step

`/define .claude/sdd/features/BRAINSTORM_PAINEL_OBSERVABILIDADE.md`
