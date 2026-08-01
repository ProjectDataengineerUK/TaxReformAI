# DESIGN: Integração de CBS/IBS à Partilha do Simples Nacional (Anexos XVIII-XXIII)

> Regime tributário SUBSTITUTIVO — nunca uma redução sobre `engine.py`. Módulo novo, Python puro,
> sem infraestrutura, mais um endpoint DEDICADO (`POST /v1/tax/simulate-simples-nacional`),
> independente do `/v1/tax/simulate` do regime geral pela mesma razão estrutural que motivou o
> endpoint dedicado do Anexo XVI: o gate de fase de `/v1/tax/simulate` recusa (422) toda
> `ano_operacao` que esta feature precisa.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMPLES_NACIONAL_CBS_IBS_TRANSICAO |
| **Date** | 2026-08-01 |
| **Author** | design-agent |
| **Status** | ✅ Shipado 2026-08-01 (ver `SHIPPED_2026-08-01.md`) |

---

## Overview

```
POST /v1/tax/simulate-simples-nacional
        │
        ▼
┌─────────────────────────────┐        ┌───────────────────────────────┐
│ api/schemas_simples_        │        │ motor_calculo/                 │
│ nacional.py                 │◄──────►│ simples_nacional.py            │
│  PayloadSimplesNacional     │        │  Atividade (enum, 6 valores)   │
│  RespostaSimplesNacional    │        │  FaixaReceita / PartilhaPerc.  │
└─────────────────────────────┘        │  TetoIss / ValorFixoMei        │
        ▲                              │  calcular_simples_nacional()   │
        │                              │  calcular_mei()                │
┌─────────────────────────────┐        └───────────────────────────────┘
│ api/routers/simulate.py     │                    │
│  novo endpoint, mesmo       │                    │  Python puro,
│  router, MESMO padrão de    │                    │  sem I/O, sem banco
│  autenticação/audit log     │                    │  (mesma classe do
└─────────────────────────────┘                    │  Anexo XVI)
                                                     ▼
                                          6 Anexos (XVIII-XXIII) +
                                          fórmula do art. 18 da
                                          LC 123/2006, todos já
                                          verificados no /define
```

**Por que NÃO reaproveita `engine.py`/`TabelaAliquotasSeed`**: o Simples Nacional não reduz uma
alíquota do regime geral — ele SUBSTITUI IRPJ/CSLL/CBS/CPP/ICMS-ou-ISS/IBS por um DAS único,
calculado sobre uma base (receita bruta) e uma fórmula (art. 18, LC 123/2006) inteiramente
diferentes das do IVA Dual. Nenhuma linha de `motor_calculo/tabela_aliquotas.py` é lida.

---

## Key Decisions

### Decision 1: Endpoint DEDICADO, não campos novos em `/v1/tax/simulate`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O `/define` (Goal MUST) previa adicionar campos novos ao `PayloadSimulacao`/
`ItemSimulacao` existentes de `/v1/tax/simulate`. Lendo `api/routers/simulate.py` linha a linha
neste `/design`, descobriu-se um bloqueio estrutural que o `/define` não tinha verificado: as
primeiras linhas de `simular()` (depois da checagem de tenant) chamam `fase_para(payload.
ano_operacao)` e `tabela.buscar(fase)`, e devolvem **422** se `regra.tributos_indisponiveis()`
não for vazio. Por `CLAUDE.md` e `motor_calculo/tabela_aliquotas.py`, isso acontece para
**QUALQUER `ano_operacao` diferente de 2026** — 2027-2028 tem CBS indisponível (art. 347), 2029+
não tem nenhuma `RegraFiscal` cadastrada. Como o Simples Nacional só se aplica de 2027 em diante
(a integração de CBS/IBS começa em 2027 pelos Anexos XVIII-XXIII), **100% dos payloads desta
feature bateriam nesse 422 antes de qualquer branch condicional ser avaliado** — mesma classe
exata do achado real do `/build` de `ANEXO_XVI_PISO_ALIQUOTA_PROPRIA` (ver Decisão 4 daquele
DESIGN).

