# DESIGN: Cesta Básica Nacional (Anexo I) — redução a zero de CBS/IBS por NCM

> Technical design para representar os 26 itens do Anexo I da LCP 214/2025 num schema novo,
> resolver os **6 itens de correspondência não-trivial** (1, 8, 15, 19, 20, 23) — **todos os 6
> nesta iteração** — e aplicar alíquota zero de CBS/IBS por item em `POST /v1/tax/simulate`,
> sem introduzir nenhuma dependência de infraestrutura em `motor_calculo/`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REGRAS_TRIBUTARIAS_CACHE |
| **Date** | 2026-07-28 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_REGRAS_TRIBUTARIAS_CACHE.md](./DEFINE_REGRAS_TRIBUTARIAS_CACHE.md) |
| **BRAINSTORM** | [BRAINSTORM_REGRAS_TRIBUTARIAS_CACHE.md](./BRAINSTORM_REGRAS_TRIBUTARIAS_CACHE.md) |
| **Status** | ✅ Shipped (ver `SHIPPED_2026-07-28.md`) |
| **Posição na sequência** | 2 de 11 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Verificação de fonte primária feita nesta sessão de `/design`

O DEFINE transcreveu os 26 itens em forma resumida e deixou os itens 19 e 20 sem os códigos
literais das exceções ("salmonídeos, atuns, bacalhau, hadoque, saithe e outros excluídos por
subposição"). Sem esses códigos não há como escrever a migração. Esta sessão **rebuscou a mesma
fonte primária do DEFINE e transcreveu o Anexo I inteiro, literalmente**:

| # | O que | URL | Resultado |
|---|-------|-----|-----------|
| 1 | Texto integral do Anexo I (26 itens) | `https://legis.senado.leg.br/norma/40180341/publicacao/40180888` | HTTP 200; transcrição literal completa na seção "Dados — Anexo I transcrito" |
| 2 | Corpo da LCP 214/2025 (arts. 1º a 544) | `https://legis.senado.leg.br/norma/40180341/publicacao/40181429` | HTTP 200; arts. 125, 126, 343-348 lidos no texto oficial |

Consultados em 2026-07-28. Esta é a mesma fonte que o DEFINE já qualificou como primária (espelho
oficial do DOU no portal do Senado); `planalto.gov.br` continua inacessível deste ambiente.

**Três achados de fonte primária que o DEFINE não tinha** — os três mudam o design:

1. **A redução a zero vale na fase de teste de 2026** (Decisão 5). O art. 348, III, "a" diz
   literalmente que as alíquotas dos arts. 343 e 346 "serão aplicadas com a respectiva redução no
   caso das operações sujeitas a alíquota reduzida". Sem essa verificação, o design teria de
   escolher entre aplicar zero por suposição ou recusar a feature inteira — 2026 é hoje a **única**
   fase que `/simulate` consegue calcular.
2. **Os itens 19 e 20 têm 19 códigos de exceção, não "dois itens com exceção"** — e o item 19 usa
   um prefixo de **7 dígitos** (`0210.99.1`), comprimento que nenhuma outra parte do projeto tinha
   encontrado até aqui.
3. **Existe uma segunda sobreposição entre itens, não notada pelo DEFINE**: os itens **4 e 26**
   citam o mesmo código `2106.90.90` (o DEFINE só registrou a sobreposição 15/25). Isso torna a
   regra de desempate uma necessidade, não um refinamento (Decisão 4).

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│  POST /v1/tax/simulate — com redução a zero da Cesta Básica por item          │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  [Cliente ERP] ──X-API-Key──► api/routers/simulate.py                         │
│                                     │                                         │
│      ┌──────────────────────────────┼───────────────────────────────┐         │
│      │ (1) ANTES do laço            │                               │         │
│      ▼                              ▼                               ▼         │
│  api/ncm.py                api/cesta_basica.py                api/ipi.py      │
│  digitos_ncm()             consultar_com_seguranca            (já existente)  │
│  prefixos_ncm()  ─────────────►     │  nunca levanta                │         │
│  (4→8 dígitos)                      ▼                               ▼         │
│                    db/repositorio.buscar_cesta_basica_por_prefixo   │         │
│                                     │  1 query / request            │         │
│                                     ▼                               ▼         │
│                       ┌─────────────────────────────┐        aliquotas_       │
│                       │ Cloud SQL                   │        ipi_tipi         │
│                       │ cesta_basica_anexo_i (26)   │                         │
│                       │ cesta_basica_anexo_i_ncm(95)│  GRANT SELECT ao papel  │
│                       │   76 inclusões + 19 exceções│  taxreformai_app        │
│                       └─────────────────────────────┘  (migração 005)         │
│                                                                               │
│      │ (2) POR item de MERCADORIA                                             │
│      ▼                                                                        │
│  cesta_basica.resolver_item(ncm) ──► SituacaoCestaBasica ∈                    │
│      │        {APLICADA, EXCLUIDA_EXPRESSAMENTE, FORA_DO_ANEXO,               │
│      │         NCM_NAO_RECONHECIDO, CONSULTA_INDISPONIVEL, NAO_APLICAVEL}     │
│      │                                                                        │
│      ▼ APLICADA?                                                              │
│  motor_calculo/reducoes.aplicar_reducao_a_zero(ResultadoCalculo)              │
│      │   CBS=0, IBS=0, IS intacto, valor_liquido recomposto                   │
│      │   (Python puro, ZERO infra — engine.py NÃO é tocado)                   │
│      ▼                                                                        │
│  ItemDetalhado.cesta_basica{item, dispositivo_legal_ref, ...}                 │
│      │                                                                        │
│      ▼ (3) agregação                                                          │
│  RespostaSimulacao.cesta_basica = CestaBasicaResumo(total_cbs_dispensado, …)  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

Fluxo de degradação (Decisão 8) — a simulação NUNCA falha e NUNCA some com CBS/IBS:

  Banco fora do ar ──► CONSULTA_INDISPONIVEL ─┐
  NCM ilegível     ──► NCM_NAO_RECONHECIDO ───┼──► 200 + alíquota GERAL da fase
  NCM fora do Anexo──► FORA_DO_ANEXO ─────────┤    (idêntico ao comportamento de hoje)
  NCM excluído (19/20)► EXCLUIDA_EXPRESSAMENTE┘    + advertência declarando o que faltou
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db/migrations/005_cesta_basica_anexo_i.sql` | **Novo** — 2 tabelas + seed dos 26 itens/95 prefixos + `GRANT SELECT` | SQL puro |
| `db/migrations/006_remover_regras_tributarias_cache.sql` | **Novo** — `DROP TABLE regras_tributarias_cache` com guarda de "está vazia?" | SQL puro |
| `db.repositorio.PrefixoCestaBasica` | **Novo** — dataclass frozen espelhando o JOIN item×prefixo | `dataclasses` |
| `db.repositorio.buscar_cesta_basica_por_prefixo` | **Novo** — 1 query, `WHERE prefixo = ANY(%s)`; propaga exceção | `psycopg` + SQL |
| `db.repositorio.buscar_regra_cache` / `RegraTributariaCache` | **Removidos** — código morto cuja tabela deixa de existir (Decisão 12) | — |
| `api/ncm.py` | **Novo** — `digitos_ncm()` (canoniza para 8 dígitos) e `prefixos_ncm()` (gera os 5 prefixos 4→8) | Python puro |
| `api.ipi.normalizar_ncm` | **Modificado** — passa a delegar a `api/ncm.py`; assinatura e comportamento idênticos | Python puro |
| `api/cesta_basica.py` | **Novo** — `SituacaoCestaBasica`, `ResolucaoCestaBasica`, `ConsultaCestaBasica`, `consultar_com_seguranca`, `resolver_item` | Python + `logging` |
| `motor_calculo/reducoes.py` | **Novo** — `aplicar_reducao_a_zero(ResultadoCalculo)` puro, sem infra | Python puro |
| `motor_calculo/regras_fiscais.py` | **Modificado** — `RegraFiscal.fonte_legal_reducoes` | `dataclasses` |
| `motor_calculo/tabela_aliquotas.py` | **Modificado** — seed de `fonte_legal_reducoes` nas 2 fases | Python puro |
| `api/schemas_simulate.py` | **Modificado** — `CestaBasicaItem` em `ItemDetalhado`, `CestaBasicaResumo` na resposta | `pydantic.BaseModel` |
| `api/routers/simulate.py` | **Modificado** — 1 lookup antes do laço, override por item, agregação e advertência | FastAPI `APIRouter` |
| `scripts/verificar_cesta_basica_producao.py` | **Novo** — prova o `GRANT SELECT` e o seed contra o Cloud SQL real, com o papel de runtime | Python + `psycopg` |

---

## Key Decisions

### Decision 1: toda correspondência é prefixo de dígitos — "exato" é o caso de prefixo de 8

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `MUST` do DEFINE sobre os 6 itens não-triviais; `A-003` |

**Context:** O DEFINE classifica os 26 itens em três tipos de correspondência — EXATO (20 itens),
PREFIXO puro (8, 15, 23), MISTO (1) e PREFIXO+EXCEÇÃO (19, 20) — e trata isso como três
semânticas de matching diferentes, que o schema teria de distinguir com um campo
`tipo_correspondencia`.

**Choice:** Não são três semânticas. A NCM/SH é um código hierárquico de largura fixa: capítulo
(2 dígitos) → posição (4) → subposição (5 ou 6) → item (7) → subitem (8). "Posição 09.01",
"subposição 1902.1", "subposição 1006.20" e "código 0405.10.00" são **todos prefixos** do código
de 8 dígitos da mercadoria — só variam em comprimento (4, 5, 6 e 8).

O schema guarda, portanto, **uma única forma**: um prefixo de dígitos de 4 a 8 caracteres, mais um
booleano `excecao` dizendo se aquele prefixo inclui ou exclui. Os 26 itens do Anexo I viram 95
linhas: 76 inclusões e 19 exceções. A regra de correspondência é:

```text
item do Anexo I casa com o código  ⟺  (∃ inclusão do item que é prefixo do código)
                                       ∧ (∄ exceção DO MESMO ITEM que é prefixo do código)
código está na Cesta Básica        ⟺  ∃ item do Anexo I que casa
```

Com isso, **os 6 itens não-triviais são resolvidos nesta iteração** — não sobra nenhum item
"não resolvido", e o `MUST` do DEFINE é atendido pelo caminho forte (resolver), não pelo caminho
de escape (declarar não resolvido).

**Rationale:**

1. **A alternativa (dois mecanismos: igualdade para 20 itens, prefixo para 6) teria duas
   implementações do mesmo conceito** e um `tipo_correspondencia` que o código precisaria ler para
   decidir *como* comparar. Um erro de classificação de um item viraria um falso negativo
   silencioso — exatamente o modo de falha que o DEFINE proíbe.
2. **O texto da lei não distingue.** O Anexo I mistura livremente "posição", "subposição" e
   "código" dentro de um mesmo item (o item 1 tem duas subposições e um código; o item 19,
   alínea a, tem duas posições, um código e uma subposição). Um schema que separasse EXATO de
   PREFIXO teria de quebrar o item 1 em duas tabelas ou repetir o item em duas linhas com
   semânticas diferentes.
3. **`tipo_correspondencia` continua existindo — mas como saída, não como entrada.** É derivado
   (`len(prefixo) == 8 → "EXATO"`, senão `"PREFIXO"`), aparece na resposta para auditoria, e não
   participa da decisão de matching. Dado derivado não pode divergir do dado que o gera.

**Alternatives Rejected:**

1. **Coluna `tipo_correspondencia` como enum de entrada, com um caminho de código por tipo** —
   rejeitado pelos motivos 1 e 3.
2. **Marcar os 6 itens como "não resolvidos nesta iteração"** (opção que o DEFINE deixa aberta) —
   rejeitado: os 6 incluem café, arroz, massas, carnes, peixes e mate, ou seja, o núcleo da cesta
   básica. Entregar a feature sem eles cobriria manteiga e margarina e deixaria de fora o que
   qualquer usuário testaria primeiro. E, uma vez que a correspondência é prefixo em todos os
   casos, resolver 20 ou resolver 26 é o mesmo código.
3. **Expandir os prefixos em códigos de 8 dígitos na carga** (materializar "09.01" nos ~100
   subitens possíveis) — rejeitado: exigiria a tabela completa da NCM (que o projeto não tem, e
   cuja ingestão é outra feature), e inventaria códigos que o Anexo I não escreveu — o oposto da
   disciplina "nenhuma inferência além do que a lei escreve literalmente" (Out of Scope do DEFINE).

---

### Decision 2: o prefixo é expandido do lado da consulta; o SQL continua sendo igualdade exata

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** Dada a Decisão 1, a consulta natural seria `WHERE %s LIKE prefixo || '%%'` ou
`WHERE starts_with(%s, prefixo)` — SQL que compara *ao contrário* do usual (a coluna é o prefixo,
o parâmetro é o valor longo), não usa índice, e precisa de um `unnest` para o lote de até 100
códigos do payload.

**Choice:** O Python gera, para cada código de 8 dígitos, seus **5 prefixos candidatos**
(comprimentos 4, 5, 6, 7 e 8) e a query continua sendo o mesmo idioma da TIPI:

```sql
WHERE p.prefixo = ANY(%s)     -- lista de até 5 × 100 = 500 strings, deduplicada
```

O comprimento mínimo (4) e o máximo (8) são fixados **nos dois lados e de forma acoplada**: o
gerador produz exatamente 4..8, e a tabela tem `CHECK (prefixo ~ '^[0-9]{4,8}$')`.

**Rationale:**

1. **Uma linha que o gerador não consegue enxergar é um falso negativo permanente e silencioso.**
   Se um dia alguém inserir um prefixo de capítulo (2 dígitos, ex. "02") para outro Anexo, ele
   nunca casaria com nada — a mercadoria simplesmente não receberia o benefício, sem erro, sem
   log, sem sintoma. O `CHECK` transforma esse cenário numa falha ruidosa **no INSERT da
   migração**, meses antes de virar um número errado numa resposta. É a mesma técnica da
   constraint `aliquota_xor_nao_tributado` da migração 004: fazer o banco recusar o estado que o
   código não sabe representar.
2. **Um só idioma de SQL no repositório.** `= ANY(%s)` com lista Python é exatamente o que
   `buscar_ipi_por_ncm` já faz; quem revisar as duas funções não precisa aprender dois modelos de
   consulta, e a proteção contra injeção é a mesma (parâmetro vinculado, nunca concatenação).
3. **Não depende do tamanho da tabela.** A alternativa "carregar as 95 linhas e casar em Python"
   funciona hoje e deixa de funcionar quando os outros 16 Anexos entrarem (milhares de linhas,
   incluindo NBS) — e o ponto de troca seria descoberto por latência em produção, não por
   revisão.
4. 4 dígitos é o nível mais amplo que o **Anexo I** usa (posição, ex. "02.07"); nenhum item cita
   capítulo. O limite não é uma suposição sobre a NCM em geral, é uma leitura do dado que está
   sendo carregado — e está registrado como acoplamento explícito no comentário da migração e no
   docstring de `prefixos_ncm`.

**Alternatives Rejected:**

1. **`starts_with`/`LIKE` no SQL** — rejeitado: seq scan, idioma novo, e move a definição de "o que
   conta como prefixo" para dentro de uma string SQL onde o `CHECK` não consegue espelhá-la.
2. **`SELECT *` das 95 linhas e matching todo em Python** — rejeitado pelo motivo 3. (Continua
   sendo a implementação certa se um dia o dado voltar a ser pequeno *e* estático — o registro
   fica aqui.)
3. **Gerar prefixos de 2 a 8** (7 candidatos, sem `CHECK` de comprimento mínimo) — rejeitado:
   removeria o acoplamento, mas também removeria a única barreira que impede alguém de carregar
   um prefixo de 3 dígitos (que não existe na NCM) achando que funciona.

---

### Decision 3: duas tabelas — o item do Anexo é a entidade, o prefixo é o detalhe 1:N

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Requisito "cardinalidade 1:N entre item e código/prefixo" do Data Contract |

**Context:** O DEFINE exige que o schema represente item (1-26), múltiplos códigos por item,
exceções, `dispositivo_legal_ref` e a descrição literal. `regras_tributarias_cache` tem uma linha
por NCM, sem entidade "item".

**Choice:**

```text
cesta_basica_anexo_i          (item PK 1..26, descricao, dispositivo_legal_ref)      26 linhas
cesta_basica_anexo_i_ncm      (item FK, prefixo, excecao, alinea, texto_ncm)         95 linhas
                                                        └ 76 inclusões + 19 exceções
```

Sem RLS nas duas (dado legal público, mesma decisão já registrada em `aliquotas_ipi_tipi` e na
migração 002). Sem `ano_vigencia`: o Anexo I não tem dimensão temporal própria — a versão de
"produção de efeitos futura" é o Anexo XVIII, explicitamente fora de escopo.

A exceção é **escopada ao item** (`excecao` mora na linha, que tem `item` como FK), não global.

**Rationale:**

1. **A citação legal é por item, não por código.** `dispositivo_legal_ref` = "LCP 214/2025,
   art. 125, Anexo I, item 5" é a mesma string para os 6 códigos do item 2 e para os 18 do item
   19. Repeti-la em 95 linhas é convite a divergência; normalizá-la é o desenho óbvio.
2. **A exceção é local ao item porque a lei a escreve assim.** O item 19, alínea d, diz "02.07,
   0209.90.00 e 0210.99.1, **exceto** os produtos dos códigos 0207.43.00 e 0207.53.00" — a
   exclusão qualifica aquele item, não a lei inteira. Com exceção global, uma exclusão do item 20
   poderia anular uma inclusão do item 19 sem que ninguém tivesse escrito isso. Hoje as duas
   listas são disjuntas (capítulo 02 × capítulo 03) e os dois modelos dariam a mesma resposta — a
   diferença só apareceria com a chegada de outro Anexo, e aí já seria um bug em produção.
3. **`texto_ncm` guarda a grafia literal do DOU** ("1006.20", "02.07", "0210.99.1", "2106.9090"),
   não só os dígitos. É o que permite a constraint da Decisão 11 e o que a resposta cita ao
   cliente — "casou com a posição 02.07" é auditável, "casou com 0207" não é a grafia da lei.
4. **`alinea`** ('a'..'d', NULL nos 24 itens sem alíneas) preserva a estrutura dos itens 19 e 20.
   Não participa do matching; existe para auditoria e para o dia em que uma exceção precisar ser
   escopada por alínea em vez de por item.

**Alternatives Rejected:**

1. **Tabela única com `item` e `dispositivo_legal_ref` repetidos em 95 linhas** — rejeitado pelo
   motivo 1.
2. **Exceções em tabela separada** (`cesta_basica_anexo_i_excecao`) — rejeitado: a exceção tem
   exatamente as mesmas colunas de uma inclusão e é consultada pela mesma query (uma exceção só
   importa quando é prefixo do código, igual à inclusão). Duas tabelas idênticas exigiriam duas
   queries ou um `UNION` para responder a mesma pergunta.
3. **Reaproveitar `regras_tributarias_cache` acrescentando colunas** — rejeitado no brainstorm
   (Key Decision 4) e confirmado aqui: sobrariam `aliquota_cbs/ibs/is`, `ano_vigencia` e
   `regime_especial`, cinco colunas sem valor a preencher. Ver Decisão 12 para o destino dela.

---

### Decision 4: quando mais de um item casa, vence o mais específico — e a resposta lista todos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `COULD` do DEFINE (sobreposição 15/25) + achado novo desta sessão (4/26) |

**Context:** O DEFINE registrou como `COULD` que o item 15 (massas, subposição `1902.1`) contém o
item 25 (massas de baixo teor de proteína, `1902.19.00`). A transcrição literal desta sessão
mostra uma **segunda** sobreposição, não registrada: os itens **4** (fórmulas infantis) e **26**
(fórmulas dietoterápicas para erros inatos do metabolismo) citam **o mesmo código**
`2106.90.90`/`2106.9090`. Portanto "qual item citar" não é uma curiosidade: acontece com dois
pares e precisa ser determinístico.

**Choice:** Regra de desempate em duas etapas, aplicada ao conjunto de itens que casaram:

| Critério | Ordem | Efeito nos casos reais |
|----------|-------|------------------------|
| 1º Prefixo mais **longo** (mais específico) | desc | `1902.19.00` (8) do item 25 vence `1902.1` (5) do item 15 |
| 2º **Menor** número de item | asc | empate em 8 dígitos entre 4 e 26 → cita o item 4 |

E a resposta traz `itens_correspondentes: [15, 25]` / `[4, 26]` além do item citado.

**Rationale:**

1. **Não há conflito jurídico a resolver — os dois itens dão zero.** A redução do art. 125 é a
   zero, não um percentual: casar dois itens não gera dupla contagem nem ambiguidade de valor. O
   desempate é só sobre *qual dispositivo citar*, e o mais específico é o que descreve melhor o
   produto (o item 25 fala do produto para aminoacidopatias; o item 15, de massas em geral).
2. **Listar todos evita a pergunta óbvia do auditor.** Um fiscal que veja "item 25" numa massa
   comum perguntaria por que não o 15. `itens_correspondentes` responde sem que ninguém precise
   reler o Anexo.
3. **Ordenação total e determinística.** Comprimento e número de item são ambos totais; não existe
   par que empate nos dois. A resposta é a mesma independentemente da ordem em que o Postgres
   devolveu as linhas — que é justamente o tipo de não-determinismo que só aparece em produção.

**Alternatives Rejected:**

1. **Citar o menor número de item sempre** — rejeitado: `1902.19.00` citaria o item 15 (massas
   alimentícias), descrição menos precisa que a do item 25 para o mesmo produto.
2. **Erro/recusa quando mais de um item casa** — rejeitado: seria transformar uma redundância
   deliberada do legislador em falha do produto.
3. **Deduplicar os itens 15/25 e 4/26 na carga** (remover a linha "redundante") — rejeitado: a
   carga precisa ser transcrição fiel do Anexo. Apagar `1902.19.00` do item 25 perderia a
   descrição que existe justamente para o público de aminoacidopatias.

---

### Decision 5: a redução a zero vale na fase de teste de 2026 — verificado no texto oficial

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Questão não prevista pelo DEFINE |

**Context:** `/simulate` só consegue calcular **2026** hoje (2027-2028 tem a CBS pendente do art.
347 e devolve 422 antes do laço; 2029+ nem existe em `TabelaAliquotasSeed`). Se a redução do art.
125 não valesse durante a fase de teste, esta feature não teria nenhum ano em que produzir efeito
— e aplicá-la mesmo assim seria inventar direito. O DEFINE não faz essa pergunta.

**Choice:** A redução **vale em 2026**, e a resposta cita o dispositivo que o autoriza. Dois
caminhos independentes do texto oficial levam ao mesmo lugar:

| Caminho | Dispositivo | Texto |
|---------|-------------|-------|
| Direto | **art. 125**, caput | "Ficam reduzidas a zero as alíquotas do IBS e da CBS incidentes sobre as vendas de produtos [...] relacionados no Anexo I" — sem condicionar a ano ou fase |
| Transição | **art. 348, III, "a"** | "as alíquotas do IBS e da CBS previstas nos arts. 343 e 346 [...] serão aplicadas com a respectiva redução no caso das operações sujeitas a alíquota reduzida, no âmbito de regimes diferenciados de tributação" |

Para 2027-2028 os equivalentes são o **art. 344, parágrafo único, I** (IBS) e o **art. 347, § 1º,
I** (CBS) — seeds registrados mesmo sem uso hoje, porque a fase é recusada por outro motivo.

Isso entra no modelo como `RegraFiscal.fonte_legal_reducoes`, ao lado de `fonte_legal_compensacao`
— conhecimento de fase mora em `motor_calculo/tabela_aliquotas.py`, onde já moram todas as outras
citações por fase.

**Rationale:**

1. **Ressalva honesta, registrada em vez de escondida:** o art. 125 está no **Título III, Capítulo
   II** ("Da Cesta Básica Nacional de Alimentos"), enquanto os arts. 344/347/348 falam de
   "regimes diferenciados de tributação", que é o **Título IV**. Literalmente, a cesta básica não
   está dentro do Título IV. Essa lacuna textual **não muda o resultado**, porque o art. 125
   aplica-se por si — ele reduz a zero "as alíquotas do IBS e da CBS", sem remeter a nenhuma
   alíquota-padrão.
2. **O que o art. 125 importa do art. 126 reforça a leitura.** Seu parágrafo único manda aplicar
   apenas os **§§ 1º e 2º** do art. 126 (importação e procedimento de alteração da lista). Ele
   **não** importa o § 4º — que é exatamente o parágrafo que amarra as reduções do Título IV às
   "alíquotas-padrão fixadas na forma do art. 14". A ausência dessa amarra é o que impede alguém
   de argumentar que a redução da cesta básica só existe sobre a alíquota-padrão.
3. **O legislador sabe excluir quando quer.** O próprio art. 348, III, "c" exclui expressamente os
   optantes do Simples Nacional das alíquotas de 2026. Não há exclusão análoga para a cesta
   básica.
4. **Uma citação por fase, não uma constante no `api/`.** Se a frase morasse em
   `api/cesta_basica.py`, a resposta citaria o art. 348 (regra de 2026) numa simulação de 2027 tão
   logo aquela fase deixe de ser recusada — um erro de citação que ninguém veria.

**Alternatives Rejected:**

1. **Aplicar a redução sem citar a regra de transição** — rejeitado: num produto que se vende como
   auditável, "por que zero se a alíquota de 2026 é 0,9%?" é a primeira pergunta do usuário, e a
   resposta está no art. 348, III, "a".
2. **Restringir a redução a 2027+** — rejeitado: contraria o art. 348, III, "a", e esvaziaria a
   feature (nenhuma fase calculável restaria).
3. **Assumir sem verificar** — rejeitado por política do projeto; foi o que motivou a busca da
   fonte primária nesta sessão.

---

### Decision 6: o override é função pura em `motor_calculo/reducoes.py`, não em `engine.py` nem no router

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Constraint do DEFINE: "override por item, aplicado depois de `engine.calcular()`, sem tocar `motor_calculo/engine.py`" |

**Context:** `engine.calcular()` resolve CBS/IBS **por fase**, uniforme para todos os itens — não
existe hoje conceito de alíquota por produto. Zerar CBS e IBS de um item não é só apagar dois
números: `ResultadoCalculo` carrega `total_tributos` e `valor_liquido`, e o `valor_liquido` do
split payment é `valor_base - total_tributos`. Um override que zere CBS/IBS e esqueça o
`valor_liquido` produz uma resposta internamente contraditória (líquido menor que o bruto sem
tributo que o justifique).

**Choice:** Um módulo novo `motor_calculo/reducoes.py`, Python puro e sem nenhum import de
infraestrutura, com uma função:

```text
aplicar_reducao_a_zero(resultado, *, split_payment_active=True) -> ResultadoCalculo
    valor_cbs      = 0,00
    valor_ibs      = 0,00
    valor_is       inalterado  (art. 125 reduz apenas IBS e CBS)
    total_tributos = valor_is
    valor_liquido  = valor_base - total_tributos   (ou valor_base, se split inativo)
```

`engine.py` não é tocado. O router chama `engine.calcular(...)` e, só quando a situação é
`APLICADA`, passa o resultado por essa função.

**Rationale:**

1. **A invariante é do motor, então mora no motor.** `valor_liquido = valor_base -
   total_tributos` é definida em `engine.calcular`. Se o recálculo morasse em `api/`, uma futura
   mudança na composição do líquido (por exemplo, split payment parcial) seria feita no motor e o
   `api/` continuaria recompondo pela fórmula antiga — divergência silenciosa entre dois arquivos
   que ninguém lê juntos. Estando no mesmo pacote, aparecem lado a lado em qualquer busca por
   `valor_liquido`.
2. **Respeita a constraint do DEFINE ao pé da letra:** aplicado *depois* de `engine.calcular()`,
   sem tocar `engine.py`, e sem acrescentar nenhuma dependência de infraestrutura a
   `motor_calculo/` — o módulo novo importa apenas `dataclasses`, `decimal` e `ResultadoCalculo`.
3. **Testável sem banco e sem HTTP**, incluindo a asserção da invariante
   (`valor_liquido == valor_base - total_tributos` depois da redução), que é a única forma de
   pegar o erro descrito no Context.
4. **`split_payment_active` é parâmetro explícito, não inferido.** Seria possível deduzir se o
   split estava ativo comparando `valor_liquido` com `valor_base - total_tributos`, mas isso é
   adivinhação sobre o passado de um objeto. Hoje o router usa o default (`True`) nos dois lugares;
   o docstring registra que os dois valores precisam ser o mesmo, e um teste cobre o ramo
   `split_payment_active=False`.

**Alternatives Rejected:**

1. **Parâmetro `zerar_cbs_ibs=True` em `engine.calcular()`** — rejeitado: o DEFINE proíbe tocar
   `engine.py`, e com razão — o motor passaria a receber uma decisão que depende de um lookup em
   banco, abrindo caminho para alguém injetar a consulta lá dentro e quebrar a garantia de
   "motor_calculo roda sem infraestrutura".
2. **Aritmética inline no laço do router** — rejeitado pelo mesmo motivo da Decisão 6 do DESIGN de
   `IPI_TIPI_MOTOR_CALCULO`: vira um bloco não testável isoladamente, e aqui carregaria uma
   invariante do motor.
3. **Uma `TabelaAliquotas` alternativa que devolva zeros** — rejeitado: `TabelaAliquotas.buscar`
   é indexada por fase, não por item; precisaria de uma instância por item e faria `engine`
   recalcular tudo por item com uma regra falsa, cujo `fonte_legal` mentiria sobre a fase.

---

### Decision 7: `SituacaoCestaBasica` tem 6 estados — e "excluído pelo próprio Anexo" é um deles

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | AT-002, AT-003, AT-004 |

**Context:** Com um booleano `cesta_basica: bool`, cinco situações radicalmente diferentes viram
`false`: produto fora do Anexo, produto **expressamente excluído** pelo Anexo (foie gras, salmão),
NCM ilegível, banco fora do ar e item de serviço.

**Choice:**

| Situação | Significado | CBS/IBS do item | Campos preenchidos |
|----------|-------------|------------------|--------------------|
| `APLICADA` | Casou com ≥1 item do Anexo I | **zero** | item, dispositivo, descrição, `texto_ncm`, tipo, `itens_correspondentes`, percentuais sem redução, valores dispensados, fonte da transição |
| `EXCLUIDA_EXPRESSAMENTE` | Casou com a inclusão de um item **e** com uma exceção do mesmo item | alíquota geral da fase | item, dispositivo, `texto_ncm` da exceção, tipo=`EXCECAO` |
| `FORA_DO_ANEXO` | NCM válido, nenhum item casou | alíquota geral da fase | — |
| `NCM_NAO_RECONHECIDO` | O código informado não canoniza para 8 dígitos | alíquota geral da fase | — |
| `CONSULTA_INDISPONIVEL` | Banco fora do ar / não configurado | alíquota geral da fase | — |
| `NAO_APLICAVEL` | `natureza == "SERVICO"` | alíquota geral da fase | — |

**Rationale:**

1. **`EXCLUIDA_EXPRESSAMENTE` é a resposta mais valiosa que esta feature dá.** "Seu produto está
   na posição 02.07, mas o Anexo I exclui expressamente o código 0207.43.00" é uma informação
   jurídica que o cliente não obteria de outra forma, e é o oposto de `FORA_DO_ANEXO` do ponto de
   vista de quem revisa uma classificação fiscal. Achatar as duas em "não tem benefício"
   descartaria o trabalho que a Decisão 1 fez para representar as exceções.
2. **`NCM_NAO_RECONHECIDO` ≠ `FORA_DO_ANEXO`.** Dizer "este produto não está na cesta básica"
   quando não se conseguiu nem ler o código é uma afirmação jurídica falsa emitida por omissão —
   a mesma razão que levou `SituacaoIpi` a separar `NCM_NAO_ENCONTRADO` de
   `CONSULTA_INDISPONIVEL`.
3. **`NAO_APLICAVEL` é preenchido no ramo de serviço explicitamente**, nunca por default do
   modelo Pydantic — mesma consequência já registrada na Decisão 3 do DESIGN da feature 1: um
   default silencioso faria um item de mercadoria com bug reportar "não se aplica".

**Alternatives Rejected:**

1. **Booleano + texto na advertência** — rejeitado: obriga o ERP a fazer parsing de português.
2. **Reusar `SituacaoIpi`** — rejeitado: os estados não coincidem (`NAO_TRIBUTADO` não existe
   aqui, `EXCLUIDA_EXPRESSAMENTE` não existe lá) e acoplaria dois tributos independentes.

---

### Decision 8: falha do lookup nunca apaga CBS/IBS — degrada para a alíquota geral, e declara

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** Na feature do IPI, um lookup indisponível fazia `total_ipi` virar `null` (Decisão 5
de lá). Aqui o lookup indisponível incide sobre **CBS e IBS**, que são o produto central da
simulação e hoje nunca são nulos.

**Choice:** Nenhum código de erro, nenhum campo nulo em CBS/IBS. Falha de consulta →
`CONSULTA_INDISPONIVEL` em todos os itens de mercadoria → **alíquota geral da fase**, que é
exatamente o que a API devolve hoje → 200. A resposta declara o ocorrido em
`cesta_basica.itens_nao_avaliados` e na advertência do escopo, dizendo que o valor pode estar
**superestimado**.

**Rationale:**

1. **A degradação é conservadora.** Não aplicar uma redução produz um tributo **maior** que o
   devido, nunca menor. Num simulador fiscal, errar para cima é recuperável (o cliente pergunta);
   errar para baixo é uma provisão insuficiente. A direção do erro é o que separa este caso do
   IPI, onde o número ausente era o próprio tributo.
2. **Zerar/anular `total_cbs` seria uma regressão de contrato** provocada por uma feature
   aditiva — `ResumoFinanceiro.total_cbs` é `Decimal` não-anulável desde `API_HTTP_SIMULACAO`,
   e todo cliente atual depende dele.
3. **É literalmente o comportamento de hoje.** Sem `DB_INSTANCE_CONNECTION_NAME`, `get_db_pool()`
   devolve `None`; toda a suíte de testes atual e qualquer deploy sem Cloud SQL caem nesse ramo e
   produzem exatamente a resposta que produzem hoje, mais um bloco novo dizendo por quê. Isso é o
   que torna a feature aditiva e testável sem banco.
4. **Degradar não é silenciar** (mesmo princípio da Decisão 2 da feature 1): a advertência muda de
   texto, os itens não avaliados são enumerados por SKU, e `logger.exception` registra a falha no
   Cloud Logging.

**Alternatives Rejected:**

1. **422/503 quando o lookup falha** — rejeitado: derruba uma simulação correta em todos os outros
   tributos por causa de um componente aditivo, e acopla a disponibilidade do produto ao Cloud SQL.
2. **`total_cbs = null` quando a cesta básica não pôde ser verificada** — rejeitado pelo motivo 2.
3. **Aplicar zero "na dúvida"** — rejeitado: é a adivinhação que o DEFINE proíbe, e na direção
   perigosa (subestimar tributo).

---

### Decision 9: os totais dispensados são `None` quando a avaliação foi parcial

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** Consequência da Decisão 8: uma resposta pode ter 9 itens avaliados e 1 não avaliado
(NCM ilegível, por exemplo). Quanto vale, então, "o total de CBS dispensado pela cesta básica"?

**Choice:** `total_cbs_dispensado` e `total_ibs_dispensado` são `Decimal | None`, governados pelo
**mesmo predicado** que decide a advertência:

```text
avaliacao_completa = (todos os itens de MERCADORIA foram avaliados)
                     ∧ (a consulta esteve disponível)

  avaliacao_completa ──► totais = soma (inclusive 0,00, que é resposta legítima)
 ¬avaliacao_completa ──► totais = null  ∧  itens_nao_avaliados[] não vazio
```

`itens_com_reducao_aplicada` (contagem) permanece sempre preenchido: é um fato sobre o que a
resposta de fato fez, não uma estimativa do que deveria ter feito. O nome carrega o "aplicada"
justamente para não ser lido como "elegíveis".

**Rationale:** Mesma disciplina da Decisão 5 da feature 1 e de `total_pis`/`total_cofins`: um
total parcial é indistinguível de um total completo na tela de um departamento fiscal. Aqui o
número tem uso comercial direto — é o "quanto a cesta básica economizou" que o controller leva
para a diretoria (o segundo pain point do DEFINE) — e um valor subestimado por 1 item não avaliado
seria citado como se fosse o benefício integral.

**Alternatives Rejected:**

1. **Somar o que deu e confiar na advertência** — rejeitado, mesmo argumento já usado duas vezes
   no projeto.
2. **`0.00` quando indisponível** — rejeitado: afirma "nada foi economizado", que é falso.

---

### Decision 10: `api/ncm.py` — uma só noção de "NCM válido" para IPI e cesta básica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** `api/ipi.py::normalizar_ncm` já canoniza `"22030000"` → `"2203.00.00"` (Decisão 4 da
feature 1). A cesta básica precisa da mesma canonização, mas da forma **só dígitos** (para gerar
prefixos). As saídas óbvias eram importar `normalizar_ncm` do módulo de IPI e tirar os pontos, ou
repetir a regex.

**Choice:** Um módulo novo `api/ncm.py` com `digitos_ncm(bruto) -> str | None` (8 dígitos ou
`None`) e `prefixos_ncm(codigo) -> list[str]`. `api/ipi.py::normalizar_ncm` passa a ser duas
linhas sobre `digitos_ncm`, mantendo nome, assinatura e comportamento.

**Rationale:**

1. **Duas definições de "NCM válido" produziriam tratamento inconsistente do mesmo payload.** Se o
   IPI aceitasse um código que a cesta básica rejeitasse (ou vice-versa), o mesmo item apareceria
   resolvido para um tributo e "não reconhecido" para outro, na mesma resposta — um bug
   praticamente indiagnosticável pelo cliente.
2. **Raio de alteração mínimo, invariante forte:** `tests/test_ipi_resolucao.py` cobre
   `normalizar_ncm` nos formatos pontuado, só-dígitos, parcial, vazio e lixo, e **deve continuar
   passando sem uma linha de edição**. Se precisar mudar, é regressão, não teste desatualizado.
3. `api/ncm.py` não conhece IPI nem cesta básica — é vocabulário de domínio (a NCM/SH), não de
   feature.

**Alternatives Rejected:**

1. **`from api.ipi import normalizar_ncm` em `api/cesta_basica.py`** — rejeitado: acopla duas
   features independentes por um detalhe de formatação e sugere hierarquia onde não há.
2. **Repetir a regex** — rejeitado pelo motivo 1.

---

### Decision 11: o seed mora dentro da migração, e o banco recusa transcrição inconsistente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** A TIPI (feature 1) veio de um PDF de 9231 linhas, com parser (`db/tipi.py`) e script
de ingestão (`scripts/ingerir_tipi.py`) disparado por workflow. O Anexo I são 95 linhas
transcritas à mão de uma tabela do DOU. Repetir o aparato de ingestão aqui seria construir um
pipeline para um dado que nunca chega duas vezes.

**Choice:** O `INSERT` dos 26 itens e das 95 linhas de prefixo vai **dentro da migração 005**, com
a URL da fonte e a data de acesso no cabeçalho do arquivo. Sem script, sem passo de workflow novo
para carregar dado. E a migração declara duas constraints que tornam a transcrição verificável
pela própria máquina:

```sql
-- O prefixo é derivado da grafia literal do DOU, não digitado à parte.
CONSTRAINT prefixo_bate_com_texto
    CHECK (prefixo = regexp_replace(texto_ncm, '[^0-9]', '', 'g')),
CONSTRAINT prefixo_comprimento_valido
    CHECK (prefixo ~ '^[0-9]{4,8}$')
```

**Rationale:**

1. **A primeira constraint elimina a classe de erro mais provável desta feature.** O humano
   transcreve `texto_ncm` = "0210.99.1" copiando do DOU; se digitar `prefixo` = "0210991**0**", o
   `INSERT` falha e a migração inteira faz rollback (o migrador roda cada migração em sua própria
   transação). Sem ela, o erro seria uma mercadoria a mais ou a menos na cesta básica, descoberto
   por um cliente.
2. **A segunda é a que fecha o acoplamento da Decisão 2** — nada entra na tabela que
   `prefixos_ncm` não consiga enxergar.
3. **A migração vira o documento de auditoria.** Quem quiser conferir a cesta básica lê um arquivo
   SQL com a grafia literal do DOU ao lado de cada prefixo e a URL no topo — o mesmo argumento que
   `db/migrador.py` usa para não ter ORM ("não esconde o SQL de quem precisa auditá-lo, que é
   metade do ponto num sistema de compliance fiscal").
4. **Contagens como teste de truncamento**: 26 itens, 76 inclusões, 19 exceções. Uma migração
   cortada pela metade passa em toda constraint e falha nessas três asserções.

**Alternatives Rejected:**

1. **`scripts/ingerir_cesta_basica.py` + passo em `migrar_banco.yml`** — rejeitado: mais peças
   móveis, e o dado ainda seria transcrito à mão (só que num `.py` em vez de num `.sql`).
2. **Scraper do Senado** — rejeitado: 95 linhas de lista fechada não justificam um scraper, e a
   fonte é uma tabela HTML de publicação única, não um endpoint estável.
3. **Constraints só em teste, não no banco** — rejeitado: o teste roda no CI, a migração roda em
   produção; a garantia precisa estar onde o dado entra.

---

### Decision 12: `regras_tributarias_cache` e `buscar_regra_cache()` são removidos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `SHOULD` do DEFINE + Open Question 3 |

**Context:** O achado original da auditoria (achado 2) é que a tabela e a função existem desde
`SCHEMA_POSTGRESQL` sem nenhum chamador, sem nenhuma linha gravada e sem script de carga. O
DEFINE pede decisão explícita: substituir, adaptar ou remover.

**Choice:** **Remover as duas.** Migração `006_remover_regras_tributarias_cache.sql` derruba a
tabela; `RegraTributariaCache` e `buscar_regra_cache` saem de `db/repositorio.py`; os dois testes
de `tests/test_schema_postgres.py` que a exercitavam (e a menção dela no `TRUNCATE` da fixture)
saem junto.

A migração 006 é **separada da 005** e derruba a tabela só depois de verificar que está vazia:

```sql
DO $$
BEGIN
    IF to_regclass('public.regras_tributarias_cache') IS NOT NULL
       AND EXISTS (SELECT 1 FROM regras_tributarias_cache) THEN
        RAISE EXCEPTION 'regras_tributarias_cache não está vazia: DROP abortado';
    END IF;
END $$;
DROP TABLE IF EXISTS regras_tributarias_cache;
```

**Rationale:**

1. **O schema dela está errado para o dado real, não só incompleto.** Guarda alíquotas absolutas
   (`aliquota_cbs/ibs/is`) quando os regimes diferenciados são *reduções percentuais sobre uma
   alíquota de referência*; tem `ncm_code` único por linha, quando um item do Anexo tem até 18
   códigos; não tem exceção; não tem `nbs_code` para os Anexos de serviço. Não serve nem para o
   Anexo I (o mais simples dos 17) nem para os outros 16 — o brainstorm chegou a essa conclusão
   (Key Decision 4) e esta sessão a confirmou contra o texto literal.
2. **Precedente direto da feature anterior:** `RegimeIndisponivelError` foi removido pela Decisão 8
   do DESIGN de `IPI_TIPI_MOTOR_CALCULO` com o argumento de que "manter uma exceção morta cuja
   justificativa foi refutada é pior que não ter — alguém a reintroduziria citando um raciocínio
   que não vale mais". Vale igual aqui, com o agravante de que uma *tabela* vazia convida alguém a
   populá-la com uma forma errada.
3. **Zero risco de perda de dado:** a tabela nunca teve linhas, e a guarda transforma essa
   afirmação numa verificação em vez de uma crença.
4. **Migração separada** para que reverter a remoção não implique reverter o Anexo I, e para que
   cada migração continue fazendo uma coisa só.

**Consequences:**

- `contexto.md` (seção 7) segue descrevendo `regras_tributarias_cache` como parte do blueprint.
  Não é reescrito por esta feature (o blueprint é registro de intenção); o `CLAUDE.md` passa a
  registrar que a intenção foi realizada por `cesta_basica_anexo_i*`, com a forma que o texto
  legal exigiu.
- O comentário da migração 004 ("Sem RLS: como regras_tributarias_cache…") cita uma tabela que
  deixará de existir. Migrações aplicadas são histórico e **não são editadas**; o docstring vivo em
  `db/repositorio.py::buscar_ipi_por_ncm` passa a citar `cesta_basica_anexo_i` no lugar.

**Alternatives Rejected:**

1. **Manter a tabela vazia "para os outros Anexos"** — rejeitado pelo motivo 1: a forma está
   errada para todos eles.
2. **Renomear/alterar `regras_tributarias_cache` para virar a tabela nova** — rejeitado: sobrariam
   5 colunas sem uso e o histórico de migrações ficaria mais difícil de ler que um `CREATE` novo.
3. **Remover só o código Python e deixar a tabela** — rejeitado: seria trocar código morto por
   schema morto.

---

### Decision 13: a feature só é dada como pronta com prova contra o Cloud SQL real

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** Pela Decisão 8, um `GRANT` faltando não produz erro: produz `CONSULTA_INDISPONIVEL`
silencioso e a alíquota geral — ou seja, **exatamente a resposta de hoje**. É o modo de falha mais
perigoso possível: a feature "funciona" (200, verde) sem fazer nada. É a repetição literal do
cenário que a Decisão 9 da feature 1 existiu para cobrir.

**Choice:** Duas verificações contra infraestrutura real, nenhuma rodando local:

1. `scripts/verificar_cesta_basica_producao.py`, disparado por `migrar_banco.yml`
   (`verificar_cesta_basica=sim`): conecta **com o papel `taxreformai_app`** (não o admin),
   confere 26 itens / 76 inclusões / 19 exceções, e resolve dois códigos de ponta a ponta —
   `04051000` (manteiga, item 5) precisa vir APLICADA e `02074300` (foie gras) precisa vir
   EXCLUÍDA. Sai com código 1 em qualquer divergência ou permissão negada.
2. **Uma chamada nova e separada** no smoke test do `deploy.yml`, com um payload próprio de
   `ncm: "04051000"`, exigindo `.cesta_basica.total_cbs_dispensado != null` e
   `.itens_detalhados[0].aliquotas_aplicadas.cbs_percentual == 0`.

**A chamada é separada de propósito** — e esta é uma armadilha real: acrescentar um segundo item
ao payload do smoke test existente faria `total_ipi` depender de `0405.10.00` estar na TIPI
ingerida. Pela Decisão 5 da feature 1, **um** item de mercadoria não resolvido zera `total_ipi`
para `null`, e a asserção de IPI do próprio deploy reprovaria o job por um motivo que nada tem a
ver com a mudança. Dois payloads, duas asserções, zero acoplamento.

**Rationale:** O projeto já classifica features por "verificado contra infraestrutura real" vs.
"revisado por código" (`DEPLOY_CLOUD_RUN` 7/7, `SCHEMA_POSTGRESQL`). Uma feature cujo único modo
de falha é indistinguível do sucesso não pode ser shipada só com fake.

**Consequences:** O smoke test do deploy passa a fazer duas chamadas a `/simulate`. É deliberado, e
coerente com o precedente já registrado no CLAUDE.md ("os defaults fazem um deploy incompleto
subir um serviço que responde 200 em `/health` e falha 100% das requisições reais").

---

## Dados — Anexo I transcrito (fonte primária, 2026-07-28)

> Transcrição literal de `https://legis.senado.leg.br/norma/40180341/publicacao/40180888`
> ("Publicação Original de Anexo", DOU Edição Extra nº 11-B de 16/01/2025, p. 47).
> É esta tabela que o `/build` copia para a migração 005 — não a versão resumida do DEFINE.
>
> `dispositivo_legal_ref` de todos: `LCP 214/2025, art. 125, Anexo I, item N`.

| Item | `texto_ncm` (grafia literal) → `prefixo` | Descrição literal (`descricao`) |
|------|------------------------------------------|----------------------------------|
| 1 | `1006.20`→100620 · `1006.30`→100630 · `1006.40.00`→10064000 | Arroz das subposições 1006.20 e 1006.30 e do código 1006.40.00 da NCM/SH |
| 2 | `0401.10.10` · `0401.10.90` · `0401.20.10` · `0401.20.90` · `0401.40.10` · `0401.50.10` | Leite, em conformidade com os requisitos da legislação específica relativos ao consumo direto pela população, classificado nos códigos 0401.10.10, 0401.10.90, 0401.20.10, 0401.20.90, 0401.40.10 e 0401.50.10 da NCM/SH |
| 3 | `0402.10.10` · `0402.10.90` · `0402.21.10` · `0402.21.20` · `0402.29.10` · `0402.29.20` | Leite em pó, em conformidade com os requisitos da legislação específica, classificado nos códigos 0402.10.10, 0402.10.90, 0402.21.10, 0402.21.20, 0402.29.10 e 0402.29.20 da NCM/SH |
| 4 | `1901.10.10` · `1901.10.90` · `2106.90.90` | Fórmulas infantis, em conformidade com os requisitos da legislação específica, classificadas nos códigos 1901.10.10, 1901.10.90 e 2106.90.90 da NCM/SH |
| 5 | `0405.10.00` | Manteiga do código 0405.10.00 da NCM/SH |
| 6 | `1517.10.00` | Margarina do código 1517.10.00 da NCM/SH |
| 7 | `0713.33.19` · `0713.33.29` · `0713.33.99` · `0713.35.90` | Feijões dos códigos 0713.33.19, 0713.33.29, 0713.33.99 e 0713.35.90 da NCM/SH |
| 8 | `09.01`→0901 · `2101.1`→21011 | Café da posição 09.01 e da subposição 2101.1, ambos da NCM/SH |
| 9 | `1513.21.20` | Óleo de babaçu do código 1513.21.20 da NCM/SH, em conformidade com os requisitos da legislação específica relativos ao consumo como alimento |
| 10 | `1106.20.00` · `1903.00.00` | Farinha de mandioca classificada no código 1106.20.00 da NCM/SH e tapioca e seus sucedâneos do código 1903.00.00 da NCM/SH |
| 11 | `1102.20.00` · `1103.13.00` | Farinha, grumos e sêmolas, de milho, dos códigos 1102.20.00 e 1103.13.00 da NCM |
| 12 | `1104.19.00` · `1104.23.00` | Grãos de milho classificados no código 1104.19.00 e do código 1104.23.00 da NCM/SH |
| 13 | `1101.00.10` | Farinha de trigo do código 1101.00.10 da NCM/SH |
| 14 | `1701.14.00` · `1701.99.00` | Açúcar classificado nos códigos 1701.14.00 e 1701.99.00 da NCM/SH |
| 15 | `1902.1`→19021 | Massas alimentícias da subposição 1902.1 da NCM/SH |
| 16 | `1905.90.90` · `1901.20.10` · `1901.20.90` | Pão comumente denominado pão francês, de formato cilíndrico e alongado, com miolo branco creme e macio, e casca dourada e crocante, elaborado a partir da mistura ou pré-mistura de farinha de trigo, fermento biológico, água, sal, açúcar, aditivos alimentares e produtos de fortificação de farinhas, em conformidade com a legislação vigente, classificado no código 1905.90.90 da NCM/SH e a pré-mistura ou massa, para preparação do pão comumente denominado pão francês, dos códigos 1901.20.10 e 1901.20.90 da NCM/SH |
| 17 | `1104.12.00` · `1104.22.00` | Grãos de aveia dos códigos 1104.12.00 e 1104.22.00 da NCM/SH |
| 18 | `1102.90.00` | Farinha de aveia classificada no código 1102.90.00 da NCM/SH |
| 19 | **a)** `02.01`→0201 · `02.02`→0202 · `0206.10.00` · `0206.2`→02062 · `0210.20.00`<br>**b)** `02.03`→0203 · `0206.30.00` · `0206.4`→02064 · `0209.10`→020910 · `0210.1`→02101<br>**c)** `02.04`→0204 · `0210.99.20` · `0210.99.90` · `0206.80.00` · `0206.90.00`<br>**d)** `02.07`→0207 · `0209.90.00` · `0210.99.1`→**0210991 (7 dígitos)**<br>**d) EXCEÇÕES:** `0207.43.00` · `0207.53.00` | Carnes bovina, suína, ovina, caprina e de aves e produtos de origem animal (exceto foies gras) dos seguintes códigos, subposições e posições da NCM/SH: a) 02.01, 02.02, 0206.10.00, 0206.2 e 0210.20.00; b) 02.03, 0206.30.00, 0206.4, 0209.10 e 0210.1; c) 02.04 e 0210.99.20, carne caprina classificada no código 0210.99.90 e miudezas comestíveis de ovinos e caprinos classificadas nos códigos 0206.80.00 e 0206.90.00; d) 02.07, 0209.90.00 e 0210.99.1, exceto os produtos dos códigos 0207.43.00 e 0207.53.00 |
| 20 | **a)** `03.02`→0302 · **EXCEÇÕES:** `0302.1`→03021 · `0302.3`→03023 · `0302.51.00` · `0302.52.00` · `0302.53.00` · `0302.9`→03029<br>**b)** `03.03`→0303 · **EXCEÇÕES:** `0303.1` · `0303.4` · `0303.63.00` · `0303.64.00` · `0303.65.00` · `0303.9`<br>**c)** `03.04`→0304 · **EXCEÇÕES:** `0304.4` · `0304.5` · `0304.7` · `0304.8` · `0304.9` | Peixes e carnes de peixes (exceto salmonídeos, atuns, bacalhaus, hadoque, saithe e ovas e outros subprodutos) dos seguintes códigos, subposições e posições da NCM/SH: a) 03.02; exceto os produtos das subposições e dos códigos 0302.1, 0302.3, 0302.51.00, 0302.52.00, 0302.53.00 e 0302.9 da NCM/SH; b) 03.03; exceto os produtos das subposições e dos códigos 0303.1, 0303.4, 0303.63.00, 0303.64.00, 0303.65.00 e 0303.9 da NCM/SH; c) 03.04; exceto os salmonídeos, atuns, bacalhaus, hadoque e saithe classificados nas subposições 0304.4, 0304.5, 0304.7, 0304.8 e 0304.9 da NCM/SH |
| 21 | `0406.10.10` · `0406.10.90` · `0406.20.00` · `0406.90.10` · `0406.90.20` · `0406.90.30` | Queijos tipo mozarela, minas, prato, queijo de coalho, ricota, requeijão, queijo provolone, queijo parmesão, queijo fresco não maturado e queijo do reino classificados nos códigos 0406.10.10, 0406.10.90, 0406.20.00, 0406.90.10, 0406.90.20 e 0406.90.30 da NCM/SH |
| 22 | `2501.00.20` · `2501.00.90` | Sal em conformidade com os requisitos da legislação específica relativos ao teor de iodo enquadrado nos limites próprios para consumo humano classificado nos códigos 2501.00.20 e 2501.00.90 da NCM/SH |
| 23 | `09.03`→0903 | Mate da posição 09.03 da NCM/SH |
| 24 | `1901.90.90` | Farinha com baixo teor de proteína para pessoas com aminoacidopatias, acidemias e defeitos do ciclo da uréia da NCM 1901.90.90 |
| 25 | `1902.19.00` | Massas com baixo teor de proteína para pessoas com aminoacidopatias, acidemias e defeitos do ciclo da uréia da NCM 1902.19.00 |
| 26 | `2106.9090`→21069090 | Fórmulas Dietoterápicas para Erros Inatos do Metabolismo da NCM 2106.9090 |

