# DESIGN: Anexos II, III, X e XI — Redução de 60% de CBS/IBS por NBS

> Technical design for implementing ANEXOS_REDUCAO_PERCENTUAL_NBS (posição 14/17 do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NBS |
| **Date** | 2026-07-31 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md](./DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md) |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                      /v1/tax/simulate — trilha NOVA (NBS)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ItemSimulacao (natureza=SERVICO, nbs="1.2202.00.00", ...)                    │
│         │                                                                     │
│         ▼                                                                     │
│  api/nbs.py::digitos_nbs()            9 dígitos canônicos, ou None            │
│         │                                                                     │
│         ▼                                                                     │
│  api/nbs.py::prefixos_nbs()           [5,6,7,9] dígitos candidatos            │
│         │                                                                     │
│         ▼                                                                     │
│  db/repositorio.py::buscar_reducao_nbs_por_prefixo()   1 query, lote          │
│         │            (JOIN anexos_reducao_nbs_prefixo → anexos_reducao_nbs   │
│         │             → anexos_reducao_catalogo)                             │
│         ▼                                                                     │
│  api/reducao_nbs.py::consultar_com_seguranca()   nunca propaga exceção        │
│         │                                                                     │
│         ▼                                                                     │
│  api/reducao_nbs.py::resolver_item_nbs()   função PURA                        │
│    ├─ casa prefixo → agrupa por (anexo,item,sub_item) → desempate            │
│    ├─ avalia condição declaratória (nacionalidade | comprador | vendedor)     │
│    └─ devolve ResolucaoReducaoNbs (situação + percentual + refs legais)       │
│         │                                                                     │
│         ▼                                                                     │
│  api/routers/simulate.py   dispatch por natureza:                             │
│    SERVICO   → resolver_item_nbs (NOVO)                                       │
│    MERCADORIA → resolver_reducao (já shipado, INTOCADO)                       │
│         │                                                                     │
│         ▼                                                                     │
│  motor_calculo/reducoes.py::aplicar_reducao_percentual()   JÁ SHIPADO,        │
│                                                             reaproveitado      │
│         │                                                                     │
│         ▼                                                                     │
│  ReducaoItem (schemas_simulate.py)   MESMO bloco `reducao` de sempre,          │
│                                       2 campos novos opcionais                │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

   Trilha NCM (10 Anexos já shipados) roda em paralelo, intocada — Decisão 1
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db/migrations/011_anexos_reducao_percentual_nbs.sql` | Duas tabelas novas (`anexos_reducao_nbs`, `anexos_reducao_nbs_prefixo`) + 4 linhas novas no catálogo já existente (`anexos_reducao_catalogo`) | SQL puro, mesmo runner idempotente |
| `api/nbs.py` | Canonização e prefixos do vocabulário NBS — irmã de `api/ncm.py`, vocabulário PRÓPRIO (9 dígitos, não 8) | Python puro, sem I/O |
| `api/reducao_nbs.py` | Política de resolução dos 4 Anexos NBS — irmã de `api/reducao.py`, mecanismo de condição PRÓPRIO (gating, não upgrade) | Python puro + 1 import tardio de `db.repositorio` |
| `db/repositorio.py` (extensão) | `buscar_reducao_nbs_por_prefixo` — novo dataclass `PrefixoReducaoNbs`, nova query, SEM tocar as funções NCM existentes | psycopg |
| `api/schemas_simulate.py` (extensão) | 3 campos novos em `ItemSimulacao` (`nbs`, `conteudo_nacional_majoritario`, `vendedor_capital_brasileiro_qualificado`); 2 campos novos em `ReducaoItem` | Pydantic v2 |
| `api/routers/simulate.py` (extensão) | Dispatch por `natureza`: SERVICO chama a trilha NBS nova, MERCADORIA continua chamando a trilha NCM já shipada | FastAPI |
| `motor_calculo/reducoes.py` | **Nenhuma mudança** — `aplicar_reducao_percentual` já aceita qualquer `Decimal` de 0 a 1 como fração removida | Python puro (reaproveitado) |

---

## Key Decisions

### Decisão 1: Tabelas NOVAS e dedicadas para NBS — nunca comingle com as tabelas NCM

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O Achado crítico 4 do `/define` prova que um prefixo NBS truncado na fronteira "posição apenas" (`12203`, 5 caracteres) tem o MESMO comprimento que um prefixo NCM válido de 5 dígitos. Uma consulta por `prefixo = ANY(%s)` contra uma tabela única não sabe de qual vocabulário uma string de dígitos veio.

**Choice:** Duas tabelas novas — `anexos_reducao_nbs` (item, análoga a `anexos_reducao`) e `anexos_reducao_nbs_prefixo` (prefixo, análoga a `anexos_reducao_ncm`) — com sua PRÓPRIA query em `db/repositorio.py` (`buscar_reducao_nbs_por_prefixo`), nunca uma cláusula `WHERE vocabulario = 'NBS'` numa tabela compartilhada. `anexos_reducao_catalogo` (metadado por ANEXO — ordem, percentual, assunto, artigo) é reaproveitado, porque ele não é vocabulário-específico: II/III/X/XI são Anexos novos, não competem com os 10 já carregados, e ganham 4 linhas novas na mesma tabela.

**Rationale:** A separação de campo/coluna sem separação de tabela/consulta seria uma convenção de nomenclatura, não uma garantia — exatamente o que o Achado crítico 4 do `/define` proíbe. Duas tabelas tornam a colisão estruturalmente impossível (a query NBS nunca lê uma linha NCM, e vice-versa), sem exigir um discriminador que alguém poderia esquecer de filtrar.

**Alternatives Rejected:**
1. Tabela única com coluna `vocabulario` (`'NCM'`/`'NBS'`) e `WHERE vocabulario = 'NBS' AND prefixo = ANY(%s)` — rejeitado porque um `WHERE` esquecido (erro de programador, não de dado) faria um prefixo de 5 dígitos casar entre vocabulários silenciosamente; a proteção viraria disciplina de code review, não de schema.
2. Reaproveitar `anexos_reducao_ncm` alargando `prefixo` para 9 caracteres e aceitando NBS ali — rejeitado pelo mesmo motivo, e ainda pioraria a legibilidade da tabela NCM já estável (5 features a usam).

**Consequences:**
- Duas tabelas a mais para manter, mas cada uma com uma única responsabilidade (mesma filosofia de `api/ipi.py` vs `api/reducao.py`).
- O catálogo (`anexos_reducao_catalogo`) cresce de 10 para 14 linhas, mas continua sendo A fonte única de ordem/percentual/assunto por Anexo — nenhuma duplicação de fato entre Python e banco.

---

### Decisão 2: Vocabulário e canonização NBS — 9 dígitos, prefixo em (5, 6, 7, 9)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O Achado crítico 1 do `/define` documenta o formato `C.PPPP.SS.II` (9 dígitos), com truncamento observado em exatamente 4 fronteiras: 5 (posição), 6 (posição + 1 dígito de subposição), 7 (posição + subposição completa) e 9 (completo) — nunca 8 (item parcial), nunca outro classificador de topo além de "1".

**Choice:** `api/nbs.py::digitos_nbs(bruto)` exige EXATAMENTE 9 dígitos E o primeiro dígito igual a `"1"` — qualquer outra coisa devolve `None` (mesma disciplina injetiva de `digitos_ncm`). `prefixos_nbs(codigo)` gera candidatos em `_COMPRIMENTOS_PREFIXO_NBS = (5, 6, 7, 9)` — lista fechada, não intervalo, mesma razão de `_COMPRIMENTOS_PREFIXO` do NCM: um comprimento inventado (8, por exemplo) que nunca aparece na lei casaria com nada, e um falso negativo mudo é pior que recusar.

**Rationale:** A Assunção A-002 do `/define` ("classificador de topo sempre '1'") não está confirmada contra fonte oficial (inacessível). Em vez de deixar a validação frouxa "esperando" outro valor aparecer, a canonização REJEITA qualquer código que não comece com "1" — isso transforma a assunção não-validada num guard explícito (`NBS_NAO_RECONHECIDO`, nunca um match silenciosamente errado) em vez de uma esperança silenciosa. Se um Anexo futuro citar um código NBS com outro classificador de topo, o sistema recusa (ruidosamente, no dado) em vez de fingir que sabe — mesma filosofia de "nunca estimar" do resto do projeto.

**Alternatives Rejected:**
1. Aceitar qualquer comprimento entre 5 e 9 (intervalo, análogo a `range`) — rejeitado: nenhuma evidência de comprimento 8 nos 90 códigos observados; aceitá-lo silenciosamente casaria uma consulta malformada com um prefixo que a lei nunca escreveu.
2. Não validar o classificador de topo (aceitar qualquer 1º dígito) — rejeitado: contradiz a Assunção A-002, que pede validação explícita, não uma aceitação tácita.

**Consequences:**
- Um Anexo futuro com classificador de topo diferente de "1" (se a Assunção A-002 se provar falsa) exigirá uma migração de código em `digitos_nbs`, documentada e revisada — não uma regressão silenciosa.
- O item 29 do Anexo III (`1.2301.99.0`, 8 dígitos após remover pontuação — 1 a menos que o padrão) NUNCA será alcançável por um prefixo de comprimento 8 (fora da lista); ver Decisão 6 para o tratamento dessa anomalia específica.

---

### Decisão 3: Mecanismo de condição declaratória — GATING, não upgrade (nova situação `CONDICAO_NAO_SATISFEITA`)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O Achado crítico 2 do `/define` já nomeia a inversão de polaridade: nos Anexos IV/V/VI (já shipados), 60% é o PADRÃO e a condição de comprador faz a alíquota IR A ZERO (upgrade). Nos Anexos X e XI desta feature, não existe padrão nenhum — a alíquota GERAL da fase é o default, e 60% só nasce quando uma condição declaratória é satisfeita (gating). Tratar os dois mecanismos com a mesma forma de dado (`zero_por_comprador_ref`, que assume "60% é o piso") produziria ou "60% incondicional" (superestima o benefício) ou "nunca 60%" (esconde um benefício real) — os dois extremos que o `/define` proíbe.

**Choice:** Novo enum `SituacaoReducaoNbs` com um valor que NÃO existe no lado NCM: `CONDICAO_NAO_SATISFEITA` — o item bate com um Anexo/item NBS que EXIGE uma condição (nacionalidade de conteúdo, ou comprador/vendedor qualificado), mas a condição não foi informada ou é falsa. Neste caso: `aplicada = False` (a alíquota geral da fase é o que se aplica), mas a resposta cita explicitamente o Anexo/item que SERIA aplicável e qual dispositivo/condição destravaria os 60% (`condicao_pendente_ref`), com um booleano espelho de `zero_por_comprador_disponivel`: `reducao_condicionada_disponivel`.

Quando o item NBS bate e NÃO exige nenhuma condição (Anexos II e III inteiros; itens do Anexo X mapeados aos incisos que dispensam nacionalidade — ver Decisão 5), a situação é `APLICADA` direto, sem nenhuma pergunta ao payload.

**Rationale:** `aplicada=True` com `percentual_reducao=0` (a alternativa mais simples) colidiria com `ReducaoResumo.anexos_aplicados` ("quais Anexos de fato moveram o número") e com `itens_com_reducao_aplicada` — um item que não recebeu NENHUM benefício real não pode contar como "redução aplicada" nesses agregados, ou o resumo financeiro mentiria por omissão para o controller que o `/define` identificou como usuário. Uma situação nova e nomeada (`CONDICAO_NAO_SATISFEITA`) mantém a mesma disciplina de "seis situações, nunca um booleano" que `SituacaoReducao` (NCM) já usa.

**Alternatives Rejected:**
1. `situacao=APLICADA` sempre que o item bate, com `percentual_reducao=0` quando a condição falta — rejeitado pela contaminação de `anexos_aplicados`/`itens_com_reducao_aplicada` acima.
2. Reaproveitar `FORA_DO_ANEXO` quando a condição falta — rejeitado: `FORA_DO_ANEXO` significa "este código não está em nenhum Anexo", uma afirmação falsa para um item que ESTÁ no Anexo XI, só não com condição provada; o auditor perderia a informação mais valiosa (qual condição destravaria o benefício).

**Consequences:**
- `resolver_item_nbs` tem uma responsabilidade a mais que `resolver_item` (NCM): avaliar uma condição booleana OU composta (comprador OU vendedor, para o Anexo XI) antes de decidir a situação final.
- O router (`api/routers/simulate.py`) precisa de um `elif` novo (item NÃO avaliado mas também não em `itens_nao_avaliados` — é uma terceira categoria: "avaliado, resolvido, sem benefício por falta de condição"), documentado no Data Flow abaixo.

---

### Decisão 4: Dois eixos de condição do Anexo XI modelados como colunas por ITEM, não por Anexo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O art. 142, I (comprador = órgão público) vale para QUALQUER item do Anexo XI. O art. 142, II (vendedor = sócio brasileiro ≥20%) vale SÓ para o subconjunto de "segurança da informação/segurança cibernética" (plausivelmente 1.1 e 1.3, por descrição — não todos os 5 itens NBS resolvíveis). Duas condições, de eixos diferentes (comprador vs. vendedor), com abrangência diferente dentro do MESMO Anexo — não cabe numa única coluna de catálogo por Anexo (o catálogo já tem `zero_por_comprador_ref`, mas seu papel semântico é "condição que ZERA", o oposto do que o Anexo XI precisa).

**Choice:** Três colunas nullable em `anexos_reducao_nbs` (a tabela de ITEM, não a de catálogo):
- `condicao_nacionalidade_ref` — Anexo X, não-nula nos itens cujo inciso exige conteúdo nacional majoritário.
- `condicao_comprador_ref` — Anexo XI, não-nula em TODOS os 5 itens NBS resolvíveis (art. 142, I vale para qualquer um).
- `condicao_vendedor_ref` — Anexo XI, não-nula SÓ nos itens de segurança da informação/cibernética do Bloco 1 (art. 142, II).

A condição efetiva de um item é: nenhuma coluna preenchida → sempre satisfeita; só `condicao_nacionalidade_ref` → exige `conteudo_nacional_majoritario is True`; `condicao_comprador_ref` e/ou `condicao_vendedor_ref` → exige `comprador_tipo == ORGAO_PUBLICO` OU (`condicao_vendedor_ref` não-nula E `vendedor_capital_brasileiro_qualificado is True`) — um OU entre os dois eixos, nunca E.

**Rationale:** Modelar por ITEM (não por Anexo) é o único jeito de expressar corretamente que nem todo item do Anexo XI tem a opção do vendedor — colocar a condição no catálogo (nível Anexo) forçaria todos os 5 itens a aceitarem a mesma condição, o que é factualmente errado para os itens 1.2, 1.13 e 1.14 (manutenção de aplicativos, veículos e equipamentos militares — não são "segurança da informação/cibernética").

**Alternatives Rejected:**
1. Uma única coluna `condicao_geral_ref` com texto livre — rejeitado: perde a distinção entre "qual eixo" (comprador vs. vendedor), que o payload precisa para saber QUAL campo checar, e o resolvedor precisaria fazer parsing de texto para decidir a lógica — dado derivado de string é exatamente o antipadrão que `_tipo_correspondencia` já evita em `api/reducao.py`.
2. Estender `zero_por_comprador_ref` do catálogo para cobrir também "condição que HABILITA" — rejeitado: o nome e a semântica existente (upgrade de 60%→0%) contradiriam o uso novo (gating de geral→60%); dois comportamentos diferentes por trás do mesmo nome de coluna é a mesma classe de risco que já motivou o rename `cesta_basica_anexo_i` → `anexos_reducao` (Decisão da feature anterior).

**Consequences:**
- `_avaliar_condicao` em `api/reducao_nbs.py` precisa ler até 3 campos por linha vencedora, mas a lógica é uma função pura de poucas linhas, testável isoladamente (AT-010, AT-011, AT-012).
- Item 9 do Anexo II e itens sem código (X 49-54, XI 1.6/1.7/1.10/1.11/1.12) simplesmente NÃO recebem linha em `anexos_reducao_nbs` — mesma disciplina de "documentar como não resolvido", nunca uma linha com `texto_nbs = NULL` fingindo ser resolvível.

---

### Decisão 5: Mapeamento item→inciso do art. 139 (nacionalidade, Anexo X) é responsabilidade do `/build`, com verificação obrigatória contra fonte primária

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` verificou que os incisos I, II, III e VII do art. 139 exigem nacionalidade e que IV, V e VI não exigem — mas não mapeou, item a item, quais dos 47 itens NBS do Anexo X pertencem a qual inciso (isso ficou explicitamente como trabalho de granularidade do `/design`/`/build`).

