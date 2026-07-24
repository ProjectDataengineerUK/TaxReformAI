# DESIGN: Orquestração Multi-Agente (LangGraph)

> Technical design for implementing o grafo LangGraph que conecta os 5 agentes especialistas numa pipeline fixa e auditável, com LLMs simulados e integração real com o motor de cálculo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ORQUESTRACAO_MULTIAGENTE |
| **Date** | 2026-07-23 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ORQUESTRACAO_MULTIAGENTE.md](./DEFINE_ORQUESTRACAO_MULTIAGENTE.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│              ORQUESTRAÇÃO MULTI-AGENTE (LangGraph) — MVP                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  [State inicial: texto_consulta, ano_operacao, valor_base]               │
│        │  nos/classificador.py                                          │
│        ▼                                                                │
│  [Nó 1: Classificador] — PII real (regex) + intenção fake               │
│        │  State.texto_mascarado, State.intencao                        │
│        ▼                                                                │
│  [Nó 2: Pesquisador Legal] — fake, Chunks reais (schema de ingestion/)  │
│        │  State.chunks_legais                                          │
│        ▼                                                                │
│  [Nó 3: Extrator de Regras] — fake, payload simulado                    │
│        │  State.payload_extraido                                       │
│        ▼                                                                │
│  [Nó 4: Determinístico] — REAL, chama motor_calculo.TaxCalculatorEngine │
│        │  State.resultado_calculo  (ou AliquotaNaoDisponivelError)     │
│        ▼                                                                │
│  [Nó 5: Sintetizador] — fake, parecer via template                     │
│        │  State.parecer_final                                          │
│        ▼                                                                │
│  [State final: historico de todas as transições, auditável]            │
│                                                                           │
│  grafo.py: wiring via langgraph.graph.StateGraph (import lazy)         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `State` + `TransicaoAuditavel` | Estado que trafega pelo grafo, com histórico auditável embutido | `pydantic.BaseModel` |
| Nó Classificador | Mascara PII (CPF/CNPJ) de verdade via regex; classifica intenção (fake) | Python puro + `re` |
| Nó Pesquisador Legal | Fake — retorna `Chunk`s simulados no schema real de `ingestion/chunking/chunk_models.py` | Python puro |
| Nó Extrator de Regras | Fake — monta payload simulado no formato esperado pelo `TaxCalculatorEngine` | Python puro |
| Nó Determinístico | **Real** — chama `motor_calculo.engine.TaxCalculatorEngine` | Reaproveita `motor_calculo/` (feature já shipada) |
| Nó Sintetizador | Fake — monta parecer Markdown a partir de template | Python puro |
| `grafo.py` | Wiring dos 5 nós via `langgraph.graph.StateGraph` | `langgraph` (import isolado/lazy) |

---

## Key Decisions

### Decision 1: Nós como funções puras `State → State`; `langgraph` isolado numa camada fina de wiring

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** `langgraph` não está instalável neste sandbox (mesmo bloqueio `externally-managed-environment` já enfrentado na feature de ingestão com `qdrant-client`/`fastembed`/`google-cloud-storage`/`typer`). O DEFINE exige que a lógica de cada nó seja testável.

**Choice:** Cada nó é uma função pura `def nome_no(state: State) -> State`, testável diretamente sem precisar de `langgraph` instalado. Um módulo separado (`orquestracao/grafo.py`) importa `langgraph` de forma lazy (dentro de uma função, não no topo do módulo) e faz apenas o *wiring* (`StateGraph(...).add_node(...).add_edge(...)`), sem nenhuma lógica de negócio própria.

**Rationale:** Consistente com o padrão já usado em `ingestion/pipeline.py` (`_build_cli()` isolando o `typer` não instalável) — separa "lógica de negócio testável" de "biblioteca de infraestrutura indisponível no sandbox atual".

**Alternatives Rejected:**
1. Bloquear a feature até `langgraph` estar instalável — rejeitado; a lógica de negócio dos 5 nós não depende do framework de wiring escolhido.
2. Reimplementar um mini-grafo próprio em vez de usar `langgraph` — rejeitado; contradiria a decisão já tomada no brainstorm.

**Consequences:**
- `grafo.py` (a integração real com `langgraph`) não é exercitada pelos testes automatizados neste sandbox — vira um item do Build Report, igual à feature de ingestão
- Toda a lógica de negócio (os 5 nós) é 100% testável sem depender de nenhuma biblioteca não instalável

---

### Decision 2: `State` como Pydantic `BaseModel` com histórico de transições embutido

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** O DEFINE exige que "o estado final do grafo contém histórico auditável de todas as transições".

**Choice:** `State` é um `BaseModel` com os campos de domínio (`texto_consulta`, `texto_mascarado`, `intencao`, `chunks_legais`, `payload_extraido`, `resultado_calculo`, `parecer_final`) mais um campo `historico: list[TransicaoAuditavel]`. Cada nó, ao terminar, adiciona uma entrada com nome do nó, resumo do input, resumo do output e timestamp.

**Rationale:** Auditabilidade é a proposta de valor central do produto (`contexto.md`, seção 1.1) — precisa nascer na estrutura de dados do grafo, não ser adicionada depois por outro componente.

**Alternatives Rejected:**
1. Logging separado (via `logging`) em vez de campo estruturado no estado — rejeitado; um log solto não viaja garantidamente com o resultado que um consumidor futuro (ex: API) receberia.

**Consequences:**
- Cada nó precisa adicionar sua própria entrada ao histórico (pequena repetição de código, mitigada por um helper)
- O estado final é auto-suficiente para auditoria, sem depender de correlacionar logs externos

---

### Decision 3: PII mascarada via regex determinístico, não fake

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** O brainstorm decidiu que a máscara de PII (CPF/CNPJ) deve ser real, mesmo com o resto do nó Classificador fake — é lógica determinística que não depende de LLM.

**Choice:** Uma função `mascarar_pii(texto: str) -> str` usa regex para CPF (`\d{3}\.?\d{3}\.?\d{3}-?\d{2}`) e CNPJ (`\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}`), substituindo ocorrências por `[CPF_MASCARADO]`/`[CNPJ_MASCARADO]`.

**Rationale:** Não faz sentido adiar algo que já pode ser implementado corretamente só porque está no mesmo nó de uma parte que depende de LLM.

**Alternatives Rejected:**
1. Máscara "fake" (retornar o texto sem alteração) — rejeitada explicitamente no brainstorm.

**Consequences:**
- Regex simples não cobre 100% dos formatos possíveis de CPF/CNPJ em texto livre (ex: espaçamento irregular, erros de digitação) — limitação conhecida, aceitável para o MVP
- O histórico auditável (`TransicaoAuditavel`) deve armazenar apenas o texto já mascarado, nunca o original com PII

---

### Decision 4: Fakes com schema fiel, reaproveitando os modelos Pydantic já existentes

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-23 |

**Context:** Pesquisador Legal, Extrator de Regras e Sintetizador são fakes, mas o Goal SHOULD do DEFINE pede que respeitem o schema real de dado esperado.

**Choice:** O fake do Pesquisador Legal retorna instâncias reais de `ingestion.chunking.chunk_models.Chunk` (já validado na feature de ingestão), populadas com dados sintéticos. O fake do Extrator retorna os campos que `TaxCalculatorEngine.calcular()` espera (`valor_base: Decimal`, `ano_operacao: int`). O Sintetizador usa um template Markdown simples referenciando `resultado_calculo.fonte_legal`.

**Rationale:** Reaproveitar schemas já validados evita inventar um formato fake que teria que ser descartado quando os nós de LLM ficarem reais.

**Alternatives Rejected:**
1. Fakes retornando dicts genéricos sem tipo — rejeitado; perderia a chance de validar que a "forma" dos dados entre nós já está correta antes de conectar LLMs reais.

**Consequences:**
- Acoplamento direto entre `orquestracao/` e `ingestion.chunking.chunk_models`/`motor_calculo` — desejado, é exatamente o que esta feature deveria provar

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `orquestracao/__init__.py` | Create | Marca o pacote | @python-developer | None |
| 2 | `orquestracao/estado.py` | Create | `State` (Pydantic) + `TransicaoAuditavel` + helper `registrar_transicao()` | @python-developer | None |
| 3 | `orquestracao/nos/__init__.py` | Create | Marca o subpacote | @python-developer | None |
| 4 | `orquestracao/nos/classificador.py` | Create | `mascarar_pii()` (real) + `no_classificador()` (PII real + intenção fake) | @python-developer | 2 |
| 5 | `orquestracao/nos/pesquisador_legal.py` | Create | `no_pesquisador_legal()` — fake, retorna `Chunk`s reais sintéticos | @python-developer | 2 |
| 6 | `orquestracao/nos/extrator_regras.py` | Create | `no_extrator_regras()` — fake, monta payload para o motor | @python-developer | 2 |
| 7 | `orquestracao/nos/deterministico.py` | Create | `no_deterministico()` — real, chama `TaxCalculatorEngine` | @python-developer | 2 |
| 8 | `orquestracao/nos/sintetizador.py` | Create | `no_sintetizador()` — fake, monta parecer Markdown | @python-developer | 2 |
| 9 | `orquestracao/grafo.py` | Create | Wiring via `langgraph.graph.StateGraph` (import lazy) | @genai-architect | 4, 5, 6, 7, 8 |
| 10 | `tests/test_nos.py` | Create | Testes unitários dos 5 nós (PII, fakes fiéis ao schema, integração real do Determinístico) | @test-generator | 4, 5, 6, 7, 8 |
| 11 | `tests/test_grafo_integration.py` | Create | AT-001, AT-002, AT-003 — encadeia os 5 nós em sequência (sem depender de `langgraph` instalado) | @test-generator | 10 |

**Total Files:** 11

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3, 4, 5, 6, 7, 8 | Especialista em código Python de domínio — Pydantic, regex, integração entre módulos |
| @genai-architect | 9 | Especialista em orquestração multi-agente e LangGraph especificamente |
| @test-generator | 10, 11 | Especialista em testes pytest cobrindo os Acceptance Tests do DEFINE |
| @code-reviewer | (revisão final) | Revisão de qualidade geral, com atenção especial ao tratamento de PII (Decision 3) |

**Agent Discovery:**
- `@genai-architect` introduzido nesta feature — é o agente recomendado no `CLAUDE.md` especificamente para "desenhar a orquestração multi-agente (LangGraph/CrewAI)"

---

## Code Patterns

### Pattern 1: `State` e histórico auditável

```python
# orquestracao/estado.py

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from ingestion.chunking.chunk_models import Chunk
from motor_calculo.engine import ResultadoCalculo


class TransicaoAuditavel(BaseModel):
    no: str
    resumo_input: str
    resumo_output: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class State(BaseModel):
    texto_consulta: str
    ano_operacao: int
    valor_base: Decimal

    texto_mascarado: str | None = None
    intencao: str | None = None
    chunks_legais: list[Chunk] = []
    payload_extraido: dict[str, Any] = {}
    resultado_calculo: ResultadoCalculo | None = None
    parecer_final: str | None = None

    historico: list[TransicaoAuditavel] = []

    def registrar_transicao(self, no: str, resumo_input: str, resumo_output: str) -> None:
        self.historico.append(
            TransicaoAuditavel(no=no, resumo_input=resumo_input, resumo_output=resumo_output)
        )
```

### Pattern 2: Nó Classificador (PII real + intenção fake)

```python
# orquestracao/nos/classificador.py

import re

from orquestracao.estado import State

_CPF_RE = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}")


def mascarar_pii(texto: str) -> str:
    texto = _CNPJ_RE.sub("[CNPJ_MASCARADO]", texto)
    texto = _CPF_RE.sub("[CPF_MASCARADO]", texto)
    return texto


def no_classificador(state: State) -> State:
    texto_mascarado = mascarar_pii(state.texto_consulta)

    # Classificação de intenção FAKE — sem LLM configurado nesta feature (ver DEFINE, Constraints)
    intencao = "SIMULACAO_TRIBUTARIA"

    state.texto_mascarado = texto_mascarado
    state.intencao = intencao
    state.registrar_transicao(
        no="classificador",
        resumo_input=texto_mascarado[:50],  # NUNCA state.texto_consulta — vazaria PII no histórico
        resumo_output=f"intencao={intencao}, pii_mascarado={texto_mascarado != state.texto_consulta}",
    )
    return state
```

### Pattern 3: Nó Determinístico (integração real)

```python
# orquestracao/nos/deterministico.py

from motor_calculo.engine import TaxCalculatorEngine
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed
from orquestracao.estado import State


def no_deterministico(state: State) -> State:
    engine = TaxCalculatorEngine(tabela=TabelaAliquotasSeed())

    # AliquotaNaoDisponivelError propaga sem ser capturada — o grafo deve
    # interromper, nunca seguir para o Sintetizador com dado inventado (AT-002)
    resultado = engine.calcular(
        valor_base=state.valor_base,
        ano_operacao=state.ano_operacao,
    )

    state.resultado_calculo = resultado
    state.registrar_transicao(
        no="deterministico",
        resumo_input=f"valor_base={state.valor_base}, ano={state.ano_operacao}",
        resumo_output=f"valor_liquido={resultado.valor_liquido}, fonte={resultado.fonte_legal}",
    )
    return state
```

### Pattern 4: `grafo.py` — wiring com import lazy do `langgraph`

```python
# orquestracao/grafo.py

from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def construir_grafo():
    """Isolado numa função — `langgraph` pode não estar instalado no ambiente
    de teste (ver Decision 1). A lógica de negócio dos nós, importada acima,
    não depende de `langgraph` para ser testada."""
    from langgraph.graph import END, START, StateGraph

    from orquestracao.estado import State

    grafo = StateGraph(State)
    grafo.add_node("classificador", no_classificador)
    grafo.add_node("pesquisador_legal", no_pesquisador_legal)
    grafo.add_node("extrator_regras", no_extrator_regras)
    grafo.add_node("deterministico", no_deterministico)
    grafo.add_node("sintetizador", no_sintetizador)

    grafo.add_edge(START, "classificador")
    grafo.add_edge("classificador", "pesquisador_legal")
    grafo.add_edge("pesquisador_legal", "extrator_regras")
    grafo.add_edge("extrator_regras", "deterministico")
    grafo.add_edge("deterministico", "sintetizador")
    grafo.add_edge("sintetizador", END)

    return grafo.compile()
```

---

## Data Flow

```text
1. Chamador cria State(texto_consulta, ano_operacao, valor_base)
   │
   ▼
2. no_classificador: mascara PII (real) + classifica intenção (fake); registra transição
   │
   ▼
3. no_pesquisador_legal: retorna Chunks sintéticos (schema real); registra transição
   │
   ▼
4. no_extrator_regras: monta payload simulado; registra transição
   │
   ▼
5. no_deterministico: chama TaxCalculatorEngine real — pode levantar AliquotaNaoDisponivelError,
   que propaga sem ser capturada (AT-002)
   │
   ▼
6. no_sintetizador: monta parecer Markdown a partir do resultado_calculo; registra transição
   │
   ▼
7. State final retornado — historico contém as 5 transições para auditoria
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| `motor_calculo` (feature já shipada) | Import Python direto, in-process | N/A |
| `ingestion.chunking.chunk_models` (feature já buildada) | Import Python direto, apenas o schema `Chunk` | N/A |
| `langgraph` | Biblioteca Python, import lazy em `grafo.py` | N/A — não instalável neste sandbox (ver Blockers no Build Report) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | Cada nó isoladamente (PII, fakes fiéis ao schema, integração real do Determinístico) | `tests/test_nos.py` | pytest | 100% dos nós |
| Integration | Encadeamento dos 5 nós em sequência, simulando o grafo sem depender de `langgraph` | `tests/test_grafo_integration.py` | pytest | AT-001, AT-002, AT-003 |
| E2E | `construir_grafo()` real via `langgraph`, invocado manualmente | Manual (fora deste sandbox) | - | Happy path, quando `langgraph` estiver instalado |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `AliquotaNaoDisponivelError` no nó Determinístico | Propaga sem ser capturada — o grafo interrompe antes do Sintetizador, nunca produz parecer com número inventado | No |
| CPF/CNPJ em formato não coberto pelo regex | Best-effort — texto passa adiante sem máscara nesse caso específico; limitação conhecida, não é uma falha silenciosa perigosa (não inventa dado, só não mascara 100% dos formatos) | No |

---

## Configuration

Nenhuma configuração externa nesta feature — todos os fakes são hardcoded em código; `TabelaAliquotasSeed` já vem do `motor_calculo` (feature anterior).

---

## Security Considerations

- O `historico` auditável (`TransicaoAuditavel`) deve armazenar apenas `texto_mascarado`, nunca `texto_consulta` original com PII — verificado por teste em `test_nos.py`
- Regex de CPF/CNPJ não é infalível (best-effort) — não deve ser apresentado como "anonimização garantida" em nenhuma documentação futura do produto
- Nenhuma credencial ou I/O externo nesta feature — todos os LLMs e a busca Qdrant são fakes in-process

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Não implementado nesta feature — o `historico` estruturado no `State` já cumpre o papel de rastreabilidade por enquanto |
| Metrics | N/A |
| Tracing | N/A — grafo síncrono, sem chamadas externas reais nesta feature |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-23 | design-agent | Versão inicial, a partir de DEFINE_ORQUESTRACAO_MULTIAGENTE.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ORQUESTRACAO_MULTIAGENTE.md`
