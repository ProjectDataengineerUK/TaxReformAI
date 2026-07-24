# DESIGN: Motor Determinístico de Cálculo (IVA Dual / Split Payment)

> Technical design for implementing o motor Python puro que calcula CBS/IBS/IS e Split Payment por fase da transição, aplicando apenas alíquotas rastreáveis a uma fonte legal real.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MOTOR_DETERMINISTICO_CALCULO |
| **Date** | 2026-07-22 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_MOTOR_DETERMINISTICO_CALCULO.md](./DEFINE_MOTOR_DETERMINISTICO_CALCULO.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────┐
│                  MOTOR DETERMINÍSTICO DE CÁLCULO (MVP)                 │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [valor_base, ano_operacao, split_payment_active]                      │
│        │  engine.py                                                    │
│        ▼                                                               │
│  [fase_para(ano_operacao)] ──► FaseTransicao (fases.py)                │
│        │                                                                │
│        ▼                                                               │
│  [TabelaAliquotas.buscar(fase)] ──► AliquotaNaoDisponivelError         │
│        │  (se a fase não tiver RegraFiscal confirmada em lei)          │
│        ▼                                                               │
│  [RegraFiscal: aliq_cbs, aliq_ibs, aliq_is, fonte_legal]               │
│        │  engine.py — Decimal + ROUND_HALF_UP                          │
│        ▼                                                               │
│  [ResultadoCalculo: valor_cbs, valor_ibs, valor_is,                    │
│   total_tributos, valor_liquido, fonte_legal]                          │
│                                                                         │
│  Sem I/O externo — motor standalone, sem GCP/Qdrant/Postgres           │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `FaseTransicao` (Enum) + `fase_para()` | Resolve um ano de operação para a fase correta da linha do tempo da reforma | Python `enum.Enum` |
| `RegraFiscal` | Alíquotas de uma fase, com fonte legal obrigatória — nunca uma alíquota "sem explicação" | `dataclass(frozen=True)` |
| `AliquotaNaoDisponivelError` | Erro explícito quando a fase solicitada não tem `RegraFiscal` confirmada | `Exception` customizada (mesmo padrão de `ASTParseError`) |
| `TabelaAliquotas` (Protocol) + `TabelaAliquotasSeed` | Fonte de `RegraFiscal` por fase — abstração para trocar por dados reais no futuro | `typing.Protocol` (mesmo padrão de `RawStorage`/`LegalSource`) |
| `TaxCalculatorEngine` | Aplica a fórmula do IVA Dual + Split Payment com `Decimal` | Python puro |

---

## Key Decisions

### Decision 1: `TabelaAliquotas` como Protocol + implementação seed em memória

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O DEFINE exige que a fonte de alíquotas seja auditável e extensível (crescer conforme mais Resoluções do Senado forem ingeridas no futuro), e que o motor nunca aceite alíquota sem fonte legal confirmada.

**Choice:** `TabelaAliquotas` é um `Protocol` com um método `buscar(fase: FaseTransicao) -> RegraFiscal`, que levanta `AliquotaNaoDisponivelError` se a fase não tiver regra confirmada. A implementação concreta `TabelaAliquotasSeed` vem hardcoded só com a fase 2026 (a única confirmada em lei), com `fonte_legal` obrigatória em cada entrada.

**Rationale:** Consistente com o padrão já usado no pipeline de ingestão (`RawStorage`, `LegalSource`, ambos `Protocol`) — quando as Resoluções do Senado forem ingeridas numa feature futura, basta trocar `TabelaAliquotasSeed` por uma implementação que lê do Qdrant/Postgres, sem alterar o motor de cálculo.

**Alternatives Rejected:**
1. Alíquotas como parâmetro direto da função de cálculo (como no exemplo do blueprint, seção 6.1) — rejeitado, não força a rastreabilidade de fonte legal exigida pelo DEFINE.
2. Alíquotas num arquivo YAML/JSON de configuração — rejeitado nesta fase; um `Protocol` Python é mais simples de testar e não precisa de infraestrutura de arquivo para uma única entrada confirmada.

**Consequences:**
- Pequena camada de indireção para uma única entrada real hoje (2026)
- Caminho claro de evolução para uma fonte de dados real sem refatorar o motor de cálculo

---

### Decision 2: `FaseTransicao` como Enum explícito, não apenas "ano"

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** A linha do tempo da reforma tem fases com regras distintas por período (2026 teste; 2027 pleno CBS/IS; 2029-2032 transição gradual ICMS/ISS; 2033 regime pleno) — mapear "ano" diretamente para "regra" sem um conceito de fase gera ambiguidade e duplicação.

**Choice:** Um `Enum FaseTransicao` (`TESTE_2026`, `PLENO_CBS_IS_2027`, `TRANSICAO_ICMS_ISS_2029_2032`, `REGIME_PLENO_2033`) com uma função `fase_para(ano: int) -> FaseTransicao` que resolve o ano para a fase correta.

**Rationale:** Simulações chegam com um ano/data de operação; o motor precisa saber automaticamente qual conjunto de regras aplicar, sem o chamador precisar conhecer os detalhes da linha do tempo da reforma.

**Alternatives Rejected:**
1. Usar o ano como chave direta da `TabelaAliquotas` — rejeitado; a fase 2029-2032 tem 4 anos com a mesma lógica de transição gradual, então mapear ano→fase evita duplicar entradas idênticas.

**Consequences:**
- Uma camada extra de mapeamento (`fase_para`)
- Motor já preparado para quando 2029-2032 tiver dados reais — basta decidir, na feature futura, se a granularidade da `RegraFiscal` é por fase ou por ano dentro da fase

---

### Decision 3: Erro explícito em vez de valor sentinela/`None`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O DEFINE exige que o motor "recusa explicitamente" o cálculo quando não há alíquota confirmada — não pode silenciosamente retornar `0`, `None`, ou uma estimativa.

**Choice:** `AliquotaNaoDisponivelError(fase, ano)` — exceção customizada com mensagem explicando o que falta (ex.: "Resolução do Senado para a fase PLENO_CBS_IS_2027 ainda não ingerida").

**Rationale:** Consistente com o padrão de `ASTParseError` já usado no pipeline de ingestão; crítico para nunca produzir uma simulação silenciosa com dado legal ausente.

**Alternatives Rejected:**
1. Retornar `ResultadoCalculo | None` — rejeitado; um chamador poderia ignorar o `None` e seguir adiante silenciosamente. Uma exceção força tratamento explícito.

**Consequences:**
- Chamadores precisam de `try/except` ao redor da chamada do motor
- Impossível ignorar acidentalmente uma simulação com dados legais incompletos

---

### Decision 4: `ResultadoCalculo` carrega a `fonte_legal` aplicada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** A proposta de valor do produto (`contexto.md`, seção 1.1) é "100% auditável, citando fontes oficiais" — o resultado do motor precisa carregar essa citação, não só os números.

**Choice:** `ResultadoCalculo` inclui um campo `fonte_legal: str`, herdado diretamente da `RegraFiscal` usada no cálculo.

**Rationale:** Sem isso, o futuro "Agente Sintetizador de Pareceres" (seção 3 do blueprint) não teria como citar a fonte no parecer final — a auditabilidade precisa nascer no motor, não ser costurada depois por outro componente.

**Alternatives Rejected:**
1. Retornar só os números e deixar o chamador buscar a fonte separadamente — rejeitado; cria risco de dessincronia entre o número calculado e a fonte citada.

**Consequences:**
- Nenhum trade-off relevante — o campo é essencialmente gratuito de incluir

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `motor_calculo/__init__.py` | Create | Marca o pacote Python | @python-developer | None |
| 2 | `motor_calculo/fases.py` | Create | `FaseTransicao` (Enum) + `fase_para(ano)` | @python-developer | None |
| 3 | `motor_calculo/regras_fiscais.py` | Create | `RegraFiscal` (dataclass) + `AliquotaNaoDisponivelError` | @python-developer | 2 |
| 4 | `motor_calculo/tabela_aliquotas.py` | Create | `TabelaAliquotas` (Protocol) + `TabelaAliquotasSeed` (só fase 2026) | @python-developer | 2, 3 |
| 5 | `motor_calculo/engine.py` | Create | `TaxCalculatorEngine` (Decimal/ROUND_HALF_UP, Split Payment) + `ResultadoCalculo` | @python-developer | 3, 4 |
| 6 | `tests/test_fases.py` | Create | `fase_para(ano)` para todo o intervalo 2026-2033 + limites inválidos | @test-generator | 2 |
| 7 | `tests/test_tabela_aliquotas.py` | Create | 2026 retorna `RegraFiscal`; demais fases levantam `AliquotaNaoDisponivelError` | @test-generator | 4 |
| 8 | `tests/test_engine.py` | Create | AT-001 (happy path 2026), AT-002 (erro em fase sem regra), AT-003 (Split Payment desativado) | @test-generator | 5 |

**Total Files:** 8

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3, 4, 5 | Especialista em código Python de domínio — dataclasses, Enum, Decimal, Protocol |
| @test-generator | 6, 7, 8 | Especialista em testes pytest cobrindo os Acceptance Tests do DEFINE |
| @code-reviewer | (revisão final, todos os arquivos) | Revisão de qualidade geral antes de marcar a feature como concluída |

**Agent Discovery:**
- Mesmos agentes já usados na feature `PIPELINE_INGESTAO_LEGAL`, reaproveitados por consistência de stack (Python puro, sem novas dependências de infraestrutura)

---

## Code Patterns

### Pattern 1: `FaseTransicao` e resolução de ano

```python
# motor_calculo/fases.py

from enum import Enum


class FaseTransicao(Enum):
    TESTE_2026 = "TESTE_2026"
    PLENO_CBS_IS_2027 = "PLENO_CBS_IS_2027"
    TRANSICAO_ICMS_ISS_2029_2032 = "TRANSICAO_ICMS_ISS_2029_2032"
    REGIME_PLENO_2033 = "REGIME_PLENO_2033"


def fase_para(ano: int) -> FaseTransicao:
    if ano == 2026:
        return FaseTransicao.TESTE_2026
    if 2027 <= ano <= 2028:
        return FaseTransicao.PLENO_CBS_IS_2027
    if 2029 <= ano <= 2032:
        return FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032
    if ano >= 2033:
        return FaseTransicao.REGIME_PLENO_2033
    raise ValueError(f"Ano {ano} anterior ao início da reforma tributária (2026)")
```

### Pattern 2: `RegraFiscal` e erro explícito

```python
# motor_calculo/regras_fiscais.py

from dataclasses import dataclass
from decimal import Decimal

from motor_calculo.fases import FaseTransicao


@dataclass(frozen=True)
class RegraFiscal:
    fase: FaseTransicao
    aliq_cbs: Decimal
    aliq_ibs: Decimal
    aliq_is: Decimal
    fonte_legal: str
    confirmado_em_lei: bool = True


class AliquotaNaoDisponivelError(Exception):
    def __init__(self, fase: FaseTransicao):
        super().__init__(
            f"Alíquota não disponível para a fase {fase.value} — "
            "requer Resolução do Senado/TCU ainda não ingerida. "
            "Nenhum cálculo é retornado para evitar simular com dado não confirmado."
        )
        self.fase = fase
```

### Pattern 3: `TabelaAliquotas` (Protocol + seed)

```python
# motor_calculo/tabela_aliquotas.py

from decimal import Decimal
from typing import Protocol

from motor_calculo.fases import FaseTransicao
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError, RegraFiscal


class TabelaAliquotas(Protocol):
    def buscar(self, fase: FaseTransicao) -> RegraFiscal: ...


class TabelaAliquotasSeed:
    """Só contém a fase 2026 — a única com alíquota 100% confirmada em lei
    no momento desta feature (ver DEFINE, Data Contract)."""

    _REGRAS: dict[FaseTransicao, RegraFiscal] = {
        FaseTransicao.TESTE_2026: RegraFiscal(
            fase=FaseTransicao.TESTE_2026,
            aliq_cbs=Decimal("0.009"),
            aliq_ibs=Decimal("0.001"),
            aliq_is=Decimal("0"),
            fonte_legal="Linha do tempo da transição — CBS 0,9% + IBS 0,1%, fase de teste 2026",
            confirmado_em_lei=True,
        ),
    }

    def buscar(self, fase: FaseTransicao) -> RegraFiscal:
        regra = self._REGRAS.get(fase)
        if regra is None:
            raise AliquotaNaoDisponivelError(fase)
        return regra
```

### Pattern 4: `TaxCalculatorEngine`

```python
# motor_calculo/engine.py

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from motor_calculo.fases import fase_para
from motor_calculo.tabela_aliquotas import TabelaAliquotas


@dataclass
class ResultadoCalculo:
    valor_base: Decimal
    valor_is: Decimal
    valor_cbs: Decimal
    valor_ibs: Decimal
    total_tributos: Decimal
    valor_liquido: Decimal
    fonte_legal: str


class TaxCalculatorEngine:
    def __init__(self, tabela: TabelaAliquotas):
        self._tabela = tabela

    def calcular(
        self,
        valor_base: Decimal,
        ano_operacao: int,
        split_payment_active: bool = True,
    ) -> ResultadoCalculo:
        if valor_base <= 0:
            raise ValueError("valor_base deve ser positivo")

        fase = fase_para(ano_operacao)
        regra = self._tabela.buscar(fase)

        valor_is = (valor_base * regra.aliq_is).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        base_iva = valor_base + valor_is
        valor_cbs = (base_iva * regra.aliq_cbs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valor_ibs = (base_iva * regra.aliq_ibs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_tributos = valor_cbs + valor_ibs + valor_is
        valor_liquido = valor_base - (total_tributos if split_payment_active else Decimal("0"))

        return ResultadoCalculo(
            valor_base=valor_base,
            valor_is=valor_is,
            valor_cbs=valor_cbs,
            valor_ibs=valor_ibs,
            total_tributos=total_tributos,
            valor_liquido=valor_liquido,
            fonte_legal=regra.fonte_legal,
        )
```

---

## Data Flow

```text
1. Chamador invoca TaxCalculatorEngine(tabela).calcular(valor_base, ano_operacao, split_payment_active)
   │
   ▼
2. Engine valida valor_base > 0
   │
   ▼
3. Engine resolve fase = fase_para(ano_operacao)
   │
   ▼
4. Engine busca regra = tabela.buscar(fase) — pode levantar AliquotaNaoDisponivelError
   │
   ▼
5. Engine aplica a fórmula (IS sobre a base; CBS+IBS sobre base+IS), Decimal + ROUND_HALF_UP
   │
   ▼
6. Engine monta ResultadoCalculo com valores + fonte_legal e retorna ao chamador
```

---

## Integration Points

Nenhum — o motor é standalone nesta feature (conforme Out of Scope do DEFINE), sem chamadas a GCP, Qdrant, Postgres ou APIs externas.

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `fase_para()` para 2026-2033 e limites inválidos | `tests/test_fases.py` | pytest | 100% das fronteiras de fase |
| Unit | `TabelaAliquotasSeed` — 2026 confirmado, demais levantam erro | `tests/test_tabela_aliquotas.py` | pytest | 100% das fases do Enum |
| Acceptance | AT-001, AT-002, AT-003 do DEFINE | `tests/test_engine.py` | pytest | 3/3 Acceptance Tests |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| Fase sem `RegraFiscal` confirmada | Levanta `AliquotaNaoDisponivelError` com mensagem explicando o que falta | No — o dado não existe, retry não resolve |
| `ano_operacao` anterior a 2026 | Levanta `ValueError` explícito em `fase_para()` | No |
| `valor_base` zero ou negativo | Levanta `ValueError` na entrada do `TaxCalculatorEngine.calcular()` | No |

---

## Configuration

Nenhuma configuração externa nesta feature — `TabelaAliquotasSeed` é hardcoded em código (única fonte é a fase 2026, confirmada em lei). Configuração de fonte de dados real fica para a feature futura que substituir o seed.

---

## Security Considerations

- Motor não tem I/O externo nem aceita input de rede diretamente — superfície de ataque nova é mínima
- Validação de `valor_base` (deve ser positivo) evita resultados numéricos sem sentido, não é uma questão de segurança tradicional, mas de correção
- Nenhuma credencial, segredo ou dado sensível envolvido nesta feature

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Não implementado nesta feature — motor é uma biblioteca pura; logging fica a cargo do chamador (ex.: futura API `/v1/tax/simulate`) |
| Metrics | N/A — sem infraestrutura de métricas nesta feature |
| Tracing | N/A — motor síncrono, sem chamadas externas a rastrear |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-22 | design-agent | Versão inicial, a partir de DEFINE_MOTOR_DETERMINISTICO_CALCULO.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_MOTOR_DETERMINISTICO_CALCULO.md`