**Choice:** Endpoint novo, `POST /v1/tax/simulate-simples-nacional`, no MESMO router
(`api/routers/simulate.py`), com payload/resposta PRÓPRIOS (`api/schemas_simples_nacional.py`),
NUNCA passando por `fase_para`/`TabelaAliquotasSeed`/`engine.py`.

**Rationale:** Além do bloqueio estrutural, a FORMA da resposta do Simples Nacional não tem
correspondência real com `RespostaSimulacao`: não há CBS/IBS/IS por ITEM (o Simples tributa a
receita agregada, não por NCM), não há ICMS/ISS/PIS/COFINS separados (estão DENTRO do DAS único),
não há `reducao`/`imposto_seletivo` (Anexos que não se aplicam a optantes do Simples). Forçar os
dois formatos no mesmo modelo violaria a disciplina já estabelecida neste projeto de nunca ter um
campo que estruturalmente nunca é usado (`ImpostoSeletivoItem` sem campo de valor; `PisoAliquotaIbs`
sem alíquota absoluta) — aqui seriam DEZENAS de campos de `RespostaSimulacao` sempre nulos para
todo payload Simples Nacional.

**Alternatives Rejected:**
1. Campos novos em `PayloadSimulacao` (`itens`/`ItemSimulacao`), branch condicional dentro de
   `simular()` ANTES do gate de fase — rejeitada: mesmo pulando o gate, o corpo da função inteira
   (laço por item chamando `engine.calcular`, `resolver_reducao`, `resolver_item_nbs`,
   `resolver_imposto_seletivo`, `resolver_item` do IPI, `icms_interno`/`iss_faixa`/
   `TabelaPisCofins`) não se aplica a uma empresa Simples Nacional — seria necessário um segundo
   `if` gigante dentro do mesmo laço, tornando a função ilegível e testando dois regimes
   inteiramente diferentes na mesma superfície.
2. `RespostaSimulacao` com `Union`/campo genérico para acomodar os dois formatos — rejeitada:
   quebraria o contrato OpenAPI limpo que `response_model` hoje garante, e adicionaria uma
   ramificação de tipo que todo cliente da API precisaria tratar mesmo fora do fluxo Simples.

**Consequences:**
- Dois endpoints POST em `/v1/tax`, cada um servindo um regime mutuamente exclusivo — mesmo
  padrão de "um regime, um endpoint" que `GET /v1/tax/piso-aliquota-ibs/{ano}` já estabeleceu.
- O `/define` previa a mudança de contrato como a MAIOR de toda a leva por tocar `/v1/tax/
  simulate`; na prática a mudança é MENOR ali (zero campo novo no endpoint existente) e maior em
  superfície nova (2 arquivos, 1 endpoint), mas SEM nenhum risco de regressão no endpoint
  existente — trade-off aceito.
- Autenticação (`verificar_api_key`) e audit log (`registrar_com_seguranca`) são reaproveitados
  intactos — só a lógica de cálculo é nova.

---

### Decision 2: Payload usa `receita_bruta_mes` direto, sem lista de `itens`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O `/define` cogitava reaproveitar `itens: list[ItemSimulacao]` só para somar
`valor_bruto_total` como proxy da receita do mês (base de cálculo do art. 18, §3º).

**Choice:** Payload dedicado com `receita_bruta_mes: Decimal` direto — sem lista de itens, sem
NCM, sem SKU.

**Rationale:** O Simples Nacional tributa a RECEITA AGREGADA do mês, nunca por produto/serviço
individual (nenhum dos 6 Anexos referencia NCM/NBS). Exigir uma lista de `ItemSimulacao` só para
somar um valor seria pedir ao cliente para inventar SKUs/NCMs fictícios — cerimônia sem
propósito. Um campo escalar é mais simples, mais correto semanticamente, e evita qualquer
tentação futura de tentar cruzar NCM com os Anexos de redução (que não se aplicam aqui).

**Alternatives Rejected:**
1. Reaproveitar `itens: list[ItemSimulacao]` como o `/define` sugeria — rejeitada pela razão
   acima.

**Consequences:**
- Payload consideravelmente mais simples que `/v1/tax/simulate`.
- Cliente que já tem uma lista de itens (ex. vindo do mesmo ERP) precisa somar o total antes de
  chamar este endpoint — custo aceito, documentado na resposta (`nota`).