**Contagens de fechamento (asserções obrigatórias do `/build`):** 26 itens · 95 linhas de prefixo ·
76 inclusões · 19 exceções · comprimentos de prefixo presentes = {4, 5, 6, 7, 8} · nenhuma
duplicata de `(item, prefixo, excecao)` · prefixo compartilhado entre itens distintos: apenas
`21069090` (itens 4 e 26).

**Invariante de exceção** (teste sobre o seed): toda linha com `excecao = true` tem, **no mesmo
item**, uma linha de inclusão que é prefixo dela. Verificado nas 19 exceções: as 2 do item 19
descendem de `0207`; as 17 do item 20 descendem de `0302`/`0303`/`0304`.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/005_cesta_basica_anexo_i.sql` | Create | 2 tabelas + 2 CHECKs + seed (26 itens, 95 prefixos) + `GRANT SELECT` a `taxreformai_app` | @database-reviewer | — |
| 2 | `db/migrations/006_remover_regras_tributarias_cache.sql` | Create | `DROP TABLE` com guarda de tabela vazia (Decisão 12) | @database-reviewer | — |
| 3 | `db/repositorio.py` | Modify | `PrefixoCestaBasica` + `buscar_cesta_basica_por_prefixo`; **remove** `RegraTributariaCache`/`buscar_regra_cache`; docstring de `buscar_ipi_por_ncm` deixa de citar a tabela removida | @database-reviewer | 1, 2 |
| 4 | `api/ncm.py` | Create | `digitos_ncm`, `prefixos_ncm` — vocabulário da NCM/SH, sem conhecer feature (Decisão 10) | @python-developer | — |
| 5 | `api/ipi.py` | Modify | `normalizar_ncm` delega a `digitos_ncm`; nenhuma mudança de assinatura ou comportamento | @python-developer | 4 |
| 6 | `api/cesta_basica.py` | Create | `SituacaoCestaBasica`, `ConsultaCestaBasica`, `ResolucaoCestaBasica`, `consultar_com_seguranca`, `resolver_item` | @python-developer | 3, 4 |
| 7 | `motor_calculo/reducoes.py` | Create | `aplicar_reducao_a_zero` — puro, sem infra (Decisão 6) | @python-developer | — |
| 8 | `motor_calculo/regras_fiscais.py` | Modify | Campo `fonte_legal_reducoes: str \| None = None` em `RegraFiscal` | @python-developer | — |
| 9 | `motor_calculo/tabela_aliquotas.py` | Modify | Seed de `fonte_legal_reducoes` em 2026 (art. 348, III, "a") e 2027-2028 (art. 344 § único, I / art. 347, § 1º, I) | @python-developer | 8 |
| 10 | `api/schemas_simulate.py` | Modify | `CestaBasicaItem` (em `ItemDetalhado`), `CestaBasicaResumo` + `ItemNaoAvaliado` (em `RespostaSimulacao`) | @python-developer | 6 |
| 11 | `api/routers/simulate.py` | Modify | 1 lookup antes do laço, override por item, agregação, advertência e texto do audit log | @python-developer | 6, 7, 10 |
| 12 | `tests/test_cesta_basica_resolucao.py` | Create | Unit puro: `digitos_ncm`/`prefixos_ncm`, `resolver_item` nas 6 situações, desempate 15/25 e 4/26, `aplicar_reducao_a_zero` e sua invariante | @test-generator | 4, 6, 7 |
| 13 | `tests/test_api_simulate_cesta_basica.py` | Create | AT-001..AT-005 via `TestClient` + fake pool; 1 query por request; pool `None` e pool que explode → 200 | @test-generator | 11 |
| 14 | `tests/test_cesta_basica_db.py` | Create | Postgres real: contagens do seed, as 2 CHECKs recusando linha inválida, invariante de exceção, `buscar_cesta_basica_por_prefixo` devolvendo inclusão+exceção no mesmo lote, `to_regclass` da tabela removida | @database-reviewer | 1, 2, 3 |
| 15 | `tests/test_schema_postgres.py` | Modify | Remove os 2 testes de `buscar_regra_cache` e a tabela do `TRUNCATE` da fixture | @database-reviewer | 2, 3 |
| 16 | `scripts/verificar_cesta_basica_producao.py` | Create | Lookup e contagens com o papel `taxreformai_app` contra o Cloud SQL real (Decisão 13) | @gcp-data-architect | 3 |
| 17 | `.github/workflows/migrar_banco.yml` | Modify | Input `verificar_cesta_basica` + passo que roda o script 16 | @gcp-data-architect | 16 |
| 18 | `.github/workflows/deploy.yml` | Modify | Segunda chamada de smoke test, com payload próprio (Decisão 13) | @gcp-data-architect | 11 |
| 19 | `CLAUDE.md` | Modify | Tabela de features, estrutura (`db/migrations`, `api/`, `motor_calculo/`), destino de `regras_tributarias_cache`, arquivos-chave | @python-developer | 1-18 |

**Total Files:** 19 (8 novos + 11 modificados)

**Fora do manifesto, deliberadamente:**

- `frontend/` — hoje só tipa `resumo_financeiro`/`itens_detalhados`; todos os campos novos são
  aditivos e opcionais. Exibir a cesta básica na tela é outra feature (mesma decisão da feature 1).
- `contexto.md` — blueprint é registro de intenção, não espelho do schema (ver Decisão 12).
- `db/migrations/004_tipi.sql` e `001_schema_inicial.sql` — migrações aplicadas são histórico e não
  são editadas, conforme o Out of Scope do DEFINE.

**Nota de tamanho (responde a Open Question 1 do DEFINE):** 19 arquivos contra 12 da feature 1.
O acréscimo **não** vem dos 6 itens não-triviais — a Decisão 1 fez os 26 caírem no mesmo código. Ele
vem de três coisas que a feature 1 não tinha: schema novo (2 migrações + 1 teste de banco), o
override por item, que não existia em nenhum lugar do motor (3 arquivos), e a remoção do código
morto que era o achado original (3 arquivos tocados). Continua sendo uma feature de uma sessão de
`/build`; não há motivo para dividir.

---

## Agent Assignment Rationale

| Agent | Files | Why This Agent |
|-------|-------|-----------------|
| @database-reviewer | 1, 2, 3, 14, 15 | Schema novo com CHECK constraints não triviais, `DROP` guardado e SQL do lookup em lote — mesmo agente de `SCHEMA_POSTGRESQL` e do lookup da TIPI |
| @python-developer | 4-11, 19 | FastAPI/Pydantic, lógica pura de resolução e o override no motor; mesmo agente das 9 features anteriores |
| @test-generator | 12, 13 | AT-001..AT-005 com fakes, incluindo o teste de falso positivo de prefixo (AT-005) e o spy de contagem de queries |
| @gcp-data-architect | 16, 17, 18 | Verificação contra Cloud SQL/Cloud Run reais e edição dos workflows |
| @security-reviewer | (revisão de 1, 3) | Confirmar que a ausência de RLS é correta (dado legal público) e que não há SQL montado por concatenação |
| @code-reviewer | (revisão final) | Revisão de qualidade geral, como em toda feature |

---

## Code Patterns

### Pattern 1: schema e seed (`db/migrations/005_cesta_basica_anexo_i.sql`)

```sql
-- Cesta Básica Nacional de Alimentos — LCP 214/2025, art. 125 e Anexo I.
--
-- Fonte primária desta transcrição (consultada em 2026-07-28):
--   https://legis.senado.leg.br/norma/40180341/publicacao/40180888
--   "Publicação Original de Anexo", DOU Edição Extra nº 11-B de 16/01/2025, p. 47.
-- O Anexo I NÃO tem republicação/errata (a única registrada na norma é do Anexo
-- XXIII) e NÃO foi alterado pela LC 227/2026 — verificado no /define.
--
-- Toda correspondência por NCM/SH é PREFIXO DE DÍGITOS: "posição 09.01" (4),
-- "subposição 1902.1" (5), "subposição 1006.20" (6), "0210.99.1" (7) e
-- "código 0405.10.00" (8) são todos prefixos do código de 8 dígitos da
-- mercadoria. Não há duas semânticas de match, só comprimentos diferentes.
--
-- Sem RLS: como aliquotas_ipi_tipi, é dado legal público, igual para todo tenant.

