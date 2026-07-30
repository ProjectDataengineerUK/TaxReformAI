# DESIGN: Anexos IV, V, VI, VII, VIII e IX — redução de 60% de CBS/IBS por NCM

> Technical design para introduzir o **primeiro mecanismo de cálculo novo desde o Anexo I** —
> redução **percentual** de alíquota, não a zero — e para unificar os 10 Anexos de redução por
> NCM/SH da LCP 214/2025 numa única resolução, porque a verificação desta sessão provou que os dois
> grupos **não são independentes**: 39 itens dos 6 Anexos novos disputam código com os 4 Anexos de
> alíquota zero já shipados.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NCM |
| **Date** | 2026-07-29 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NCM.md](./DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NCM.md) (Clarity 14/15) |
| **Feature irmã (referência de mecanismo)** | [`ANEXOS_REDUCAO_ZERO_XII_XIII_XV`](../archive/ANEXOS_REDUCAO_ZERO_XII_XIII_XV/DESIGN_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md) — shipada 2026-07-29 |
| **Status** | Ready for Build (Decisão 9 — rename do bloco da resposta — confirmada com Jonatas em 2026-07-29) |
| **Posição na sequência** | 13 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, segunda da segunda leva) |

---

## Verificação de fonte primária feita nesta sessão de `/design`

O DEFINE transcreveu os 6 Anexos **em forma resumida** e deixou explícito que a transcrição
literal (descrição de cada item e grafia de cada código) ficaria para o `/design`. Esta sessão
rebuscou a mesma fonte primária, **extraiu a estrutura de tabela (`<tr>/<td>`) de cada Anexo em vez
de ler prosa**, e reconciliou item a item contra o DEFINE.

| # | O que | URL | Resultado |
|---|-------|-----|-----------|
| 1 | Anexo IV integral | `https://legis.senado.leg.br/norma/40180341/publicacao/40180906` | HTTP 200 — 112 linhas de tabela |
| 2 | Anexo V integral | `.../publicacao/40180912` | HTTP 200 — 30 linhas |
| 3 | Anexo VI integral | `.../publicacao/40180918` | HTTP 200 — 82 linhas |
| 4 | Anexo VII integral | `.../publicacao/40180967` | HTTP 200 — 18 linhas |
| 5 | Anexo VIII integral | `.../publicacao/40180973` | HTTP 200 — 8 linhas |
| 6 | Anexo IX integral | `.../publicacao/40180979` | HTTP 200 — 36 linhas |
| 7 | Corpo da LCP 214/2025 | `.../publicacao/40181429` | HTTP 200 — arts. **129 a 148** lidos na íntegra |
| 8 | Página de detalhe da norma (Normas posteriores) | `https://legis.senado.leg.br/norma/40180341` | HTTP 200 — lista literal de alterações relida |

Consultados em 2026-07-29, com `User-Agent` de navegador (sem ele, 403 — aviso herdado das três
features anteriores). `planalto.gov.br` continua inacessível deste ambiente.

**Sete achados de fonte primária que o DEFINE não tinha — e todos os sete mudam o design:**

### Achado 1 — A premissa `A-003` do DEFINE está ERRADA, e é o achado central desta feature

O DEFINE registrou `A-003` (“não há overlap além da remissão textual do Anexo VII”) como **não
verificado**, com a observação de que o volume tornava a checagem manual inviável. A checagem foi
feita **programaticamente** nesta sessão, comparando cada um dos 389 prefixos novos com cada um dos
151 já carregados (dois prefixos compartilham um código concreto se, e somente se, um é prefixo do
outro — a mesma equivalência exata da Decisão 12 da feature anterior).

Resultado: **117 pares de prefixo em sobreposição, envolvendo 39 itens dos 6 Anexos novos e 14 dos
4 Anexos zero.** Não é uma exceção pontual; é estrutural, e em vários casos o **mesmo código de 8
dígitos** aparece nos dois grupos:

| Sobreposição | Código | Zero | 60% |
|--------------|--------|------|-----|
| Dispositivos médicos | `9018.90.99` | XII/9 “Aparelho de crioterapia” | **9 itens** do Anexo IV (2, 29, 30, 31, 32, 68, 72, 92, 105) |
| Dispositivos médicos | `9021.90.19` | XIII/6 “Implantes cocleares” | **6 itens** do Anexo IV (11, 12, 17, 34, 37, 38) |
| Dispositivos médicos | `9021.10.10` / `9021.10.20` | XII/3 e XII/4 | IV/42 |
| Dispositivos médicos | `9018.90.10` | XII/15 “Bomba de infusão” | IV/10 |
| Fórmulas metabólicas | `2106.90.90` | I/4 e I/26 | **8 itens** do Anexo VI (39-46) |
| Sal | `2501.00.90` | I/22 | VI/30 |
| Alimentos (remissão escrita na lei) | cap. 07/08/10/12 e posições | I/1, 7, 9, 10, 11, 12, 13, 17, 18; XV/2, 3, 5, 6 | VII/4, 6, 8, 14, 15 |
| Insumos agropecuários | cap. 07/10/11/12/15/25 | I/1, 6, 7, 9, 10, 11, 12, 13, 17, 18, 19, 22; XV/2, 4, 5 | IX/3, 10, 11, 19, 21 |

**Consequência de projeto (a decisão mais importante do documento):** as duas listas **não podem
ser resolvidas em separado**. Uma consulta que devolva o Anexo IV sem saber que o Anexo XII cobre o
mesmo código responde 60% onde a lei dá zero. É isto — e não a comodidade — que decide a Decisão 1
(uma tabela só) e a Decisão 3 (uma ordem total só).

**E é isto que refuta a alternativa “tabela nova e paralela” cogitada pelo DEFINE (`A-004`)**: duas
tabelas exigiriam ou um `UNION` (uma tabela só usando fantasia) ou uma junção feita em Python entre
duas listas, com a ordem de desempate declarada em dois lugares.

### Achado 2 — A contagem do Anexo V está errada no DEFINE (26 → **29**), e a do item 7 do IX (28 → **29**)

O DEFINE conta “Anexo V: 26 itens (3 cabeçalhos + 23 sub-itens)”. A tabela do DOU tem **3
cabeçalhos + 26 sub-itens = 29 linhas** (1.1 a 1.13 = 13; 2.1 a 2.10 = 10; 3.1 a 3.3 = 3). E o item
7 do Anexo IX cita **29** códigos, não 28. O total do DEFINE (271) vira **274 linhas de DOU**,
das quais **261 entram na tabela** (as 13 restantes são os 12 itens NBS e o item 34 do Anexo IX —
Decisão 10).

Este é o terceiro `/define` seguido cuja contagem o `/design` corrige. A conclusão prática já foi
tirada na feature anterior e vale de novo: **contagem de item só é confiável quando sai da estrutura
`<tr>` da tabela, não da leitura do texto renderizado.**

### Achado 3 — O Anexo IV **não** é “todos EXATO (8 dígitos)”: 13 dos seus 112 códigos são prefixos curtos

O DEFINE afirma “todos EXATO (8 dígitos)” para o Anexo IV. São **99 de 8 dígitos e 13 prefixos**:
`3917.40` (itens 7 e 8), `3006.10` (23), `3822.1` (49), `4015.1` (58), `9018.31` (59), `9018.32`
(60), `9018.39.2` (62), `9018.39.9` (64), `9018.49.1` (65), `9402.90` (69), `9027.30` (82),
`9027.90.9` (90). Comprimentos 5, 6 e 7 — todos já suportados, mas a afirmação “exato” teria feito
o `/build` transcrever `39174000`, um código que **não existe** e que jamais casaria com nada.

O Anexo V também tem um prefixo (`8517.1`, item 3.1) onde o DEFINE dizia “todos EXATO”.

### Achado 4 — **14 prefixos de 2 dígitos** (capítulo), contra 1 no projeto inteiro até hoje

O DEFINE previu o padrão “Capítulos X, Y e Z” do Anexo IX. A contagem real é maior e vai além dele:

| Anexo/item | Capítulos | Texto do item |
|------------|-----------|---------------|
| VII / 14 | **07, 08** | “Frutas, produtos hortícolas e demais produtos vegetais… classificados nos capítulos 7 e 8” |
| VII / 15 | **10, 12** | “Cereais do capítulo 10 e sementes e frutos oleaginosos classificados no capítulo 12” |
| IX / 2 | **31** | “Fertilizantes (adubos)…” |
| IX / 3 | **25** | “Corretivos de solo (inclusive condicionadores), remineralizadores e substratos para plantas…” |
| IX / 10 | **07, 10, 12** | “Semente genética, semente básica…” |
| IX / 19 | **10, 11, 12** | “Sementes e cereais… destinados diretamente à fabricação de ração para animais…” |
| IX / 21 | **15** | “Alho em pó, sal mineralizado, farinhas de peixe… destinados diretamente à fabricação de ração…” |

São 13 novos (+ o `06` do Anexo XV já shipado). **A amplitude é o risco número 1 desta feature** —
`25` concede 60% a todo o Capítulo 25 da NCM, que inclui cimento, mármore e gesso, enquanto o item
3 qualifica “corretivos de solo… em conformidade com as definições e demais requisitos da legislação
específica”. Ver Decisão 7, que responde a isso com um valor novo de `tipo_correspondencia`
(`CAPITULO`), e “Limitações declaradas”, item 1.

### Achado 5 — Os artigos que instituem cada redução, lidos no texto (e o do Anexo VI não é o que o roadmap supunha)

| Anexo | Artigo | Texto do caput (trecho literal) |
|-------|--------|----------------------------------|
| IV | **art. 131** | “Ficam reduzidas em 60% (sessenta por cento) as alíquotas do IBS e da CBS incidentes sobre o fornecimento dos **dispositivos médicos** relacionados no Anexo IV” |
| V | **art. 132** | “…dos **dispositivos de acessibilidade** próprios para pessoas com deficiência relacionados no Anexo V” |
| VI | **art. 133, § 1º** | O **caput** do art. 133 reduz em 60% os **medicamentos** em geral (não um Anexo); é o **§ 1º** que estende a redução “às operações de fornecimento das composições para nutrição enteral e parenteral… relacionadas no Anexo VI” |
| VII | **art. 135** | “…dos **alimentos destinados ao consumo humano** relacionados no Anexo VII” |
| VIII | **art. 136** | “…dos **produtos de higiene pessoal e limpeza** relacionados no Anexo VIII” |
| IX | **art. 138** | “…dos **insumos agropecuários e aquícolas** relacionados no Anexo IX… da NCM/SH e da NBS” |

O `dispositivo_legal_ref` do Anexo VI precisa citar **“art. 133, § 1º”**, não “art. 133”: o caput
trata de outra coisa (medicamentos registrados na Anvisa, sem lista), e citar só o caput mandaria o
cliente a um dispositivo que não menciona o Anexo VI.

### Achado 6 — A condição de comprador dos Anexos IV/V/VI, lida literalmente (confirma e detalha o DEFINE)

```text
Art. 144. Ficam reduzidas a zero as alíquotas do IBS e da CBS … dos dispositivos médicos relacionados:
  I – no Anexo XII …; e
  II – no Anexo IV …, caso adquiridos por:
      a) órgãos da administração pública direta, autarquias e fundações públicas; e
      b) as entidades de saúde imunes ao IBS e à CBS que possuam Certificação de Entidade
         Beneficente de Assistência Social (CEBAS) por comprovarem a prestação de serviços ao SUS,
         nos termos dos arts. 9º a 11 da Lei Complementar nº 187, de 16 de dezembro de 2021.

Art. 145, II — idêntico, para o Anexo V ("quando adquiridos por").
Art. 146, § 2º — a redução a zero do caput "aplica-se também ao fornecimento das composições …
   relacionadas no Anexo VI …, quando adquiridas pelos órgãos e entidades mencionados nos incisos
   do § 1º deste artigo" (§ 1º, I e II: os mesmos dois tipos de comprador).
```

Os três dispositivos são idênticos em estrutura e **cobrem 212 dos 261 itens** desta feature (81%
do volume). Isso decide a Decisão 6: o campo entra no payload; a lacuna é **fechada**, não
documentada.

### Achado 7 — LC 227/2026 reconfirmada, e um veto que o DEFINE não mencionou

A lista de “Alteração Permanente” da LC 227/2026 relida nesta sessão, na íntegra: entre os arts.
129-148, **só o art. 146**; entre Anexos, `Anexo 7 – Alteração Vetada`, `Anexo 14 – Revogação`,
`Anexo 20 – Alteração`, `Anexo 21 – Alteração`. Nenhum dos Anexos IV, V, VI, VIII, IX foi tocado, e
nenhum dos arts. 131, 132, 133, 135, 136, 138, 144, 145 foi tocado. **A conclusão do DEFINE está
confirmada, agora contra a lista literal e não só contra o resumo.**

Achado adicional: a **Mensagem de Veto nº 88/2025** (a original, da própria LCP 214/2025) vetou o
**art. 138, § 4º** e o **art. 138, § 9º, II** — os dois aparecem como `(VETADO)` no texto lido.
Nenhum deles toca a redução de 60% nem o Anexo IX; são partes do regime de **diferimento**, que já
está fora de escopo (`SHOULD` do DEFINE). Registrado porque é a única parte do art. 138 com buraco
no texto, e o `/build` vai encontrá-la ao ler o artigo.

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  POST /v1/tax/simulate — redução de CBS/IBS por item, agora em 10 Anexos e 2 percentuais │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [Cliente ERP] ──X-API-Key──► api/routers/simulate.py                                  │
│    payload.comprador_tipo ∈ {ORGAO_PUBLICO, ENTIDADE_CEBAS_SUS, None}  ← NOVO           │
│                                     │                                                  │
│      ┌──────────────────────────────┼──────────────────────────────┐                   │
│      │ (1) ANTES do laço            │                              │                   │
│      ▼                              ▼                              ▼                   │
│  api/ncm.py                  api/reducao.py                  api/ipi.py                │
│  prefixos_ncm()              consultar_com_seguranca         (intocado)                │
│  {2,4,5,6,7,8} — INTOCADO           │  nunca levanta               │                   │
│                                     ▼                              ▼                   │
│                  db.repositorio.buscar_reducao_por_prefixo    aliquotas_ipi_tipi        │
│                                     │  1 query / request                               │
│                                     ▼                                                  │
│      ┌──────────────────────────────────────────────────────────────┐                  │
│      │ Cloud SQL                                                    │                  │
│      │ anexos_reducao_catalogo   10 linhas ← 009 (NOVA)             │                  │
│      │   anexo · anexo_ordem · percentual_reducao · artigo_ref ·    │                  │
│      │   zero_por_comprador_ref                                     │                  │
│      │        ▲ FK (anexo)                                          │                  │
│      │ anexos_reducao        321 itens  (60 + 261)  ← 009 renomeia  │                  │
│      │ anexos_reducao_ncm    540 linhas (151 + 389)    010 carrega  │                  │
│      │   I:26/95 · IV:105/112 · V:29/30 · VI:81/86 · VII:17/53 ·    │                  │
│      │   VIII:7/7 · IX:22/101 · XII:20/24 · XIII:8/7 · XV:6/25      │                  │
│      └──────────────────────────────────────────────────────────────┘                  │
│                                                                                        │
│      │ (2) POR item de MERCADORIA                                                      │
│      ▼                                                                                 │
│  reducao.resolver_item(natureza, ncm, consulta, comprador_tipo)                         │
│      │   desempate ÚNICO sobre os 10 Anexos:                                            │
│      │   (len(prefixo), percentual_efetivo, percentual_reducao,                         │
│      │    -anexo_ordem, -item, -sub_item)                                               │
│      ▼ APLICADA?                                                                        │
│  ┌────────────────────────────┬───────────────────────────────────────────┐            │
│  │ percentual == 1.0000       │ percentual == 0.6000                      │            │
│  │ motor_calculo/reducoes.py  │ motor_calculo/reducoes.py                 │            │
│  │ aplicar_reducao_a_zero()   │ aplicar_reducao_percentual(res, regra, p) │            │
│  │ INTOCADA (já shipada)      │ NOVA — reduz a ALÍQUOTA, não o valor      │            │
│  └────────────────────────────┴───────────────────────────────────────────┘            │
│      ▼                                                                                 │
│  ItemDetalhado.reducao{anexo, item, percentual_reducao, dispositivo_legal_ref, …}       │
│      ▼ (3) agregação                                                                   │
│  RespostaSimulacao.reducao = ReducaoResumo(total_cbs_dispensado, anexos_aplicados, …)   │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘

Degradação — idêntica à já shipada, nenhum estado novo:

  Banco fora do ar ──────► CONSULTA_INDISPONIVEL ─┐
  NCM ilegível     ──────► NCM_NAO_RECONHECIDO ───┼─► 200 + alíquota GERAL da fase
  NCM fora dos 10 Anexos► FORA_DO_ANEXO ──────────┤   (tributo MAIOR que o devido)
  NCM excluído pelo item► EXCLUIDA_EXPRESSAMENTE ─┘   + advertência
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db/migrations/009_generalizar_anexos_reducao.sql` | **Novo** — cria `anexos_reducao_catalogo` (10 linhas), renomeia as 2 tabelas para `anexos_reducao`/`_ncm`, move `anexo_ordem` para o catálogo, troca a CHECK `anexo_conhecido` por uma FK, e **prova** que os 4 Anexos zero sobreviveram (60 itens/151 prefixos) | SQL puro |
| `db/migrations/010_anexos_reducao_percentual_ncm.sql` | **Novo** — seed dos 6 Anexos (261 itens, 389 prefixos) + catálogo de “exceto” + bloco de asserções, incluindo a **prova em SQL da remissão do Anexo VII** | SQL puro |
| `db.repositorio.PrefixoReducao` | **Renomeado/estendido** (era `PrefixoReducaoZero`) — ganha `percentual_reducao`, `zero_por_comprador_ref`; `anexo_ordem` passa a vir do catálogo | `dataclasses` |
| `db.repositorio.buscar_reducao_por_prefixo` | **Renomeado** — mesma query `= ANY(%s)`, mais um `JOIN` do catálogo | `psycopg` + SQL |
| `motor_calculo/reducoes.py` | **Modificado** — `aplicar_reducao_percentual` (nova) + `_recompor` (helper compartilhado); `aplicar_reducao_a_zero` mantém assinatura e comportamento | Python puro |
| `motor_calculo/engine.py` | **Modificado** — extrai `valor_do_tributo(base, aliquota)`, usado por `calcular` e pela redução percentual: a fórmula do tributo passa a existir **uma vez só** | Python puro |
| `api/reducao.py` | **Renomeado** (era `api/reducao_zero.py`) — `SituacaoReducao`, `ResolucaoReducao`, `ConsultaReducao`, `resolver_item` com `comprador_tipo` e o desempate de 6 componentes | Python + `logging` |
| `api/schemas_simulate.py` | **Modificado** — `ReducaoItem`/`ReducaoResumo`; `CompradorTipo`; `PayloadSimulacao.comprador_tipo` | `pydantic.BaseModel` |
| `api/routers/simulate.py` | **Modificado** — dois caminhos de redução, `aliquotas_aplicadas` derivadas do percentual, agregação, advertência e parecer | FastAPI `APIRouter` |
| `api/ncm.py` | **Intocado** — `_COMPRIMENTOS_PREFIXO = (2,4,5,6,7,8)` já cobre tudo que os 6 Anexos usam (achado 3 e 4) | — |
| `scripts/verificar_reducao_producao.py` | **Renomeado/estendido** — 15 casos contra o Cloud SQL real, um por mecanismo novo | Python + `psycopg` |

---
## Key Decisions

### Decision 1: uma tabela para os **10** Anexos, com o percentual como dado — não uma tabela paralela

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | `A-004` e Open Question 2 do DEFINE; achado 1 desta sessão |

**Context:** O DEFINE deixou a forma do schema aberta entre (a) estender
`anexos_reducao_zero`/`_ncm` com uma coluna de percentual e (b) criar uma tabela irmã
`anexos_reducao_percentual`/`_ncm`. Registrou também a preocupação legítima que empurrava para (b):
“misturar zero e percentual na mesma tabela pode ser arriscado”.

**Choice:** **(a), e agora não por elegância — por necessidade.** As duas tabelas são renomeadas e
generalizadas por `ALTER`, e o percentual entra como dado:

```text
anexos_reducao_zero      →  anexos_reducao        (item do Anexo;  60 → 321 linhas)
anexos_reducao_zero_ncm  →  anexos_reducao_ncm    (prefixo;       151 → 540 linhas)
                            anexos_reducao_catalogo  (NOVA; 10 linhas — Decisão 2)