---

### Decision 3: Três caminhos de cálculo internos, não uma função universal

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O `/define` já apontava a possibilidade (Open Question 3, não bloqueante) entre uma
função universal com muitos parâmetros ou caminhos distintos.

**Choice:** Três funções internas dentro de `motor_calculo/simples_nacional.py`:
- `_calcular_percentual_simples(atividade, faixa_dados, rbt12, receita_mes, ano)` — Anexos
  XVIII, XIX, XXII (sem teto de ISS).
- `_calcular_percentual_com_teto_iss(atividade, faixa_dados, rbt12, receita_mes, ano)` — Anexos
  XX, XXI (com a cláusula de teto/redistribuição na 5ª Faixa).
- `calcular_mei(receita_mes, ano)` — Anexo XXIII (valores fixos, sem faixa, sem alíquota
  efetiva).

Uma função pública, `calcular_simples_nacional(atividade, rbt12, receita_mes, ano)`, despacha
para a função interna certa por `atividade`, e para MEI delega para `calcular_mei` (ignorando
`rbt12`, que não se aplica).

**Rationale:** Os três caminhos têm bases de cálculo estruturalmente diferentes (percentual sobre
alíquota efetiva; o mesmo mais uma cláusula condicional de teto; valor fixo em R$ sem nenhuma
alíquota). Uma função única faria os `if`s do teto de ISS e da ausência de alíquota do MEI
disputarem espaço com a lógica comum, prejudicando a legibilidade sem ganho real de reuso — os
dois caminhos "percentuais" já compartilham `calcular_aliquota_efetiva`/`buscar_faixa` como
funções auxiliares próprias.

**Alternatives Rejected:**
1. Uma função universal com flags (`tem_teto_iss: bool`, `eh_mei: bool`) — rejeitada por
   obscurecer qual caminho está de fato executando para qual Anexo.

**Consequences:**
- Mais funções, cada uma mais simples e testável isoladamente.
- `calcular_simples_nacional` é o único ponto de entrada público — o router nunca escolhe o
  caminho, só chama a função pública com a `atividade`.

---

### Decision 4: "Regime permanente" (2033+) não duplica linha por ano

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** As tabelas de partilha têm uma linha por ano de 2027 a 2032, e uma última tabela
"a partir de 2033" que NUNCA MAIS muda (confirmado no `/define`: nenhum dos 6 Anexos tem uma
linha para 2034, 2035 etc. — a de 2033 é, pelo próprio texto, permanente).

**Choice:** A tabela de partilha por Anexo é `dict[int, dict[int, PartilhaPercentual]]` — chave
externa é a FAIXA (1-6), chave interna é o ANO **ou o sentinela `2033`**, e a função de busca usa
`min(ano_operacao, 2033)` como chave de lookup — qualquer ano ≥ 2033 cai na mesma entrada.

**Rationale:** Evita duplicar a mesma tupla de percentuais 44 vezes (uma por ano até um horizonte
arbitrário) só para simular "permanência". `min(ano, 2033)` é uma linha, testável com um caso em
2033 e outro em, por exemplo, 2050, ambos batendo no mesmo dado.

**Consequences:**
- Nenhum limite superior de ano é imposto pela tabela em si (diferente do Anexo XVI, que tem
  janela fechada 2029-2077) — o Simples Nacional, uma vez em regime permanente, não tem uma data
  de expiração conhecida hoje. Validação de ano mínimo (< 2027) continua existindo (AT-011).

---

### Decision 5: 6ª Faixa declara `icms_iss_fora_do_das`, nunca omite silenciosamente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O `/define` deixou como Open Question por que a 6ª Faixa não tem ICMS/ISS/IBS na
partilha. Resolvido neste `/design`: LC 123/2006, art. 19, §4º — acima do "sublimite" de
R$3.600.000,00 (exatamente o piso da 6ª Faixa), ICMS e ISS (e por extensão IBS, seu substituto na
reforma) são recolhidos SEPARADAMENTE, fora do DAS, pelo regime geral.

**Choice:** `ResultadoSimplesNacional.icms_iss_fora_do_das: bool` — `True` sempre que a faixa
resolvida for a 6ª, declarado na resposta com o dispositivo (art. 19, §4º) citado.

