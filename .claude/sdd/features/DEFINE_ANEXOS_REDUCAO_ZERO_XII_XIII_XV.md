# DEFINE: Anexos XII, XIII e XV — Redução a Zero/100% de CBS/IBS por NCM

> Estender o mecanismo já shipado no Anexo I (`aplicar_reducao_a_zero`, `api/ncm.py`, prefixo de
> dígitos) para cobrir os Anexos XII (dispositivos médicos), XIII (acessibilidade) e XV
> (hortícolas, frutas e ovos) da LCP 214/2025 — os 3 Anexos restantes de redução a zero/100% por
> NCM puro — e conectar `/v1/tax/simulate` a eles, citando o Anexo e item corretos.
>
> **Posição na sequência:** 12 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Primeira das 6 features que cobrem os 16 Anexos restantes da LCP 214/2025 mais
> o Simples Nacional — o Anexo I foi shipado em `REGRAS_TRIBUTARIAS_CACHE` (posição 2).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_ZERO_XII_XIII_XV |
| **Date** | 2026-07-28 |
| **Author** | define-agent |
| **Status** | Designed (ver `DESIGN_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`, 2026-07-28) |
| **Clarity Score** | 15/15 |

---

## Problem Statement

`/v1/tax/simulate` só conhece o Anexo I (Cesta Básica Nacional) como fonte de redução a zero de
CBS/IBS. Os Anexos XII (dispositivos médicos), XIII (acessibilidade para pessoas com deficiência)
e XV (hortícolas, frutas e ovos) da LCP 214/2025 também zeram CBS/IBS por NCM — 56 linhas de
código/prefixo distribuídas em 29 itens — mas hoje são simulados com a alíquota geral da fase,
superestimando a carga tributária projetada para cadeiras de rodas, tomógrafos, implantes
cocleares, hortaliças, frutas e ovos.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Simula CBS/IBS de dispositivos médicos, produtos de acessibilidade e hortifrutigranjeiros com a alíquota geral da fase, quando a lei já garante alíquota zero/100% para esses produtos especificamente |
| Controller/CFO usando o simulador | Consumidor indireto do produto (via ERP ou frontend) | Não consegue demonstrar o benefício fiscal real de setores sensíveis (saúde, acessibilidade, alimentação in natura) numa simulação que se propõe auditável |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo completo dos Anexos XII (17 itens/24 linhas), XIII (6 itens/7 linhas) e XV (6 itens/25 linhas) verificado contra fonte primária nesta sessão — ver "Verificação de Fonte Primária" e "Os 3 Anexos, item a item" — nenhum código aceito de memória nem só da contagem aproximada do brainstorm |
| **MUST** | Decisão explícita no `/design` sobre como o schema do Anexo I (`cesta_basica_anexo_i`/`_ncm`) acomoda **3 diferenças estruturais que o brainstorm não previu** (ver "Achados que corrigem a estimativa do brainstorm"): numeração de item reiniciando em 1 por Anexo, itens com numeração decimal (`1.1`, `2.2`), e um prefixo de **2 dígitos** (capítulo) no Anexo XV — nunca tratado por adivinhação ou por um schema que não consiga representar o dado literal |
| **MUST** | `/v1/tax/simulate` aplica CBS/IBS zero ao item de mercadoria cujo NCM bate com um item resolvido de XII, XIII **ou** XV, citando o Anexo e item exatos (`dispositivo_legal_ref` no formato "LCP 214/2025, Anexo {XII\|XIII\|XV}, item N") |
| **MUST** | As exceções explícitas dos 2 itens que as têm (Anexo XII, item 5 e item 7-c; Anexo XV, item 2) nunca recebem zero — mesmo mecanismo de prefixo+exceção do Anexo I |
| **MUST** | A sobreposição intra-Anexo do Anexo XII (itens 1.2, 1.3 e 14 citam o mesmo código `9018.19.80`) resolvida com regra de desempate determinística — mesmo princípio da Decisão 4 do `/design` do Anexo I, generalizado para 3 itens em vez de 2 e para numeração decimal |
| **MUST** | Confirmado, nesta sessão e contra fonte primária, que a LC 227/2026 **não** alterou os Anexos XII, XIII nem XV |
| **MUST** | Itens de mercadoria cujo NCM não bate com nenhum item de I, XII, XIII ou XV continuam recebendo a alíquota geral da fase — zero regressão no Anexo I nem no caminho já existente |
| **MUST** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura — `aplicar_reducao_a_zero` já existe e é agnóstico a qual Anexo populou a tabela; nenhuma função de cálculo nova |
| **SHOULD** | Overlap entre os NCMs de XII/XIII/XV e os do Anexo I verificado (análise nesta sessão não encontrou nenhum — ver "Overlap entre os 4 Anexos zero" — mas a confirmação programática fica registrada como recomendação ao `/design`, dado o volume 4x maior que o do Anexo I sozinho) |
| **SHOULD** | Teste cobrindo ao menos 1 item de cada tipo de correspondência novo: prefixo de 2 dígitos (capítulo), prefixo+exceção do Anexo XII, e o desempate de 3 vias do Anexo XII |
| **COULD** | Documentar, para quem for popular a migração, quais itens têm cláusula "exceto" **descritiva** (não gera linha de exceção porque o código do próprio item já é exato de 8 dígitos e distinto dos códigos citados — Anexo XII, itens 1.3 e 11) vs. "exceto" **operante** (gera linha de exceção — Anexo XII, itens 5 e 7-c; Anexo XV, item 2) — para não transcrever a mesma palavra-chave de duas formas inconsistentes |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