```

**Rationale:**

1. **O achado 1 torna a alternativa (b) incorreta, não apenas mais cara.** Com 117 pares de
   prefixo em sobreposição entre os dois grupos — inclusive **o mesmo código de 8 dígitos** em
   `9018.90.99` (XII/9 zero × 9 itens do Anexo IV a 60%) — a resposta certa depende de comparar
   linhas dos dois grupos entre si. Duas tabelas obrigam a: um `UNION ALL` (que é uma tabela só
   usando fantasia, com a forma duplicada em ~100 linhas de DDL), ou duas consultas mescladas em
   Python (dois domínios de falha, e a ordem de desempate declarada em dois lugares). A primeira
   feature em que “separar” custaria correção, não só linhas.
2. **A ressalva da feature anterior era condicionada, e a condição não se verificou.** A Decisão 1
   de lá rejeitou generalizar “porque as posições 13/14 têm formas *provadamente diferentes*”. Esta
   sessão leu os 6 Anexos: a forma é **idêntica** (item → N prefixos; exceção escopada ao item;
   cabeçalho sem NCM; mesma chave `(anexo, item, sub_item)`). O único eixo novo é **um número**.
   Rejeitar hoje pelo argumento de ontem seria manter uma conclusão cuja premissa caiu.
3. **`ALTER` em vez de tabela nova porque as 151 linhas já carregadas não podem ser retranscritas.**
   Mesmo motivo da feature anterior, agora com o dobro do dado: retranscrever é a operação com maior
   chance de erro de dígito em toda a feature, e sem nenhum ganho.
4. **O rename é obrigatório pelo mesmo critério de sempre.** Uma linha do Anexo VIII (sabão de
   toucador, 60%) gravada numa tabela chamada `anexos_reducao_zero` é uma afirmação falsa dentro de
   um produto cujo valor inteiro é auditabilidade — e a migração é o documento de auditoria.
   `ALTER TABLE … RENAME` preserva dados, índices e privilégios.
5. **Este nome é estável.** `anexos_reducao_zero` só durou uma feature porque afirmava o
   percentual no nome. `anexos_reducao` acomoda 100%, 60% e o que vier (os Anexos II/III/X/XI da
   posição 14 são 60% também, e o único bloqueio deles é a chave NBS, não o percentual). É o
   terceiro e último rename destas tabelas por este motivo.

**Alternatives Rejected:**

1. **Tabela irmã `anexos_reducao_percentual*` + `UNION ALL` no lookup** — rejeitada pelo motivo 1.
   Fica registrado que ela era viável e que a única razão para preferi-la seria não tocar em
   estrutura provada; o preço seria duplicar ~100 linhas de DDL (FK composta, 4 CHECKs, índice) e
   pagar a ordem de desempate em dois lugares.
2. **Duas tabelas, duas consultas, mescla em Python** — rejeitada: duplica o domínio de falha (uma
   sem `GRANT` degradaria metade dos Anexos em silêncio) e faz `resolver_item` conhecer a origem de
   cada linha, que é exatamente o que o percentual como dado elimina.
3. **Percentual como constante de código (`0.60` para IV-IX, `1.00` para os demais)** — rejeitada:
   seria a mesma armadilha do mapa romano→número da Decisão 3 da feature anterior. Um Anexo novo
   entraria numa migração e a constante ficaria para trás, sem erro nenhum, aplicando o percentual
   do vizinho.

---

### Decision 2: `anexos_reducao_catalogo` — o que é verdade **sobre o Anexo** mora numa linha só

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | Onde vivem o percentual, o ordinal, o artigo e a condição de comprador |

**Context:** Quatro fatos são propriedades do **Anexo**, não do item: o percentual de redução, o
ordinal para desempate (`anexo_ordem`, hoje repetido em 60 linhas de item), o artigo que institui a
redução (hoje embutido dentro de cada `dispositivo_legal_ref`) e — novidade desta feature — o
dispositivo que zera a alíquota conforme o comprador (arts. 144 II, 145 II, 146 § 2º). Guardá-los
por item os repetiria 321 vezes; guardá-los em Python os tiraria do alcance do banco.

**Choice:** Uma terceira tabela, com **10 linhas**, referenciada por FK:

```sql
CREATE TABLE anexos_reducao_catalogo (
    anexo                  VARCHAR(4) PRIMARY KEY,
    anexo_ordem            SMALLINT   NOT NULL UNIQUE,
    percentual_reducao     NUMERIC(5,4) NOT NULL,   -- fração da alíquota REMOVIDA
    assunto                TEXT NOT NULL,
    artigo_ref             TEXT NOT NULL,           -- 'LCP 214/2025, art. 131'
    zero_por_comprador_ref TEXT,                    -- 'LCP 214/2025, art. 144, II' | NULL

    -- O conjunto fechado agora declara os TRÊS fatos no mesmo lugar. Carregar o
    -- Anexo IV com percentual 1.0 (ou o XII com 0.6) falha aqui, no INSERT.
    CONSTRAINT catalogo_conhecido CHECK (
        (anexo, anexo_ordem, percentual_reducao) IN (
            ('I',1,1.0), ('IV',4,0.6), ('V',5,0.6), ('VI',6,0.6), ('VII',7,0.6),
            ('VIII',8,0.6), ('IX',9,0.6), ('XII',12,1.0), ('XIII',13,1.0), ('XV',15,1.0))
    ),
    -- Anexo já reduzido a zero não pode ter condição de comprador: seria uma
    -- condição para chegar onde ele já está.
    CONSTRAINT so_percentual_tem_condicao_de_comprador CHECK (
        percentual_reducao < 1 OR zero_por_comprador_ref IS NULL
    )
);
ALTER TABLE anexos_reducao
    ADD FOREIGN KEY (anexo) REFERENCES anexos_reducao_catalogo (anexo);
```

`anexos_reducao.anexo_ordem` é **removida** (`DROP COLUMN`) — passa a vir do catálogo.

**Rationale:**

1. **A FK substitui a CHECK `anexo_conhecido` com vantagem.** A garantia “ninguém carrega aqui um
   Anexo que esta tabela não declara” continua existindo, mas agora quem quiser acrescentar um
   Anexo precisa **inserir uma linha dizendo qual é o percentual e qual artigo o institui** — a
   decisão consciente que se queria forçar fica ainda mais explícita.
2. **`percentual_reducao` no catálogo, não no item.** Ele não varia dentro de um Anexo em nenhum dos
   10, e a `catalogo_conhecido` amarra o valor ao rótulo. Se um Anexo futuro tiver percentual por
   item (o Anexo XVI, posição 15, é uma tabela por ano), a coluna desce para o item numa migração
   própria — e aí será uma decisão, não um acidente.
3. **`zero_por_comprador_ref` não tem outro lugar razoável.** É um fato de 3 Anexos; por item seria
   repetido 212 vezes, e uma tabelinha só para ele seria um catálogo pela metade.
4. **`artigo_ref` remove a única redundância que a feature anterior deixou passar:** hoje
   “art. 144” está escrito 20 vezes dentro dos `dispositivo_legal_ref` do Anexo XII. Ele
   **continua** lá (a CHECK `dispositivo_cita_o_proprio_item` depende da string completa e o
   cliente consome a citação pronta), mas agora existe uma fonte canônica por Anexo para as
   mensagens agregadas — que hoje são montadas por concatenação à mão no router.
5. **Custo de consulta: zero round-trips a mais.** É um `JOIN` de 10 linhas na mesma query. A
   exigência “1 query, não N+1” do pedido de `/design` continua satisfeita literalmente.

**Alternatives Rejected:**

1. **`percentual_reducao` como coluna de `anexos_reducao` + CHECK de 10 triplas `(anexo,
   anexo_ordem, percentual)`** — rejeitada por 2 e 3: funcionaria para o percentual, mas deixaria a
   condição de comprador sem casa (ou repetida 212 vezes, ou numa tabela de 3 linhas que é este
   catálogo pela metade). Fica registrado que é a alternativa mais barata e que a diferença é de
   coerência, não de correção.
2. **Manter `anexo_ordem` no item e só acrescentar o catálogo** — rejeitada: dois lugares
   declarando o ordinal é exatamente o defeito que a Decisão 3 da feature anterior eliminou.
3. **Catálogo em Python (dict) em vez de tabela** — rejeitada pelo mesmo motivo de sempre: o banco
   deixaria de poder recusar uma linha inconsistente no `INSERT`.

---

### Decision 3: uma ordem total só, de **seis** componentes — e a precedência que a lei escreve sai de graça

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | MUST “precedência normativa explícita”; AT-002 e AT-003; achado 1 |

**Context:** A feature anterior desempatava por `(len(prefixo), -anexo_ordem, -item, -sub_item)`.
Com os 10 Anexos na mesma tabela, essa chave responde **errado** em 35 pares reais: `9018.90.99`
empata em comprimento entre XII/9 (zero) e IV/2 (60%), e `-anexo_ordem` faria **IV (4) vencer XII
(12)** — 60% onde a lei dá zero. Além disso o DEFINE exige tratar a remissão textual do Anexo VII
(“ressalvados os produtos relacionados no Anexo I”), e a condição de comprador (Decisão 6) pode
transformar um 60% em zero **em tempo de requisição**.

**Choice:** Uma chave de **seis** componentes, aplicada por `max()` ao conjunto de linhas que
casaram — os quatro antigos, mais dois:

```python
def _chave_especificidade(linha, comprador_qualificado: bool):
    """Mais específico primeiro; a MAIOR redução desempata; a INCONDICIONAL
    desempata de novo; depois a ordem do documento legal."""
    return (
        len(linha.prefixo),                              # 1. especificidade do código
        _percentual_efetivo(linha, comprador_qualificado),  # 2. maior redução vence
        linha.percentual_reducao,                        # 3. redução INCONDICIONAL vence
        -linha.anexo_ordem, -linha.item, -linha.sub_item,   # 4-6. ordem da lei
    )
```

onde `_percentual_efetivo` devolve `Decimal("1.0000")` quando o comprador é qualificado e o Anexo
tem `zero_por_comprador_ref`, e `percentual_reducao` no caso contrário.

**A consequência mais importante é que nada precisa ser dito sobre o Anexo VII.** A remissão
textual dos itens 4, 5, 6, 14 e 15 é honrada pelo **componente 1**, sozinho — porque em **todos os
13 pares** em que um item “ressalvado” do Anexo VII se sobrepõe a um Anexo zero, o prefixo do
Anexo zero é **estritamente mais longo**:

| Anexo VII | prefixo | Cede a | prefixo | Verificado |
|-----------|---------|--------|---------|------------|
| 4 (farinha) | `1101.00`(6), `11.02`(4), `11.06`(4) | I/13, I/11, I/18, I/10 | 8 dígitos | ✔ 8 > 6 e 8 > 4 |
| 5 (grumos/sêmolas) | `1103.11.00`, `1103.19.00` (8) | — | — | ✔ **sem sobreposição real** (o Anexo I cita `1103.13.00`); a ressalva do item 5 é inerte hoje |
| 6 (grãos de cereais) | `1104.1`, `1104.2` (5) | I/12, I/17 | 8 dígitos | ✔ 8 > 5 |
| 14 (frutas/hortícolas) | `07`, `08` (2) | I/7; XV/2, 3, 5, 6 | 4 a 8 dígitos | ✔ |
| 15 (cereais/oleaginosas) | `10`, `12` (2) | I/1 | `100620`, `100630`, `10064000` | ✔ |

Isso é **verificado por asserção na migração 010**, não afirmado: a migração recusa a transcrição
se qualquer inclusão de um Anexo zero se sobrepuser a um desses 5 itens com prefixo de comprimento
menor ou igual.

**Rationale:**

1. **A especificidade vem primeiro porque é a única regra que a lei escreve para *todos* os casos.**
   O Anexo VII declara sua cessão em 5 itens; os outros 34 itens em sobreposição não declaram nada.
   Uma regra “zero sempre vence” (ver alternativa 1) precisaria valer para todos e produz erro na
   direção perigosa em 4 casos concretos (Decisão 4). Uma regra “o mais específico vence” resolve
   os 5 declarados **e** os 34 silenciosos com o mesmo critério, e coincide com o que a lei
   escreveu onde ela escreveu.
2. **O componente 2 (maior redução) é o que corrige os 35 empates.** Onde os dois grupos citam
   exatamente o mesmo código de 8 dígitos, não há especificidade que os separe — e aí a escolha
   entre 0% e 40% da alíquota não pode cair num ordinal de Anexo. Fica com quem reduz mais, que é
   também a leitura que nenhum contribuinte contestaria.
3. **O componente 3 existe para a citação, não para o número.** Quando o comprador é qualificado,
   um item do Anexo IV e um do Anexo XII passam a valer zero os dois; citar o **incondicional**
   (art. 144, I) é mais forte na defesa fiscal do que citar o condicional (art. 144, II), porque
   não depende de provar a qualidade do comprador. Sem este componente, `-anexo_ordem` citaria o
   Anexo IV por ser 4 < 12 — o número certo com a fundamentação mais frágil.
4. **Ordem total, portanto determinística** — pela `UNIQUE (anexo, item, sub_item, prefixo,
   excecao)`, não existem duas linhas distintas com a chave inteira igual. Sem isso, `2106.90.90`
   citaria ora I/4, ora I/26, ora um dos 8 itens do Anexo VI, conforme a ordem em que o Postgres
   devolvesse as linhas.
5. **Os desempates já shipados continuam idênticos** (`1902.19.00` → I/25; `2106.90.90` → I/4;
   `9018.19.80` → XII/1.2): os componentes 2 e 3 empatam entre linhas do mesmo Anexo, e os antigos
   4-6 decidem como antes. É o guard-rail de não-regressão que AT-012 exige.

**Alternatives Rejected:**

1. **Ranquear “é redução a zero” ACIMA do comprimento do prefixo** — rejeitada, e é a alternativa
   séria. Ela garantiria que zero sempre vence, o que soa mais seguro, mas produz **subtributação**
   em 4 casos reais (Decisão 4): o `06` do Anexo XV (capítulo inteiro) zeraria as mudas do Anexo
   IX/11, e o `9025` do Anexo XII zeraria o termômetro falante do Anexo V/2.3. Estender um prefixo
   de 2 dígitos sobre um código de 4 é a direção **perigosa** de erro — a única que este projeto
   não aceita como degradação.
2. **Uma coluna `cede_ao_anexo` nos 5 itens do Anexo VII** — rejeitada: seria uma segunda regra de
   precedência para o caso que a primeira já resolve, e as duas divergiriam no dia em que um Anexo
   novo se sobrepusesse a esses itens. A remissão continua registrada onde a lei a escreveu: dentro
   da `descricao` literal do item, que volta na resposta.
3. **Recusar (`422`) quando um código cai em dois Anexos de percentuais diferentes** — rejeitada:
   39 itens estão em sobreposição, o que transformaria uma classe inteira de mercadorias (todos os
   dispositivos médicos) em erro. A lei não é ambígua para o contribuinte — ela dá a maior redução;
   ambígua é só a citação, e para isso existe `itens_correspondentes`.

---

### Decision 4: as **4 sobreposições em que o 60% vence a redução a zero** são declaradas e fixadas por teste

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | A consequência da Decisão 3 que ninguém deve descobrir em produção |

**Context:** Pelo componente 1 da Decisão 3, um prefixo mais longo vence. Em 4 pares (e só 4, de
117), o prefixo do Anexo **zero** é mais curto que o do Anexo de 60% — então o resultado é 60% onde
uma leitura ingênua esperaria zero.

**Choice:** Os 4 casos ficam como estão, **nominalmente listados** no cabeçalho da migração 010, e
um teste os fixa: se aparecer um quinto, o teste falha.

| Código-exemplo | Zero (perde) | 60% (vence) | Por quê é defensável |
|----------------|--------------|-------------|----------------------|
| `0601.10.00` | XV/4 — `06`, “plantas e produtos de floricultura… Capítulo 6” | IX/11 — `06.01`, “Mudas de plantas e demais materiais propagativos” | A lei citou **capítulo** de um lado e **posição** do outro; a posição é a regra específica |
| `0602.90.90` | XV/4 — `06` | IX/11 — `06.02` | idem |
| `9025.19.90` | XII/12 — `90.25`, “Densímetros… termômetros…” | V/2.3 — `9025.19.90`, “Termômetro digital com sistema de voz” | Código de 8 dígitos contra posição de 4 |
| `9018.20.10` | XII/2 — `9018.20`, “Aparelhos de raios ultravioleta ou infravermelhos” | IV/70 — `9018.20.10`, “Fotocoagulador a laser” | Código de 8 dígitos contra subposição de 6 |

**Rationale:**

1. **O erro é na direção segura.** Nos 4 casos, aplicar 60% cobra **mais** tributo do que aplicar
   zero. É a mesma direção de degradação que o projeto já aceita e declara desde a Decisão 8 do
   Anexo I; o inverso (a alternativa 1 da Decisão 3) cobraria menos.
2. **Nos 4 casos, a regra específica é a de 60%.** Não é um acidente de arredondamento de regra: em
   todos, o legislador escreveu um código mais preciso no Anexo de 60% e um mais amplo no de zero.
   Um fotocoagulador a laser é um aparelho de raios infravermelhos — e o Anexo IV o nomeia.
3. **A lista fechada é o que impede a regressão silenciosa.** O perigo real não é o caso conhecido;
   é o quinto, que entraria numa revisão de 120 dias (art. 131 § 2º) sem ninguém notar. O teste que
   compara o conjunto com esta tabela é o alarme.
4. **`itens_correspondentes` já mostra os dois lados** — quem estranhar “Fotocoagulador a laser
   60%” vê o XII/2 na lista e decide sozinho.

---

### Decision 5: `aplicar_reducao_percentual` reduz a **alíquota**, não o valor já arredondado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | MUST “nova função de cálculo”; Open Question 3 do DEFINE |

**Context:** O DEFINE mapeou duas opções de assinatura (função nova vs. generalizar
`aplicar_reducao_a_zero` com `percentual=1.0`) e deixou a escolha para o `/design`. Ao escrever a
função, aparece uma decisão que o DEFINE não previu e que **muda o número na resposta**: o que
exatamente é multiplicado por 0,40?

- **Escalar o valor já calculado:** `valor_cbs_reduzido = round(round(base × 0,9%) × 0,40)`.
- **Reduzir a alíquota e recalcular:** `valor_cbs_reduzido = round(base × 0,9% × 0,40)`.

Os dois divergem em **1 centavo** para entradas reais. Com `base_iva = 137,49`: a primeira dá
`round(1,2374) = 1,24 → × 0,40 = 0,496 → 0,50`; a segunda dá `137,49 × 0,36% = 0,49496 → 0,49`.

**Choice:** **Reduzir a alíquota.** A função nova recebe a `RegraFiscal` e recalcula a partir da
base, usando a mesma fórmula do engine, extraída para uma função pública compartilhada:

```python
# motor_calculo/engine.py
def valor_do_tributo(base: Decimal, aliquota: Decimal) -> Decimal:
    """A fórmula do tributo mora AQUI, e em nenhum outro lugar."""
    return (base * aliquota).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# motor_calculo/reducoes.py
def aplicar_reducao_percentual(
    resultado: ResultadoCalculo,
    regra: RegraFiscal,
    percentual_reducao: Decimal,
    *,
    split_payment_active: bool = True,
) -> ResultadoCalculo:
    """CBS e IBS recalculados com a alíquota REDUZIDA; IS intacto."""
```

**Rationale:**

1. **É o que a lei diz.** Os arts. 131 a 138 escrevem “ficam reduzidas em 60% (sessenta por cento)
   **as alíquotas** do IBS e da CBS” — não “fica reduzido em 60% o valor devido”. O objeto da
   redução é a alíquota, e reduzi-la é a tradução literal.
2. **É o que torna a resposta auditável, que é o argumento decisivo.** A resposta devolve
   `aliquotas_aplicadas.cbs_percentual = 0.36` (0,9% × 0,40). Se o valor tivesse sido obtido
   escalando o valor cheio, existiriam payloads em que `valor ≠ base × 0,36%` — e o cliente que
   refizesse a conta a partir da alíquota citada acharia um centavo de diferença **sem nenhuma
   forma de descobrir por quê**. Num produto cujo entregável é uma defesa fiscal, um número não
   reproduzível a partir da própria fundamentação é pior do que um número diferente.
3. **`valor_do_tributo` extraída elimina a única duplicação que essa escolha criaria.** Sem ela, a
   fórmula `round(base × alíquota)` passaria a existir em dois arquivos, e o dia em que o
   arredondamento mudasse (de `ROUND_HALF_UP` para bancário, por exemplo) mudaria só num.
4. **`aplicar_reducao_a_zero` mantém assinatura e comportamento** — o MUST do DEFINE. Ela continua
   sendo a função chamada no caminho de zero, mesmo sendo hoje matematicamente equivalente a
   `aplicar_reducao_percentual(…, Decimal("1.0000"))`: manter o caminho já shipado independente da
   `RegraFiscal` significa que um bug na leitura da regra não pode transformar um zero provado em
   outra coisa. **Um teste prova que as duas coincidem** — que é o jeito de ter a garantia sem ter o
   acoplamento.
   As duas passam a compartilhar `_recompor(resultado, valor_cbs, valor_ibs, split_payment_active)`,
   que recompõe `total_tributos` e `valor_liquido`: é mudança de corpo, **não** de assinatura nem de
   comportamento, e os testes já shipados de `aplicar_reducao_a_zero` seguem sem uma linha de
   edição — é essa a prova.
5. **`regra` explícita, não deduzida.** Mesma disciplina de `split_payment_active`: o chamador
   precisa passar a **mesma** `RegraFiscal` usada em `engine.calcular()`. Deduzi-la do
   `ResultadoCalculo` (dividindo valor por base) seria adivinhar o passado dele, e falharia
   justamente quando o valor foi arredondado.

**Alternatives Rejected:**

1. **`aplicar_reducao_a_zero(resultado, percentual=Decimal(1))` generalizada** — rejeitada pelo
   motivo 4 e porque o DEFINE pede explicitamente não alterá-la. Além disso a versão correta
   (motivo 1) exige a `RegraFiscal`, que o caminho de zero não precisa: generalizar tornaria
   obrigatório um argumento que 4 Anexos não usam.
2. **Escalar o valor já calculado** (`valor × 0,40`) — rejeitada pelo motivo 2. É mais simples e
   não precisaria da `RegraFiscal`; o preço seria uma resposta em que a alíquota citada não
   reproduz o valor citado.
3. **Um parâmetro `reducao_aliquota` em `engine.calcular()`** — rejeitada: o engine deixaria de ser
   “alíquota por fase, uniforme para todo o payload” (Decisão 6 do Anexo I), e o router precisaria
   chamá-lo duas vezes por item para saber quanto foi dispensado.

---

### Decision 6: `comprador_tipo` entra no payload — a lacuna dos arts. 144 II / 145 II / 146 § 2º é **fechada**, não documentada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | MUST/“Achado crítico” e `A-005` do DEFINE; Open Question 1 |

**Context:** O DEFINE deixou explícito que a condição de comprador dos Anexos IV, V e VI (212 de
261 itens, 81% do volume) **não pode ficar implícita**, e ofereceu duas saídas: um campo novo no
payload, ou uma limitação declarada por item na resposta.

**Choice:** **O campo entra.** `PayloadSimulacao` ganha um campo opcional, no nível da operação (o
comprador é da operação, não do item), com o mesmo contrato de `regime_apuracao` — `None` significa
“não informado”, nunca um default:

```python
class CompradorTipo(StrEnum):
    """Quem ADQUIRE, quando isso muda a alíquota. Só os dois tipos que a lei
    nomeia — não é uma taxonomia de clientes."""
    ORGAO_PUBLICO = "ORGAO_PUBLICO"          # arts. 144 II "a" / 145 II "a" / 146 §1º I
    ENTIDADE_CEBAS_SUS = "ENTIDADE_CEBAS_SUS"  # arts. 144 II "b" / 145 II "b" / 146 §1º II