**Rationale:** Mesma disciplina de todo o projeto: um valor ausente sem explicação parece um bug;
um booleano com dispositivo citado é a mesma informação, auditável.

**Consequences:**
- `partilha`/`valores_devidos` da resposta, na 6ª Faixa, contêm só IRPJ/CSLL/CBS/CPP (mais IPI
  para Indústria) — nunca uma entrada de ICMS/ISS/IBS com valor zero (que pareceria "não devido",
  quando na verdade é "devido fora deste cálculo").

---

## Achados adicionais desta sessão (não decisões arquiteturais, mas registrados)

Dois itens que o `/define` original não tinha capturado por completo foram fechados durante este
`/design`, com o texto já incorporado ao `DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`:

1. **Coeficientes de redistribuição do teto de ISS (Anexos XX/XXI) MUDAM todo ano** — o `/define`
   só tinha capturado 2027-2028; os anos 2029-2032 têm coeficientes PRÓPRIOS, agora transcritos
   por completo (10 conjuntos de coeficientes: 5 anos × 2 Anexos).
2. **Uma célula (Anexo XXI, 2029, Faixa 5) ficou ambígua** na extração `-layout` do PDF (colunas
   coladas visualmente) — resolvida re-extraindo a mesma página com `pdftotext -raw`, que
   preserva a ordem de leitura em vez de tentar reconstruir colunas. Técnica nova para este
   projeto (as features anteriores só precisaram de `-layout`); vale registrar para uso futuro
   quando `-layout` produzir ambiguidade em tabelas com células multi-linha.

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|--------------|
| 1 | `motor_calculo/simples_nacional.py` | Create | Módulo puro: `Atividade`, tabelas dos 6 Anexos, fórmula do art. 18, 3 caminhos de cálculo | Nenhuma |
| 2 | `api/schemas_simples_nacional.py` | Create | `PayloadSimplesNacional`, `RespostaSimplesNacional`, `ItemPartilhaSimplesNacional` | 1 |
| 3 | `api/routers/simulate.py` | Modify | Novo endpoint `POST /v1/tax/simulate-simples-nacional`, mesmo router | 1, 2 |
| 4 | `tests/test_simples_nacional.py` | Create | Testes unitários do módulo puro — os 6 Anexos, fórmula, teto de ISS, MEI, 6ª Faixa | 1 |
| 5 | `tests/test_api_simulate_simples_nacional.py` | Create | E2E via `TestClient` — AT-001 a AT-012 | 2, 3 |

**Sem migração, sem `db/`, sem `GRANT`, sem `.github/workflows/migrar_banco.yml`** — segunda
feature do projeto (depois do Anexo XVI) sem nenhuma superfície de infraestrutura. `deploy.yml`
ganha só UMA linha nova de smoke test no `/ship` (mesmo padrão de toda feature anterior),
independente de Cloud SQL.

---

## Code Patterns

### `motor_calculo/simples_nacional.py` — estrutura de dados

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

FONTE_FORMULA = "LC 123/2006, art. 18, §§1º, 1º-A e 1º-B (redação da LC 155/2016)"


class Atividade(StrEnum):
    COMERCIO = "COMERCIO"                        # Anexo XVIII → LC 123/2006, Anexo I
    INDUSTRIA = "INDUSTRIA"                       # Anexo XIX → Anexo II
    LOCACAO_SERVICO_GERAL = "LOCACAO_SERVICO_GERAL"  # Anexo XX → Anexo III (teto ISS)
    SERVICO_PAR_5C = "SERVICO_PAR_5C"             # Anexo XXI → Anexo IV (sem CPP, teto ISS)
    SERVICO_PAR_5I = "SERVICO_PAR_5I"             # Anexo XXII → Anexo V
    MEI = "MEI"                                   # Anexo XXIII → Anexo VII (valor fixo)


@dataclass(frozen=True)
class FaixaReceita:
    faixa: int  # 1-6
    limite_inferior: Decimal
    limite_superior: Decimal | None  # None só teoricamente; as 6 faixas são sempre limitadas
    aliquota_nominal: Decimal
    valor_deduzir: Decimal


