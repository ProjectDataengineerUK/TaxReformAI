# DESIGN: Anexo XVI — Piso da Alíquota Própria de Estados e Municípios

> Technical design for implementing ANEXO_XVI_PISO_ALIQUOTA_PROPRIA (posição 15/17 do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVI_PISO_ALIQUOTA_PROPRIA |
| **Date** | 2026-07-31 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md](./DEFINE_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md) |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│         /v1/tax/simulate — bloco informativo NOVO, nível de REQUISIÇÃO   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  PayloadSimulacao.ano_operacao (JÁ EXISTE — nenhum campo novo no input)  │
│         │                                                                 │
│         ▼                                                                 │
│  motor_calculo/piso_aliquota_ibs.py :: piso_aliquota_ibs(ano)             │
│    ├─ ano em [2029, 2077]  → PisoAliquotaIbs(percentual, dispositivo)     │
│    └─ ano fora da janela   → None ("não se aplica", nunca omitido em     │
│                               silêncio nem confundido com "não fixado")   │
│         │                                                                 │
│         ▼                                                                 │
│  api/routers/simulate.py :: monta RespostaSimulacao.piso_aliquota_ibs     │
│         │                                                                 │
│         ▼                                                                 │
│  RespostaSimulacao (schemas_simulate.py) — campo ADITIVO, sem tocar       │
│  nenhum bloco existente (reducao, regime_vigente, escopo, ...)            │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘

   ZERO infraestrutura: sem migração, sem tabela no Cloud SQL, sem GRANT,
   sem consulta de banco — a MESMA razão pela qual regime_atual.py
   (PIS/COFINS, ICMS, ISS) também é Python puro (Decisão 1 abaixo).
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `motor_calculo/piso_aliquota_ibs.py` | Tabela de 49 anos (2029-2077) + `piso_aliquota_ibs(ano)` | Python puro, sem I/O — mesmo padrão de `regime_atual.py`/`tabela_aliquotas.py` |
| `api/schemas_simulate.py` (extensão) | Novo model `PisoAliquotaIbs` + campo `RespostaSimulacao.piso_aliquota_ibs` | Pydantic v2 |
| `api/routers/simulate.py` (extensão) | Popula o campo a partir de `payload.ano_operacao` — nenhuma mudança no laço por item | FastAPI |

Nenhuma migração, nenhuma tabela nova no Cloud SQL, nenhum script de verificação de produção —
primeira feature do projeto sem NENHUMA superfície de infraestrutura (ver Decisão 1).

---

## Key Decisions

### Decisão 1: Python puro em `motor_calculo/`, nunca uma tabela SQL

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` deixou em aberto (Open Question 1) se as 49 linhas do Anexo XVI deveriam
viver em Python puro ou numa migração SQL — todas as 6 features anteriores desta leva usaram
Cloud SQL, mas nenhuma delas tinha um dado tão simples (uma chave, um valor, sem correspondência
por prefixo, sem condição declaratória, sem junção).

**Choice:** `motor_calculo/piso_aliquota_ibs.py`, um dicionário `{ano: Decimal}` de 49 entradas,
no mesmo estilo de `_TABELA_ICMS_INTERNO` (27 UFs) já usada em `regime_atual.py`.

**Rationale:** O dado é lei promulgada e IMUTÁVEL — o art. 371 não tem cláusula de revisão
periódica (diferente dos Anexos IV/V/VI/IX, revisados a cada 120 dias por ato conjunto), e a
tabela não cresce nem muda por operação do tenant. `regime_atual.py` já estabelece o precedente
de "tabela pequena, estática, citável por artigo, sem I/O" para exatamente esta classe de dado
(a tabela de 27 UFs do ICMS interno é maior que as 49 linhas deste Anexo, e vive em Python há
duas features sem problema). Colocar isso em SQL exigiria uma migração, um `GRANT`, uma consulta,
um script de verificação de produção — toda a superfície de risco que a Decisão do `/define`
(MUST: `motor_calculo/` sem infraestrutura nova) já rejeita.

**Alternatives Rejected:**
1. Migração SQL própria (`piso_aliquota_ibs` tabela, 49 linhas) — rejeitada: replicaria a
   superfície de risco das 6 features anteriores (GRANT faltando degradando silenciosamente,
   necessidade de script de verificação contra Cloud SQL real) para um dado que nunca muda e não
   tem chave de tenant nem de produto.
2. Reaproveitar `TabelaAliquotasSeed`/`RegraFiscal` (`motor_calculo/tabela_aliquotas.py`) —
   rejeitada: aquele módulo é indexado por `FaseTransicao` (2026/2027-28/2029-32/2033+), um
   agrupamento de 4 fases, não por ano individual — o Anexo XVI muda TODO ANO dentro da fase
   `REGIME_PLENO_2033` (que hoje cobre 2033 em diante como um bloco só). Forçar o piso dentro
   dessa estrutura exigiria quebrar `FaseTransicao` em 49 sub-fases, uma mudança muito maior que
   o problema pede.

**Consequences:**
- Sem migração significa sem a classe inteira de riscos das 6 features anteriores (rename de
  tabela em uso, GRANT nunca exercitado, degradação silenciosa) — mas também sem uma CHECK
  constraint de banco garantindo a integridade da tabela. Aceitável porque o dado nunca é escrito
  em runtime (é uma constante do módulo, não um seed carregado por migração) — o próprio código
  Python É a fonte de verdade, testada por `tests/test_piso_aliquota_ibs.py`.
- Nenhum script `verificar_*_producao.py` é necessário — não há papel de runtime a testar, não há
  GRANT a esquecer.

---

### Decisão 2: Bloco informativo a nível de REQUISIÇÃO, campo `RespostaSimulacao.piso_aliquota_ibs`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` já tinha decidido (MUST) que o dado é indexado só por `ano_operacao`,
nunca por item — o art. 371 não menciona produto, serviço, NCM nem NBS. Restava decidir a FORMA
exata do campo na resposta.