**Choice:** Este `/design` NÃO inventa o mapeamento a partir de memória. O `/build` desta feature deve, como parte da migração 011, ler o texto integral do Anexo X (mesma URL já qualificada pelo `/define`) e classificar cada um dos 47 itens NBS ao inciso correspondente ANTES de decidir o valor de `condicao_nacionalidade_ref` — mesma disciplina de verificação de fonte primária já seguida por todas as 5 features anteriores desta leva. Isso é trabalho de dado (preencher a migração 011 corretamente), não trabalho de arquitetura — por isso não bloqueia este `/design`.

**Rationale:** Uma DESIGN document que "decidisse" o mapeamento sem reler a fonte reintroduziria exatamente o risco que o `/define` já preveniu para os 142 itens (nenhum código aceito de memória). O mecanismo (coluna nullable, condição gating) é o que o `/design` precisa fixar; o CONTEÚDO da coluna é dado, e dado só é confiável depois de lido.

**Alternatives Rejected:**
1. Assumir "nacionalidade sempre exigida" para todos os 47 itens do Anexo X (mais simples, mas superestimaria a restrição para os itens dos incisos IV/V/VI — eventos acadêmicos, feiras de negócios, exposições/galerias/mostras — que a lei não restringe).
2. Assumir "nacionalidade nunca exigida" (mais simples, mas concederia 60% a produções estrangeiras que a lei não beneficia — exatamente o erro que o `/define` chama de "risco oposto").