CREATE TABLE IF NOT EXISTS cesta_basica_anexo_i (
    item                  SMALLINT PRIMARY KEY CHECK (item BETWEEN 1 AND 26),
    descricao             TEXT NOT NULL,   -- texto literal do item no DOU
    dispositivo_legal_ref TEXT NOT NULL,   -- "LCP 214/2025, art. 125, Anexo I, item N"
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cesta_basica_anexo_i_ncm (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item      SMALLINT NOT NULL REFERENCES cesta_basica_anexo_i (item) ON DELETE CASCADE,
    prefixo   VARCHAR(8) NOT NULL,          -- só dígitos
    excecao   BOOLEAN NOT NULL DEFAULT FALSE,
    alinea    CHAR(1),                      -- 'a'..'d' nos itens 19 e 20; NULL nos demais
    texto_ncm TEXT NOT NULL,                -- grafia literal do DOU: "02.07", "0210.99.1"

    UNIQUE (item, prefixo, excecao),

    -- O prefixo é DERIVADO da grafia literal, não digitado à parte: transcrever
    -- "0210.99.1" e digitar "02109910" passa a falhar no INSERT, em vez de virar
    -- uma mercadoria a mais na cesta básica descoberta por um cliente.
    CONSTRAINT prefixo_bate_com_texto
        CHECK (prefixo = regexp_replace(texto_ncm, '[^0-9]', '', 'g')),

    -- 4 = posição (o nível mais amplo que o Anexo I usa), 8 = subitem.
    -- api/ncm.py::prefixos_ncm gera EXATAMENTE estes comprimentos: uma linha
    -- fora da faixa jamais casaria com nada e seria um falso negativo mudo.
    -- Se um Anexo futuro citar capítulo (2 dígitos), os DOIS mudam juntos.
    CONSTRAINT prefixo_comprimento_valido CHECK (prefixo ~ '^[0-9]{4,8}$')
);

CREATE INDEX IF NOT EXISTS idx_cesta_basica_prefixo ON cesta_basica_anexo_i_ncm (prefixo);

INSERT INTO cesta_basica_anexo_i (item, descricao, dispositivo_legal_ref) VALUES
 (1,  'Arroz das subposições 1006.20 e 1006.30 e do código 1006.40.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 1'),
 -- … 26 itens, descrição literal conforme a seção "Dados — Anexo I transcrito"
ON CONFLICT (item) DO NOTHING;

INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, excecao, alinea, texto_ncm) VALUES
 (1,  '100620',   FALSE, NULL, '1006.20'),
 (1,  '100630',   FALSE, NULL, '1006.30'),
 (1,  '10064000', FALSE, NULL, '1006.40.00'),
 -- …
 (19, '0207',     FALSE, 'd',  '02.07'),
 (19, '0210991',  FALSE, 'd',  '0210.99.1'),
 (19, '02074300', TRUE,  'd',  '0207.43.00'),   -- foie gras: excluído pelo próprio item
 (19, '02075300', TRUE,  'd',  '0207.53.00'),
 (20, '0302',     FALSE, 'a',  '03.02'),
 (20, '03021',    TRUE,  'a',  '0302.1'),       -- salmonídeos
 -- … 95 linhas no total: 76 inclusões + 19 exceções
