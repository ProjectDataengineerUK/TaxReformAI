# DESIGN: Anexos XII, XIII e XV — redução a zero de CBS/IBS por NCM

> Technical design para generalizar o schema do Anexo I (hoje `cesta_basica_anexo_i*`) a **quatro
> Anexos de redução a zero**, carregar os Anexos XII (dispositivos médicos), XIII (acessibilidade)
> e XV (hortícolas, frutas e ovos) da LCP 214/2025 e aplicá-los em `POST /v1/tax/simulate` —
> **sem nenhuma função de cálculo nova** e sem tocar `motor_calculo/`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_ZERO_XII_XIII_XV |
| **Date** | 2026-07-28 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md](./DEFINE_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md) |
| **BRAINSTORM** | [BRAINSTORM_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md](./BRAINSTORM_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md) |
| **Feature irmã (referência de mecanismo)** | [`REGRAS_TRIBUTARIAS_CACHE`](../archive/REGRAS_TRIBUTARIAS_CACHE/DESIGN_REGRAS_TRIBUTARIAS_CACHE.md) — Anexo I, shipada 2026-07-28 |
| **Status** | Ready for Build |
| **Posição na sequência** | 12 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, primeira da segunda leva) |

---

## Verificação de fonte primária feita nesta sessão de `/design`