Mesma fonte primária já qualificada e usada em `REGRAS_TRIBUTARIAS_CACHE` (Anexo I): o portal
oficial do Senado Federal (`legis.senado.leg.br`), que espelha a "Publicação Original" do DOU.
`planalto.gov.br` e domínios irmãos continuam inacessíveis deste ambiente (mesmo padrão já
registrado nas duas features anteriores). O acesso a `legis.senado.leg.br` só respondeu 200 com um
**header de `User-Agent` de navegador** — sem ele, 403 (aviso herdado do brainstorm, confirmado
nesta sessão).

**O que foi verificado, com URL e conteúdo real, nesta sessão (2026-07-28):**

1. **Texto integral do Anexo XII** — `https://legis.senado.leg.br/norma/40180341/publicacao/40180960`
   ("Publicação Original de Anexo", DOU Edição Extra nº 11-B de 16/01/2025, p. 54, col. 1). HTTP 200.
   Tabela de 3 colunas (ITEM/DESCRIÇÃO/NCM-SH), 17 itens, 21 linhas de código/prefixo de inclusão,
   3 linhas de exceção — transcrição completa na próxima seção.
2. **Texto integral do Anexo XIII** — `https://legis.senado.leg.br/norma/40180341/publicacao/40180966`
   (mesma publicação, p. 54, col. 1). HTTP 200. Tabela de 3 colunas, 6 itens, 7 linhas de código,
   **nenhuma** exceção, **nenhum** prefixo mais curto que 8 dígitos.
3. **Texto integral do Anexo XV** — `https://legis.senado.leg.br/norma/40180341/publicacao/40181038`
   (mesma publicação, p. 58, col. 1). HTTP 200. Tabela de **2 colunas** (não tem coluna de NCM
   separada — os códigos aparecem embutidos na "DESCRIÇÃO DO PRODUTO"), 6 itens, 23 linhas de
   código/prefixo de inclusão, 2 linhas de exceção.
4. **Página de detalhe da norma** (`https://legis.senado.leg.br/norma/40180341`, mesma página já
   usada no `/define` do Anexo I para checar a LC 227/2026): a seção "Normas posteriores" lista
   explicitamente, sob a "Mensagem de Veto Parcial nº 36 de 13/01/2026" (LC 227/2026), as únicas
   alterações a Anexos da LCP 214/2025: **"Anexo 7 — Alteração Vetada"**, **"Anexo 14 —
   Revogação"**, **"Anexo 20 — Alteração"**, **"Anexo 21 — Alteração"**. **Os Anexos XII, XIII e XV
   não aparecem nessa lista** — confirmado nesta sessão, não herdado da investigação anterior
   (`LC_227_2026_ATUALIZACAO_LEGAL`, que nunca tinha checado especificamente estes 3 Anexos).
   Fecha o Aviso Herdado nº 1.