ON CONFLICT DO NOTHING;

-- Mesmo padrão da migração 004: GRANT ... ON ALL TABLES não é retroativo, então
-- sem este bloco o papel de runtime ficaria sem SELECT — e, pela Decisão 8, isso
-- NÃO gera erro: gera CONSULTA_INDISPONIVEL silencioso com a alíquota geral,
-- que é indistinguível do comportamento de hoje. Ver Decisão 13.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON cesta_basica_anexo_i TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON cesta_basica_anexo_i_ncm TO taxreformai_app';
    END IF;
END $$;
```

### Pattern 2: vocabulário da NCM (`api/ncm.py`)

```python
"""Canonização e hierarquia de códigos NCM/SH.

Vive aqui, e não dentro de `api/ipi.py` ou `api/cesta_basica.py`, porque as duas
features precisam da MESMA noção de "NCM válido". Duas definições fariam o mesmo
item aparecer resolvido para um tributo e "não reconhecido" para outro na mesma
resposta — bug indiagnosticável pelo cliente (ver Decisão 10).
"""

import re

_SO_DIGITOS = re.compile(r"\D")

# 4 = posição (09.01), 5/6 = subposição (1902.1 / 1006.20), 7 = item (0210.99.1),
# 8 = subitem (0405.10.00). Espelhado pela CHECK `prefixo_comprimento_valido` da
# migração 005: o que a tabela aceita é exatamente o que esta função enxerga.
_COMPRIMENTOS_PREFIXO = (4, 5, 6, 7, 8)


