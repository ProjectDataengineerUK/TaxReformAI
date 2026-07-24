# BRAINSTORM: Orquestração Multi-Agente (LangGraph)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ORQUESTRACAO_MULTIAGENTE |
| **Date** | 2026-07-23 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Depois de shipar `MOTOR_DETERMINISTICO_CALCULO` e ter `PIPELINE_INGESTAO_LEGAL` com build completo (execução real ainda pendente de credenciais), o usuário confirmou (consultando `CLAUDE.md`) que o próximo componente do blueprint é a orquestração multi-agente (seção 3 do `contexto.md`) — o que conecta `ingestion/` e `motor_calculo/` nos 5 agentes especialistas descritos: Classificador, Pesquisador Legal, Extrator de Regras, Determinístico, Sintetizador.

**Context Gathered:**
- `contexto.md` (seção 3) descreve um pipeline **fixo e sequencial**: Classificador → Pesquisador Legal → Extrator de Regras → Determinístico → Sintetizador, sem menção a delegação autônoma entre agentes.
- `motor_calculo/` (feature já shipada) já implementa o Agente Determinístico de verdade — pode ser integrado diretamente, sem fake.
- `ingestion/` (build completo, não shipado) seria a base do Agente Pesquisador Legal, mas depende de Qdrant Cloud real — ainda não disponível.
- Não há, ainda, acesso configurado ao Claude via Vertex AI/API para este projeto.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo diretório `orquestracao/` na raiz, paralelo a `ingestion/` e `motor_calculo/` | Terceiro componente independente do sistema |
| Relevant KB Domains | genai-architect (orquestração multi-agente, LangGraph), python-developer | Padrões a consultar no /design |
| IaC Impact | Nenhum nesta fase — tudo roda com fakes, sem infraestrutura nova | Motor_calculo já é real; ingestion/Qdrant continuam fake nesta feature |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Já existe acesso configurado ao Claude via Vertex AI/API para este projeto? | Não — a orquestração deve rodar com LLMs **simulados (fakes)** nesta feature | O grafo pode ser testado sem custo real de API, mas nenhum nó de LLM prova comportamento real ainda — fica para uma feature futura |
| 2 | LangGraph ou CrewAI (o blueprint cita os dois)? | Delegado ao Claude para decidir com base no encaixe técnico | Escolhido **LangGraph** — o pipeline do blueprint é fixo/sequencial, sem agentes decidindo autonomamente a quem delegar; LangGraph dá estado explícito por nó, o que serve diretamente à exigência de auditabilidade |
| 3 | Existe exemplo real de pergunta de usuário para grounding do Classificador/Extrator? | Não — usar exemplo sintético baseado no payload da seção 8 do blueprint (`/v1/tax/simulate`) | Casos de teste construídos, não extraídos de dado real |
| 4 | Anonimização de PII deve ser real ou fake, já que o resto do Classificador é fake? | **Real** — é lógica determinística (regex de CPF/CNPJ), não depende de LLM | Separa as duas responsabilidades do nó Classificador: mascaramento de PII (real) e classificação de intenção (fake) |
| 5 | Faz sentido usar Kafka na orquestração? | Não | Padrão é requisição-resposta (grafo roda e retorna numa única invocação), sem necessidade de fila entre consumidores independentes; o caso de uso de fila assíncrona (upload de SKUs em lote) já é Celery+Redis no blueprint — feature diferente desta |

**Minimum Questions:** 3 ✅ (5 perguntas, incluindo validações)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | Nenhum exemplo real de consulta de usuário disponível | 0 | Será construído um exemplo sintético baseado no payload da seção 8 do blueprint |
| Output examples | Payload de resposta de `/v1/tax/simulate` (seção 8 do blueprint) | 1 | Referência de formato para o Sintetizador (fake) e para o `ResultadoCalculo` do Determinístico (real) |
| Related code | `motor_calculo/engine.py` (real), `ingestion/pipeline.py` (fake de storage/embedder já estabelecido) | 2 | Padrões de fake/Protocol já usados nas duas features anteriores serão reaproveitados |

**Como as fontes serão usadas:**

- O payload da seção 8 vira a base do exemplo sintético de consulta ponta a ponta usado nos testes de integração do grafo
- Os padrões de `Protocol` + fake já estabelecidos (`RawStorage`, `LegalSource`, `TabelaAliquotas`) serão reaproveitados para os nós de LLM (Classificador/Pesquisador/Extrator/Sintetizador)

