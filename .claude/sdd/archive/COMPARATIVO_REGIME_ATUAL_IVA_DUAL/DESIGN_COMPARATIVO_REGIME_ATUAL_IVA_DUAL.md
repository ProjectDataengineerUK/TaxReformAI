# DESIGN: COMPARATIVO_REGIME_ATUAL_IVA_DUAL

> Arquitetura e especificação técnica para expor a comparação regime atual x IVA Dual no `/simulador` e no `/consulta`, com paridade total de cálculo entre os dois endpoints.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMPARATIVO_REGIME_ATUAL_IVA_DUAL |
| **Date** | 2026-08-06 |
| **Author** | design-agent |
| **Status** | ✅ Shipped |

---

## Investigação prévia obrigatória (Assumption A-004 do DEFINE)

Antes de desenhar qualquer arquivo, a Open Question do DEFINE foi resolvida por leitura direta do código:

- `orquestracao/nos/sintetizador.py` tem um guardrail que exige que TODOS os campos numéricos calculados (`valor_base`, `valor_liquido`, `valor_cbs`, `valor_ibs`, `valor_is`) e a `fonte_legal` reapareçam literalmente (por identificador numérico) no parecer gerado pelo LLM. Hoje isso opera sobre `ResultadoCalculo`, um resultado ÚNICO (payload de `/consulta` tem 1 `valor_base` agregado).
- Com `itens: list[ItemSimulacao]` chegando no `/consulta` (paridade total confirmada no brainstorm), o resultado do cálculo passa a ser ITEMIZADO — múltiplos NCMs, múltiplos Anexos de redução, múltiplas fundamentações legais por item.
- **Risco real**: se o guardrail passasse a exigir que o parecer reproduza a fundamentação legal de CADA item individualmente, o texto livre gerado pelo Sonnet quase certamente resumiria/agruparia os itens em vez de listar cada um — reproduzindo o INCIDENTE JÁ DOCUMENTADO (`project_sintetizador_guardrail_reprovando_llm_direto.md`) em escala maior.

**Resolução (Decision 5 abaixo):** o guardrail passa a verificar só um conjunto FIXO e limitado de totais agregados — nunca escala com o número de itens. O detalhamento por item vira dado ESTRUTURADO (JSON), renderizado diretamente pelo frontend, no MESMO modelo de confiança que `itens_detalhados` já usa hoje no `/simulador` (nunca passa por narrativa de LLM). Isso preserva a garantia original do guardrail (nenhum número agregado pode ser alterado silenciosamente) sem reintroduzir o modo de falha já visto.

---

## Architecture Overview

```text
                         ┌─────────────────────────────┐
                         │   api/simulacao.py (NOVO)     │
                         │  calcular_simulacao_completa() │
                         │  (payload itens + ano +        │
                         │   regime_apuracao + comprador, │
                         │   db_pool, tenant_id)           │
                         │  -> RespostaSimulacao           │
                         │  (TODA a lógica hoje em          │
                         │   simular(), extraída sem         │
                         │   mudar comportamento)             │
                         └───────────┬─────────────┬────────┘
                                     │             │
                     chamada direta │             │ chamada direta
                     (mesmo processo)│             │(mesmo processo)
                                     │             │
                    ┌────────────────▼──┐      ┌───▼─────────────────────┐
                    │ api/routers/         │      │ orquestracao/nos/         │
                    │ simulate.py           │      │ deterministico.py           │
                    │ (casca fina: valida,   │      │ (chama a MESMA função,       │
                    │  chama, audit log,      │      │  guarda RespostaSimulacao     │
                    │  responde)               │      │  em state.resultado_simulacao) │
                    └────────────────┬──┘      └───┬─────────────────────┘
                                     │             │
                    POST /v1/tax/simulate           │
                                     │             │
                                     │      ┌──────▼──────────────────┐
                                     │      │ orquestracao/executor.py │
                                     │      │ (5 nós, sem mudança de    │
                                     │      │  ordem)                    │
                                     │      └──────┬──────────────────┘
                                     │             │
                                     │      ┌──────▼──────────────────┐
                                     │      │ nos/sintetizador.py       │
                                     │      │ guardrail SÓ sobre         │
                                     │      │ totais AGREGADOS            │
                                     │      │ (bounded, não escala        │
                                     │      │  com nº de itens)             │
                                     │      └──────┬──────────────────┘
                                     │             │
                                     │      POST /v1/tax/query
                                     │             │
                    ┌────────────────▼─────────────▼──────────────┐
                    │           frontend                           │
                    │  ComparativoRegime.tsx (NOVO, compartilhado)  │
                    │  usado por /simulador E /consulta               │
                    └────────────────────────────────────────────┘
```