5. **Republicação/errata**: a mesma página lista uma única "Republicação de Anexo" (a do Anexo
   XXIII, já identificada no `/define` do Anexo I) e um único veto parcial de Anexo ("Anexo 11 —
   Veto de Parte do Texto", itens 1.4/1.5/1.8/1.9 — não é nenhum dos 3 Anexos desta feature).
   **Nenhuma republicação/errata/veto registrado para XII, XIII ou XV** — o texto das seções acima
   é o texto vigente.

Consultados em 2026-07-28.

---

## Os 3 Anexos, item a item (fonte primária, verificados nesta sessão)

### Anexo XII — Dispositivos médicos (17 itens, 21 inclusões + 3 exceções = 24 linhas)

| Item | Descrição (resumida) | Código(s)/prefixo(s) NCM/SH | Tipo |
|------|------------------------|--------------------------------|------|
| 1.1 | Eletrocardiógrafos | `9018.11.00` | EXATO |
| 1.2 | Eletroencefalógrafos | `9018.19.80` | EXATO — **mesmo código dos itens 1.3 e 14** |
| 1.3 | Aparelhos de eletrodiagnóstico, exceto os códigos 9018.11.00, 9018.12.10, 9018.12.90, 9018.13.00, 9018.14.10, 9018.14.20, 9018.14.90, 9018.19.10 e 9018.19.20 | `9018.19.80` | EXATO — o "exceto" é **descritivo**, não operante: o próprio código do item já é de 8 dígitos e não contém nenhum dos códigos citados como exceção; nenhuma linha de exclusão é necessária |
| 2 | Aparelhos de raios ultravioleta ou infravermelhos | `9018.20` | PREFIXO (6 dígitos) |
| 3 | Artigos e aparelhos ortopédicos | `9021.10.10` | EXATO |
| 4 | Artigos e aparelhos para fraturas | `9021.10.20` | EXATO |
| 5 | Artigos e aparelhos de prótese, exceto os dentários e os produtos dos códigos 9021.39.91 e 9021.39.99 | `9021.3` | **PREFIXO (5 dígitos) + EXCEÇÃO operante** (2 códigos de 8 dígitos, ambos prefixados por `90213`) |
| 6 | Tomógrafo computadorizado | `9022.12.00` | EXATO |
| 7-a | Aparelhos de raio X, móveis | `9022.13` | PREFIXO (6 dígitos) |
| 7-b | Aparelhos de raio X, móveis | `9022.14` | PREFIXO (6 dígitos) |
| 7-c | Aparelhos de raio X, móveis, exceto o código 9022.19.91 | `9022.19` | **PREFIXO (6 dígitos) + EXCEÇÃO operante** (1 código, prefixado por `902219`) |
| 8 | Aparelho de radiocobalto (bomba de cobalto) | `9022.21.10` | EXATO |
| 9 | Aparelho de crioterapia | `9018.90.99` | EXATO |
| 10 | Aparelho de gamaterapia | `9022.21.20` | EXATO |
| 11 | Aparelhos de radiações alfa/beta/gama para usos médicos, exceto os códigos 9022.21.10 e 9022.21.20 | `9022.21.90` | EXATO — "exceto" **descritivo**: código próprio já exato e distinto dos citados (que são os itens 8 e 10) |
| 12 | Densímetros, areômetros, termômetros, barômetros, higrômetros e psicrômetros | `90.25` | PREFIXO (4 dígitos) |
| 13 | Respirador | `9019.20.40` | EXATO |
| 14 | Monitor multiparâmetros | `9018.19.80` | EXATO — **mesmo código dos itens 1.2 e 1.3** |
| 15 | Bomba de infusão | `9018.90.10` | EXATO |
| 16 | Aparelhos de diagnóstico por ressonância magnética | `9018.13.00` | EXATO |
| 17 | Aparelhos de ultrassom | `9018.12` | PREFIXO (6 dígitos) |

**Fonte:** `LCP 214/2025, Anexo XII` (redução a zero de IBS/CBS sobre dispositivos médicos).
**Contagem:** 21 linhas de inclusão (14 EXATO + 5 PREFIXO sem exceção + 2 PREFIXO com exceção
operante) + 3 linhas de exceção (2 do item 5, 1 do item 7-c) = **24 linhas**.

### Anexo XIII — Acessibilidade para pessoas com deficiência (6 itens, 7 linhas, todas EXATO)

| Item | Descrição | Código NCM/SH | Tipo |
|------|-----------|----------------|------|
| 1 | Barra de apoio para pessoa com deficiência física | `8302.41.00` | EXATO |
| 2.1 | Cadeira de rodas sem mecanismo de propulsão | `8713.10.00` | EXATO |
| 2.2 | Cadeiras de rodas com motor/mecanismo de propulsão e outros veículos para pessoas com incapacidade | `8713.90.00` | EXATO |
| 3 | Partes e acessórios exclusivos de cadeiras de rodas ou outros veículos para deficientes | `8714.20.00` | EXATO |
| 4 | Aparelhos para facilitar a audição dos surdos, exceto partes e acessórios | `9021.40.00` | EXATO |
| 5 | Partes e acessórios de aparelhos para facilitar a audição dos surdos | `9021.90.92` | EXATO |
| 6 | Implantes cocleares | `9021.90.19` | EXATO |

**Fonte:** `LCP 214/2025, Anexo XIII` (redução a zero de IBS/CBS sobre dispositivos de
acessibilidade). **Contagem:** 7/7 itens são correspondência exata de 8 dígitos — **o Anexo mais
simples dos 3**, mais simples ainda do que a estimativa do brainstorm (~9 códigos, nenhuma
exceção). Nenhum prefixo mais curto que 8 dígitos, nenhuma exceção.

### Anexo XV — Hortícolas, frutas e ovos (6 itens, 23 inclusões + 2 exceções = 25 linhas)

> Diferença estrutural do Anexo I e dos outros dois desta feature: **não há coluna de NCM
> separada** — a tabela oficial só tem "ITEM" e "DESCRIÇÃO DO PRODUTO", com os códigos embutidos no
> texto corrido, igual ao observado pelo brainstorm.

| Item | Descrição (resumida) | Código(s)/prefixo(s) citados | Tipo |
|------|------------------------|---------------------------------|------|
| 1 | Ovos | `0407.2` | PREFIXO (5 dígitos) |
| 2 | Produtos hortícolas das posições 07.01, 07.02.00.00, 07.03, 07.04, 07.05, 07.06, 0707.00.00, 07.08, 07.09 e 07.10, exceto cogumelos/trufas da subposição 0709.5 e do código 0710.80.00 | `0701` `07020000` `0703` `0704` `0705` `0706` `07070000` `0708` `0709` `0710` | **PREFIXO (4 e 8 dígitos) + EXCEÇÃO operante** (2 códigos: `0709.5` prefixado por `0709`, incluído acima; `0710.80.00` prefixado por `0710`, incluído acima) |
| 3 | Frutas frescas ou refrigeradas e congeladas sem adição de açúcar/edulcorante, posições 08.03 a 08.11 | `0803` `0804` `0805` `0806` `0807` `0808` `0809` `0810` `0811` | PREFIXO (4 dígitos), sem exceção — nenhum código de exclusão citado no texto |
| 4 | Plantas e produtos de floricultura relativos à horticultura, cultivados para fins alimentares, ornamentais ou medicinais, do **Capítulo 6** da NCM/SH | `06` | **PREFIXO DE 2 DÍGITOS (capítulo)** — achado novo, ver "Achados que corrigem a estimativa do brainstorm", item 3 |
| 5 | Raízes e tubérculos | `0714` | PREFIXO (4 dígitos) |
| 6 | Cocos | `0801.1` | PREFIXO (5 dígitos) |

**Fonte:** `LCP 214/2025, Anexo XV` (redução de 100% de IBS/CBS — funcionalmente equivalente a
zero). **Contagem:** 23 linhas de inclusão + 2 linhas de exceção (ambas do item 2) = **25 linhas**.
**Nenhum item é EXATO de 8 dígitos** — todos os 6 itens do Anexo XV citam posição, subposição ou
capítulo, nunca um código completo.

**Achado favorável, sem ação necessária**: o próprio cabeçalho oficial do Anexo I já se
autodenomina *"PRODUTOS DESTINADOS À ALIMENTAÇÃO HUMANA [...] (EXCLUSIVE PRODUTOS HORTÍCOLAS,
FRUTAS E OVOS, RELACIONADOS NO ANEXO XV)"* — ou seja, a própria lei desenhou os dois Anexos para
serem mutuamente exclusivos por categoria de produto. Combinado com a checagem de capítulos feita
nesta sessão (Anexo I não cita nenhuma posição dos capítulos 04 [ovos], 06, 07 ou 08 usados pelo
Anexo XV), **não há overlap entre o Anexo I e o Anexo XV** — ver também "Overlap entre os 4 Anexos
zero" abaixo.