**Consequences:**
- O BUILD_REPORT desta feature precisa registrar explicitamente a leitura e a classificação item-a-inciso como um passo de verificação de fonte primária, com URL e data — mesmo padrão dos 5 builds anteriores.
- Até essa classificação existir, nenhum item do Anexo X pode ser inserido com `condicao_nacionalidade_ref` adivinhado.

---

### Decisão 6: Anomalia do item 29 (Anexo III) — texto literal preservado, prefixo completado com nota

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O texto oficial publica `1.2301.99.0` para o item 29 (Esterilização) — 8 dígitos após remover pontuação, 1 a menos que todo item de nível "item" (2 dígitos finais) nos 4 Anexos. Um prefixo armazenado literalmente com 8 dígitos NUNCA seria alcançado por `prefixos_nbs()` (candidatos são 5/6/7/9, nunca 8) — o item ficaria permanentemente inatingível, silenciosamente.

**Choice:** `texto_nbs` (coluna de auditoria, mostrada na resposta) preserva a grafia literal da fonte (`"1.2301.99.0"`). O `prefixo` armazenado (coluna usada para casar) é completado para 9 dígitos assumindo que o dígito faltante é o "0" final do par de item (`"123019900"`) — mesma convenção dos demais itens de 2 dígitos do nível "item". A migração 011 documenta esta decisão inline, com comentário citando a anomalia e a suposição, no mesmo espírito de `CHECK`s de auditoria já usados (`dispositivo_cita_o_proprio_item`).