**Data Flow (paridade `/simulador` x `/consulta`):**

1. `/simulador`: `PayloadSimulacao` (já itemizado hoje) → `api/routers/simulate.py` → `calcular_simulacao_completa()` → `RespostaSimulacao` → JSON direto pro frontend.
2. `/consulta`: `PayloadConsulta` (agora itemizado, `valor_base` removido) → `api/routers/query.py` monta `State` (com `itens`) → `orquestracao/executor.py` → `no_deterministico` chama a MESMA `calcular_simulacao_completa()` → `state.resultado_simulacao` → `no_sintetizador` narra os TOTAIS agregados → `RespostaConsulta` embute o `RespostaSimulacao` completo + o parecer em Markdown.

---

## Key Decisions

### Decision 1: Extrair `simular()` para `api/simulacao.py::calcular_simulacao_completa()`, chamada direta (sem HTTP interno)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** `api/routers/simulate.py::simular()` tem ~700 linhas de lógica de cálculo (resolução de SKU, IPI, 10 Anexos de redução, Imposto Seletivo, regime atual por item) dentro do handler HTTP. `/consulta` precisa da MESMA lógica.

**Choice:** Nova função pura `calcular_simulacao_completa(itens, ano_operacao, regime_apuracao, comprador_tipo, db_pool, tenant_id) -> RespostaSimulacao` em `api/simulacao.py`. `simular()` vira casca fina: valida `tenant_id`, chama a função, grava audit log, responde. `orquestracao/nos/deterministico.py` chama a MESMA função.

**Rationale:** Mesmo padrão já usado no projeto (`db/repositorio.py` reaproveitado por API e scripts). Nenhuma duplicação de ~700 linhas de lógica já verificada em produção.

**Alternatives Rejected:**
1. Chamada HTTP interna do nó da orquestração para `/v1/tax/simulate` (como o padrão OIDC de Cloud Tasks) — desproporcional: os dois já rodam no mesmo processo.
2. Duplicar a lógica dentro de `orquestracao/nos/deterministico.py` — divergiria silenciosamente da versão do `/simulador` no primeiro bugfix.

**Consequences:**
- `orquestracao/` passa a importar de `api/simulacao.py` — estende a direção de dependência já existente (`api/` já depende de `orquestracao/`), mas SEM ciclo: `api/simulacao.py` não importa nada de `orquestracao/`. Documentado aqui para não ser lido como acidente na revisão de código.
- Erros de validação (SKU não resolvido, alíquota indisponível) deixam de ser `HTTPException` (acoplado ao FastAPI) e viram exceções de domínio simples, traduzidas por CADA chamador para o formato que precisa (ver Decision 4).

---

### Decision 2: `State` ganha `itens`/`regime_apuracao`/`comprador_tipo`/`tenant_id`; `resultado_calculo` vira `resultado_simulacao: RespostaSimulacao`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** `orquestracao/estado.py::State` hoje carrega só `valor_base` (Decimal único) e `resultado_calculo: ResultadoCalculo` (resultado agregado único). Precisa carregar itens e devolver o resultado itemizado completo.

**Choice:** `State` ganha `itens: list[ItemSimulacao]`, `regime_apuracao: RegimeApuracao | None`, `comprador_tipo: CompradorTipo | None`, `tenant_id: str`. `resultado_calculo: ResultadoCalculo | None` é RENOMEADO e RETIPADO para `resultado_simulacao: RespostaSimulacao | None` — reaproveita o schema Pydantic já existente em `api/schemas_simulate.py`, em vez de inventar uma estrutura paralela.

**Rationale:** `RespostaSimulacao` já é exatamente a forma de dado que `no_sintetizador` e `api/routers/query.py` precisam (resumo financeiro + itens detalhados + regime vigente + itens do regime vigente). Duplicar essa estrutura como um novo dataclass só para a orquestração criaria duas fontes de verdade para o mesmo formato.