class PayloadSimulacao(BaseModel):
    ...
    comprador_tipo: CompradorTipo | None = None
```

Efeito, e só ele: para um item cujo Anexo vencedor tenha `zero_por_comprador_ref` (IV, V, VI), o
percentual aplicado passa de 0,6000 para 1,0000 e a resposta cita **os dois** dispositivos — o do
item e o da condição. Quando o campo é `None`, aplica-se 60% **e** a resposta declara, no próprio
item, que a alíquota seria zero para comprador qualificado (`zero_por_comprador_disponivel: true` +
`dispositivo_legal_comprador` preenchido).

**Rationale:**

1. **Sem o campo, o MUST do DEFINE é literalmente insatisfazível.** Ele proíbe “aplicar 60% quando o
   comprador é conhecido como órgão público/CEBAS”. Se o payload não tem como dizer quem compra, o
   comprador nunca é conhecido — a proibição só pode ser cumprida existindo a forma de informá-lo.
   A opção “documentar” cumpriria metade do MUST (não aplicar zero em silêncio) e deixaria a outra
   metade fora de alcance para sempre.
2. **O custo é um campo opcional; o benefício é 81% do volume da feature.** Nenhum payload
   existente muda de resposta (ausente ⇒ `None` ⇒ 60%, exatamente o que aconteceria sem o campo), e
   nenhum cliente precisa mudar para continuar funcionando. É aditivo em contrato e em
   comportamento.
3. **Enum fechado de dois valores, não texto livre.** `operacao_tipo` é `str` livre e o
   `regime_apuracao` é enum; a diferença é que este campo **muda o número**. `"orgao publico"`,
   `"ÓRGÃO PÚBLICO"` e `"prefeitura"` precisariam todos significar a mesma coisa — ou, pior,
   silenciosamente não significar nada.
4. **O campo não presume nada sobre o produto.** Ele não verifica se o comprador é de fato imune,
   nem se tem CEBAS válido; declara o que o cliente afirmou. Isso é dito em `fonte_legal`, e é a
   mesma natureza declaratória de `bem_importado` e `regime_apuracao`.
5. **A condição entra no desempate, não só no cálculo** (componente 2 da Decisão 3). Se ficasse só
   no cálculo, um código presente no Anexo IV **e** num Anexo de 60% sem condição poderia ser
   resolvido pelo segundo, e o zero do comprador qualificado sumiria sem sintoma. Hoje, por sorte,
   o item de IV/V/VI vence todos os 12 pares em que isso ocorreria — e “por sorte” não é garantia:
   com a condição no desempate, passa a ser por construção.

**Alternatives Rejected:**

1. **Documentar como limitação, sem mudar o payload** — rejeitada pelo motivo 1. Era a saída
   admitida pelo DEFINE “apenas se a resposta deixar explícito, por produto, que a redução pode ser
   maior”. Essa declaração **continua existindo** nesta escolha (é o caso `comprador_tipo = None`),
   então a alternativa é um subconjunto estrito do que foi decidido.
2. **`comprador_tipo` por item** — rejeitada: não existe operação em que dois itens da mesma nota
   tenham compradores diferentes. Seria 100 cópias do mesmo valor por payload.
3. **Um booleano `comprador_qualificado`** — rejeitada: os dois incisos têm fundamentos distintos
   (um é ente público, o outro é entidade imune com CEBAS comprovando serviço ao SUS) e a resposta
   precisa citar o inciso certo. Um booleano obrigaria a citar “art. 144, II” sem a alínea.

---

### Decision 7: `tipo_correspondencia` ganha o valor **`CAPITULO`** — o risco nº 1 da feature vira campo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | Achado 4; a limitação mais perigosa desta feature |

**Context:** 14 prefixos (13 novos + o `06` já shipado) têm 2 dígitos e concedem redução a um
**capítulo inteiro** da NCM, enquanto o texto do item restringe por destinação (“destinados
diretamente à fabricação de ração para animais”), por natureza (“Semente genética, semente
básica…”) ou por conformidade (“em conformidade com as definições e demais requisitos da legislação
específica”) — nada disso verificável a partir de `sku`, `ncm`, quantidade e valor. O caso extremo é
o Capítulo **25** (IX/3): a NCM o usa para sal, enxofre, **cimento, mármore e gesso**, e o item fala
de corretivos de solo.

Aqui o erro é na direção **perigosa** (tributo a menos), a única exceção à degradação conservadora
do projeto — e agora ela é 14 vezes maior que quando foi aceita para o `06` do Anexo XV.

**Choice:** `tipo_correspondencia`, que hoje vale `EXATO | PREFIXO | EXCECAO`, ganha **`CAPITULO`**
para `len(prefixo) == 2`. É derivado, nunca armazenado — a mesma disciplina de `EXATO`:

```python
def _tipo_correspondencia(prefixo: str) -> str:
    if len(prefixo) == 8:
        return "EXATO"
    if len(prefixo) == 2:
        return "CAPITULO"   # capítulo INTEIRO da NCM: a mais ampla que existe
    return "PREFIXO"
```

E `ReducaoResumo` ganha `itens_por_capitulo: int` — quantos itens do payload tiveram a redução
concedida por correspondência de capítulo.

**Rationale:**

1. **Uma limitação que o cliente pode filtrar vale mais que uma que ele precisa ler.** A prosa de
   `fonte_legal` já dizia que condições textuais não são verificadas, e continua dizendo. A
   diferença é que um ERP consegue programar “revisar manualmente todo item com
   `tipo_correspondencia == 'CAPITULO'`” — 14 prefixos, provavelmente poucos itens por payload —
   e não consegue programar “ler o aviso”.
2. **Não custa nada e melhora o passado.** O `06` do Anexo XV, já em produção, passa a devolver
   `CAPITULO` em vez de `PREFIXO`, que é uma descrição mais verdadeira do que aconteceu.
3. **A alternativa de não carregar os capítulos foi considerada e recusada** (alternativa 1): ela
   trocaria subtributação por sonegação do benefício, e faria a tabela deixar de ser transcrição
   da lei — que é o que permite usá-la como documento de auditoria.
4. **`PREFIXO` continua significando “4 a 7 dígitos”**, que é uma faixa em que a correspondência
   ainda é razoavelmente específica (posição/subposição/item). O corte em 2 não é arbitrário: é o
   único nível da NCM em que um prefixo cobre milhares de códigos.

**Alternatives Rejected:**

1. **Não carregar os 13 prefixos de capítulo, documentando-os como não resolvidos** — rejeitada
   pelo motivo 3. Ela é a leitura conservadora do ponto de vista do fisco e a **errada** do ponto
   de vista do contribuinte: negaria uma redução que a lei concede, em cima de código que a lei
   escreveu. Fica registrada porque é a única mitigação que elimina o risco de subtributação, e
   porque a decisão foi consciente.
2. **Uma coluna `condicao_textual BOOLEAN` no item** — rejeitada: seria `TRUE` em quase todos os
   261 itens (Anvisa no IV, norma de órgão competente no V, CMED no VI, MAPA no IX). Dado que não
   varia não é dado — mesmo argumento da Decisão 6 da feature anterior contra `tipo_excecao`.
3. **Rebaixar o capítulo a “sugestão” (devolver a alíquota cheia e um aviso)** — rejeitada:
   inventaria um sétimo estado de resolução para 14 linhas, e a lei não escreveu “sugestão”.

---

### Decision 8: a exceção continua **escopada ao item** — e a resposta passa a mostrar quem excluiu

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | Um efeito da união dos 10 Anexos que muda resposta já shipada |

**Context:** A Decisão 3 do Anexo I estabeleceu que uma exceção exclui a mercadoria **daquele
item**, nunca dos demais. Com os 10 Anexos na mesma resolução, isso produz um efeito novo e
correto, mas que **muda uma resposta já em produção**:

```text
0709.51.00 (cogumelos Agaricus)
  XV/2  → prefixo 07095, excecao=TRUE   "exceto os cogumelos e trufas…"   (Anexo zero)
  VII/14→ prefixo 07,    inclusão       "…capítulos 7 e 8…"               (Anexo 60%)

  hoje:   EXCLUIDA_EXPRESSAMENTE, alíquota cheia
  depois: APLICADA, 60%, citando VII/14
```

É a leitura certa: o Anexo VII/14 ressalva “os produtos **relacionados** nos Anexos I e XV”, e um
cogumelo não é relacionado no Anexo XV — ele é **retirado** de lá. Mas quem só olhar o diff verá
uma resposta mudar de “excluída” para “reduzida”, o que parece regressão.

**Choice:** A regra fica como está (exceção escopada ao item), e `ReducaoItem` ganha
`itens_excluidos: list[ItemCorrespondente]` — **sempre** preenchido quando houve exclusão, mesmo
que uma inclusão tenha vencido. Hoje as exclusões só aparecem quando **não** há inclusão nenhuma.

**Rationale:**

1. **Flexibilizar a regra daria a resposta errada em um caso e certa em outro — não há regra
   uniforme.** A tentação é “uma exceção mais longa vence uma inclusão mais curta”. Ela acertaria
   `0711.10.00` (posição expressamente excetuada por VII/14, mas incluída pelo capítulo 07 do
   IX/10 — ver Limitações, item 2) e **erraria** o cogumelo. Como o critério não separa os dois,
   mantém-se o que a lei escreve item a item.
2. **`itens_excluidos` transforma o caso confuso em caso inspecionável.** A resposta do cogumelo
   passa a dizer, ao mesmo tempo, “60% pelo Anexo VII, item 14” e “o Anexo XV, item 2 exclui
   expressamente este código” — que é exatamente o raciocínio que um auditor faria.
3. **É aditivo.** Nenhum campo muda de tipo; quem não olhar continua vendo o que via.

---

### Decision 9: o bloco da resposta passa de `reducao_zero` para `reducao` — **pendente de confirmação**

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted — confirmado diretamente com Jonatas em 2026-07-29 (renomear sem alias, mesmo protocolo da Decisão 8 da feature anterior) |
| **Date** | 2026-07-29 |
| **Resolve** | Consequência inevitável de a resposta passar a carregar 60% |

**Context:** O bloco `reducao_zero` tem **um dia de vida** (shipado em 2026-07-29 pela feature
anterior, que por sua vez renomeou `cesta_basica`). Depois desta feature ele responderá por um
sabão de toucador com 60% de redução. `"reducao_zero": {"situacao": "APLICADA"}` num item cuja
CBS não é zero é falso.

**Choice:** Renomear para `reducao`, com um campo novo que dá o número:

| Campo | Antes | Depois |
|-------|-------|--------|
| bloco por item / agregado | `reducao_zero` | `reducao` |
| `percentual_reducao` | — | **novo**: `60.00` \| `100.00` |
| `zero_por_comprador_disponivel` | — | **novo**: `bool` (Anexos IV/V/VI) |
| `dispositivo_legal_comprador` | — | **novo**: `"LCP 214/2025, art. 144, II"` \| `null` |
| `itens_excluidos` | — | **novo** (Decisão 8) |
| `tipo_correspondencia` | `EXATO\|PREFIXO\|EXCECAO` | `+ CAPITULO` (Decisão 7) |
| `anexos_aplicados` | `["I","XV"]` | idem, agora com 10 rótulos possíveis, **ordenados pelo catálogo** |
| `situacao`, `anexo`, `item`, `descricao`, `descricao_contexto`, `ncm_correspondido`, `itens_correspondentes`, `*_sem_reducao`, `valor_*_dispensado`, `fonte_legal_transicao` | — | inalterados em nome e semântica |

**Sem alias**, e com o mesmo guard-rail que substituiu o alias na feature anterior:

> A alteração dos testes já existentes dos 4 Anexos zero deve se limitar ao **nome do bloco** e aos
> **campos novos**. Qualquer *valor* asserido que precise mudar — situação, dispositivo legal,
> percentual, total dispensado — é regressão, não teste desatualizado. A única exceção prevista e
> autorizada é `0709.5*`/`0710.80.00` (Decisão 8) e o `tipo_correspondencia` de `06031100`
> (Decisão 7), ambos com teste próprio dizendo por quê.

**Rationale:**

1. **Manter o nome faria a resposta mentir** — o mesmo argumento que obrigou o rename anterior, e
   que obriga o rename da tabela (Decisão 1). Um alias exigiria carregar dois blocos com semânticas
   divergentes para sempre.
2. **O raio de alcance é o mesmo medido ontem, e continua pequeno:** `grep` por `reducao_zero` fora
   de `.claude/sdd` encontra o próprio código, 3 arquivos de teste, `deploy.yml` (caminhos `jq`),
   `migrar_banco.yml` (1 input) e `CLAUDE.md`. O `frontend/` **não lê nem tipa o bloco** —
   verificado por `grep` nesta sessão.
3. **É o terceiro rename do mesmo bloco em três features, e isso é o argumento para confirmar com o
   usuário, não para evitá-lo.** `cesta_basica` → `reducao_zero` → `reducao`. Os três foram
   forçados pelo mesmo motivo (o nome afirmava um escopo que o conteúdo passou a exceder) e
   `reducao` é o primeiro que não afirma escopo nenhum além do que a feature faz — é o nome que
   ainda vale quando os Anexos NBS (posição 14) chegarem.

**Alternatives Rejected:**

1. **Manter `reducao_zero` e acrescentar um bloco `reducao_percentual` irmão** — rejeitada: um item
   pertence a exatamente um dos dois, então metade dos itens teria um bloco vazio, e todo cliente
   precisaria olhar os dois para saber o que aconteceu. É o alias da feature anterior com outro
   nome.
2. **Manter `reducao_zero` com `percentual_reducao` dentro** — rejeitada pelo motivo 1.

---

### Decision 10: os 13 itens sem chave NCM do Anexo IX **não entram na tabela** — entram no cabeçalho da migração

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | MUST do DEFINE (itens NBS documentados, item 34 documentado à parte); AT-008 e AT-009 |

**Context:** Dos 35 itens do Anexo IX, 12 (itens 22 a 33) têm chave **NBS** (`1.1410.90.00`,
`1.1405.21.00`, …) e 1 (item 34, “Melhoramento genético de animais e plantas e biotecnologia,
inclusive seus royalties”) **não tem chave nenhuma** — a célula está vazia na fonte.

**Choice:** Nenhum dos 13 entra em `anexos_reducao`. Os 13 são transcritos **como comentário** no
cabeçalho da migração 010, com o código NBS de cada um, e a `fonte_legal` do resumo declara que os
itens 22-34 do Anexo IX não são resolvidos por esta simulação.

**Rationale:**

1. **A tabela é operacional: cada linha existe para casar com um código NCM.** Um item sem prefixo
   e sem sub-item já é recusado pela asserção herdada da Decisão 7 da feature anterior — inseri-los
   exigiria afrouxar uma asserção que existe para pegar `INSERT` truncado.
2. **O schema, por acaso, já os recusaria sozinho** — e isso é uma propriedade que vale registrar:
   um código NBS sem pontuação tem **9 dígitos** (`1.1410.90.00` → `114109000`), e a CHECK
   `prefixo_comprimento_valido` só admite `{2,4,5,6,7,8}`. Não existe transcrição “por engano” de
   NBS nesta tabela: o banco recusa.
3. **O item 34 é uma limitação de espécie diferente e fica separado.** “Chave errada para esta
   tabela” (NBS) e “nenhuma chave” não são o mesmo problema: o primeiro é resolvido pela posição 14
   do roadmap, o segundo não é resolvido por nenhuma, porque não há o que casar. Confundi-los faria
   a posição 14 nascer prometendo algo que não pode entregar.
4. **O catálogo no cabeçalho é o que impede a próxima leitura do zero.** Mesmo papel do catálogo de
   “exceto” da feature anterior: mostra que os 13 foram **considerados e descartados**, não
   esquecidos.

---

### Decision 11: o seed mora na migração, e a migração **prova a precedência escrita na lei**

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | Risco central: 389 linhas transcritas à mão (2,5× a feature anterior) |

**Context:** Mesma situação das três features anteriores, com o dobro do volume e um tipo de
armadilha novo: agora um erro de transcrição pode fazer um item de 60% **vencer** um de zero, o
que muda o número devido em vez de só a citação.

**Choice:** `INSERT` dentro da migração 010, com URL e data no cabeçalho, mais um bloco `DO $$ … $$`
final que **assere o resultado inteiro** e faz rollback de tudo se algo não bater:

| # | Asserção | O que pega |
|---|----------|------------|
| 1 | Contagem por Anexo (itens/prefixos) nos **10** | `INSERT` truncado; item esquecido |
| 2 | Inclusões/exceções no total: `508 / 32` (= 127+381 inclusões e 24+8 exceções) | exceção transcrita como inclusão |
| 3 | Toda exceção desce de uma inclusão do **mesmo item** (herdada) | “exceto” descritivo virado linha |
| 4 | Todo item sem prefixo tem ≥1 sub-item, e todo sub-item tem cabeçalho (herdada) | linha de prefixo perdida; cabeçalho esquecido |
| 5 | Comprimentos ⊆ `{2,4,5,6,7,8}` (herdada) | prova que a CHECK está ativa |
| 6 | **Nova:** para os itens 4, 5, 6, 14 e 15 do Anexo VII, toda inclusão de Anexo zero que se sobreponha tem prefixo **estritamente mais longo** | a remissão que a lei escreve deixaria de ser honrada pelo desempate genérico (Decisão 3) |
| 7 | **Nova:** todo item de `anexos_reducao` tem `anexo` no catálogo com o percentual esperado | (redundante com a FK e a CHECK — de propósito, prova que estão ativas) |

A asserção 6 escrita:

```sql
IF EXISTS (
    SELECT 1
    FROM anexos_reducao_ncm sete
    JOIN anexos_reducao_ncm zero_ ON zero_.prefixo LIKE sete.prefixo || '%'
    JOIN anexos_reducao izero
      ON izero.anexo = zero_.anexo AND izero.item = zero_.item
     AND izero.sub_item = zero_.sub_item
    JOIN anexos_reducao_catalogo czero ON czero.anexo = izero.anexo
    WHERE sete.anexo = 'VII' AND sete.item IN (4,5,6,14,15) AND sete.excecao IS FALSE
      AND zero_.excecao IS FALSE AND czero.percentual_reducao = 1
      AND length(zero_.prefixo) <= length(sete.prefixo)
) THEN
    RAISE EXCEPTION 'Anexo VII: a ressalva expressa aos Anexos I/XV deixou de ser '
        'honrada pelo desempate por especificidade — ver Decisão 3 do DESIGN';