**Rationale:** A alternativa de "nunca resolver este item" (deixá-lo fora da tabela, como os itens sem código) trataria uma anomalia de transcrição como se fosse ausência de código — categorias diferentes que o `/define` já pede para nunca confundir. Completar com nota explícita é "correção documentada", não "correção silenciosa" — a diferença que o `/define` exige.

**Alternatives Rejected:**
1. Deixar o item 29 fora da tabela (tratado como "sem código") — rejeitado: mistura a categoria "anomalia de transcrição" com a categoria "célula vazia na fonte", que o `/define` trata como fatos distintos.
2. Armazenar o prefixo com 8 dígitos e estender `_COMPRIMENTOS_PREFIXO_NBS` para incluir 8 só por causa deste item — rejeitado: criaria um comprimento aceito no vocabulário inteiro por causa de uma única anomalia, arriscando casar uma consulta real de 8 dígitos truncados (se um dia existir) com este item por engano.

**Consequences:**
- Uma linha na migração 011 carrega um comentário mais longo que o normal, documentando a suposição — aceitável, mesmo padrão de "nota sobre anomalia" já usado no `/define`.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/011_anexos_reducao_percentual_nbs.sql` | Create | Tabelas `anexos_reducao_nbs`/`anexos_reducao_nbs_prefixo` + 4 linhas novas no catálogo (II, III, X, XI); leitura/classificação item-a-inciso do Anexo X contra fonte primária (Decisão 5) | @database-reviewer | None |
| 2 | `api/nbs.py` | Create | `digitos_nbs`/`prefixos_nbs` — canonização e prefixos do vocabulário NBS (Decisão 2) | @python-developer | None |
| 3 | `db/repositorio.py` | Modify | Novo dataclass `PrefixoReducaoNbs` + `buscar_reducao_nbs_por_prefixo` (append, sem tocar funções existentes) | @database-reviewer | 1 |
| 4 | `api/reducao_nbs.py` | Create | `SituacaoReducaoNbs`, `ResolucaoReducaoNbs`, `ConsultaReducaoNbs`, `consultar_com_seguranca`, `resolver_item_nbs` (Decisões 3, 4) | @python-developer | 2, 3 |
| 5 | `api/schemas_simulate.py` | Modify | 3 campos novos em `ItemSimulacao` (`nbs`, `conteudo_nacional_majoritario`, `vendedor_capital_brasileiro_qualificado`); 2 campos novos em `ReducaoItem` (`condicao_pendente_ref`, `reducao_condicionada_disponivel`) | @python-developer | None |
| 6 | `api/routers/simulate.py` | Modify | Dispatch por `natureza`: SERVICO chama `resolver_item_nbs`, MERCADORIA chama `resolver_reducao` (já existente, intocado); nova consulta em lote de prefixos NBS | @python-developer | 4, 5 |
| 7 | `tests/test_nbs.py` | Create | Unit tests de `digitos_nbs`/`prefixos_nbs` (canonização, truncamento parcial, rejeição de classificador ≠ "1") | @test-generator | 2 |
| 8 | `tests/test_reducao_nbs.py` | Create | Unit tests de `resolver_item_nbs` — AT-001, AT-002, AT-003, AT-004, AT-006, AT-008, AT-009, AT-010, AT-011, AT-012, AT-015 (função pura, sem banco) | @test-generator | 4 |
| 9 | `tests/test_reducao_nbs_db.py` | Create | Integration tests contra Postgres real (CI) — schema aplicado, `buscar_reducao_nbs_por_prefixo`, zero regressão dos 10 Anexos NCM (AT-014) | @test-generator | 1, 3 |
| 10 | `tests/test_simulate_nbs.py` | Create | E2E via `TestClient` — AT-005, AT-007, AT-013 (itens NCM minoritários de X/XI nunca recebem 60% "por acidente") | @test-generator | 6 |
| 11 | `.github/workflows/migrar_banco.yml` | Modify | Novo passo `verificar_reducao_nbs` (mesmo padrão de `verificar_reducao`) chamando `scripts/verificar_reducao_nbs_producao.py` | @ci-cd-specialist | 1 |
| 12 | `scripts/verificar_reducao_nbs_producao.py` | Create | Verificação real contra Cloud SQL — mesmo padrão de `verificar_reducao_producao.py` | @database-reviewer | 1, 3 |
| 13 | `.github/workflows/deploy.yml` | Modify | Novo smoke-test call citando um item NBS real (ex. Anexo II, item 4) | @ci-cd-specialist | 6 |
| 14 | `CLAUDE.md` | Modify | Atualizar tabela de features + estrutura + estado do runbook | (nenhum — feito no `/ship`) | — |

**Total Files:** 13 (+ CLAUDE.md no `/ship`)

---

## Agent Assignment Rationale

> Agentes descobertos no roteamento do projeto (ver tabela "Agentes recomendados" do `CLAUDE.md`).

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @database-reviewer | 1, 3, 12 | Schema PostgreSQL (migração, CHECK constraints, query em lote) — mesmo agente usado nas 5 migrações anteriores desta leva |
| @python-developer | 2, 4, 5, 6 | Motor de cálculo e API em Python puro (dataclasses, type hints) — mesmo agente usado em `api/ncm.py`/`api/reducao.py`/`api/ipi.py` |
| @test-generator | 7, 8, 9, 10 | Testes pytest (unit + integration + E2E), padrão já estabelecido pelas 5 features anteriores |
| @ci-cd-specialist | 11, 13 | Workflows do GitHub Actions (`migrar_banco.yml`, `deploy.yml`) |
| @security-reviewer | (revisão, não arquivo) | Recomendado antes do `/ship`, mesma cautela já aplicada às features anteriores que tocam `comprador_tipo`/condições declaratórias — aqui há DOIS campos booleanos novos que também são autodeclarados, não verificados (mesma natureza de risco de "cliente mente sobre nacionalidade/capital social") |

---

## Code Patterns

### Pattern 1: `api/nbs.py` — canonização e prefixos (espelha `api/ncm.py`)

```python
"""Canonização e hierarquia de códigos NBS (Nomenclatura Brasileira de Serviços).

Vive separado de `api/ncm.py` porque o vocabulário NÃO é NCM com pontuação
diferente: 9 dígitos (não 8), com um classificador de topo fixo ("1", único
valor observado nos 90 códigos dos Anexos II/III/X/XI) e truncamento parcial
observado numa fronteira que a NCM não tem (1 dígito dentro da subposição).

Ver Decisão 2 do DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md.
"""