**Alternatives Rejected:**
1. Manter `ResultadoCalculo` e adicionar campos itemizados por fora — perderia a estrutura já testada de `RespostaSimulacao` (escopo, compensação, IPI não resolvido, etc.)

**Consequences:**
- `State` (que vive em `orquestracao/`) importa de `api/schemas_simulate.py` — mesma extensão de direção de dependência da Decision 1, mesma justificativa.
- `valor_base: Decimal` continua existindo em `State` (não removido) — passa a ser DERIVADO (soma dos itens), calculado em `api/routers/query.py` antes de montar o `State`, preservando o comportamento de `extrator_regras.py` (que compara `valor_base` extraído do texto contra `state.valor_base`) sem tocar aquele nó.

---

### Decision 3: `DependenciasOrquestracao` ganha `db_pool`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** `calcular_simulacao_completa()` precisa de `db_pool` (IPI, Anexos de redução, Imposto Seletivo, catálogo de SKUs). `no_deterministico` só recebe `deps: DependenciasOrquestracao`, que hoje não carrega `db_pool` (só é usado localmente em `criar_dependencias_reais` para construir o `RegistradorUsoLLMPostgres`).

**Choice:** Novo campo `db_pool: Any = None` em `DependenciasOrquestracao`. `criar_dependencias_reais` passa a armazenar o `db_pool` recebido, além de usá-lo para o registrador.

**Rationale:** Mesmo padrão de opcionalidade já usado (`RegistradorUsoLLMPostgres` já lida com `db_pool=None` sem quebrar) — `db_pool=None` em teste continua funcionando para os nós que não o tocam.

**Consequences:**
- `criar_dependencias_fake` (usado em testes) também ganha `db_pool: Any = None` no construtor, default `None` — testes existentes que não passam `db_pool` continuam passando sem alteração.

---

### Decision 4: Nova exceção de domínio `SkuNaoResolvidoError`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** `simular()` hoje levanta `HTTPException(422, ...)` diretamente dentro do laço de resolução de SKU (2 pontos: SKU não cadastrado, catálogo indisponível). `HTTPException` é uma classe do FastAPI — não faz sentido para código chamado pela orquestração (que não está numa request HTTP).

**Choice:** `api/simulacao.py` define `SkuNaoResolvidoError(Exception)` com uma mensagem já formatada. `api/routers/simulate.py` captura e traduz para `HTTPException(422, ...)` (comportamento idêntico a hoje). `api/routers/query.py` captura e traduz para o mesmo 422 que já usa para `AliquotaNaoDisponivelError`/`ConsultaForaDeEscopoError`.

**Rationale:** Mesmo padrão já usado no projeto para `AliquotaNaoDisponivelError` — exceção de domínio, tradução no limite de cada camada.

**Consequences:**
- Nenhuma mudança de comportamento observável no `/simulador` (AT-007 do DEFINE) — só o TIPO da exceção interna muda, a resposta HTTP final é idêntica.

---

### Decision 5: Guardrail do sintetizador verifica só totais agregados (resolve A-004)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** Ver seção "Investigação prévia obrigatória" acima.

**Choice:**
- `RespostaSimulacao` ganha um campo novo: `fonte_legal_fase: str` — a citação da fase vigente para CBS/IBS/IS (`regra.fonte_legal`, já calculada uma vez no topo de `simular()`/`calcular_simulacao_completa()`, igual para TODOS os itens de um mesmo `ano_operacao`, independente de quantos itens existam ou de quais Anexos cada um dispara).
- O prompt do sintetizador para `/consulta` passa a incluir só: os 5 campos de `resumo_financeiro`, os até 8 campos NÃO-NULOS de `regime_vigente` (totais agregados: `total_pis`, `total_cofins`, `total_icms_interestadual`, `total_icms_interno`, `total_icms_interno_fecp`, `total_iss_piso`, `total_iss_teto`, `total_ipi`) e `fonte_legal_fase`.
- O guardrail (`_valor_aparece`/`_fonte_legal_aparece`) roda sobre esse conjunto FIXO — nunca itera `itens_detalhados`/`itens_regime_vigente` item a item.
- O prompt instrui explicitamente o LLM a narrar a comparação em termos AGREGADOS, e menciona que o detalhamento por item já está disponível em outra parte da tela (não pede pro LLM listar item a item).