END IF;
```

**Rationale:**

1. **A asserção 6 é a única que protege uma regra *jurídica* em vez de uma contagem.** As demais
   pegam erro de digitação; esta pega uma mudança de dado que tornaria a Decisão 3 inválida sem
   quebrar nada visível. Ela roda onde o dado entra (Cloud SQL), não só no CI.
2. **`LIKE … || '%'` sobre colunas da própria tabela** — validadas por CHECK como só-dígitos, sem
   nenhum dado de requisição. Mesma análise de segurança já feita na feature anterior.
3. **Contagens por Anexo, não globais**, para que a falha diga *onde*.

---

### Decision 12: as sobreposições viram **três** testes SQL, e nenhuma delas é proibida

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | `SHOULD` do DEFINE (verificação programática de overlap); `A-003` |

**Context:** A Decisão 12 da feature anterior era um teste que exigia **conjunto vazio** de
sobreposições entre Anexos. Com o achado 1, esse teste passaria a falhar em 117 pares — e a
resposta certa não é relaxá-lo para “ignorar”, é trocá-lo por três testes que descrevem o que existe.

**Choice:** Em `tests/test_reducao_db.py` (Postgres real do CI):

| Teste | Consulta | Espera |
|-------|----------|--------|
| A | Pares (zero, 60%) em que o prefixo zero é **mais curto** | **Exatamente** os 4 pares da Decisão 4, nominalmente |
| B | Pares (zero, 60%) em que os prefixos têm o **mesmo comprimento** | 35 pares, todos resolvidos a favor do zero pelo componente 2 |
| C | Sobreposição entre dois Anexos de **60%** | Só muda a citação, nunca o número — asserção de que o percentual dos dois lados é igual |
| D | Pares em que um item de **IV/V/VI** (condição de comprador) disputa com um de **VII/VIII/IX** | O de IV/V/VI vence **sempre** — senão o zero por comprador qualificado sumiria sem sintoma |

O teste A é o que importa: ele é a lista fechada da Decisão 4 executada. O teste D é o que impede a
Decisão 6 de depender de sorte.

**Rationale:**

1. **Sobreposição não é ilegal — a lei criou 117 delas.** Proibi-la faria o teste ser desligado no
   primeiro Anexo novo, que é o pior destino de um teste.
2. **A equivalência “prefixo contém prefixo ⇔ existe código comum” é exata**, então nenhum dos três
   precisa da tabela completa da NCM nem inventa códigos.
3. **O teste C é barato e cobre a classe mais chata de erro de transcrição**: um item do Anexo IX
   digitado com percentual do Anexo VIII não existiria (o percentual vem do catálogo), mas um
   prefixo digitado no Anexo errado apareceria aqui como sobreposição nova.

---

### Decision 13: ordem de aplicação e verificação — migrar, provar, deployar (herdada, com um caso a mais)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |
| **Resolve** | Consequência operacional do rename (Decisão 1) + modo de falha silencioso herdado |

**Context:** A API em produção consulta `anexos_reducao_zero_ncm`; a migração 009 renomeia. E, pela
degradação conservadora, um `GRANT` faltando ou um seed truncado **não** produzem erro: produzem
`CONSULTA_INDISPONIVEL` e a alíquota geral — a resposta de antes da feature. A feature “funciona”
(200, verde) sem fazer nada.

**Choice:** Ordem **009/010 → verificação → deploy**, com a janela declarada e aceita (durante ela a
API antiga cai no `except` e devolve 200 com a alíquota geral). A verificação é
`scripts/verificar_reducao_producao.py`, com o papel `taxreformai_app`, via `migrar_banco.yml`
(input renomeado para `verificar_reducao`), **15 casos** — os 7 herdados, que provam a
não-regressão, e 8 novos, um por mecanismo:

| Código | Espera | Prova |
|--------|--------|-------|
| `04051000` | APLICADA · I/5 · 100% | não-regressão (herdado) |
| `02074300` | EXCLUIDA_EXPRESSAMENTE · I/19 | exceção do Anexo I (herdado) |
| `09012100` | APLICADA · I/8 | prefixo de 4 (herdado) |
| `87131000` | APLICADA · XIII/2.1 · `descricao_contexto` não-nula | Anexo zero com sub-item (herdado) |
| `90181980` | APLICADA · XII/1.2 · 3 correspondentes | desempate intra-Anexo (herdado) |
| `90213991` | EXCLUIDA_EXPRESSAMENTE · XII/5 | exceção nos Anexos novos (herdado) |
| `06031100` | APLICADA · XV/4 · `tipo_correspondencia == "CAPITULO"` | Decisão 7 sobre dado já shipado |
| `34011190` | APLICADA · **VIII/1 · 60%** | AT-001 — o caminho novo, no caso mais simples |
| `90189099` | APLICADA · **XII/9 · 100%**, com IV/2 entre os correspondentes | os **35 empates** (Decisão 3, componente 2) |
| `06021000` | APLICADA · **IX/11 · 60%** | os **4 casos** em que 60% vence zero (Decisão 4) |
| `10063021` | APLICADA · **I/1 · 100%** | precedência do Anexo VII escrita na lei (AT-002) |
| `07095100` | APLICADA · **VII/14 · 60%**, com XV/2 em `itens_excluidos` | Decisão 8 |
| `11090000` | APLICADA · **IX/19 · 60% · CAPITULO** | múltiplos capítulos no mesmo item (AT-007) |
| `87089910` | APLICADA · **V/1.1 · 60%** · `descricao_contexto` · `zero_por_comprador_disponivel` | cabeçalho + condição de comprador não informada (AT-006, AT-010) |
| `87089910` **com** `comprador_tipo=ORGAO_PUBLICO` | APLICADA · **V/1.1 · 100%** · `dispositivo_legal_comprador == "LCP 214/2025, art. 145, II"` | Decisão 6 ponta a ponta |

Mais uma **quarta chamada** no smoke test do `deploy.yml`, com payload próprio de `ncm:
"34011190"`, exigindo `reducao.percentual_reducao == 60.00` e
`itens_detalhados[0].aliquotas_aplicadas.cbs_percentual == 0.36`.

**Rationale:**

1. **A janela existe nas duas ordens**, então a escolha é sobre *qual* degradação. Migrar primeiro
   é melhor porque `migrar_banco.yml` prova o estado final do banco **antes** de qualquer tráfego
   tocar o código novo.
2. **`0.36` no smoke test é a asserção que só o caminho novo satisfaz.** `cbs_percentual == 0`
   (zero) e `== 0.9` (sem redução) já existem hoje; `0.36` só aparece se a alíquota tiver sido
   reduzida em 60% de verdade, com a Decisão 5 implementada.
3. **Os dois casos de `87089910`** (com e sem comprador) são o único par em que a mesma entrada
   deve dar respostas diferentes — a prova de que o campo novo tem efeito e de que a ausência dele
   não vira default.

---
## Dados — os 6 Anexos transcritos (fonte primária, 2026-07-29)

> Transcrição literal das seis publicações citadas na seção de verificação, **extraída da estrutura
> `<tr>/<td>` da tabela do DOU**, não do texto renderizado. É **esta** tabela que o `/build` copia
> para a migração 010 — não a versão resumida do DEFINE, que difere em três pontos verificados
> (contagem do Anexo V, comprimento de 13 códigos do Anexo IV, contagem do item 7 do Anexo IX).
>
> Notação: `texto_ncm` (grafia do DOU) → `prefixo` (dígitos). Linhas de exceção marcadas com **✗**.
> `dispositivo_legal_ref` de cada Anexo indicado no cabeçalho da sua seção.
>
> **Regra de transcrição que vale para os seis:** `descricao` é o texto **literal** da célula do
> DOU, com a grafia dela — inclusive as que parecem erro de digitação do próprio Diário
> (“Fórmula para dieta isenta **demetionina**”, Anexo VI, item 40; “( *clamps* )” com espaços e
> itálico, Anexo IV, item 57). Corrigir a fonte é editorializar um documento de auditoria.

### Anexo IV — Dispositivos médicos · art. 131 (+ art. 144, II para o comprador)

`dispositivo_legal_ref`: `LCP 214/2025, art. 131, Anexo IV, item N`

**105 itens · 112 linhas de prefixo · nenhuma exceção.** 6 itens citam mais de um código (12, 37,
42, 48, 68, 102) e **13 códigos não são de 8 dígitos** (achado 3): `3917.40`, `3006.10`, `3822.1`,
`4015.1`, `9018.31`, `9018.32`, `9018.39.2`, `9018.39.9`, `9018.49.1`, `9402.90`, `9027.30`,
`9027.90.9`.

| item | descricao | texto_ncm → prefixo |
|---|---|---|
| 1 | Bolsa para drenagem | `3926.90.30`→39269030 |
| 2 | Sistema para drenagem com conjunto intermediário para medição contínua da diurese | `9018.90.99`→90189099 |
| 3 | Chapas e filmes para raios-X, sensibilizados em uma face | `3701.10.10`→37011010 |
| 4 | Cimentos para reconstituição óssea | `3006.40.20`→30064020 |
| 5 | Substitutos de enxerto ósseo | `3004.90.99`→30049099 |
| 6 | Coletor para unidade de drenagem externa | `3926.90.40`→39269040 |
| 7 | Conector completo com tampa | `3917.40`→391740 |
| 8 | Conector em Y | `3917.40`→391740 |
| 9 | Conjuntos de troca e concentrados polieletrolíticos para diálise | `3004.90.99`→30049099 |
| 10 | Conjunto para autotransfusão | `9018.90.10`→90189010 |
| 11 | Conjunto para hidrocefalia de baixo perfil | `9021.90.19`→90219019 |
| 12 | Conjunto para hidrocefalia standard | `9021.90.19`→90219019 · `9021.90.80`→90219080 |
| 13 | Eletrodo endocárdico definitivo | `9021.90.91`→90219091 |
| 14 | Eletrodo epicárdico definitivo | `9021.90.91`→90219091 |
| 15 | Eletrodo para marcapasso temporário endocárdico | `9021.90.91`→90219091 |
| 16 | Eletrodo para marcapasso temporário epicárdico | `9021.90.91`→90219091 |
| 17 | Espaçador de tendão | `9021.90.19`→90219019 |
| 18 | Filmes especiais para raios-X sensibilizados em ambas as faces | `3702.10.20`→37021020 |
| 19 | Filmes especiais para raios-X sensibilizados em uma face | `3702.10.10`→37021010 |
| 20 | Filtro de linha arterial e venoso | `8421.29.90`→84212990 |
| 21 | Filtro de sangue arterial e venoso para recirculação | `8421.29.90`→84212990 |
| 22 | Filtro para cardioplegia | `8421.29.90`→84212990 |
| 23 | Categutes esterilizados, materiais esterilizados semelhantes para suturas cirúrgicas (incluídos os fios absorvíveis esterilizados para cirurgia ou odontologia) e adesivos esterilizados para tecidos orgânicos, utilizados em cirurgia para fechar ferimentos; laminárias esterilizadas; hemostáticos absorvíveis esterilizados para cirurgia ou odontologia; barreiras antiaderentes esterilizadas para cirurgia ou odontologia, absorvíveis ou não | `3006.10`→300610 |
| 24 | Hemoconcentrador para circulação extracorpórea | `9018.90.40`→90189040 |
| 25 | Hemodialisador capilar | `8421.29.11`→84212911 |
| 26 | Marcapasso cardíaco câmara dupla | `9021.50.00`→90215000 |
| 27 | Marcapasso cardíaco multiprogramável com telemetria | `9021.50.00`→90215000 |
| 28 | Outras chapas e filmes para raios-X | `3701.10.29`→37011029 |
| 29 | Oxigenador de bolha com tubos para circulação extracorpórea | `9018.90.99`→90189099 |
| 30 | Oxigenador de membrana com tubos para circulação extracorpórea | `9018.90.99`→90189099 |
| 31 | Reservatório de cardiotomia | `9018.90.99`→90189099 |
| 32 | Reservatório para cardioplegia com tubo sem filtro | `9018.90.99`→90189099 |
| 33 | Rins artificiais | `9018.90.40`→90189040 |
| 34 | Shunt lombo-peritonal | `9021.90.19`→90219019 |
| 35 | Substituto temporário de pele (biológica/sintética) (por cm2) | `3005.90.90`→30059090 |
| 36 | Tela inorgânica | `3006.10.90`→30061090 |
| 37 | Válvula para hidrocefalia | `9021.90.19`→90219019 · `9021.90.89`→90219089 |
| 38 | Válvula para tratamento de ascite | `9021.90.19`→90219019 |
| 39 | Fonte de irídio 192 | `2844.43.90`→28444390 |
| 40 | Stent vascular | `9021.90.12`→90219012 |
| 41 | Reprocessador de filtros utilizados em hemodiálise | `8479.89.99`→84798999 |
| 42 | Implantes osseointegráveis, na forma de parafuso, e seus componentes manufaturados, tais como tampas de proteção, montadores, conjuntos, pilares (cicatrizador, conector, de transferência ou temporário), cilindros, seus acessórios, destinados a sustentar, amparar, acoplar ou fixar próteses dentárias | `9021.29.00`→90212900 · `9021.10.10`→90211010 · `9021.10.20`→90211020 |
| 43 | Cardiodesfibrilador implantável | `9021.90.11`→90219011 |
| 44 | Espiral para embolização | `9021.90.12`→90219012 |
| 45 | Imunoglobulina anti-Rh | `3002.12.21`→30021221 |
| 46 | Outras imunoglobulinas séricas | `3002.12.22`→30021222 |
| 47 | Concentrado de fator VIII | `3002.12.23`→30021223 |
| 48 | Outras frações do sangue, exceto as preparadas como medicamentos, as imunoglobulinas séricas, o concentrado de fator VIII e a soroalbumina sob a forma de gel para preparação de reagentes de diagnóstico | `3002.12.21`→30021221 · `3002.12.29`→30021229 |
| 49 | Reagentes de diagnóstico ou de laboratório em qualquer suporte e reagentes de diagnóstico ou de laboratório preparados, mesmo em um suporte, mesmo apresentados sob a forma de estojos, exceto os da posição 30.06; materiais de referência certificados | `3822.1`→38221 |
| 50 | Reagentes de diagnóstico concebidos para serem administrados ao paciente, à base de somatoliberina | `3006.30.21`→30063021 |
| 51 | Produtos para obturação dentária, exceto cimentos | `3006.40.12`→30064012 |
| 52 | Preparações em gel, concebidas para uso em medicina humana ou veterinária como lubrificante para certas partes do corpo em intervenções cirúrgicas ou exames médicos ou como agente de ligação entre o corpo e os instrumentos médicos | `3006.70.00`→30067000 |
| 53 | Bolsas para uso em colostomia, ileostomia e urostomia | `3006.91.10`→30069110 |
| 54 | Equipamentos identificáveis para ostomia, exceto bolsas para uso em colostomia, ileostomia e urostomia | `3006.91.90`→30069190 |
| 55 | Bolsas para uso em medicina (hemodiálise e usos semelhantes) | `3926.90.30`→39269030 |
| 56 | Artigos exclusivamente de laboratório de análises clínicas | `3926.90.40`→39269040 |
| 57 | Acessórios de plástico do tipo utilizado em linhas de sangue para hemodiálise, tais como: obturadores, incluídos os reguláveis (clamps), clipes e similares | `3926.90.50`→39269050 |
| 58 | Luvas cirúrgicas e luvas de procedimento | `4015.1`→40151 |
| 59 | Seringas, mesmo com agulhas | `9018.31`→901831 |
| 60 | Agulhas tubulares de metal e agulhas para suturas | `9018.32`→901832 |
| 61 | Agulhas, exceto as de metal e as para suturas | `9018.39.10`→90183910 |
| 62 | Sondas, cateteres e cânulas, individualmente ou em conjunto | `9018.39.2`→9018392 |
| 63 | Lancetas para vacinação e cautérios | `9018.39.30`→90183930 |
| 64 | Instrumentos semelhantes a seringas, a agulhas, a cateteres e a cânulas | `9018.39.9`→9018399 |
| 65 | Brocas para odontologia | `9018.49.1`→9018491 |
| 66 | Limas | `9018.49.20`→90184920 |
| 67 | Grampos e clipes, seus aplicadores e extratores | `9018.90.95`→90189095 |
| 68 | Outros instrumentos e aparelhos para medicina, cirurgia e odontologia, excluídas seringas e agulhas, das posições 9018.31 e 9018.32 | `9018.39.99`→90183999 · `9018.90.99`→90189099 |
| 69 | Mesas de operação e para exames, camas hospitalares e de uso clínico | `9402.90`→940290 |
| 70 | Fotocoagulador a laser | `9018.20.10`→90182010 |
| 71 | Bisturi elétrico | `9018.90.21`→90189021 |
| 72 | Aparelho de anestesia com monitor multiparâmetros | `9018.90.99`→90189099 |
| 73 | Autoclave | `8419.81.10`→84198110 |
| 74 | Retinógrafo | `9018.50.90`→90185090 |
| 75 | Meios de cultura | `3821.00.00`→38210000 |
| 76 | Termocicladores utilizados em diagnóstico e na pesquisa científica | `8419.89.99`→84198999 |
| 77 | Partes e peças de termocicladores | `8419.90.40`→84199040 |
| 78 | Pipetadores laboratoriais para diagnóstico e pesquisa científica | `8479.89.12`→84798912 |
| 79 | Cromatógrafo de fase líquida | `9027.20.12`→90272012 |
| 80 | Sequenciadores automáticos de ADN mediante eletroforese capilar | `9027.20.21`→90272021 |
| 81 | Aparelhos de eletroforese para diagnóstico e pesquisa científica | `9027.20.29`→90272029 |
| 82 | Analisadores por espectrofotometria para diagnóstico e pesquisa científica | `9027.30`→902730 |
| 83 | Analisadores por fotometria para diagnóstico e pesquisa científica | `9027.50.20`→90275020 |
| 84 | Citômetro de fluxo | `9027.50.50`→90275050 |
| 85 | Analisadores por radiações ópticas para diagnóstico e pesquisa científica | `9027.50.90`→90275090 |
| 86 | Outros analisadores para diagnóstico e pesquisa científica | `9027.89.99`→90278999 |
| 87 | Espectrômetro de massa | `9027.81.00`→90278100 |
| 88 | Outros analisadores para diagnóstico | `9027.89.99`→90278999 |
| 89 | Micrótomo | `9027.90.10`→90279010 |
| 90 | Partes e peças de equipamentos analisadores laboratoriais | `9027.90.9`→9027909 |
| 91 | Preservativo | `4014.10.00`→40141000 |
| 92 | Dispositivo intrauterino (DIU) | `9018.90.99`→90189099 |
| 93 | Substância para conservação de órgãos e tecidos | `3824.99.89`→38249989 |
| 94 | Introdutor de punção para implante de eletrodo endocárdico | `9021.90.91`→90219091 |
| 95 | Enxerto tubular de politetrafluoretileno - PTFE (por cm2) | `9021.90.99`→90219099 |
| 96 | Enxerto arterial e venoso tubular inorgânico | `9021.90.99`→90219099 |
| 97 | Botão para crânio | `9021.90.99`→90219099 |
| 98 | Guia metálico para introdução de cateter duplo lumen | `9018.39.29`→90183929 |
| 99 | Dilatador para implante de cateter duplo lumen | `9018.39.29`→90183929 |
| 100 | Guia de troca para angioplastia | `9018.39.29`→90183929 |
| 101 | Introdutor para cateter com e sem válvula | `9018.39.29`→90183929 |
| 102 | Kit cânula | `9018.39.99`→90183999 · `9018.39.91`→90183991 |
| 103 | Dreno para sucção | `9018.39.29`→90183929 |
| 104 | Sistema de drenagem mediastinal | `9018.39.29`→90183929 |
| 105 | Conjunto descartável de balão intra-aórtico | `9018.90.99`→90189099 |

### Anexo V — Acessibilidade · art. 132 (+ art. 145, II para o comprador)

`dispositivo_legal_ref`: `LCP 214/2025, art. 132, Anexo V, item N[.M]`

**29 itens** (3 cabeçalhos sem NCM + 26 sub-itens — corrige o DEFINE, que contava 26 no total) ·
**30 linhas de prefixo** · nenhuma exceção. Estrutura idêntica à do Anexo XIII já shipado (Decisão
7 de lá): os itens 1, 2 e 3 são cabeçalhos, e sem eles a `descricao` de 1.1 (“Comando de embreagem
manual, suas partes e acessórios”) perde o sujeito (“…para veículos automotores destinados a
pessoas com deficiência física”). Um único prefixo curto: `8517.1` (item 3.1).

| item | sub | descricao | texto_ncm → prefixo |
|---|---|---|---|
| 1 | 0 | ACESSÓRIOS E ADAPTAÇÕES ESPECIAIS PARA SEREM INSTALADOS EM VEÍCULOS AUTOMOTORES PERTENCENTES OU QUE FOREM DESTINADOS A PESSOAS COM DEFICIÊNCIA FÍSICA | *(cabeçalho — nenhuma linha)* |
| 1 | 1 | Comando de embreagem manual, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 2 | Comando de freio manual, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 3 | Comando de acelerador manual, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 4 | Inversão do pedal do acelerador, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 5 | Prolongamento de pedais, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 6 | Empunhadura, suas partes e acessórios | `8708.29.99`→87082999 |
| 1 | 7 | Servo acionadores de volante, suas partes e acessórios | `8708.99.10`→87089910 |
| 1 | 8 | Deslocamento de comandos do painel, suas partes e acessórios | `8708.29.99`→87082999 |
| 1 | 9 | Plataforma giratória para deslocamento giratório do assento de veículo, suas partes e acessórios | `8708.29.99`→87082999 |
| 1 | 10 | Trilho elétrico para deslocamento do assento dianteiro para outra parte do interior do veículo, suas partes e acessórios | `8708.29.99`→87082999 |
| 1 | 11 | Plataforma de elevação para cadeira de rodas, manual, eletro-hidráulica ou eletromecânica | `8428.90.90`→84289090 |
| 1 | 12 | Rampa para cadeira de rodas, suas partes e acessórios | `8708.29.99`→87082999 |
| 1 | 13 | Guincho para transportar cadeira de rodas | `8425.31.10`→84253110 |
| 2 | 0 | PRODUTOS DESTINADOS A USO DE PESSOA COM DEFICIÊNCIA VISUAL | *(cabeçalho — nenhuma linha)* |
| 2 | 1 | Bengala inteiriça, dobrável ou telescópica, com ponteira de náilon | `6602.00.00`→66020000 |
| 2 | 2 | Relógio em braille, com sintetizador de voz e mostrador ampliado | `9102.11.10`→91021110 · `9102.11.90`→91021190 · `9102.91.00`→91029100 |
| 2 | 3 | Termômetro digital com sistema de voz | `9025.19.90`→90251990 |
| 2 | 4 | Calculadora digital com sistema de voz, com verbalização dos ajustes de minutos e horas, tanto no modo horário, como no modo alarme, e comunicação por voz dos dígitos de cálculo e resultados | `8470.10.00`→84701000 · `8470.29.00`→84702900 |
| 2 | 5 | Agenda eletrônica com teclado em braille, com ou sem sintetizador de voz | `8543.70.99`→85437099 |
| 2 | 6 | Reglete para escrita em braille | `9017.20.00`→90172000 |
| 2 | 7 | Display braille e teclado em Braille para uso em microcomputador, com sistema interativo para introdução e leitura de dados por meio de tabelas de caracteres Braille | `8471.60.90`→84716090 |
| 2 | 8 | Máquina de escrever para escrita em braille, manual ou elétrica, com teclado de datilografia comum ou na formação Braille | `8472.90.99`→84729099 |
| 2 | 9 | Impressora de caracteres em braille para uso com microcomputadores, com sistema de folha solta ou dois lados da folha, com ou sem sistema de comando de voz ou sistema acústico | `8443.32.22`→84433222 |
| 2 | 10 | Equipamento sintetizador para reprodução em voz de sinais gerados por microcomputadores, permitida a leitura de dados de arquivos, de uso interno ou externo, com padrão de protocolo SSIL de interface com softwares leitores de tela | `8471.80.00`→84718000 |
| 3 | 0 | PRODUTOS DESTINADOS AO USO DE PESSOAS COM DEFICIÊNCIA AUDITIVA | *(cabeçalho — nenhuma linha)* |
| 3 | 1 | Aparelho telefônico com teclado alfanumérico e visor luminoso, com ou sem impressora embutida, que permite converter sinais transmitidos por sistema telefônico em caracteres e símbolos | `8517.1`→85171 |
| 3 | 2 | Relógio despertador vibratório e/ou luminoso | `9103.10.00`→91031000 · `9105.11.00`→91051100 |
| 3 | 3 | Unidades de entrada de dados tipo mouse controláveis pelo movimento dos olhos para deficientes | `8471.60.53`→84716053 |

### Anexo VI — Nutrição enteral/parenteral · art. 133, § 1º (+ art. 146, § 2º para o comprador)

`dispositivo_legal_ref`: `LCP 214/2025, art. 133, § 1º, Anexo VI, item N`

**81 itens · 86 linhas · todos de 8 dígitos · nenhuma exceção** — o mais simples dos seis nessa
dimensão, e o segundo maior em volume. 5 itens citam 2 códigos (26, 27, 29, 67, 81).

**Atenção do `/build` ao dispositivo:** é `art. 133, § 1º`, **não** `art. 133` (achado 5) — o caput
do art. 133 trata dos medicamentos em geral e não menciona o Anexo VI.

| item | descricao | texto_ncm → prefixo |
|---|---|---|
| 1 | Acetato de dextroalfatocoferol | `2936.28.12`→29362812 |
| 2 | Acetato de lisina | `2922.41.90`→29224190 |
| 3 | Acetato de potássio | `2915.29.90`→29152990 |
| 4 | Acetato de sódio | `2915.29.10`→29152910 |
| 5 | Acetato de zinco | `2915.29.90`→29152990 |
| 6 | Acetiltirosina | `2922.50.39`→29225039 |
| 7 | Ácido acético | `2915.21.00`→29152100 |
| 8 | Ácido ascórbico | `2936.27.10`→29362710 |
| 9 | Ácido aspártico | `2922.49.90`→29224990 |
| 10 | Ácido cítrico | `2918.14.00`→29181400 |
| 11 | Ácido fólico | `2936.29.11`→29362911 |
| 12 | Ácido glutâmico | `2922.42.10`→29224210 |
| 13 | Ácido málico | `2918.19.90`→29181990 |
| 14 | Ácido selenioso | `2811.19.90`→28111990 |
| 15 | Água para injeção | `2002.10.00`→20021000 |
| 16 | Alanilglutamina | `2922.49.90`→29224990 |
| 17 | Alanina | `2922.49.90`→29224990 |
| 18 | Albumina humana | `3002.12.36`→30021236 |
| 19 | Arginina | `2925.29.19`→29252919 |
| 20 | Asparagina | `2922.49.90`→29224990 |
| 21 | Bicarbonato de sódio | `2836.30.00`→28363000 |
| 22 | Biotina | `2936.29.31`→29362931 |
| 23 | Cianocobalamina | `2936.26.10`→29362610 |
| 24 | Cistina | `2930.90.39`→29309039 |
| 25 | Cloreto crômico | `2827.39.93`→28273993 |
| 26 | Cloreto de cálcio | `2827.20.10`→28272010 · `2827.20.90`→28272090 |
| 27 | Cloreto de magnésio | `2827.31.10`→28273110 · `2827.31.90`→28273190 |
| 28 | Cloreto de manganês | `2827.39.95`→28273995 |
| 29 | Cloreto de potássio | `3104.20.10`→31042010 · `3104.20.90`→31042090 |
| 30 | Cloreto de sódio | `2501.00.90`→25010090 |
| 31 | Cloreto de zinco | `2827.39.98`→28273998 |
| 32 | Cloridrato de piridoxina | `2936.25.20`→29362520 |
| 33 | Cloridrato de tiamina | `2936.22.10`→29362210 |
| 34 | Cocarboxilase | `2936.22.90`→29362290 |
| 35 | Colecalciferol | `2936.29.21`→29362921 |
| 36 | Ergocalciferol | `2936.29.29`→29362929 |
| 37 | Fenilalanina | `2922.49.90`→29224990 |
| 38 | Fitomenadiona | `2936.29.40`→29362940 |
| 39 | Fórmula para dieta isenta de fenilalanina | `2106.90.90`→21069090 |
| 40 | Fórmula para dieta isenta demetionina | `2106.90.90`→21069090 |
| 41 | Fórmula para dieta isenta de lisina e pobre de triptofano | `2106.90.90`→21069090 |
| 42 | Fórmula para dieta isenta de leucina, de isoleucina ou de valina | `2106.90.90`→21069090 |
| 43 | Fórmula para dieta isenta de fenilalanina e de metionina | `2106.90.90`→21069090 |
| 44 | Fórmula para dieta isenta de aminoácidos não essenciais | `2106.90.90`→21069090 |
| 45 | Fórmula para dieta isenta de metionina, de treonina, de valina e restrita de isoleucina | `2106.90.90`→21069090 |
| 46 | Fórmula para dieta cetogênica, na proporção de 4 g de gordura para cada 1 g de carboidratos e proteínas | `2106.90.90`→21069090 |
| 47 | Fórmula hiperlipídica, para suplementação de triglicerídios de cadeia média ou triheptanoína | `2202.99.00`→22029900 |
| 48 | Preparação líquida, de quatro partes de trioleato de glicerol de ácido para uma parte de trierucato de glicerol | `2202.99.00`→22029900 |
| 49 | Fosfato de potássio dibásico | `2835.24.00`→28352400 |
| 50 | Fosfato de potássio monobásico | `2835.24.00`→28352400 |
| 51 | Fosfato de sódio monobásico | `2835.22.00`→28352200 |
| 52 | Fosfato de tiamina | `2936.22.90`→29362290 |
| 53 | Fosfato sódico de riboflavina | `2936.23.20`→29362320 |
| 54 | Frutose | `1702.50.00`→17025000 |
| 55 | Glicerofosfato de sódio | `2919.90.90`→29199090 |
| 56 | Glicina | `2922.49.10`→29224910 |
| 57 | Gliconato de cálcio | `2918.16.10`→29181610 |
| 58 | Glicose | `1702.30.11`→17023011 |
| 59 | Histidina | `2933.29.92`→29332992 |
| 60 | Icodextrina | `3505.10.00`→35051000 |
| 61 | Iodeto de potássio | `2827.60.12`→28276012 |
| 62 | Isoleucina | `2922.49.90`→29224990 |
| 63 | Lecitina de ovo | `2923.20.00`→29232000 |
| 64 | Leucina | `2922.49.90`→29224990 |
| 65 | Levovalina | `2922.49.90`→29224990 |
| 66 | Lisina | `2922.41.10`→29224110 |
| 67 | Metionina | `2930.40.10`→29304010 · `2930.40.90`→29304090 |
| 68 | Nicotinamida | `2936.29.52`→29362952 |
| 69 | Palmitato de retinol | `2936.21.13`→29362113 |
| 70 | Prolina | `2922.49.90`→29224990 |
| 71 | Riboflavina | `2936.23.10`→29362310 |
| 72 | Selenito de sódio | `2842.90.00`→28429000 |
| 73 | Serina | `2922.50.99`→29225099 |
| 74 | Sorbitol | `2905.44.00`→29054400 |
| 75 | Sulfato de magnésio | `2833.21.00`→28332100 |
| 76 | Sulfato de zinco | `2833.29.70`→28332970 |
| 77 | Taurina | `2922.49.90`→29224990 |
| 78 | Tirosina | `2922.50.39`→29225039 |
| 79 | Tocoferol | `2936.28.11`→29362811 |
| 80 | Treonina | `2922.50.99`→29225099 |
| 81 | Triglicerídeos de cadeia média | `1513.19.00`→15131900 · `1513.29.11`→15132911 |

### Anexo VII — Alimentos destinados ao consumo humano · art. 135

`dispositivo_legal_ref`: `LCP 214/2025, art. 135, Anexo VII, item N`

**17 itens · 53 linhas = 45 inclusões + 8 exceções** — o único dos seis com exceção operante, o
único com alínea, e o que carrega a remissão expressa aos Anexos zero. Tabela de **2 colunas**
(ITEM · DESCRIÇÃO DO PRODUTO): os códigos vêm embutidos na prosa, como no Anexo XV.

| item | alínea | `descricao` (literal, resumida aqui — o `/build` copia a célula inteira) | `texto_ncm` → `prefixo` |
|---|---|---|---|
| 1 | a | Crustáceos (exceto lagostas e lagostim) e moluscos dos seguintes códigos e subposições da NCM/SH: a) 0306.1 e 0306.3, exceto os produtos da subposição 0306.11 e dos códigos 0306.15.00, 0306.31.00, 0306.34.00, 0306.39.10; e b) 0307.31.00, 0307.32.00, 0307.42.00, 0307.43, 0307.51.00, 0307.52.00, 0307.91.00 e 0307.92.00 | `0306.1`→03061 · `0306.3`→03063 · ✗`0306.11`→030611 · ✗`0306.15.00`→03061500 · ✗`0306.31.00`→03063100 · ✗`0306.34.00`→03063400 · ✗`0306.39.10`→03063910 |
| 1 | b | *(mesma célula, alínea b)* | `0307.31.00`→03073100 · `0307.32.00`→03073200 · `0307.42.00`→03074200 · `0307.43`→030743 · `0307.51.00`→03075100 · `0307.52.00`→03075200 · `0307.91.00`→03079100 · `0307.92.00`→03079200 |
| 2 | — | Leite fermentado, bebidas e compostos lácteos, em conformidade com os requisitos da legislação específica, classificados nos códigos 0403.20.00, 0403.90.00 e 2202.99.00 da NCM/SH | `0403.20.00`→04032000 · `0403.90.00`→04039000 · `2202.99.00`→22029900 |
| 3 | — | Mel natural do código 0409.00.00 da NCM/SH | `0409.00.00`→04090000 |
| 4 | — | Farinha das posições 1101.00, 11.02, 11.05, 11.06 e 12.08 da NCM/SH; ressalvados os produtos relacionados no Anexo I | `1101.00`→110100 · `11.02`→1102 · `11.05`→1105 · `11.06`→1106 · `12.08`→1208 |
| 5 | — | Grumos e sêmolas de cereais dos códigos 1103.11.00 e 1103.19.00 da NCM/SH; ressalvados os produtos relacionados no Anexo I | `1103.11.00`→11031100 · `1103.19.00`→11031900 |
| 6 | — | Grãos de cereais das subposições 1104.1 e 1104.2 da NCM/SH; ressalvados os produtos relacionados no Anexo I | `1104.1`→11041 · `1104.2`→11042 |
| 7 | — | Amido de milho do código 1108.12.00 da NCM/SH | `1108.12.00`→11081200 |
| 8 | — | Óleos de soja, de milho, canola e demais óleos vegetais, em conformidade com os requisitos da legislação específica relativos ao consumo como alimento, classificados na subposição 1507.90 e nas posições 15.08, 15.11, 15.12, 15.13, 15.14 e 15.15 da NCM/SH | `1507.90`→150790 · `15.08`→1508 · `15.11`→1511 · `15.12`→1512 · `15.13`→1513 · `15.14`→1514 · `15.15`→1515 |
| 9 | — | Massas alimentícias dos códigos 1902.20.00 e 1902.30.00 da NCM/SH | `1902.20.00`→19022000 · `1902.30.00`→19023000 |
| 10 | — | Sucos naturais de fruta ou de produtos hortícolas sem adição de açúcar ou de outros edulcorantes e sem conservantes classificados na posição 20.09 da NCM/SH | `20.09`→2009 |
| 11 | — | Polpas de frutas ou de produtos hortícolas sem adição de açúcar ou de outros edulcorantes e sem conservantes classificadas na posição 20.08 da NCM/SH | `20.08`→2008 |
| 12 | — | Pão de Forma do código 1905.90.10 da NCM/SH | `1905.90.10`→19059010 |
| 13 | — | Extrato de tomate classificado no código 2002.90.00 da NCM/SH | `2002.90.00`→20029000 |
| 14 | — | Frutas, produtos hortícolas e demais produtos vegetais, sem adição de açúcar ou de outros edulcorantes, classificados nos capítulos 7 e 8 da NCM/SH, ressalvados as frutas de casca rija não regionais e os produtos relacionados nos Anexos I e XV e excetuadas as posições 07.11, 08.12 e 0814.00.00 | `07`→07 **(capítulo)** · `08`→08 **(capítulo)** · ✗`07.11`→0711 · ✗`08.12`→0812 · ✗`0814.00.00`→08140000 |
| 15 | — | Cereais do capítulo 10 e sementes e frutos oleaginosos classificados no capítulo 12, ambos da NCM/SH, ressalvados os produtos relacionados no Anexo I | `10`→10 **(capítulo)** · `12`→12 **(capítulo)** |
| 16 | — | Produtos hortícolas, mesmo misturados entre si, apenas pré-cozidos ou cozidos em água ou vapor, sem adição de sal ou de quaisquer outros produtos e substâncias, classificados nas posições 20.04 e 20.05 e no código 2002.10.00 da NCM/SH | `20.04`→2004 · `20.05`→2005 · `2002.10.00`→20021000 |
| 17 | — | Fruta de casca rija regional, amendoins e outras sementes, mesmo misturados entre si, apenas torrados ou cozidos, sem adição de sal ou de quaisquer outros produtos e substâncias, classificados na subposição 2008.1 da NCM/SH | `2008.1`→20081 |

**O item 2 é o alvo do veto da LC 227/2026** (achado 7): o texto acima é o **original**, que
permanece vigente porque a nova redação foi **integralmente vetada**. O `/build` transcreve este, e
o cabeçalho da migração registra o porquê.

**As 8 exceções são todas OPERANTES** (cada uma desce de uma inclusão do mesmo item): `030611`,
`03061500`, `03063100`, `03063400`, `03063910` descem de `03061`/`03063`; `0711`/`0812` descem de
`07`/`08`; `08140000` desce de `08`.

### Anexo VIII — Higiene pessoal e limpeza · art. 136

`dispositivo_legal_ref`: `LCP 214/2025, art. 136, Anexo VIII, item N`

**7 itens · 7 linhas · todos de 8 dígitos · nenhuma exceção** — o menor e mais simples dos seis, e
por isso o caso do AT-001 e do smoke test de produção.

| item | `descricao` (literal) | `texto_ncm` → `prefixo` |
|---|---|---|
| 1 | Sabões de toucador classificados no código 3401.11.90 da NCM/SH | `3401.11.90`→34011190 |
| 2 | Dentifrícios do código 3306.10.00 da NCM/SH | `3306.10.00`→33061000 |
| 3 | Escovas de dentes do código 9603.21.00 da NCM/SH | `9603.21.00`→96032100 |
| 4 | Papel higiênico do código 4818.10.00 da NCM/SH | `4818.10.00`→48181000 |
| 5 | Água sanitária classificada no código 3808.94.19 da NCM/SH | `3808.94.19`→38089419 |
| 6 | Sabões em barra classificados no código 3401.19.00 da NCM/SH | `3401.19.00`→34011900 |
| 7 | Fraldas e artigos higiênicos semelhantes, de qualquer matéria classificadas no código 9619.00.00 da NCM/SH | `9619.00.00`→96190000 |

**Achado do item 7, que vira limitação declarada:** o **art. 147** (fora de qualquer Anexo, portanto
fora da tabela) reduz a **zero** tampões, absorventes, calcinhas absorventes e coletores menstruais —
todos no **mesmo código `9619.00.00`**. Dois produtos diferentes, um código só, duas alíquotas
diferentes: indecidível a partir da NCM. Esta feature aplica 60% (over-tributa o absorvente, na
direção segura) e declara. Ver “Limitações declaradas”, item 4.

### Anexo IX — Insumos agropecuários e aquícolas · art. 138

`dispositivo_legal_ref`: `LCP 214/2025, art. 138, Anexo IX, item N`

**22 itens em escopo · 101 linhas · nenhuma exceção operante.** Cabeçalho oficial de coluna: “NBS /
NCM/SH”. Dos 35 itens do DOU, 12 têm chave NBS (22-33) e 1 não tem chave nenhuma (34) — os 13 ficam
fora da tabela (Decisão 10).

Densidade sem precedente no projeto: o **item 7 cita 29 códigos** (não 28, achado 2) misturando
comprimentos 4, 5, 6, 7 e 8; o item 8 cita 18. **9 prefixos de capítulo** em 5 itens.

| item | `descricao` (literal) | `texto_ncm` → `prefixo` |
|---|---|---|
| 1 | Biofertilizantes, em conformidade com as definições e demais requisitos da legislação específica | `3101.00.00`→31010000 |
| 2 | Fertilizantes (adubos), em conformidade com as definições e demais requisitos da legislação específica | `31`→31 **(capítulo)** · `3824.99.77`→38249977 · `3824.99.79`→38249979 · `3824.99.89`→38249989 |
| 3 | Corretivos de solo (inclusive condicionadores), remineralizadores e substratos para plantas; em conformidade com as definições e demais requisitos da legislação específica | `25`→25 **(capítulo)** |
| 4 | Inoculantes, meios de cultura e outros microorganismos para uso agrícola; em conformidade com as definições e demais requisitos da legislação específica | `3002.49`→300249 · `3002.90.00`→30029000 · `3821.00.00`→38210000 |
| 5 | Bioestimulantes e bioinsumos para controle fitossanitário, em conformidade com as definições e demais requisitos da legislação específica | `38.24`→3824 · `3807.00.00`→38070000 · `12.11`→1211 · `38.08`→3808 |
| 6 | Inseticidas, fungicidas, formicidas, herbicidas, parasiticidas, germicidas, acaricidas, nematicidas, raticidas, desfolhantes, dessecantes, espalhantes adesivos, estimuladores e inibidores de crescimento (reguladores); todos destinados diretamente ao uso agropecuário ou destinados diretamente à fabricação de defensivo agropecuário; em conformidade com as definições e demais requisitos da legislação específica | `38.08`→3808 · `3824.99.89`→38249989 |
| 7 | Calcário, casca de coco triturada, turfa; tortas, bagaços e demais resíduos e desperdícios vegetais das indústrias alimentares; cascas, serragens e demais resíduos e desperdícios de madeira; resíduos da indústria de celulose (dregs e grits), ossos, borra de carnaúba, cinzas, resíduos agroindustriais orgânicos, DL-Metionina e seus análogos, vermiculita e argilas expandidas, palhas e cascas de produtos vegetais, fibra de coco e outras fibras vegetais, silicatos de potássio ou de magnésio, resinas e oleorresinas naturais, sucos e extratos vegetais, aminoácidos e microrganismos mortos, óleos essenciais, argilas e terras, carvão vegetal e pastas mecânicas de madeira; todos destinados diretamente à fabricação de biofertilizantes, fertilizantes, corretivos de solo (inclusive condicionadores), remineralizadores, substratos para plantas, bioestimulantes ou biodefensivos para controle fitossanitário ou utilizados diretamente como biofertilizantes, fertilizantes, corretivos de solo (inclusive condicionadores), remineralizadores, substratos para plantas, bioestimulantes ou biodefensivos para controle fitossanitário; em conformidade com as definições e demais requisitos da legislação específica | `05.06`→0506 · `1201.10.00`→12011000 · `1213.00.00`→12130000 · `1301.90.90`→13019090 · `1302.19.9`→1302199 · `1401.90.00`→14019000 · `1404.90.90`→14049090 · `2102.20.00`→21022000 · `23.02`→2302 · `23.03`→2303 · `2304.00`→230400 · `2305.00.00`→23050000 · `23.06`→2306 · `2308.00.00`→23080000 · `2703.00.00`→27030000 · `2839.90.10`→28399010 · `2839.90.50`→28399050 · `2922.4`→29224 · `2930.40`→293040 · `33.01`→3301 · `3802.90.40`→38029040 · `3804.00`→380400 · `3824.99.71`→38249971 · `4401.39.00`→44013900 · `4401.4`→44014 · `4402.90.00`→44029000 · `4701.00.00`→47010000 · `5305.00.90`→53050090 · `6806.20.00`→68062000 |
| 8 | Ácido nítrico, ácido sulfúrico, ácido fosfórico, fosfatos de cálcio naturais, enxofre, ácido clorídrico, ácido fosforoso, ácido acético, hidróxido de sódio e carbonato dissódico; todos destinados diretamente à fabricação de fertilizantes | `2503.00.10`→25030010 · `2503.00.90`→25030090 · `2510.10.10`→25101010 · `2510.10.90`→25101090 · `2510.20.10`→25102010 · `2510.20.90`→25102090 · `2802.00.00`→28020000 · `2806.10.20`→28061020 · `2807.00.10`→28070010 · `2808.00.10`→28080010 · `2809.20.11`→28092011 · `2809.20.19`→28092019 · `2811.19.20`→28111920 · `2815.11.00`→28151100 · `2815.12.00`→28151200 · `2836.20.10`→28362010 · `2836.20.90`→28362090 · `2915.21.00`→29152100 |
| 9 | Enzimas preparadas para decomposição de matéria orgânica animal e vegetal | `3507.90.4`→3507904 |
| 10 | Semente genética, semente básica, semente nativa in natura, semente certificada de primeira geração (C1), semente certificada de segunda geração (C2), semente não certificada de primeira geração (S1), semente não certificada de segunda geração (S2) e sementes de cultivar local, tradicional ou crioula; em conformidade com as definições e demais requisitos da legislação específica | `07`→07 **(capítulo)** · `10`→10 **(capítulo)** · `12`→12 **(capítulo)** |
| 11 | Mudas de plantas e demais materiais propagativos de plantas e fungos, inclusive plantas e fungos nativos de espécies florestais; em conformidade com as definições e demais requisitos da legislação específica | `06.01`→0601 · `06.02`→0602 |
| 12 | Vacinas, soros e medicamentos, de uso veterinário, exceto de animais domésticos | `3002.12`→300212 · `3002.15`→300215 · `3002.42`→300242 · `3002.90.00`→30029000 · `30.04`→3004 |
| 13 | Aves de um dia, exceto as ornamentais | `0105.1`→01051 |
| 14 | Embriões e sêmen, congelado ou resfriado | `0511.10.00`→05111000 · `0511.9`→05119 |
| 15 | Reprodutores de raça pura, inclusive matrizes de animais puros de origem com registro genealógico; em conformidade com as definições e demais requisitos da legislação específica | `01.02`→0102 · `01.03`→0103 · `01.04`→0104 |
| 16 | Ovos fertilizados | `0407.1`→04071 |
| 17 | Girinos e alevinos | `0106.90.00`→01069000 |
| 18 | Rações para animais, concentrados, suplementos, aditivos, premix ou núcleo, exceto para animais domésticos | `2309.90`→230990 |
| 19 | Sementes e cereais, mesmo triturados, em grãos esmagados ou trabalhados de outro modo; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos | `10`→10 **(capítulo)** · `11`→11 **(capítulo)** · `12`→12 **(capítulo)** |
| 20 | Farelos e tortas de produtos vegetais e demais resíduos e desperdícios das indústrias alimentares; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos | `23.01`→2301 · `23.02`→2302 · `23.03`→2303 · `2304.00`→230400 · `2305.00.00`→23050000 · `23.06`→2306 · `2308.00.00`→23080000 |
| 21 | Alho em pó, sal mineralizado, farinhas de peixe, de ostra, de carne, de osso, de pena, de sangue e de víscera, calcário calcítico, gorduras e óleos animais, resíduos de óleo e de gordura de origem animal ou vegetal descartados por empresas do ramo alimentício, e DL-Metionina e seus análogos; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos | `02.10`→0210 · `03.09`→0309 · `0712.90.10`→07129010 · `15`→15 **(capítulo)** · `2501.00`→250100 · `2521.00.00`→25210000 · `2930.40`→293040 |
| 35 | Vinhaça | `2303.30.00`→23033000 · `2303.20.00`→23032000 |

### Anexo IX — os 13 itens que **não** entram na tabela (vão para o cabeçalho da migração 010)

| item | descrição | chave | Por que não entra |
|---|---|---|---|
| 22 | Serviços agronômicos | NBS `1.1410.90.00` | Chave NBS — posição 14 do roadmap |
| 23 | Serviços de técnico agrícola, agropecuário ou em agroecologia | NBS `1.1410.90.00` | idem |
| 24 | Serviços veterinários para produção animal | NBS `1.1405.21.00`, `1.1405.22.00`, `1.1405.90.00` | idem |
| 25 | Serviços de zootecnistas | NBS `1.1410.90.00` | idem |
| 26 | Serviços de inseminação e fertilização de animais de criação | NBS `1.1405.22.00` | idem |
| 27 | Serviços de engenharia florestal | NBS `1.1403.10.00` | idem |
| 28 | Serviços de pulverização e controle de pragas | NBS `1.1901.10.00` | idem |
| 29 | Serviços de semeadura, adubação, inclusive mistura de adubos, reparação de solo, plantio e colheita | NBS `1.1901.10.00` | idem |
| 30 | Serviços de projetos para irrigação e fertirrigação | NBS `1.1403.29.00` | idem |
| 31 | Serviços de análise laboratorial de solos, sementes e outros materiais propagativos, fitossanitários, água de produção, bromatologia e sanidade animal | NBS `1.1404.41.00` | idem |
| 32 | Licenciamento de direitos sobre cultivares | NBS `1.1105.10.00` | idem |
| 33 | Cessão definitiva de direitos sobre cultivares | NBS `1.1109.10.00` | idem |
| 34 | Melhoramento genético de animais e plantas e biotecnologia, inclusive seus royalties | **nenhuma** (célula vazia na fonte) | Limitação de espécie diferente: não há o que casar, em nenhuma tabela |

Observação que vale para o `/build`: um código NBS sem pontuação tem **9 dígitos**
(`1.1410.90.00` → `114109000`) e a CHECK `prefixo_comprimento_valido` só admite `{2,4,5,6,7,8}` —
**o banco recusaria uma transcrição de NBS nesta tabela**, mesmo que alguém tentasse.

---

## Catálogo das cláusulas “exceto” e “ressalvado” (vai no cabeçalho da migração 010)

Mesma regra mecânica de duas perguntas da Decisão 6 da feature anterior, agora com uma quarta
classe (**remissão**), que é resolvida pelo desempate e não por linha:

```text
A cláusula nomeia código(s) NCM?
├─ NÃO  → NÃO CODIFICÁVEL. Zero linhas. Vira limitação declarada.
└─ SIM  → nomeia um ANEXO inteiro em vez de códigos?
          ├─ SIM → REMISSÃO. Zero linhas — resolvida pelo desempate (Decisão 3),
          │         e provada pela asserção 6 da migração.
          └─ NÃO → o código nomeado desce de uma INCLUSÃO do MESMO item?
                    ├─ SIM → OPERANTE.    1 linha com excecao = TRUE.
                    └─ NÃO → DESCRITIVA.  Zero linhas (seria inerte).