import re

_SO_DIGITOS = re.compile(r"\D")

# 5 = posição (C+PPPP), 6 = posição + 1º dígito da subposição (truncamento
# parcial, ex. "1.2201.1"), 7 = posição + subposição completa, 9 = código
# completo (C+PPPP+SS+II). NUNCA 8: nenhuma evidência de truncamento parcial
# do "item" nos 90 códigos observados — ver Decisão 2 (Assunção A-002/A-006).
_COMPRIMENTOS_PREFIXO_NBS = (5, 6, 7, 9)


def digitos_nbs(bruto: str) -> str | None:
    """9 dígitos canônicos começando em "1", ou None.

    Diferente de `digitos_ncm`, também valida o classificador de topo: a
    Assunção A-002 do DEFINE (todo código observado começa com "1") não está
    confirmada contra a fonte oficial do NBS (inacessível). Em vez de aceitar
    qualquer 1º dígito silenciosamente, a função recusa o que não bate com o
    único padrão observado — erra para o lado de NBS_NAO_RECONHECIDO, nunca
    para o lado de um match não verificável.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")
    if len(digitos) != 9 or not digitos.startswith("1"):
        return None
    return digitos


def prefixos_nbs(codigo: str) -> list[str]:
    """Os 4 prefixos hierárquicos aceitos de um código de 9 dígitos."""
    return [codigo[:n] for n in _COMPRIMENTOS_PREFIXO_NBS]
```

### Pattern 2: `api/reducao_nbs.py` — situação e resolução (mecanismo de gating)

```python
"""Resolve os 4 Anexos de redução de 60% de CBS/IBS por NBS (II, III, X, XI).

Irmão de `api/reducao.py`, mas com um mecanismo de condição estruturalmente
diferente (ver Decisão 3 do DESIGN): lá, a condição de comprador faz a
alíquota IR A ZERO a partir de um padrão de 60% (upgrade). Aqui, não existe
padrão — a alíquota GERAL da fase é o default, e 60% só nasce quando uma
condição declaratória (nacionalidade de conteúdo, comprador OU vendedor
qualificado) é satisfeita (gating). É por isso que existe uma situação nova,
`CONDICAO_NAO_SATISFEITA`, que não tem equivalente do lado NCM.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from api.nbs import digitos_nbs

logger = logging.getLogger("api.reducao_nbs")

SESSENTA_POR_CENTO = Decimal("0.6000")


class SituacaoReducaoNbs(StrEnum):
    APLICADA = "APLICADA"
    CONDICAO_NAO_SATISFEITA = "CONDICAO_NAO_SATISFEITA"
    FORA_DO_ANEXO = "FORA_DO_ANEXO"
    NBS_NAO_RECONHECIDO = "NBS_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == MERCADORIA, ou nbs ausente


@dataclass(frozen=True)
class ConsultaReducaoNbs:
    disponivel: bool
    linhas: Any = field(default_factory=tuple)