**Choice:** Um novo campo opcional em `RespostaSimulacao`, `piso_aliquota_ibs:
PisoAliquotaIbs | None`, populado UMA VEZ por requisição (não por item), a partir só de
`payload.ano_operacao` — nunca lido dentro do laço `for item in payload.itens`.

**Rationale:** Todo campo de `RespostaSimulacao` hoje que não é por item (`escopo`,
`compensacao`, `regime_vigente`) já segue este padrão — um bloco resumo a nível de requisição. O
Anexo XVI se encaixa exatamente nessa categoria, sem precisar de nenhuma estrutura nova.
`None` quando o ano está fora de [2029, 2077] seque a MESMA convenção que `regra_pis_cofins`
(`None` quando `regime_apuracao` não foi informado) — ausência de dado aplicável, não erro.

**Alternatives Rejected:**
1. Endpoint dedicado (`GET /v1/tax/piso-aliquota-propria?ano=N`, Approach B do brainstorm) —
   rejeitada no próprio `/define`: menos descoberta, rota nova para um dado que cabe como campo
   aditivo.
2. Repetir o piso em CADA `ItemDetalhado` — rejeitada: o dado não varia por item (não tem NCM,
   NBS, nem natureza), repeti-lo por item sugeriria falsamente uma dependência de item que não
   existe, e infla o payload sem necessidade.

**Consequences:**
- Zero mudança no laço principal do router — o campo é calculado uma vez, fora do `for item in
  payload.itens`, ao lado de `escopo`/`compensacao`.
- Clientes que já consomem `/v1/tax/simulate` não quebram: o campo é aditivo (Pydantic permite
  campo novo opcional sem exigir nada do cliente).

---