```

| Anexo/item | Cláusula | Classe | Linhas |
|---|---|---|---|
| IV / 48 | “exceto as preparadas como medicamentos, as imunoglobulinas séricas, o concentrado de fator VIII e a soroalbumina…” | **NÃO CODIFICÁVEL** | 0 |
| IV / 49 | “exceto os da posição 30.06” | **DESCRITIVA** — `30.06` não desce de `3822.1`, a única inclusão do item | 0 |
| IV / 51 | “exceto cimentos” | **NÃO CODIFICÁVEL** (cimentos são o item 4, `3006.40.20`; o item 51 é `3006.40.12`) | 0 |
| IV / 54 | “exceto bolsas para uso em colostomia, ileostomia e urostomia” | **NÃO CODIFICÁVEL** (são o item 53, `3006.91.10`; o 54 é `3006.91.90`) | 0 |
| IV / 61 | “exceto as de metal e as para suturas” | **NÃO CODIFICÁVEL** (são o item 60, `9018.32`) | 0 |
| IV / 68 | “excluídas seringas e agulhas, das posições 9018.31 e 9018.32” | **DESCRITIVA** — nenhuma das duas desce de `90183999`/`90189099` | 0 |
| VII / 1 | “(exceto lagostas e lagostim)” | **NÃO CODIFICÁVEL** | 0 |
| VII / 1 | “exceto os produtos da subposição 0306.11 e dos códigos 0306.15.00, 0306.31.00, 0306.34.00, 0306.39.10” | **OPERANTE** — os 5 descem de `03061`/`03063` | **5** |
| VII / 4, 5, 6, 15 | “ressalvados os produtos relacionados no Anexo I” | **REMISSÃO** — Decisão 3 | 0 |
| VII / 14 | “ressalvados as frutas de casca rija não regionais” | **NÃO CODIFICÁVEL** | 0 |
| VII / 14 | “os produtos relacionados nos Anexos I e XV” | **REMISSÃO** (dupla) — Decisão 3 | 0 |
| VII / 14 | “excetuadas as posições 07.11, 08.12 e 0814.00.00” | **OPERANTE** — as 3 descem de `07`/`08` | **3** |
| IX / 12 | “exceto de animais domésticos” | **NÃO CODIFICÁVEL** | 0 |
| IX / 13 | “exceto as ornamentais” | **NÃO CODIFICÁVEL** | 0 |
| IX / 18, 19, 20, 21 | “exceto para/de animais domésticos” | **NÃO CODIFICÁVEL** | 0 |
| V, VI, VIII | *(nenhuma cláusula em todo o Anexo)* | — | 0 |

**Total: 8 linhas de exceção**, todas no Anexo VII — chegando lá por uma regra verificável, não por
contagem. O `COULD` do DEFINE (confirmar contra a TIPI que as cláusulas descritivas são inócuas)
fica **atendido por construção** nas duas descritivas: a regra as classifica pela estrutura da NCM,
sem precisar da TIPI.

---

## Contagens de fechamento (asserções obrigatórias do `/build`)

| Anexo | Itens | Prefixos | Inclusões | Exceções | Comprimentos presentes |
|---|---|---|---|---|---|
| I (existente, intocado) | 26 | 95 | 76 | 19 | 4,5,6,7,8 |
| **IV** | **105** | **112** | 112 | 0 | 5,6,7,8 |
| **V** | **29** | **30** | 30 | 0 | 5,8 |
| **VI** | **81** | **86** | 86 | 0 | 8 |
| **VII** | **17** | **53** | 45 | 8 | 2,4,5,6,8 |
| **VIII** | **7** | **7** | 7 | 0 | 8 |
| **IX** | **22** | **101** | 101 | 0 | 2,4,5,6,7,8 |
| XII (existente) | 20 | 24 | 21 | 3 | 4,6,8 |
| XIII (existente) | 8 | 7 | 7 | 0 | 8 |
| XV (existente) | 6 | 25 | 23 | 2 | 2,4,5,6,8 |
| **Total** | **321** | **540** | **508** | **32** | `{2,4,5,6,7,8}` |

Novos nesta feature: **261 itens · 389 linhas · 381 inclusões · 8 exceções.**

Itens **sem** linha de prefixo = exatamente **5** (XII/1, XIII/2, V/1, V/2, V/3), todos cabeçalhos
com sub-itens. Prefixos de 2 dígitos = **14** (`06` no XV; `07`,`08`,`10`,`12` no VII;
`07`,`10`,`11`,`12`,`15`,`25`,`31` no IX — com `10` e `12` aparecendo em dois itens do IX cada).

---

## Mapa das sobreposições (o que o `/build` **não** deve tratar como erro)

### Entre os Anexos zero e os de 60% — 117 pares, três regimes

| Regime | Pares | Vencedor | Componente que decide |
|--------|-------|----------|------------------------|
| Prefixo do Anexo zero **mais longo** | 78 | zero | 1 (especificidade) |
| Prefixos de **mesmo comprimento** | 35 | zero | 2 (maior redução) |
| Prefixo do Anexo zero **mais curto** | 4 | **60%** | 1 (especificidade) — Decisão 4 |

### Dentro do grupo de 60% — só a citação muda, nunca o número

| Sobreposição | Vencedor | Perdedor |
|---|---|---|
| `2002.10.00` | VI/15 “Água para injeção” | VII/16 “Produtos hortícolas pré-cozidos” |
| `2202.99.00` | VI/47 e VI/48 | VII/2 “Leite fermentado…” |
| `2915.21.00` | VI/7 “Ácido acético” | IX/8 |
| `3821.00.00` | IV/75 “Meios de cultura” | IX/4 |
| `3824.99.89` | IV/93 | IX/2 e IX/6 |
| `2922.4*`, `2930.40`, `3002.12`, `3004`, `31`, `25`, `15`, `3808` etc. | o de prefixo mais longo | o capítulo/posição |
| chapters `10`/`12` | VII/15 (anexo_ordem 7) | IX/10 e IX/19 (anexo_ordem 9) |
| chapter `07` | VII/14 (anexo_ordem 7) | IX/10 |

**Em todos os pares em que um item de IV/V/VI (com condição de comprador) disputa com um item de
VII/VIII/IX, quem vence é o de IV/V/VI** — hoje por especificidade (o prefixo de IV/V/VI é mais
longo em 20 dos 27 pares) ou por `anexo_ordem` (nos 7 empates de 8 dígitos, porque 4 < 5 < 6 < 7 <
8 < 9). Isso importa porque, se um par fosse vencido pelo Anexo VII/VIII/IX, o zero do comprador
qualificado sumiria sem sintoma. **Hoje é por sorte; com o componente 2 da Decisão 3 passa a ser
por construção**, e um teste SQL (Decisão 12, variante D) fixa a propriedade.

### Dentro de um mesmo Anexo — esperado, já suportado

`itens_correspondentes` fica maior do que já foi: **9 itens** do Anexo IV citam `9018.90.99`,
**10 itens** do Anexo VI citam `2922.49.90`, **8 itens** do Anexo VI citam `2106.90.90`. A lista é
devolvida inteira, na ordem numérica do documento legal (`anexo_ordem`, `item`, `sub_item`) —
nenhum limite artificial: truncá-la seria esconder do auditor exatamente o que ele foi procurar.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/009_generalizar_anexos_reducao.sql` | Create | `anexos_reducao_catalogo` (10 linhas); rename das 2 tabelas; `DROP COLUMN anexo_ordem`; FK para o catálogo no lugar da CHECK `anexo_conhecido`; re-`GRANT`; prova de que os 4 Anexos zero sobreviveram (60/151) — Decisões 1, 2 | @database-reviewer | — |
| 2 | `db/migrations/010_anexos_reducao_percentual_ncm.sql` | Create | Catálogo de “exceto” + os 13 itens fora de escopo + seed de 261 itens/389 prefixos + 7 asserções, incluindo a prova SQL da remissão do Anexo VII — Decisões 10, 11 | @database-reviewer | 1 |
| 3 | `db/repositorio.py` | Modify | `PrefixoReducao` (+`percentual_reducao`, `zero_por_comprador_ref`; `anexo_ordem` vem do catálogo) e `buscar_reducao_por_prefixo` (+`JOIN` do catálogo) | @database-reviewer | 1, 2 |
| 4 | `motor_calculo/engine.py` | Modify | Extrai `valor_do_tributo(base, aliquota)`; `calcular` passa a usá-la. **Nenhuma mudança de comportamento** — Decisão 5 | @python-developer | — |
| 5 | `motor_calculo/reducoes.py` | Modify | `aplicar_reducao_percentual` (nova) + `_recompor` (helper); `aplicar_reducao_a_zero` mantém assinatura e comportamento — Decisão 5 | @python-developer | 4 |
| 6 | `api/reducao.py` | Create (`git mv` de `api/reducao_zero.py`) | `SituacaoReducao`, `ConsultaReducao`, `ResolucaoReducao`, `_chave_especificidade` de 6 componentes, `_tipo_correspondencia` com `CAPITULO`, `resolver_item(…, comprador_tipo)` — Decisões 3, 6, 7, 8 | @python-developer | 3 |
| 7 | `api/schemas_simulate.py` | Modify | `CompradorTipo`; `PayloadSimulacao.comprador_tipo`; `ReducaoItem`/`ReducaoResumo` com `percentual_reducao`, `zero_por_comprador_disponivel`, `dispositivo_legal_comprador`, `itens_excluidos`, `itens_por_capitulo`; `fonte_legal` reescrita para os 10 Anexos — Decisões 6, 7, 8, 9 | @python-developer | 6 |
| 8 | `api/routers/simulate.py` | Modify | Dois caminhos de redução; `aliquotas_aplicadas` derivadas do percentual; `anexos_aplicados` ordenados pelo catálogo; advertência e parecer do audit log — Decisões 5, 6, 9 | @python-developer | 5, 6, 7 |
| 9 | `motor_calculo/regras_fiscais.py` | Modify | **Só comentário** — `fonte_legal_reducoes` deixa de citar apenas os 4 Anexos zero e passa a citar os 10 (o texto semeado em `tabela_aliquotas.py` **não muda**: ele já cita o art. 348, III, “a”, genérico para “operações sujeitas a alíquota reduzida”) | @python-developer | — |
| 10 | `tests/test_reducoes_percentual.py` | Create | Unit puro de `motor_calculo`: 60% sobre a alíquota; equivalência entre `aplicar_reducao_percentual(…, 1.0)` e `aplicar_reducao_a_zero`; IS intacto; `valor_liquido` recomposto; o caso de arredondamento de `137,49` (Decisão 5) | @test-generator | 4, 5 |
| 11 | `tests/test_reducao_resolucao.py` | Modify (`git mv` de `test_reducao_zero_resolucao.py`) | Desempate de 6 componentes; `CAPITULO`; comprador; `itens_excluidos`; **assertions dos 4 Anexos zero inalteradas em valor** | @test-generator | 6 |
| 12 | `tests/test_api_simulate_reducao.py` | Modify (`git mv` de `test_api_simulate_reducao_zero.py`) | AT-001..AT-013 via `TestClient` + fake pool; 1 query por request; pool `None`/pool que explode → 200 | @test-generator | 8 |
| 13 | `tests/test_reducao_db.py` | Modify (`git mv` de `test_reducao_zero_db.py`) | Postgres real: contagens por Anexo, catálogo/FK, CHECKs, exceção órfã, cabeçalho×sub-item, os **três** testes de sobreposição (Decisão 12), remissão do Anexo VII | @database-reviewer | 1, 2, 3 |
| 14 | `scripts/verificar_reducao_producao.py` | Modify (`git mv` de `verificar_reducao_zero_producao.py`) | 15 casos com o papel `taxreformai_app` contra o Cloud SQL real — Decisão 13 | @gcp-data-architect | 3, 6 |
| 15 | `.github/workflows/migrar_banco.yml` | Modify | Input `verificar_reducao_zero` → `verificar_reducao`; passo aponta para o script renomeado | @gcp-data-architect | 14 |
| 16 | `.github/workflows/deploy.yml` | Modify | Caminhos `jq` (`.reducao_zero` → `.reducao`) + **quarta** chamada de smoke test com `34011190` exigindo `cbs_percentual == 0.36` | @gcp-data-architect | 8 |
| 17 | `CLAUDE.md` | Modify | Tabela de features, estrutura, nomes das tabelas e do módulo, arquivos-chave | @python-developer | 1-16 |