@dataclass(frozen=True)
class PartilhaPercentual:
    irpj: Decimal
    csll: Decimal
    cbs: Decimal
    cpp: Decimal | None    # None só para SERVICO_PAR_5C (Anexo XXI)
    icms: Decimal | None   # só COMERCIO/INDUSTRIA, faixas 1-5
    iss: Decimal | None    # só Anexos de serviço, faixas 1-5
    ibs: Decimal | None    # faixas 1-5; None na 6ª (Decisão 5)
    ipi: Decimal | None    # só INDUSTRIA


@dataclass(frozen=True)
class TetoIss:
    gatilho_aliquota_efetiva: Decimal  # > este valor aciona a redistribuição
    limite_percentual: Decimal          # ISS fica fixo neste valor
    coef_irpj: Decimal
    coef_csll: Decimal
    coef_cbs: Decimal
    coef_cpp: Decimal | None  # None para SERVICO_PAR_5C
    coef_ibs: Decimal


@dataclass(frozen=True)
class ValorFixoMei:
    icms: Decimal | None  # None a partir de 2033 (Decisão de fonte: só CBS+IBS)
    iss: Decimal | None
    cbs: Decimal
    ibs: Decimal


@dataclass(frozen=True)
class ResultadoSimplesNacional:
    atividade: Atividade
    ano_operacao: int
    faixa: int | None                    # None só para MEI
    aliquota_nominal: Decimal | None     # None só para MEI
    valor_deduzir: Decimal | None
    aliquota_efetiva: Decimal | None     # None só para MEI
    receita_bruta_acumulada_12_meses: Decimal | None
    receita_bruta_mes: Decimal
    partilha_percentual: dict[str, Decimal]  # tributo -> percentual efetivo (vazio p/ MEI)
    valores_devidos: dict[str, Decimal]      # tributo -> R$ devido no mês
    valor_total_das: Decimal
    teto_iss_aplicado: bool
    icms_iss_fora_do_das: bool  # True só na 6ª Faixa (Decisão 5)
    dispositivo_legal_ref: str
```

### Fórmula do art. 18 (Decisão de fonte primária do `/define`)

```python
def calcular_aliquota_efetiva(
    rbt12: Decimal, aliquota_nominal: Decimal, valor_deduzir: Decimal
) -> Decimal:
    """LC 123/2006, art. 18, §1º-A: (RBT12 × Aliq − PD) / RBT12.

    Divisão por RBT12 confirmada via inspeção do HTML bruto de planalto.gov.br
    (formatação de fração — numerador sublinhado, denominador na mesma célula)
    — ver DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md.
    """
    return (rbt12 * aliquota_nominal - valor_deduzir) / rbt12


def calcular_percentual_por_tributo(
    aliquota_efetiva: Decimal, percentual_reparticao: Decimal
) -> Decimal:
    """LC 123/2006, art. 18, §1º-B: percentual efetivo do tributo = alíquota
    efetiva × percentual de repartição do Anexo."""
    return aliquota_efetiva * percentual_reparticao
