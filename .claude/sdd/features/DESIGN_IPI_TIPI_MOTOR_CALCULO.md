# DESIGN: IPI/TIPI no Motor de Cálculo

> Technical design para conectar `aliquotas_ipi_tipi` (9231 NCMs já ingeridos e verificados no
> Cloud SQL) a `POST /v1/tax/simulate`, via lookup em lote na camada de dados — sem introduzir
> nenhuma dependência de infraestrutura em `motor_calculo/`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | IPI_TIPI_MOTOR_CALCULO |
| **Date** | 2026-07-27 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_IPI_TIPI_MOTOR_CALCULO.md](./DEFINE_IPI_TIPI_MOTOR_CALCULO.md) |
| **Status** | Built (ver `BUILD_REPORT_IPI_TIPI_MOTOR_CALCULO.md`) |
| **Posição na sequência** | 1 de 11 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  POST /v1/tax/simulate — com IPI resolvido por NCM                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Cliente ERP] ──X-API-Key──► api.auth.verificar_api_key                     │
│                                      │                                       │
│                                      ▼                                       │
│                          api/routers/simulate.py                             │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐          │
│         │ (1) ANTES do laço          │                            │          │
│         ▼                            ▼                            ▼          │
│  motor_calculo/*                api/ipi.py                  api/audit.py     │
│  (Python puro,             consultar_ipi_com_seguranca      registrar_com_   │
│   ZERO infra)                        │                       seguranca       │
│  CBS/IBS/IS                          │ nunca levanta               │         │
│  PIS/COFINS                          ▼                              │        │
│  ICMS/ISS                  db/repositorio.buscar_ipi_por_ncm        │        │
│                                      │  1 query / request          │        │
│                                      ▼                              ▼        │
│                            ┌────────────────────┐          pareceres_        │
│                            │  Cloud SQL         │          audit_log         │
│                            │ aliquotas_ipi_tipi │  (GRANT SELECT ao          │
│                            │  9231 linhas       │   papel taxreformai_app,   │
│                            └────────────────────┘   migração 004)            │
│                                                                              │
│         │ (2) POR item de MERCADORIA                                         │
│         ▼                                                                    │
│   api.ipi.resolver_item(ncm) ──► SituacaoIpi ∈ {CALCULADO, NAO_TRIBUTADO,    │
│         │                          NCM_NAO_ENCONTRADO, CONSULTA_INDISPONIVEL,│
│         │                          NAO_APLICAVEL}                            │
│         ▼                                                                    │
│   ItemRegimeVigente(ipi_percentual, fonte_legal_ipi, ipi_situacao)           │
│         │                                                                    │
│         ▼ (3) agregação                                                      │
│   RegimeVigenteResumo(total_ipi, ipi_nao_resolvido[]) + EscopoSimulacao      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Fluxo de degradação (Decisões 1 e 2) — a simulação NUNCA falha por causa do IPI:

  Banco fora do ar ──► situacao=CONSULTA_INDISPONIVEL ─┐
  NCM fora da TIPI ──► situacao=NCM_NAO_ENCONTRADO ────┼──► 200 + "IPI" em
  Item de serviço  ──► situacao=NAO_APLICAVEL ─────────┘    tributos_nao_incluidos
                                                            + total_ipi = null
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db.repositorio.buscar_ipi_por_ncm` | **Novo** — lookup em lote, 1 query (`WHERE ncm_code = ANY(%s)`); SQL puro, propaga exceção | `psycopg` + SQL |
| `db.repositorio.AliquotaIpi` | **Novo** — dataclass frozen espelhando a linha de `aliquotas_ipi_tipi` | `dataclasses` |
| `api.ipi.normalizar_ncm` | **Novo** — canoniza `"22030000"` → `"2203.00.00"` (Decisão 4) | Python puro |
| `api.ipi.consultar_ipi_com_seguranca` | **Novo** — fronteira de política: nunca levanta, devolve `ConsultaIpi(disponivel, mapa)` | Python + `logging` |
| `api.ipi.resolver_item` | **Novo** — função pura NCM+natureza+consulta → `ResolucaoIpi` (situação, valor, fonte) | Python puro |
| `api.schemas_simulate` | **Modificado** — 3 campos por item, `total_ipi` + `ipi_nao_resolvido` no resumo | `pydantic.BaseModel` |
| `api.routers.simulate` | **Modificado** — 1 lookup antes do laço, aplicação por item, escopo dinâmico | FastAPI `APIRouter` |
| `motor_calculo.regime_atual` | **Modificado** — `TRIBUTOS_INDISPONIVEIS = ()`, docstring corrigida, dead code removido | Python puro |
| `scripts/verificar_ipi_producao.py` | **Novo** — prova o `GRANT SELECT` do papel de runtime contra o Cloud SQL real | Python + `psycopg` |

---

## Key Decisions

### Decision 1: NCM ausente da TIPI falha só aquele item (200), nunca a requisição inteira (422)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |
| **Resolve** | Open Question 1 do DEFINE / `A-003` |

**Context:** A `Decision 4` do DESIGN de `API_HTTP_SIMULACAO` estabeleceu que a simulação é
tudo-ou-nada: se a fase não tem alíquota confirmada, a requisição inteira devolve 422 antes de
processar qualquer item. A pergunta aqui é se o NCM ausente segue a mesma regra.

**Choice:** Não segue. O item recebe `ipi_situacao = "NCM_NAO_ENCONTRADO"`, a resposta continua
200, todos os demais tributos daquele item são calculados normalmente, e `"IPI"` permanece em
`escopo.tributos_nao_incluidos` (Decisão 5).

**Rationale:**

1. **A natureza do fato é diferente.** `ano_operacao` é um só para o payload inteiro — uma fase
   sem alíquota invalida *todos* os itens, e o all-or-nothing lá é a descrição honesta do que
   aconteceu. O NCM é por item: recusar 99 itens corretos por causa de 1 NCM desconhecido
   descarta trabalho válido e não torna a resposta mais verdadeira.
2. **422 seria quebra de contrato para clientes existentes.** Hoje qualquer NCM devolve 200 —
   `ncm` sequer é usado em cálculo. Passar a rejeitar payloads que ontem funcionavam viola o
   critério "Zero mudança de contrato externo obrigatório" do DEFINE e derrubaria integrações
   ERP em produção no dia do deploy.
3. **A TIPI cobre só NCMs completos (`NNNN.NN.NN`).** Códigos parciais (capítulo/posição) são
   cabeçalhos sem alíquota própria — ver `db/tipi.py`. Um ERP mandando um código parcial é um
   caso normal e previsível, não um payload malformado.
4. O risco que o DEFINE realmente quer evitar (`MUST`: "nunca confundidos com alíquota zero
   silenciosa") é resolvido pela Decisão 3, não pelo código HTTP.

**Alternatives Rejected:**

1. **422 do payload inteiro** — rejeitado pelos motivos 1-3 acima.
2. **200 omitindo o item da lista de IPI** — rejeitado: omissão silenciosa é exatamente o modo
   de falha que o DEFINE proíbe.

**Consequences:**

- A resposta pode ser parcialmente resolvida; o contrato precisa de um campo explícito que
  enumere o que ficou de fora (`ipi_nao_resolvido`, Decisão 5).
- Um cliente que *queira* rigor all-or-nothing consegue implementá-lo do lado dele: basta
  rejeitar respostas com `ipi_nao_resolvido` não-vazio. O inverso não seria possível.

---

### Decision 2: Falha do Postgres degrada graciosamente (200 declarado), nunca 5xx

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |
| **Resolve** | Open Question 2 do DEFINE / `A-001` |

**Context:** Diferente do audit log — uma escrita que o cliente não vê — o IPI é *conteúdo da
resposta*. O DEFINE pergunta qual código HTTP usar quando a consulta falha (timeout, conexão,
`GRANT` faltando).

**Choice:** Nenhum código de erro. A consulta é envolvida por `consultar_ipi_com_seguranca`, que
captura qualquer exceção, loga via `logger.exception` e devolve `ConsultaIpi(disponivel=False)`.
Todos os itens de mercadoria recebem `ipi_situacao = "CONSULTA_INDISPONIVEL"`, `total_ipi` fica
`null`, `"IPI"` permanece em `tributos_nao_incluidos` e a advertência diz que a consulta falhou.
Resposta: **200**.

**Rationale:**

1. **Todo o resto da simulação é infra-free por construção.** CBS/IBS/IS, PIS/COFINS, ICMS e ISS
   saem de `motor_calculo/`, Python puro sem I/O. Transformar indisponibilidade do Cloud SQL em
   5xx acoplaria a disponibilidade do produto inteiro ao banco para adicionar *um* tributo — uma
   regressão de disponibilidade causada por uma feature aditiva.
2. **É exatamente o estado de hoje.** Sem `DB_INSTANCE_CONNECTION_NAME`, `get_db_pool()` devolve
   `None` e a API responde 200 sem IPI. `pool is None` e "pool falhou" produzem a mesma situação
   (`CONSULTA_INDISPONIVEL`): não há regressão de comportamento, só um campo novo dizendo por quê.
3. **`A-001` do DEFINE** registra que depender do Postgres em `/simulate` só é aceitável porque
   a falha não propaga. Um 5xx invalidaria a premissa que autorizou esta abordagem.
4. **Degradar não é silenciar.** A diferença crítica em relação ao audit log é que aqui a
   degradação é *declarada na resposta*, com situação própria e distinta de `NCM_NAO_ENCONTRADO`
   — o cliente sabe se o dado não existe ou se o sistema não conseguiu consultar, e pode
   reprocessar no segundo caso.

**Alternatives Rejected:**

1. **503 Service Unavailable** — rejeitado: derruba uma simulação inteira e correta em todos os
   outros tributos por causa de um componente opcional.
2. **500 genérico** — rejeitado pelo mesmo motivo, e ainda esconderia do cliente que a única
   parte afetada foi o IPI.
3. **Retry/circuit breaker** — fora de escopo (o DEFINE marca observabilidade como `COULD`); o
   pool `psycopg_pool` já reconecta, e um retry síncrono dentro do request só somaria latência.

**Consequences:**

- Um `GRANT` faltando ou uma migração não aplicada não reprova nada no runtime — some no log.
  Por isso a Decisão 8 exige verificação explícita contra produção, e o smoke test do
  `deploy.yml` passa a exigir `total_ipi` não-nulo.
- `logger.exception` no stdout do container é encaminhado ao Cloud Logging pelo Cloud Run, mesmo
  caminho já usado por `api/audit.py`.

---

### Decision 3: `ipi_situacao` é um enum de 5 estados, não um percentual anulável

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** O DEFINE exige (`MUST`) que "NCM ausente" e "`nao_tributado = true`" nunca sejam
confundidos com alíquota zero. Com só `ipi_percentual: Decimal | None`, quatro coisas
radicalmente diferentes colapsam no mesmo `null`: não tributado (NT), NCM desconhecido, consulta
falhou e item de serviço.

**Choice:** `ItemRegimeVigente` ganha `ipi_situacao`, um `Literal` de 5 valores:

| Situação | Significado | `ipi_percentual` | Conta em `total_ipi`? |
|----------|-------------|------------------|------------------------|
| `CALCULADO` | NCM na TIPI com alíquota | preenchido | sim |
| `NAO_TRIBUTADO` | NCM na TIPI com classificação **NT** | `null` | sim, contribuindo 0,00 |
| `NCM_NAO_ENCONTRADO` | NCM não existe na tabela (Decisão 1) | `null` | não — bloqueia o total |
| `CONSULTA_INDISPONIVEL` | Banco fora do ar / não configurado (Decisão 2) | `null` | não — bloqueia o total |
| `NAO_APLICAVEL` | `natureza == "SERVICO"` — serviço não paga IPI | `null` | não se aplica |

**Rationale:** "NT" é classificação tributária de primeira classe na própria TIPI — a migração
004 já a modelou como coluna separada (`nao_tributado`) e a CHECK constraint
`aliquota_xor_nao_tributado` a torna mutuamente exclusiva da alíquota. Achatá-la para `0%` na
resposta perderia uma distinção que a norma faz e o banco preserva. Um enum torna a diferença
inspecionável por máquina, não só por leitura humana da advertência.

**Alternatives Rejected:**

1. **Só `ipi_percentual: Decimal | None` + texto na advertência** — rejeitado: obriga o ERP a
   fazer parsing de português para saber o que houve.
2. **Booleano `ipi_nao_tributado` isolado** — rejeitado: cobre NT mas deixa os outros três
   estados indistinguíveis.

**Consequences:**

- `ipi_situacao` é preenchido em **ambos** os ramos do laço (mercadoria e serviço), nunca por
  default do modelo: um default silencioso faria um item de mercadoria com bug reportar
  `NAO_APLICAVEL` — uma afirmação jurídica falsa emitida sem ninguém perceber.

---

### Decision 4: NCM é normalizado de formato antes da igualdade exata — e isso não é fuzzy match

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** `aliquotas_ipi_tipi.ncm_code` guarda o formato pontuado do PDF oficial
(`2203.00.00`, `VARCHAR(10)`, ver `_PADRAO_CODIGO` em `db/tipi.py`). Mas `ItemSimulacao.ncm` é
string livre, e o próprio repositório já manda os dois formatos:

| Origem | Valor enviado |
|--------|---------------|
| `tests/test_api_simulate.py:30` | `"8471.30.12"` (pontuado) |
| `tests/test_escopo_e_compensacao.py:78` | `"22030000"` (só dígitos) |
| **Smoke test do `deploy.yml`** (contra produção) | `"22030000"` (só dígitos) |

Sem normalização, o smoke test do próprio deploy — o caminho que prova a feature em produção —
receberia `NCM_NAO_ENCONTRADO`, e ERPs (que emitem NFe com NCM de 8 dígitos sem pontuação, como
manda o layout) nunca resolveriam IPI nenhum. A feature entregaria "indisponível" para
praticamente 100% do tráfego real.

**Choice:** `normalizar_ncm(bruto) -> str | None`: remove tudo que não é dígito; se sobrarem
exatamente 8 dígitos, formata como `NNNN.NN.NN`; qualquer outra coisa devolve `None` (que vira
`NCM_NAO_ENCONTRADO`, sem consultar o banco). A comparação no SQL continua sendo igualdade exata
de `ncm_code`.

**Rationale:**

1. **Normalizar formato ≠ aproximar valor.** `"22030000"` e `"2203.00.00"` são *o mesmo código*
   em duas grafias; a restrição do DEFINE ("sem fuzzy match, sem prefixo") proíbe adivinhar um
   código *diferente* do informado. Nenhum código de 8 dígitos normaliza para outro código —
   a função é injetiva.
2. **A normalização acontece em Python, não no SQL.** `WHERE replace(ncm_code,'.','') = ANY(...)`
   funcionaria e mataria o índice `idx_aliquotas_ipi_ncm`, forçando seq scan em 9231 linhas por
   request. Canonizar do lado da aplicação mantém o índice e o SQL trivial.
3. **Código parcial não vira prefixo.** `"2203"` (posição) devolve `None`, não busca "o primeiro
   NCM que começa com 2203" — é exatamente o fallback por prefixo que o DEFINE proíbe, e
   cabeçalhos de categoria não têm alíquota própria.

**Alternatives Rejected:**

1. **Exigir formato pontuado no payload (validador Pydantic)** — rejeitado: mudança de contrato
   externo obrigatória, proibida pelo DEFINE, e quebraria o smoke test em produção.
2. **Gravar as duas grafias na tabela** — rejeitado: duplica dado e altera o schema, que o
   DEFINE põe explicitamente fora de escopo.
3. **Normalizar no SQL** — rejeitado pelo motivo 2 acima.

**Consequences:**

- `normalizar_ncm` é função pura testável sem banco, e a suíte precisa cobrir os dois formatos
  mais o código parcial.
- NCMs com sufixo "EX" (exceção tarifária) não são suportados — não constam da tabela ingerida e
  cairiam em `NCM_NAO_ENCONTRADO`, o comportamento correto.

---

### Decision 5: `total_ipi` só existe quando 100% dos itens de mercadoria foram resolvidos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** Consequência direta da Decisão 1: uma resposta pode ter 9 itens com IPI resolvido e
1 sem. Qual número aparece em `total_ipi`?

**Choice:** `total_ipi: Decimal | None`. É `None` sempre que existir ao menos um item de
mercadoria não resolvido (`NCM_NAO_ENCONTRADO` ou `CONSULTA_INDISPONIVEL`), ou quando não houver
item de mercadoria nenhum. Caso contrário, é a soma — inclusive `0.00` para um payload
inteiramente NT, que é conhecimento legítimo, não ausência de dado.

O mesmo predicado governa três coisas, para não existirem duas noções de "resolvido":

```text
tudo_resolvido = (há ≥1 item MERCADORIA) e (nenhum deles ficou não resolvido)

  tudo_resolvido ──► total_ipi = soma   ∧  "IPI" ∈ tributos_incluidos
 ¬tudo_resolvido ──► total_ipi = null   ∧  "IPI" ∈ tributos_nao_incluidos
```

Os itens que ficaram de fora são enumerados em `RegimeVigenteResumo.ipi_nao_resolvido`
(`[{sku, ncm, situacao}]`), atendendo ao `SHOULD` do DEFINE. Os valores por item já resolvidos
continuam visíveis em `itens_regime_vigente` — nada é descartado, só não é somado.

**Rationale:** Um total parcial é indistinguível de um total completo na tela de um
departamento fiscal — o mesmo modo de falha que motivou `EscopoSimulacao` e a advertência do
`valor_liquido`. `total_ipi` com número passa a significar sempre "total completo deste payload",
sem asterisco. É a mesma disciplina de `total_pis`/`total_cofins`, que são `None` quando
`regime_apuracao` não foi informado em vez de `0`.

**Alternatives Rejected:**

1. **Somar o que deu e confiar na advertência** — rejeitado: valor com aparência de total é
   precisamente o que este projeto vem recusando desde `AliquotaNaoDisponivelError`.
2. **`total_ipi = 0` quando indisponível** — rejeitado: é o "0% silencioso" que o DEFINE proíbe,
   só que agregado.

**Consequences:**

- `RegimeVigenteResumo.total_ipi` é o único campo `Decimal | None` do resumo além de PIS/COFINS;
  clientes precisam tratar `null`. Fica documentado no docstring do modelo e na advertência.
- Payload só de serviços: `total_ipi = null` e `"IPI"` em `tributos_nao_incluidos` — coerente com
  como `ICMS_INTERNO`/`ISS` já são tratados quando nenhum item os dispara.

---

### Decision 6: `api/ipi.py` é a fronteira de política, espelhando `api/audit.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** As Decisões 1-5 são política (o que fazer quando falta dado), não acesso a dados.
Se essa política morar dentro de `db/repositorio.py`, o repositório passa a decidir semântica de
resposta HTTP; se morar dentro do handler, vira um bloco de 40 linhas não testável isoladamente.

**Choice:** Três camadas com responsabilidade estrita:

| Camada | Responsabilidade | Levanta exceção? |
|--------|------------------|------------------|
| `db/repositorio.buscar_ipi_por_ncm` | SQL puro, 1 query, devolve `dict[str, AliquotaIpi]` | **Sim** — erro de banco é erro |
| `api/ipi.py` | Normalização, captura de falha, mapeamento para `SituacaoIpi` | **Nunca** |
| `api/routers/simulate.py` | Chama uma vez, aplica por item, agrega | só as já existentes |

`api/ipi.py` é o gêmeo de leitura de `api/audit.py`: mesmo padrão de import tardio de
`db.repositorio` dentro da função (para `api.main` importar sem `psycopg` instalado), mesmo
`logger.exception`, mesma garantia de não propagação.

**Rationale:** Mantém `db/repositorio.py` consistente com `registrar_parecer`/`buscar_regra_cache`
— nenhum deles engole exceção. Preserva a constraint do DEFINE de `motor_calculo/` continuar sem
infraestrutura, e ainda deixa `resolver_item` como função pura: os cenários AT-001..AT-003 podem
ser testados sem banco e sem HTTP.

**Alternatives Rejected:**

1. **`try/except` direto no handler** — rejeitado: mistura política com orquestração e obriga a
   subir `TestClient` para testar cada situação.
2. **`buscar_ipi_por_ncm` devolvendo `{}` em caso de falha** — rejeitado, e é o ponto mais
   perigoso: apagaria a diferença entre `NCM_NAO_ENCONTRADO` e `CONSULTA_INDISPONIVEL`, que a
   Decisão 3 existe para preservar.

---

### Decision 7: no máximo 1 query por request — e zero quando não há mercadoria

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** Payload aceita até 100 itens (`Field(max_length=100)`). AT-004 exige N NCMs
distintos em exatamente 1 query; AT-005 exige que item de serviço não dispare lookup.

**Choice:** Antes do laço, o handler coleta
`sorted({normalizar_ncm(i.ncm) for i in payload.itens if i.natureza == "MERCADORIA"})`,
descartando `None`. Se o conjunto ficar vazio, **nenhuma conexão é aberta**. Caso contrário, uma
única chamada a `buscar_ipi_por_ncm` com `WHERE ncm_code = ANY(%s)`.

**Rationale:** `set` resolve `A-002` (NCMs duplicados) sem cláusula extra: 100 itens do mesmo SKU
viram 1 elemento na lista. `= ANY(%s)` com uma lista Python é o idioma nativo do `psycopg` para
lote, usa o índice `idx_aliquotas_ipi_ncm` e não monta SQL por concatenação. `sorted` deixa a
query determinística — testável por comparação de argumento, não só de contagem.

**Alternatives Rejected:**

1. **`IN` com placeholders gerados dinamicamente** — rejeitado: SQL de tamanho variável polui o
   plan cache do Postgres e convida a erro de quoting.
2. **`buscar_ipi_por_ncm(ncm)` chamado por item** — rejeitado: é o N+1 que o DEFINE proíbe (até
   100 round-trips ao Cloud SQL por request).

**Consequences:**

- AT-004 é verificável por um fake de conexão que conta `execute` e guarda os argumentos.
- Payload só de serviços não toca o banco — o caminho mais rápido continua tão rápido quanto hoje.

---

### Decision 8: `TRIBUTOS_INDISPONIVEIS` esvazia e `RegimeIndisponivelError` é removido

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** `motor_calculo/regime_atual.py` declara `TRIBUTOS_INDISPONIVEIS = ("IPI",)` e uma
exceção cuja mensagem afirma que o IPI "depende da tabela TIPI por NCM (milhares de linhas), dado
tabular sem alíquota única para citar". Essa premissa acabou de ser refutada na prática: a tabela
está ingerida, verificada (9231 linhas) e cada linha carrega seu `dispositivo_legal_ref`.

**Choice:**

- `TRIBUTOS_INDISPONIVEIS = ()` — a constante permanece (é importada por `simulate.py` e é o
  ponto de extensão para o próximo tributo estruturalmente indisponível), com docstring
  reescrita explicando que o IPI saiu porque ganhou fonte de dado, não porque virou estimativa.
- `RegimeIndisponivelError` é **removido**: `grep` em todo o repositório mostra a definição e
  nenhum uso. Manter uma exceção morta cuja justificativa foi refutada é pior que não ter —
  alguém a reintroduziria citando um raciocínio que não vale mais.
- `"IPI"` passa a entrar no escopo pelo mesmo mecanismo dinâmico de `ICMS_INTERNO`/`ISS`, que já
  dependem do conteúdo do payload.

**Rationale:** A honestidade do escopo é o produto aqui. Deixar `("IPI",)` fixo enquanto o valor
é calculado por item produziria uma resposta que se contradiz. E a limitação estrutural que
resta em `regime_atual.py` (alíquotas de ICMS por NCM/CEST, exceções por mercadoria) continua
citando o IPI como analogia em três comentários — todos precisam ser reescritos, senão o arquivo
passa a justificar decisões com um exemplo que ele mesmo desmentiu.

**Alternatives Rejected:**

1. **Manter `("IPI",)` e filtrar no router** — rejeitado: constante que mente exige que todo
   consumidor conheça a exceção.
2. **Manter a exceção "por compatibilidade"** — rejeitado: zero consumidores, zero
   compatibilidade a preservar.

**Consequences:**

- `tests/test_escopo_e_compensacao.py:98` (que exige `"IPI"` em `tributos_nao_incluidos`)
  **continua passando sem alteração**: sem `DB_INSTANCE_CONNECTION_NAME`, `get_db_pool()` devolve
  `None`, a situação é `CONSULTA_INDISPONIVEL` e o IPI segue não incluído. Vale registrar
  explicitamente no BUILD: é a prova de que a feature é aditiva e não muda o comportamento de
  quem não tem banco.

---

### Decision 9: a feature só é considerada pronta com prova contra o Cloud SQL real

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-27 |

**Context:** O `GRANT SELECT ON aliquotas_ipi_tipi TO taxreformai_app` da migração 004 está
dentro de um bloco `DO $$ ... IF EXISTS (SELECT FROM pg_roles ...)` e **nunca foi exercitado por
nenhum SELECT** — a ingestão gravou como `taxreformai_admin`. Pela Decisão 2, um grant faltando
não produz erro visível: produz `CONSULTA_INDISPONIVEL` silencioso em produção. A lição 3 do
SHIPPED de `SCHEMA_POSTGRESQL` (nenhum papel do Cloud SQL é superusuário, ao contrário de
Postgres autogerido) é precisamente sobre config de papel que parecia certa e não era.

**Choice:** Duas verificações contra infraestrutura real, nenhuma rodando local:

1. `scripts/verificar_ipi_producao.py`, disparado por `migrar_banco.yml` (`verificar_ipi=sim`):
   conecta **com o papel `taxreformai_app`**, não o admin, e faz o mesmo lookup em lote do
   runtime para um NCM com alíquota e um NT, falhando o job se vier vazio ou permissão negada.
2. O smoke test do `deploy.yml` (que já manda `ncm: "22030000"`) passa a exigir
   `.regime_vigente.total_ipi != null` em `/tmp/sim.json`. É o E2E completo: normalização
   (Decisão 4) + grant + pool + agregação, contra a API pública.

**Rationale:** Este projeto já classificou features por "verificado contra infraestrutura real"
vs. "revisado por código" (ver `DEPLOY_CLOUD_RUN`, 7/7). Uma feature cujo único modo de falha é
silencioso não pode ser shipada só com teste de fake.

**Consequences:**

- O smoke test do deploy passa a depender do banco. É deliberado e coerente com o precedente já
  registrado no CLAUDE.md: "os defaults fazem um deploy incompleto subir um serviço que responde
  200 em `/health` e falha 100% das requisições reais".

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/repositorio.py` | Modify | `AliquotaIpi` + `buscar_ipi_por_ncm()` — 1 query, `= ANY(%s)`, sem RLS (dado público) | @database-reviewer | — |
| 2 | `api/ipi.py` | Create | `normalizar_ncm`, `SituacaoIpi`, `ResolucaoIpi`, `ConsultaIpi`, `consultar_ipi_com_seguranca`, `resolver_item` | @python-developer | 1 |
| 3 | `api/schemas_simulate.py` | Modify | `ipi_percentual`/`fonte_legal_ipi`/`ipi_situacao` em `ItemRegimeVigente`; `total_ipi` + `ipi_nao_resolvido` em `RegimeVigenteResumo`; modelo `IpiNaoResolvido` | @python-developer | 2 |
| 4 | `api/routers/simulate.py` | Modify | Lookup único antes do laço, aplicação por item, `total_ipi`/escopo/advertência dinâmicos, IPI no texto do audit log | @python-developer | 2, 3 |
| 5 | `motor_calculo/regime_atual.py` | Modify | `TRIBUTOS_INDISPONIVEIS = ()`, remoção de `RegimeIndisponivelError`, docstring e 3 comentários que usavam o IPI como analogia | @python-developer | — |
| 6 | `tests/test_ipi_resolucao.py` | Create | Unit puro: `normalizar_ncm` (pontuado/dígitos/parcial/lixo), `resolver_item` nas 5 situações | @test-generator | 2 |
| 7 | `tests/test_api_simulate_ipi.py` | Create | AT-001..AT-005 via `TestClient` + fake pool; AT-004 conta `execute`; pool `None` → `CONSULTA_INDISPONIVEL`; pool que explode → 200 | @test-generator | 4 |
| 8 | `tests/test_tipi_db.py` | Modify | `buscar_ipi_por_ncm` contra PostgreSQL real: lote com NCM presente/ausente/NT, 1 query | @database-reviewer | 1 |
| 9 | `scripts/verificar_ipi_producao.py` | Create | Lookup como papel `taxreformai_app` contra o Cloud SQL real (Decisão 9) | @gcp-data-architect | 1 |
| 10 | `.github/workflows/migrar_banco.yml` | Modify | Input `verificar_ipi` + passo que roda o script 9 | @gcp-data-architect | 9 |
| 11 | `.github/workflows/deploy.yml` | Modify | Smoke test exige `total_ipi` não-nulo | @gcp-data-architect | 4 |
| 12 | `CLAUDE.md` | Modify | Tabela de features, seção do regime vigente (IPI sai de "fora de escopo"), `db/repositorio.py` em arquivos-chave | @python-developer | 1-11 |

**Total Files:** 12 (4 novos + 8 modificados)

**Fora do manifesto, deliberadamente:** `frontend/lib/types.ts` e componentes. O frontend hoje
sequer tipa `regime_vigente` (só `resumo_financeiro`/`itens_detalhados`), e todos os campos novos
são aditivos e opcionais — nada quebra. Exibir IPI na tela é outra feature; misturá-la aqui
adicionaria superfície sem fechar nenhum critério do DEFINE.

---

## Agent Assignment Rationale

| Agent | Files | Why This Agent |
|-------|-------|-----------------|
| @database-reviewer | 1, 8 | SQL do lookup em lote, uso do índice, e o teste contra Postgres real — mesmo agente que shipou `SCHEMA_POSTGRESQL` |
| @python-developer | 2, 3, 4, 5, 12 | FastAPI/Pydantic e a lógica pura de resolução; mesmo agente das 8 features anteriores |
| @test-generator | 6, 7 | Cobertura dos AT-001..AT-005 com fakes, incluindo o spy de contagem de queries |
| @gcp-data-architect | 9, 10, 11 | Verificação contra Cloud SQL/Cloud Run reais e edição dos workflows |
| @code-reviewer | (revisão final) | Revisão de qualidade geral, como em toda feature |
| @security-reviewer | (revisão de 1) | Confirmar que o lookup sem RLS é correto aqui (dado legal público) e que não há concatenação de SQL |

---

## Code Patterns

### Pattern 1: lookup em lote (`db/repositorio.py`)

```python
@dataclass(frozen=True)
class AliquotaIpi:
    ncm_code: str
    aliquota_percentual: Decimal | None  # NULL quando nao_tributado (CHECK da migração 004)
    nao_tributado: bool
    dispositivo_legal_ref: str


def buscar_ipi_por_ncm(conexao, ncms: list[str]) -> dict[str, AliquotaIpi]:
    """Lookup em lote da TIPI. Sem RLS: como `regras_tributarias_cache`, é dado
    legal público, igual para todo tenant.

    UMA query para N códigos — `= ANY(%s)` com uma lista Python é o idioma
    nativo do psycopg para lote e usa `idx_aliquotas_ipi_ncm`. Um laço de
    `buscar_ipi(ncm)` seriam até 100 round-trips ao Cloud SQL por requisição.

    Propaga exceção de propósito: quem decide degradar é `api/ipi.py`, não este
    módulo (ver Decisão 6). NCM ausente simplesmente não aparece no dicionário —
    o chamador distingue ausência de falha porque falha vira exceção.
    """
    if not ncms:
        return {}

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT ncm_code, aliquota_percentual, nao_tributado, dispositivo_legal_ref
            FROM aliquotas_ipi_tipi
            WHERE ncm_code = ANY(%s)
            """,
            (list(ncms),),
        )
        linhas = cur.fetchall()

    return {
        linha[0]: AliquotaIpi(
            ncm_code=linha[0],
            aliquota_percentual=linha[1],
            nao_tributado=linha[2],
            dispositivo_legal_ref=linha[3],
        )
        for linha in linhas
    }
```

### Pattern 2: normalização e política (`api/ipi.py`)

```python
"""Resolve IPI por NCM sem nunca derrubar a simulação.

Gêmeo de leitura de `api/audit.py`: mesma garantia de não propagação, mesma
razão. A diferença crítica é que aqui a degradação é DECLARADA na resposta —
o audit log falha em silêncio porque o cliente não o vê; o IPI, não. Cada
situação tem nome próprio (`SituacaoIpi`), então o ERP distingue "este NCM não
existe na TIPI" de "não consegui consultar" e sabe se vale reprocessar.
"""

import logging
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

logger = logging.getLogger("api.ipi")

_SO_DIGITOS = re.compile(r"\D")


class SituacaoIpi(StrEnum):
    CALCULADO = "CALCULADO"
    NAO_TRIBUTADO = "NAO_TRIBUTADO"          # "NT" na TIPI — NÃO é alíquota 0%
    NCM_NAO_ENCONTRADO = "NCM_NAO_ENCONTRADO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"          # natureza == SERVICO


def normalizar_ncm(bruto: str) -> str | None:
    """`"22030000"` e `"2203.00.00"` são o MESMO código em duas grafias — a
    tabela guarda o pontuado (formato do PDF oficial), ERPs e o próprio smoke
    test do deploy mandam só dígitos. Canonizar não é fuzzy match: a função é
    injetiva, nenhum código de 8 dígitos vira outro código (ver Decisão 4).

    Qualquer coisa que não tenha exatamente 8 dígitos devolve None — códigos
    parciais (capítulo/posição) são cabeçalhos de categoria sem alíquota
    própria, e adivinhar por prefixo é justamente o que o DEFINE proíbe.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")
    if len(digitos) != 8:
        return None
    return f"{digitos[:4]}.{digitos[4:6]}.{digitos[6:8]}"


@dataclass(frozen=True)
class ConsultaIpi:
    disponivel: bool
    por_ncm: dict = field(default_factory=dict)


def consultar_ipi_com_seguranca(pool, ncms: list[str]) -> ConsultaIpi:
    """`disponivel=False` significa "não consegui consultar", nunca "não existe"
    — apagar essa diferença devolvendo `{}` seria o erro que a Decisão 6 evita.

    `pool is None` (todo teste, e qualquer deploy antes do Cloud SQL) cai no
    mesmo caminho: é indisponibilidade, não ausência de dado.
    """
    if pool is None or not ncms:
        return ConsultaIpi(disponivel=False)

    from db.repositorio import buscar_ipi_por_ncm

    try:
        with pool.connection() as conexao:
            return ConsultaIpi(disponivel=True, por_ncm=buscar_ipi_por_ncm(conexao, ncms))
    except Exception:
        logger.exception(
            "Falha ao consultar IPI/TIPI — a simulação segue sem IPI, declarado na resposta"
        )
        return ConsultaIpi(disponivel=False)


@dataclass(frozen=True)
class ResolucaoIpi:
    situacao: SituacaoIpi
    valor: Decimal = Decimal(0)          # só somável quando `resolvido`
    percentual: Decimal | None = None    # em pontos percentuais, ex. Decimal("3.250")
    fonte_legal: str | None = None

    @property
    def resolvido(self) -> bool:
        """NT conta como resolvido: sabemos a resposta jurídica (não tributado),
        ela só não vira valor."""
        return self.situacao in (SituacaoIpi.CALCULADO, SituacaoIpi.NAO_TRIBUTADO)


def resolver_item(natureza: str, ncm: str, valor_base: Decimal, consulta: ConsultaIpi) -> ResolucaoIpi:
    """Função pura — os cenários AT-001..AT-003 são testáveis sem banco e sem HTTP."""
    if natureza == "SERVICO":
        return ResolucaoIpi(SituacaoIpi.NAO_APLICAVEL)

    if not consulta.disponivel:
        return ResolucaoIpi(SituacaoIpi.CONSULTA_INDISPONIVEL)

    codigo = normalizar_ncm(ncm)
    linha = consulta.por_ncm.get(codigo) if codigo else None
    if linha is None:
        return ResolucaoIpi(SituacaoIpi.NCM_NAO_ENCONTRADO)

    if linha.nao_tributado:
        return ResolucaoIpi(
            SituacaoIpi.NAO_TRIBUTADO, fonte_legal=linha.dispositivo_legal_ref
        )

    # Mesma disciplina de arredondamento do engine e de PIS/COFINS/ICMS no
    # router: ROUND_HALF_UP em centavos. A tabela guarda fração (0.03250),
    # a resposta expõe pontos percentuais (3.250) — convenção de `regime_atual`.
    return ResolucaoIpi(
        situacao=SituacaoIpi.CALCULADO,
        valor=(valor_base * linha.aliquota_percentual).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        percentual=linha.aliquota_percentual * 100,
        fonte_legal=linha.dispositivo_legal_ref,
    )
```

### Pattern 3: campos novos (`api/schemas_simulate.py`)

```python
class IpiNaoResolvido(BaseModel):
    """Enumera o que ficou de fora quando a resolução foi parcial (Decisão 5).
    Sem isto, `total_ipi = null` não diria QUAL item causou."""

    sku: str
    ncm: str
    situacao: str  # NCM_NAO_ENCONTRADO | CONSULTA_INDISPONIVEL


class ItemRegimeVigente(BaseModel):
    ...
    # IPI (TIPI, Decreto 11.158/2022). `ipi_situacao` é sempre preenchido, nos
    # dois ramos do laço: quatro coisas diferentes colapsariam num só `null` de
    # `ipi_percentual` — NT, NCM desconhecido, consulta falha e item de serviço.
    # NT (`NAO_TRIBUTADO`) NÃO é alíquota 0%: é classificação tributária própria
    # da TIPI, preservada como coluna separada desde a migração 004.
    ipi_percentual: Decimal | None = None
    fonte_legal_ipi: str | None = None
    ipi_situacao: str = SituacaoIpi.NAO_APLICAVEL


class RegimeVigenteResumo(BaseModel):
    ...
    # `None` quando QUALQUER item de mercadoria ficou sem resolver, ou quando
    # não há item de mercadoria — nunca um total parcial com cara de total
    # (Decisão 5). `Decimal("0.00")` é um total legítimo: payload todo NT.
    total_ipi: Decimal | None = None
    ipi_nao_resolvido: list[IpiNaoResolvido] = []
```

### Pattern 4: consumo no router (`api/routers/simulate.py`)

```python
    # UMA consulta por requisição, antes do laço — não uma por item (Decisão 7).
    # `set` cobre NCMs repetidos (100 itens do mesmo SKU = 1 código); `sorted`
    # deixa a query determinística e comparável em teste. Payload só de
    # serviços não abre conexão nenhuma.
    ncms_consultar = sorted(
        {
            codigo
            for item in payload.itens
            if item.natureza == "MERCADORIA" and (codigo := normalizar_ncm(item.ncm))
        }
    )
    consulta_ipi = consultar_ipi_com_seguranca(db_pool, ncms_consultar)

    total_ipi = Decimal(0)
    itens_mercadoria = 0
    ipi_nao_resolvido: list[IpiNaoResolvido] = []

    for item in payload.itens:
        ...
        resolucao = resolver_item(item.natureza, item.ncm, valor_base_item, consulta_ipi)
        item_regime = item_regime.model_copy(
            update={
                "ipi_situacao": resolucao.situacao.value,
                "ipi_percentual": resolucao.percentual,
                "fonte_legal_ipi": resolucao.fonte_legal,
            }
        )
        if item.natureza == "MERCADORIA":
            itens_mercadoria += 1
            if resolucao.resolvido:
                total_ipi += resolucao.valor
            else:
                ipi_nao_resolvido.append(
                    IpiNaoResolvido(sku=item.sku, ncm=item.ncm, situacao=resolucao.situacao.value)
                )

    # Um único predicado governa total, escopo e advertência — duas noções de
    # "resolvido" divergiriam no primeiro refactor.
    ipi_completo = itens_mercadoria > 0 and not ipi_nao_resolvido
    if ipi_completo:
        tributos_regime_vigente_incluidos.add("IPI")
    else:
        total_ipi = None
```

E o escopo dinâmico, substituindo a menção fixa ao IPI:

```python
    tributos_nao_calculados = sorted(
        set(TRIBUTOS_INDISPONIVEIS)  # hoje vazio — ver Decisão 8
        | ({"ICMS_INTERESTADUAL", "ICMS_INTERNO", "ISS", "IPI"}
           - tributos_regime_vigente_incluidos)
    )
```

Advertência: a frase fixa "NÃO inclui IPI (tabela TIPI por NCM, sem alíquota única para citar)"
sai. No lugar, um trecho condicional — quando `ipi_completo`, cita a TIPI como incluída; quando
não, diz quantos itens ficaram sem e por qual situação, sem prometer 0%.

### Pattern 5: verificação em produção (`scripts/verificar_ipi_producao.py`)

```python
"""Prova o lookup de IPI contra o Cloud SQL real, com o papel de RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
a ingestão gravou como `taxreformai_admin`, e o `GRANT SELECT` da migração 004
para `taxreformai_app` nunca foi exercitado por nenhum SELECT. Pela Decisão 2,
um grant faltando NÃO gera erro em runtime — gera CONSULTA_INDISPONIVEL
silencioso. Este script é o único lugar onde isso vira uma falha ruidosa.
"""
```

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`), chama `buscar_ipi_por_ncm` para um NCM
com alíquota e um NT, e sai com código 1 se o dicionário vier vazio, se a permissão for negada,
ou se a linha NT vier com alíquota preenchida.

---

## Data Flow

```text
1. Cliente envia POST /v1/tax/simulate (X-API-Key + payload) — `ncm` já existia, contrato intacto
2. verificar_api_key → tenant_id; payload.tenant_id divergente → 403
3. Fase/RegraFiscal resolvida uma vez → 422 se não confirmada (comportamento inalterado)
4. NOVO: coleta NCMs distintos e normalizados dos itens MERCADORIA
   4a. conjunto vazio  → nenhuma conexão aberta         (AT-005)
   4b. conjunto cheio  → 1 query `= ANY(%s)`            (AT-004)
   4c. qualquer exceção → capturada, logada, disponivel=False (Decisão 2)
5. Por item: motor_calculo (CBS/IBS/IS) + PIS/COFINS + ICMS/ISS, exatamente como hoje
   5a. NOVO: resolver_item → situação + valor + fonte legal do dispositivo da própria linha
6. Agregação: total_ipi (só se completo), ipi_nao_resolvido[], escopo dinâmico
7. Audit log (nunca propaga) — o texto do parecer passa a citar o IPI resolvido
8. 200 com RespostaSimulacao
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL `taxreformai-pg` / `aliquotas_ipi_tipi` | `psycopg_pool` via socket unix do Cloud Run (`api/db.py`), SELECT | Papel `taxreformai_app`, senha do Secret Manager |
| `motor_calculo` | Import Python direto, in-process | N/A — e continua sem tocar em banco |
| Cliente ERP | REST/JSON, campos aditivos | `X-API-Key` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit puro | `normalizar_ncm` (pontuado, dígitos, parcial, vazio, lixo); `resolver_item` nas 5 situações | `tests/test_ipi_resolucao.py` | pytest | Toda a lógica de política, sem banco |
| Integration (fake) | AT-001..AT-005 via `TestClient` + `FakePool` (mesmo padrão de `tests/test_audit.py`) | `tests/test_api_simulate_ipi.py` | pytest + `TestClient` | Contrato da resposta |
| Integration (Postgres real) | `buscar_ipi_por_ncm`: lote misto (presente/ausente/NT), 1 query, tipo `Decimal` preservado | `tests/test_tipi_db.py` | pytest + container `postgres:16` do CI | SQL de verdade |
| Verificação real | Papel `taxreformai_app` fazendo SELECT no Cloud SQL | `scripts/verificar_ipi_producao.py` via `migrar_banco.yml` | workflow_dispatch | Decisão 9 |
| E2E produção | `total_ipi` não-nulo no smoke test do deploy (`ncm: 22030000`) | `.github/workflows/deploy.yml` | curl + jq | Decisão 9 |

**Mapa Acceptance Test → teste:**

| AT | Onde | Asserção-chave |
|----|------|----------------|
| AT-001 | `test_api_simulate_ipi.py` | `total_ipi == aliquota × valor_base`; `fonte_legal_ipi == dispositivo_legal_ref`; `"IPI"` fora de `tributos_nao_incluidos` |
| AT-002 | idem + `test_ipi_resolucao.py` | `ipi_situacao == "NAO_TRIBUTADO"`, `ipi_percentual is None`, total não cresce, `ipi_nao_resolvido` vazio |
| AT-003 | idem | `ipi_situacao == "NCM_NAO_ENCONTRADO"`, status **200**, item presente em `ipi_nao_resolvido`, `total_ipi is None` |
| AT-004 | `test_api_simulate_ipi.py` (fake cursor com contador) | `execute` chamado 1×; argumento contém os N NCMs distintos normalizados |
| AT-005 | idem | payload só de serviço: `pool.connection` nunca chamado; `ipi_situacao == "NAO_APLICAVEL"` |

**Dois testes além dos AT, por causa das decisões novas:**

- pool `None` → todos os itens `CONSULTA_INDISPONIVEL`, resposta 200 (prova de que a feature é
  aditiva: é o estado de toda a suíte atual e de qualquer deploy sem Cloud SQL).
- pool que levanta `ConnectionError` → 200, não 5xx (Decisão 2), com situação distinta de
  `NCM_NAO_ENCONTRADO`.

Testes existentes que **devem continuar passando sem edição** —
`tests/test_escopo_e_compensacao.py` (exige `"IPI"` em `tributos_nao_incluidos` sem banco) e
`tests/test_api_simulate.py`. Se algum precisar mudar, é sinal de regressão de contrato, não de
teste desatualizado.

---

## Error Handling

| Error Type | Handling Strategy | HTTP | Retry? |
|------------|---------------------|------|--------|
| NCM não existe na TIPI | `ipi_situacao=NCM_NAO_ENCONTRADO` no item + entrada em `ipi_nao_resolvido` | 200 | Não — reenviar não muda |
| NCM em formato não reconhecível (parcial, vazio, `EX`) | Mesmo tratamento, sem consultar o banco | 200 | Não |
| NCM com `nao_tributado = true` | `NAO_TRIBUTADO` — resolvido, contribui 0,00; nunca "0%" | 200 | N/A |
| Cloud SQL fora do ar / timeout / grant faltando | `CONSULTA_INDISPONIVEL` em todos os itens de mercadoria + `logger.exception` | 200 | Sim, pelo cliente |
| `db_pool is None` (sem `DB_INSTANCE_CONNECTION_NAME`) | Idem, sem log de exceção — é estado esperado, não falha | 200 | N/A |
| `psycopg` não instalado no processo | Import tardio dentro de `consultar_ipi_com_seguranca` → `ImportError` capturado como indisponibilidade | 200 | N/A |
| Item `natureza=SERVICO` | `NAO_APLICAVEL`, sem lookup | 200 | N/A |

Nada nesta feature introduz um novo código de erro. É proposital: o IPI é aditivo ao que a
simulação já entrega, e nenhum modo de falha dele justifica invalidar os demais tributos.

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `DB_INSTANCE_CONNECTION_NAME` | string | — | Já existente (`api/db.py`); ausente ⇒ IPI `CONSULTA_INDISPONIVEL` |
| `DB_USER` | string | `taxreformai_app` | Já existente; é o papel que precisa do `GRANT SELECT` da migração 004 |
| `verificar_ipi` (input de workflow) | `sim`/`nao` | `nao` | Novo input de `migrar_banco.yml` (Decisão 9) |

Nenhuma variável de ambiente nova na aplicação, nenhuma mudança de IaC, nenhuma migração.

---

## Security Considerations

- **Sem SQL dinâmico.** `= ANY(%s)` recebe a lista como parâmetro vinculado; o NCM ainda passa
  por `normalizar_ncm`, que só deixa passar 8 dígitos — a string que chega ao banco é sempre
  `[0-9]{4}\.[0-9]{2}\.[0-9]{2}`, jamais o texto bruto do cliente.
- **Sem RLS, deliberadamente.** `aliquotas_ipi_tipi` é dado legal público (decreto), idêntico
  para todo tenant — mesma decisão já tomada em `regras_tributarias_cache` e registrada na
  migração 004. Introduzir tenant scoping aqui contrariaria o schema existente sem proteger nada.
- **Privilégio mínimo preservado.** Só `SELECT`; a escrita continua exclusiva do papel admin via
  `scripts/ingerir_tipi.py`. Esta feature não pede grant novo.
- **Sem PII.** NCM e alíquota são dados de produto e norma pública; nada aqui entra na máscara de
  PII de `orquestracao/nos/classificador.py`.
- **Enumeração de NCM não é vazamento.** A TIPI é publicada pela RFB em PDF aberto — responder
  "este NCM não está na tabela" não revela nada que o cliente não possa baixar.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `api.ipi` quando a consulta falha — stdout do container → Cloud Logging. É o **único** sinal de que o IPI parou de funcionar em runtime (consequência aceita da Decisão 2), por isso a Decisão 9 exige verificação ativa |
| Metrics | Latência da query fica como `COULD` do DEFINE — fora de escopo |
| Tracing | N/A |
| Verificação ativa | `scripts/verificar_ipi_producao.py` + asserção de `total_ipi` no smoke test do deploy |

---

## Open Questions do DEFINE — resolvidas aqui

| # | Pergunta | Resolução |
|---|----------|-----------|
| 1 | NCM ausente: falha do item ou 422 do payload? | **Falha só do item, 200** — Decisão 1 (`A-003` confirmada) |
| 2 | Falha do Postgres: qual código HTTP? | **Nenhum — 200 com degradação declarada** — Decisão 2 (`A-001` confirmada) |

Duas questões que o DEFINE não previu e o Design precisou responder, ambas descobertas lendo o
código real: a divergência de formato de NCM entre payload e tabela (Decisão 4, que sem
tratamento faria a feature falhar em 100% do tráfego real, inclusive no smoke test do próprio
deploy) e o `GRANT SELECT` da migração 004 nunca exercitado por nenhum SELECT (Decisão 9).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-27 | design-agent | Versão inicial, a partir de `DEFINE_IPI_TIPI_MOTOR_CALCULO.md` v1.1 |

---

## Next Step

**Build concluído** — ver [BUILD_REPORT_IPI_TIPI_MOTOR_CALCULO.md](./BUILD_REPORT_IPI_TIPI_MOTOR_CALCULO.md).
Dois defeitos do `Pattern 2` foram corrigidos durante a implementação (lista vazia tratada como
indisponibilidade; ordem das guardas em `resolver_item`) — ambos registrados no BUILD REPORT.

**Ready for:** as duas verificações da Decisão 9 (`migrar_banco.yml` com `verificar_ipi=sim` e o
smoke test do `deploy.yml`), e então `/ship`.