**Rationale:** Preserva a garantia original (nenhum total agregado pode ser alterado silenciosamente pelo LLM) sem escalar com o número de itens — a mesma lição já aprendida (formatação rígida demais quebra respostas corretas) aplicada preventivamente, antes de causar um incidente novo em escala maior.

**Alternatives Rejected:**
1. Exigir que o parecer reproduza a fundamentação de CADA item — rejeitado pelo risco de rejeição em massa já documentado.
2. Não verificar nada sobre `regime_vigente` no parecer (só o lado IVA Dual, como hoje) — rejeitado porque a resposta é sobre justamente ADICIONAR essa comparação; deixá-la sem guardrail abriria a MESMA classe de vulnerabilidade que a revisão de segurança de `LLM_REAL_VERTEX_AI` já encontrou uma vez (LLM alterando um valor que o guardrail não olha).

**Consequences:**
- Itens individuais (`itens_detalhados`, `itens_regime_vigente`) nunca passam pelo LLM — chegam ao frontend como JSON estruturado, MESMO modelo de confiança que `/simulador` já usa hoje.
- `_valor_aparece`/`_fonte_legal_aparece` (funções puras já existentes) não mudam de assinatura — só o CONJUNTO de valores verificados muda.

---

### Decision 6: `PayloadConsulta` perde `valor_base`, ganha `itens`; `RespostaConsulta` compõe `RespostaSimulacao`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** Decisão já tomada no brainstorm (mudança breaking, sem cliente externo conhecido além do próprio frontend — Assumption A-001 do DEFINE).

**Choice:**
```python
class PayloadConsulta(BaseModel):
    texto_consulta: str = Field(min_length=1)
    ano_operacao: int
    itens: list[ItemSimulacao] = Field(min_length=1, max_length=100)
    regime_apuracao: RegimeApuracao | None = None
    comprador_tipo: CompradorTipo | None = None

class RespostaConsulta(BaseModel):
    parecer_final: str
    resultado_simulacao: RespostaSimulacao
    historico: list[TransicaoResposta]
```

**Rationale:** Reaproveita `ItemSimulacao`/`RespostaSimulacao` inteiros (nenhum campo novo duplicado) — o mesmo componente de frontend que renderiza a comparação do `/simulador` passa a servir o `/consulta` sem adaptação de schema.

**Consequences:**
- `valor_base` some do payload de entrada — quem chamava `/v1/tax/query` com `valor_base` direto quebra (mudança breaking documentada, Assumption A-001).
- `RespostaConsulta.valor_liquido`/`.fonte_legal` (campos antigos, top-level) somem — consumidores leem `resultado_simulacao.resumo_financeiro.valor_liquido_projetado_split_payment` em vez disso.

---

### Decision 7: Formulários ganham `natureza` (por item) e `regime_apuracao` (por operação)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** Sem esses campos, ISS e PIS/COFINS sempre apareceriam como "não calculado" na tabela nova — a comparação ficaria incompleta por padrão em todo simulador (já confirmado no brainstorm).

**Choice:** `SimuladorForm.tsx` e o novo formulário itemizado do `/consulta` ganham: um `<select>` de `natureza` (MERCADORIA/SERVICO) por item, e um `<select>` de `regime_apuracao` (nível de operação, não por item) com opção vazia = "não informado".

**Rationale:** Espelha exatamente a semântica do backend (`natureza` já é por item em `ItemSimulacao`; `regime_apuracao` já é por operação em `PayloadSimulacao`/`PayloadConsulta`).

**Consequences:**
- Nenhum campo passa a ser obrigatório — `natureza` mantém default `MERCADORIA` (comportamento idêntico a hoje se o usuário não mexer), `regime_apuracao` mantém `None`/vazio.

---

### Decision 8: `ComparativoRegime.tsx` — um componente só, usado pelas duas telas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-06 |

**Context:** `/simulador` e `/consulta` agora devolvem o MESMO shape de dado de comparação (`RespostaSimulacao`, direto ou aninhado em `resultado_simulacao`).

**Choice:** Um componente novo, `frontend/components/ComparativoRegime.tsx`, recebe `{ resposta: RespostaSimulacao }` e renderiza:
1. Uma tabela agregada (regime atual x IVA Dual, cada linha um tributo, com fonte legal e "não calculado" quando `null`).
2. Uma tabela por item (SKU, tributos do regime atual aplicáveis àquele item, tributos do IVA Dual daquele item).