```

### Teto de ISS (Anexos XX/XXI, 5ª Faixa) — exemplo de uma entrada

```python
# Anexo XX (LOCACAO_SERVICO_GERAL), 5ª Faixa, por ano — coeficientes verificados
# linha a linha contra o PDF, MUDAM todo ano (achado deste /design, ver acima).
_TETO_ISS_XX: dict[int, TetoIss] = {
    2027: TetoIss(
        gatilho_aliquota_efetiva=Decimal("0.1492537"),
        limite_percentual=Decimal("0.05"),
        coef_irpj=Decimal("0.0602"), coef_csll=Decimal("0.0526"),
        coef_cbs=Decimal("0.2320"), coef_cpp=Decimal("0.6526"),
        coef_ibs=Decimal("0.0026"),
    ),
    # 2028 idêntico a 2027 (mesma vigência "1º/1/2027 a 31/12/2028")
    2028: ...,  # = 2027
    2029: TetoIss(
        gatilho_aliquota_efetiva=Decimal("0.1492537"),
        limite_percentual=Decimal("0.045"),
        coef_irpj=Decimal("0.0573"), coef_csll=Decimal("0.0501"),
        coef_cbs=Decimal("0.2233"), coef_cpp=Decimal("0.6213"),
        coef_ibs=Decimal("0.0480"),
    ),
    # 2030, 2031, 2032 — mesma estrutura, coeficientes já verificados no /define
    # 2033+ não tem teto (tabela permanente não inclui ISS)
}
```

### Despacho público

```python
def calcular_simples_nacional(
    atividade: Atividade,
    receita_bruta_acumulada_12_meses: Decimal | None,
    receita_bruta_mes: Decimal,
    ano_operacao: int,
) -> ResultadoSimplesNacional:
    if atividade is Atividade.MEI:
        return calcular_mei(receita_bruta_mes, ano_operacao)
    if receita_bruta_acumulada_12_meses is None:
        raise ValueError(
            "receita_bruta_acumulada_12_meses é obrigatória para toda atividade "
            "exceto MEI — sem ela não há como determinar a faixa"
        )
    if atividade in (Atividade.LOCACAO_SERVICO_GERAL, Atividade.SERVICO_PAR_5C):
        return _calcular_percentual_com_teto_iss(
            atividade, receita_bruta_acumulada_12_meses, receita_bruta_mes, ano_operacao
        )
    return _calcular_percentual_simples(
        atividade, receita_bruta_acumulada_12_meses, receita_bruta_mes, ano_operacao
    )
```

### `api/schemas_simples_nacional.py`

```python
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class AtividadeSimplesNacional(StrEnum):
    COMERCIO = "COMERCIO"
    INDUSTRIA = "INDUSTRIA"
    LOCACAO_SERVICO_GERAL = "LOCACAO_SERVICO_GERAL"
    SERVICO_PAR_5C = "SERVICO_PAR_5C"
    SERVICO_PAR_5I = "SERVICO_PAR_5I"
    MEI = "MEI"


class PayloadSimplesNacional(BaseModel):
    tenant_id: str
    ano_operacao: int
    atividade: AtividadeSimplesNacional
    # Obrigatória para toda atividade exceto MEI (validado no router, não no
    # schema — Pydantic não expressa "obrigatório condicional a outro campo"
    # sem um validator; a mensagem de erro do router é mais específica que a
    # de um validator genérico).
    receita_bruta_acumulada_12_meses: Decimal | None = Field(default=None, gt=0)
    receita_bruta_mes: Decimal = Field(gt=0)


class ItemPartilhaSimplesNacional(BaseModel):
    tributo: str  # "IRPJ" | "CSLL" | "CBS" | "CPP" | "ICMS" | "ISS" | "IBS" | "IPI"
    percentual_efetivo: Decimal | None = None  # None só para MEI
    valor_devido: Decimal


class RespostaSimplesNacional(BaseModel):
    status: str = "SUCCESS"
    ano_operacao: int
    atividade: str
    faixa: int | None = None
    receita_bruta_acumulada_12_meses: Decimal | None = None
    receita_bruta_mes: Decimal
    aliquota_nominal: Decimal | None = None
    valor_deduzir: Decimal | None = None
    aliquota_efetiva: Decimal | None = None
    partilha: list[ItemPartilhaSimplesNacional]
    valor_total_das: Decimal
    teto_iss_aplicado: bool
    icms_iss_fora_do_das: bool
    dispositivo_legal_ref: str
    nota: str = (
        "O Simples Nacional é um regime SUBSTITUTIVO — este DAS unificado "
        "substitui IRPJ/CSLL/CBS/CPP/ICMS-ou-ISS/IBS, nunca se soma a "
        "eles. A opção pelo Simples e a atividade informada são "
        "DECLARATÓRIAS: esta simulação não verifica elegibilidade "
        "(atividade permitida, sublimites, impedimentos dos arts. 3º/17 "
        "da LC 123/2006)."
    )
```

### `api/routers/simulate.py` — novo endpoint

```python
from api.schemas_simples_nacional import (
    ItemPartilhaSimplesNacional,
    PayloadSimplesNacional,
    RespostaSimplesNacional,
)
from motor_calculo.simples_nacional import Atividade, calcular_simples_nacional