def digitos_ncm(bruto: str) -> str | None:
    """8 dígitos canônicos, ou None. `"0405.10.00"` e `"04051000"` são o MESMO
    código em duas grafias — canonizar não é fuzzy match, a função é injetiva."""
    digitos = _SO_DIGITOS.sub("", bruto or "")
    return digitos if len(digitos) == 8 else None


def prefixos_ncm(codigo: str) -> list[str]:
    """Os 5 prefixos hierárquicos de um código de 8 dígitos.

    É o que transforma "casar por prefixo" numa igualdade exata do lado do SQL
    (`WHERE prefixo = ANY(%s)`), preservando o índice e o mesmo idioma de
    `buscar_ipi_por_ncm` — ver Decisão 2.
    """
    return [codigo[:n] for n in _COMPRIMENTOS_PREFIXO]
```

### Pattern 3: lookup em lote (`db/repositorio.py`)

```python
@dataclass(frozen=True)
class PrefixoCestaBasica:
    """Uma linha de `cesta_basica_anexo_i_ncm` já com o item resolvido pelo JOIN.

    `excecao=True` significa que este prefixo EXCLUI a mercadoria do item — e
    exclui só DESTE item, nunca dos demais (Decisão 3).
    """

    item: int
    prefixo: str
    excecao: bool
    texto_ncm: str
    alinea: str | None
    descricao: str
    dispositivo_legal_ref: str