---

## Approaches Explored

### Approach A: Grafo LangGraph completo (5 nós), fakes de LLM/Qdrant, PII real, integração real com `motor_calculo` ⭐ Recomendada

**Description:** Construir os 5 nós do pipeline como funções `State → State` do LangGraph. Classificador (PII real via regex + intent fake), Pesquisador Legal (fake, simula retorno de chunks do Qdrant), Extrator de Regras (fake, simula payload JSON), Determinístico (real — chama `motor_calculo.engine.TaxCalculatorEngine`), Sintetizador (fake, monta um parecer a partir de template).

**Pros:**
- Custo zero de API — todos os LLMs são fakes, então construir os 5 nós de uma vez custa o mesmo que construir 2
- Prova a lógica de estado/roteamento do grafo inteiro, ponta a ponta, incluindo uma integração real (Determinístico)
- Reaproveita o padrão `Protocol`/fake já validado nas duas features anteriores

**Cons:**
- Nenhum nó de LLM prova comportamento real ainda — precisa de uma feature futura quando houver acesso a Claude/Vertex AI
- Pesquisador Legal fake não reflete a complexidade real do Qdrant (filtros de vigência, busca híbrida) — só simula a forma do retorno

**Why Recommended:** Como os LLMs já seriam fakes de qualquer forma (sem acesso configurado), não há razão para construir só um subconjunto do grafo — o custo marginal dos outros 3 nós fake é desprezível, e um grafo completo prova a forma do sistema de ponta a ponta pela primeira vez no projeto.

---

### Approach B: CrewAI com agentes delegando entre si

**Description:** Implementar os 5 agentes como uma "Crew" do CrewAI, com papéis e tarefas, delegando trabalho entre si conforme necessário.

**Pros:**
- Framework também citado no blueprint
- Abstração de "papel" pode ser mais legível para stakeholders não-técnicos

**Cons:**
- O pipeline do blueprint é fixo e sequencial — não há necessidade de um agente decidir autonomamente a quem delegar, que é o problema que o CrewAI resolve
- Estado explícito por nó (necessário para auditabilidade) é mais natural no modelo de grafo do LangGraph do que no modelo de delegação do CrewAI

---

### Approach C: Subconjunto de nós (ex: só Classificador + Determinístico)

**Description:** Construir só 2 dos 5 nós nesta feature, deixando Pesquisador/Extrator/Sintetizador para depois.

**Pros:**
- Escopo menor

