# BRAINSTORM: LLM_CLAUDE_API_DIRETA

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_CLAUDE_API_DIRETA |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | Approaches Identified — Ready for Define |

---

## Initial Idea

**Raw Input:** Contorno explícito pedido pelo usuário para o bloqueio real documentado em
`LLM_REAL_VERTEX_AI` (`.claude/sdd/archive/LLM_REAL_VERTEX_AI/SHIPPED_2026-08-03.md`): o projeto
`taxreformai-dev` tem quota zero/mínima do Vertex AI para modelos Claude
(`429 RESOURCE_EXHAUSTED`), bloqueio externo que só o usuário resolve no Console do GCP. Em vez de
esperar, a orientação foi usar a API Claude direta (Anthropic) como caminho alternativo.

**Context Gathered:**
- `orquestracao/llm/cliente.py` já define `ClienteLLM` como `Protocol` (`gerar(modelo, mensagens,
  max_tokens) -> str`) — a abstração certa já existe, `ClienteVertexAI` é só UMA implementação.
- `ClienteVertexAI` usa `AnthropicVertex(project_id, region="global")` da lib `anthropic[vertex]`
  — essa mesma lib TAMBÉM inclui a classe `Anthropic` (API direta), sem exigir dependência nova.
- Modelos hoje usam formato Model Garden do Vertex (`claude-haiku-4-5@20251001`,
  `claude-sonnet-5`) — a API direta usa outro formato de ID (`claude-haiku-4-5-20251001`, sem
  `@`, e `claude-sonnet-5` continua igual).
- `orquestracao/config.py` (`OrquestracaoSettings.from_env()`) e
  `orquestracao/dependencias.py` (`criar_dependencias_reais`) são os dois pontos que precisam
  aprender sobre o provider novo — nenhum nó (`classificador`, `pesquisador_legal`,
  `extrator_regras`, `sintetizador`) precisa mudar, porque todos dependem só do Protocol
  `ClienteLLM`.
- `requirements-api.txt` já tem `anthropic[vertex]` — nenhuma dependência nova a instalar.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `orquestracao/llm/cliente.py` (nova classe), `orquestracao/config.py`, `orquestracao/dependencias.py` | Nenhuma mudança nos 5 nós nem na API HTTP |
| Relevant KB Domains | N/A | Troca de transporte, não de lógica de orquestração |
| IaC Impact | Nenhum recurso Terraform novo — só um GitHub Secret novo (`ANTHROPIC_API_KEY`) e uma env var nova (`LLM_PROVIDER`) no Cloud Run já existente da API | Credencial manual, mesma disciplina já estabelecida (usuário cria, nunca o agente) |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | `ClienteVertexAI` é substituído por completo, ou os dois convivem? | Manter os dois, escolher via env var | Precisa de um mecanismo de seleção explícito (`LLM_PROVIDER`), não uma substituição direta |
| 2 | IDs de modelo da API direta — confirma `claude-haiku-4-5-20251001`/`claude-sonnet-5`? | Sim, esses IDs | Mesmos modelos por nó já usados hoje, só muda o formato do ID |
| 3 | Qual o default quando `LLM_PROVIDER` não for setado? | API Claude direta por padrão | O caminho que funciona HOJE é o default; Vertex vira opt-in explícito para quando a quota for liberada |

**Minimum Questions:** 3 — atendido.

---

## Sample Data Inventory

> Não aplicável — esta feature troca o TRANSPORTE de chamada ao LLM (Vertex AI vs. API direta da
> Anthropic), sem alterar nenhum prompt, extração estruturada ou lógica de negócio dos 5 nós da
> orquestração. Não há amostra nova de grounding a coletar.

---

## Approaches Explored

### Approach A: `ClienteAnthropicDireto` novo, selecionado por env var ⭐ Recomendado

**Description:** Nova classe `ClienteAnthropicDireto` em `orquestracao/llm/cliente.py`,
implementando o mesmo `Protocol` `ClienteLLM` (`gerar(modelo, mensagens, max_tokens) -> str`),
usando `anthropic.Anthropic(api_key=...)`. `OrquestracaoSettings` ganha um campo `llm_provider`
(lido de `LLM_PROVIDER`, default `"direto"`) e um campo opcional `anthropic_api_key`.
`criar_dependencias_reais` escolhe qual classe instanciar com base em `llm_provider`.

**Pros:**
- Zero mudança nos 5 nós da orquestração — todos dependem só do `Protocol`, não da classe
  concreta.
- Zero dependência nova — `anthropic[vertex]` já inclui a classe `Anthropic` da API direta.
- Reversível com uma env var só (`LLM_PROVIDER=vertex`) quando a quota do Vertex for liberada —
  não precisa reverter código.

**Cons:**
- Dois caminhos de código para testar/manter (mitigado: ambos passam pelos mesmos testes do
  Protocol `ClienteLLM`, já existentes).
- IDs de modelo diferentes entre os dois providers — precisa de um mapeamento explícito por
  provider, não pode reusar as constantes `MODELO_HAIKU`/`MODELO_SONNET` como estão hoje (que são
  do formato Vertex).

**Why Recommended:** Resolve o bloqueio real de hoje sem descartar o investimento já feito em
`ClienteVertexAI` — a escolha explícita do usuário foi manter os dois convivendo, não substituir.