@dataclass(frozen=True)
class ResolucaoReducaoNbs:
    situacao: SituacaoReducaoNbs
    anexo: str | None = None
    anexo_ordem: int | None = None
    item: str | None = None
    percentual_reducao: Decimal | None = None
    dispositivo_legal_ref: str | None = None
    # Preenchido sempre que a linha vencedora TEM alguma condição (satisfeita
    # ou não) — nunca só quando falta, para o auditor ver a fundamentação
    # inteira mesmo no caso feliz (mesma disciplina de
    # `dispositivo_legal_comprador` do lado NCM).
    condicao_pendente_ref: str | None = None
    # True só quando a condição existe E não foi satisfeita — espelha
    # `zero_por_comprador_disponivel`, com a polaridade invertida (aqui,
    # "disponível" significa "poderia ter ganhado 60% e não ganhou").
    reducao_condicionada_disponivel: bool = False
    descricao: str | None = None
    descricao_contexto: str | None = None
    texto_nbs: str | None = None
    itens_correspondentes: tuple[tuple[str, str], ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoReducaoNbs.APLICADA


def _condicao_satisfeita(
    linha: Any,
    comprador_tipo: str | None,
    conteudo_nacional_majoritario: bool | None,
    vendedor_capital_brasileiro_qualificado: bool | None,
) -> bool:
    """Nenhuma condição na linha → sempre satisfeita (Anexos II/III; itens do
    X cujo inciso não exige nacionalidade). Ver Decisão 4 — comprador OU
    vendedor, nunca E; `ENTIDADE_CEBAS_SUS` NUNCA satisfaz o eixo comprador
    aqui (só `ORGAO_PUBLICO` tem base no art. 142, I — AT-012)."""
    if linha.condicao_nacionalidade_ref is not None:
        return conteudo_nacional_majoritario is True
    condicoes_xi = linha.condicao_comprador_ref is not None or (
        linha.condicao_vendedor_ref is not None
    )
    if condicoes_xi:
        comprador_ok = (
            linha.condicao_comprador_ref is not None
            and comprador_tipo == "ORGAO_PUBLICO"
        )
        vendedor_ok = (
            linha.condicao_vendedor_ref is not None
            and vendedor_capital_brasileiro_qualificado is True
        )
        return comprador_ok or vendedor_ok
    return True


def resolver_item_nbs(
    natureza: str,
    nbs: str | None,
    consulta: ConsultaReducaoNbs,
    comprador_tipo: str | None = None,
    conteudo_nacional_majoritario: bool | None = None,
    vendedor_capital_brasileiro_qualificado: bool | None = None,
) -> ResolucaoReducaoNbs:
    """Função pura — mesma disciplina de `api/reducao.py::resolver_item`."""
    if natureza != "SERVICO" or not nbs:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.NAO_APLICAVEL)

    codigo = digitos_nbs(nbs)
    if codigo is None:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.NBS_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.CONSULTA_INDISPONIVEL)

    por_item: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_item[(linha.anexo, linha.item, linha.sub_item)].append(linha)

    if not por_item:
        return ResolucaoReducaoNbs(SituacaoReducaoNbs.FORA_DO_ANEXO)

    # Desempate por especificidade — mesma fórmula do lado NCM (Achado
    # crítico 3): prefixo mais longo primeiro, depois ordem do documento legal
    # (Anexo, item, sub-item). Percentual é sempre 0.6 nos 4 Anexos NBS, então
    # o 2º componente da chave NCM (percentual efetivo) não se aplica aqui.
    candidatas = [max(linhas, key=lambda linha: len(linha.prefixo)) for linhas in por_item.values()]
    vencedora = max(
        candidatas,
        key=lambda linha: (len(linha.prefixo), -linha.anexo_ordem, -linha.item, -linha.sub_item),
    )

    satisfeita = _condicao_satisfeita(
        vencedora,
        comprador_tipo,
        conteudo_nacional_majoritario,
        vendedor_capital_brasileiro_qualificado,
    )
    tem_condicao = (
        vencedora.condicao_nacionalidade_ref is not None
        or vencedora.condicao_comprador_ref is not None
        or vencedora.condicao_vendedor_ref is not None
    )
    condicao_ref = (
        vencedora.condicao_nacionalidade_ref
        or vencedora.condicao_comprador_ref
        or vencedora.condicao_vendedor_ref
    )

    itens_correspondentes = tuple(
        sorted(
            ((linha.anexo, linha.item, linha.sub_item) for linha in candidatas),
        )
    )

    return ResolucaoReducaoNbs(
        situacao=(
            SituacaoReducaoNbs.APLICADA
            if satisfeita
            else SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA
        ),
        anexo=vencedora.anexo,
        anexo_ordem=vencedora.anexo_ordem,
        item=_formatar_item(vencedora.item, vencedora.sub_item),
        percentual_reducao=SESSENTA_POR_CENTO if satisfeita else None,
        dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
        condicao_pendente_ref=condicao_ref if tem_condicao else None,
        reducao_condicionada_disponivel=tem_condicao and not satisfeita,
        descricao=vencedora.descricao,
        descricao_contexto=vencedora.descricao_contexto,
        texto_nbs=vencedora.texto_nbs,
        itens_correspondentes=tuple(
            (anexo, _formatar_item(item, sub)) for anexo, item, sub in itens_correspondentes
        ),
    )


def _formatar_item(item: int, sub_item: int) -> str:
    return f"{item}.{sub_item}" if sub_item else str(item)
```

### Pattern 3: Migração — extensão do catálogo + tabelas novas

```sql
-- 011_anexos_reducao_percentual_nbs.sql
-- Estende anexos_reducao_catalogo (metadado por Anexo, vocabulário-agnóstico)
-- com os 4 Anexos novos, e cria DUAS tabelas dedicadas ao vocabulário NBS —
-- nunca comingladas com anexos_reducao/anexos_reducao_ncm (Decisão 1).