`ResultadoSimulacao.tsx` passa a renderizar `<ComparativoRegime resposta={resposta} />` além do que já renderiza. `ParecerMarkdown.tsx` passa a renderizar `<ComparativoRegime resposta={resposta.resultado_simulacao} />` além do parecer em Markdown.

**Rationale:** DRY — uma tabela, testada uma vez, reaproveitada nas duas telas.

**Consequences:** Nenhuma duplicação de lógica de renderização entre as duas páginas.

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|--------------|
| 1 | `api/simulacao.py` | Create | Extrai `calcular_simulacao_completa()` + `SkuNaoResolvidoError` de `simular()` | None |
| 2 | `api/schemas_simulate.py` | Modify | Adiciona `fonte_legal_fase: str` a `RespostaSimulacao` | None |
| 3 | `api/routers/simulate.py` | Modify | Vira casca fina sobre `api/simulacao.py`; captura `SkuNaoResolvidoError` | 1, 2 |
| 4 | `api/schemas_query.py` | Modify | `PayloadConsulta` ganha `itens`/`regime_apuracao`/`comprador_tipo`, perde `valor_base`; `RespostaConsulta` compõe `RespostaSimulacao` | 2 |
| 5 | `orquestracao/dependencias.py` | Modify | `DependenciasOrquestracao` ganha `db_pool`; `criar_dependencias_reais`/`criar_dependencias_fake` atualizados | None |
| 6 | `orquestracao/estado.py` | Modify | `State` ganha `itens`/`regime_apuracao`/`comprador_tipo`/`tenant_id`; `resultado_calculo` → `resultado_simulacao: RespostaSimulacao` | 2 |
| 7 | `orquestracao/nos/deterministico.py` | Modify | Chama `calcular_simulacao_completa()` em vez de `TaxCalculatorEngine.calcular()` direto | 1, 5, 6 |
| 8 | `orquestracao/nos/sintetizador.py` | Modify | Guardrail passa a verificar totais agregados de `resultado_simulacao` (Decision 5) | 6 |
| 9 | `orquestracao/executor.py` | Modify | Captura `SkuNaoResolvidoError` (re-propaga, mesmo padrão de `AliquotaNaoDisponivelError`) | 1 |
| 10 | `api/routers/query.py` | Modify | Monta `State` com `itens`; captura `SkuNaoResolvidoError`; monta `RespostaConsulta` com `resultado_simulacao` aninhado | 4, 6, 9 |
| 11 | `frontend/lib/types.ts` | Modify | `RespostaSimulacao` ganha `regime_vigente`/`itens_regime_vigente`/`fonte_legal_fase`; `PayloadConsulta`/`RespostaConsulta` redesenhados | None |
| 12 | `frontend/components/ComparativoRegime.tsx` | Create | Tabela comparativa agregada + por item (Decision 8) | 11 |
| 13 | `frontend/components/ResultadoSimulacao.tsx` | Modify | Renderiza `<ComparativoRegime />` | 11, 12 |
| 14 | `frontend/components/SimuladorForm.tsx` | Modify | Ganha seletor de `natureza` por item + `regime_apuracao` por operação | 11 |
| 15 | `frontend/components/ConsultaForm.tsx` | Modify | Troca `valor_base` por lista de itens (mesmo padrão de `SimuladorForm`) + `natureza`/`regime_apuracao` | 11 |
| 16 | `frontend/components/ParecerMarkdown.tsx` | Modify | Renderiza `<ComparativoRegime resposta={resposta.resultado_simulacao} />` | 11, 12 |
| 17 | `tests/test_api_simulate.py` | Modify | AT-007: resposta byte-idêntica antes/depois da extração | 1, 3 |
| 18 | `tests/test_simulacao.py` | Create | Testes unitários de `calcular_simulacao_completa()` isolada | 1 |
| 19 | `tests/test_nos.py` | Modify | `no_deterministico` com itens reais; guardrail do sintetizador com resultado itemizado | 7, 8 |
| 20 | `tests/test_grafo_integration.py` | Modify | AT-003/AT-008: paridade `/simulador` x `/consulta` para o mesmo payload | 7, 8, 9, 10 |
| 21 | `tests/test_api_query.py` | Modify | Novo shape de `PayloadConsulta`/`RespostaConsulta`; AT-004 (valor_base derivado) | 10 |
| 22 | `frontend/components/ComparativoRegime.test.tsx` | Create | Testes do componente novo (não calculado, fonte legal, agregado + por item) | 12 |
| 23 | `frontend/app/simulador/page.test.tsx` | Modify | Cobre o novo campo `natureza`/`regime_apuracao` no submit | 14 |
| 24 | `frontend/app/consulta/page.test.tsx` | Modify | Cobre o novo payload itemizado | 15 |