---

### Approach B: Failover automático (tenta Vertex, cai para API direta em erro de quota)

**Description:** Um único cliente que tenta `ClienteVertexAI` primeiro e, se a chamada falhar com
`429 RESOURCE_EXHAUSTED`, tenta de novo via API direta automaticamente, sem intervenção humana.

**Pros:**
- Nenhuma env var nova — o sistema se autoajusta.

**Cons:**
- Comportamento implícito: o audit log (`pareceres_audit_log`) não deixaria claro qual provider
  respondeu de fato, quebrando a disciplina de auditabilidade que todo o projeto já segue —
  "nunca falhar em silêncio" vale também para "nunca trocar de fornecedor em silêncio".
- Mais complexo de testar (precisa simular a falha específica do Vertex para exercitar o
  fallback) por um ganho pequeno, já que a escolha explícita via env var resolve o mesmo problema
  com menos risco.

**Why Rejected:** O usuário já escolheu explicitamente "os dois convivem, escolha via env var" —
descarta a premissa de failover automático da Approach B.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — `ClienteAnthropicDireto` novo, selecionado por env var `LLM_PROVIDER` |
| **User Confirmation** | 2026-08-04, confirmado explicitamente após apresentação consolidada |
| **Reasoning** | Resolve o bloqueio real de hoje, preserva o investimento em `ClienteVertexAI`, reversível com uma env var só |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Manter os dois clientes, escolher via `LLM_PROVIDER` | Decisão explícita do usuário — flexibilidade para voltar ao Vertex quando a quota for liberada | Substituir `ClienteVertexAI` por completo |
| 2 | Default de `LLM_PROVIDER` é a API direta (`"direto"`) | O caminho que funciona HOJE deve ser o padrão, sem exigir configuração extra para contornar o bloqueio | Vertex como default, direta como opt-in |
| 3 | IDs de modelo da API direta: `claude-haiku-4-5-20251001` / `claude-sonnet-5` | IDs oficiais confirmados, mesmos modelos por nó já usados hoje | Revisar/trocar o mapeamento de modelo por nó nesta oportunidade |
| 4 | Sem dependência Python nova | `anthropic[vertex]` já inclui a classe `Anthropic` da API direta | Instalar pacote `anthropic` separado |
| 5 | `ANTHROPIC_API_KEY` como GitHub Secret novo, criado manualmente pelo usuário | Mesma disciplina de toda credencial já vista neste projeto — nunca gerada pelo agente | N/A |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Failover automático Vertex → API direta | Usuário já escolheu seleção explícita via env var, não failover implícito | Sim, se o padrão de uso mudar e a troca manual se mostrar operacionalmente custosa |
| Revisão do mapeamento de modelo por nó | Usuário confirmou manter os mesmos modelos (Haiku no classificador, Sonnet nos outros 3) | Sim, é decisão independente desta feature |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Substituir vs. conviver | ✅ | Confirmou "manter os dois, escolher via env var" | Não |
| IDs de modelo da API direta | ✅ | Confirmou os IDs oficiais propostos | Não |
| Default do provider | ✅ | Confirmou "API direta por padrão" | Não |
| Abordagem consolidada (Approach A completa) | ✅ | "Sim, seguir com essa abordagem" | Não |

**Minimum Validations:** 2 — atendido (4 validações).

---

## Suggested Requirements for /define

### Problem Statement (Draft)
`taxreformai-dev` tem quota zero/mínima do Vertex AI para modelos Claude, bloqueando por completo
o caminho `200` de `POST /v1/tax/query` (`429 RESOURCE_EXHAUSTED`) — bloqueio externo, resolvível
só pelo usuário no Console do GCP, sem prazo definido. É preciso um caminho alternativo real, via
API Claude direta, para destravar o produto sem depender da liberação da quota.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Usuário final do endpoint conversacional (`POST /v1/tax/query`) | Hoje recebe 503 sempre que o LLM é chamado, mesmo com todo o resto da orquestração funcionando |
| Time de operação/deploy | Precisa de uma forma simples e reversível de trocar de provider sem reescrever código |

### Success Criteria (Draft)
- [ ] `LLM_PROVIDER=direto` (ou ausente) usa `ClienteAnthropicDireto`, chamando a API Claude real
- [ ] `LLM_PROVIDER=vertex` continua usando `ClienteVertexAI`, sem nenhuma regressão
- [ ] Nenhum nó da orquestração (`classificador`, `pesquisador_legal`, `extrator_regras`,
      `sintetizador`) muda uma linha — só `cliente.py`/`config.py`/`dependencias.py`
- [ ] `POST /v1/tax/query` responde 200 de verdade contra a API Claude direta, verificado contra
      infraestrutura real (mesma disciplina de `LLM_REAL_VERTEX_AI`)

### Constraints Identified
- Zero dependência Python nova
- `ANTHROPIC_API_KEY` criada manualmente pelo usuário no Console da Anthropic, nunca pelo agente
- Sem mudança em nenhum nó de `orquestracao/nos/`

### Out of Scope (Confirmed)
- Failover automático entre providers
- Revisão do mapeamento de modelo por nó
- Remoção de `ClienteVertexAI`/suporte ao Vertex AI

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 4 |
| Duration | ~15min |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_LLM_CLAUDE_API_DIRETA.md`