**Contagem consolidada (XII + XIII + XV):** 29 itens (contando sub-itens 1.1-1.3/2.1-2.2 como
itens próprios), **56 linhas de código/prefixo** (24 + 7 + 25), das quais **5 são exceções
operantes** (3 no XII, 2 no XV) e **21 são EXATO de 8 dígitos** (14 no XII, 7 no XIII).

---

## Achados que corrigem a estimativa do brainstorm

O brainstorm estimou esta feature como "mais simples" que o Anexo I porque reaproveitaria o
mecanismo sem alteração. A verificação literal contra fonte primária desta sessão encontrou
**3 diferenças estruturais que o mecanismo atual (schema da migração 005 + `api/ncm.py`) não
representa como está** — registradas aqui explicitamente, não escondidas:

1. **Numeração de item reinicia em 1 por Anexo.** `cesta_basica_anexo_i.item` é `SMALLINT PRIMARY
   KEY` — um único namespace global de 1 a 26. O Anexo XII também tem um "item 1", o Anexo XIII
   também tem um "item 1" etc. Não é possível inserir os 3 Anexos novos na mesma tabela sem uma
   coluna `anexo` fazendo parte da chave (`(anexo, item)` em vez de `item` sozinho) — isso já era
   antecipado pela Decisão 1 do brainstorm em nível conceitual ("uma coluna `anexo`"), mas o
   `/design` precisa tratar como mudança de **chave primária**, não como coluna decorativa.
2. **Itens com numeração decimal.** O Anexo XII tem itens `1.1`, `1.2`, `1.3` (sob o item 1) e o
   Anexo XIII tem `2.1`, `2.2` (sob o item 2) — o Anexo XV, como o Anexo I, usa só inteiros. Um
   `SMALLINT` não representa `"1.1"`. O `/design` precisa decidir a representação (ex.: `TEXT`,
   ou duas colunas `item_principal SMALLINT` + `sub_item SMALLINT NULL`) — decisão de schema, não
   só de dado.
3. **Um prefixo de 2 dígitos (capítulo), nunca visto antes no projeto.** O Anexo XV, item 4, cita
   **"Capítulo 6 da NCM/SH"** — um prefixo de 2 dígitos (`"06"`). O schema atual proíbe isso
   explicitamente: a `CHECK (prefixo ~ '^[0-9]{4,8}$')` da migração 005 e
   `api/ncm.py::_COMPRIMENTOS_PREFIXO = (4, 5, 6, 7, 8)` **rejeitam qualquer prefixo menor que 4
   dígitos**. Este não é um caso não previsto — o comentário da própria migração 005 já registrava:
   *"Se um Anexo futuro citar capítulo (2 dígitos), os DOIS mudam juntos"* — mas é a primeira vez
   que isso de fato acontece, e o `/design` precisa alargar os dois lados do acoplamento (`CHECK` e
   `_COMPRIMENTOS_PREFIXO`) de `4..8` para `2..8`.