**Total: 17 arquivos** (3 novos, 4 renomeados-e-modificados, 10 modificados). Nenhum arquivo
deletado: os renames são `git mv`, para o histórico seguir os arquivos.

**Fora do manifesto, deliberadamente:**

- `api/ncm.py` — `_COMPRIMENTOS_PREFIXO = (2,4,5,6,7,8)` já cobre todos os 389 prefixos novos
  (comprimentos 2, 4, 5, 6, 7 e 8). A feature anterior alargou na medida certa, e a simetria
  “o que a tabela aceita é exatamente o que o gerador enxerga” continua exata.
- `motor_calculo/tabela_aliquotas.py` — `fonte_legal_reducoes` já é genérico (“operações sujeitas a
  alíquota reduzida”, art. 348, III, “a”) e vale igual para 60% e para zero. Zero mudança ⇒ zero
  risco de regressão em `test_tabela_aliquotas.py` e `test_engine.py`.
- `frontend/` — não tipa nem lê o bloco (verificado por `grep` nesta sessão); `comprador_tipo` é
  opcional, então o formulário atual continua válido. Expor o campo na UI é candidato a feature
  própria.
- `db/migrations/005..008` — migrações aplicadas são histórico e não se editam.
- `contexto.md` — blueprint é registro de intenção (mesma decisão das 3 features anteriores).
- `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` — atualizado no `/ship`; **o achado do art. 147
  (`9619.00.00` a zero, fora de Anexo) e o do art. 137 (60% a produtos in natura, sem Anexo) devem
  entrar lá como candidatos a feature própria.**

---

## Agent Assignment Rationale

| Agent | Files | Why This Agent |
|-------|-------|-----------------|
| @database-reviewer | 1, 2, 3, 13 | Tabela de catálogo com FK, `DROP COLUMN` numa tabela em produção, 389 linhas de seed e 7 asserções em `DO $$` — a parte mais arriscada da feature continua sendo SQL, e agora o SQL também **prova uma regra jurídica** (asserção 6) |
| @python-developer | 4-9, 17 | A função de cálculo nova (a primeira desde o Anexo I), o desempate de 6 componentes e a disciplina de “renomear sem mudar valor” |
| @test-generator | 10, 11, 12 | AT-001..AT-013 com fakes, o teste de arredondamento da Decisão 5 e o guard-rail de não-regressão dos 4 Anexos zero |
| @gcp-data-architect | 14, 15, 16 | Verificação contra Cloud SQL/Cloud Run reais e edição dos dois workflows |
| @security-reviewer | (revisão de 1, 2, 3, 7) | Confirmar que a ausência de RLS segue correta (dado legal público); que o `LIKE` construído por concatenação nas asserções não é injeção (roda dentro da migração, sobre colunas validadas por CHECK); e — novo nesta feature — que **`comprador_tipo` não é PII nem credencial**: é uma declaração do cliente sobre a operação, gravada no audit log junto com o resto do payload, e não identifica pessoa nenhuma |
| @code-reviewer | (revisão final) | Como em toda feature — com atenção especial ao diff dos testes dos 4 Anexos zero (Decisão 9) e às duas mudanças de comportamento autorizadas (Decisões 7 e 8) |

---

## Code Patterns

### Pattern 1: catálogo e generalização (`009_generalizar_anexos_reducao.sql`)

