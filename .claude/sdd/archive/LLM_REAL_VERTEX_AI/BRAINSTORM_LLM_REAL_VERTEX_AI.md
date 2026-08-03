# BRAINSTORM: LLM Real via Vertex AI + Nós Reais da Orquestração

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posições 4 e 5 fundidas** da "primeira leva" (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`): por instrução explícita do
> usuário ("ja pode entregar tudo"), esta feature entrega tanto a conexão real com Claude via
> Vertex AI (posição 4) quanto a reescrita dos 4 nós fake da orquestração para usar essa
> conexão de verdade (posição 5, `ORQUESTRACAO_NOS_REAIS`). As duas nunca fariam sentido
> separadas: a posição 4 sozinha não teria nenhum consumidor real até a 5 existir.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_REAL_VERTEX_AI |
| **Date** | 2026-08-03 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 4 (fundida com 5) de 11 da "primeira leva" |

---

## Initial Idea

**Raw Input:** Conectar Claude via Vertex AI de verdade (`anthropic`/`google-cloud-aiplatform`
ausentes hoje) e usar essa conexão para reescrever os 4 nós fake de `orquestracao/nos/` —
`classificador.py`, `pesquisador_legal.py`, `extrator_regras.py`, `sintetizador.py`. O 5º nó,
`deterministico.py`, já é 100% real (chama `motor_calculo/`) e não muda.

**Context Gathered (nesta sessão):**

| Nó | Estado hoje | O que precisa virar real |
|----|-------------|---------------------------|
| `classificador.py` | Mascaramento de PII (CPF/CNPJ, regex) é REAL; `intencao = "SIMULACAO_TRIBUTARIA"` é hardcoded, sem chamada de LLM | Classificar a intenção real via Claude (Haiku, per `contexto.md` seção 3.1) |
| `pesquisador_legal.py` | Retorna um `Chunk` sintético fixo, sem consultar Qdrant | Busca híbrida REAL via `ingestion/indexing/qdrant_indexer.py::QdrantIndexer.search_hybrid(...)` — infraestrutura já existe e já está verificada em produção (6866 pontos, `scripts/verificar_busca_hibrida.py` APROVADA) |
| `extrator_regras.py` | Monta `payload_extraido` direto do `state`, sem LLM | Extração estruturada real via Claude (Sonnet), a partir do texto/chunks recuperados |
| `sintetizador.py` | Monta um Markdown hardcoded a partir de `state.resultado_calculo`, com marcador `"[FAKE]"` no histórico | Síntese real via Claude (Sonnet), citando as fontes recuperadas pelo Pesquisador Legal |
| `deterministico.py` | Já real (chama `motor_calculo/`), Python puro, sem LLM | Sem mudança |

- Nenhum pacote (`anthropic`, `google-cloud-aiplatform`) está em `requirements.txt` ou
  `requirements-api.txt` hoje.
- Nenhum `.tf` em `infra/terraform/` referencia `aiplatform`/`vertex` — a API do Vertex AI
  nunca foi habilitada no projeto `taxreformai-dev`.
- `taxreformai-runtime@taxreformai-dev.iam.gserviceaccount.com` (a service account de runtime
  do Cloud Run) é **deliberadamente sem role de projeto**, só `roles/cloudsql.client` + leitura
  do secret de senha do Postgres — precisa ganhar uma nova permissão explícita para chamar
  Vertex AI.
- `contexto.md` seção 3.1 já define a matriz de modelos recomendada: Classificador → Haiku,
  Pesquisador Legal/Extrator de Regras/Sintetizador → Sonnet.
- **Achado desta sessão, via documentação oficial da Anthropic (`platform.claude.com/docs/en/
  build-with-claude/claude-on-vertex-ai`)**: o SDK correto é `anthropic[vertex]` (client
  `AnthropicVertex`), não `google-cloud-aiplatform` cru. Model IDs no Vertex: `claude-sonnet-5`
  e `claude-haiku-4-5@20251001` (mesmos nomes usados neste próprio ambiente Claude Code).
- **Achado que resolve a dúvida original sobre região**: o endpoint **`global`**
  (`region="global"` no `AnthropicVertex`) é a opção **recomendada pela própria Anthropic** —
  roteamento dinâmico para máxima disponibilidade, **sem premium de preço**, e não exige
  provisionar em nenhuma região específica. Isso elimina o conflito que parecia existir com
  `southamerica-east1` (região padrão de todo o resto do projeto — Cloud Run, Cloud SQL, GCS):
  não é preciso escolher entre `us-east5`/`europe-west1` (endpoints regionais, only para
  Sonnet 4.6 e anteriores) e a região do resto da stack. O client Python simplesmente aponta
  para `region="global"`, chamando `aiplatform.googleapis.com` sem endpoint regional — o Cloud
  Run em `southamerica-east1` faz uma chamada de saída para esse endpoint global, do mesmo jeito
  que já faz para o Qdrant Cloud (também fora de `southamerica-east1`).
- **IAM necessário**: a role padrão do Google Cloud para consumir modelos do Model Garden via
  Vertex AI é `roles/aiplatform.user` (permite `predict`/`rawPredict` nos endpoints de
  publisher). Precisa ser concedida à SA de runtime.
- **Habilitação de API**: `aiplatform.googleapis.com` precisa ser habilitada no projeto via
  Terraform (`google_project_service`), seguindo o padrão já usado para as APIs atualmente
  habilitadas (Cloud Run, Cloud SQL, etc.).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Escopo fundido (4+5) | Instrução explícita do usuário: "ja pode entregar tudo" | `/define` deve tratar como UMA feature, não duas — sem endpoint/feature intermediária "só o client sem nós reais" |
| Custo real por chamada | Usuário já confirmou ciência (build/verificação/deploy vão gerar cobrança real por token) | Nenhuma chamada real deve rodar localmente (ver memória `feedback_cloud_only_execution.md`) — só via GitHub Actions (`workflow_dispatch`), igual a todo o resto da infraestrutura real do projeto |
| Região do Vertex AI | Endpoint `global`, recomendado pela Anthropic, sem premium, sem conflito com `southamerica-east1` | Terraform não precisa fixar região para o Vertex AI — só habilitar a API a nível de projeto |
| SA de runtime | `taxreformai-runtime` hoje sem role de projeto (decisão deliberada da feature `SCHEMA_POSTGRESQL`) | Precisa ganhar `roles/aiplatform.user` — primeira vez que essa SA ganha uma permissão de projeto, não só recursos específicos (Cloud SQL client, secret) |
| Busca híbrida do Pesquisador Legal | Infraestrutura já existe e já está verificada (`QdrantIndexer.search_hybrid`, `scripts/verificar_busca_hibrida.py`) | Wiring é reuso, não infraestrutura nova — reduz risco desta feature em relação ao Vertex AI, que É infraestrutura nova |
| Onde o cliente Vertex AI mora | `orquestracao/executor.py` já existe como orquestrador sequencial (sem depender de `langgraph`), chamado por `POST /v1/tax/query` | O client real deve ser injetável/testável com fake, mesmo padrão `Protocol` já usado em `RawStorage`/`LegalSource`/`Embedder` |
| Prompt injection / segurança | Nós recebem texto de usuário (consulta conversacional) e de fontes externas (chunks recuperados do Qdrant) que vão para dentro de prompts | Superfície nova de segurança que o projeto não teve até agora — primeira feature onde entrada de usuário e conteúdo de terceiros (legislação) se misturam dentro de um prompt de LLM real |
| Relevant KB Domains | genai-architect, python-developer, security-reviewer | Revisão de segurança dedicada é candidata forte, dado o histórico do projeto (CLAUDE.md já recomenda `@security-reviewer` para dados sensíveis, e o próprio `classificador.py` já mascara PII antes de qualquer chamada) |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Prosseguir com `/brainstorm` dado o perfil de custo/infra único desta feature? | "Sim, seguir com /brainstorm" | Autorizado a continuar |
| 2 | Escopo: só o client Vertex AI (posição 4), deferindo os nós (posição 5)? | Rejeitado — usuário instruiu: **"ja pode entregar tudo"** | Escopo fundido: client + 4 nós reais nesta única feature |
| 3 | Vertex AI suporta a região padrão do projeto (`southamerica-east1`)? | Verificado nesta sessão via documentação oficial: não é necessário decidir região — o endpoint `global` (recomendado, sem premium) resolve isso sem exigir escolha entre regiões | Remove o que parecia ser um trade-off de arquitetura real; Terraform só habilita a API, não fixa região |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Matriz de modelos por agente | `contexto.md` seção 3.1 | 5 agentes (1 sem LLM) | Já validada, não precisa nova pesquisa |
| Coleção Qdrant já indexada | `legislacao_tributaria` (Qdrant Cloud) | 6866 pontos, 4 fontes | Já verificada E2E (`PIPELINE_INGESTAO_LEGAL`) — reuso direto pelo Pesquisador Legal |
| Documentação oficial Vertex AI | `platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai` | 1 página, lida integralmente nesta sessão | Model IDs, SDK, IAM, exemplo de código todos confirmados |
| Fixture de teste (prompts/respostas fake) | Nenhuma ainda | 0 | A definir no `/design` — mesmo padrão `Protocol` real/fake já usado no projeto todo |

---

## Approaches Explored

### Approach A: Client Vertex AI único e injetável, consumido pelos 4 nós via `Protocol` ⭐ Recomendada

**What:** Um módulo novo (`orquestracao/llm/vertex_client.py` ou similar) expõe um `Protocol`
(`ClienteLLM`) com um método mínimo (`gerar(...)`), implementado por `ClienteVertexAI` (real,
usa `AnthropicVertex`) e por um fake determinístico para testes — mesmo padrão de
`RawStorage`/`LegalSource`/`Embedder` já usado em `ingestion/`. Cada nó recebe o client injetado
(mesmo padrão de `parser` injetável em `pipeline.py`) e escolhe o modelo (Haiku/Sonnet) conforme
a matriz do `contexto.md`. `pesquisador_legal.py` ganha uma dependência adicional injetável para
`QdrantIndexer.search_hybrid`.

**Pros:**
- Reaproveita o padrão `Protocol` real/fake já validado em 3+ features anteriores — zero
  surpresa arquitetural
- Testável sem custo real (fake determinístico) — mantém a suíte de testes local gratuita,
  igual a todo o resto do projeto
- Um único ponto de configuração de credenciais/projeto/região para os 4 nós

**Cons:**
- Precisa de disciplina para não deixar nenhum teste/CI chamar o client real sem querer (mesmo
  cuidado já exercido com Qdrant/GCS reais)

**Why Recommended:** É a única abordagem consistente com o histórico do projeto inteiro: toda
integração externa (GCS, Qdrant, Cloud SQL) já segue exatamente este padrão.

### Approach B: Cada nó importa `AnthropicVertex` diretamente, sem abstração

**What:** Chamar o SDK diretamente dentro de cada nó, sem `Protocol` nem injeção.

**Pros:**
- Menos código no primeiro momento

**Cons:**
- Quebra o padrão estabelecido do projeto inteiro
- Testes unitários dos nós passariam a exigir mock manual do SDK em vez de um fake limpo —
  mais frágil, mais acoplado à biblioteca externa
- Dificulta trocar de modelo/região no futuro (cada nó teria a configuração espalhada)

**Rejected:** Regressão de padrão sem ganho real.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — client `Protocol` injetável, real via `AnthropicVertex`, fake para testes |
| **User Confirmation** | Escopo fundido confirmado ("ja pode entregar tudo"); abordagem técnica segue o padrão já estabelecido, não precisa de nova confirmação explícita |
| **Reasoning** | Consistência total com o histórico do projeto + menor risco de custo acidental em CI/local |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Fundir posições 4 e 5 em uma única feature | Instrução explícita do usuário | Entregar só o client (posição 4) e deferir os nós — rejeitado pelo usuário |
| 2 | Usar endpoint `region="global"` do Vertex AI, não um endpoint regional fixo | Recomendação oficial da Anthropic, sem premium de preço, elimina conflito de região com `southamerica-east1` | Provisionar em `us-east5`/`europe-west1` — rejeitado, adicionaria complexidade de região sem benefício, já que o global é o caminho recomendado |
| 3 | SDK `anthropic[vertex]` (client `AnthropicVertex`), não `google-cloud-aiplatform` cru | É o SDK oficial da Anthropic para Vertex AI, API quase idêntica à Messages API que o resto do ecossistema Claude já usa | `google-cloud-aiplatform` genérico — rejeitado, exigiria reimplementar o protocolo de mensagens manualmente |
| 4 | Nenhuma chamada real ao Vertex AI roda localmente — só via `workflow_dispatch` | Mesma política já registrada em memória (`feedback_cloud_only_execution.md`) e seguida por toda infraestrutura real do projeto (Qdrant, GCS, Cloud SQL) | Permitir chamadas reais em dev local — rejeitado, risco de custo não rastreado |
| 5 | `taxreformai-runtime` ganha `roles/aiplatform.user` via Terraform | É a SA que já roda o Cloud Run onde os nós de orquestração executam | Criar uma SA nova dedicada a LLM — considerar no `/design`, mas reuso é mais simples e seguro dado que a chamada já parte do mesmo serviço |
| 6 | `pesquisador_legal.py` reusa `QdrantIndexer.search_hybrid` diretamente, sem reingestão nem nova infraestrutura | Coleção já populada e verificada (6866 pontos) | Reingerir para "garantir dados frescos" — rejeitado, fora de escopo e sem necessidade demonstrada |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Suporte a múltiplos provedores de LLM (Anthropic direto, Bedrock, etc.) | `contexto.md` já fixa Vertex AI como a integração do blueprint; nenhum requisito pede portabilidade de provedor | Sim, se o produto precisar — o `Protocol` já deixa essa porta aberta sem esforço extra |
| Endpoint regional dedicado (`us-east5`) para reduzir latência | Endpoint `global` é a recomendação oficial, sem dado real de latência que justifique a complexidade adicional agora | Sim, se medição real em produção mostrar necessidade |
| Cache de respostas de LLM (evitar rechamar para a mesma consulta) | Nenhum requisito de performance/custo levantou essa necessidade ainda; adicionaria complexidade de invalidação sem dado que justifique | Sim, como otimização futura se o volume de chamadas repetidas for medido |
| SA dedicada só para chamadas de LLM (separada da SA de runtime da API) | Reuso da SA de runtime já existente é mais simples e a chamada parte do mesmo serviço Cloud Run | Sim, se um requisito de auditoria/isolamento futuro exigir |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Continuar com `/brainstorm` dado o perfil de custo | ✅ | Confirmado | Mantido |
| Escopo: client-only vs. fundido com nós reais | ✅ | Corrigido pelo usuário para "fundido" | Escopo ajustado para incluir posição 5 |
| Achado de região do Vertex AI (`global` resolve o conflito) | ✅ (nesta mensagem) | Pendente de reação do usuário — segue como achado documentado, decisão tomada com base em fonte oficial | Registrado como Key Decision 2 |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
4 dos 5 nós da orquestração multi-agente (`classificador`, `pesquisador_legal`,
`extrator_regras`, `sintetizador`) são fake — não chamam nenhum LLM real nem fazem busca
híbrida real no Qdrant, apesar da infraestrutura de busca já existir e estar verificada em
produção. Isso impede que `POST /v1/tax/query` (o endpoint conversacional) entregue respostas
reais fundamentadas em legislação.

### Success Criteria (Draft)
- [ ] `anthropic[vertex]` adicionado a `requirements.txt`/`requirements-api.txt`
- [ ] Terraform habilita `aiplatform.googleapis.com` no projeto `taxreformai-dev`
- [ ] Terraform concede `roles/aiplatform.user` à SA `taxreformai-runtime`
- [ ] Client `Protocol` real/fake (`ClienteLLM` ou nome equivalente) criado, seguindo o padrão
      já usado em `RawStorage`/`LegalSource`/`Embedder`
- [ ] `classificador.py` classifica intenção real via Claude Haiku (mantendo o mascaramento de
      PII já real, que roda ANTES de qualquer chamada de LLM)
- [ ] `pesquisador_legal.py` chama `QdrantIndexer.search_hybrid` de verdade, sem reingestão
- [ ] `extrator_regras.py` extrai estrutura real via Claude Sonnet
- [ ] `sintetizador.py` sintetiza resposta real via Claude Sonnet, citando fontes recuperadas —
      remove o marcador `"[FAKE]"` do histórico auditável
- [ ] Nenhuma chamada real ao Vertex AI acontece em teste local/CI — só via `workflow_dispatch`
      gated, mesmo padrão de `ingestao.yml`/`migrar_banco.yml`/`deploy.yml`
- [ ] Verificação real end-to-end de pelo menos uma chamada por nó, via workflow (não só teste
      com fake)
- [ ] Revisão de segurança dedicada (prompt injection via conteúdo recuperado do Qdrant e via
      consulta do usuário) antes do `/ship`

### Constraints Identified
- Custo real por token em cada chamada de verificação/deploy — usuário já ciente e autorizou
- Endpoint `global` do Vertex AI (sem premium, recomendado pela Anthropic) — não fixar região
- SA de runtime ganha permissão de projeto pela primeira vez (`aiplatform.user`) — desvio
  deliberado do princípio "zero role de projeto" estabelecido em `SCHEMA_POSTGRESQL`, mas
  necessário e escopado (só essa role, não mais)

### Out of Scope (Confirmed)
- Suporte a múltiplos provedores de LLM
- Endpoint regional dedicado / otimização de latência
- Cache de respostas de LLM
- SA dedicada separada da SA de runtime
- Qualquer mudança em `motor_calculo/` ou `deterministico.py` (já real, sem LLM, por desenho)
- Reingestão do Qdrant (dados já existentes e verificados)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 3 de 2 |
| Duration | Sessão contínua (retomada após compactação de contexto) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_LLM_REAL_VERTEX_AI.md`