### Decisão 3: `piso_aliquota_ibs()` nunca calcula uma alíquota absoluta — só o percentual e a citação

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` já identificou (MUST, Achado 4 da verificação de fonte primária) que o
percentual do Anexo XVI multiplica uma "alíquota de referência da respectiva esfera federativa"
que é uma grandeza CALCULADA a partir de execução fiscal real (art. 370), nunca um valor de lei.
Um `/design` ingênuo poderia tentar "ajudar" combinando o percentual com alguma alíquota já
calculada em `regime_atual.py` ou `tabela_aliquotas.py` (ex. a alíquota de IBS da fase) — o que
seria uma invenção: nenhuma dessas alíquotas É a "alíquota de referência por esfera federativa"
do art. 371 (que é por ESTADO/MUNICÍPIO, não nacional).

**Choice:** `PisoAliquotaIbs` (o model de resposta) expõe SÓ `ano_operacao`,
`limite_inferior_percentual` (ex. `81.0`, `90.5`, `6.9`) e `dispositivo_legal_ref` — mais um campo
`nota` fixo explicando que o percentual multiplica uma alíquota de referência que este projeto não
calcula. Nenhum campo de "alíquota mínima absoluta" existe no model, por desenho — não é um campo
que fica `None`, é um campo que NÃO EXISTE, para que nenhuma versão futura do código o preencha
por engano com uma alíquota que não é a certa.

**Rationale:** Mesma disciplina de "nunca estimar" já aplicada ao art. 347 (CBS de referência
2027-2028, `AliquotaNaoDisponivelError`) — mas aqui a resposta correta não é "recusar a
requisição" (o piso do Anexo XVI é conhecido e útil por si só), é "nunca fingir que o cálculo
seguinte também está disponível". Omitir o campo por completo (em vez de modelá-lo como sempre
`None`) é o que impede um futuro desenvolvedor de "só preencher aquele None" com a alíquota da
fase por engano.

**Alternatives Rejected:**
1. Adicionar um campo `alíquota_minima_absoluta: Decimal | None = None`, sempre `None` por agora
   — rejeitada: um campo que existe e é sempre `None` convida alguém a preenchê-lo mais tarde com
   o primeiro `Decimal` que pareça plausível (ex. a alíquota do IBS da fase, que não é a alíquota
   de referência por esfera federativa). Não ter o campo é a garantia mais forte.

**Consequences:**
- Se um dia a alíquota de referência por esfera federativa se tornar calculável (Assunção A-002
  do `/define` — ex. se o CGIBS publicar esse valor), esta feature precisará de uma extensão
  explícita (campo novo, decisão consciente), nunca de "descongelar" um campo já existente.

---

### Decisão 4: Endpoint dedicado `GET /v1/tax/piso-aliquota-ibs/{ano_operacao}` — achado do `/build`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** Durante o `/build`, verificar `RespostaSimulacao.piso_aliquota_ibs` contra o endpoint
real revelou um fato que nem o `/define` nem as Decisões 1-3 deste `/design` tinham checado
executando código: **`/v1/tax/simulate` já devolve 422 para QUALQUER `ano_operacao >= 2027`** —
`TabelaAliquotasSeed` não tem `RegraFiscal` para as fases `TRANSICAO_ICMS_ISS_2029_2032` e
`REGIME_PLENO_2033` (2029 em diante — nem a fase existe na tabela), e mesmo `PLENO_CBS_IS_2027`
(2027-2028) é recusada por `regra.tributos_indisponiveis()` porque CBS/IS não têm alíquota de
referência fixada (art. 347 ainda pendente). Na prática, **2026 é o único ano em que `/v1/tax/
simulate` responde 200 hoje**. Como o Anexo XVI só se aplica de 2029 a 2077, a interseção entre
"anos em que `/v1/tax/simulate` funciona" e "anos em que o piso existe" é o CONJUNTO VAZIO — o
campo `piso_aliquota_ibs` da Decisão 2, embora corretamente implementado, nunca apareceria em
NENHUMA resposta de sucesso real hoje.

**Choice:** Adicionar `GET /v1/tax/piso-aliquota-ibs/{ano_operacao}`, um endpoint que chama só
`piso_aliquota_ibs(ano)` — sem tocar `TabelaAliquotasSeed`, `TaxCalculatorEngine` nem nenhuma parte
do motor de cálculo do IVA Dual. Devolve 200 sempre (nunca 422): `aplicavel=true/false` substitui
o padrão de erro, porque "ano fora da janela do art. 371" não é uma falha de requisição, é uma
resposta válida sobre o próprio dado. O campo `RespostaSimulacao.piso_aliquota_ibs` da Decisão 2 é
MANTIDO (não removido) — o código está correto e é forward-compatible: no dia em que o "achado 12"
desbloquear CBS/IS para 2027+, o campo começa a aparecer sem nenhuma mudança de código.

**Rationale:** O `/define` já tinha decidido (Out of Scope) que um endpoint dedicado era
complexidade desnecessária — mas esse raciocínio partia da premissa de que o campo embutido seria
ALCANÇÁVEL, o que a execução real provou falso. Manter só a Decisão 2 entregaria "código
correto, porém inútil hoje" — o Problem Statement do `/define` (dar visibilidade ao usuário sobre
este piso legal) fica sem solução real enquanto o achado 12 não for desbloqueado, o que pode
nunca acontecer neste projeto (ver Constraint do `/define`: bloqueio estrutural, não temporário).
Um endpoint de ~20 linhas que reaproveita a MESMA função pura já escrita (`piso_aliquota_ibs`) é o
menor incremento possível para fechar essa lacuna sem esperar por uma feature futura inteira.

**Alternatives Rejected:**
1. Manter só o campo embutido, aceitando que é inalcançável até o achado 12 — rejeitada: não cumpre
   o Problem Statement do `/define`, que pede visibilidade REAL, não uma garantia teórica para o
   futuro.
2. Remover o campo `piso_aliquota_ibs` de `RespostaSimulacao` e ficar só com o endpoint — rejeitada:
   o campo já está correto e testado, é forward-compatible de graça, e sua presença documenta a
   intenção de longo prazo (quando 2027+ for calculável, o piso aparece junto automaticamente).
   Removê-lo seria trabalho descartável.
3. Relaxar `regra.tributos_indisponiveis()` para permitir simular parcialmente em 2027+ mesmo sem
   CBS/IS — rejeitada com veemência: mudaria o comportamento de OUTRA feature (o motor determinístico
   já shipado) para acomodar esta, violando a disciplina central do projeto ("nunca estimar"); o
   bloqueio de `/v1/tax/simulate` para esses anos é uma decisão correta e deliberada de features
   anteriores, não um bug a corrigir aqui.

**Consequences:**
- Duas formas de acessar o mesmo dado (campo embutido + endpoint) — aceitável porque servem
  propósitos temporais diferentes: o endpoint é o que funciona HOJE; o campo é o que funciona
  quando o resto do simulador alcançar 2029+.
- `PisoAliquotaIbsConsulta` (novo model) precisa ser uma forma ligeiramente diferente de
  `PisoAliquotaIbs` (o model embutido): o endpoint precisa expressar "não aplicável" (200 +
  `aplicavel=false`) onde o campo embutido usa `None` — formas de modelar a MESMA ausência que
  fazem sentido em contextos diferentes (corpo sempre presente vs. campo opcional).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `motor_calculo/piso_aliquota_ibs.py` | Create | Tabela de 49 anos (2029-2077) + `piso_aliquota_ibs(ano)` (Decisão 1) | @python-developer | None |
| 2 | `api/schemas_simulate.py` | Modify | Novo model `PisoAliquotaIbs` + campo `RespostaSimulacao.piso_aliquota_ibs` (Decisões 2, 3); novo model `PisoAliquotaIbsConsulta` (Decisão 4) | @python-developer | 1 |
| 3 | `api/routers/simulate.py` | Modify | Popula o campo uma vez por requisição, fora do laço por item; novo endpoint `GET /piso-aliquota-ibs/{ano_operacao}` (Decisão 4) | @python-developer | 1, 2 |
| 4 | `tests/test_piso_aliquota_ibs.py` | Create | Unit tests da tabela/lookup — AT-001, AT-002, AT-003, AT-004, AT-005, AT-008 | @test-generator | 1 |
| 5 | `tests/test_api_simulate_piso.py` | Create | E2E via `TestClient` — confirma que `/v1/tax/simulate` 422 para 2027+ (achado da Decisão 4) e que o campo é aditivo/None nos anos alcançáveis | @test-generator | 2, 3 |
| 6 | `tests/test_api_piso_aliquota_ibs.py` | Create | E2E do endpoint dedicado — AT-001 a AT-005 de ponta a ponta, incluindo prova de que não depende do motor de cálculo | @test-generator | 2, 3 |

**Total Files:** 6 (nenhuma migração, nenhum script de verificação de produção, nenhuma mudança em workflow)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3 | Python puro (dataclasses, type hints) — mesmo agente usado em `regime_atual.py`/`fases.py` |
| @test-generator | 4, 5 | Testes pytest (unit + E2E), padrão já estabelecido pelas 6 features anteriores |

Não há linha para @database-reviewer nem @ci-cd-specialist nesta feature — primeira da leva sem
nenhuma superfície de banco ou workflow a tocar (consequência direta da Decisão 1).

---

## Code Patterns

### Pattern 1: `motor_calculo/piso_aliquota_ibs.py` — tabela e lookup

```python
"""Piso da alíquota própria de Estados/Municípios para o IBS (LCP 214/2025,
art. 371, Anexo XVI) — de 2029 a 2077, o percentual mínimo (em proporção da
alíquota de referência da respectiva esfera federativa) que um ente pode
fixar para sua fatia do IBS.

Vive aqui, não em `tabela_aliquotas.py` (indexado por `FaseTransicao`, um
agrupamento de 4 fases): o Anexo XVI muda TODO ANO dentro do que hoje é uma
única fase (`REGIME_PLENO_2033`, 2033 em diante) — encaixá-lo ali quebraria
`FaseTransicao` em 49 sub-fases por um problema que não pede isso.

NÃO calcula nenhuma alíquota absoluta: o percentual multiplica a "alíquota
de referência da respectiva esfera federativa" (art. 371, §1º), uma
grandeza CALCULADA a partir de execução fiscal real (art. 370) que este
projeto não ingere e não tem como ingerir — mesma classe de limitação já
aceita para ICMS interno/ISS ("não existe agregador federal"). Por isso
`PisoAliquotaIbs` não tem nenhum campo de alíquota absoluta, por desenho:
ver Decisão 3 do DESIGN.
"""