O DEFINE transcreveu os 3 Anexos em forma resumida e deixou **duas lacunas que impedem escrever a
migração**: (a) o artigo que cria cada uma das três reduções ("prováveis candidatos: arts. 126-131,
a confirmar" — Open Question 2) e (b) a redação literal de cada item, necessária para as colunas
`descricao` e `texto_ncm`. Esta sessão rebuscou a mesma fonte primária e transcreveu os três Anexos
**literalmente**, mais o trecho do corpo da lei que os institui.

| # | O que | URL | Resultado |
|---|-------|-----|-----------|
| 1 | Texto integral do Anexo XII | `https://legis.senado.leg.br/norma/40180341/publicacao/40180960` | HTTP 200 — transcrito na seção "Dados" |
| 2 | Texto integral do Anexo XIII | `https://legis.senado.leg.br/norma/40180341/publicacao/40180966` | HTTP 200 — idem |
| 3 | Texto integral do Anexo XV | `https://legis.senado.leg.br/norma/40180341/publicacao/40181038` | HTTP 200 — idem |
| 4 | Corpo da LCP 214/2025 (arts. 1º a 544) | `https://legis.senado.leg.br/norma/40180341/publicacao/40181429` | HTTP 200 — arts. 143 a 148, 126 e 348 lidos no texto oficial |
| 5 | Página de detalhe da norma (lista de alterações da LC 227/2026) | `https://legis.senado.leg.br/norma/40180341` | HTTP 200 — lista completa de "Normas posteriores" lida |

Consultados em 2026-07-28, com header `User-Agent` de navegador (sem ele, 403 — aviso já herdado).
`planalto.gov.br` continua inacessível deste ambiente.

**Cinco achados de fonte primária que o DEFINE não tinha — os cinco mudam o design:**

1. **Os artigos são 144, 145 e 148** (Open Question 2 resolvida, e nenhum dos "prováveis candidatos"
   do DEFINE estava certo):

   | Anexo | Artigo | Texto do caput |
   |-------|--------|----------------|
   | XII | **art. 144, I** | "Ficam reduzidas a zero as alíquotas do IBS e da CBS incidentes sobre o fornecimento dos dispositivos médicos relacionados: I – no Anexo XII desta Lei Complementar, com a especificação das respectivas classificações da NCM/SH" |
   | XIII | **art. 145, I** | "…dos dispositivos de acessibilidade próprios para pessoas com deficiência relacionados: I – no Anexo XIII…" |
   | XV | **art. 148** | "…sobre o fornecimento dos produtos hortícolas, frutas e ovos relacionados no Anexo XV…" |

2. **O Anexo XV é redução a ZERO no corpo da lei, ainda que o cabeçalho do Anexo diga "100%".**
   O art. 148 escreve "ficam reduzidas a **zero**"; o cabeçalho do Anexo XV diz "SUBMETIDOS À
   REDUÇÃO DE 100% (CEM POR CENTO)". O DEFINE tratava a equivalência como funcional ("100% ≈
   zero"); ela agora é **literal no dispositivo operativo**, e `aplicar_reducao_a_zero` é a função
   certa por texto de lei, não por analogia.

3. **Os três artigos estão dentro do Título IV — "DOS REGIMES DIFERENCIADOS DO IBS E DA CBS"**
   (Capítulo IV, "DA REDUÇÃO A ZERO DAS ALÍQUOTAS DO IBS E DA CBS", arts. 143-149). Isso **fecha a
   única ressalva registrada na Decisão 5 do `/design` do Anexo I**: lá, o art. 125 estava no Título
   III e a ponte de transição do art. 348, III, "a" fala em "regimes diferenciados de tributação",
   o que obrigou a um argumento de que o art. 125 se aplica por si. Aqui a subsunção é literal: os
   Anexos XII/XIII/XV **são** regime diferenciado, e o art. 348, III, "a" os alcança sem ressalva.
   Consequência prática: `motor_calculo/tabela_aliquotas.py::fonte_legal_reducoes` já está correto
   e **não muda uma linha** (o texto semeado não cita o art. 125 — cita os arts. 343/346/348).
4. **A estrutura de itens do Anexo XII é diferente da que o DEFINE descreveu.** O DEFINE inventou
   os rótulos "7-a, 7-b, 7-c"; o DOU tem **um único item 7**, com uma descrição só ("Aparelhos de
   raio X, móveis, exceto os produtos classificados no código 9022.19.91") e **três células de
   NCM** (9022.13, 9022.14, 9022.19). Além disso, os itens **1 (Anexo XII)** e **2 (Anexo XIII)**
   são **linhas de cabeçalho sem NCM**, com os sub-itens abaixo. Isso simplifica o desempate (a
   exceção do item 7 é escopada ao item, como no Anexo I, e não precisa de escopo por alínea) e
   cria uma pergunta nova, resolvida na Decisão 7 (o que fazer com linhas de cabeçalho).
   **As contagens do DEFINE continuam corretas**: 24 linhas em XII, 7 em XIII, 25 em XV.
5. **A LC 227/2026 não alterou os arts. 143-145, 147 nem 148** — verificado na lista literal de
   "Alteração Permanente" da norma, que dessa faixa cita apenas `Art. 142, caput, Inciso 2`,
   **`Art. 146`** (medicamentos, Anexo XIV), `Art. 149, § 2, Inciso 2` e `Art. 149, § 3`. O DEFINE
   tinha verificado só os **Anexos**; esta sessão verificou também os **artigos que esta feature
   passa a citar**, que é o que `dispositivo_legal_ref` afirma ao cliente.

**Achado adicional, fora de escopo mas que muda a próxima feature:** o art. 144, **II** e o art.
145, **II** reduzem a **zero** os Anexos **IV** e **V** quando adquiridos por órgãos públicos ou
entidades CEBAS — ou seja, os Anexos IV e V **não são apenas "60%"**, como o roadmap os classifica
(posição 13): têm uma alíquota zero condicionada ao *comprador*, condição que o payload atual de
`/v1/tax/simulate` não expressa. Registrado aqui para o `/define` da posição 13; **nada é feito a
respeito nesta feature** (IV e V estão explicitamente fora de escopo no DEFINE).

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────────────────┐
│  POST /v1/tax/simulate — redução a zero de CBS/IBS por item, agora em 4 Anexos      │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  [Cliente ERP] ──X-API-Key──► api/routers/simulate.py                              │
│                                     │                                              │
│      ┌──────────────────────────────┼──────────────────────────────┐               │
│      │ (1) ANTES do laço            │                              │               │
│      ▼                              ▼                              ▼               │
│  api/ncm.py                api/reducao_zero.py               api/ipi.py            │
│  digitos_ncm()             consultar_com_seguranca           (intocado)            │
│  prefixos_ncm()  ─────────────►     │  nunca levanta               │               │
│  2,4,5,6,7,8 dígitos                ▼                              ▼               │
│  (era 4..8)         db.repositorio.buscar_reducao_zero_por_prefixo │               │
│                                     │  1 query / request           │               │
│                                     ▼                              ▼               │
│                  ┌──────────────────────────────────────┐   aliquotas_ipi_tipi     │
│                  │ Cloud SQL                            │                          │
│                  │ anexos_reducao_zero      (60 itens)  │  ← 007 renomeia e        │
│                  │ anexos_reducao_zero_ncm  (151 linhas)│    generaliza; 008       │
│                  │   I:26/95 · XII:20/24 · XIII:8/7     │    carrega XII/XIII/XV   │
│                  │   XV:6/25   (127 inclusões+24 exceç.)│  GRANT SELECT → app      │
│                  └──────────────────────────────────────┘                          │
│                                                                                    │
│      │ (2) POR item de MERCADORIA                                                  │
│      ▼                                                                             │
│  reducao_zero.resolver_item(ncm) ──► SituacaoReducaoZero ∈                         │
│      │   {APLICADA, EXCLUIDA_EXPRESSAMENTE, FORA_DO_ANEXO, NCM_NAO_RECONHECIDO,     │
│      │    CONSULTA_INDISPONIVEL, NAO_APLICAVEL}          (os 6 estados de antes)    │
│      │   desempate: prefixo mais longo → menor Anexo → menor item → menor sub-item  │
│      ▼ APLICADA?                                                                   │
│  motor_calculo/reducoes.aplicar_reducao_a_zero(ResultadoCalculo)  ← INTOCADO        │
│      │   CBS=0, IBS=0, IS intacto, valor_liquido recomposto                        │
│      ▼                                                                             │
│  ItemDetalhado.reducao_zero{anexo, item, dispositivo_legal_ref, …}                 │
│      ▼ (3) agregação                                                               │
│  RespostaSimulacao.reducao_zero = ReducaoZeroResumo(total_cbs_dispensado, …)       │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

Fluxo de degradação — idêntico ao já shipado (Decisão 8 do Anexo I), nada novo aqui:

  Banco fora do ar ─────► CONSULTA_INDISPONIVEL ─┐
  NCM ilegível     ─────► NCM_NAO_RECONHECIDO ───┼─► 200 + alíquota GERAL da fase
  NCM fora dos 4 Anexos► FORA_DO_ANEXO ──────────┤   (tributo MAIOR que o devido,
  NCM excluído pelo item► EXCLUIDA_EXPRESSAMENTE─┘    nunca menor) + advertência
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db/migrations/007_generalizar_anexos_reducao_zero.sql` | **Novo** — renomeia as 2 tabelas, troca a PK para `(anexo, item, sub_item)`, alarga a CHECK de comprimento para `{2,4,5,6,7,8}`, adiciona a CHECK que amarra `dispositivo_legal_ref` à chave, e **prova** que o Anexo I sobreviveu (26/95) | SQL puro |
| `db/migrations/008_anexos_reducao_zero_xii_xiii_xv.sql` | **Novo** — seed dos 3 Anexos (34 itens, 56 prefixos) + bloco de asserções que recusa transcrição inconsistente | SQL puro |
| `db.repositorio.PrefixoReducaoZero` | **Renomeado/estendido** (era `PrefixoCestaBasica`) — ganha `anexo`, `anexo_ordem`, `sub_item`, `descricao_contexto` | `dataclasses` |
| `db.repositorio.buscar_reducao_zero_por_prefixo` | **Renomeado** (era `buscar_cesta_basica_por_prefixo`) — mesma query `= ANY(%s)`, mais um `LEFT JOIN` do item-pai | `psycopg` + SQL |
| `api/ncm.py` | **Modificado** — `_COMPRIMENTOS_PREFIXO` passa de `(4,5,6,7,8)` para `(2,4,5,6,7,8)`; `digitos_ncm` intocado | Python puro |
| `api/reducao_zero.py` | **Renomeado** (era `api/cesta_basica.py`) — `SituacaoReducaoZero`, `ResolucaoReducaoZero`, `ConsultaReducaoZero`, `consultar_com_seguranca`, `resolver_item`, `formatar_item` | Python + `logging` |
| `api/schemas_simulate.py` | **Modificado** — `ReducaoZeroItem`/`ReducaoZeroResumo`/`ItemCorrespondente` no lugar de `CestaBasicaItem`/`CestaBasicaResumo` | `pydantic.BaseModel` |
| `api/routers/simulate.py` | **Modificado** — nomes, agregação por Anexo, advertência e parecer do audit log | FastAPI `APIRouter` |
| `motor_calculo/*` | **Intocado** — `aplicar_reducao_a_zero`, `RegraFiscal.fonte_legal_reducoes` e o seed por fase já servem os 4 Anexos (achado 3) | — |
| `scripts/verificar_reducao_zero_producao.py` | **Renomeado/estendido** — prova, com o papel de runtime contra o Cloud SQL real, os 4 Anexos e os 3 mecanismos novos | Python + `psycopg` |

---

## Key Decisions

### Decision 1: uma tabela para os 4 Anexos, generalizada por `ALTER` — não uma tabela por Anexo, não uma tabela nova

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `A-004` do DEFINE (confirmação da Approach A); achado estrutural 1 |

**Context:** O DEFINE pede confirmação explícita de que os 3 achados estruturais (namespace de item
por Anexo, numeração decimal, prefixo de 2 dígitos) não inviabilizam a Approach A do brainstorm
(estender o schema do Anexo I). As alternativas eram uma tabela por Anexo (Approach B) ou uma
tabela nova, genérica, com recarga do Anexo I.

**Choice:** **Approach A confirmada.** As duas tabelas existentes são **renomeadas e generalizadas
por `ALTER`**, sem recriar nem repopular nada:

```text
cesta_basica_anexo_i      →  anexos_reducao_zero       (item do Anexo; 26 → 60 linhas)
cesta_basica_anexo_i_ncm  →  anexos_reducao_zero_ncm   (prefixo;      95 → 151 linhas)
```

Duas migrações, não uma (mesmo motivo da separação 005/006 do Anexo I: cada migração faz uma coisa
só, e reverter uma transcrição ruim não deve reverter o schema):

- **007** — só forma: rename, colunas novas, PK/FK/UNIQUE/CHECK novas, e a prova de que o Anexo I
  atravessou intacto.
- **008** — só dado: o seed dos 3 Anexos e suas asserções.

**Rationale:**

1. **Nenhum dos 3 achados toca o mecanismo, só a chave e o intervalo.** A correspondência continua
   sendo "prefixo de dígitos de comprimento variável" (Decisão 1 do Anexo I), a exceção continua
   escopada ao item (Decisão 3 de lá) e o override continua sendo `aplicar_reducao_a_zero`. O que
   muda é *quem é o item* (`(anexo, item, sub_item)` em vez de `item`) e *quanto pode medir um
   prefixo* (2 a 8 em vez de 4 a 8). Isso é exatamente o que a Approach A previa.
2. **Uma tabela por Anexo multiplicaria o caminho de código por 4** — 4 lookups, 4 resoluções, e a
   pergunta "qual Anexo cita?" viraria uma junção feita em Python entre 4 listas, sem ordem total.
   Com uma tabela, o desempate da Decisão 5 resolve tudo de uma vez, e AT-003 ("NCM fora dos 4
   Anexos") é uma consulta só que volta vazia.
3. **`ALTER` em vez de tabela nova porque o DEFINE proíbe repopular o Anexo I** ("não re-popular
   seus dados", Out of Scope). Uma tabela nova exigiria retranscrever 95 linhas do DOU — a operação
   com maior chance de introduzir um erro de dígito em toda a feature, sem nenhum ganho. Com
   `ALTER`, as 121 linhas do Anexo I nunca são reescritas: ganham colunas com `DEFAULT 'I'`/`0` que
   são verdade sobre elas, e os defaults são removidos em seguida para não valerem sobre as
   próximas.
4. **O rename é obrigatório, não cosmético.** Um tomógrafo gravado numa tabela chamada
   `cesta_basica_anexo_i` é uma afirmação falsa dentro de um produto cujo valor inteiro é
   auditabilidade — e a migração é o documento de auditoria (Decisão 11 do Anexo I). `ALTER TABLE
   … RENAME` preserva dados, índices e **privilégios** (o `GRANT SELECT` da 005 segue valendo; a
   007 reemite mesmo assim, custo zero).

**Alternatives Rejected:**

1. **Uma tabela por Anexo (Approach B do brainstorm)** — rejeitada pelo motivo 2. Ela só seria
   melhor se os Anexos tivessem *formas* diferentes; têm a mesma (item → N prefixos, com exceções).
2. **Tabela nova genérica + `INSERT … SELECT` do Anexo I + `DROP` da antiga** — rejeitada pelo
   motivo 3 em sua variante mais cara (retranscrição) e, na variante `INSERT … SELECT`, por ser
   um `ALTER` disfarçado com um `DROP` a mais no caminho.
3. **Manter os nomes `cesta_basica_anexo_i*` e só acrescentar a coluna `anexo`** — rejeitada pelo
   motivo 4.
4. **Resolver agora a forma genérica para os 16 Anexos** (percentual, NBS, condicionado ao
   comprador) — rejeitada por instrução explícita do DEFINE e porque as posições 13/14 têm formas
   *provadamente diferentes* (percentual sobre alíquota de referência, chave NBS, e o achado do
   art. 144, II). Presumir a forma delas hoje seria adivinhar; esta tabela declara no nome e numa
   CHECK que trata de **redução a zero**, e é só isso.

---

### Decision 2: a identidade do item é `(anexo, item, sub_item)`, com `sub_item = 0` significando "sem sub-item"

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Achados estruturais 1 e 2 do DEFINE (numeração reinicia por Anexo; sub-itens decimais) |

**Context:** `cesta_basica_anexo_i.item` é `SMALLINT PRIMARY KEY CHECK (item BETWEEN 1 AND 26)` —
namespace global de 1 a 26. Os três Anexos novos têm "item 1" próprio, e dois deles numeram
sub-itens em decimal (`1.1`, `1.2`, `1.3` no XII; `2.1`, `2.2` no XIII). As opções mapeadas pelo
DEFINE eram `item TEXT` ou duas colunas.

**Choice:** **Duas colunas inteiras**, mais o Anexo, formando a chave primária:

```sql
anexo    VARCHAR(4) NOT NULL,      -- 'I' | 'XII' | 'XIII' | 'XV'
item     SMALLINT   NOT NULL CHECK (item >= 1),
sub_item SMALLINT   NOT NULL DEFAULT 0 CHECK (sub_item >= 0),
PRIMARY KEY (anexo, item, sub_item)
```

`sub_item = 0` é o sentinela para "este item não tem sub-item" (as 26 linhas do Anexo I recebem 0
no backfill). A grafia canônica — `"5"`, `"1.2"` — é **derivada**, nunca armazenada:

```python
def formatar_item(item: int, sub_item: int) -> str:
    return f"{item}.{sub_item}" if sub_item else str(item)
```

**Rationale:**

1. **`sub_item NOT NULL` não é preferência de estilo: é o que faz a FK existir.** A tabela de
   prefixos referencia o item por chave composta. Em Postgres, uma FK com `MATCH SIMPLE` (o padrão)
   é **satisfeita trivialmente quando qualquer coluna da chave é NULL** — com `sub_item` anulável,
   toda linha de prefixo com `sub_item IS NULL` teria integridade referencial *desligada*, sem
   erro, sem sintoma. O sentinela 0 é o que mantém a garantia que a migração 005 já tinha.
   Pelo mesmo motivo, `UNIQUE` parcial (`… WHERE sub_item IS NULL`) não serve: FK exige uma única
   constraint de unicidade sobre exatamente as colunas referenciadas.
2. **0 nunca colide com dado real:** a lei numera sub-itens a partir de 1 e jamais escreve
   "item 1.0". A `CHECK` da Decisão 3 (`dispositivo_legal_ref` termina com a grafia derivada) faz o
   banco recusar qualquer linha em que o sentinela discorde da citação legal.
3. **Ordenação numérica sai de graça, e ela é o ponto do desempate.** O DEFINE alerta que `"14" <
   "1.2"` lexicograficamente enquanto `1.2 < 14` numericamente, e que a lei quer a ordem numérica.
   Com dois inteiros, a comparação é `(item, sub_item)` — numérica por construção, sem parser, sem
   risco de alguém ordenar strings por engano em SQL (`ORDER BY item`) e obter a ordem errada.
   Com `item TEXT`, todo ponto de ordenação (Python, SQL, teste) precisaria lembrar de converter.
4. **`item TEXT` também obrigaria a converter a coluna do Anexo I** (`SMALLINT → TEXT`) e a mexer
   na FK inteira só para acomodar 5 linhas com ponto. Duas colunas custam um `ADD COLUMN` com
   default correto e nada mais.

**Alternatives Rejected:**

1. **`item TEXT` com `CHECK (item ~ '^[0-9]+(\.[0-9]+)?$')`** — rejeitada pelos motivos 3 e 4. Fica
   registrado que ela é *mais fiel à grafia* e que essa fidelidade é recuperada pela função
   `formatar_item` e pela CHECK da Decisão 3, sem custar a ordenação.
2. **`sub_item SMALLINT NULL` com `UNIQUE` parcial** — rejeitada pelo motivo 1 (FK vazia).
3. **`item DECIMAL(4,1)`** (1.2 como número) — rejeitada: `1.10` e `1.1` seriam o mesmo número, e a
   NCM/SH não é o único lugar deste projeto onde "o zero à direita importa"; além disso, um Anexo
   futuro com `1.10` depois de `1.9` (que existe: o Anexo XI tem itens 1.4/1.5/1.8/1.9) seria
   ordenado errado.

---

### Decision 3: `anexo` é um conjunto fechado, e a citação legal é amarrada à chave por CHECK

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Ordem total entre Anexos (pré-requisito da Decisão 5); erro de transcrição em `dispositivo_legal_ref` |

**Context:** O desempate precisa de uma ordem total entre Anexos, e numeral romano **não ordena
lexicograficamente** (`'IV' < 'IX' < 'V'` como texto, mas 4 < 5 < 9 como número — a ordem se
inverte). Ao mesmo tempo, `dispositivo_legal_ref` passa a ser transcrito 34 vezes a mais, e um erro
nele ("Anexo XII, item 13" numa linha cujo item é 14) é invisível: o número certo continua na
chave, e o cliente recebe a citação errada.

**Choice:** Duas constraints declarativas na tabela de itens:

```sql
-- Conjunto fechado, com o ordinal declarado no MESMO lugar que o rótulo.
CONSTRAINT anexo_conhecido CHECK (
    (anexo, anexo_ordem) IN (('I', 1), ('XII', 12), ('XIII', 13), ('XV', 15))
),

-- A citação legal precisa terminar com o Anexo e o item que estão na CHAVE.
CONSTRAINT dispositivo_cita_o_proprio_item CHECK (
    dispositivo_legal_ref LIKE '%Anexo ' || anexo || ', item '
        || CASE WHEN sub_item = 0 THEN item::text
                ELSE item::text || '.' || sub_item::text END
)
```

**Rationale:**

1. **O ordinal mora ao lado do rótulo, então não pode divergir dele.** A alternativa óbvia — um
   dicionário `{"I": 1, "XII": 12, …}` em Python — cria dois lugares onde a mesma verdade é
   declarada, e o dia em que o Anexo XVI entrar num deles e não no outro produz uma ordem de
   desempate silenciosamente errada. É o mesmo raciocínio do acoplamento `_COMPRIMENTOS_PREFIXO` ↔
   `prefixo_comprimento_valido`, só que aqui o acoplamento é eliminado em vez de documentado: o
   Python lê `anexo_ordem` da linha e não sabe nada sobre numerais romanos.
2. **O conjunto fechado declara o significado da tabela.** `anexos_reducao_zero` é "os Anexos cuja
   redução é a zero" — I (art. 125), XII (art. 144), XIII (art. 145) e XV (art. 148). A CHECK
   impede que alguém carregue aqui o Anexo IV (60%, art. 131) porque "é NCM também". Um Anexo novo
   exige uma migração que declare explicitamente o par `(rótulo, ordinal)` — que é exatamente a
   decisão consciente que se quer forçar.
3. **A segunda CHECK é da mesma família de `prefixo_bate_com_texto`** (Decisão 11 do Anexo I): um
   dado transcrito duas vezes é conferido pelo banco no `INSERT`, e a migração inteira faz rollback
   se as duas grafias discordarem. Ela custa nada, cobre as 60 linhas (inclusive as 26 do Anexo I,
   que passam sem alteração) e substitui com vantagem o teste
   `test_todo_item_cita_o_proprio_numero_no_dispositivo_legal`, que só rodava no CI.
4. **`LIKE` com padrão construído por concatenação é seguro aqui**: `anexo` e os inteiros não
   contêm `%` nem `_`, e a âncora é o fim da string — `'…item 15'` não casa com o padrão
   `'%item 5'` (os últimos 6 caracteres são `tem 15`).

**Alternatives Rejected:**

1. **Ordenar Anexos pelo texto do rótulo** — rejeitada: numeral romano em ordem lexicográfica é
   errado em geral (`IV`/`IX`/`V`) e *acidentalmente* certo para os 4 rótulos de hoje, que é a pior
   combinação possível (passa nos testes de hoje, quebra no primeiro Anexo novo).
2. **Um parser de numeral romano** — rejeitado: código novo, testável, para converter 4 valores
   fixos que a lei não vai renumerar.
3. **`anexo` como `ENUM` do Postgres** — rejeitado: acrescentar valor a um tipo `ENUM` tem regras
   próprias (não pode ser feito dentro de qualquer transação em versões antigas) e não carrega o
   ordinal junto, que é metade do ponto.

---

### Decision 4: o prefixo passa a aceitar **2** dígitos — e a lista é `{2,4,5,6,7,8}`, não o intervalo `2..8`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Achado estrutural 3 do DEFINE (Capítulo 6, Anexo XV, item 4) |

**Context:** O Anexo XV, item 4, cita "**Capítulo 6** da NCM/SH" — um prefixo de 2 dígitos. Hoje
`api/ncm.py::_COMPRIMENTOS_PREFIXO = (4,5,6,7,8)` e a CHECK `prefixo ~ '^[0-9]{4,8}$'` (migração
005) rejeitam qualquer coisa menor que 4, e o comentário da própria 005 já previa: *"Se um Anexo
futuro citar capítulo (2 dígitos), os DOIS mudam juntos"*. O DEFINE pede alargar para `2..8`.

**Choice:** Os dois lados mudam juntos, e para **`{2, 4, 5, 6, 7, 8}` — sem o 3**:

```python
# api/ncm.py
_COMPRIMENTOS_PREFIXO = (2, 4, 5, 6, 7, 8)
```

```sql
CONSTRAINT prefixo_comprimento_valido
    CHECK (prefixo ~ '^[0-9]+$' AND length(prefixo) IN (2, 4, 5, 6, 7, 8))
```

**Rationale:**

1. **Não existe nível de 3 dígitos na NCM/SH.** Os níveis são capítulo (2), posição (4), subposição
   (5 ou 6), item (7) e subitem (8). Um `CHECK (… ~ '^[0-9]{2,8}$')` aceitaria `'060'`, que é
   transcrição errada de alguma coisa e **nunca casaria com nada** — o falso negativo mudo que a
   Decisão 2 do Anexo I existe para impedir. Trocar a regex por uma lista de comprimentos mantém a
   propriedade original ("o que a tabela aceita é exatamente o que o gerador enxerga") em vez de
   afrouxá-la.
2. **A simetria continua exata:** `prefixos_ncm` gera 6 candidatos por código, e a CHECK aceita
   exatamente esses 6 comprimentos. Nenhuma linha inserível é invisível ao gerador; nenhum
   candidato gerado é inaceitável pela tabela.
3. **Custo de consulta desprezível:** de 5 para 6 prefixos por código — no pior payload (100
   itens), 600 strings em vez de 500, todas deduplicadas antes da query, com o mesmo índice.
4. **O `texto_ncm` desta linha é `'06'`, não `'Capítulo 6'`** — a única linha das 151 em que a
   coluna não copia a grafia do DOU. Motivo: `texto_ncm` é definido como *a grafia do código*, e
   aqui o DOU não escreve código nenhum, escreve prosa ("classificados no Capítulo 6 da NCM/SH").
   A prosa é preservada onde ela realmente mora — na `descricao` literal do item. Escrever
   `'Capítulo 6'` em `texto_ncm` faria `prefixo_bate_com_texto` derivar `'6'` (um dígito) e a
   migração falharia — o que, note-se, é a constraint funcionando: ela força a decisão a ser
   tomada, em vez de deixá-la implícita.

**Consequência declarada (e é a mais perigosa desta feature):** um prefixo de 2 dígitos é 100× mais
amplo que um de 4. `'06'` concede alíquota zero a **todo o Capítulo 6** da NCM, enquanto o item 4
qualifica: "plantas e produtos de floricultura **relativos à horticultura e cultivados para fins
alimentares, ornamentais ou medicinais**". Essa qualificação **restringe**, não amplia, e não é
verificável a partir do payload (que traz só `sku`, `ncm`, quantidade e valor) — ou seja, o erro
aqui é na direção **perigosa** (tributo a menos), diferente da degradação da Decisão 8 do Anexo I.
É a mesma classe de limitação já aceita e declarada no Anexo I ("em conformidade com os requisitos
da legislação específica", "carne caprina classificada no código 0210.99.90"), e recebe o mesmo
tratamento: a `descricao` literal volta na resposta, `fonte_legal` do resumo diz que a
correspondência é por NCM/SH e que condições textuais do item não são verificadas. Ver "Limitações
declaradas", item 1 — **e é por isso que ela está escrita aqui, não escondida numa nota de rodapé.**

**Alternatives Rejected:**

1. **`CHECK (prefixo ~ '^[0-9]{2,8}$')`** (o alargamento literal que o DEFINE sugeriu) — rejeitado
   pelo motivo 1: admite comprimento 3, que a NCM não tem e o gerador não enxerga.
2. **Tratar o Capítulo 6 como caso especial** (uma coluna `capitulo` ou uma linha marcada) —
   rejeitado: seria uma segunda semântica de correspondência para o mesmo conceito, exatamente o
   que a Decisão 1 do Anexo I eliminou. Capítulo é prefixo curto, não outra coisa.
3. **Expandir o Capítulo 6 nas suas posições (0601…0604)** — rejeitado: exigiria a tabela completa
   da NCM para saber quais posições existem, e inventaria códigos que o Anexo XV não escreveu.
   (A TIPI ingerida em `aliquotas_ipi_tipi` *permitiria* essa expansão — e é justamente por isso
   que a tentação está registrada aqui como rejeitada: a lista de posições do capítulo 6 mudaria a
   cada revisão da TIPI, e a lei citou o capítulo, não as posições.)

---

### Decision 5: desempate generalizado — prefixo mais longo → menor Anexo → menor item → menor sub-item

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Achado do DEFINE: sobreposição tripla no Anexo XII (itens 1.2, 1.3 e 14, código `9018.19.80`) |

**Context:** A Decisão 4 do Anexo I ordenava por `(len(prefixo), -item)` — dois critérios, feitos
para pares de itens com numeração inteira dentro de um único Anexo. Agora há três itens em conflito
(1.2, 1.3, 14), numeração composta, e quatro Anexos na mesma tabela.

**Choice:** Uma chave de ordenação de **quatro componentes**, aplicada por `max()` ao conjunto de
linhas que casaram:

```python
def _chave_especificidade(linha):
    """Mais específico primeiro: prefixo mais longo; empate → menor Anexo;
    → menor item; → menor sub-item."""
    return (len(linha.prefixo), -linha.anexo_ordem, -linha.item, -linha.sub_item)
```

Resultado nos casos reais:

| Código | Casam | Vence | Por quê |
|--------|-------|-------|---------|
| `1902.19.00` | I/15 (`19021`, 5) · I/25 (`19021900`, 8) | **I, item 25** | prefixo mais longo (regra 1, inalterada) |
| `2106.90.90` | I/4 · I/26 (ambos 8) | **I, item 4** | menor item (regra 3, inalterada) |
| `9018.19.80` | XII/1.2 · XII/1.3 · XII/14 (todos 8) | **XII, item 1.2** | menor item (1 < 14), depois menor sub-item (2 < 3) |

E a resposta lista **todos** os correspondentes, agora qualificados pelo Anexo:

```json
"itens_correspondentes": [
  {"anexo": "XII", "item": "1.2"},
  {"anexo": "XII", "item": "1.3"},
  {"anexo": "XII", "item": "14"}
]
```

**Rationale:**

1. **É a mesma regra do Anexo I, estendida — não uma regra nova.** Os dois critérios originais
   continuam sendo o 1º e o 3º; o Anexo entra antes do item porque item só é comparável dentro de
   um Anexo (todo Anexo tem um item 1), e o sub-item entra depois, porque só existe dentro de um
   item. A ordem dos componentes é a ordem da hierarquia do documento legal. Consequência: os dois
   desempates já shipados (15/25 e 4/26) continuam resolvendo **exatamente** como hoje — o que é
   testável, e é o teste que AT-002 exige.
2. **Ordem total, portanto determinística.** Não existem duas linhas distintas com o mesmo
   `(anexo, item, sub_item, prefixo)` — a `UNIQUE` da tabela garante. Sem ordem total, `9018.19.80`
   citaria ora "Eletroencefalógrafos", ora "Monitor multiparâmetros", conforme a ordem em que o
   Postgres devolveu as linhas: não-determinismo que só apareceria em produção, num campo que o
   cliente leva para uma defesa fiscal.
3. **Nenhum conflito jurídico é resolvido aqui — os três itens dão zero.** O desempate escolhe
   *qual dispositivo citar*, e por isso `itens_correspondentes` existe: o auditor que estranhar
   "item 1.2" num monitor multiparâmetros vê os três e conclui sozinho. Este é o único caso
   conhecido em que a citação vencedora é *menos* descritiva do produto que uma perdedora (o item
   14 descreve "Monitor multiparâmetros" literalmente) — o que é aceitável porque a lista completa
   está na resposta, e é preferível a inventar um critério de "descrição mais parecida", que seria
   heurística de texto num produto que promete determinismo.
4. **`-anexo_ordem` vem da coluna, não de um mapa em Python** (Decisão 3), então a regra não pode
   discordar do banco.

**Alternatives Rejected:**

1. **Manter `(len(prefixo), -item)` e ignorar `sub_item`** — rejeitado: 1.2 e 1.3 empatariam e a
   escolha voltaria a depender da ordem do `SELECT`.
2. **Comparar a grafia `"1.2"` como string** — rejeitado: `"14" < "1.2"` lexicograficamente, exatamente
   a inversão que o DEFINE identificou.
3. **Citar todos os itens empatados em `dispositivo_legal_ref`** (uma string com 3 citações) —
   rejeitado: `dispositivo_legal_ref` é a citação *da* redução aplicada, consumida como identidade
   por quem integra; a pluralidade tem campo próprio.

---

### Decision 6: "exceto" tem **três** classes, e o banco recusa a confusão entre elas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `COULD` do DEFINE (descritivo × operante); pergunta 5 do pedido de `/design` |

**Context:** O DEFINE identificou duas classes de cláusula "exceto": a **operante** (gera linha de
exclusão) e a **descritiva** (não gera). A leitura literal desta sessão encontrou uma **terceira**:
cláusulas que **não nomeiam código nenhum** ("exceto os dentários", no XII/5; "exceto partes e
acessórios", no XIII/4). São três coisas diferentes e o processo de transcrição precisa separá-las
sem depender da atenção de quem escreve a migração.

**Choice:** Uma regra mecânica de duas perguntas, aplicada a cada cláusula "exceto", **mais** uma
asserção na migração que torna o erro impossível de aplicar:

```text
A cláusula nomeia código(s) NCM?
├─ NÃO  → classe NÃO CODIFICÁVEL. Zero linhas. Vira limitação declarada
│          (a condição fica na `descricao` literal, que volta na resposta).
└─ SIM  → o código nomeado é descendente (prefixo) de alguma INCLUSÃO do MESMO item?
          ├─ SIM → classe OPERANTE.    1 linha com excecao = TRUE.
          └─ NÃO → classe DESCRITIVA.  Zero linhas — a exclusão já é fato da
                    estrutura da NCM, e uma linha aqui seria inerte.
```

A segunda pergunta **não é heurística: é a definição**. Uma exceção só tem efeito quando o código
excluído cairia dentro de uma inclusão do próprio item (a exceção é escopada ao item — Decisão 3 do
Anexo I). Se não cai, a linha nunca casaria com nada: seria ruído indistinguível de erro de
transcrição. Por isso a migração 008 termina com:

```sql
-- Exceção órfã = ou erro de transcrição, ou "exceto" DESCRITIVO virado linha.
-- Nos dois casos a migração inteira faz rollback, em vez de gravar ruído.
IF EXISTS (
    SELECT 1 FROM anexos_reducao_zero_ncm e
    WHERE e.excecao IS TRUE AND NOT EXISTS (
        SELECT 1 FROM anexos_reducao_zero_ncm i
        WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
          AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%'
    )
) THEN RAISE EXCEPTION 'exceção órfã: …';
```

**Onde a distinção vive:** é decisão de **quem escreve a migração**, não do runtime. O código de
`resolver_item` não sabe (nem precisa saber) se um "exceto" era descritivo — para ele só existem
linhas com `excecao = TRUE` ou `FALSE`. A migração 008 carrega, no cabeçalho, o **catálogo completo
das 6 cláusulas "exceto"** dos 3 Anexos com sua classe e a justificativa (ver "Catálogo das
cláusulas 'exceto'" abaixo), para que o revisor veja que as descritivas foram *consideradas e
descartadas*, não esquecidas.

**Rationale:**

1. **A asserção transforma o único erro plausível em falha ruidosa, no momento certo.** Transcrever
   os 9 códigos do "exceto" do item 1.3 do Anexo XII como exclusões é o erro natural de quem lê a
   tabela depressa; a consequência silenciosa seria… nenhuma visível em 90% dos casos (as linhas
   seriam inertes), até o dia em que uma delas colidisse com outro item. Falhar no `INSERT` custa
   um `git commit`; descobrir em produção custa uma resposta fiscal errada.
2. **A regra é uma definição, não um proxy** — então não tem falso positivo nem falso negativo. É
   raro poder dizer isso de uma verificação automática.
3. **A terceira classe precisava existir**: forçar "exceto os dentários" a virar linha exigiria
   inventar um código NCM que a lei não escreveu. Ela é declarada como limitação (mesmo tratamento
   das condições textuais do Anexo I), e o `/build` **não deve** tentar resolvê-la.
4. **O catálogo no cabeçalho é o que impede o próximo Anexo de repetir a análise do zero.** As
   posições 13 a 17 terão cláusulas "exceto" também; a regra e o formato ficam prontos.

**Nota sobre "exceto os dentários" (XII, item 5), registrada por honestidade:** há forte indício de
que a cláusula seja **inócua por estrutura da NCM** — próteses dentárias ficam na subposição
`9021.2` e o item cita `9021.3` —, mas isso **não foi verificado contra fonte primária nesta
sessão** e, por política do projeto, não é afirmado. Fica como recomendação ao `/build`: a TIPI já
ingerida (`aliquotas_ipi_tipi`, 9231 códigos) permite confirmar com um `SELECT` no
script de verificação em produção. Enquanto não confirmado, a cláusula é tratada como limitação
declarada (classe NÃO CODIFICÁVEL), que é a leitura conservadora do ponto de vista do desenho — e a
*arriscada* do ponto de vista fiscal, o que está dito em "Limitações declaradas".

**Alternatives Rejected:**

1. **Uma coluna `tipo_excecao` ('OPERANTE'|'DESCRITIVA')** — rejeitada: descritivas não viram
   linha, então a coluna teria um único valor em 100% das linhas. Dado que não varia não é dado.
2. **Transcrever tudo e deixar as inertes no banco "por fidelidade"** — rejeitada: fidelidade é da
   `descricao`, que já traz o texto integral do item, inclusive a cláusula. A tabela de prefixos é
   *operacional*: cada linha existe para casar com um código.
3. **Verificar a órfã só em teste (como faz o Anexo I)** — rejeitada aqui: o teste roda no CI, a
   migração roda no Cloud SQL. Com 4 Anexos e 151 linhas, a garantia tem de estar onde o dado
   entra. O teste **continua existindo** (agora cobrindo os 4 Anexos), como segunda rede.

---

### Decision 7: linhas de cabeçalho entram como itens sem prefixo; o contexto vem da própria chave

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Achado 4 desta sessão (item 1 do XII e item 2 do XIII são cabeçalhos sem NCM) |

**Context:** No DOU, o item 1 do Anexo XII ("Aparelhos de eletrodiagnóstico (incluídos os aparelhos
de exploração funcional e os de verificação de parâmetros fisiológicos)") e o item 2 do Anexo XIII
("CADEIRA DE RODAS E OUTROS VEÍCULOS PARA DEFICIENTES…") **não têm célula de NCM** — são
cabeçalhos dos sub-itens abaixo. E os sub-itens, sozinhos, são ininteligíveis: a `descricao` do item
2.1 do Anexo XIII é literalmente **"Sem mecanismo de propulsão"**. Devolver isso como fundamentação
legal de uma cadeira de rodas seria pior do que não devolver nada.

**Choice:** Os 2 cabeçalhos **entram na tabela de itens** (com `descricao` e
`dispositivo_legal_ref` próprios) e **não têm nenhuma linha de prefixo** — nunca casam com código
nenhum. O contexto é recuperado sem coluna nova, porque a chave já o codifica: o pai de
`(XIII, 2, 1)` é `(XIII, 2, 0)`.

```sql
LEFT JOIN anexos_reducao_zero pai
       ON pai.anexo = i.anexo AND pai.item = i.item
      AND pai.sub_item = 0    AND i.sub_item > 0
```

O resultado vira o campo `descricao_contexto` da resposta (`null` quando o item não é sub-item).

**Rationale:**

1. **Sem isso, a resposta cita uma frase sem sujeito.** `"descricao": "Sem mecanismo de propulsão"`
   com `dispositivo_legal_ref` correto é o tipo de saída que passa em qualquer teste automatizado e
   é inútil para o humano que precisa dela — que é o usuário-alvo declarado no DEFINE.
2. **Nenhuma coluna nova, nenhuma FK nova**: o `item_pai` seria informação redundante com a chave.
   Chave composta bem escolhida paga dividendos aqui.
3. **Concatenar pai + filho na `descricao`** quebraria a regra de que `descricao` é transcrição
   literal do DOU — a mesma regra que permite usar a migração como documento de auditoria.
4. **Cabeçalho sem prefixo é inofensivo e verificável**: a migração 008 assere que *todo item sem
   linha de prefixo tem ao menos um sub-item* (e vice-versa: todo sub-item tem cabeçalho). Um
   `INSERT` truncado que perdesse as linhas de prefixo de um item comum falha nessa asserção, em
   vez de virar um item que nunca casa.

**Alternatives Rejected:**

1. **Não inserir os cabeçalhos** — rejeitada: perderia a única frase que dá sentido ao item 2.1 do
   XIII, e a tabela deixaria de ser transcrição da tabela do DOU.
2. **Coluna `item_pai`/`descricao_contexto` materializada** — rejeitada pelo motivo 2 (redundância
   com a chave) e porque materializar a descrição do pai a duplicaria em N linhas, o mesmo erro que
   a Decisão 3 do Anexo I evitou ao normalizar `dispositivo_legal_ref`.

---

### Decision 8: o bloco da resposta passa a se chamar `reducao_zero`, e `item` passa a ser a grafia canônica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted — confirmado diretamente com Jonatas em 2026-07-28 (renomear sem alias, não manter `cesta_basica` depreciado) |
| **Date** | 2026-07-28 |
| **Resolve** | MUST "citando o Anexo e item exatos"; consequência inevitável da união dos 4 Anexos |

**Context:** Hoje a resposta tem `itens_detalhados[].cesta_basica` e `cesta_basica` no topo, com
`item: int`. Depois desta feature, o mesmo bloco responderá por um tomógrafo e por uma cadeira de
rodas, e o item pode ser `"1.2"`. Além disso, o estado `FORA_DO_ANEXO` **já muda de significado de
qualquer forma**: passa de "fora do Anexo I" para "fora dos 4 Anexos de alíquota zero" — a
generalização semântica é o objetivo da feature, não um efeito colateral evitável.

**Choice:** Renomear o bloco para `reducao_zero` (em `ItemDetalhado` e na resposta) e representar o
item pela **grafia canônica em string**:

| Campo | Antes | Depois |
|-------|-------|--------|
| bloco por item | `cesta_basica` | `reducao_zero` |
| bloco agregado | `cesta_basica` | `reducao_zero` |
| `anexo` | — | **novo**: `"I"` \| `"XII"` \| `"XIII"` \| `"XV"` |
| `item` | `int \| None` (1..26) | `str \| None` (`"5"`, `"1.2"`) |
| `descricao_contexto` | — | **novo** (Decisão 7) |
| `itens_correspondentes` | `list[int]` | `list[{anexo, item}]` |
| `anexos_aplicados` (resumo) | — | **novo**: `["I", "XV"]` |
| demais campos | — | inalterados, mesmos nomes e semântica |

**Sem alias de compatibilidade.** E o guard-rail que substitui o alias:

> **A alteração dos testes já existentes do Anexo I deve se limitar ao nome do bloco, ao tipo
> escalar de `item` e à forma de `itens_correspondentes`. Qualquer *valor* asserido que precise
> mudar — situação, dispositivo legal, percentual, total dispensado — é regressão, não teste
> desatualizado.**

**Rationale:**

1. **Manter o nome seria fazer a resposta mentir.** `"cesta_basica": {"situacao": "APLICADA"}` para
   um implante coclear é falso num produto cuja proposta inteira é auditabilidade — o mesmo motivo
   que obriga o rename da tabela (Decisão 1). E "manter e não popular" (o alias) exigiria carregar
   *dois* blocos com semânticas divergentes na mesma resposta, para sempre.
2. **O raio de alcance é conhecido e pequeno**, porque foi medido nesta sessão, não estimado:
   `grep` por `cesta_basica`/`itens_correspondentes` fora de `.claude/sdd` encontra **apenas** o
   próprio código, 2 arquivos de teste, o `deploy.yml` (2 caminhos `jq`) e o `migrar_banco.yml` (1
   input). O `frontend/` **não tipa nem lê** o bloco (só `resumo_financeiro` e `itens_detalhados`).
   Não há cliente externo conhecido; o campo tem um dia de vida.
3. **O MUST do DEFINE é sobre resolução, não sobre serialização.** A constraint escrita lá é: "os
   26 itens do Anexo I devem continuar **resolvendo exatamente como resolvem hoje** (AT-002)". O
   guard-rail acima é a versão executável dessa frase — mais forte, na prática, do que um alias:
   um alias esconderia uma mudança de valor; o guard-rail a expõe como diff.
4. **`item` como string é a citação que a lei escreve.** A alternativa (`item: int` + `sub_item:
   int` + um terceiro campo com a grafia) mantém compatibilidade binária ao custo de três campos
   para um conceito, e obriga todo cliente a reconstruir `"1.2"` para exibir. A chave estruturada
   continua existindo — no banco, onde ela serve para ordenar (Decisão 2).
5. **`SituacaoReducaoZero` mantém os 6 valores literais** (`APLICADA`, `EXCLUIDA_EXPRESSAMENTE`,
   `FORA_DO_ANEXO`, `NCM_NAO_RECONHECIDO`, `CONSULTA_INDISPONIVEL`, `NAO_APLICAVEL`): a máquina de
   estados da Decisão 7 do Anexo I estava certa e não muda — só o universo a que `FORA_DO_ANEXO` se
   refere, que agora são os 4 Anexos.

**Alternatives Rejected:**

1. **Manter `cesta_basica` como alias depreciado, populado só quando `anexo == 'I'`** — rejeitada
   pelo motivo 1 e pelo precedente da Decisão 12 do Anexo I ("manter algo morto cuja justificativa
   foi refutada é pior que não ter — alguém o reintroduziria citando um raciocínio que não vale
   mais"). Fica registrado que ela era viável e barata (~15 linhas), e que a escolha foi por
   honestidade de contrato, não por economia.
2. **Manter o nome `cesta_basica`** — rejeitada pelo motivo 1.
3. **`item: int` + `sub_item: int | None` + `item_ref: str`** — rejeitada pelo motivo 4.

---

### Decision 9: `motor_calculo/` não é tocado — nem uma linha

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | MUST do DEFINE ("nenhuma função de cálculo nova"); achados 2 e 3 desta sessão |

**Context:** O DEFINE exige que `aplicar_reducao_a_zero` seja reutilizada sem alteração de
assinatura. Restavam duas dúvidas que só a fonte primária resolvia: (a) o Anexo XV, cujo cabeçalho
fala em "redução de 100%", exigiria uma função de percentual? (b) `fonte_legal_reducoes`, semeado
por fase em `tabela_aliquotas.py`, cita a regra de transição correta para os Anexos novos?

**Choice:** Nenhum arquivo de `motor_calculo/` entra no manifesto. As duas dúvidas se resolvem no
texto:

- **(a)** O art. 148 diz "ficam reduzidas a **zero**" — o "100%" está no cabeçalho do Anexo, não no
  dispositivo. `aplicar_reducao_a_zero` é literalmente a função certa (achado 2).
- **(b)** O seed já semeado é genérico e **não cita o art. 125**: para 2026, "art. 348, III, 'a' —
  as alíquotas do IBS e da CBS previstas nos arts. 343 e 346 são aplicadas com a respectiva redução
  no caso das operações sujeitas a alíquota reduzida"; para 2027-2028, arts. 344 § único, I e 347,
  § 1º, I. Como os arts. 144/145/148 estão **dentro do Título IV** (achado 3), a subsunção a
  "regimes diferenciados de tributação" é literal — mais direta, inclusive, do que era para o
  próprio Anexo I.

Único ajuste em `motor_calculo/`: **dois comentários** em `regras_fiscais.py` que citam
"Cesta Básica, art. 125" e "`api/cesta_basica.py`" como exemplo — passam a citar os 4 Anexos e o
módulo renomeado. Comentário desatualizado que aponta para arquivo inexistente é armadilha para o
próximo leitor; não é mudança de comportamento.

**Rationale:**

1. **A garantia "`motor_calculo` roda sem infraestrutura" é a mais valiosa do projeto** e é mantida
   por construção: a feature inteira vive em `db/` e `api/`.
2. **A verificação de (a) era obrigatória.** Aceitar "100% ≈ zero" por equivalência aritmética
   funcionaria hoje e criaria um precedente errado para a posição 13, onde 60% **não** é zero e a
   diferença é toda a feature.
3. **Zero mudança em `tabela_aliquotas.py` significa zero risco de regressão** em
   `tests/test_tabela_aliquotas.py` e `tests/test_engine.py`.

---

### Decision 10: o seed mora na migração, e a migração recusa transcrição inconsistente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Risco central da feature: 56 linhas transcritas à mão |

**Context:** Mesma situação da Decisão 11 do Anexo I (dado de lista fechada, transcrito uma vez,
que nunca chega duas vezes), com o dobro do volume e dois tipos de armadilha novos (sub-itens e
"exceto" descritivo).

**Choice:** `INSERT` dentro da migração 008, com URL e data de acesso no cabeçalho, mais um bloco
`DO $$ … $$` final que **assere o resultado inteiro** e faz rollback de tudo se algo não bater:

| Asserção | O que pega |
|----------|------------|
| Contagem por Anexo: itens `I:26 · XII:20 · XIII:8 · XV:6` | `INSERT` truncado; item esquecido |
| Contagem por Anexo: prefixos `I:95 · XII:24 · XIII:7 · XV:25` | idem |
| Inclusões/exceções: `127 / 24` no total | exceção transcrita como inclusão (e vice-versa) |
| Toda exceção desce de uma inclusão do mesmo item | "exceto" descritivo virado linha (Decisão 6) |
| Todo item sem prefixo tem ≥1 sub-item; todo sub-item tem cabeçalho | linha de prefixo perdida; cabeçalho esquecido |
| Comprimentos de prefixo presentes ⊆ `{2,4,5,6,7,8}` | (redundante com a CHECK — de propósito: prova que a CHECK está ativa) |

Somadas às constraints declarativas — `prefixo_bate_com_texto` (herdada), `prefixo_comprimento_valido`
(Decisão 4), `anexo_conhecido` e `dispositivo_cita_o_proprio_item` (Decisão 3) — o resultado é que
**nenhum dígito desta feature é digitado duas vezes sem que o banco compare as duas grafias**.

**Rationale:**

1. **A migração é o documento de auditoria** (argumento do `db/migrador.py`, "não esconde o SQL de
   quem precisa auditá-lo"). Com o catálogo de "exceto" e a URL no cabeçalho, um fiscal confere os
   3 Anexos lendo um arquivo `.sql`.
2. **Asserção dentro da transação da migração > teste no CI**, porque o CI roda contra um Postgres
   efêmero e a migração roda contra o Cloud SQL. As duas existem; só uma roda onde o dado importa.
3. **Contagens são teste de truncamento**, e por Anexo em vez de global para que a falha diga
   *onde*.

**Alternatives Rejected:** as mesmas três da Decisão 11 do Anexo I (script de ingestão, scraper,
constraints só em teste), pelos mesmos motivos — não repetidas aqui.

---

### Decision 11: a prova contra o Cloud SQL real cobre os **três mecanismos novos**, não só as contagens

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Modo de falha silencioso herdado (grant/seed ausente ⇒ resposta idêntica à de antes) |

**Context:** Pela degradação da Decisão 8 do Anexo I, um `GRANT` faltando ou um seed truncado não
produzem erro: produzem `CONSULTA_INDISPONIVEL` e a alíquota geral — **exatamente a resposta de
antes da feature**. A feature "funciona" (200, verde) sem fazer nada. Isso já era verdade para o
Anexo I; agora há três mecanismos novos que podem falhar sozinhos, sem afetar o Anexo I: prefixo de
2 dígitos, exceção operante nos Anexos novos e desempate composto.

**Choice:** `scripts/verificar_reducao_zero_producao.py` (renomeado de
`verificar_cesta_basica_producao.py`), rodando com o papel **`taxreformai_app`** via
`migrar_banco.yml` (input renomeado para `verificar_reducao_zero`), com 7 casos — os 3 herdados,
que provam a não-regressão, e 4 novos, um por mecanismo:

| Código | Espera | Prova |
|--------|--------|-------|
| `04051000` | APLICADA · I/5 | não-regressão (herdado) |
| `02074300` | EXCLUIDA_EXPRESSAMENTE · I/19 | exceção do Anexo I (herdado) |
| `09012100` | APLICADA · I/8 | prefixo de 4 (herdado) |
| `87131000` | APLICADA · XIII/2.1 · `descricao_contexto` não-nula | Anexo novo + sub-item + Decisão 7 |
| `90181980` | APLICADA · XII/1.2 · 3 correspondentes | desempate triplo (Decisão 5) |
| `90213991` | EXCLUIDA_EXPRESSAMENTE · XII/5 | exceção operante nos Anexos novos |
| `06031100` | APLICADA · XV/4 · `ncm_correspondido == "06"` | **prefixo de 2 dígitos** (Decisão 4) |

Mais uma **terceira chamada** no smoke test do `deploy.yml`, com payload próprio de
`ncm: "06031100"`, exigindo `reducao_zero.total_cbs_dispensado != null` e
`itens_detalhados[0].aliquotas_aplicadas.cbs_percentual == 0`.

**Rationale:**

1. **O script exercita o caminho de produção**, não um `SELECT` parecido: chama
   `buscar_reducao_zero_por_prefixo` + `resolver_item`, os mesmos que `/simulate` chama.
2. **A terceira chamada de smoke tem payload separado, pelo mesmo motivo da Decisão 13 do Anexo I**:
   acrescentar um item ao payload existente faria `total_ipi` virar `null` se `06031100` não
   estiver na TIPI ingerida, reprovando o deploy por um motivo alheio à mudança. E é justamente por
   `06031100` **não** precisar existir na TIPI que ele serve: a redução a zero por capítulo não
   depende do cadastro da TIPI, e a asserção nova não menciona IPI.
3. **O caso do capítulo é o único que pode falhar sozinho de forma invisível**: se
   `_COMPRIMENTOS_PREFIXO` for atualizado e a CHECK não (ou vice-versa), tudo o mais continua verde.

---

### Decision 12: a checagem de overlap entre Anexos é um teste SQL, não um script — e é exata

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | `SHOULD` do DEFINE; `A-002` |

**Context:** O DEFINE verificou manualmente que não há overlap de NCM entre os 4 Anexos e
recomendou automatizar, "dado que o volume total (151 linhas) começa a tornar inspeção manual menos
confiável".

**Choice:** Um teste em `tests/test_reducao_zero_db.py` (Postgres real do CI) que decide a questão
**sem precisar da tabela da NCM**: dois Anexos compartilham um código concreto de 8 dígitos se, e
somente se, um prefixo de inclusão de um é prefixo do outro.

```sql
SELECT a.anexo, a.prefixo, b.anexo, b.prefixo
FROM anexos_reducao_zero_ncm a
JOIN anexos_reducao_zero_ncm b
  ON a.anexo < b.anexo
 AND (b.prefixo LIKE a.prefixo || '%' OR a.prefixo LIKE b.prefixo || '%')
WHERE a.excecao IS FALSE AND b.excecao IS FALSE;
```

Espera-se conjunto vazio. **Teste, não asserção de migração**: overlap entre Anexos não é ilegal
(a lei pode criar um), e o desempate da Decisão 5 já o trata de forma determinística — o teste
existe para tornar o fato **visível** quando mudar, não para proibi-lo.

**Rationale:**

1. **A verificação manual do DEFINE passou raspando.** O Anexo I tem o item 7 (feijões) nos códigos
   `0713.33.19`/`0713.33.29`/`0713.33.99`/`0713.35.90` — **capítulo 07**, o mesmo capítulo do item
   2 do Anexo XV (produtos hortícolas). Não há colisão porque o Anexo XV lista `07.01`–`07.10` e
   `07.14`, e `0713` não está em nenhuma das duas listas. A conclusão do DEFINE está certa, mas a
   margem foi de **uma posição NCM** — exatamente o tipo de coisa que a leitura manual erra na
   próxima vez.
2. **A equivalência "prefixo contém prefixo ⇔ existe código comum" é exata**, então o teste não
   precisa da NCM completa nem inventa códigos.
3. **Filtrar `a.anexo < b.anexo` isola o cross-Anexo**: a sobreposição *intra*-Anexo XII (1.2/1.3/14)
   é esperada e não deve fazer o teste falhar.

---

### Decision 13: ordem de aplicação — migrar antes de deployar, com a janela declarada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |
| **Resolve** | Consequência operacional do rename (Decisão 1) |

**Context:** A API em produção consulta `cesta_basica_anexo_i_ncm`. A migração 007 renomeia a
tabela. Entre a migração e o deploy da nova revisão existe uma janela em que o código antigo
consulta um nome que não existe mais (ou, na ordem inversa, o código novo consulta um nome que
ainda não existe).

**Choice:** Ordem **007/008 → deploy**, com a janela declarada e aceita. Durante ela, a API antiga
recebe exceção no `SELECT`, cai no `except` de `consultar_com_seguranca`, devolve
`CONSULTA_INDISPONIVEL` e aplica a **alíquota geral da fase** — 200, com `logger.exception` no
Cloud Logging e a advertência no corpo. Nenhum 5xx, nenhum cálculo errado *para menos*.

**Rationale:**

1. **A janela existe nas duas ordens** (o código novo também não acha o nome novo antes da
   migração), então a escolha é sobre *qual degradação*, não sobre evitá-la. Migrar primeiro é
   melhor porque `migrar_banco.yml` já roda `verificar_reducao_zero`, que prova o estado final do
   banco **antes** de qualquer tráfego tocar o código novo.
2. **A degradação é a mesma já projetada e testada** (Decisão 8 do Anexo I) e erra na direção
   conservadora: tributo maior que o devido, nunca menor.
3. **Os dois workflows são `workflow_dispatch`**, disparados manualmente e em sequência por uma
   pessoa na mesma sessão — a janela é de minutos, não de dias, e não há deploy automático que
   possa inverter a ordem.

**Alternatives Rejected:**

1. **`CREATE VIEW cesta_basica_anexo_i(_ncm)` como ponte, dropada numa migração 009** — rejeitada:
   elimina uma janela de minutos ao custo de uma view que precisa ser lembrada e removida, e de uma
   migração a mais no histórico. Fica registrada como a saída correta caso o projeto passe a ter
   deploy contínuo ou SLA de disponibilidade — o que hoje não tem.
2. **Não renomear** — ver Decisão 1, motivo 4.

---

## Dados — os 3 Anexos transcritos (fonte primária, 2026-07-28)

> Transcrição literal das três publicações citadas na seção de verificação. É **esta** tabela que o
> `/build` copia para a migração 008 — não a versão resumida do DEFINE, que difere em três pontos
> (item 7 do XII, cabeçalhos, redação de vários itens).
>
> Notação: `texto_ncm` (grafia do DOU) → `prefixo` (dígitos). Linhas de exceção marcadas com **✗**.

### Anexo XII — Dispositivos médicos · art. 144, I

`dispositivo_legal_ref`: `LCP 214/2025, art. 144, Anexo XII, item N`

| item | sub | `descricao` (literal) | `texto_ncm` → `prefixo` |
|------|-----|------------------------|--------------------------|
| 1 | 0 | Aparelhos de eletrodiagnóstico (incluídos os aparelhos de exploração funcional e os de verificação de parâmetros fisiológicos) | *(cabeçalho — nenhuma linha)* |
| 1 | 1 | Eletrocardiógrafos | `9018.11.00`→90181100 |
| 1 | 2 | Eletroencefalógrafos | `9018.19.80`→90181980 |
| 1 | 3 | Aparelhos de eletrodiagnóstico, exceto os produtos classificados nos códigos 9018.11.00, 9018.12.10, 9018.12.90, 9018.13.00, 9018.14.10, 9018.14.20, 9018.14.90, 9018.19.10 e 9018.19.20 | `9018.19.80`→90181980 |
| 2 | 0 | Aparelhos de raios ultravioleta ou infravermelhos | `9018.20`→901820 |
| 3 | 0 | Artigos e aparelhos ortopédicos | `9021.10.10`→90211010 |
| 4 | 0 | Artigos e aparelhos para fraturas | `9021.10.20`→90211020 |
| 5 | 0 | Artigos e aparelhos de prótese, exceto os dentários e os produtos classificados nos códigos 9021.39.91 e 9021.39.99 | `9021.3`→90213 · ✗`9021.39.91`→90213991 · ✗`9021.39.99`→90213999 |
| 6 | 0 | Tomógrafo computadorizado | `9022.12.00`→90221200 |
| 7 | 0 | Aparelhos de raio X, móveis, exceto os produtos classificados no código 9022.19.91 | `9022.13`→902213 · `9022.14`→902214 · `9022.19`→902219 · ✗`9022.19.91`→90221991 |
| 8 | 0 | Aparelho de radiocobalto (bomba de cobalto) | `9022.21.10`→90222110 |
| 9 | 0 | Aparelho de crioterapia | `9018.90.99`→90189099 |
| 10 | 0 | Aparelho de gamaterapia | `9022.21.20`→90222120 |
| 11 | 0 | Aparelhos que utilizem radiações alfa, beta, gama ou outras radiações ionizantes, para usos médicos, cirúrgicos, odontológicos ou veterinários, incluídos os aparelhos de radiofotografia ou de radioterapia, exceto os produtos classificados nos códigos 9022.21.10 e 9022.21.20 | `9022.21.90`→90222190 |
| 12 | 0 | Densímetros, areômetros, pesa-líquidos e instrumentos flutuantes semelhantes, termômetros, pirômetros, barômetros, higrômetros e psicômetros, registradores ou não, mesmo combinados entre si | `90.25`→9025 |
| 13 | 0 | Respirador | `9019.20.40`→90192040 |
| 14 | 0 | Monitor multiparâmetros | `9018.19.80`→90181980 |
| 15 | 0 | Bomba de infusão | `9018.90.10`→90189010 |
| 16 | 0 | Aparelhos de diagnóstico por visualização de ressonância magnética | `9018.13.00`→90181300 |
| 17 | 0 | Aparelhos de ultrassom | `9018.12`→901812 |

**Contagem:** 20 itens (17 numerados, dos quais o 1 é cabeçalho, + 3 sub-itens) · **24 linhas** =
21 inclusões + 3 exceções.

### Anexo XIII — Dispositivos de acessibilidade · art. 145, I

`dispositivo_legal_ref`: `LCP 214/2025, art. 145, Anexo XIII, item N`

| item | sub | `descricao` (literal) | `texto_ncm` → `prefixo` |
|------|-----|------------------------|--------------------------|
| 1 | 0 | Barra de apoio para pessoa com deficiência física | `8302.41.00`→83024100 |
| 2 | 0 | CADEIRA DE RODAS E OUTROS VEÍCULOS PARA DEFICIENTES, MESMO COM MOTOR OU OUTRO MECANISMO DE PROPULSÃO | *(cabeçalho — nenhuma linha)* |
| 2 | 1 | Sem mecanismo de propulsão | `8713.10.00`→87131000 |
| 2 | 2 | Cadeiras de rodas com motor ou outro mecanismo de propulsão e outros veículos para pessoas com incapacidade, mesmo com motor ou outro mecanismo de propulsão | `8713.90.00`→87139000 |
| 3 | 0 | Partes e acessórios destinados exclusivamente a aplicação em cadeiras de rodas ou em outros veículos para deficientes | `8714.20.00`→87142000 |
| 4 | 0 | Aparelhos para facilitar a audição dos surdos, exceto partes e acessórios | `9021.40.00`→90214000 |
| 5 | 0 | Partes e acessórios de aparelhos para facilitar a audição dos surdos | `9021.90.92`→90219092 |
| 6 | 0 | Implantes cocleares | `9021.90.19`→90219019 |

**Contagem:** 8 itens (6 numerados, dos quais o 2 é cabeçalho, + 2 sub-itens) · **7 linhas**, todas
inclusão exata de 8 dígitos, nenhuma exceção. O Anexo mais simples dos três.

### Anexo XV — Produtos hortícolas, frutas e ovos · art. 148

`dispositivo_legal_ref`: `LCP 214/2025, art. 148, Anexo XV, item N`

> A tabela do DOU tem **2 colunas** (ITEM · DESCRIÇÃO DO PRODUTO): os códigos vêm embutidos na
> prosa. `texto_ncm` recorta a grafia do código de dentro da frase — exceto no item 4, onde o DOU
> não escreve código (ver Decisão 4, motivo 4).

| item | `descricao` (literal) | `texto_ncm` → `prefixo` |
|------|------------------------|--------------------------|
| 1 | Ovos da subposição 0407.2 da NCM/SH | `0407.2`→04072 |
| 2 | Produtos hortícolas das posições 07.01, 07.02.00.00, 07.03, 07.04, 07.05, 07.06, 0707.00.00, 07.08, 07.09 e 07.10, exceto os cogumelos e trufas classificados na subposição 0709.5 e no código 0710.80.00 da NCM/SH | `07.01`→0701 · `07.02.00.00`→07020000 · `07.03`→0703 · `07.04`→0704 · `07.05`→0705 · `07.06`→0706 · `0707.00.00`→07070000 · `07.08`→0708 · `07.09`→0709 · `07.10`→0710 · ✗`0709.5`→07095 · ✗`0710.80.00`→07108000 |
| 3 | Frutas frescas ou refrigeradas e frutas congeladas sem adição de açúcar ou de outros edulcorantes classificadas nas posições 08.03, 08.04, 08.05, 08.06, 08.07, 08.08, 08.09, 08.10 e 08.11 da NCM/SH | `08.03`→0803 · `08.04`→0804 · `08.05`→0805 · `08.06`→0806 · `08.07`→0807 · `08.08`→0808 · `08.09`→0809 · `08.10`→0810 · `08.11`→0811 |
| 4 | Plantas e produtos de floricultura relativos à horticultura e cultivados para fins alimentares, ornamentais ou medicinais classificados no Capítulo 6 da NCM/SH | `06`→06 **(2 dígitos)** |
| 5 | Raízes e tubérculos da posição 07.14 da NCM/SH | `07.14`→0714 |
| 6 | Cocos da subposição 0801.1 da NCM/SH | `0801.1`→08011 |

**Contagem:** 6 itens · **25 linhas** = 23 inclusões + 2 exceções.

**Nota do art. 148, parágrafo único** (não gera linha, mas explica a amplitude): os produtos "podem
apresentar-se inteiros, cortados em fatias ou em pedaços, ralados, torneados, descascados,
desfolhados, lavados, higienizados, embalados, frescos, resfriados ou congelados, mesmo que
misturados" — ou seja, a lei **amplia** deliberadamente, o que reforça a leitura literal dos
prefixos.

### Contagens de fechamento (asserções obrigatórias do `/build`)

| Anexo | Itens | Prefixos | Inclusões | Exceções |
|-------|-------|----------|-----------|----------|
| I (existente, intocado) | 26 | 95 | 76 | 19 |
| XII | 20 | 24 | 21 | 3 |
| XIII | 8 | 7 | 7 | 0 |
| XV | 6 | 25 | 23 | 2 |
| **Total** | **60** | **151** | **127** | **24** |

Comprimentos de prefixo presentes = `{2, 4, 5, 6, 7, 8}` (o 7 só existe no Anexo I, `0210.99.1`; o
2 só no Anexo XV, item 4). Itens sem linha de prefixo = exatamente 2 (XII/1 e XIII/2), ambos com
sub-itens. Prefixo compartilhado entre itens distintos: `21069090` (I/4 e I/26) e `90181980`
(XII/1.2, XII/1.3 e XII/14) — nenhum entre Anexos diferentes.

---

## Catálogo das cláusulas "exceto" (vai no cabeçalho da migração 008)

| Anexo/item | Cláusula | Classe | Linhas |
|------------|----------|--------|--------|
| XII / 1.3 | "exceto os produtos classificados nos códigos 9018.11.00, 9018.12.10, 9018.12.90, 9018.13.00, 9018.14.10, 9018.14.20, 9018.14.90, 9018.19.10 e 9018.19.20" | **DESCRITIVA** — nenhum dos 9 códigos desce de `90181980`, a única inclusão do item | 0 |
| XII / 5 | "exceto os dentários" | **NÃO CODIFICÁVEL** — nenhum código citado; vira limitação declarada | 0 |
| XII / 5 | "e os produtos classificados nos códigos 9021.39.91 e 9021.39.99" | **OPERANTE** — os dois descem de `90213` | 2 |
| XII / 7 | "exceto os produtos classificados no código 9022.19.91" | **OPERANTE** — desce de `902219` | 1 |
| XII / 11 | "exceto os produtos classificados nos códigos 9022.21.10 e 9022.21.20" | **DESCRITIVA** — nenhum desce de `90222190` (são os itens 8 e 10) | 0 |
| XIII / 4 | "exceto partes e acessórios" | **NÃO CODIFICÁVEL** — a exclusão é realizada pela própria NCM: partes e acessórios têm item próprio (XIII/5, `9021.90.92`) | 0 |
| XV / 2 | "exceto os cogumelos e trufas classificados na subposição 0709.5 e no código 0710.80.00" | **OPERANTE** — descem de `0709` e `0710` | 2 |

**Total: 5 linhas de exceção** — exatamente o que o DEFINE previu, chegando lá por uma regra
verificável em vez de por contagem.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/007_generalizar_anexos_reducao_zero.sql` | Create | Rename das 2 tabelas; `anexo`/`anexo_ordem`/`sub_item`; PK/FK/UNIQUE compostas; CHECKs novas (Decisões 2, 3, 4); prova de que o Anexo I sobreviveu (26/95); re-`GRANT` | @database-reviewer | — |
| 2 | `db/migrations/008_anexos_reducao_zero_xii_xiii_xv.sql` | Create | Catálogo de "exceto" + seed de 34 itens/56 prefixos + bloco de asserções (Decisões 6, 10) | @database-reviewer | 1 |
| 3 | `db/repositorio.py` | Modify | `PrefixoReducaoZero` (+`anexo`, `anexo_ordem`, `sub_item`, `descricao_contexto`) e `buscar_reducao_zero_por_prefixo` (+`LEFT JOIN` do pai); docstring de `buscar_ipi_por_ncm` deixa de citar `cesta_basica_anexo_i` | @database-reviewer | 1, 2 |
| 4 | `api/ncm.py` | Modify | `_COMPRIMENTOS_PREFIXO = (2,4,5,6,7,8)` + comentário do acoplamento com a CHECK (Decisão 4) | @python-developer | 1 |
| 5 | `api/reducao_zero.py` | Create (`git mv` de `api/cesta_basica.py`) | `SituacaoReducaoZero`, `ConsultaReducaoZero`, `ResolucaoReducaoZero`, `formatar_item`, `_chave_especificidade`, `resolver_item` agrupando por `(anexo, item, sub_item)` | @python-developer | 3, 4 |
| 6 | `api/schemas_simulate.py` | Modify | `ReducaoZeroItem`, `ItemCorrespondente`, `ReducaoZeroResumo` no lugar de `CestaBasicaItem`/`CestaBasicaResumo`; `ItemDetalhado.reducao_zero`; `fonte_legal` reescrita para os 4 Anexos | @python-developer | 5 |
| 7 | `api/routers/simulate.py` | Modify | Renomeações; `anexos_aplicados`; advertência e parecer do audit log citando os 4 Anexos | @python-developer | 5, 6 |
| 8 | `motor_calculo/regras_fiscais.py` | Modify | **Só comentários** — deixam de citar "art. 125" como exemplo único e `api/cesta_basica.py` (arquivo que não existirá) | @python-developer | 5 |
| 9 | `tests/test_reducao_zero_resolucao.py` | Modify (`git mv` de `test_cesta_basica_resolucao.py`) | Unit puro: prefixo de 2 dígitos, desempate triplo com sub-item, `formatar_item`, exceções dos Anexos novos; **assertions do Anexo I inalteradas em valor** | @test-generator | 4, 5 |
| 10 | `tests/test_api_simulate_reducao_zero.py` | Modify (`git mv` de `test_api_simulate_cesta_basica.py`) | AT-001..AT-010 via `TestClient` + fake pool; 1 query por request; pool `None`/pool que explode → 200 | @test-generator | 7 |
| 11 | `tests/test_reducao_zero_db.py` | Modify (`git mv` de `test_cesta_basica_db.py`) | Postgres real: contagens por Anexo, CHECKs novas recusando linha inválida, exceção órfã, cabeçalho×sub-item, **overlap entre Anexos** (Decisão 12), lookup com `descricao_contexto` | @database-reviewer | 1, 2, 3 |
| 12 | `scripts/verificar_reducao_zero_producao.py` | Modify (`git mv` de `verificar_cesta_basica_producao.py`) | 7 casos com o papel `taxreformai_app` contra o Cloud SQL real (Decisão 11) | @gcp-data-architect | 3, 5 |
| 13 | `.github/workflows/migrar_banco.yml` | Modify | Input `verificar_cesta_basica` → `verificar_reducao_zero`; passo aponta para o script renomeado | @gcp-data-architect | 12 |
| 14 | `.github/workflows/deploy.yml` | Modify | Caminhos `jq` (`.cesta_basica` → `.reducao_zero`) + **terceira** chamada de smoke test com `06031100` (Decisão 11) | @gcp-data-architect | 7 |
| 15 | `CLAUDE.md` | Modify | Tabela de features, estrutura (`db/migrations`, `api/reducao_zero.py`), nomes das tabelas, arquivos-chave | @python-developer | 1-14 |

**Total: 15 arquivos** (2 novos, 6 renomeados-e-modificados, 7 modificados). Nenhum arquivo novo em
`motor_calculo/` — e nenhum arquivo *deletado* de verdade: os 6 renames são `git mv`, para o
histórico seguir os arquivos.

**Fora do manifesto, deliberadamente:**

- `frontend/` — não tipa nem lê o bloco (verificado por `grep` nesta sessão); todos os campos
  continuam aditivos do ponto de vista dele.
- `motor_calculo/reducoes.py`, `engine.py`, `tabela_aliquotas.py` — Decisão 9.
- `db/migrations/005_*.sql` e `006_*.sql` — migrações aplicadas são histórico e não se editam
  (a 005 seguirá descrevendo `cesta_basica_anexo_i` com a CHECK `{4,8}`; é o registro correto do
  que foi aplicado naquele dia).
- `contexto.md` — blueprint é registro de intenção (mesma decisão do Anexo I).
- `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` — atualizado no `/ship`, junto com o status; **o achado
  do art. 144, II / art. 145, II (Anexos IV e V com zero condicionado ao comprador) deve entrar
  lá**, porque muda a premissa da posição 13.

---

## Agent Assignment Rationale

| Agent | Files | Why This Agent |
|-------|-------|-----------------|
| @database-reviewer | 1, 2, 3, 11 | Troca de chave primária com FK composta, `ALTER` que preserva dados e privilégios, CHECKs não triviais e asserções em `DO $$` — a parte mais arriscada da feature é SQL |
| @python-developer | 4-8, 15 | Resolução pura, schemas Pydantic, router e a disciplina de "renomear sem mudar valor" |
| @test-generator | 9, 10 | AT-001..AT-010 com fakes, incluindo o falso positivo de prefixo e o guard-rail de não-regressão do Anexo I |
| @gcp-data-architect | 12, 13, 14 | Verificação contra Cloud SQL/Cloud Run reais e edição dos dois workflows |
| @security-reviewer | (revisão de 1, 2, 3) | Confirmar que a ausência de RLS segue correta (dado legal público), que o `LIKE` construído por concatenação nas asserções não é injeção (roda só dentro da migração, sobre dados da própria tabela) e que nada do payload do cliente chega concatenado ao SQL |
| @code-reviewer | (revisão final) | Como em toda feature — com atenção especial ao diff dos testes do Anexo I (Decisão 8) |

---

## Code Patterns

### Pattern 1: generalização do schema (`007_generalizar_anexos_reducao_zero.sql`)

```sql
-- Generaliza o schema do Anexo I para os 4 Anexos de REDUÇÃO A ZERO da
-- LCP 214/2025: I (art. 125), XII (art. 144), XIII (art. 145) e XV (art. 148).
--
-- Nada de dado é reescrito aqui: as 26 linhas de item e as 95 de prefixo do
-- Anexo I ganham colunas com DEFAULT que é verdade sobre elas, e os defaults
-- caem em seguida para não valerem sobre as próximas. O seed dos 3 Anexos
-- novos é a migração 008 — esta migração só muda a FORMA.
--
-- ALTER TABLE ... RENAME preserva dados, índices e PRIVILÉGIOS; o GRANT do
-- final é redundante de propósito (custo zero, torna a migração autocontida).

ALTER TABLE cesta_basica_anexo_i     RENAME TO anexos_reducao_zero;
ALTER TABLE cesta_basica_anexo_i_ncm RENAME TO anexos_reducao_zero_ncm;
ALTER INDEX idx_cesta_basica_prefixo RENAME TO idx_anexos_reducao_zero_prefixo;

-- 1) Colunas novas. 'I'/1/0 descrevem o conteúdo atual, não uma regra futura.
ALTER TABLE anexos_reducao_zero
    ADD COLUMN anexo       VARCHAR(4) NOT NULL DEFAULT 'I',
    ADD COLUMN anexo_ordem SMALLINT   NOT NULL DEFAULT 1,
    ADD COLUMN sub_item    SMALLINT   NOT NULL DEFAULT 0;
ALTER TABLE anexos_reducao_zero_ncm
    ADD COLUMN anexo    VARCHAR(4) NOT NULL DEFAULT 'I',
    ADD COLUMN sub_item SMALLINT   NOT NULL DEFAULT 0;

ALTER TABLE anexos_reducao_zero
    ALTER COLUMN anexo       DROP DEFAULT,
    ALTER COLUMN anexo_ordem DROP DEFAULT;
ALTER TABLE anexos_reducao_zero_ncm
    ALTER COLUMN anexo DROP DEFAULT;
-- sub_item MANTÉM o default 0: "item sem sub-item" é regra geral da tabela,
-- não um fato sobre o Anexo I.

-- 2) Chave. Os nomes abaixo são os que o Postgres gerou na migração 005
--    (tabela_pkey / tabela_coluna_fkey / tabela_colunas_key) e sobrevivem ao
--    RENAME da tabela — constraint não é renomeada junto.
ALTER TABLE anexos_reducao_zero_ncm
    DROP CONSTRAINT cesta_basica_anexo_i_ncm_item_fkey,
    DROP CONSTRAINT cesta_basica_anexo_i_ncm_item_prefixo_excecao_key;
ALTER TABLE anexos_reducao_zero
    DROP CONSTRAINT cesta_basica_anexo_i_pkey,
    DROP CONSTRAINT cesta_basica_anexo_i_item_check;   -- era "item BETWEEN 1 AND 26"

ALTER TABLE anexos_reducao_zero
    ADD PRIMARY KEY (anexo, item, sub_item),
    ADD CONSTRAINT item_positivo     CHECK (item >= 1),
    ADD CONSTRAINT sub_item_positivo CHECK (sub_item >= 0),
    -- O ordinal mora ao lado do rótulo: nenhum mapa romano→número em Python.
    ADD CONSTRAINT anexo_conhecido CHECK (
        (anexo, anexo_ordem) IN (('I', 1), ('XII', 12), ('XIII', 13), ('XV', 15))
    ),
    -- A citação legal precisa terminar com o Anexo e o item da PRÓPRIA chave:
    -- transcrever "item 13" numa linha cujo item é 14 falha no INSERT.
    ADD CONSTRAINT dispositivo_cita_o_proprio_item CHECK (
        dispositivo_legal_ref LIKE '%Anexo ' || anexo || ', item '
            || CASE WHEN sub_item = 0 THEN item::text
                    ELSE item::text || '.' || sub_item::text END
    );

ALTER TABLE anexos_reducao_zero_ncm
    ADD FOREIGN KEY (anexo, item, sub_item)
        REFERENCES anexos_reducao_zero (anexo, item, sub_item) ON DELETE CASCADE,
    ADD UNIQUE (anexo, item, sub_item, prefixo, excecao);
-- sub_item é NOT NULL porque uma FK MATCH SIMPLE com coluna NULL é satisfeita
-- TRIVIALMENTE — seria integridade referencial desligada sem erro nenhum.

-- 3) Comprimento de prefixo: passa a aceitar CAPÍTULO (2 dígitos), exigido pelo
--    Anexo XV, item 4 ("Capítulo 6"). Lista, não intervalo: 3 dígitos não é
--    nível da NCM/SH e nunca casaria com nada (falso negativo mudo).
--    Espelha api/ncm.py::_COMPRIMENTOS_PREFIXO — os dois mudam JUNTOS.
ALTER TABLE anexos_reducao_zero_ncm
    DROP CONSTRAINT prefixo_comprimento_valido,
    ADD  CONSTRAINT prefixo_comprimento_valido
         CHECK (prefixo ~ '^[0-9]+$' AND length(prefixo) IN (2, 4, 5, 6, 7, 8));

CREATE INDEX IF NOT EXISTS idx_anexos_reducao_zero_ncm_item
    ON anexos_reducao_zero_ncm (anexo, item, sub_item);

-- 4) O Anexo I atravessou intacto? (MUST "zero regressão" do DEFINE, provado
--    pela própria migração, não só por teste.)
DO $$
DECLARE itens int; prefixos int;
BEGIN
    SELECT count(*) INTO itens    FROM anexos_reducao_zero     WHERE anexo = 'I';
    SELECT count(*) INTO prefixos FROM anexos_reducao_zero_ncm WHERE anexo = 'I';
    IF (itens, prefixos) <> (26, 95) THEN
        RAISE EXCEPTION 'Anexo I não sobreviveu à generalização: % itens / % prefixos (esperado 26/95)',
            itens, prefixos;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao_zero     TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_zero_ncm TO taxreformai_app';
    END IF;
END $$;
```

### Pattern 2: seed e asserções (`008_anexos_reducao_zero_xii_xiii_xv.sql`)

```sql
-- Anexos XII (art. 144, I), XIII (art. 145, I) e XV (art. 148) da LCP 214/2025
-- — redução a ZERO das alíquotas do IBS e da CBS, por NCM/SH.
--
-- Fonte primária desta transcrição (consultada em 2026-07-28, DOU Edição Extra
-- nº 11-B de 16/01/2025):
--   Anexo XII  https://legis.senado.leg.br/norma/40180341/publicacao/40180960 (p. 54)
--   Anexo XIII https://legis.senado.leg.br/norma/40180341/publicacao/40180966 (p. 54)
--   Anexo XV   https://legis.senado.leg.br/norma/40180341/publicacao/40181038 (p. 58)
--   Corpo      https://legis.senado.leg.br/norma/40180341/publicacao/40181429 (arts. 143-148)
-- Nenhum dos três tem republicação/errata, e a LC 227/2026 não alterou nem os
-- Anexos nem os arts. 144/145/148 — verificado item a item no /design.
--
-- O art. 148 diz "reduzidas a ZERO" ainda que o cabeçalho do Anexo XV diga
-- "redução de 100%": vale o dispositivo, e por isso o Anexo XV entra AQUI.
--
-- CLÁUSULAS "EXCETO" — três classes, e só uma vira linha:
--   XII/1.3  9 códigos          DESCRITIVA      0 linhas (nenhum desce de 90181980)
--   XII/5    "os dentários"     NÃO CODIFICÁVEL 0 linhas (sem código; limitação declarada)
--   XII/5    9021.39.91/.99     OPERANTE        2 linhas (descem de 90213)
--   XII/7    9022.19.91         OPERANTE        1 linha  (desce de 902219)
--   XII/11   9022.21.10/.20     DESCRITIVA      0 linhas (são os itens 8 e 10)
--   XIII/4   "partes e acess."  NÃO CODIFICÁVEL 0 linhas (item próprio: XIII/5)
--   XV/2     0709.5, 0710.80.00 OPERANTE        2 linhas (descem de 0709 e 0710)
-- Regra: uma exceção só é OPERANTE se descende de uma inclusão DO MESMO item.
-- O bloco de asserções no fim recusa qualquer exceção que não descenda.
--
-- Contagens: XII 20 itens/24 linhas · XIII 8/7 · XV 6/25.

INSERT INTO anexos_reducao_zero (anexo, anexo_ordem, item, sub_item, descricao, dispositivo_legal_ref) VALUES
 ('XII', 12, 1, 0, 'Aparelhos de eletrodiagnóstico (incluídos os aparelhos de exploração funcional e os de verificação de parâmetros fisiológicos)',
  'LCP 214/2025, art. 144, Anexo XII, item 1'),          -- cabeçalho: sem NCM
 ('XII', 12, 1, 1, 'Eletrocardiógrafos',
  'LCP 214/2025, art. 144, Anexo XII, item 1.1'),
 -- … 34 linhas de item, conforme a seção "Dados" do DESIGN
 ('XV',  15, 4, 0, 'Plantas e produtos de floricultura relativos à horticultura e cultivados para fins alimentares, ornamentais ou medicinais classificados no Capítulo 6 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 4')
ON CONFLICT DO NOTHING;

INSERT INTO anexos_reducao_zero_ncm (anexo, item, sub_item, prefixo, excecao, alinea, texto_ncm) VALUES
 ('XII',  1, 1, '90181100', FALSE, NULL, '9018.11.00'),
 ('XII',  1, 2, '90181980', FALSE, NULL, '9018.19.80'),  -- mesmo código de 1.3 e 14
 ('XII',  1, 3, '90181980', FALSE, NULL, '9018.19.80'),
 -- Item 5: UMA inclusão de 5 dígitos e DUAS exceções que descem dela.
 ('XII',  5, 0, '90213',    FALSE, NULL, '9021.3'),
 ('XII',  5, 0, '90213991', TRUE,  NULL, '9021.39.91'),
 ('XII',  5, 0, '90213999', TRUE,  NULL, '9021.39.99'),
 -- Item 7: TRÊS células de NCM num item só, e a exceção do caput desce de 902219.
 ('XII',  7, 0, '902213',   FALSE, NULL, '9022.13'),
 ('XII',  7, 0, '902214',   FALSE, NULL, '9022.14'),
 ('XII',  7, 0, '902219',   FALSE, NULL, '9022.19'),
 ('XII',  7, 0, '90221991', TRUE,  NULL, '9022.19.91'),
 -- …
 ('XIII', 2, 1, '87131000', FALSE, NULL, '8713.10.00'),  -- "Sem mecanismo de propulsão"
 -- …
 -- Anexo XV, item 4: ÚNICO prefixo de 2 dígitos do projeto. `texto_ncm` é '06',
 -- e não 'Capítulo 6', porque a coluna guarda a grafia do CÓDIGO e o DOU não
 -- escreve código aqui — a prosa fica na `descricao`, literal. Escrever
 -- 'Capítulo 6' faria prefixo_bate_com_texto derivar '6' e a migração falhar.
 ('XV',   4, 0, '06',       FALSE, NULL, '06'),
 ('XV',   2, 0, '07095',    TRUE,  NULL, '0709.5'),
 ('XV',   2, 0, '07108000', TRUE,  NULL, '0710.80.00')
ON CONFLICT DO NOTHING;

DO $$
DECLARE r RECORD; n int;
BEGIN
    -- (1) Contagem por Anexo: uma migração truncada passa em toda CHECK e falha aqui.
    FOR r IN SELECT * FROM (VALUES ('I',26,95),('XII',20,24),('XIII',8,7),('XV',6,25))
                          AS e(anexo, itens, prefixos) LOOP
        IF (SELECT count(*) FROM anexos_reducao_zero     WHERE anexo = r.anexo) <> r.itens
        OR (SELECT count(*) FROM anexos_reducao_zero_ncm WHERE anexo = r.anexo) <> r.prefixos THEN
            RAISE EXCEPTION 'Anexo %: contagem não bate com a transcrição do DESIGN', r.anexo;
        END IF;
    END LOOP;

    -- (2) Inclusões/exceções no total.
    SELECT count(*) INTO n FROM anexos_reducao_zero_ncm WHERE excecao IS TRUE;
    IF n <> 24 THEN RAISE EXCEPTION 'exceções: % (esperado 24 = 19 do Anexo I + 5 novas)', n; END IF;

    -- (3) Exceção órfã: ou erro de transcrição, ou "exceto" DESCRITIVO virado
    --     linha. Nos dois casos a linha seria inerte — ruído indistinguível de
    --     erro. Ver Decisão 6.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero_ncm e
        WHERE e.excecao IS TRUE AND NOT EXISTS (
            SELECT 1 FROM anexos_reducao_zero_ncm i
            WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
              AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%')
    ) THEN RAISE EXCEPTION 'exceção que não desce de nenhuma inclusão do próprio item'; END IF;

    -- (4) Item sem prefixo só é legítimo se for CABEÇALHO (tem sub-itens); e
    --     todo sub-item precisa do seu cabeçalho (Decisão 7).
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero i
        WHERE NOT EXISTS (SELECT 1 FROM anexos_reducao_zero_ncm p
                          WHERE p.anexo = i.anexo AND p.item = i.item AND p.sub_item = i.sub_item)
          AND NOT EXISTS (SELECT 1 FROM anexos_reducao_zero f
                          WHERE f.anexo = i.anexo AND f.item = i.item AND f.sub_item > 0)
    ) THEN RAISE EXCEPTION 'item sem linha de prefixo e sem sub-item: INSERT truncado'; END IF;

    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero f
        WHERE f.sub_item > 0 AND NOT EXISTS (SELECT 1 FROM anexos_reducao_zero c
                                             WHERE c.anexo = f.anexo AND c.item = f.item AND c.sub_item = 0)
    ) THEN RAISE EXCEPTION 'sub-item sem linha de cabeçalho'; END IF;
END $$;
```

### Pattern 3: vocabulário da NCM (`api/ncm.py`)

```python
# 2 = capítulo (Capítulo 6, Anexo XV item 4), 4 = posição (09.01), 5/6 =
# subposição (1902.1 / 1006.20), 7 = item (0210.99.1), 8 = subitem (0405.10.00).
# NÃO existe nível de 3 dígitos na NCM/SH: um prefixo de 3 seria transcrição
# errada que nunca casaria com nada — falso negativo mudo. Por isso é uma LISTA
# de comprimentos, não o intervalo 2..8.
# Espelhado pela CHECK `prefixo_comprimento_valido` (migração 007): o que a
# tabela aceita é exatamente o que esta função enxerga. Os dois mudam JUNTOS.
_COMPRIMENTOS_PREFIXO = (2, 4, 5, 6, 7, 8)
```

`digitos_ncm` não muda. `prefixos_ncm` não muda de corpo (`[codigo[:n] for n in
_COMPRIMENTOS_PREFIXO]`), só passa a devolver 6 candidatos — e `tests/test_ipi_resolucao.py`
**deve continuar passando sem uma linha de edição** (ele cobre `normalizar_ncm`, que delega a
`digitos_ncm`).

### Pattern 4: lookup em lote (`db/repositorio.py`)

```python
@dataclass(frozen=True)
class PrefixoReducaoZero:
    """Uma linha de `anexos_reducao_zero_ncm` já com o item resolvido pelo JOIN.

    `excecao=True` exclui a mercadoria DESTE item, nunca dos demais — a lei
    escreve a exclusão dentro do item ("9021.3 [...] exceto os produtos dos
    códigos 9021.39.91 e 9021.39.99").

    `anexo_ordem` vem da coluna, não de um mapa romano→número em Python: com
    dois lugares declarando a mesma verdade, o dia em que só um for atualizado
    produz uma ordem de desempate silenciosamente errada (Decisão 3).

    `descricao_contexto` é a descrição do item-pai quando esta linha pertence a
    um sub-item — sem ela, a resposta citaria "Sem mecanismo de propulsão"
    (Anexo XIII, item 2.1) como fundamentação legal de uma cadeira de rodas.
    """

    anexo: str
    anexo_ordem: int
    item: int
    sub_item: int
    prefixo: str
    excecao: bool
    texto_ncm: str
    alinea: str | None
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str


def buscar_reducao_zero_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoReducaoZero]:
    """Lookup em lote dos 4 Anexos de alíquota zero. Sem RLS: dado legal público.

    UMA query para os prefixos de todos os itens do payload, inclusões e
    exceções no mesmo lote (uma exceção só importa quando ela própria é prefixo
    do código, então cai no mesmo `= ANY`).
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT i.anexo, i.anexo_ordem, p.item, p.sub_item, p.prefixo, p.excecao,
                   p.texto_ncm, p.alinea, i.descricao, pai.descricao,
                   i.dispositivo_legal_ref
            FROM anexos_reducao_zero_ncm p
            JOIN anexos_reducao_zero i
              ON i.anexo = p.anexo AND i.item = p.item AND i.sub_item = p.sub_item
            LEFT JOIN anexos_reducao_zero pai
              ON pai.anexo = i.anexo AND pai.item = i.item
             AND pai.sub_item = 0 AND i.sub_item > 0
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoReducaoZero(*linha) for linha in cur.fetchall()]
```

### Pattern 5: resolução e desempate (`api/reducao_zero.py`)

```python
def formatar_item(item: int, sub_item: int) -> str:
    """Grafia canônica do DOU: "5", "1.2". DERIVADA da chave, nunca armazenada —
    e a CHECK `dispositivo_cita_o_proprio_item` (migração 007) garante que a
    citação legal gravada termina exatamente com esta string."""
    return f"{item}.{sub_item}" if sub_item else str(item)


def _chave_especificidade(linha: Any) -> tuple[int, int, int, int]:
    """Mais específico primeiro, com `max()`: prefixo mais longo; empate →
    menor Anexo; → menor item; → menor sub-item.

    Os dois primeiros critérios do Anexo I (comprimento, menor item) continuam
    sendo o 1º e o 3º — a ordem dos componentes é a ordem da hierarquia do
    documento legal. Ordem TOTAL: sem ela, `9018.19.80` citaria ora
    "Eletroencefalógrafos" (XII/1.2) ora "Monitor multiparâmetros" (XII/14)
    conforme a ordem em que o Postgres devolveu as linhas (Decisão 5).
    """
    return (len(linha.prefixo), -linha.anexo_ordem, -linha.item, -linha.sub_item)


def resolver_item(natureza, ncm, consulta) -> ResolucaoReducaoZero:
    if natureza == "SERVICO":
        return ResolucaoReducaoZero(SituacaoReducaoZero.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoReducaoZero(SituacaoReducaoZero.NCM_NAO_RECONHECIDO)
    if not consulta.disponivel:
        return ResolucaoReducaoZero(SituacaoReducaoZero.CONSULTA_INDISPONIVEL)

    # A chave do agrupamento é o ITEM INTEIRO — (anexo, item, sub_item) —, não
    # `item`: todo Anexo tem um item 1, e 1.2 e 1.3 são itens distintos que
    # citam o mesmo código.
    por_item: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_item[(linha.anexo, linha.item, linha.sub_item)].append(linha)

    inclusoes, exclusoes = [], []
    for linhas in por_item.values():
        excecoes = [linha for linha in linhas if linha.excecao]
        if excecoes:
            exclusoes.append(max(excecoes, key=_chave_especificidade))
        else:
            inclusoes.append(max(linhas, key=_chave_especificidade))

    if inclusoes:
        vencedora = max(inclusoes, key=_chave_especificidade)
        return ResolucaoReducaoZero(
            situacao=SituacaoReducaoZero.APLICADA,
            anexo=vencedora.anexo,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXATO" if len(vencedora.prefixo) == 8 else "PREFIXO",
            itens_correspondentes=_ordenar_correspondentes(inclusoes),
        )
    # … EXCLUIDA_EXPRESSAMENTE (idem, com `exclusoes`) … FORA_DO_ANEXO


def _ordenar_correspondentes(linhas) -> tuple[tuple[str, str], ...]:
    """Ordem NUMÉRICA por (Anexo, item, sub-item) — nunca lexicográfica: como
    string, "14" < "1.2", que inverte o que a lei quer dizer."""
    ordenadas = sorted(linhas, key=lambda l: (l.anexo_ordem, l.item, l.sub_item))
    return tuple((l.anexo, formatar_item(l.item, l.sub_item)) for l in ordenadas)
```

### Pattern 6: campos da resposta (`api/schemas_simulate.py`)

```python
class ItemCorrespondente(BaseModel):
    """Um item que também casou com o código. Qualificado pelo Anexo porque
    "item 5" sozinho é ambíguo entre 4 Anexos (todos têm um item 5)."""

    anexo: str
    item: str


class ReducaoZeroItem(BaseModel):
    """Situação do item frente aos 4 Anexos de ALÍQUOTA ZERO da LCP 214/2025:
    I (art. 125, cesta básica), XII (art. 144, dispositivos médicos), XIII
    (art. 145, acessibilidade) e XV (art. 148, hortícolas/frutas/ovos).

    SEMPRE presente, inclusive quando não se aplica: seis coisas diferentes
    colapsariam num booleano `false`. `EXCLUIDA_EXPRESSAMENTE` (foie gras no
    I/19, próteses dentárias do XII/5, cogumelos no XV/2) NÃO é o mesmo que
    `FORA_DO_ANEXO`.

    Sucede o bloco `cesta_basica`, renomeado porque o mesmo bloco agora responde
    por um tomógrafo e por uma cadeira de rodas (Decisão 8).
    """

    situacao: str
    anexo: str | None = None                   # "I" | "XII" | "XIII" | "XV"
    item: str | None = None                    # grafia do DOU: "5", "1.2"
    dispositivo_legal_ref: str | None = None   # "LCP 214/2025, art. 144, Anexo XII, item 1.2"
    descricao: str | None = None               # texto literal do item no DOU
    # Descrição do item-pai, quando `item` é sub-item: sem ela, "Sem mecanismo
    # de propulsão" (XIII/2.1) seria a fundamentação inteira (Decisão 7).
    descricao_contexto: str | None = None
    ncm_correspondido: str | None = None       # grafia que casou: "9021.3", "06"
    tipo_correspondencia: str | None = None    # EXATO | PREFIXO | EXCECAO
    itens_correspondentes: list[ItemCorrespondente] = []
    cbs_percentual_sem_reducao: Decimal | None = None
    ibs_percentual_sem_reducao: Decimal | None = None
    valor_cbs_dispensado: Decimal | None = None
    valor_ibs_dispensado: Decimal | None = None
    fonte_legal_transicao: str | None = None


class ReducaoZeroResumo(BaseModel):
    consulta_disponivel: bool
    itens_com_reducao_aplicada: int = 0
    # Quais Anexos de fato moveram o número neste payload — ["I", "XV"].
    anexos_aplicados: list[str] = []
    total_cbs_dispensado: Decimal | None = None   # None em avaliação parcial
    total_ibs_dispensado: Decimal | None = None
    itens_nao_avaliados: list[ItemNaoAvaliado] = []
    fonte_legal: str = (
        "LCP 214/2025 — alíquotas do IBS e da CBS reduzidas a zero: art. 125 e "
        "Anexo I (Cesta Básica Nacional de Alimentos), art. 144 e Anexo XII "
        "(dispositivos médicos), art. 145 e Anexo XIII (dispositivos de "
        "acessibilidade) e art. 148 e Anexo XV (produtos hortícolas, frutas e "
        "ovos). A correspondência é feita por NCM/SH; vários itens impõem "
        "condições adicionais em seu próprio texto (requisitos da Anvisa nos "
        "Anexos XII e XIII, destinação e tipo de produto no Anexo XV, "
        "conformidade com legislação específica no Anexo I) que esta simulação "
        "não verifica."
    )
```

### Pattern 7: consumo no router (`api/routers/simulate.py`)

```python
    # Cada código de 8 dígitos vira 6 prefixos candidatos (era 5, antes do
    # capítulo de 2 dígitos do Anexo XV, item 4). `set` + `sorted` mantêm a
    # query determinística e comparável em teste; payload só de serviços não
    # abre conexão nenhuma.
    prefixos_consultar = sorted({...})
    consulta_zero = consultar_com_seguranca(db_pool, prefixos_consultar)

    anexos_aplicados: set[str] = set()
    ...
        if resolucao_zero.aplicada:
            anexos_aplicados.add(resolucao_zero.anexo)
            ...
    # Ordem de exibição = ordem dos Anexos na lei, não alfabética de rótulo
    # romano ('XII' < 'XV' < 'XIII' como texto — errado).
    resumo_zero = ReducaoZeroResumo(
        anexos_aplicados=[a for a in ("I", "XII", "XIII", "XV") if a in anexos_aplicados],
        ...
    )
```

A advertência de escopo e o parecer do audit log deixam de citar "Cesta Básica Nacional (art. 125,
Anexo I)" e passam a citar "os Anexos de alíquota zero (I, XII, XIII e XV)", nomeando os que de
fato se aplicaram no payload.

---

## Data Flow

```text
1. POST /v1/tax/simulate (X-API-Key + payload) — contrato de ENTRADA inalterado
2. verificar_api_key → tenant_id; divergência com payload.tenant_id → 403
3. Fase/RegraFiscal resolvida uma vez → 422 se não confirmada (inalterado)
4. Coleta dos prefixos (2,4,5,6,7,8) de cada NCM distinto dos itens MERCADORIA
   4a. conjunto vazio   → nenhuma conexão aberta
   4b. conjunto cheio   → 1 query `= ANY(%s)` nos 4 Anexos
   4c. qualquer exceção → capturada, logada, disponivel=False
5. Por item: engine.calcular + PIS/COFINS + ICMS/ISS + IPI, como hoje
   5a. resolver_item → 6 estados, agrupando por (anexo, item, sub_item)
   5b. se APLICADA → aplicar_reducao_a_zero(resultado) — INTOCADA
6. Agregação: total_cbs/ibs já refletem as reduções; reducao_zero{dispensado,
   anexos_aplicados, não avaliados}
7. Audit log (nunca propaga) — parecer cita quantos itens e quais Anexos
8. 200 com RespostaSimulacao
```

**Custo por requisição:** continua em no máximo **2 queries** (TIPI + redução a zero), ambas O(1)
no número de itens. A tabela de redução a zero cresceu 59% em linhas (95 → 151) e continua sendo um
`= ANY` sobre índice.

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL `taxreformai-pg` / `anexos_reducao_zero*` | `psycopg_pool` via socket unix (`api/db.py`), SELECT | Papel `taxreformai_app`, senha do Secret Manager |
| `motor_calculo` | Import Python direto, in-process | N/A — segue sem tocar em banco |
| Cliente ERP | REST/JSON; **bloco renomeado** (`cesta_basica` → `reducao_zero`) e **valores de CBS/IBS mudam** para itens dos Anexos XII/XIII/XV | `X-API-Key` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit puro | `prefixos_ncm` com 6 comprimentos; `formatar_item`; `_chave_especificidade`; `resolver_item` nos 6 estados e nos 3 desempates | `tests/test_reducao_zero_resolucao.py` | pytest | Toda a política, sem banco |
| Integration (fake) | AT-001..AT-010 via `TestClient` + `FakePool`; 1 query; pool `None`; pool que explode | `tests/test_api_simulate_reducao_zero.py` | pytest + `TestClient` | Contrato da resposta |
| Integration (Postgres real) | Contagens por Anexo, CHECKs novas, exceção órfã, cabeçalho×sub-item, overlap entre Anexos, `descricao_contexto` | `tests/test_reducao_zero_db.py` | pytest + `postgres:16` do CI | SQL e constraints |
| Verificação real | 7 casos com o papel `taxreformai_app` no Cloud SQL | `scripts/verificar_reducao_zero_producao.py` via `migrar_banco.yml` | workflow_dispatch | Decisão 11 |
| E2E produção | 3ª chamada do smoke test (`06031100`) | `.github/workflows/deploy.yml` | curl + jq | Decisão 11 |

**Mapa Acceptance Test → teste:**

| AT | Cenário concreto | Onde | Asserção-chave |
|----|------------------|------|----------------|
| AT-001 | `8713.10.00` — cadeira de rodas (XIII/2.1) | api + unit | CBS/IBS = 0; `dispositivo_legal_ref == "LCP 214/2025, art. 145, Anexo XIII, item 2.1"`; `descricao_contexto` traz o cabeçalho do item 2 |
| AT-002 | `04051000` — manteiga (I/5) | api | **Valores idênticos aos do teste já shipado**: situação, dispositivo, percentuais, dispensado. Só o nome do bloco e o tipo de `item` mudam no arquivo de teste |
| AT-003 | `22030000` — cerveja | api | `FORA_DO_ANEXO`; CBS 0,9% / IBS 0,1%; nenhum Anexo citado |
| AT-004 | `07141000` — raízes/tubérculos (XV/5, prefixo `0714`) | api + unit | APLICADA; `tipo_correspondencia == "PREFIXO"`; `ncm_correspondido == "07.14"` |
| AT-005 | `06031100` — capítulo 6 (XV/4, prefixo de **2 dígitos**) | api + unit + produção | APLICADA; `ncm_correspondido == "06"`; é o caso que prova a Decisão 4 ponta a ponta |
| AT-006 | `90213991` — dentro de `9021.3`, excluído (XII/5) | api + unit | `EXCLUIDA_EXPRESSAMENTE`; alíquota **geral**, nunca zero |
| AT-007 | `07108000` — dentro de `0710`, excluído (XV/2) | api + unit | idem, citando XV/2 |
| AT-008 | `90181980` — "exceto" DESCRITIVO do XII/1.3 | api + unit + db | APLICADA (não excluída): prova que a cláusula descritiva não virou linha |
| AT-009 | `90181980` — desempate triplo | api + unit | Cita **XII/1.2**; `itens_correspondentes == [{XII,1.2},{XII,1.3},{XII,14}]`, nessa ordem |
| AT-010 | `90223000` — dentro de `9022`, fora de `9022.12/13/14/19/21` | api + unit | `FORA_DO_ANEXO` — o match é por prefixo hierárquico, não "contém a substring" |

**Testes além dos AT, por causa das decisões novas:**

- **Não-regressão dos desempates do Anexo I:** `19021900` → I/25 com `[{I,15},{I,25}]`;
  `21069090` → I/4 com `[{I,4},{I,26}]`. Mesmos vencedores de hoje, com a chave de 4 componentes.
- **Prefixo de 7 dígitos** (`02109911` → I/19) continua funcionando — o comprimento que só existe
  no Anexo I.
- **`formatar_item`**: `(5,0) → "5"`, `(1,2) → "1.2"`, `(14,0) → "14"`.
- **Ordem numérica de `itens_correspondentes`**: 1.2 antes de 14 (o teste que falha se alguém
  ordenar as strings).
- **CHECK `anexo_conhecido`** recusa `('IV', 4)`; **CHECK `dispositivo_cita_o_proprio_item`** recusa
  uma linha cuja citação diz "item 13" com `item = 14`; **CHECK de comprimento** recusa `'060'`.
- **Exceção órfã** rejeitada pelo bloco de asserções (teste que reexecuta a consulta da migração).
- **Cabeçalhos**: `buscar_reducao_zero_por_prefixo` nunca devolve XII/1 nem XIII/2 (não têm
  prefixo), e `descricao_contexto` é `None` para itens sem pai.
- **Overlap entre Anexos** (Decisão 12) — conjunto vazio, com o comentário sobre a margem de uma
  posição entre I/7 (`0713`) e XV/2 (`0701`–`0710`).
- **Pool `None`** → todos `CONSULTA_INDISPONIVEL`, 200, alíquota geral, `total_cbs_dispensado is
  None`. **Pool que levanta** → 200, não 5xx. **Serviço** → `NAO_APLICAVEL`, nenhuma conexão.

**Testes existentes que devem continuar passando SEM edição:** `tests/test_ipi_resolucao.py`,
`tests/test_api_simulate_ipi.py`, `tests/test_api_simulate.py`, `tests/test_escopo_e_compensacao.py`,
`tests/test_engine.py`, `tests/test_tabela_aliquotas.py`, `tests/test_regime_atual.py`,
`tests/test_schema_postgres.py`. Se algum precisar mudar, é regressão. **Exceção prevista e única:**
os 3 arquivos renomeados, cujo diff deve se limitar ao que a Decisão 8 autoriza.

---

## Error Handling

| Error Type | Handling Strategy | HTTP | Retry? |
|------------|---------------------|------|--------|
| NCM fora dos 4 Anexos | `FORA_DO_ANEXO`, alíquota geral da fase | 200 | Não |
| NCM excluído pelo próprio item (I/19-20, XII/5, XII/7, XV/2) | `EXCLUIDA_EXPRESSAMENTE` + citação da exceção; **nunca** zero | 200 | Não |
| NCM ilegível | `NCM_NAO_RECONHECIDO`, sem consultar o banco, item enumerado | 200 | Não |
| Cloud SQL fora do ar / grant faltando / **janela do rename** (Decisão 13) | `CONSULTA_INDISPONIVEL` + `logger.exception`; alíquota geral | 200 | Sim, pelo cliente |
| `db_pool is None` | Idem, sem log de exceção — estado esperado | 200 | N/A |
| Item `natureza=SERVICO` | `NAO_APLICAVEL`, sem coletar prefixo | 200 | N/A |
| Fase sem alíquota confirmada (2027+) | 422 **antes** do laço, como hoje | 422 | N/A |

Nenhum código de erro novo — a feature é aditiva em comportamento, e nenhum modo de falha dela
justifica invalidar CBS/IBS.

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `DB_INSTANCE_CONNECTION_NAME` | string | — | Já existente; ausente ⇒ `CONSULTA_INDISPONIVEL` |
| `DB_USER` | string | `taxreformai_app` | Papel que precisa do `GRANT SELECT` (reemitido pela 007) |
| `verificar_reducao_zero` (input de workflow) | `sim`/`nao` | `sim` | **Renomeia** `verificar_cesta_basica` em `migrar_banco.yml` |

Nenhuma variável de ambiente nova na aplicação, nenhuma mudança de Terraform. Duas migrações novas,
aplicadas pelo fluxo de sempre (`migrar_banco.yml`, guarda `MIGRAR`).

---

## Security Considerations

- **Sem SQL dinâmico com dado do cliente.** `= ANY(%s)` recebe lista como parâmetro vinculado, e
  todo prefixo passa por `digitos_ncm`/`prefixos_ncm`, que só deixam passar `[0-9]{2,8}`.
- **O `LIKE … || '%'` das asserções** opera sobre colunas da própria tabela (prefixos validados por
  CHECK como só-dígitos), dentro da migração, sem nenhum dado de requisição. Nada ali vem do
  cliente.
- **Sem RLS, deliberadamente** — lei federal, idêntica para todo tenant (mesma decisão de
  `aliquotas_ipi_tipi` e da migração 002). O rename não altera isso; `ALTER TABLE … RENAME`
  preserva as políticas existentes (não há nenhuma) e os privilégios.
- **Privilégio mínimo preservado:** só `SELECT` para o papel de runtime; escrita exclusiva do papel
  admin via migração.
- **Nenhum `DROP TABLE`** nesta feature — o rename preserva o dado. As únicas operações
  destrutivas são `DROP CONSTRAINT`, todas substituídas por constraints mais estritas na mesma
  transação.
- **Sem PII.** NCM, descrição de produto e dispositivo legal são públicos.
- **Enumeração não é vazamento:** os 4 Anexos estão publicados no DOU.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `api.reducao_zero` quando a consulta falha — é o **único** sinal em runtime de que a redução parou de ser aplicada (inclusive durante a janela da Decisão 13) |
| Resposta | `reducao_zero.consulta_disponivel`, `anexos_aplicados[]` e `itens_nao_avaliados[]` tornam a degradação e a cobertura inspecionáveis por máquina |
| Metrics | Fora de escopo (mesmo tratamento das features anteriores) |
| Verificação ativa | `scripts/verificar_reducao_zero_producao.py` (7 casos) + 3ª asserção no smoke test do deploy |

---

## Limitações declaradas (e por que não são resolvidas aqui)

1. **O prefixo de 2 dígitos concede zero a todo o Capítulo 6, e o item 4 do Anexo XV qualifica.**
   A lei diz "classificados no Capítulo 6"; a qualificação ("relativos à horticultura e cultivados
   para fins alimentares, ornamentais ou medicinais") **restringe** e não é verificável a partir do
   payload. Esta é a única limitação desta feature cujo erro é na direção **perigosa** (tributo a
   menos), e por isso está em primeiro lugar: a `descricao` literal volta na resposta e
   `fonte_legal` declara que a condição não é verificada. Fechar a lacuna exige atributos por SKU —
   `API_EMPRESA_SKUS`, posição 3 da sequência.
2. **Os arts. 144, § 1º e 145, § 1º condicionam a redução a requisitos da Anvisa** (XII) e de
   "norma de órgão público competente" (XIII). Mesma classe da limitação 1 e das condições do Anexo
   I ("em conformidade com os requisitos da legislação específica"): a simulação aplica pelo código
   e devolve o texto do item para o cliente conferir.
3. **Duas cláusulas "exceto" não são codificáveis** ("os dentários" no XII/5; "partes e acessórios"
   no XIII/4). A do XIII é inócua na prática (partes e acessórios têm item próprio, XIII/5); a do
   XII **não foi verificada** (ver a nota da Decisão 6) e é tratada como limitação até que o
   `/build` confirme contra a TIPI já ingerida.
4. **O art. 144, § 3º permite ato conjunto MEF/CGIBS incluir dispositivos não listados** em
   emergência de saúde pública, com vigência limitada ao período e à localidade. Fora de escopo:
   é lista dinâmica, com dimensão temporal e geográfica que a tabela não tem — mesma decisão já
   registrada para alterações futuras do Anexo I, SPED/IBPT e TIPI.
5. **Sem dimensão temporal.** A tabela não tem `vigencia_inicio`/`vigencia_fim`; alteração futura de
   qualquer dos 4 Anexos exige nova migração.
6. **2026 segue sendo a única fase com efeito prático** (2027-2028 é recusada com 422 pela CBS
   pendente do art. 347; 2029+ não existe em `TabelaAliquotasSeed`). O `fonte_legal_reducoes` de
   2027-2028 já está semeado e passa a valer sozinho quando a alíquota de referência for fixada.
7. **Os outros 13 Anexos continuam sem efeito** (60% por NCM, 60% por NBS, XVI, XVII, Simples
   Nacional). A tabela desta feature declara no nome e na CHECK `anexo_conhecido` que trata só de
   redução a zero; a forma dos demais será examinada contra o texto deles — e o achado do art. 144,
   II / art. 145, II já mostra que a premissa "Anexos IV e V são 60%" do roadmap é incompleta.

---

## Open Questions do DEFINE — resolvidas aqui

| # | Pergunta | Resolução |
|---|----------|-----------|
| 1 | Forma da chave primária e tipo de `item` | `(anexo, item, sub_item)` com `sub_item NOT NULL DEFAULT 0` — Decisão 2. A grafia `"1.2"` é derivada, e o banco confere a derivação contra `dispositivo_legal_ref` (Decisão 3) |
| 2 | Formato de `dispositivo_legal_ref` e **qual artigo cria cada redução** | **arts. 144 (XII), 145 (XIII) e 148 (XV)**, lidos no texto oficial nesta sessão — nenhum dos candidatos que o DEFINE supôs (126-131). Formato idêntico ao do Anexo I: `LCP 214/2025, art. N, Anexo X, item M` |
| 3 | Regra de desempate para numeração decimal e 3+ vias | Decisão 5: `(len(prefixo), -anexo_ordem, -item, -sub_item)`. `9018.19.80` → XII/1.2, listando os 3 |
| 4 | Verificação automatizada de overlap (`SHOULD`) | Decisão 12: teste SQL exato, sem precisar da tabela da NCM. Resultado vazio hoje — com margem de **uma posição** entre I/7 e XV/2 |
| — | `A-004` (Approach A ainda vale?) | **Sim**, confirmada na Decisão 1: os 3 achados são de chave, tipo e intervalo, não de mecanismo |
| — | `COULD`: catálogo descritivo × operante | Decisão 6, com uma **terceira** classe (não codificável) e uma asserção de migração que torna o erro inaplicável |

**Cinco perguntas que o DEFINE não previu e o Design precisou responder**, todas descobertas lendo
a fonte primária e o código real: qual artigo institui cada redução (achado 1); se "100%" no Anexo
XV é ou não redução a zero no dispositivo (achado 2); se a ressalva de Título da Decisão 5 do Anexo
I se repete aqui — não se repete, e é o que dispensa qualquer mudança em `motor_calculo/` (achado
3); o que fazer com as duas linhas de cabeçalho sem NCM (achado 4, Decisão 7); e se o rename da
tabela cria janela de indisponibilidade (Decisão 13).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | design-agent | Versão inicial, a partir de `DEFINE_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md` v1.0; transcrição literal dos Anexos XII, XIII e XV e leitura dos arts. 126, 143-148 e 348 contra a fonte primária do Senado; confirmado na lista de "Alteração Permanente" da LC 227/2026 que os arts. 144/145/148 não foram alterados |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`

Ordem sugerida de implementação: migração 007 (1) → migração 008 e seu catálogo (2) → repositório e
`api/ncm.py` (3, 4) → resolução (5) → schemas e router (6, 7, 8) → testes (9, 10, 11) → script e
workflows (12, 13, 14) → `CLAUDE.md` (15).

**A feature só é dada como pronta depois das duas verificações da Decisão 11** — `migrar_banco.yml`
com `verificar_reducao_zero=sim` (7 casos, papel de runtime) e a 3ª chamada do smoke test do
`deploy.yml` com `06031100` —, **nessa ordem** (Decisão 13). Então `/ship`, levando ao roadmap o
achado do art. 144, II / art. 145, II.