ALTER TABLE anexos_reducao_catalogo DROP CONSTRAINT catalogo_conhecido;
ALTER TABLE anexos_reducao_catalogo ADD CONSTRAINT catalogo_conhecido CHECK (
    (anexo, anexo_ordem, percentual_reducao) IN (
        ('I',1,1.0), ('II',2,0.6), ('III',3,0.6), ('IV',4,0.6), ('V',5,0.6),
        ('VI',6,0.6), ('VII',7,0.6), ('VIII',8,0.6), ('IX',9,0.6),
        ('X',10,0.6), ('XI',11,0.6),
        ('XII',12,1.0), ('XIII',13,1.0), ('XV',15,1.0))
);

INSERT INTO anexos_reducao_catalogo
       (anexo, anexo_ordem, percentual_reducao, assunto, artigo_ref, zero_por_comprador_ref) VALUES
 ('II',  2, 0.6, 'Educação',                                  'LCP 214/2025, art. 129', NULL),
 ('III', 3, 0.6, 'Saúde',                                     'LCP 214/2025, art. 130', NULL),
 ('X',  10, 0.6, 'Produções artísticas/culturais/audiovisuais','LCP 214/2025, art. 139', NULL),
 ('XI', 11, 0.6, 'Soberania e segurança nacional/cibernética', 'LCP 214/2025, art. 142', NULL)
ON CONFLICT (anexo) DO NOTHING;

CREATE TABLE anexos_reducao_nbs (
    anexo                      VARCHAR(4)  NOT NULL REFERENCES anexos_reducao_catalogo(anexo),
    item                       SMALLINT    NOT NULL CHECK (item >= 1),
    sub_item                   SMALLINT    NOT NULL DEFAULT 0 CHECK (sub_item >= 0),
    -- NULL = item existe na lei mas sem código citável (célula vazia OU
    -- "pendente de classificação" — distinguidos por `situacao_codigo`).
    texto_nbs                  TEXT,
    situacao_codigo            VARCHAR(24) NOT NULL DEFAULT 'ATRIBUIDO'
        CHECK (situacao_codigo IN ('ATRIBUIDO', 'CELULA_VAZIA', 'PENDENTE_CLASSIFICACAO')),
    descricao                  TEXT        NOT NULL,
    descricao_contexto         TEXT,
    dispositivo_legal_ref      TEXT        NOT NULL,
    -- Ver Decisão 4 — nulas quando o item não exige a condição.
    condicao_nacionalidade_ref TEXT,
    condicao_comprador_ref     TEXT,
    condicao_vendedor_ref      TEXT,
    -- texto_nbs só é obrigatório quando a situação é ATRIBUIDO.
    CONSTRAINT texto_nbs_xor_sem_codigo CHECK (
        (situacao_codigo = 'ATRIBUIDO' AND texto_nbs IS NOT NULL)
        OR (situacao_codigo <> 'ATRIBUIDO' AND texto_nbs IS NULL)
    ),
    PRIMARY KEY (anexo, item, sub_item)
);

CREATE TABLE anexos_reducao_nbs_prefixo (
    anexo    VARCHAR(4)  NOT NULL,
    item     SMALLINT    NOT NULL,
    sub_item SMALLINT    NOT NULL DEFAULT 0,
    -- Ver Decisão 2 — só os 4 comprimentos observados; espelha
    -- api/nbs.py::_COMPRIMENTOS_PREFIXO_NBS.
    prefixo  VARCHAR(9)  NOT NULL
        CHECK (prefixo ~ '^1[0-9]*$' AND length(prefixo) IN (5, 6, 7, 9)),
    texto_nbs TEXT NOT NULL,
    FOREIGN KEY (anexo, item, sub_item)
        REFERENCES anexos_reducao_nbs (anexo, item, sub_item) ON DELETE CASCADE,
    UNIQUE (anexo, item, sub_item, prefixo)
);

CREATE INDEX idx_anexos_reducao_nbs_prefixo ON anexos_reducao_nbs_prefixo (prefixo);

-- Item 29 do Anexo III (Esterilização): fonte publica "1.2301.99.0" (8
-- dígitos, 1 a menos que o padrão). `texto_nbs` preserva a grafia literal;
-- o prefixo casável é completado para 9 dígitos assumindo o dígito faltante
-- é o "0" final do par de item — ver Decisão 6. NÃO um comprimento aceito
-- a mais na CHECK acima: é uma completude pontual desta linha, documentada
-- aqui, não uma mudança de vocabulário.
-- INSERT INTO anexos_reducao_nbs (anexo, item, ..., dispositivo_legal_ref) VALUES
--   ('III', 29, ..., 'LCP 214/2025, art. 130, Anexo III, item 29');
-- INSERT INTO anexos_reducao_nbs_prefixo (anexo, item, prefixo, texto_nbs) VALUES
--   ('III', 29, '123019900', '1.2301.99.0');  -- ver comentário acima

-- (INSERTs completos dos 90 itens NBS + 4 catálogo ficam no /build, após a
-- leitura/classificação item-a-inciso do Anexo X exigida pela Decisão 5.)

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao_nbs         TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_nbs_prefixo TO taxreformai_app';
    END IF;
END $$;
```

---

## Data Flow

```text
1. Cliente envia ItemSimulacao com natureza="SERVICO", nbs="1.2202.00.00"
   │
   ▼
2. api/routers/simulate.py agrupa nbs de TODOS os itens SERVICO do payload,
   canoniza via digitos_nbs, gera o conjunto de prefixos candidatos
   (prefixos_nbs) — mesmo padrão em lote já usado para NCM/IPI
   │
   ▼
3. UMA query (buscar_reducao_nbs_por_prefixo) traz todas as linhas candidatas
   │
   ▼