from dataclasses import dataclass
from decimal import Decimal

FONTE_LEGAL = "LCP 214/2025, art. 371, §1º, Anexo XVI"

# 49 entradas, 2029-2077, lidas e conferidas contra DUAS fontes independentes
# (Senado + Câmara dos Deputados) no /define. Chave é o ANO, não a UF/Município
# — o percentual é nacional e uniforme; só a alíquota de referência que ele
# multiplica varia por esfera federativa (e essa não está aqui, ver acima).
_TABELA_PISO: dict[int, Decimal] = {
    2029: Decimal("81.0"), 2030: Decimal("81.0"), 2031: Decimal("81.0"),
    2032: Decimal("81.0"), 2033: Decimal("90.5"), 2034: Decimal("88.6"),
    2035: Decimal("86.7"), 2036: Decimal("84.8"), 2037: Decimal("82.9"),
    2038: Decimal("81.0"), 2039: Decimal("79.1"), 2040: Decimal("77.2"),
    2041: Decimal("75.3"), 2042: Decimal("73.4"), 2043: Decimal("71.5"),
    2044: Decimal("69.6"), 2045: Decimal("67.7"), 2046: Decimal("65.8"),
    2047: Decimal("63.9"), 2048: Decimal("62.0"), 2049: Decimal("60.1"),
    2050: Decimal("58.2"), 2051: Decimal("56.3"), 2052: Decimal("54.4"),
    2053: Decimal("52.5"), 2054: Decimal("50.6"), 2055: Decimal("48.7"),
    2056: Decimal("46.8"), 2057: Decimal("44.9"), 2058: Decimal("43.0"),
    2059: Decimal("41.1"), 2060: Decimal("39.2"), 2061: Decimal("37.3"),
    2062: Decimal("35.4"), 2063: Decimal("33.5"), 2064: Decimal("31.6"),
    2065: Decimal("29.7"), 2066: Decimal("27.8"), 2067: Decimal("25.9"),
    2068: Decimal("24.0"), 2069: Decimal("22.1"), 2070: Decimal("20.2"),
    2071: Decimal("18.3"), 2072: Decimal("16.4"), 2073: Decimal("14.5"),
    2074: Decimal("12.6"), 2075: Decimal("10.7"), 2076: Decimal("8.8"),
    2077: Decimal("6.9"),
}