```sql
-- Generaliza o schema dos 4 Anexos de redução A ZERO para os 10 Anexos de
-- redução por NCM/SH da LCP 214/2025 — porque a verificação do /design provou
-- que os dois grupos NÃO são independentes: 117 pares de prefixo em
-- sobreposição, inclusive o MESMO código de 8 dígitos (9018.90.99 é XII/9 a
-- zero e é 9 itens do Anexo IV a 60%). Resolver em separado responderia 60%
-- onde a lei dá zero.
--
-- Nada de dado é reescrito: as 60 linhas de item e as 151 de prefixo já
-- carregadas só mudam de nome de tabela. O seed dos 6 Anexos novos é a 010.

CREATE TABLE IF NOT EXISTS anexos_reducao_catalogo (
    anexo                  VARCHAR(4)   PRIMARY KEY,
    anexo_ordem            SMALLINT     NOT NULL UNIQUE,
    -- Fração da ALÍQUOTA que é removida: 1.0 = "reduzidas a zero" (arts. 125,
    -- 144, 145, 148); 0.6 = "reduzidas em 60%" (arts. 131 a 138). O nome diz
    -- "reducao" e não "aliquota" de propósito: 0.6 aqui significa que RESTAM
    -- 40% da alíquota da fase.
    percentual_reducao     NUMERIC(5,4) NOT NULL,
    assunto                TEXT NOT NULL,
    artigo_ref             TEXT NOT NULL,
    -- Só os Anexos IV, V e VI: a lei zera a alíquota deles conforme QUEM compra.
    zero_por_comprador_ref TEXT,

    CONSTRAINT catalogo_conhecido CHECK (
        (anexo, anexo_ordem, percentual_reducao) IN (
            ('I',1,1.0), ('IV',4,0.6), ('V',5,0.6), ('VI',6,0.6), ('VII',7,0.6),
            ('VIII',8,0.6), ('IX',9,0.6), ('XII',12,1.0), ('XIII',13,1.0), ('XV',15,1.0))
    ),
    CONSTRAINT so_percentual_tem_condicao_de_comprador CHECK (
        percentual_reducao < 1 OR zero_por_comprador_ref IS NULL
    )
);

INSERT INTO anexos_reducao_catalogo
       (anexo, anexo_ordem, percentual_reducao, assunto, artigo_ref, zero_por_comprador_ref) VALUES
 ('I',    1, 1.0, 'Cesta Básica Nacional de Alimentos',        'LCP 214/2025, art. 125',        NULL),
 ('IV',   4, 0.6, 'Dispositivos médicos',                      'LCP 214/2025, art. 131',        'LCP 214/2025, art. 144, II'),
 ('V',    5, 0.6, 'Dispositivos de acessibilidade',            'LCP 214/2025, art. 132',        'LCP 214/2025, art. 145, II'),
 ('VI',   6, 0.6, 'Nutrição enteral e parenteral',             'LCP 214/2025, art. 133, § 1º',  'LCP 214/2025, art. 146, § 2º'),
 ('VII',  7, 0.6, 'Alimentos destinados ao consumo humano',    'LCP 214/2025, art. 135',        NULL),
 ('VIII', 8, 0.6, 'Produtos de higiene pessoal e limpeza',     'LCP 214/2025, art. 136',        NULL),
 ('IX',   9, 0.6, 'Insumos agropecuários e aquícolas',         'LCP 214/2025, art. 138',        NULL),
 ('XII', 12, 1.0, 'Dispositivos médicos',                      'LCP 214/2025, art. 144, I',     NULL),
 ('XIII',13, 1.0, 'Dispositivos de acessibilidade',            'LCP 214/2025, art. 145, I',     NULL),
 ('XV',  15, 1.0, 'Produtos hortícolas, frutas e ovos',        'LCP 214/2025, art. 148',        NULL)
ON CONFLICT (anexo) DO NOTHING;

ALTER TABLE anexos_reducao_zero     RENAME TO anexos_reducao;
ALTER TABLE anexos_reducao_zero_ncm RENAME TO anexos_reducao_ncm;

-- O ordinal passa a viver SÓ no catálogo: dois lugares declarando a mesma
-- verdade divergem no primeiro Anexo novo (Decisão 3 da feature anterior, agora
-- levada às últimas consequências).
ALTER TABLE anexos_reducao DROP CONSTRAINT anexo_conhecido;
ALTER TABLE anexos_reducao DROP COLUMN anexo_ordem;
ALTER TABLE anexos_reducao
    ADD CONSTRAINT anexo_no_catalogo FOREIGN KEY (anexo)
        REFERENCES anexos_reducao_catalogo (anexo);
-- A FK substitui a CHECK: quem quiser carregar um Anexo novo precisa declarar
-- ANTES qual é o percentual e qual artigo o institui.

-- Os 4 Anexos zero atravessaram intactos? (MUST "zero regressão" do DEFINE,
-- provado pela própria migração, não só por teste.)
DO $$
DECLARE itens int; prefixos int;
BEGIN
    SELECT count(*) INTO itens    FROM anexos_reducao;
    SELECT count(*) INTO prefixos FROM anexos_reducao_ncm;
    IF (itens, prefixos) <> (60, 151) THEN
        RAISE EXCEPTION 'Anexos zero não sobreviveram: % itens / % prefixos (esperado 60/151)',
            itens, prefixos;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao           TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_ncm       TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_catalogo  TO taxreformai_app';
    END IF;
END $$;
```

### Pattern 2: lookup em lote (`db/repositorio.py`)

```python
@dataclass(frozen=True)
class PrefixoReducao:
    """Uma linha de `anexos_reducao_ncm` com o item e o Anexo já resolvidos.

    `percentual_reducao` é a FRAÇÃO DA ALÍQUOTA REMOVIDA — 1.0000 para os
    Anexos de redução a zero, 0.6000 para os de 60%. Vem do catálogo, não de
    uma constante em Python, pelo mesmo motivo de `anexo_ordem`: duas
    declarações da mesma verdade divergem no primeiro Anexo novo.

    `zero_por_comprador_ref` é não-nulo só nos Anexos IV, V e VI, e é o que
    permite ao runtime aplicar ZERO (não 60%) quando o payload informa
    `comprador_tipo` — arts. 144, II; 145, II; 146, § 2º.
    """

    anexo: str
    anexo_ordem: int
    percentual_reducao: Decimal
    zero_por_comprador_ref: str | None
    item: int
    sub_item: int
    prefixo: str
    excecao: bool
    texto_ncm: str
    alinea: str | None
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str


def buscar_reducao_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoReducao]:
    """Lookup em lote dos 10 Anexos de redução por NCM. Sem RLS: dado legal público.

    UMA query — e ela precisa ser uma só, não por economia: a resposta certa
    depende de comparar linhas dos dois grupos entre si (117 pares em
    sobreposição). Duas consultas devolveriam duas listas que alguém teria de
    reconciliar em Python, com a ordem de desempate declarada em dois lugares.
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT c.anexo, c.anexo_ordem, c.percentual_reducao, c.zero_por_comprador_ref,
                   p.item, p.sub_item, p.prefixo, p.excecao, p.texto_ncm, p.alinea,
                   i.descricao, pai.descricao, i.dispositivo_legal_ref
            FROM anexos_reducao_ncm p
            JOIN anexos_reducao i
              ON i.anexo = p.anexo AND i.item = p.item AND i.sub_item = p.sub_item
            JOIN anexos_reducao_catalogo c ON c.anexo = i.anexo
            LEFT JOIN anexos_reducao pai
              ON pai.anexo = i.anexo AND pai.item = i.item
             AND pai.sub_item = 0 AND i.sub_item > 0
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoReducao(*linha) for linha in cur.fetchall()]
```

### Pattern 3: cálculo (`motor_calculo/engine.py` e `reducoes.py`)

```python
# engine.py — a fórmula do tributo passa a existir UMA vez.
def valor_do_tributo(base: Decimal, aliquota: Decimal) -> Decimal:
    """Tributo em centavos, ROUND_HALF_UP.

    Pública porque `motor_calculo/reducoes.py` precisa da MESMA fórmula para
    recalcular CBS/IBS com a alíquota reduzida (Decisão 5). Duas cópias
    divergiriam no dia em que a regra de arredondamento mudasse.
    """
    return (base * aliquota).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

```python
# reducoes.py
UM = Decimal("1.0000")


def aplicar_reducao_percentual(
    resultado: ResultadoCalculo,
    regra: RegraFiscal,
    percentual_reducao: Decimal,
    *,
    split_payment_active: bool = True,
) -> ResultadoCalculo:
    """CBS e IBS recalculados com a ALÍQUOTA reduzida; IS intacto.

    Os arts. 131 a 138 reduzem "em 60% (sessenta por cento) AS ALÍQUOTAS do IBS
    e da CBS" — o objeto da redução é a alíquota, não o valor devido. A
    diferença não é retórica: escalar o valor já arredondado
    (`round(round(base*0,9%)*0,4)`) diverge de recalcular
    (`round(base*0,36%)`) em 1 centavo para entradas reais (base_iva 137,49 →
    0,50 contra 0,49), e só a segunda é reproduzível pelo cliente a partir da
    alíquota que a resposta cita (0,36%). Num produto cujo entregável é uma
    defesa fiscal, um número que não fecha com a própria fundamentação é pior
    que um número diferente.

    O Imposto Seletivo não é tocado: os arts. 131-138 falam do IBS e da CBS, e
    o IS tem lista própria (Anexo XVII, posição 16 do roadmap).

    `regra` precisa ser a MESMA passada a `engine.calcular()` — mesma
    disciplina de `split_payment_active`. Deduzi-la do `ResultadoCalculo`
    (dividindo valor por base) seria adivinhar o passado dele, e falharia
    justamente onde houve arredondamento.
    """
    fator_restante = UM - percentual_reducao
    base_iva = resultado.valor_base + resultado.valor_is
    return _recompor(
        resultado,
        valor_cbs=valor_do_tributo(base_iva, regra.aliq_cbs * fator_restante),
        valor_ibs=valor_do_tributo(base_iva, regra.aliq_ibs * fator_restante),
        split_payment_active=split_payment_active,
    )


def _recompor(resultado, *, valor_cbs, valor_ibs, split_payment_active):
    """Reescreve CBS/IBS e recompõe total e líquido.

    Não é detalhe: trocar CBS/IBS e deixar o líquido como estava produziria uma
    resposta internamente contraditória — líquido menor que o bruto sem tributo
    que o justifique. Compartilhado com `aplicar_reducao_a_zero` para que a
    invariante `valor_liquido = valor_base - total_tributos` exista uma vez só.
    """
    total_tributos = valor_cbs + valor_ibs + resultado.valor_is
    return replace(
        resultado,
        valor_cbs=valor_cbs,
        valor_ibs=valor_ibs,
        total_tributos=total_tributos,
        valor_liquido=(
            resultado.valor_base - total_tributos
            if split_payment_active
            else resultado.valor_base
        ),
    )
```

### Pattern 4: resolução e desempate (`api/reducao.py`)

```python
UM = Decimal("1.0000")


def _percentual_efetivo(linha: Any, comprador_qualificado: bool) -> Decimal:
    """O percentual que de fato se aplica a ESTA requisição.

    Os arts. 144, II; 145, II e 146, § 2º reduzem a ZERO — não a 60% — os
    Anexos IV, V e VI quando o adquirente é órgão da administração pública
    direta/autarquia/fundação pública ou entidade de saúde imune com CEBAS
    comprovando serviço ao SUS. É condição sobre o COMPRADOR, então só pode ser
    avaliada com `comprador_tipo` no payload (Decisão 6).
    """
    if comprador_qualificado and linha.zero_por_comprador_ref is not None:
        return UM
    return linha.percentual_reducao


def _chave_especificidade(linha: Any, comprador_qualificado: bool):
    """Mais específico primeiro, com `max()`:

    1. prefixo mais LONGO — a única regra que a lei escreve para todos os casos,
       e a que honra sozinha a remissão expressa do Anexo VII ("ressalvados os
       produtos relacionados no Anexo I"): nos 13 pares em que isso importa, o
       prefixo do Anexo zero é estritamente mais longo (provado por asserção na
       migração 010);
    2. MAIOR redução — decide os 35 pares em que os dois grupos citam o mesmo
       código de 8 dígitos e não há especificidade que os separe (9018.90.99 é
       XII/9 a zero e 9 itens do Anexo IV a 60%);
    3. redução INCONDICIONAL antes da condicionada — quando o comprador é
       qualificado, IV e XII valem zero os dois; citar o art. 144, I é mais
       forte que citar o art. 144, II, porque não depende de provar a qualidade
       do comprador;
    4-6. ordem do documento legal (Anexo, item, sub-item).

    Ordem TOTAL, portanto determinística: sem ela, `2106.90.90` citaria ora
    I/4, ora I/26, ora um dos 8 itens do Anexo VI, conforme a ordem em que o
    Postgres devolvesse as linhas — não-determinismo que só apareceria em
    produção, num campo que o cliente leva para uma defesa fiscal.
    """
    return (
        len(linha.prefixo),
        _percentual_efetivo(linha, comprador_qualificado),
        linha.percentual_reducao,
        -linha.anexo_ordem,
        -linha.item,
        -linha.sub_item,
    )


def _tipo_correspondencia(prefixo: str) -> str:
    """EXATO (8) · CAPITULO (2) · PREFIXO (4-7).

    `CAPITULO` existe porque um prefixo de 2 dígitos cobre um capítulo INTEIRO
    da NCM — o Capítulo 25 do Anexo IX/3 inclui cimento, mármore e gesso,
    enquanto o item fala de corretivos de solo. É a única classe de
    correspondência desta feature cujo erro é na direção PERIGOSA (tributo a
    menos), e por isso é a única que o cliente consegue filtrar por máquina
    (Decisão 7).
    """
    if len(prefixo) == 8:
        return "EXATO"
    if len(prefixo) == 2:
        return "CAPITULO"
    return "PREFIXO"


def resolver_item(
    natureza: str, ncm: str, consulta: ConsultaReducao,
    comprador_tipo: str | None = None,
) -> ResolucaoReducao:
    if natureza == "SERVICO":
        return ResolucaoReducao(SituacaoReducao.NAO_APLICAVEL)
    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoReducao(SituacaoReducao.NCM_NAO_RECONHECIDO)
    if not consulta.disponivel:
        return ResolucaoReducao(SituacaoReducao.CONSULTA_INDISPONIVEL)

    qualificado = comprador_tipo is not None
    chave = partial(_chave_especificidade, comprador_qualificado=qualificado)

    por_item: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_item[(linha.anexo, linha.item, linha.sub_item)].append(linha)

    inclusoes, exclusoes = [], []
    for linhas in por_item.values():
        # Exceção do PRÓPRIO item vence a inclusão do próprio item — e não toca
        # nenhum outro item, nem de outro Anexo. É por isso que um cogumelo
        # (excluído do XV/2) recebe 60% pelo VII/14: ele não é "relacionado no
        # Anexo XV", é retirado de lá (Decisão 8).
        excecoes = [linha for linha in linhas if linha.excecao]
        (exclusoes if excecoes else inclusoes).append(
            max(excecoes or linhas, key=chave)
        )

    if inclusoes:
        vencedora = max(inclusoes, key=chave)
        percentual = _percentual_efetivo(vencedora, qualificado)
        return ResolucaoReducao(
            situacao=SituacaoReducao.APLICADA,
            anexo=vencedora.anexo,
            anexo_ordem=vencedora.anexo_ordem,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            percentual_reducao=percentual,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            # Citado SEMPRE que o Anexo tem a condição — informado ou não. Com
            # `comprador_tipo` ausente, é o aviso de que a alíquota real pode
            # ser ZERO; com ele presente, é a fundamentação do zero aplicado.
            dispositivo_legal_comprador=vencedora.zero_por_comprador_ref,
            zero_por_comprador_disponivel=(
                vencedora.zero_por_comprador_ref is not None and not qualificado
            ),
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia=_tipo_correspondencia(vencedora.prefixo),
            itens_correspondentes=_ordenar(inclusoes),
            itens_excluidos=_ordenar(exclusoes),   # Decisão 8
        )
    # … EXCLUIDA_EXPRESSAMENTE (idem, com `exclusoes`) … FORA_DO_ANEXO
```

### Pattern 5: consumo no router (`api/routers/simulate.py`)

```python
    resolucao = resolver_reducao(
        item.natureza, item.ncm, consulta_reducao, payload.comprador_tipo
    )

    if resolucao.aplicada:
        cbs_cheio, ibs_cheio = resultado.valor_cbs, resultado.valor_ibs
        if resolucao.percentual_reducao == UM:
            # O caminho de zero continua passando pela função já shipada e
            # provada, mesmo sendo hoje matematicamente equivalente à nova com
            # percentual 1.0 (há um teste que prova a equivalência). Manter o
            # caminho antigo independente da RegraFiscal significa que um bug na
            # leitura da regra não pode transformar um zero provado em outra coisa.
            resultado = aplicar_reducao_a_zero(resultado)
        else:
            resultado = aplicar_reducao_percentual(
                resultado, regra, resolucao.percentual_reducao
            )
        # Dispensado é a DIFERENÇA, não o valor cheio: com 60% o cliente
        # continua devendo 40%, e reportar o cheio superestimaria o benefício.
        cbs_dispensado = cbs_cheio - resultado.valor_cbs
        ibs_dispensado = ibs_cheio - resultado.valor_ibs
        ...

    # As alíquotas exibidas saem do MESMO fator usado no cálculo — nunca de um
    # `0 if aplicada else cheia`, que era verdade só enquanto toda redução era
    # a zero. Com 60% em 2026: 0,9% × 0,40 = 0,36% e 0,1% × 0,40 = 0,04%.
    restante = UM - resolucao.percentual_reducao if resolucao.aplicada else UM
    aliquotas = AliquotasAplicadas(
        cbs_percentual=regra.aliq_cbs * restante * 100,
        ibs_percentual=regra.aliq_ibs * restante * 100,
        is_percentual=regra.aliq_is * 100,
    )

    # Ordem de exibição = ordem dos Anexos na lei, lida do CATÁLOGO — não uma
    # tupla literal no router ('XII' < 'XV' < 'XIII' como texto estaria errado,
    # e uma tupla literal seria um segundo lugar declarando a mesma ordem).
    anexos_aplicados = [a for _, a in sorted(anexos_vistos)]  # {(anexo_ordem, anexo)}
```

### Pattern 6: campos da resposta (`api/schemas_simulate.py`)

```python
class CompradorTipo(StrEnum):
    """Quem ADQUIRE, quando isso muda a alíquota.

    Só os dois tipos que a lei nomeia (arts. 144, II; 145, II; 146, § 1º) —
    não é uma taxonomia de clientes. Informá-lo é DECLARATÓRIO: a simulação não
    verifica imunidade nem validade de CEBAS, e diz isso em `fonte_legal`.
    """

    ORGAO_PUBLICO = "ORGAO_PUBLICO"
    ENTIDADE_CEBAS_SUS = "ENTIDADE_CEBAS_SUS"


class ReducaoItem(BaseModel):
    """Situação do item frente aos 10 Anexos de redução por NCM da LCP 214/2025.

    Redução a ZERO: I (art. 125), XII (art. 144, I), XIII (art. 145, I) e XV
    (art. 148). Redução de 60%: IV (art. 131), V (art. 132), VI (art. 133, §1º),
    VII (art. 135), VIII (art. 136) e IX (art. 138).

    Sucede o bloco `reducao_zero`, renomeado porque o mesmo bloco agora responde
    por uma cadeira de rodas a zero e por um sabão de toucador a 60% (Decisão 9).
    """

    situacao: str
    anexo: str | None = None
    item: str | None = None
    # 100.00 = alíquota reduzida a zero; 60.00 = restam 40% da alíquota da fase.
    percentual_reducao: Decimal | None = None
    dispositivo_legal_ref: str | None = None
    # Preenchido em TODO item dos Anexos IV/V/VI: com `comprador_tipo` ausente é
    # o aviso de que a alíquota real seria zero; com ele presente é a
    # fundamentação do zero aplicado.
    dispositivo_legal_comprador: str | None = None
    # True quando 60% foi aplicado MAS a alíquota seria zero se o comprador
    # fosse órgão público/CEBAS e o payload tivesse informado.
    zero_por_comprador_disponivel: bool = False
    descricao: str | None = None
    descricao_contexto: str | None = None
    ncm_correspondido: str | None = None
    # EXATO | PREFIXO | CAPITULO | EXCECAO — `CAPITULO` é a mais ampla que
    # existe e a única cujo erro é tributo a MENOS (Decisão 7).
    tipo_correspondencia: str | None = None
    itens_correspondentes: list[ItemCorrespondente] = []
    # Itens que EXCLUEM expressamente este código, mesmo quando outro item o
    # inclui — o cogumelo é excluído do XV/2 e incluído pelo VII/14 (Decisão 8).
    itens_excluidos: list[ItemCorrespondente] = []
    cbs_percentual_sem_reducao: Decimal | None = None
    ibs_percentual_sem_reducao: Decimal | None = None
    valor_cbs_dispensado: Decimal | None = None
    valor_ibs_dispensado: Decimal | None = None
    fonte_legal_transicao: str | None = None
```

`ReducaoResumo.fonte_legal` passa a declarar, além dos 10 Anexos: (a) que a correspondência é por
NCM/SH e não verifica as condições textuais de cada item (Anvisa nos IV/XII, norma de órgão
competente nos V/XIII, CMED no VI, MAPA no IX); (b) que os itens **22 a 34 do Anexo IX** (chave NBS
e sem chave) **não são resolvidos**; (c) que `comprador_tipo` é declaratório; e (d) que as listas
dos Anexos IV, V, VI e IX são revisadas **a cada 120 dias** por ato conjunto MF/CGIBS (arts. 131
§2º, 132 §2º, 134 e 138 §10) e que esta tabela não tem dimensão temporal.

---

## Data Flow

```text
1. POST /v1/tax/simulate (X-API-Key + payload) — contrato de entrada ADITIVO
   (comprador_tipo opcional; ausência ⇒ None ⇒ comportamento de hoje)
2. verificar_api_key → tenant_id; divergência com payload.tenant_id → 403
3. Fase/RegraFiscal resolvida uma vez → 422 se não confirmada (inalterado)
4. Coleta dos prefixos (2,4,5,6,7,8) de cada NCM distinto dos itens MERCADORIA
   4a. conjunto vazio   → nenhuma conexão aberta
   4b. conjunto cheio   → 1 query `= ANY(%s)` sobre os 10 Anexos (2 JOINs)
   4c. qualquer exceção → capturada, logada, disponivel=False
5. Por item: engine.calcular + PIS/COFINS + ICMS/ISS + IPI, como hoje
   5a. resolver_item(…, comprador_tipo) → 6 estados, desempate de 6 componentes
   5b. APLICADA e percentual == 1.0000 → aplicar_reducao_a_zero   (INTOCADA)
   5c. APLICADA e percentual == 0.6000 → aplicar_reducao_percentual (NOVA)
6. Agregação: total_cbs/ibs já refletem as reduções; reducao{dispensado,
   anexos_aplicados, itens_por_capitulo, não avaliados}
7. Audit log (nunca propaga) — parecer cita quantos itens, quais Anexos e se
   comprador_tipo foi informado