@router.post("/simulate-simples-nacional", response_model=RespostaSimplesNacional)
def simular_simples_nacional(
    payload: PayloadSimplesNacional,
    tenant_id: str = Depends(verificar_api_key),
    db_pool=Depends(get_db_pool),
) -> RespostaSimplesNacional:
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id do payload não corresponde à credencial autenticada",
        )
    if payload.ano_operacao < 2027:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "A integração de CBS/IBS à partilha do Simples Nacional "
                "(LCP 214/2025, Anexos XVIII-XXIII) só vale a partir de "
                f"2027 — {payload.ano_operacao} está fora dessa janela."
            ),
        )
    atividade = Atividade(payload.atividade.value)
    if atividade is not Atividade.MEI and payload.receita_bruta_acumulada_12_meses is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="receita_bruta_acumulada_12_meses é obrigatória para toda "
            "atividade exceto MEI.",
        )

    resultado = calcular_simples_nacional(
        atividade,
        payload.receita_bruta_acumulada_12_meses,
        payload.receita_bruta_mes,
        payload.ano_operacao,
    )

    resposta = RespostaSimplesNacional(
        ano_operacao=resultado.ano_operacao,
        atividade=resultado.atividade.value,
        faixa=resultado.faixa,
        receita_bruta_acumulada_12_meses=resultado.receita_bruta_acumulada_12_meses,
        receita_bruta_mes=resultado.receita_bruta_mes,
        aliquota_nominal=resultado.aliquota_nominal,
        valor_deduzir=resultado.valor_deduzir,
        aliquota_efetiva=resultado.aliquota_efetiva,
        partilha=[
            ItemPartilhaSimplesNacional(
                tributo=tributo,
                percentual_efetivo=resultado.partilha_percentual.get(tributo),
                valor_devido=valor,
            )
            for tributo, valor in resultado.valores_devidos.items()
        ],
        valor_total_das=resultado.valor_total_das,
        teto_iss_aplicado=resultado.teto_iss_aplicado,
        icms_iss_fora_do_das=resultado.icms_iss_fora_do_das,
        dispositivo_legal_ref=resultado.dispositivo_legal_ref,
    )

    registrar_com_seguranca(
        db_pool,
        tenant_id,
        prompt_consulta=(
            f"POST /v1/tax/simulate-simples-nacional ano={payload.ano_operacao} "
            f"atividade={payload.atividade} receita_mes={payload.receita_bruta_mes}"
        ),
        resposta_parecer_md=(
            f"DAS total: {resultado.valor_total_das} "
            f"(faixa={resultado.faixa}, alíquota efetiva="
            f"{resultado.aliquota_efetiva})."
        ),
        payload_calculo=payload.model_dump(mode="json"),
    )

    return resposta
```

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `motor_calculo/simples_nacional.py` — os 6 Anexos, fórmula do art. 18, teto de ISS (com e sem gatilho), MEI (inclusive 2033+ sem ICMS/ISS), 6ª Faixa (`icms_iss_fora_do_das=True`), regime permanente (2033 == 2050) | `pytest` |
| Integration/E2E | `POST /v1/tax/simulate-simples-nacional` via `TestClient` — AT-001 a AT-012 do DEFINE | `pytest` + `TestClient` |
| Regression | Nenhuma mudança em `api/routers/simulate.py` fora da adição do novo endpoint — suíte completa (519 testes) deve permanecer verde | `pytest` |

**Fonte única de verdade para os valores de teste**: os números literais do
`DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md` (já verificados contra fonte primária) — os testes
NÃO duplicam uma segunda transcrição independente, para não criar "duas fontes de verdade" que
possam divergir silenciosamente (mesma disciplina já usada nos testes de Anexo que fazem parsing
de migração SQL; aqui, sem migração, o DEFINE É a fonte).

---

## Quality Gate

```text
[x] Arquitetura clara — endpoint dedicado, módulo puro, sem infraestrutura
[x] Decisões documentadas com rationale (5 decisões inline)
[x] File manifest completo
[x] Padrões de código prontos para copiar
[x] Estratégia de teste cobre os 12 acceptance tests do DEFINE
[x] Sem dependência circular — módulo novo não importa `engine.py`/`tabela_aliquotas.py`
```

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`
