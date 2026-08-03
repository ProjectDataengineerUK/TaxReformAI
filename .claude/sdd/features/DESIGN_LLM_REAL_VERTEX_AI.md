# DESIGN: LLM Real via Vertex AI + Nós Reais da Orquestração

> Technical design for implementing LLM_REAL_VERTEX_AI (posições 4+5 fundidas do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_REAL_VERTEX_AI |
| **Date** | 2026-08-03 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_LLM_REAL_VERTEX_AI.md](./DEFINE_LLM_REAL_VERTEX_AI.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────────┐
│  POST /v1/tax/query  (api/routers/query.py)                                │
│                                                                              │
│  Depends(get_dependencias_orquestracao) ──► DependenciasOrquestracao        │
│    ├─ cliente_llm: ClienteLLM        (real: ClienteVertexAI / fake: teste) │
│    ├─ qdrant_indexer: QdrantIndexer  (já existe, PIPELINE_INGESTAO_LEGAL)  │
│    └─ embedder: Embedder             (já existe, FastEmbedHybridEmbedder) │
│                                                                              │
│  executar_consulta(state, deps)                                            │
│     │                                                                       │
│     ▼                                                                      │
│  [1] no_classificador(state, deps)                                         │
│      mascarar_pii(texto_consulta) ──► texto_mascarado                      │
│      cliente_llm.gerar(HAIKU, [texto_mascarado]) ──► intencao (real)       │
│     │                                                                       │
│     ▼                                                                      │
│  [2] no_pesquisador_legal(state, deps)                                     │
│      embedder.embed_consulta(texto_mascarado) ──► EmbeddedQuery            │
│      qdrant_indexer.search_hybrid(...) ──► pontos reais (Qdrant Cloud)     │
│      pontos ──► [Chunk.model_validate(p.payload) for p in pontos]          │
│     │                                                                       │
│     ▼                                                                      │
│  [3] no_extrator_regras(state, deps)                                       │
│      cliente_llm.gerar(SONNET, [texto_mascarado + chunks]) ──► extração   │
│      reconcilia extração vs. valor_base/ano_operacao JÁ estruturados       │
│      (campos estruturados sempre vencem; discrepância vai pro histórico)   │
│     │                                                                       │
│     ▼                                                                      │
│  [4] no_deterministico(state)            ◄── SEM MUDANÇA, sem LLM          │
│      TaxCalculatorEngine.calcular(...)                                     │
│     │                                                                       │
│     ▼                                                                      │
│  [5] no_sintetizador(state, deps)                                          │
│      cliente_llm.gerar(SONNET, [resultado_calculo + chunks]) ──► parecer  │
│      valida que o parecer contém o valor_liquido EXATO (guardrail)        │
│     │                                                                       │
│     ▼                                                                      │
│  RespostaConsulta (contexto_recuperado_ids agora REAL, não mais vazio)     │
└────────────────────────────────────────────────────────────────────────────┘

              Vertex AI (Claude via AnthropicVertex, region="global")
                        ▲
                        │ chamadas reais só via workflow_dispatch
                        │ (nunca local — feedback_cloud_only_execution.md)
                        │
         GitHub Actions: deploy.yml (smoke test estendido)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `orquestracao/llm/cliente.py` | `Protocol ClienteLLM` + `ClienteVertexAI` (real) + `ClienteLLMFake` (teste) | `anthropic[vertex]` (`AnthropicVertex`) |
| `orquestracao/dependencias.py` | Container `DependenciasOrquestracao` (client LLM + Qdrant + embedder) + factories real/fake | Python puro |
| `orquestracao/nos/classificador.py` (modificado) | Classificação real de intenção via Claude Haiku, preservando mascaramento de PII | `anthropic[vertex]` |
| `orquestracao/nos/pesquisador_legal.py` (modificado) | Busca híbrida real no Qdrant, reusando infraestrutura já indexada | `QdrantIndexer.search_hybrid` + `Embedder.embed_consulta` (já existentes) |
| `orquestracao/nos/extrator_regras.py` (modificado) | Extração estruturada real via Claude Sonnet + reconciliação com campos já estruturados | `anthropic[vertex]` |
| `orquestracao/nos/sintetizador.py` (modificado) | Síntese real via Claude Sonnet, com guardrail numérico | `anthropic[vertex]` |
| `orquestracao/nos/deterministico.py` | Sem mudança — já real, Python puro | `motor_calculo/` |
| `api/dependencias_orquestracao.py` | Provider FastAPI (`Depends`), constrói `DependenciasOrquestracao` real a partir de env vars, cacheado | FastAPI |
| `orquestracao/config.py` | `OrquestracaoSettings.from_env()` (projeto GCP, região, Qdrant) | Python puro |
| `infra/terraform/main.tf` (modificado) | Habilita `aiplatform.googleapis.com` + concede `roles/aiplatform.user` a `taxreformai-runtime` | Terraform |
| `.github/workflows/deploy.yml` (modificado) | Smoke test estendido: 1 chamada real a `/v1/tax/query` exercitando os 3 nós com LLM | GitHub Actions |

---

## Key Decisions

### Decision 1: Dependências injetadas via um container único (`DependenciasOrquestracao`), não parâmetros soltos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** 3 dos 4 nós precisam de um client LLM; 1 deles (`pesquisador_legal`) precisa também
de um `Embedder` e um `QdrantIndexer`. Passar cada dependência solta como parâmetro de função
poluiria a assinatura de `executar_consulta` e de cada nó à medida que mais integrações forem
adicionadas.

**Choice:** Um único dataclass `DependenciasOrquestracao(cliente_llm, qdrant_indexer, embedder)`
é construído uma vez (por request, via FastAPI `Depends`, ou uma vez por processo de teste) e
passado para `executar_consulta(state, deps)`, que repassa para cada nó que precisar.

**Rationale:** Mesmo espírito do padrão `Protocol` real/fake já usado em `ingestion/` (`RawStorage`,
`LegalSource`, `Embedder`), mas evita explosão de parâmetros — `no_deterministico` continua
recebendo só `state`, porque genuinamente não precisa de nada além disso.

**Alternatives Rejected:**
1. Cada nó constrói seu próprio client internamente (lendo env vars direto) — rejeitado: torna
   testes impossíveis sem monkeypatch, quebra o padrão real/fake do projeto inteiro.
2. Variável global/singleton de módulo — rejeitado: esconde a dependência, dificulta isolar
   testes paralelos, e o projeto nunca usou esse padrão em nenhuma das 15 features anteriores.

**Consequences:**
- Toda chamada a `executar_consulta` (produção e teste) precisa montar um `DependenciasOrquestracao`
  explícito — sem "modo implícito" que possa vazar uma chamada real para dentro de um teste.
- `orquestracao/grafo.py` (LangGraph, não executável neste sandbox) precisa de um pequeno ajuste
  via `functools.partial` para capturar `deps` em cada nó, já que nós do LangGraph recebem só
  `state` — mudança pequena, só revisão de código (mesma situação já registrada para essa DAG).

---

### Decision 2: Endpoint `global` do Vertex AI, sem fixar região

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** O resto da infraestrutura do projeto vive em `southamerica-east1`. Claude via
Vertex AI Model Garden tem endpoints regionais só em `us-east5`/`europe-west1` — nenhum deles é
`southamerica-east1`.

**Choice:** `ClienteVertexAI` usa `region="global"` no client `AnthropicVertex`, conforme a
recomendação oficial da documentação da Anthropic (`platform.claude.com/docs/en/build-with-claude/
claude-on-vertex-ai`): roteamento dinâmico para máxima disponibilidade, sem premium de preço.

**Rationale:** Elimina a necessidade de escolher entre região do resto da stack e região do
Vertex AI — o Cloud Run em `southamerica-east1` simplesmente faz uma chamada de saída HTTPS para
o endpoint global, do mesmo jeito que já faz para o Qdrant Cloud.

**Alternatives Rejected:**
1. Endpoint regional fixo (`us-east5`) — rejeitado: premium de 10% sobre o preço, sem ganho de
   disponibilidade real para este volume de tráfego, e limitado a Sonnet 4.6 e anteriores (não
   os modelos atuais usados aqui).
2. Multi-region (`us`/`eu`) — rejeitado: também tem premium de 10%, e nenhuma exigência de
   residência de dados foi levantada no `/define`.

**Consequences:**
- Nenhuma variável de região precisa ser adicionada ao Terraform para o Vertex AI — só a
  habilitação da API a nível de projeto.
- Se uma exigência de residência de dados aparecer no futuro, a mudança é só no valor de
  `region` passado ao `AnthropicVertex`, sem mudança de arquitetura.

---

### Decision 3: `extrator_regras` extrai de `texto_consulta` e RECONCILIA com os campos já estruturados, nunca os substitui silenciosamente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** Achado real desta fase de design: `PayloadConsulta` (`api/schemas_query.py`) já
exige `valor_base` e `ano_operacao` como campos ESTRUTURADOS, não texto livre. Isso significa
que, para o payload de hoje, uma "extração" que só copiasse esses dois campos de volta seria
teatro — geraria custo real de token do Vertex AI sem nenhum valor extra sobre o que já está
disponível no request.

**Choice:** `no_extrator_regras` chama Claude Sonnet para extrair `valor_base`/`ano_operacao` a
partir de `texto_mascarado` (o texto livre da consulta) via saída estruturada (JSON). O
resultado da extração é comparado aos campos já estruturados do payload:
- Se coincidirem (ou o texto não mencionar valores explícitos): usa os campos estruturados,
  sem mudança de comportamento observável.
- Se divergirem: os campos estruturados CONTINUAM sendo a fonte de verdade para o cálculo (são
  a entrada explícita e não-ambígua da API), mas a divergência é registrada no histórico
  auditável (`registrar_transicao`), tornando visível que o texto da pergunta e os campos
  numéricos não bateram.

**Rationale:** Mantém a chamada de LLM genuinamente útil (detecta contradição
texto-vs-estrutura) sem introduzir o risco de um valor monetário incorreto entrar no motor de
cálculo por causa de uma extração de LLM ruim — coerente com a disciplina do projeto de nunca
deixar um LLM alterar um número que alimenta `motor_calculo/`.

**Alternatives Rejected:**
1. Usar o valor extraído pelo LLM como fonte de verdade — rejeitado: um LLM pode "ler errado"
   um valor do texto; a API já tem o dado correto e não-ambíguo em campo estruturado, não faz
   sentido preferir uma leitura textual sobre um campo tipado.
2. Não fazer chamada real nenhuma neste nó, mantendo o comportamento atual — rejeitado: contraria
   o Success Criteria do DEFINE ("payload_extraido é montado a partir da extração do LLM, não
   mais copiado diretamente de state") e o objetivo de tornar o nó real.

**Consequences:**
- `payload_extraido` não muda de valor no caminho feliz (mesmo resultado de hoje), mas o
  histórico auditável passa a registrar quando a extração LLM e os campos estruturados
  discordam — informação nova e real, não decorativa.
- Custo de 1 chamada Sonnet por consulta, já contabilizado no orçamento que o usuário aceitou.

---

### Decision 4: `sintetizador` tem um guardrail que rejeita uma síntese que não reproduz o valor líquido exato

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** O parecer final é gerado por um LLM a partir de `resultado_calculo` (que já é
100% determinístico e correto). Um LLM pode arredondar, reformatar ou "ajudar" um número de
forma que ele deixe de bater com o valor que `motor_calculo/` calculou — isso seria uma
regressão grave numa plataforma que promete simulações auditáveis.

**Choice:** Depois de gerar o parecer via Claude Sonnet, `no_sintetizador` verifica que a string
exata de `resultado.valor_liquido` (formatada como `Decimal`) aparece literalmente no texto
retornado. Se não aparecer, levanta `LLMRespostaInconsistenteError` (nova exceção), que se
propaga sem ser capturada — mesmo padrão de `AliquotaNaoDisponivelError` em
`no_deterministico.py`: o grafo interrompe, nunca segue com dado potencialmente incorreto.

**Rationale:** Guardrail barato (comparação de string) que aproveita que o valor já é conhecido
antes da chamada ao LLM — não depende de o LLM "prometer" não errar, verifica de fato.

**Alternatives Rejected:**
1. Confiar cegamente no texto gerado — rejeitado: viola a garantia central do produto
   ("simulações 100% auditáveis").
2. Pós-processar/injetar o número no texto do LLM via regex de substituição — rejeitado: mais
   frágil (o LLM pode formatar o número de formas imprevisíveis) e mascara o problema em vez de
   expô-lo.

**Consequences:**
- Uma falha aqui é rara mas visível (erro 5xx explícito), nunca um número errado servido como
  se fosse certo.
- Nenhuma tentativa automática de retry nesta primeira versão — YAGNI até haver evidência de
  que o guardrail dispara com frequência real.

---

### Decision 5: `taxreformai-runtime` ganha `roles/aiplatform.user` — primeira role de projeto dessa SA

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-03 |

**Context:** `taxreformai-runtime` foi criada deliberadamente sem nenhuma role de projeto
(`SCHEMA_POSTGRESQL`) — só `roles/cloudsql.client` (recurso específico) e leitura de um secret
específico. Chamar Vertex AI exige uma permissão que só existe como role de projeto
(`roles/aiplatform.user` não tem equivalente por recurso específico para modelos de publisher).

**Choice:** Conceder `roles/aiplatform.user` a `taxreformai-runtime` via
`google_project_iam_member`, no mesmo arquivo `infra/terraform/main.tf`, documentando
explicitamente que este é um desvio intencional do princípio "zero role de projeto" — não um
descuido.

**Rationale:** É a SA que já roda o serviço Cloud Run de onde os nós de orquestração executam;
criar uma SA nova só para isso duplicaria a superfície de credenciais sem ganho de isolamento
real (a chamada parte do mesmo processo).

**Alternatives Rejected:**
1. SA dedicada só para Vertex AI — considerada e rejeitada por ora (ver YAGNI do brainstorm);
   pode ser revisitada se um requisito de auditoria futuro exigir.

**Consequences:**
- `taxreformai-runtime` deixa de ser "zero role de projeto" — isso deve ficar documentado no
  `CLAUDE.md` para não ser lido como regressão de segurança não percebida.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `orquestracao/llm/__init__.py` | Create | Marca o pacote novo | @python-developer | None |
| 2 | `orquestracao/llm/cliente.py` | Create | `ClienteLLM` (Protocol), `ClienteVertexAI` (real), `ClienteLLMFake` (teste), `LLMIndisponivelError` | @python-developer | None |
| 3 | `orquestracao/config.py` | Create | `OrquestracaoSettings.from_env()` (projeto GCP, região Vertex AI, Qdrant URL/key/collection) | @python-developer | None |
| 4 | `orquestracao/dependencias.py` | Create | `DependenciasOrquestracao` (dataclass) + `criar_dependencias_reais()` + `criar_dependencias_fake()` | @python-developer | 2, 3 |
| 5 | `orquestracao/nos/classificador.py` | Modify | Classificação real de intenção via Haiku (mantendo `mascarar_pii` antes da chamada) | @python-developer | 2, 4 |
| 6 | `orquestracao/nos/pesquisador_legal.py` | Modify | Busca híbrida real via `Embedder`+`QdrantIndexer`, reconstrói `Chunk` do payload | @python-developer | 4 |
| 7 | `orquestracao/nos/extrator_regras.py` | Modify | Extração real via Sonnet + reconciliação (Decision 3) | @python-developer | 2, 4 |
| 8 | `orquestracao/nos/sintetizador.py` | Modify | Síntese real via Sonnet + guardrail numérico (Decision 4), remove `[FAKE]` | @python-developer | 2, 4 |
| 9 | `orquestracao/executor.py` | Modify | `executar_consulta(state, deps)` — assinatura ganha `deps` | @python-developer | 4, 5, 6, 7, 8 |
| 10 | `orquestracao/grafo.py` | Modify | `construir_grafo(deps)` — nós via `functools.partial(no_x, deps=deps)` (revisão de código só, `langgraph` não instalável) | @python-developer | 9 |
| 11 | `api/dependencias_orquestracao.py` | Create | `get_dependencias_orquestracao()` — provider FastAPI cacheado, monta `DependenciasOrquestracao` real a partir de env vars | @python-developer | 3, 4 |
| 12 | `api/routers/query.py` | Modify | Injeta `deps` via `Depends`, captura `LLMIndisponivelError`/`LLMRespostaInconsistenteError` → 503, popula `contexto_recuperado_ids` real | @python-developer | 8, 11 |
| 13 | `requirements.txt` | Modify | Adiciona `anthropic[vertex]` | @python-developer | None |
| 14 | `requirements-api.txt` | Modify | Adiciona `anthropic[vertex]` (roda dentro do request da API) | @python-developer | None |
| 15 | `infra/terraform/main.tf` | Modify | `google_project_service.aiplatform` + `google_project_iam_member.runtime_aiplatform_user` | @python-developer | None |
| 16 | `.github/workflows/deploy.yml` | Modify | Smoke test estendido: 1 `POST /v1/tax/query` real, valida ausência de `"[FAKE]"` e presença de `contexto_recuperado_ids` não-vazio | @python-developer | 15 |
| 17 | `tests/test_llm_cliente.py` | Create | Testes do `Protocol`/fake/real (mock de rede para o real) | @test-generator | 2 |
| 18 | `tests/test_nos.py` | Modify | Todos os testes existentes passam a injetar `ClienteLLMFake`/fakes de Qdrant/Embedder via `DependenciasOrquestracao` fake | @test-generator | 5, 6, 7, 8 |
| 19 | `tests/test_grafo_integration.py` | Modify | Ajusta para nova assinatura (revisão de código, `langgraph` não instalável) | @test-generator | 10 |
| 20 | `tests/test_api_query_llm_real.py` | Create | Testes E2E do endpoint com deps fake injetadas via `app.dependency_overrides` | @test-generator | 12 |
| 21 | `CLAUDE.md` | Modify | Nova linha da feature na tabela, atualização da seção de agentes (`@genai-architect` de "não conectado" para "conectado"), documentação do desvio de IAM (Decision 5) | @doc-updater | 1-20 |

**Total Files:** 21

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1-16 | Todo o código é Python puro seguindo os padrões já estabelecidos (`Protocol` real/fake, dataclasses, FastAPI `Depends`) |
| @test-generator | 17-20 | Geração de testes pytest seguindo o padrão de fixtures já usado em `tests/test_nos.py` e `tests/test_api_*.py` |
| @security-reviewer | (revisão, não arquivo) | Recomendado no `/define` (Success Criteria) — roda DEPOIS do build, sobre prompt injection e vazamento de PII, antes do `/ship` |
| @doc-updater | 21 | Atualização de `CLAUDE.md` |

---

## Code Patterns

### Pattern 1: `Protocol ClienteLLM` real/fake (mesmo padrão de `RawStorage`/`Embedder`)

```python
# orquestracao/llm/cliente.py
from dataclasses import dataclass, field
from typing import Protocol


class LLMIndisponivelError(Exception):
    """Levantada quando a chamada ao Vertex AI falha (rede, auth, timeout, 5xx)."""


class ClienteLLM(Protocol):
    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str: ...


MODELO_HAIKU = "claude-haiku-4-5@20251001"
MODELO_SONNET = "claude-sonnet-5"


class ClienteVertexAI:
    """Real — chama Claude via Vertex AI (Agent Platform), endpoint global
    (Decision 2: sem premium de preço, sem exigir região específica)."""

    def __init__(self, project_id: str, region: str = "global"):
        from anthropic import AnthropicVertex

        self._client = AnthropicVertex(project_id=project_id, region=region)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        try:
            resposta = self._client.messages.create(
                model=modelo, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            raise LLMIndisponivelError(f"Vertex AI indisponível: {exc}") from exc

        bloco_texto = next((b for b in resposta.content if b.type == "text"), None)
        if bloco_texto is None:
            raise LLMIndisponivelError("Resposta do Vertex AI sem bloco de texto")
        return bloco_texto.text


@dataclass
class ClienteLLMFake:
    """Usado apenas em tests/ — nunca gera custo real. Grava as chamadas para
    permitir assertions de segurança (ex: PII nunca chega mascarado errado)."""

    respostas_por_modelo: dict[str, str] = field(default_factory=dict)
    chamadas: list[dict] = field(default_factory=list)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        self.chamadas.append({"modelo": modelo, "mensagens": mensagens, "max_tokens": max_tokens})
        return self.respostas_por_modelo.get(modelo, '{"resultado": "fake"}')
```

### Pattern 2: `DependenciasOrquestracao` + factories real/fake

```python
# orquestracao/dependencias.py
from dataclasses import dataclass

from ingestion.embedding.hybrid_embedder import Embedder
from ingestion.indexing.qdrant_indexer import QdrantIndexer
from orquestracao.config import OrquestracaoSettings
from orquestracao.llm.cliente import ClienteLLM, ClienteVertexAI


@dataclass
class DependenciasOrquestracao:
    cliente_llm: ClienteLLM
    qdrant_indexer: QdrantIndexer
    embedder: Embedder


def criar_dependencias_reais(settings: OrquestracaoSettings) -> DependenciasOrquestracao:
    from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder

    return DependenciasOrquestracao(
        cliente_llm=ClienteVertexAI(project_id=settings.gcp_project_id),
        qdrant_indexer=QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        ),
        embedder=FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model),
    )
```

### Pattern 3: nó real com PII mascarado ANTES da chamada (`classificador.py`)

```python
# orquestracao/nos/classificador.py (trecho relevante)
from orquestracao.dependencias import DependenciasOrquestracao
from orquestracao.llm.cliente import MODELO_HAIKU

_INTENCOES_VALIDAS = ("SIMULACAO_TRIBUTARIA", "CONSULTA_LEGISLACAO", "OUTRO")


def no_classificador(state: State, deps: DependenciasOrquestracao) -> State:
    texto_mascarado = mascarar_pii(state.texto_consulta)  # SEMPRE antes da chamada ao LLM

    resposta = deps.cliente_llm.gerar(
        modelo=MODELO_HAIKU,
        mensagens=[
            {
                "role": "user",
                "content": (
                    "Classifique a intenção da consulta abaixo em uma destas opções: "
                    f"{', '.join(_INTENCOES_VALIDAS)}. Responda só com a opção escolhida.\n\n"
                    f"Consulta: {texto_mascarado}"
                ),
            }
        ],
    )
    intencao = resposta.strip() if resposta.strip() in _INTENCOES_VALIDAS else "OUTRO"

    state.texto_mascarado = texto_mascarado
    state.intencao = intencao
    state.registrar_transicao(
        no="classificador",
        resumo_input=texto_mascarado[:50],
        resumo_output=f"intencao={intencao}, pii_mascarado={texto_mascarado != state.texto_consulta}",
    )
    return state
```

### Pattern 4: busca híbrida real (`pesquisador_legal.py`)

```python
# orquestracao/nos/pesquisador_legal.py (trecho relevante)
from ingestion.chunking.chunk_models import Chunk
from orquestracao.dependencias import DependenciasOrquestracao


def no_pesquisador_legal(state: State, deps: DependenciasOrquestracao) -> State:
    consulta_embutida = deps.embedder.embed_consulta(state.texto_mascarado or state.texto_consulta)

    resultado = deps.qdrant_indexer.search_hybrid(
        dense_query=consulta_embutida.dense_vector,
        sparse_indices=consulta_embutida.sparse_indices,
        sparse_values=consulta_embutida.sparse_values,
        limit=5,
    )
    chunks = [Chunk.model_validate(ponto.payload) for ponto in resultado.points]

    state.chunks_legais = chunks
    state.registrar_transicao(
        no="pesquisador_legal",
        resumo_input=state.intencao or "",
        resumo_output=f"{len(chunks)} chunk(s) reais recuperados do Qdrant",
    )
    return state
```

### Pattern 5: guardrail numérico no sintetizador

```python
# orquestracao/nos/sintetizador.py (trecho relevante)
class LLMRespostaInconsistenteError(Exception):
    """O parecer gerado pelo LLM não reproduz o valor líquido calculado."""


def no_sintetizador(state: State, deps: DependenciasOrquestracao) -> State:
    resultado = state.resultado_calculo
    assert resultado is not None

    fontes = "\n".join(f"- {c.dispositivo}: {c.texto}" for c in state.chunks_legais)
    resposta = deps.cliente_llm.gerar(
        modelo=MODELO_SONNET,
        mensagens=[{
            "role": "user",
            "content": (
                "Escreva um parecer de simulação tributária em Markdown, citando as fontes "
                "abaixo. Reproduza os valores EXATAMENTE como fornecidos, sem arredondar ou "
                f"reformatar.\n\nValor líquido: R$ {resultado.valor_liquido}\n"
                f"CBS: R$ {resultado.valor_cbs}\nIBS: R$ {resultado.valor_ibs}\n"
                f"IS: R$ {resultado.valor_is}\nFundamentação legal: {resultado.fonte_legal}\n\n"
                f"Fontes recuperadas:\n{fontes}"
            ),
        }],
        max_tokens=1024,
    )

    if str(resultado.valor_liquido) not in resposta:
        raise LLMRespostaInconsistenteError(
            f"Parecer gerado não reproduz o valor líquido exato ({resultado.valor_liquido})"
        )

    state.parecer_final = resposta
    state.registrar_transicao(
        no="sintetizador",
        resumo_input=f"valor_liquido={resultado.valor_liquido}",
        resumo_output="parecer Markdown gerado via Claude Sonnet, citando fontes reais",
    )
    return state
```

---

## Data Flow

```text
1. POST /v1/tax/query chega com {texto_consulta, ano_operacao, valor_base}
   │
   ▼
2. api/routers/query.py injeta DependenciasOrquestracao via Depends (real, cacheada)
   │
   ▼
3. executar_consulta(state, deps) encadeia os 5 nós na ordem fixa
   │  ├─ classificador: PII mascarado → Haiku classifica intenção (1 chamada real)
   │  ├─ pesquisador_legal: embedding da consulta → busca híbrida Qdrant (sem LLM)
   │  ├─ extrator_regras: Sonnet extrai de texto_mascarado → reconcilia com campos
   │  │  estruturados (1 chamada real)
   │  ├─ deterministico: motor_calculo puro, sem mudança
   │  └─ sintetizador: Sonnet gera parecer citando fontes, guardrail valida número
   │     (1 chamada real)
   ▼
4. api/routers/query.py monta RespostaConsulta com contexto_recuperado_ids REAL
   (dispositivo de cada chunk recuperado, não mais lista vazia)
   │
   ▼
5. registrar_com_seguranca grava audit log com contexto_recuperado_ids real
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|------------------|
| Vertex AI (Claude via Agent Platform) | SDK `anthropic[vertex]` (`AnthropicVertex`, REST por baixo) | Application Default Credentials da SA `taxreformai-runtime` (mesma usada para Cloud SQL) |
| Qdrant Cloud | REST via `qdrant-client` (já integrado desde `PIPELINE_INGESTAO_LEGAL`) | `QDRANT_URL`/`QDRANT_API_KEY` (já em GitHub Secrets) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `ClienteLLM` real/fake, `LLMIndisponivelError` | `tests/test_llm_cliente.py` | pytest, mock de `AnthropicVertex` (sem rede real) | Client real testado só com mocks — nunca chamada de rede em teste |
| Unit | Cada nó (classificador/pesquisador_legal/extrator_regras/sintetizador) | `tests/test_nos.py` (modificado) | pytest + `ClienteLLMFake` + fakes de `QdrantIndexer`/`Embedder` | Mesma cobertura de hoje, sem custo real |
| Unit | Guardrail numérico do sintetizador (Decision 4) | `tests/test_nos.py` | pytest — `ClienteLLMFake` configurado para devolver texto SEM o número | Confirma `LLMRespostaInconsistenteError` é levantada |
| Unit | Reconciliação do extrator (Decision 3) | `tests/test_nos.py` | pytest — `ClienteLLMFake` devolvendo extração divergente | Confirma que campos estruturados vencem e a divergência vai pro histórico |
| Integration | Endpoint `/v1/tax/query` com deps fake | `tests/test_api_query_llm_real.py` | pytest + `app.dependency_overrides` | Fluxo completo sem `[FAKE]`, com `contexto_recuperado_ids` populado |
| Security | PII nunca chega em texto plano ao client | `tests/test_nos.py` | pytest — inspeciona `ClienteLLMFake.chamadas` | 0 ocorrências de CPF/CNPJ cru em qualquer `mensagens` registrada |
| E2E real | 1 chamada real por deploy, exercitando os 3 nós com LLM | `.github/workflows/deploy.yml` (smoke test) | `curl` + `workflow_dispatch` | Resposta sem `"[FAKE]"`, `contexto_recuperado_ids` não-vazio |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `LLMIndisponivelError` (rede/auth/timeout do Vertex AI) | Propaga até `api/routers/query.py`, que devolve 503 (mesmo padrão de `db_pool is None` em `API_EMPRESA_SKUS`) | Não — sem retry automático nesta versão (YAGNI até haver evidência de necessidade) |
| `LLMRespostaInconsistenteError` (guardrail numérico do sintetizador) | Propaga até `api/routers/query.py`, devolve 503 — nunca serve um parecer com número potencialmente errado | Não |
| Qdrant indisponível durante `search_hybrid` | Propaga (sem captura silenciosa) — sem chunk real, não há como sintetizar parecer com citação; comportamento é falhar visivelmente, não voltar ao chunk fake antigo | Não |
| Classificação retorna intenção fora do enum esperado | Cai em `"OUTRO"` (fallback explícito, não erro) — a execução do grafo não depende de `intencao` para nenhuma ramificação hoje (fora de escopo) | N/A |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `GCP_PROJECT_ID` | string | (já existe, obrigatório) | Projeto usado tanto pelo `AnthropicVertex` quanto pelo restante do GCP |
| `VERTEX_AI_REGION` | string | `"global"` | Região do endpoint Vertex AI (Decision 2) — não fixar `southamerica-east1` |
| `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_COLLECTION_NAME` | string | (já existem) | Reuso direto da config já usada em `ingestion/config.py` |

---

## Security Considerations

- **PII mascarado antes de qualquer chamada de LLM**: `mascarar_pii()` roda primeiro em
  `no_classificador`; todo texto enviado ao Vertex AI (classificador, extrator, sintetizador)
  usa `state.texto_mascarado`, nunca `state.texto_consulta` cru. Testado explicitamente via
  inspeção de `ClienteLLMFake.chamadas`.
- **Prompt injection via conteúdo recuperado do Qdrant**: os chunks de legislação são conteúdo
  de terceiros (texto oficial, mas fora do controle da aplicação em tempo de execução). Os
  prompts desta feature tratam esse texto explicitamente como DADO a ser citado, nunca como
  instrução — nenhum prompt intercala instrução de sistema dentro do texto do chunk sem
  delimitação clara. Revisão de segurança dedicada (`@security-reviewer`) roda após o build,
  antes do `/ship`, especificamente sobre esse ponto.
- **Guardrail numérico (Decision 4)** é também uma mitigação de segurança, não só de qualidade:
  impede que um prompt injection bem-sucedido no texto de um chunk altere o valor monetário
  reportado ao usuário sem ser detectado.
- **IAM mínimo**: `taxreformai-runtime` ganha só `roles/aiplatform.user` (Decision 5), não
  `roles/aiplatform.admin` nem acesso a outros recursos do projeto.
- **Nenhuma chamada real em CI/local**: `ClienteLLMFake` é o único client usado em
  `tests/`, sem exceção — nenhuma variável de credencial do Vertex AI é lida fora do
  `workflow_dispatch` de deploy.

---

## Observability

| Aspect | Implementation |
|--------|-------------------|
| Logging | Mesma trilha auditável já existente (`state.historico`/`registrar_transicao`) — cada nó real registra o modelo usado e o resultado, sem incluir texto de PII |
| Metrics | Nenhuma métrica nova nesta feature (fora de escopo — YAGNI, sem requisito de observabilidade de custo/latência levantado no `/define`) |
| Tracing | Nenhum novo — segue o padrão de `state.historico` como trilha sequencial já usado desde `ORQUESTRACAO_MULTIAGENTE` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-03 | design-agent | Initial version, extraído de DEFINE_LLM_REAL_VERTEX_AI.md |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_LLM_REAL_VERTEX_AI.md`