4. Por item: resolver_item_nbs() agrupa por (anexo,item,sub_item), desempata
   por especificidade, avalia a condição declaratória (se houver)
   │
   ├─ Sem condição, ou condição satisfeita → situacao=APLICADA,
   │  percentual_reducao=0.6 → aplicar_reducao_percentual() (JÁ SHIPADO)
   │
   ├─ Condição existe mas não satisfeita → situacao=CONDICAO_NAO_SATISFEITA,
   │  alíquota GERAL da fase aplicada (nenhuma chamada a
   │  aplicar_reducao_percentual) — resposta cita anexo/item + condicao_pendente_ref
   │
   └─ Nenhum match, NBS ilegível, ou consulta indisponível → alíquota geral,
      mesma disciplina de FORA_DO_ANEXO/NCM_NAO_RECONHECIDO/CONSULTA_INDISPONIVEL
   │
   ▼
5. ReducaoItem populado (MESMO bloco `reducao` de sempre) com os 2 campos
   novos preenchidos só quando relevante — item de MERCADORIA nunca os toca
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL (`anexos_reducao_nbs`, `anexos_reducao_nbs_prefixo`, `anexos_reducao_catalogo`) | SQL via `psycopg`, papel `taxreformai_app` (SELECT) | Secret Manager (já configurado) |
| `legis.senado.leg.br` (verificação de fonte primária, só em tempo de `/build`, nunca em runtime) | HTTP (leitura manual/scriptada durante o build) | Nenhuma — página pública |

Nenhuma integração nova de infraestrutura (Terraform intocado, mesmo padrão das 5 migrações anteriores).

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|-----------------|
| Unit — canonização | `digitos_nbs`, `prefixos_nbs` | `tests/test_nbs.py` | pytest | AT-002 (truncamento parcial), rejeição de classificador ≠ "1" |
| Unit — resolução | `resolver_item_nbs` (sem banco, `ConsultaReducaoNbs` fake) | `tests/test_reducao_nbs.py` | pytest | AT-001, AT-003, AT-004, AT-006, AT-008, AT-009, AT-010, AT-011, AT-012, AT-015 |
| Integration — banco real | Schema aplicado, `buscar_reducao_nbs_por_prefixo`, zero regressão NCM | `tests/test_reducao_nbs_db.py` | pytest + Postgres real (CI) | AT-014 |
| E2E — API | `TestClient` contra `/v1/tax/simulate` | `tests/test_simulate_nbs.py` | pytest + `fastapi.testclient` | AT-005, AT-007, AT-013 |
| Verificação real (produção) | `migrar_banco.yml` (`verificar_reducao_nbs=sim`) + smoke test do `deploy.yml` | `scripts/verificar_reducao_nbs_producao.py` | psycopg contra Cloud SQL real | Mesmo padrão das 5 features anteriores — nunca só teste automatizado |

**AT-003 (Achado crítico 3) merece nota própria**: precisa de um fixture com as 10 linhas do Anexo III que compartilham `1.2301.99.00`, provando que o item vencedor é o de MENOR número (18) e que os 10 aparecem em `itens_correspondentes` — comportamento herdado do desempate NCM, mas nunca antes exercitado dentro do MESMO Anexo.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| Cloud SQL indisponível/GRANT faltando | `consultar_com_seguranca` (novo, em `api/reducao_nbs.py`) nunca propaga — devolve `disponivel=False`, item vira `CONSULTA_INDISPONIVEL`, alíquota geral aplicada, `logger.exception` | Não |
| `nbs` malformado (não canoniza) | `NBS_NAO_RECONHECIDO` — mesma disciplina de `NCM_NAO_RECONHECIDO`, nunca reportado como falha de infraestrutura | Não |
| Condição declaratória ausente/falsa | `CONDICAO_NAO_SATISFEITA` — não é erro, é resposta de negócio; a citação do que destravaria o benefício é OBRIGATÓRIA na resposta | Não |
| Item do Anexo X/XI com chave NCM minoritária (fora de escopo) | Nunca chega à trilha NBS (só itens `natureza=SERVICO` com `nbs` preenchido entram); se o cliente mandar o `ncm` de um desses itens como MERCADORIA, a trilha NCM já existente devolve `FORA_DO_ANEXO`, corretamente (AT-005, AT-013) | Não |

---

## Configuration

Nenhuma configuração nova — reaproveita `DATABASE_URL`/pool já existentes (`api/db.py`).

---

## Security Considerations

- `conteudo_nacional_majoritario` e `vendedor_capital_brasileiro_qualificado` são DECLARATÓRIOS, como `comprador_tipo` e `bem_importado` já existentes — a simulação não verifica nacionalidade de obra nem composição societária real. A resposta e a documentação da API precisam deixar isso explícito, mesma disciplina de `fonte_legal` do `ReducaoResumo`.
- Nenhum dado pessoal novo é introduzido (mesma superfície de PII do payload já existente).
- Recomendado `@security-reviewer` antes do `/ship`, mesma cautela já registrada no `CLAUDE.md` para qualquer extensão de payload que carregue afirmações auto-declaradas usadas para reduzir tributo.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `api/reducao_nbs.py::consultar_com_seguranca`, mesmo padrão de `api/reducao.py` — nomeando os 4 Anexos afetados |
| Metrics | Nenhuma nova (mesma ausência de métricas dedicadas do resto do projeto) |
| Tracing | Nenhum (não usado no projeto hoje) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|-----------|
| 1.0 | 2026-07-31 | design-agent | Versão inicial. Seis decisões-chave: tabelas NBS dedicadas (Decisão 1, Achado crítico 4), canonização de 9 dígitos com classificador de topo validado (Decisão 2), mecanismo de gating com situação nova `CONDICAO_NAO_SATISFEITA` em vez de reaproveitar o upgrade já usado por IV/V/VI (Decisão 3, Achado crítico 2), condições do Anexo XI modeladas por ITEM em 2 eixos independentes — comprador OU vendedor (Decisão 4), mapeamento item-a-inciso do Anexo X deferido ao `/build` com verificação obrigatória de fonte primária (Decisão 5), e tratamento documentado da anomalia de 1 dígito do item 29/Anexo III (Decisão 6). `motor_calculo/` permanece sem nenhuma mudança — `aplicar_reducao_percentual` já shipada é inteiramente reaproveitável. |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md`