def buscar_cesta_basica_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoCestaBasica]:
    """Lookup em lote do Anexo I. Sem RLS: dado legal público, igual para todo tenant.

    UMA query para os prefixos de todos os itens do payload. Devolve tanto
    inclusões quanto exceções — uma exceção só é relevante quando ela própria é
    prefixo do código, então ela cai no mesmo `= ANY` e não precisa de segunda
    consulta.

    Propaga exceção de propósito: quem decide degradar é `api/cesta_basica.py`
    (mesma divisão da Decisão 6 do DESIGN de IPI_TIPI_MOTOR_CALCULO). Lista vazia
    de retorno significa "nenhum prefixo casou", nunca "falhou".
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT p.item, p.prefixo, p.excecao, p.texto_ncm, p.alinea,
                   i.descricao, i.dispositivo_legal_ref
            FROM cesta_basica_anexo_i_ncm p
            JOIN cesta_basica_anexo_i i ON i.item = p.item
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoCestaBasica(*linha) for linha in cur.fetchall()]
```

### Pattern 4: política e resolução (`api/cesta_basica.py`)

```python
"""Resolve a Cesta Básica Nacional (LCP 214/2025, art. 125, Anexo I) por NCM.

Irmão de `api/ipi.py`: mesma garantia de não propagação de exceção, mesma
divisão em três camadas. A diferença é a DIREÇÃO da degradação — aqui, não
conseguir consultar significa aplicar a alíquota GERAL da fase, ou seja, um
tributo maior que o devido, nunca menor (Decisão 8).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm, prefixos_ncm

logger = logging.getLogger("api.cesta_basica")


class SituacaoCestaBasica(StrEnum):
    APLICADA = "APLICADA"
    EXCLUIDA_EXPRESSAMENTE = "EXCLUIDA_EXPRESSAMENTE"  # o próprio Anexo exclui o código
    FORA_DO_ANEXO = "FORA_DO_ANEXO"
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaCestaBasica:
    """`disponivel` responde "consegui consultar?", nunca "achei alguma coisa?"."""

    disponivel: bool
    linhas: list[Any] = field(default_factory=list)


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaCestaBasica:
    """Nunca levanta. `pool is None` (toda a suíte de testes e qualquer deploy sem
    Cloud SQL) é indisponibilidade, não ausência de dado.

    Lista vazia com pool presente é `disponivel=True`: não há NADA a perguntar, o
    que é diferente de não CONSEGUIR perguntar — mesma correção que o BUILD da
    feature 1 precisou fazer em `consultar_ipi_com_seguranca`.
    """
    if pool is None:
        return ConsultaCestaBasica(disponivel=False)
    if not prefixos:
        return ConsultaCestaBasica(disponivel=True)

    try:
        from db.repositorio import buscar_cesta_basica_por_prefixo

        with pool.connection() as conexao:
            return ConsultaCestaBasica(
                disponivel=True, linhas=buscar_cesta_basica_por_prefixo(conexao, prefixos)
            )
    except Exception:
        logger.exception(
            "Falha ao consultar a Cesta Básica (Anexo I) — a simulação segue com a "
            "alíquota geral da fase, declarado na resposta"
        )
        return ConsultaCestaBasica(disponivel=False)