---

## Code Patterns

### `api/simulacao.py` — assinatura da função extraída

```python
class SkuNaoResolvidoError(Exception):
    """Substitui os 2 HTTPException inline de simular() — traduzido para 422
    por CADA chamador (router HTTP, orquestração), nunca acoplado ao FastAPI."""


def calcular_simulacao_completa(
    itens: list[ItemSimulacao],
    ano_operacao: int,
    regime_apuracao: RegimeApuracao | None,
    comprador_tipo: CompradorTipo | None,
    db_pool,
    tenant_id: str,
) -> RespostaSimulacao:
    """TODA a lógica hoje em simular(), do `tabela = TabelaAliquotasSeed()`
    até o `resposta = RespostaSimulacao(...)` — comportamento IDÊNTICO,
    só movido de lugar (AT-007). Levanta AliquotaNaoDisponivelError e
    SkuNaoResolvidoError; NUNCA HTTPException."""
    ...
```

### `orquestracao/nos/deterministico.py` — reescrito

```python
from api.simulacao import calcular_simulacao_completa
from orquestracao.estado import State
from orquestracao.dependencias import DependenciasOrquestracao


def no_deterministico(state: State, deps: DependenciasOrquestracao) -> State:
    # AliquotaNaoDisponivelError/SkuNaoResolvidoError propagam sem serem
    # capturadas — o grafo deve interromper, nunca seguir para o
    # Sintetizador com dado inventado (mesma disciplina de AT-002).
    resultado = calcular_simulacao_completa(
        itens=state.itens,
        ano_operacao=state.ano_operacao,
        regime_apuracao=state.regime_apuracao,
        comprador_tipo=state.comprador_tipo,
        db_pool=deps.db_pool,
        tenant_id=state.tenant_id,
    )

    state.resultado_simulacao = resultado
    state.registrar_transicao(
        no="deterministico",
        resumo_input=f"{len(state.itens)} item(ns), ano={state.ano_operacao}",
        resumo_output=(
            f"valor_liquido={resultado.resumo_financeiro.valor_liquido_projetado_split_payment}, "
            f"fonte={resultado.fonte_legal_fase}"
        ),
    )
    return state
```

Nota: `no_deterministico` passa a receber `deps`, mudando sua assinatura (hoje é só `state`) — `orquestracao/executor.py` já passa `deps` para os outros 4 nós, então a chamada em `executar_consulta` muda de `no_deterministico(state)` para `no_deterministico(state, deps)`.

### `orquestracao/nos/sintetizador.py` — guardrail sobre totais agregados

```python
def no_sintetizador(state: State, deps: DependenciasOrquestracao) -> State:
    resultado = state.resultado_simulacao
    assert resultado is not None

    resumo = resultado.resumo_financeiro
    regime = resultado.regime_vigente

    # Campos AGREGADOS só — nunca itera itens_detalhados/itens_regime_vigente
    # (Decision 5, resolve Assumption A-004 do DEFINE).
    campos_numericos = {
        "valor_bruto_total": resumo.valor_bruto_total,
        "total_cbs": resumo.total_cbs,
        "total_ibs": resumo.total_ibs,
        "total_is": resumo.total_is,
        "valor_liquido": resumo.valor_liquido_projetado_split_payment,
    }
    for nome, valor in {
        "total_pis": regime.total_pis,
        "total_cofins": regime.total_cofins,
        "total_icms_interestadual": regime.total_icms_interestadual,
        "total_icms_interno": regime.total_icms_interno,
        "total_icms_interno_fecp": regime.total_icms_interno_fecp,
        "total_iss_piso": regime.total_iss_piso,
        "total_iss_teto": regime.total_iss_teto,
        "total_ipi": regime.total_ipi,
    }.items():
        if valor is not None:  # "não calculado" nunca precisa aparecer no texto
            campos_numericos[nome] = valor

    ausentes = [n for n, v in campos_numericos.items() if not _valor_aparece(v, resposta)]
    if not _fonte_legal_aparece(resultado.fonte_legal_fase, resposta):
        ausentes.append("fonte_legal_fase")
    ...
```