8. 200 com RespostaSimulacao
```

**Custo por requisição:** continua em no máximo **2 queries** (TIPI + redução), ambas O(1) no
número de itens. A tabela de prefixos cresceu 3,6× (151 → 540 linhas) e continua sendo um `= ANY`
sobre índice; os dois `JOIN` novos são contra 321 e 10 linhas.

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL `taxreformai-pg` / `anexos_reducao*` | `psycopg_pool` via socket unix (`api/db.py`), SELECT | Papel `taxreformai_app`, senha do Secret Manager |
| `motor_calculo` | Import Python direto, in-process | N/A — segue sem tocar em banco |
| Cliente ERP | REST/JSON; **entrada aditiva** (`comprador_tipo`); **saída com bloco renomeado** (`reducao_zero` → `reducao`) e **valores de CBS/IBS mudam** para itens dos 6 Anexos novos | `X-API-Key` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit puro (cálculo) | 60% sobre a alíquota; equivalência `percentual(1.0)` × `a_zero`; IS intacto; recomposição do líquido; o caso de arredondamento | `tests/test_reducoes_percentual.py` | pytest | A função nova, sem banco |
| Unit puro (resolução) | Desempate de 6 componentes; `CAPITULO`; comprador; `itens_excluidos`; `formatar_item` | `tests/test_reducao_resolucao.py` | pytest | Toda a política, sem banco |
| Integration (fake) | AT-001..AT-013 via `TestClient` + `FakePool`; 1 query; pool `None`; pool que explode | `tests/test_api_simulate_reducao.py` | pytest + `TestClient` | Contrato da resposta |
| Integration (Postgres real) | Contagens por Anexo, catálogo/FK/CHECKs, exceção órfã, cabeçalho×sub-item, os 3 testes de sobreposição, remissão do Anexo VII | `tests/test_reducao_db.py` | pytest + `postgres:16` do CI | SQL e constraints |
| Verificação real | 15 casos com o papel `taxreformai_app` no Cloud SQL | `scripts/verificar_reducao_producao.py` via `migrar_banco.yml` | workflow_dispatch | Decisão 13 |
| E2E produção | 4ª chamada do smoke test (`34011190`, `cbs_percentual == 0.36`) | `.github/workflows/deploy.yml` | curl + jq | Decisão 13 |

**Mapa Acceptance Test → teste:**

| AT | Cenário concreto | Onde | Asserção-chave |
|----|------------------|------|----------------|
| AT-001 | `3401.11.90` — sabão de toucador (VIII/1) | api + unit + produção + smoke | `percentual_reducao == 60.00`; `cbs_percentual == 0.36`; `dispositivo_legal_ref == "LCP 214/2025, art. 136, Anexo VIII, item 1"` |
| AT-002 | `1006.30.21` — arroz: I/1 (zero, `100630`) × VII/15 (60%, capítulo `10`) | api + unit + produção | **Zero**, citando o Anexo I; `itens_correspondentes` traz I/1 e VII/15. É a precedência que a lei escreve, saindo do componente 1 |
| AT-003 | `0803.10.00` — banana: XV/3 (zero, `0803`) × VII/14 (60%, capítulo `08`) | api + unit | **Zero**, citando XV/3 — a remissão dupla do item 14 (Anexos I **e** XV) |
| AT-004 | `0306.11.00` — dentro de `0306.1`, expressamente excluído (VII/1, alínea a) | api + unit | `EXCLUIDA_EXPRESSAMENTE`; alíquota **geral**, nunca 60% |
| AT-005 | `0711.20.10` — dentro do capítulo 7, expressamente excetuado por VII/14 | api + unit | **Nunca 60% por VII/14** — mas recebe 60% por **IX/10** (capítulo 7, sementes), com VII/14 em `itens_excluidos` e `tipo_correspondencia == "CAPITULO"`. Ver Limitações, item 2 |
| AT-006 | `8708.99.10` — comando de embreagem (V/1.1, sob o cabeçalho V/1) | api + unit + produção | 60%; `item == "1.1"`; `descricao_contexto` traz o cabeçalho; `zero_por_comprador_disponivel is True` |
| AT-007 | `1109.00.00` — glúten de trigo, capítulo 11 (IX/19: capítulos 10, 11 e 12) | api + unit + produção | 60% citando IX/19; `tipo_correspondencia == "CAPITULO"` — prova múltiplos capítulos no mesmo item |
| AT-008 | Item NBS do Anexo IX (22-33) | db + doc | `SELECT` prova que **nenhuma** linha do Anexo IX tem item entre 22 e 33; `fonte_legal` declara. Um NBS transcrito por engano seria recusado pela CHECK de comprimento (9 dígitos) |
| AT-009 | Anexo IX, item 34 (sem chave) | doc | Nenhum teste pode “resolvê-lo”; documentado no cabeçalho da migração e em `fonte_legal` |
| AT-010 | `3926.90.30` (IV/1) **sem** `comprador_tipo` | api + unit | 60%; `zero_por_comprador_disponivel is True`; `dispositivo_legal_comprador == "LCP 214/2025, art. 144, II"` |
| AT-010b | idem **com** `comprador_tipo=ORGAO_PUBLICO` | api + unit + produção | `percentual_reducao == 100.00`; CBS/IBS zero; os dois dispositivos citados |
| AT-011 | `0403.20.00` — leite fermentado (VII/2, alvo do veto) | api + unit | 60% com o texto **original** do item 2; nenhum vestígio da redação vetada |
| AT-012 | `0405.10.00` (I/5), `0207.43.00` (I/19), `9018.19.80` (XII/1.2), `8713.10.00` (XIII/2.1), `1902.19.00` (I/25), `2106.90.90` (I/4), `0210.99.11` (I/19) | api + unit + produção | **Valores idênticos aos já shipados** — só o nome do bloco e os campos novos mudam no arquivo de teste |
| AT-013 | `2203.00.00` — cerveja | api | `FORA_DO_ANEXO`; CBS 0,9% / IBS 0,1%; nenhum Anexo citado |

**Testes além dos AT, por causa das decisões novas:**

- **Os 35 empates (Decisão 3, componente 2):** `9018.90.99` → **XII/9, 100%**, com 9 itens do Anexo
  IV entre os correspondentes. Sem o componente 2, este caso devolveria 60% — é o teste que falha
  se alguém “simplificar” a chave de desempate.
- **Os 4 casos invertidos (Decisão 4):** `0601.10.00` → IX/11 60%; `9025.19.90` → V/2.3 60%;
  `9018.20.10` → IV/70 60%. Mais o teste SQL que prova que **são só esses 4**.
- **Componente 3 (citação):** `9021.10.10` — presente em **IV/42** (60%, zero se comprador
  qualificado) e em **XII/3** (zero incondicional) — com `comprador_tipo=ORGAO_PUBLICO`. Os dois
  valem zero; a citação tem de ser **XII/3, art. 144, I**, que não depende de provar a qualidade do
  comprador. Sem o componente 3, `-anexo_ordem` citaria o Anexo IV (4 < 12).
- **Arredondamento (Decisão 5):** `valor_base` que produza `base_iva = 137,49` → `valor_cbs ==
  0.49` (recálculo), **não** `0.50` (escalonamento). É o teste que fixa a escolha.
- **Equivalência:** `aplicar_reducao_percentual(r, regra, Decimal("1.0000"))` devolve exatamente o
  mesmo objeto que `aplicar_reducao_a_zero(r)`, para várias bases.
- **`CAPITULO`:** `06031100` (Anexo XV/4, já shipado) passa a devolver `CAPITULO` — a única mudança
  autorizada num valor já asserido, com teste próprio dizendo por quê.
- **Cogumelo (Decisão 8):** `0709.51.00` → APLICADA 60% VII/14 **com** XV/2 em `itens_excluidos`. A
  segunda mudança autorizada.
- **Catálogo:** a CHECK `catalogo_conhecido` recusa `('IV', 4, 1.0)`; a FK recusa um item com
  `anexo = 'XVI'`; `so_percentual_tem_condicao_de_comprador` recusa `('XII', …, 'art. X')`.
- **Ordem de `anexos_aplicados`** vem do catálogo: um payload com itens de I, VII e XV devolve
  `["I","VII","XV"]`, não a ordem alfabética do rótulo romano.
- **Pool `None`** → todos `CONSULTA_INDISPONIVEL`, 200, alíquota geral, `total_cbs_dispensado is
  None`. **Pool que levanta** → 200, não 5xx. **Serviço** → `NAO_APLICAVEL`, nenhuma conexão.

**Testes existentes que devem continuar passando SEM edição:** `tests/test_ipi_resolucao.py`,
`tests/test_api_simulate_ipi.py`, `tests/test_api_simulate.py`, `tests/test_escopo_e_compensacao.py`,
`tests/test_engine.py`, `tests/test_tabela_aliquotas.py`, `tests/test_regime_atual.py`,
`tests/test_schema_postgres.py`, e **os testes já existentes de `aplicar_reducao_a_zero`** — estes
últimos são a prova de que a extração de `_recompor` não mudou comportamento. Se algum precisar
mudar, é regressão.

---

## Error Handling

| Error Type | Handling Strategy | HTTP | Retry? |
|------------|---------------------|------|--------|
| NCM fora dos 10 Anexos | `FORA_DO_ANEXO`, alíquota geral da fase | 200 | Não |
| NCM excluído pelo próprio item | `EXCLUIDA_EXPRESSAMENTE` + citação; **nunca** redução | 200 | Não |
| NCM excluído por um item **e** incluído por outro | `APLICADA` pelo que inclui, com o que exclui em `itens_excluidos` (Decisão 8) | 200 | Não |
| NCM ilegível | `NCM_NAO_RECONHECIDO`, sem consultar o banco | 200 | Não |
| Cloud SQL fora do ar / grant faltando / **janela do rename** | `CONSULTA_INDISPONIVEL` + `logger.exception`; alíquota geral | 200 | Sim, pelo cliente |
| `db_pool is None` | Idem, sem log de exceção — estado esperado | 200 | N/A |
| Item `natureza=SERVICO` | `NAO_APLICAVEL`, sem coletar prefixo | 200 | N/A |
| `comprador_tipo` fora do enum | 422 do Pydantic, **antes** de qualquer cálculo | 422 | Não |
| Fase sem alíquota confirmada (2027+) | 422 **antes** do laço, como hoje | 422 | N/A |

Nenhum estado de resolução novo — a máquina de 6 estados da Decisão 7 do Anexo I continua certa; o
que mudou foi o universo a que `FORA_DO_ANEXO` se refere (agora 10 Anexos) e o fato de `APLICADA`
carregar um percentual.

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `DB_INSTANCE_CONNECTION_NAME` | string | — | Já existente; ausente ⇒ `CONSULTA_INDISPONIVEL` |
| `DB_USER` | string | `taxreformai_app` | Papel que precisa do `GRANT SELECT` nas **3** tabelas (reemitido pela 009) |
| `verificar_reducao` (input de workflow) | `sim`/`nao` | `sim` | **Renomeia** `verificar_reducao_zero` em `migrar_banco.yml` |

Nenhuma variável de ambiente nova na aplicação, nenhuma mudança de Terraform. Duas migrações novas,
aplicadas pelo fluxo de sempre (`migrar_banco.yml`, guarda `MIGRAR`).

---

## Security Considerations

- **Sem SQL dinâmico com dado do cliente.** `= ANY(%s)` recebe lista como parâmetro vinculado, e
  todo prefixo passa por `digitos_ncm`/`prefixos_ncm`, que só deixam passar `[0-9]{2,8}`.
  `comprador_tipo` é enum do Pydantic e **nunca** chega ao SQL — ele só escolhe um `Decimal` em
  memória.
- **O `LIKE … || '%'` das asserções** opera sobre colunas da própria tabela (prefixos validados por
  CHECK como só-dígitos), dentro da migração, sem nenhum dado de requisição.
- **`comprador_tipo` não é PII.** É uma classificação da operação (“órgão público” / “entidade
  CEBAS”), não uma identificação de pessoa. Vai para o audit log dentro de `payload_calculo`, como
  o resto do payload, sob o RLS do tenant.
- **Sem RLS nas 3 tabelas, deliberadamente** — lei federal, idêntica para todo tenant (mesma
  decisão de `aliquotas_ipi_tipi`). O rename preserva privilégios; a 009 os reemite.
- **Privilégio mínimo preservado:** só `SELECT` para o papel de runtime; escrita exclusiva do papel
  admin via migração.
- **Nenhum `DROP TABLE`.** As operações destrutivas são um `DROP COLUMN` (`anexo_ordem`, cujo
  conteúdo passa a viver no catálogo, semeado **antes** na mesma transação) e `DROP CONSTRAINT`
  (substituída por FK). O `/build` deve manter as duas migrações em transação única, como o
  `db/migrador.py` já faz.
- **Sem PII no dado legal.** NCM, descrição de produto e dispositivo legal são públicos;
  enumeração não é vazamento (os 10 Anexos estão no DOU).

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `api.reducao` quando a consulta falha — o **único** sinal em runtime de que a redução parou de ser aplicada (inclusive na janela do rename) |
| Resposta | `reducao.consulta_disponivel`, `anexos_aplicados[]`, `itens_nao_avaliados[]` e — novo — `itens_por_capitulo` tornam a degradação, a cobertura e o **risco de correspondência ampla** inspecionáveis por máquina |
| Audit log | O parecer passa a registrar o percentual aplicado por item e se `comprador_tipo` foi informado — é o que permite, depois, medir quantos clientes usam o campo |
| Metrics | Fora de escopo (mesmo tratamento das features anteriores) |
| Verificação ativa | `scripts/verificar_reducao_producao.py` (15 casos) + 4ª asserção no smoke test do deploy |

---

## Limitações declaradas (e por que não são resolvidas aqui)

1. **14 prefixos de 2 dígitos concedem redução a capítulos inteiros da NCM, e o texto do item
   restringe.** O pior caso é o Capítulo **25** (IX/3, “corretivos de solo”), que na NCM inclui
   cimento, mármore e gesso; em seguida vêm os capítulos 10, 11, 12 e 15 (IX/10, 19, 21 —
   condicionados a “destinados diretamente à fabricação de ração”) e 7 e 8 (VII/14, IX/10). Esta é
   a **única limitação desta feature cujo erro é na direção perigosa** (tributo a menos), e por
   isso está em primeiro lugar. Mitigação: `tipo_correspondencia == "CAPITULO"` e
   `reducao.itens_por_capitulo` (Decisão 7) tornam o caso filtrável por máquina; a `descricao`
   literal volta na resposta. Fechar de verdade exige atributos por SKU (destinação, registro no
   MAPA) — `API_EMPRESA_SKUS`, posição 3 da sequência.
2. **`0711.20.10` (e o resto da posição 07.11) recebe 60% por IX/10, apesar de o Anexo VII/14 a
   excetuar expressamente.** É consequência direta de a exceção ser escopada ao item (Decisão 8) e
   de o Anexo IX cobrir o capítulo 7 inteiro. Não há regra uniforme que acerte este caso **e** o do
   cogumelo ao mesmo tempo; a resposta mostra os dois lados (`itens_excluidos`), e a limitação 1 é
   a mesma causa raiz.
3. **As condições textuais de cada item não são verificadas** — Anvisa (arts. 131 §1º, 144 §1º),
   norma de órgão público competente (arts. 132 §1º, 145 §1º), compromisso CMED (art. 133 §2º),
   registro no MAPA (art. 138 §1º), “em conformidade com as definições e demais requisitos da
   legislação específica” (quase todo o Anexo IX). A simulação aplica pelo código e devolve o texto
   do item para o cliente conferir. Mesma classe já aceita nas 3 features anteriores.
4. **`9619.00.00` tem duas alíquotas diferentes na mesma lei e um código só.** O Anexo VIII/7
   (fraldas e artigos higiênicos semelhantes) é 60%; o **art. 147** — que não tem Anexo, e por isso
   está fora desta tabela — reduz a **zero** tampões, absorventes, calcinhas absorventes e
   coletores menstruais, no mesmo código. Indecidível por NCM. Esta feature aplica 60%
   (over-tributa o absorvente, direção segura) e declara. O art. 147 é candidato a feature própria
   e vai para o roadmap no `/ship`.
5. **`comprador_tipo` é declaratório.** A simulação não verifica imunidade, não valida CEBAS e não
   consulta o SUS; aplica zero porque o cliente afirmou. Mesma natureza de `bem_importado` e
   `regime_apuracao`, e dito em `fonte_legal`.
6. **As listas dos Anexos IV, V, VI e IX são revisadas a cada 120 dias** por ato conjunto
   MF/CGIBS (arts. 131 §2º, 132 §2º, 134, 138 §10) — muito mais dinâmicas que o Anexo I. A tabela
   não tem `vigencia_inicio`/`vigencia_fim` e nenhum desses atos é ingerido. Fechar isso é um
   pipeline de ingestão, não um schema.
7. **Os 12 itens NBS do Anexo IX (22-33) não são resolvidos**, e o item 34 não tem chave nenhuma
   (Decisão 10). Os primeiros dependem da posição 14 do roadmap; o segundo não é resolvível por
   nenhuma delas.
8. **O art. 137 (60% a produtos agropecuários, aquícolas, pesqueiros, florestais e extrativistas
   vegetais *in natura*) fica fora**, como o DEFINE determinou: ele não cita Anexo nenhum — define
   por categoria, com os §§1º a 3º explicando o que é “in natura”. É mecanismo de correspondência
   por natureza do produto, não por código; candidato a feature própria.
9. **O diferimento do art. 138 §2º não é redução** — é adiamento do recolhimento em certas cadeias
   B2B com produtor rural não contribuinte. Identificado, documentado, e nenhuma linha de cálculo
   nesta feature. (Os §§ 4º e 9º-II do mesmo artigo foram vetados na sanção original — achado 7.)
10. **Sem dimensão temporal, e 2026 segue sendo a única fase com efeito prático** (2027-2028 é
    recusada com 422 pela CBS pendente do art. 347; 2029+ não existe em `TabelaAliquotasSeed`).
11. **Os 6 Anexos restantes continuam sem efeito** (II, III, X, XI por NBS; XVI, XVII, XVIII-XXIII
    por natureza própria). O catálogo declara em 10 linhas exatamente quais Anexos esta tabela
    conhece.

---

## Open Questions do DEFINE — resolvidas aqui

| # | Pergunta | Resolução |
|---|----------|-----------|
| 1 | Como tratar a condição de comprador (IV/V/VI) | **Decisão 6** — `comprador_tipo` opcional no payload, `None` = não informado. A lacuna é fechada, não documentada: sem o campo, o MUST “nunca aplicar 60% quando o comprador é conhecido como órgão público” seria insatisfazível por construção |
| 2 | Forma exata do schema (estender × tabela paralela) | **Decisão 1** — estender, e por necessidade: 117 pares de sobreposição entre os dois grupos tornam a resolução em separado **incorreta**, não só mais cara. Mais o catálogo de 10 linhas (Decisão 2) |
| 3 | Assinatura de `aplicar_reducao_percentual` | **Decisão 5** — função nova, que recebe a `RegraFiscal` e reduz a **alíquota** (não o valor arredondado); `aplicar_reducao_a_zero` mantém assinatura e comportamento, e um teste prova a equivalência entre as duas |
| 4 | Verificação automatizada de overlap (`SHOULD`) | **Decisão 12** — três testes SQL, e a `A-003` do DEFINE é **refutada**: existem 117 pares, não zero |
| 5 | Múltiplos prefixos curtos por item | Suportado sem mudança: o mecanismo 1:N já existia. **Nenhum limite por item** — o item 7 do Anexo IX gera 29 linhas e o mecanismo não nota a diferença |
| — | `A-003` (não há overlap além do Anexo VII) | **FALSA.** É o achado 1, e reorganizou o design inteiro |
| — | `A-005` (o `/design` decide o tratamento da lacuna do comprador) | Decidido: **Decisão 6** |
| — | `COULD` (cláusulas “exceto” não codificáveis são inócuas?) | Atendido **por construção** para as 2 descritivas do Anexo IV (a regra as classifica pela estrutura da NCM, sem precisar da TIPI); as 8 não codificáveis continuam sendo limitação declarada |

**Sete perguntas que o DEFINE não previu e o Design precisou responder**, todas descobertas lendo a
fonte primária e comparando dado com dado: se os dois grupos de Anexos se sobrepõem (sim, 117
vezes); o que é multiplicado por 0,40 (a alíquota, não o valor); qual artigo institui o Anexo VI
(o §1º do art. 133, não o caput); quantos prefixos de capítulo existem (14, não 2); o que fazer
quando um Anexo exclui e outro inclui o mesmo código (Decisão 8); o que fazer com `9619.00.00`,
que a mesma lei tributa de dois jeitos (limitação 4); e se o rename da tabela e do bloco se
justifica pela terceira vez (sim, Decisões 1 e 9).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent | Versão inicial, a partir de `DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NCM.md` v1.0; transcrição literal dos 6 Anexos extraída da estrutura de tabela do DOU e leitura integral dos arts. 129-148 contra a fonte primária do Senado; verificação programática de sobreposição refutando `A-003` (117 pares); contagens corrigidas (Anexo V 26→29; item 7 do Anexo IX 28→29 códigos; 13 códigos do Anexo IV não são de 8 dígitos); LC 227/2026 reconfirmada contra a lista literal de alterações |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NCM.md`

**Antes de começar, uma confirmação:** a Decisão 9 renomeia o bloco da resposta pela terceira vez em
três features (`cesta_basica` → `reducao_zero` → `reducao`). O protocolo da feature anterior foi
perguntar diretamente ao Jonatas antes do `/build`; o mesmo vale aqui.

Ordem sugerida de implementação: migração 009 e o catálogo (1) → migração 010 e seu seed (2) →
repositório (3) → `engine.valor_do_tributo` e `aplicar_reducao_percentual` (4, 5) → resolução (6) →
schemas e router (7, 8, 9) → testes (10-13) → script e workflows (14-16) → `CLAUDE.md` (17).

**A feature só é dada como pronta depois das duas verificações da Decisão 13** —
`migrar_banco.yml` com `verificar_reducao=sim` (15 casos, papel de runtime) e a 4ª chamada do smoke
test do `deploy.yml` com `34011190` (`cbs_percentual == 0.36`) —, **nessa ordem**. Então `/ship`,
levando ao roadmap os dois achados fora de escopo: o **art. 147** (`9619.00.00` a zero, fora de
Anexo) e o **art. 137** (60% a produtos *in natura*, sem Anexo).