@dataclass(frozen=True)
class PisoAliquotaIbs:
    ano_operacao: int
    limite_inferior_percentual: Decimal
    dispositivo_legal_ref: str


def piso_aliquota_ibs(ano: int) -> PisoAliquotaIbs | None:
    """None fora de [2029, 2077] — o art. 371 delimita essa janela no caput
    ("De 2029 a 2077"), então fora dela o regime deste piso simplesmente NÃO
    VIGORA (não é "não encontrado": é "não se aplica a este ano")."""
    percentual = _TABELA_PISO.get(ano)
    if percentual is None:
        return None
    return PisoAliquotaIbs(
        ano_operacao=ano,
        limite_inferior_percentual=percentual,
        dispositivo_legal_ref=FONTE_LEGAL,
    )
```

### Pattern 2: Extensão de `api/schemas_simulate.py`

```python
class PisoAliquotaIbs(BaseModel):
    """Piso do art. 371/Anexo XVI — NUNCA uma alíquota absoluta (Decisão 3 do
    DESIGN). `limite_inferior_percentual` é a fração da alíquota de
    referência da esfera federativa que o ente não pode fixar abaixo dela;
    essa alíquota de referência em si não é calculada por este projeto."""

    ano_operacao: int
    limite_inferior_percentual: Decimal
    dispositivo_legal_ref: str
    nota: str = (
        "Este percentual multiplica a alíquota de referência do IBS da "
        "respectiva esfera federativa (Estado, Distrito Federal ou "
        "Município) — uma grandeza calculada a partir de execução fiscal "
        "real (LCP 214/2025, art. 370), que este simulador NÃO calcula. "
        "Este campo não produz nenhuma alíquota mínima absoluta."
    )