@dataclass(frozen=True)
class ResolucaoCestaBasica:
    situacao: SituacaoCestaBasica
    item: int | None = None
    dispositivo_legal_ref: str | None = None
    descricao: str | None = None
    texto_ncm: str | None = None
    tipo_correspondencia: str | None = None  # EXATO | PREFIXO | EXCECAO
    itens_correspondentes: tuple[int, ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoCestaBasica.APLICADA

    @property
    def avaliada(self) -> bool:
        """Serviço e "fora do anexo" são respostas conhecidas; só as duas
        situações abaixo significam "não sei" (Decisão 9)."""
        return self.situacao not in (
            SituacaoCestaBasica.CONSULTA_INDISPONIVEL,
            SituacaoCestaBasica.NCM_NAO_RECONHECIDO,
        )


def _mais_especifica(linhas):
    """Prefixo mais longo; empate resolvido pelo MENOR número de item.

    Ordenação total e determinística: sem ela, `1902.19.00` citaria ora o item 15
    ora o 25 conforme a ordem em que o Postgres devolveu as linhas (Decisão 4).
    """
    return max(linhas, key=lambda linha: (len(linha.prefixo), -linha.item))


def resolver_item(natureza: str, ncm: str, consulta: ConsultaCestaBasica) -> ResolucaoCestaBasica:
    """Função pura — AT-001..AT-005 são testáveis sem banco e sem HTTP.

    A ordem das guardas é a mesma de `api/ipi.py::resolver_item`, pela mesma
    razão: um código que não canoniza para 8 dígitos é propriedade do payload,
    não do banco, e reportá-lo como CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta.
    """
    if natureza == "SERVICO":
        return ResolucaoCestaBasica(SituacaoCestaBasica.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoCestaBasica(SituacaoCestaBasica.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoCestaBasica(SituacaoCestaBasica.CONSULTA_INDISPONIVEL)

    por_item: dict[int, list] = defaultdict(list)
    for linha in consulta.linhas:
        # O lote pode trazer prefixos de OUTROS códigos do mesmo payload.
        if codigo.startswith(linha.prefixo):
            por_item[linha.item].append(linha)

    inclusoes, exclusoes = [], []
    for linhas in por_item.values():
        # Exceção do PRÓPRIO item vence a inclusão do próprio item — e não toca
        # nenhum outro item (Decisão 3).
        excecoes = [linha for linha in linhas if linha.excecao]
        if excecoes:
            exclusoes.append(_mais_especifica(excecoes))
        else:
            inclusoes.append(_mais_especifica(linhas))

    if inclusoes:
        vencedora = _mais_especifica(inclusoes)
        return ResolucaoCestaBasica(
            situacao=SituacaoCestaBasica.APLICADA,
            item=vencedora.item,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXATO" if len(vencedora.prefixo) == 8 else "PREFIXO",
            itens_correspondentes=tuple(sorted(linha.item for linha in inclusoes)),
        )

    if exclusoes:
        vencedora = _mais_especifica(exclusoes)
        return ResolucaoCestaBasica(
            situacao=SituacaoCestaBasica.EXCLUIDA_EXPRESSAMENTE,
            item=vencedora.item,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXCECAO",
            itens_correspondentes=tuple(sorted(linha.item for linha in exclusoes)),
        )

    return ResolucaoCestaBasica(SituacaoCestaBasica.FORA_DO_ANEXO)
```

### Pattern 5: o override, puro e no motor (`motor_calculo/reducoes.py`)

```python
"""Reduções de alíquota aplicadas por ITEM, depois do cálculo por fase.

`engine.calcular()` resolve CBS/IBS por FASE, uniforme para todo o payload — não
existe nele conceito de alíquota por produto, e introduzi-lo exigiria que o motor
conhecesse um lookup em banco. Este módulo é a alternativa: recebe o
`ResultadoCalculo` pronto e devolve outro, sem I/O, sem import de infraestrutura.

Mora em `motor_calculo/` (e não em `api/`) porque a composição
`valor_liquido = valor_base - total_tributos` é invariante do engine: se um dia o
split payment mudar de fórmula, os dois arquivos aparecem lado a lado em qualquer
busca. Ver Decisão 6.
"""

from dataclasses import replace
from decimal import Decimal

from motor_calculo.engine import ResultadoCalculo

ZERO = Decimal("0.00")


def aplicar_reducao_a_zero(
    resultado: ResultadoCalculo, *, split_payment_active: bool = True
) -> ResultadoCalculo:
    """CBS e IBS a zero; IS intacto; líquido recomposto.

    O art. 125 reduz a zero as alíquotas "do IBS e da CBS" — e só. O Imposto
    Seletivo tem lista própria (Anexo XVII), fora do escopo desta feature, então
    zerá-lo aqui seria inventar um benefício que a lei não deu.

    `split_payment_active` precisa ser o MESMO valor passado a
    `engine.calcular()`; hoje as duas chamadas usam o default. Deduzi-lo do
    objeto seria adivinhar o passado dele.
    """
    total_tributos = resultado.valor_is
    return replace(
        resultado,
        valor_cbs=ZERO,
        valor_ibs=ZERO,
        total_tributos=total_tributos,
        valor_liquido=(
            resultado.valor_base - total_tributos
            if split_payment_active
            else resultado.valor_base
        ),
    )
```

### Pattern 6: campos novos (`api/schemas_simulate.py`)

```python
class CestaBasicaItem(BaseModel):
    """Situação do item frente ao Anexo I. SEMPRE presente, inclusive quando não
    se aplica: seis coisas diferentes colapsariam num booleano `false` — fora do
    Anexo, EXPRESSAMENTE excluído pelo Anexo, NCM ilegível, consulta indisponível
    e item de serviço (Decisão 7).

    `EXCLUIDA_EXPRESSAMENTE` é a informação mais valiosa desta feature: o produto
    está na posição citada pelo item, mas o próprio Anexo I o retira (foie gras
    no item 19, salmonídeos e atuns no item 20). NÃO é o mesmo que
    `FORA_DO_ANEXO`.
    """

    situacao: str
    item: int | None = None                    # 1..26
    dispositivo_legal_ref: str | None = None   # "LCP 214/2025, art. 125, Anexo I, item 5"
    descricao: str | None = None               # texto literal do item no DOU
    ncm_correspondido: str | None = None       # grafia literal que casou: "02.07"
    tipo_correspondencia: str | None = None    # EXATO | PREFIXO | EXCECAO
    # Itens 15/25 e 4/26 citam códigos sobrepostos; `item` é o mais específico,
    # esta lista mostra todos, para o auditor não perguntar por que não o outro.
    itens_correspondentes: list[int] = []
    # O que teria sido cobrado sem a redução — é assim que o controller demonstra
    # o benefício da Cesta Básica, que é o segundo pain point do DEFINE.
    cbs_percentual_sem_reducao: Decimal | None = None
    ibs_percentual_sem_reducao: Decimal | None = None
    valor_cbs_dispensado: Decimal | None = None
    valor_ibs_dispensado: Decimal | None = None
    # Por que a redução vale numa fase cuja alíquota é 0,9%/0,1% (Decisão 5).
    fonte_legal_transicao: str | None = None


class ItemNaoAvaliado(BaseModel):
    """Sem isto, `total_cbs_dispensado = null` não diria QUAL item causou."""

    sku: str
    ncm: str
    situacao: str  # NCM_NAO_RECONHECIDO | CONSULTA_INDISPONIVEL


class CestaBasicaResumo(BaseModel):
    consulta_disponivel: bool
    itens_com_reducao_aplicada: int = 0
    # `None` quando QUALQUER item de mercadoria ficou sem avaliação — nunca um
    # total parcial com cara de total (Decisão 9). `0.00` é resposta legítima:
    # payload inteiro fora do Anexo.
    total_cbs_dispensado: Decimal | None = None
    total_ibs_dispensado: Decimal | None = None
    itens_nao_avaliados: list[ItemNaoAvaliado] = []
    fonte_legal: str = (
        "LCP 214/2025, art. 125 e Anexo I — Cesta Básica Nacional de Alimentos: "
        "alíquotas do IBS e da CBS reduzidas a zero. A correspondência é feita "
        "por NCM/SH; vários itens do Anexo I impõem condições adicionais em seu "
        "próprio texto (conformidade com legislação específica, tipo de produto) "
        "que esta simulação não verifica."
    )
```

### Pattern 7: consumo no router (`api/routers/simulate.py`)

```python
    # UMA consulta por requisição, antes do laço. Cada código de 8 dígitos vira 5
    # prefixos candidatos (Decisão 2); `set` cobre códigos repetidos e prefixos
    # comuns entre itens diferentes (100 itens do mesmo capítulo compartilham o
    # prefixo de 4); `sorted` deixa a query determinística e comparável em teste.
    # Payload só de serviços não abre conexão nenhuma.
    prefixos_consultar = sorted(
        {
            prefixo
            for item in payload.itens
            if item.natureza == "MERCADORIA" and (codigo := digitos_ncm(item.ncm))
            for prefixo in prefixos_ncm(codigo)
        }
    )
    consulta_cesta = consultar_com_seguranca(db_pool, prefixos_consultar)

    total_cbs_dispensado = Decimal(0)
    total_ibs_dispensado = Decimal(0)
    itens_com_reducao = 0
    itens_nao_avaliados: list[ItemNaoAvaliado] = []

    for item in payload.itens:
        ...
        resultado = engine.calcular(valor_base=valor_base_item, ano_operacao=payload.ano_operacao)

        resolucao = resolver_cesta_basica(item.natureza, item.ncm, consulta_cesta)
        cesta_basica_item = CestaBasicaItem(situacao=resolucao.situacao.value, ...)

        if resolucao.aplicada:
            cbs_dispensado, ibs_dispensado = resultado.valor_cbs, resultado.valor_ibs
            resultado = aplicar_reducao_a_zero(resultado)
            total_cbs_dispensado += cbs_dispensado
            total_ibs_dispensado += ibs_dispensado
            itens_com_reducao += 1
            cesta_basica_item = cesta_basica_item.model_copy(update={
                "cbs_percentual_sem_reducao": regra.aliq_cbs * 100,
                "ibs_percentual_sem_reducao": regra.aliq_ibs * 100,
                "valor_cbs_dispensado": cbs_dispensado,
                "valor_ibs_dispensado": ibs_dispensado,
                "fonte_legal_transicao": regra.fonte_legal_reducoes,
            })
        elif item.natureza == "MERCADORIA" and not resolucao.avaliada:
            itens_nao_avaliados.append(
                ItemNaoAvaliado(sku=item.sku, ncm=item.ncm, situacao=resolucao.situacao.value)
            )

        # `resultado` já reduzido: os totais gerais e as alíquotas exibidas por
        # item saem DELE, nunca de `regra`, senão a resposta se contradiria.
        total_cbs += resultado.valor_cbs
        ...
        aliquotas = AliquotasAplicadas(
            cbs_percentual=Decimal(0) if resolucao.aplicada else regra.aliq_cbs * 100,
            ibs_percentual=Decimal(0) if resolucao.aplicada else regra.aliq_ibs * 100,
            is_percentual=regra.aliq_is * 100,
        )

    # Um único predicado governa os dois totais e a advertência (Decisão 9).
    avaliacao_completa = consulta_cesta.disponivel and not itens_nao_avaliados
```

### Pattern 8: verificação em produção (`scripts/verificar_cesta_basica_producao.py`)

```python
"""Prova o Anexo I contra o Cloud SQL real, com o papel de RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
o seed entra como `taxreformai_admin` (a própria migração), e o GRANT para
`taxreformai_app` nunca é exercitado por nenhum SELECT. Pela Decisão 8, um grant
faltando NÃO gera erro em runtime — gera CONSULTA_INDISPONIVEL silencioso e a
alíquota geral, que é EXATAMENTE a resposta de antes da feature. Este script é o
único lugar onde isso falha ruidosamente.

Sai com código 1 se: as contagens não forem 26/76/19; `04051000` não resolver
APLICADA no item 5; `02074300` não resolver EXCLUIDA_EXPRESSAMENTE; ou o SELECT
for negado por permissão.
"""
```

---

## Data Flow

```text
1. Cliente envia POST /v1/tax/simulate (X-API-Key + payload) — `ncm` já existia, contrato intacto
2. verificar_api_key → tenant_id; payload.tenant_id divergente → 403
3. Fase/RegraFiscal resolvida uma vez → 422 se não confirmada (comportamento inalterado)
4. NOVO: coleta os prefixos (4..8) de cada NCM distinto dos itens MERCADORIA
   4a. conjunto vazio   → nenhuma conexão aberta
   4b. conjunto cheio   → 1 query `= ANY(%s)`
   4c. qualquer exceção → capturada, logada, disponivel=False (Decisão 8)
5. Por item: engine.calcular (CBS/IBS/IS) + PIS/COFINS + ICMS/ISS + IPI, como hoje
   5a. NOVO: resolver_item → situação (6 estados)
   5b. NOVO: se APLICADA → aplicar_reducao_a_zero(resultado) — CBS=0, IBS=0, IS intacto,
       líquido recomposto; totais e `aliquotas_aplicadas` passam a sair do resultado reduzido
6. Agregação: total_cbs/ibs já refletem as reduções; cesta_basica{dispensado, não avaliados}
7. Audit log (nunca propaga) — o parecer passa a citar quantos itens tiveram redução
8. 200 com RespostaSimulacao
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL `taxreformai-pg` / `cesta_basica_anexo_i*` | `psycopg_pool` via socket unix do Cloud Run (`api/db.py`), SELECT | Papel `taxreformai_app`, senha do Secret Manager |
| `motor_calculo` | Import Python direto, in-process | N/A — e continua sem tocar em banco |
| Cliente ERP | REST/JSON, campos aditivos; **valores de CBS/IBS mudam** para itens do Anexo I | `X-API-Key` |

**Custo por requisição:** no máximo **2 queries** (1 da TIPI + 1 da cesta básica), ambas O(1) no
número de itens do payload. As duas mantêm domínios de falha separados de propósito: uma tabela
sem `GRANT` degrada só o seu tributo. Fundi-las numa "consulta de tributos" faria a falha de uma
apagar a outra.

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit puro | `digitos_ncm`/`prefixos_ncm`; `resolver_item` nas 6 situações; desempate 15/25 e 4/26; `aplicar_reducao_a_zero` + invariante do líquido | `tests/test_cesta_basica_resolucao.py` | pytest | Toda a lógica de política e aritmética, sem banco |
| Integration (fake) | AT-001..AT-005 via `TestClient` + `FakePool`; 1 query; pool `None`; pool que explode | `tests/test_api_simulate_cesta_basica.py` | pytest + `TestClient` | Contrato da resposta |
| Integration (Postgres real) | Contagens do seed (26/76/19), as 2 CHECKs recusando linha inválida, invariante de exceção, lookup em lote, tabela removida | `tests/test_cesta_basica_db.py` | pytest + container `postgres:16` do CI | SQL e constraints de verdade |
| Verificação real | Papel `taxreformai_app` lendo o Anexo I no Cloud SQL | `scripts/verificar_cesta_basica_producao.py` via `migrar_banco.yml` | workflow_dispatch | Decisão 13 |
| E2E produção | 2ª chamada do smoke test: `total_cbs_dispensado` não-nulo e `cbs_percentual == 0` | `.github/workflows/deploy.yml` | curl + jq | Decisão 13 |

**Mapa Acceptance Test → teste:**

| AT | Cenário concreto | Onde | Asserção-chave |
|----|------------------|------|----------------|
| AT-001 | Manteiga `0405.10.00` (item 5, EXATO) | `test_api_simulate_cesta_basica.py` | `total_cbs`/`total_ibs` do item = 0; `dispositivo_legal_ref == "LCP 214/2025, art. 125, Anexo I, item 5"`; `aliquotas_aplicadas.cbs_percentual == 0`; `valor_liquido == valor_base` (IS zero em 2026) |
| AT-002 | Cerveja `22030000` (o NCM do smoke test atual) | idem | `situacao == "FORA_DO_ANEXO"`; CBS = 0,9% e IBS = 0,1% da fase, idênticos ao teste que já existe; nenhuma referência ao Anexo I |
| AT-003 | Café `09012100` (item 8, PREFIXO de 4) e mate `09032000` (item 23) | idem + unit | `situacao == "APLICADA"`, `tipo_correspondencia == "PREFIXO"`, `ncm_correspondido == "09.01"`, CBS/IBS = 0 |
| AT-004 | Foie gras `02074300` (excluído pelo item 19) e salmão `03021100` (excluído pelo item 20) | idem + unit | `situacao == "EXCLUIDA_EXPRESSAMENTE"`; CBS/IBS na alíquota **geral**; `ncm_correspondido == "0207.43.00"` / `"0302.1"`; **nunca** zero |
| AT-005 | Arroz com casca `10061010` — dentro de `1006`, fora de `1006.20`/`1006.30`/`1006.40.00` | idem + unit | `situacao == "FORA_DO_ANEXO"`; prova que o match respeita o limite da subposição e não é "contém a substring" |

**Testes além dos AT, por causa das decisões novas:**

- **Sobreposição 15/25:** `19021900` → cita o item **25**, `itens_correspondentes == [15, 25]`.
- **Sobreposição 4/26:** `21069090` → cita o item **4** (empate em 8 dígitos, menor número),
  `itens_correspondentes == [4, 26]`.
- **Prefixo de 7 dígitos:** `02109911` → APLICADA pelo item 19 (`0210.99.1`) — o único caso de 7
  no Anexo, e o comprimento que não aparece em nenhum outro lugar do projeto.
- **Invariante do líquido:** depois de `aplicar_reducao_a_zero`,
  `valor_liquido == valor_base - total_tributos` e `total_tributos == valor_is`; mais o ramo
  `split_payment_active=False` (líquido = bruto).
- **Invariante do seed** (Postgres real): toda linha `excecao=true` tem uma inclusão do mesmo item
  que é prefixo dela — impede que uma exceção órfã produza `EXCLUIDA_EXPRESSAMENTE` sem que o item
  jamais tivesse incluído o código.
- **CHECK `prefixo_bate_com_texto`** rejeita `('0210.99.1', '02109910')`; **CHECK de comprimento**
  rejeita `'020'`.
- **Pool `None`** → todos os itens `CONSULTA_INDISPONIVEL`, 200, CBS/IBS na alíquota geral,
  `total_cbs_dispensado is None`. É a prova de que a feature é aditiva: é o estado de toda a suíte
  atual e de qualquer deploy sem Cloud SQL.
- **Pool que levanta `ConnectionError`** → 200, não 5xx, com situação distinta de `FORA_DO_ANEXO`.
- **Serviço** → `NAO_APLICAVEL`, nenhum prefixo coletado, `pool.connection` nunca chamado.

**Testes existentes que devem continuar passando sem edição:** `tests/test_ipi_resolucao.py`
(cobre `normalizar_ncm`, que a Decisão 10 refatora sem mudar comportamento),
`tests/test_api_simulate_ipi.py`, `tests/test_api_simulate.py`, `tests/test_escopo_e_compensacao.py`
e `tests/test_engine.py` / `tests/test_tabela_aliquotas.py` (o campo novo de `RegraFiscal` tem
default). Se algum precisar mudar, é regressão de contrato, não teste desatualizado. **Exceção
prevista e única:** `tests/test_schema_postgres.py`, que perde 2 testes por decisão explícita
(Decisão 12).

---

## Error Handling

| Error Type | Handling Strategy | HTTP | Retry? |
|------------|---------------------|------|--------|
| NCM fora do Anexo I | `FORA_DO_ANEXO`, alíquota geral da fase | 200 | Não — reenviar não muda |
| NCM excluído pelo próprio item (19/20) | `EXCLUIDA_EXPRESSAMENTE` + citação da exceção; **nunca** zero | 200 | Não |
| NCM ilegível (parcial, vazio, com sufixo EX) | `NCM_NAO_RECONHECIDO`, sem consultar o banco, item enumerado em `itens_nao_avaliados` | 200 | Não |
| Cloud SQL fora do ar / timeout / grant faltando | `CONSULTA_INDISPONIVEL` em todos os itens de mercadoria + `logger.exception` | 200 | Sim, pelo cliente |
| `db_pool is None` (sem `DB_INSTANCE_CONNECTION_NAME`) | Idem, sem log de exceção — é estado esperado | 200 | N/A |
| `psycopg` não instalado no processo | Import tardio → `ImportError` capturado como indisponibilidade | 200 | N/A |
| Item `natureza=SERVICO` | `NAO_APLICAVEL`, sem coletar prefixo | 200 | N/A |
| Fase sem alíquota confirmada (2027+) | 422 **antes** do laço, como hoje — a redução nem chega a ser avaliada | 422 | N/A |

Nada nesta feature introduz um código de erro novo. É proposital: a redução é aditiva, e nenhum
modo de falha dela justifica invalidar CBS/IBS, que são o produto central da simulação.

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `DB_INSTANCE_CONNECTION_NAME` | string | — | Já existente (`api/db.py`); ausente ⇒ `CONSULTA_INDISPONIVEL` |
| `DB_USER` | string | `taxreformai_app` | Já existente; é o papel que precisa do `GRANT SELECT` da migração 005 |
| `verificar_cesta_basica` (input de workflow) | `sim`/`nao` | `sim` | Novo input de `migrar_banco.yml` (Decisão 13) |

Nenhuma variável de ambiente nova na aplicação, nenhuma mudança de Terraform/IaC. Duas migrações
novas, aplicadas pelo fluxo já existente (`migrar_banco.yml`, guarda `MIGRAR`).

---

## Security Considerations

- **Sem SQL dinâmico.** `= ANY(%s)` recebe a lista como parâmetro vinculado, e todo prefixo passa
  antes por `digitos_ncm`/`prefixos_ncm`, que só deixam passar `[0-9]{4,8}` — a string que chega ao
  banco nunca é o texto bruto do cliente.
- **Sem RLS, deliberadamente.** O Anexo I é lei federal, idêntico para todo tenant — mesma decisão
  já registrada em `aliquotas_ipi_tipi` (migração 004) e na 002. Tenant scoping aqui não protegeria
  nada e quebraria o padrão.
- **Privilégio mínimo preservado.** Só `SELECT` para o papel de runtime; a escrita é exclusiva da
  migração, rodada pelo papel admin. Nenhum grant novo além dos dois `SELECT`.
- **`DROP TABLE` guardado.** A migração 006 recusa derrubar uma tabela com linhas — o roteiro
  destrutivo é o único da feature e não confia em memória sobre o estado do banco.
- **Sem PII.** NCM, descrição de produto e dispositivo legal são dados públicos; nada aqui entra na
  máscara de PII de `orquestracao/nos/classificador.py`.
- **Enumeração não é vazamento.** O Anexo I é publicado no DOU; responder "este NCM não está na
  cesta básica" não revela nada que o cliente não possa ler no Diário Oficial.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `api.cesta_basica` quando a consulta falha — stdout do container → Cloud Logging. É o **único** sinal em runtime de que a redução parou de ser aplicada (consequência aceita da Decisão 8), e por isso a Decisão 13 exige verificação ativa |
| Resposta | `cesta_basica.consulta_disponivel` e `itens_nao_avaliados[]` tornam a degradação inspecionável por máquina, sem parsing de português |
| Metrics | Fora de escopo (mesmo tratamento do DEFINE da feature 1) |
| Verificação ativa | `scripts/verificar_cesta_basica_producao.py` + 2ª asserção no smoke test do deploy |

---

## Limitações declaradas (e por que não são resolvidas aqui)

1. **A correspondência é por NCM/SH, e o Anexo I qualifica vários itens além do código.** Os itens
   2, 3, 4, 9 e 22 exigem "conformidade com os requisitos da legislação específica"; o item 16
   descreve o pão francês por formato, miolo e casca; o item 19, alínea c, inclui `0210.99.90`
   apenas enquanto **carne caprina** (o código abrange "outras"); os itens 24-26 são destinados a
   pessoas com aminoacidopatias e erros inatos do metabolismo. **Nenhuma dessas condições é
   verificável a partir do payload atual**, que só traz `sku`, `ncm`, quantidade, valor e UFs. A
   feature aplica zero pelo código e devolve a `descricao` literal do item, para que o cliente
   confira a condição; a advertência do escopo e `CestaBasicaResumo.fonte_legal` dizem isso
   explicitamente. É uma correspondência **necessária, nem sempre suficiente** — e o lugar natural
   para fechar essa lacuna é `API_EMPRESA_SKUS` (posição 3 da sequência), onde o cliente cadastra
   descrição e atributos por SKU.
2. **Só o Anexo I.** Os outros 16 Anexos (reduções de 60%, serviços por NBS, Imposto Seletivo no
   XVII) continuam sem efeito na simulação. O schema desta feature é dedicado ao Anexo I e não
   pretende ser genérico: quando outro Anexo entrar, sua forma (percentual de redução, `nbs_code`)
   será examinada contra o texto dele, não presumida agora.
3. **Sem dimensão temporal.** O Anexo XVIII (versão "produção de efeitos futura" do Anexo I) está
   fora de escopo, e a tabela não tem `vigencia_inicio`/`vigencia_fim`. Uma alteração futura do
   Anexo I exige nova migração — mesma decisão já registrada para SPED/IBPT e TIPI.
4. **2026 é a única fase em que a redução tem efeito prático hoje**, porque 2027-2028 é recusada
   com 422 pela CBS pendente do art. 347 e 2029+ não existe em `TabelaAliquotasSeed`. O seed de
   `fonte_legal_reducoes` para 2027-2028 já está correto e passa a valer sozinho no dia em que a
   alíquota de referência for fixada.

---

## Open Questions do DEFINE — resolvidas aqui

| # | Pergunta | Resolução |
|---|----------|-----------|
| 1 | Risco de tamanho: 6 de 26 itens exigem correspondência não-trivial | **Os 6 são resolvidos nesta iteração, sem custo extra de código** — a Decisão 1 mostra que prefixo e igualdade são o mesmo mecanismo. O crescimento da feature (19 arquivos vs. 12) vem do schema novo, do override por item e da remoção do código morto, não dos 6 itens |
| 2 | Impacto da LC 227/2026 no restante da LCP 214/2025 | **Fora de escopo, confirmado.** Esta sessão releu a lista de alterações: o art. 125 e o Anexo I não estão nela. Segue como achado de projeto próprio (`DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md`, ainda em Needs Clarification) |
| 3 | Nome da tabela nova e destino de `regras_tributarias_cache` | `cesta_basica_anexo_i` + `cesta_basica_anexo_i_ncm` (Decisão 3); tabela e função antigas **removidas** (Decisão 12) |
| — | `COULD`: sobreposição item 15 × item 25 | Resolvida pela Decisão 4, que também cobre a sobreposição **4 × 26** descoberta nesta sessão |

**Três perguntas que o DEFINE não previu e o Design precisou responder**, todas descobertas lendo a
fonte primária e o código real: se a redução vale na fase de teste de 2026 (Decisão 5 — sem ela a
feature não teria nenhum ano em que produzir efeito), o que fazer com o `valor_liquido` do split
payment quando CBS/IBS são zerados (Decisão 6), e o fato de que acrescentar um item ao payload do
smoke test do deploy derrubaria a asserção de `total_ipi` da feature anterior (Decisão 13).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | design-agent | Versão inicial, a partir de `DEFINE_REGRAS_TRIBUTARIAS_CACHE.md` v1.0; transcrição literal completa do Anexo I e leitura dos arts. 125/126/343-348 contra a fonte primária do Senado |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_REGRAS_TRIBUTARIAS_CACHE.md`

Ordem sugerida de implementação: migração 005 e seed (1) → repositório e `api/ncm.py` (3, 4, 5) →
resolução e redução (6, 7, 8, 9) → schemas e router (10, 11) → testes (12, 13, 14, 15) → migração
006 e limpeza (2) → verificação real e workflows (16, 17, 18) → `CLAUDE.md` (19).

**A feature só é dada como pronta depois das duas verificações da Decisão 13** — `migrar_banco.yml`
com `verificar_cesta_basica=sim` e a segunda chamada do smoke test do `deploy.yml` — e então
`/ship`.