### Frontend — `ComparativoRegime.tsx`, assinatura

```tsx
export function ComparativoRegime({ resposta }: { resposta: RespostaSimulacao }) {
  // Tabela 1: agregado — uma linha por tributo do regime_vigente + os 3 do
  // IVA Dual (CBS/IBS/IS), "não calculado" quando o total é null.
  // Tabela 2: itens_detalhados[i] ao lado de itens_regime_vigente[i]
  // (mesmo índice — resposta.itens_detalhados[i].sku === resposta
  // .itens_regime_vigente[i].sku, útil para o teste de correspondência).
}
```

### `frontend/lib/types.ts` — trechos novos

```typescript
export interface RegimeVigenteResumo {
  regime_apuracao: string | null;
  total_pis: string | null;
  total_cofins: string | null;
  total_icms_interestadual: string;
  total_icms_interno: string;
  total_icms_interno_fecp: string;
  total_iss_piso: string;
  total_iss_teto: string;
  total_ipi: string | null;
  tributos_nao_calculados: string[];
}

export interface ItemRegimeVigente {
  sku: string;
  natureza: string;
  icms_interestadual_percentual: string | null;
  fonte_legal_icms: string | null;
  icms_interno_percentual: string | null;
  fonte_legal_icms_interno: string | null;
  icms_interno_fecp_percentual: string | null;
  fonte_legal_icms_interno_fecp: string | null;
  iss_piso_percentual: string | null;
  iss_teto_percentual: string | null;
  pis_percentual: string | null;
  cofins_percentual: string | null;
  fonte_legal_pis: string | null;
  fonte_legal_cofins: string | null;
}

export interface RespostaSimulacao {
  status: string;
  ano_operacao: number;
  resumo_financeiro: ResumoFinanceiro;
  itens_detalhados: ItemDetalhado[];
  regime_vigente: RegimeVigenteResumo;
  itens_regime_vigente: ItemRegimeVigente[];
  fonte_legal_fase: string;
}

export interface PayloadConsulta {
  texto_consulta: string;
  ano_operacao: number;
  itens: ItemSimulacao[];
  regime_apuracao?: string | null;
  comprador_tipo?: string | null;
}

export interface RespostaConsulta {
  parecer_final: string;
  resultado_simulacao: RespostaSimulacao;
  historico: TransicaoResposta[];
}
```

> Nota de implementação: os campos exatos de `ItemDetalhado`/`RegimeVigenteResumo`/`ItemRegimeVigente` devem ser lidos direto de `api/schemas_simulate.py` no momento do `/build` — o trecho acima é ilustrativo, não a lista definitiva de campos (o schema real tem mais campos que os citados no DEFINE, ex: `escopo`, `reducao`, `piso_aliquota_ibs`, `ipi_nao_resolvido`).

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `calcular_simulacao_completa()` isolada (fakes de `db_pool`) | pytest |
| Non-regression | `/v1/tax/simulate` — resposta idêntica antes/depois da extração (AT-007) | pytest, comparação de payload completo |
| Integration | `/v1/tax/query` com itens reais — paridade numérica com `/v1/tax/simulate` para o mesmo payload (AT-003, AT-008) | pytest |
| Integration | Guardrail do sintetizador com `resultado_simulacao` itemizado, incluindo campos `None` (regime_apuracao ausente) | pytest, `ClienteLLMFake` |
| Unit | Frontend `ComparativoRegime.tsx` — agregado, por item, "não calculado" | Vitest + Testing Library |
| Integration | Formulários (`SimuladorForm`/`ConsultaForm`) — novo campo `natureza`/`regime_apuracao` no submit | Vitest + Testing Library |

**Casos de borda cobertos pelos ATs do DEFINE:**
- AT-001 (happy path), AT-002 (tributo não calculado declarado), AT-003 (paridade `/consulta`), AT-004 (valor_base derivado), AT-005 (não-regressão `ano_operacao >= 2027`), AT-006 (SERVICO aciona ISS), AT-007 (extração sem regressão), AT-008 (condição de comprador idêntica nos dois endpoints).

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md`