**Cons:**
- Como todos os nós de LLM são fakes de qualquer forma, não há economia real de esforço em cortar nós — o custo é de poucas linhas de código fake por nó
- Não prova a forma completa do grafo, que é justamente o que esta feature deveria validar

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — Grafo LangGraph completo, fakes de LLM/Qdrant, PII real, integração real com `motor_calculo` |
| **User Confirmation** | 2026-07-23 |
| **Reasoning** | Custo marginal desprezível de incluir todos os 5 nós, dado que os LLMs já seriam fakes; prova a forma completa do sistema pela primeira vez no projeto |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | LangGraph em vez de CrewAI | Pipeline fixo/sequencial do blueprint não precisa de delegação autônoma; estado explícito por nó serve diretamente à auditabilidade | CrewAI — resolveria um problema (delegação autônoma) que este pipeline não tem |
| 2 | Todos os 5 nós construídos nesta feature, mesmo com LLMs fakes | Custo marginal desprezível quando o LLM já é fake — não há razão para cortar escopo | Approach C (subconjunto) — rejeitada, "economia de escopo" seria ilusória |
| 3 | Anonimização de PII real (regex), separada da classificação de intenção (fake) | Mascarar CPF/CNPJ é lógica determinística, não depende de LLM — não faz sentido deixar de implementar algo que já dá pra fazer certo | Manter todo o nó Classificador fake, incluindo PII — rejeitada, seria abrir mão de uma parte real e simples só porque está no mesmo nó de uma parte fake |
| 4 | Kafka descartado do escopo | Orquestração é requisição-resposta (uma invocação do grafo por consulta), sem necessidade de fila entre consumidores independentes | Introduzir Kafka na orquestração — rejeitado; o caso de uso real de fila assíncrona (upload de SKUs em lote) já é Celery+Redis no blueprint, e é uma feature diferente desta |
| 5 | Nó Determinístico integra de verdade com `motor_calculo.engine.TaxCalculatorEngine` | É a única dependência desta feature que já é real e funciona — não faz sentido fakear algo que já existe | Fakear também o Determinístico por "consistência" com os demais nós — rejeitada, jogaria fora uma integração real já disponível |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Retry/recuperação de erro dentro do grafo (ex: reinvocar o Extrator se o JSON vier inválido) | Sem LLM real, não há como um retry mudar o resultado de um nó fake — não testa nada de verdade ainda | Sim — quando os nós de LLM forem reais |
| Streaming de resposta | Não há UI consumindo a resposta ainda; adicionar streaming antes de ter um consumidor real é especulativo | Sim |
| Checkpointing de estado do grafo entre sessões | Sem persistência configurada (Postgres/Redis) ainda nesta feature | Sim — quando o schema de audit log (seção 7 do blueprint) for implementado |
| Human-in-the-loop (interrupção do grafo para revisão humana) | Nenhum requisito do blueprint pede isso nesta fase | Sim, se necessário depois |
| Kafka para comunicação entre agentes | Resolve um problema (fila assíncrona entre consumidores independentes) que este pipeline requisição-resposta não tem | Não para esta orquestração — Celery+Redis já cobre o caso de uso real (upload em lote) numa feature futura separada |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Escolha de framework (LangGraph vs. CrewAI) | ✅ | Usuário delegou a decisão ao Claude, que escolheu LangGraph com justificativa técnica | Não — aceito como apresentado |
| Escopo (PII real + Kafka descartado) | ✅ | Usuário questionou os dois pontos; após explicação, confirmou ("sim") | Sim — PII passou de "fake" (corte original) para "real", com justificativa registrada |

**Minimum Validations:** 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O sistema precisa de um grafo de orquestração (LangGraph) que conecte os 5 agentes especialistas do blueprint numa pipeline fixa e auditável — hoje, `ingestion/` e `motor_calculo/` existem como componentes isolados, sem nada que os invoque em conjunto para responder a uma consulta de usuário.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Sistema TaxReform AI (consumidor interno futuro, ex: API `/v1/tax/simulate`) | Precisa de um ponto de entrada único que rode os 5 agentes em ordem e produza um resultado auditável |
| CFO / Head de Tax (usuário final, indireto) | Eventualmente vai consumir o parecer produzido pelo Sintetizador — nesta fase, o parecer ainda é fake, mas a estrutura de dados deve já refletir o formato real |

### Success Criteria (Draft)
- [ ] O grafo executa os 5 nós em ordem (Classificador → Pesquisador Legal → Extrator de Regras → Determinístico → Sintetizador) para uma consulta de teste sintética
- [ ] O nó Classificador mascara CPF/CNPJ de verdade (regex), mesmo com a classificação de intenção fake
- [ ] O nó Determinístico produz um `ResultadoCalculo` real via `motor_calculo.engine.TaxCalculatorEngine`, não um fake
- [ ] O estado final do grafo contém o histórico de todas as transições (auditável), incluindo qual fonte legal foi usada no cálculo

### Constraints Identified
- Sem acesso a Claude/Vertex AI configurado — Classificador (intent), Pesquisador Legal, Extrator e Sintetizador ficam fakes nesta feature
- Sem Qdrant Cloud real disponível — Pesquisador Legal simula o formato de retorno, não busca de verdade
- Motor Determinístico é a única integração real desta feature

### Out of Scope (Confirmed)
- Chamadas reais a Claude/Vertex AI para qualquer nó — feature futura, quando houver credenciais
- Busca real no Qdrant — depende do `/ship` de `PIPELINE_INGESTAO_LEGAL` (credenciais GCP/Qdrant pendentes)
- Retry/recuperação de erro, streaming, checkpointing, human-in-the-loop
- Kafka ou qualquer fila assíncrona — não é o padrão de acesso desta feature
- Integração com uma API HTTP (`/v1/tax/simulate`) — o grafo fica invocável como função Python nesta feature, sem endpoint exposto

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |
| Duration | 1 sessão de diálogo |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ORQUESTRACAO_MULTIAGENTE.md`