Nenhuma dessas 3 diferenças exige um mecanismo de cálculo novo (o "prefixo de dígitos, comprimento
variável" da Decisão 1 do Anexo I continua sendo a resposta certa) — mas todas as 3 são mudanças de
**schema**, não só inserção de linha. Corrige a premissa do brainstorm de que esta feature seria
"só dado novo, zero decisão de design". É menor que desenhar o Anexo I do zero, mas maior que
"copiar e colar 26 INSERTs a mais".

**Achado adicional, dentro do mesmo Anexo (não entre Anexos):** o Anexo XII tem uma sobreposição de
**3 itens** (1.2, 1.3, 14) citando o mesmíssimo código `9018.19.80` — mais itens em conflito do que
qualquer par do Anexo I (que tinha no máximo 2: itens 4/26 e 15/25). A regra de desempate da
Decisão 4 do `/design` do Anexo I ("prefixo mais longo vence; empate quebrado pelo menor número de
item") precisa ser confirmada como válida para 3 vias e para números de item decimais (comparar
`1.2` com `14` exige decidir se a comparação é numérica por partes ou lexicográfica — `"14" <
"1.2"` lexicograficamente, mas `1.2 < 14` numericamente; o texto legal claramente pretende os itens
em ordem numérica, não lexicográfica).

---

## Overlap entre os 4 Anexos zero (I, XII, XIII, XV)

Verificado nesta sessão por análise de capítulo/posição NCM (não por script automatizado — ver
`SHOULD` correspondente para a recomendação ao `/design`):

- **Anexo I** cobre alimentos dos capítulos 04, 07 (só farinha de mandioca/tapioca, códigos
  específicos), 09, 10, 11, 15, 17, 19, 21, 25 e posições de carne/peixe (02, 03) — nunca as
  posições 07.01-07.10 nem 08.xx nem 0407.2 usadas pelo Anexo XV (exclusão desenhada pela própria
  lei, ver seção anterior).
- **Anexo XII** cobre majoritariamente o capítulo 90 (instrumentos/aparelhos) mais a posição 90.25
  — nenhuma sobreposição de capítulo com I, XIII ou XV.
- **Anexo XIII** cobre os capítulos 83 (`8302.41.00`), 87 (`8713`/`8714`) e 90 (`9021.4`/`9021.90`)
  — os códigos do capítulo 90 (`9021.40.00`, `9021.90.92`, `9021.90.19`) não colidem com nenhum
  prefixo do Anexo XII (que usa `9021.10.xx`, `9021.3` e a família `9022.xx`/`9018.xx`;
  `9021.90.xx` nunca é citado por XII).
- **Anexo XV** cobre capítulos 04 (só `0407.2`), 06, 07 e 08 — sem sobreposição com I (ver acima),
  XII ou XIII (capítulos totalmente diferentes).

**Conclusão desta sessão: nenhum overlap entre os 4 Anexos zero.** Diferente do Anexo I (que tinha
2 pares de overlap *dentro de si mesmo*), aqui o único overlap encontrado é *intra*-Anexo XII (ver
seção anterior), não *entre* Anexos. Isso é registrado como verificação manual, não como prova
programática — dado que o volume total (I: 95 linhas + esta feature: 56 linhas = 151 linhas)
começa a tornar inspeção manual menos confiável, fica como recomendação `SHOULD` que o `/design`
rode uma checagem automatizada (ex.: um teste que gera todos os prefixos de todas as linhas e
confere que nenhum par de Anexos diferentes compartilha um código de 8 dígitos concreto) antes do
`/build`.

---

## Success Criteria

- [ ] Conteúdo dos Anexos XII (17 itens/24 linhas), XIII (6 itens/7 linhas) e XV (6 itens/25
      linhas) verificado contra fonte primária (Senado Federal/DOU), com URLs e data de acesso
      registrados neste documento — concluído nesta sessão
- [ ] Confirmado contra fonte primária que a LC 227/2026 não alterou nenhum dos 3 Anexos —
      concluído nesta sessão (item 4 da "Verificação de Fonte Primária")
- [ ] Decisão explícita no `/design` sobre as 3 diferenças estruturais (item por Anexo, numeração
      decimal, prefixo de 2 dígitos) — nenhuma tratada por adivinhação nem por schema que não
      consiga representá-la
- [ ] `/v1/tax/simulate` aplica CBS/IBS zero a **100%** das 56 linhas de inclusão resolvidas de
      XII/XIII/XV, citando o Anexo e item corretos, em vez da alíquota geral da fase
- [ ] As 5 linhas de exceção (3 do Anexo XII, 2 do Anexo XV) **nunca** recebem zero, mesmo quando o
      NCM cai dentro do prefixo de inclusão do mesmo item
- [ ] O desempate de 3 vias do Anexo XII (itens 1.2/1.3/14, código `9018.19.80`) resolve de forma
      determinística e documentada, listando os 3 itens correspondentes na resposta
- [ ] Zero regressão: Anexo I continua funcionando exatamente como hoje; itens de mercadoria fora
      dos 4 Anexos zero continuam recebendo a alíquota geral da fase
- [ ] `motor_calculo/` não ganha dependência de infraestrutura — `aplicar_reducao_a_zero`
      reutilizado sem alteração de assinatura

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — correspondência exata (Anexo XIII) | Item de mercadoria com `ncm = "8713.10.00"` (cadeira de rodas sem propulsão, item 2.1) | `POST /v1/tax/simulate` | 200; CBS/IBS zero; fonte citada é "LCP 214/2025, Anexo XIII, item 2.1" |
| AT-002 | Regressão — Anexo I intacto | Item de mercadoria com `ncm` de um item do Anexo I (ex.: manteiga, `0405.10.00`) | `POST /v1/tax/simulate` | Comportamento idêntico ao já shipado — zero citando "Anexo I, item 5", sem qualquer interferência dos Anexos novos |
| AT-003 | Regressão — item fora dos 4 Anexos | `ncm` que não corresponde a nenhum item de I, XII, XIII ou XV | `POST /v1/tax/simulate` | 200; alíquota geral da fase, sem nenhuma referência a Anexo |
| AT-004 | Correspondência por prefixo, sem exceção (Anexo XV) | Item de mercadoria com `ncm` de 8 dígitos que começa com `0714` (raízes e tubérculos, item 5) | `POST /v1/tax/simulate` | Zero, citando "Anexo XV, item 5" |
| AT-005 | Correspondência por prefixo de **capítulo (2 dígitos)** (Anexo XV, item 4) | `ncm` de 8 dígitos que começa com `06` (ex.: flores/plantas do capítulo 6) | `POST /v1/tax/simulate` | Zero, citando "Anexo XV, item 4" — prova que o mecanismo aceita prefixo de 2 dígitos após a mudança do `/design` |
| AT-006 | Exceção operante (Anexo XII, item 5) | `ncm = "9021.39.91"` (dentro do prefixo `9021.3` do item 5, mas expressamente excluído) | `POST /v1/tax/simulate` | **Nunca** recebe zero por este item — alíquota geral aplicada, mesmo estando dentro do prefixo de inclusão |
| AT-007 | Exceção operante (Anexo XV, item 2) | `ncm` correspondente a `0710.80.00` (dentro do prefixo `0710`, mas expressamente excluído) | `POST /v1/tax/simulate` | Nunca recebe zero por este item |
| AT-008 | "Exceto" descritivo não gera exclusão indevida (Anexo XII, item 1.3/11) | `ncm = "9018.19.80"` (código do item 1.3, cuja descrição cita "exceto" outros códigos que não são o próprio) | `POST /v1/tax/simulate` | Recebe zero normalmente — o "exceto" descritivo não deve ter virado uma linha de exclusão que bloqueasse o próprio item |
| AT-009 | Desempate de 3 vias (Anexo XII, itens 1.2/1.3/14) | `ncm = "9018.19.80"` | `POST /v1/tax/simulate` | Resolve para exatamente 1 item citado (o de menor número, conforme a regra de desempate do `/design`), com `itens_correspondentes` listando os 3 (`1.2`, `1.3`, `14`) |
| AT-010 | Falso positivo de prefixo | `ncm` que compartilha os primeiros dígitos de um prefixo do Anexo XII/XV mas não pertence a ele (ex.: código de 8 dígitos dentro de `9022` fora de `9022.12`/`9022.13`/`9022.14`/`9022.19`/`9022.21`) | `POST /v1/tax/simulate` | Não recebe zero — prova que o matching por prefixo respeita os limites reais da subposição, não é "contém a substring" |

---

## Out of Scope

- Anexos IV, V, VI, VII, VIII, IX (redução de 60%, posição 13) e II, III, X, XI (redução de 60%
  por NBS, posição 14) — mecanismo de cálculo diferente (percentual sobre alíquota de referência,
  não zero), decisão de agrupamento já tomada
- Anexo XVI (piso de alíquota própria, posição 15), Anexo XVII (Imposto Seletivo, posição 16),
  Anexos XVIII-XXIII (Simples Nacional, posição 17) — features futuras próprias
- Anexo XIV — já resolvido como revogado pela LC 227/2026 (`LC_227_2026_ATUALIZACAO_LEGAL`)
- Qualquer alteração ao Anexo I além do necessário para acomodar as 3 diferenças estruturais desta
  seção (ex.: não renomear `dispositivo_legal_ref` do Anexo I, não re-popular seus dados)
- Verificação programática automatizada de overlap entre os 4 Anexos — feita manualmente nesta
  sessão (ver "Overlap entre os 4 Anexos zero"); uma suíte automatizada fica como `SHOULD`
  recomendado ao `/design`, não como requisito bloqueante desta feature
- Sincronização de eventuais alterações futuras aos Anexos XII/XIII/XV (nova lei complementar) —
  mesma decisão já registrada para o Anexo I, SPED/IBPT e TIPI
- Fuzzy match ou heurística além do que o texto de cada Anexo define literalmente

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura | `aplicar_reducao_a_zero` é reutilizado sem alteração — a novidade toda vive em `db/`/`api/` |
| Technical | O schema do Anexo I (`item SMALLINT PRIMARY KEY CHECK (item BETWEEN 1 AND 26)`) não comporta namespace por Anexo nem numeração decimal | O `/design` precisa decidir a nova forma da chave (`(anexo, item)` e tipo de `item`) antes de popular XII/XIII/XV — ver "Achados que corrigem a estimativa do brainstorm" |
| Technical | `CHECK (prefixo ~ '^[0-9]{4,8}$')` (migração 005) e `api/ncm.py::_COMPRIMENTOS_PREFIXO = (4,5,6,7,8)` rejeitam o prefixo de 2 dígitos do Anexo XV, item 4 | Os dois precisam mudar juntos para `2..8` — mudança já antecipada no comentário da migração 005, mas nunca antes exercitada |
| Technical | O desempate de overlap (Decisão 4 do Anexo I) foi desenhado para 2 itens com numeração inteira; o Anexo XII tem 3 itens com numeração decimal (`1.2`, `1.3`, `14`) | O `/design` precisa generalizar a comparação para N itens e decidir a ordenação correta (numérica por partes, não lexicográfica) |
| Business | Escopo estritamente limitado aos Anexos XII, XIII e XV — nenhum outro Anexo, nem alteração aos dados já shipados do Anexo I | Mesmo se o `/design` alterar a forma da tabela (para acomodar `anexo`/numeração decimal/prefixo de 2 dígitos), os 26 itens do Anexo I devem continuar resolvendo exatamente como resolvem hoje (AT-002) |
| Legal | Nenhum NCM/prefixo deve ser tratado como definitivo sem verificação contra fonte primária | Concluído nesta sessão para as 56 linhas de XII/XIII/XV |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Migração nova em `db/migrations/` (nome exato a definir no `/design`, ex.: `007_anexos_reducao_zero_xii_xiii_xv.sql` — a numeração 006 já foi usada pela remoção de `regras_tributarias_cache`) + extensão de `api/cesta_basica.py`/`api/ncm.py` + consumo em `api/routers/simulate.py` | Nenhum diretório novo — mesma estrutura de `REGRAS_TRIBUTARIAS_CACHE` |
| **KB Domains** | `data-modeling` (schema-migration — a mudança de chave primária e de tipo de coluna é uma decisão de modelagem real, não uma migração trivial), `data-quality` (data-contract-authoring — o contrato precisa nomear explicitamente o que é EXATO/PREFIXO/PREFIXO+EXCEÇÃO por linha, incluindo as diferenças "exceto descritivo" vs. "exceto operante"), `python` (clean-architecture), `testing` (o padrão `Protocol` real/fake já usado três vezes no projeto) | Mesmos domínios usados no Anexo I, com ênfase maior em `data-modeling` por causa da mudança de chave |
| **IaC Impact** | Nova migração Postgres a aplicar via `migrar_banco.yml` (mesmo fluxo já usado 3 vezes: TIPI, Anexo I, remoção de `regras_tributarias_cache`); `GRANT SELECT` (ou reconfirmação de um já existente, se a tabela for a mesma do Anexo I) para `taxreformai_app` | Nenhuma mudança de Terraform |

**Why This Matters:**

- **Location** → Reaproveita a estrutura já validada 3 vezes; nenhuma decisão arquitetural nova de onde as coisas vivem
- **KB Domains** → `data-modeling` precisa ser puxado com peso maior que no Anexo I, porque aqui a mudança de chave primária é real, não hipotética
- **IaC Impact** → Mesmo fluxo de migração de sempre; nenhuma surpresa de infraestrutura

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexo XII (verificado via `legis.senado.leg.br`, mirror oficial do DOU) | Texto legal (lei complementar federal) | 17 itens, 24 linhas de código/prefixo (21 inclusões + 3 exceções) | Estático — confirmado nesta sessão que não foi alterado pela LC 227/2026 | Legislativo Federal |
| LCP 214/2025, Anexo XIII (idem) | Texto legal | 6 itens, 7 linhas (todas inclusão exata) | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo XV (idem) | Texto legal | 6 itens, 25 linhas (23 inclusões + 2 exceções) | Estático — idem | Legislativo Federal |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Identificação do Anexo | Distinguir I / XII / XIII / XV — namespace de item reinicia por Anexo | Sim |
| Identificação do item, incluindo sub-itens decimais | `1`, `1.1`, `1.2`, `1.3`, `2.1`, `2.2` etc. — o tipo precisa acomodar numeração decimal, presente em XII e XIII | Sim |
| Prefixo de dígitos de comprimento **2 a 8** | Alargamento do intervalo atual (4-8); o capítulo de 2 dígitos do Anexo XV, item 4, é o único caso hoje, mas o schema deve aceitar o intervalo completo | Sim |
| Exceção (booleano `excecao`, escopada ao item) | 5 linhas novas (3 no Anexo XII, 2 no Anexo XV) além das 19 já existentes do Anexo I | Sim |
| Distinção entre "exceto" descritivo e operante | Só o "exceto" que cria uma linha de exceção real deve virar linha na tabela; o descritivo (itens 1.3 e 11 do Anexo XII) não deve gerar linha nenhuma | Sim, para evitar erro de transcrição |
| `dispositivo_legal_ref` | Formato "LCP 214/2025, Anexo {Anexo}, item {N}" — nota: o Anexo I já usa "art. 125, Anexo I, item N"; o `/design` decide se XII/XIII/XV seguem o mesmo padrão de citação (sem artigo próprio, já que a redução dos Anexos XII/XIII/XV decorre de artigos diferentes do art. 125 — a citar corretamente no `/design`, análogo à Decisão 5 do Anexo I) | Sim |
| Descrição do produto | Texto literal do item, para auditoria | Sim |

### Freshness SLAs

Não aplicável — dado estático, sem pipeline de atualização recorrente.

### Completeness Metrics

- 29/29 itens (56/56 linhas) dos Anexos XII, XIII e XV verificados contra fonte primária nesta
  sessão (100%)
- 21/56 linhas (38%) são correspondência exata simples; 30/56 (54%) exigem prefixo sem exceção;
  5/56 (9%) exigem prefixo com exceção operante — nenhuma tratada como resolvida sem decisão
  explícita do `/design`

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto dos 3 Anexos obtido via `legis.senado.leg.br` (mirror oficial do DOU) é o texto vigente, sem alterações posteriores | Os itens/códigos usados no `/design`/`/build` estariam errados | [x] Validado nesta sessão — checada a lista de republicações/vetos (nenhum toca XII/XIII/XV) e a lista de alterações da LC 227/2026 (idem) |
| A-002 | Não há overlap de NCM entre os 4 Anexos zero (I, XII, XIII, XV) | Se houvesse, a citação da fonte poderia apontar para o Anexo errado | [x] Verificado manualmente nesta sessão por análise de capítulo/posição — nenhum overlap encontrado; verificação automatizada recomendada como `SHOULD` ao `/design`, não bloqueante |
| A-003 | O mecanismo de prefixo de dígitos (Decisão 1 do `/design` do Anexo I) generaliza para prefixo de 2 dígitos (capítulo) sem precisar de um mecanismo novo — só alargar o intervalo aceito | Se a generalização não valer (ex.: um prefixo de 2 dígitos colidir amplamente com outros Anexos por ser amplo demais), o `/design` precisaria de uma exceção estrutural | [x] Verificado nesta sessão: nenhum dos outros Anexos (I, XII, XIII) usa capítulo 06, então o prefixo de 2 dígitos do Anexo XV, item 4, não colide com nada hoje conhecido |
| A-004 | A abordagem técnica continua sendo a Approach A do brainstorm (estender o schema do Anexo I), mesmo após os 3 achados estruturais desta sessão | Se o `/design` concluir que os achados tornam a Approach A inviável (não só mais trabalhosa), a Approach B (tabelas isoladas por Anexo) precisaria ser reconsiderada — nenhum dos achados aponta nessa direção, mas a decisão final é do `/design` | [ ] A confirmar no `/design` — nenhum dos 3 achados estruturais parece, nesta sessão, inviabilizar a Approach A; são mudanças de chave/tipo/intervalo, não de mecanismo |

**Note:** Validar A-004 explicitamente no `/design`, como já foi feito no `/design` do Anexo I com
a Decisão 1 (que reafirmou a escolha do brainstorm depois de uma verificação mais profunda).

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, quantificada (56 linhas, 29 itens, 3 Anexos), causa raiz idêntica à já resolvida no Anexo I |
| Users | 3 | Mesmos dois usuários concretos já validados na feature irmã, com pain points específicos a este escopo |
| Goals | 3 | MoSCoW explícito; as 3 diferenças estruturais nomeadas como MUST, não escondidas nem deferidas silenciosamente |
| Success | 3 | Critérios testáveis e numéricos (29/29 itens, 56/56 linhas, 21/56 EXATO, 5/56 exceção) |
| Scope | 3 | Out of scope extremamente explícito; overlap com os outros 13 Anexos e com o Simples Nacional descartado por decisão já tomada no roadmap |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** o brainstorm estimou esta feature como "a
mais simples das 6" por reaproveitar 100% do mecanismo do Anexo I. A verificação desta sessão
confirma que **nenhuma função de cálculo nova é necessária** (a premissa central do brainstorm se
sustenta), mas encontra 3 mudanças de schema que o brainstorm não previu (namespace por Anexo,
numeração decimal, prefixo de 2 dígitos) e um caso de desempate mais complexo que o do Anexo I (3
itens em vez de 2). Isso não muda a nota de clareza — o que precisa ser decidido está claramente
mapeado — mas é maior do que "copiar 26 INSERTs a mais", análogo ao que aconteceu com a correção de
"2 exceções" para "6 itens não-triviais" no `/define` do Anexo I.

---

## Open Questions

Nenhum item abaixo bloqueia o avanço para `/design` — são decisões de implementação, não lacunas de
entendimento:

1. **Forma final da chave primária e do tipo de `item`** (SMALLINT vs. TEXT vs. duas colunas) —
   decisão do `/design`, com as opções já mapeadas em "Achados que corrigem a estimativa do
   brainstorm".
2. **Formato exato de `dispositivo_legal_ref` para XII/XIII/XV** — o Anexo I cita "art. 125, Anexo
   I, item N" porque o art. 125 é o dispositivo que cria a redução; XII/XIII/XV são criados por
   outros artigos (não verificados nesta sessão, já que o foco era o conteúdo dos próprios Anexos).
   **Recomendação**: o `/design`, ao reler a fonte primária para escrever a migração (mesmo padrão
   do Anexo I, que rebuscou a fonte no `/design`), deve identificar o artigo que cria cada uma
   dessas 3 reduções (prováveis candidatos: arts. 126-131, a confirmar), para citar o dispositivo
   correto, não assumir "art. 125" para todos.
3. **Regra de desempate para numeração decimal e 3+ vias** (Anexo XII, itens 1.2/1.3/14) — decisão
   do `/design`, generalizando a Decisão 4 do Anexo I.
4. **Verificação automatizada de overlap** entre os 4 Anexos — recomendada como `SHOULD`, não
   bloqueante.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | define-agent | Versão inicial, extraída de `BRAINSTORM_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`; verificação de fonte primária realizada nesta sessão (Anexos XII, XIII e XV via `legis.senado.leg.br`, IDs 40180960/40180966/40181038); confirmado que a LC 227/2026 não alterou nenhum dos 3 Anexos; identificadas 3 diferenças estruturais não previstas pelo brainstorm (namespace de item por Anexo, numeração decimal, prefixo de 2 dígitos/capítulo) e 1 overlap intra-Anexo de 3 vias (Anexo XII) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`