class RespostaSimulacao(BaseModel):
    # ... campos existentes intocados ...
    # None quando ano_operacao está fora de [2029, 2077] — o regime do art.
    # 371 simplesmente não vigora fora dessa janela, não é "não encontrado".
    piso_aliquota_ibs: PisoAliquotaIbs | None = None
```

### Pattern 3: Extensão de `api/routers/simulate.py`

```python
from motor_calculo.piso_aliquota_ibs import piso_aliquota_ibs

# ... dentro de `simular()`, ao lado de `escopo`/`compensacao` (fora do
# laço `for item in payload.itens` — o dado não varia por item):

piso = piso_aliquota_ibs(payload.ano_operacao)

resposta = RespostaSimulacao(
    # ... campos existentes ...
    piso_aliquota_ibs=(
        PisoAliquotaIbs(
            ano_operacao=piso.ano_operacao,
            limite_inferior_percentual=piso.limite_inferior_percentual,
            dispositivo_legal_ref=piso.dispositivo_legal_ref,
        )
        if piso is not None
        else None
    ),
)
```

---

## Data Flow

```text
1. Cliente envia PayloadSimulacao com ano_operacao=2033 (campo JÁ EXISTENTE,
   nenhuma mudança de contrato de entrada)
   │
   ▼
2. api/routers/simulate.py chama piso_aliquota_ibs(2033) UMA VEZ, fora do
   laço por item
   │
   ├─ 2029 ≤ ano ≤ 2077 → PisoAliquotaIbs(90.5%, "LCP 214/2025, art. 371,
   │  §1º, Anexo XVI")
   │
   └─ fora da janela → None
   │
   ▼
3. RespostaSimulacao.piso_aliquota_ibs populado (ou None) — campo aditivo,
   nenhum outro bloco da resposta é tocado
```

---

## Integration Points

Nenhuma — primeira feature do projeto sem nenhum ponto de integração externo (sem Cloud SQL, sem
GCS, sem Qdrant). `motor_calculo/piso_aliquota_ibs.py` é uma constante de módulo.

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|-----------------|
| Unit | `piso_aliquota_ibs()` | `tests/test_piso_aliquota_ibs.py` | pytest | AT-001, AT-002, AT-003, AT-004, AT-005, AT-008 |
| E2E | `/v1/tax/simulate` | `tests/test_api_simulate_piso.py` | pytest + `fastapi.testclient` | AT-006, AT-007 |

Nenhum teste de integração contra Postgres real é necessário — não há banco envolvido.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| `ano_operacao` fora de [2029, 2077] | `piso_aliquota_ibs()` devolve `None` — não é erro, é "regime não vigora" | Não |
| `ano_operacao` anterior a 2026 (já rejeitado por `fase_para()`) | Já tratado por `HTTPException` existente em `api/routers/simulate.py` — esta feature não muda esse caminho | Não |

---

## Configuration

Nenhuma — tabela é constante de módulo, sem variável de ambiente.

---

## Security Considerations

Nenhuma nova superfície — dado público, sem PII, sem I/O.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Nenhum necessário — função pura sem caminho de falha (nunca lança, só devolve `None`) |
| Metrics | Nenhuma |
| Tracing | Nenhum |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|-----------|
| 1.0 | 2026-07-31 | design-agent | Versão inicial. Três decisões: Python puro em `motor_calculo/`, nunca uma migração SQL (Decisão 1 — primeira feature da leva sem NENHUMA superfície de infraestrutura); bloco informativo a nível de requisição, populado uma vez fora do laço por item (Decisão 2); `PisoAliquotaIbs` NUNCA expõe uma alíquota absoluta, só o percentual e a citação — por desenho, não por default vazio (Decisão 3, evita que uma versão futura "preencha" um campo que pareceria pronto para isso). |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md`
