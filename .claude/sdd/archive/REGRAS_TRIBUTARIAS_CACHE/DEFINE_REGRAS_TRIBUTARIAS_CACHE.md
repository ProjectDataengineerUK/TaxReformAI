# DEFINE: Regras Tributárias Cache — Cesta Básica Nacional (Anexo I)

> Desenhar um schema novo (schema atual não serve como está) para os 26 itens do Anexo I
> da LCP 214/2025 (Cesta Básica Nacional, art. 125 — alíquota zero de CBS/IBS) e conectar
> `/v1/tax/simulate` a ele, citando o item exato como fonte legal por produto.
>
> **Posição na sequência:** 2 de 11 (ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).
> Esta sessão cobre só o escopo do achado original nº 2 — nenhuma decisão sobre as outras 10
> features da sequência foi tomada aqui.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REGRAS_TRIBUTARIAS_CACHE |
| **Date** | 2026-07-28 |
| **Author** | define-agent |
| **Status** | ✅ Shipped (ver `SHIPPED_2026-07-28.md`) |
| **Clarity Score** | 15/15 |

---

## Problem Statement

`regras_tributarias_cache` existe desde `SCHEMA_POSTGRESQL` sem nenhum consumidor real, e seu
schema (`ncm_code` + `ano_vigencia` + `regime_especial` livre) não corresponde à forma real de
nenhum regime diferenciado da LCP 214/2025. A Cesta Básica Nacional (art. 125, Anexo I) é o
subconjunto mais simples e citável de um achado bem maior (17 Anexos de regimes diferenciados) —
26 itens de alimentos com alíquota zero de CBS/IBS, hoje ausentes de `/v1/tax/simulate`, que
aplica a alíquota geral da fase mesmo a produtos que a própria lei já zera.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Simula CBS/IBS para alimentos da cesta básica com a alíquota geral da fase, quando a lei já garante alíquota zero para esses produtos especificamente — superestimando a carga tributária projetada |
| Controller/CFO usando o simulador | Consumidor indireto do produto (via ERP ou frontend) | Não consegue demonstrar o benefício real da Cesta Básica Nacional (mudança relevante de política pública da reforma) numa simulação que se propõe auditável |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo do Anexo I (26 itens, códigos NCM/SH) verificado contra fonte oficial primária nesta sessão de `/define` — ver seção "Verificação de Fonte Primária" — não aceito de memória nem só de fontes secundárias |
| **MUST** | Schema novo (nome e forma exatos a definir no `/design`) armazena os 26 itens do Anexo I, cada um com `dispositivo_legal_ref` citando "LCP 214/2025, art. 125, Anexo I, item N" |
| **MUST** | Decisão explícita e documentada no `/design` sobre a estratégia de correspondência por NCM para os **6 itens que não são igualdade exata simples** (itens 1, 8, 15, 19, 20, 23 — ver classificação completa abaixo): resolvidos nesta iteração (com a técnica descrita) ou marcados como "não resolvido nesta iteração", nunca aplicando zero por adivinhação nem ignorados silenciosamente |
| **MUST** | `/v1/tax/simulate` aplica alíquota zero de CBS/IBS ao item de mercadoria cujo NCM bate com um item do Anexo I **resolvido por esta feature**, citando o item exato como fonte legal na resposta |
| **MUST** | Itens de mercadoria cujo NCM não bate com nenhum item do Anexo I continuam recebendo a alíquota geral da fase — sem regressão no caminho já existente |
| **MUST** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura — mesmo princípio já usado em `IPI_TIPI_MOTOR_CALCULO`; o lookup vive em `api/`/`db/repositorio.py` |
| **SHOULD** | `regras_tributarias_cache`/`buscar_regra_cache()` originais: decisão explícita no `/design` sobre se são substituídas por schema novo, adaptadas, ou removidas como código morto |
| **SHOULD** | Teste cobrindo pelo menos 1 item de correspondência exata e 1 item de correspondência não-trivial (prefixo, com ou sem exceção) |
| **COULD** | Documentar a sobreposição entre o item 15 (massas alimentícias, prefixo `1902.1`) e o item 25 (massas de baixo teor de proteína, código `1902.19.00`, já contido no prefixo do item 15) — não é um bug da lei, mas merece nota para não gerar dupla contagem/confusão no `/design` |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

O brainstorm usou só fontes secundárias (`modeloinicial.com.br`, `simtax.com.br`) porque
`planalto.gov.br` estava inacessível deste ambiente. Nesta sessão, `planalto.gov.br` e domínios
irmãos (`legislacao.planalto.gov.br`, `pesquisa.in.gov.br`) **continuam inacessíveis** (handshake
TLS completa, servidor não responde — mesmo padrão do brainstorm, não uma regressão nova). O
acesso geral à internet funciona (`example.com`, `google.com` respondem 200); o bloqueio é
específico a esses domínios.

Como alternativa, **o portal oficial do Senado Federal (`legis.senado.leg.br`) respondeu 200** e
serve o texto integral da "Publicação Original" da LCP 214/2025 no Diário Oficial da União —
mesma fonte que o registro do LexML (`lexml.gov.br`, também acessível) aponta como publicação
oficial. Isto é uma fonte primária (texto oficial publicado em DOU, espelhado pelo Senado), não
uma fonte secundária/terciária como as usadas no brainstorm.

**O que foi verificado, com URL e conteúdo real:**

1. **Registro LexML** (`https://www.lexml.gov.br/urn/urn:lex:br:federal:lei.complementar:2025-01-16;214`,
   consultado em 2026-07-28): confirma metadados oficiais (ementa, datas de publicação, veto
   parcial) e aponta a publicação original no DOU (Seção 1, Edição Extra, 16/01/2025, p. 1) e o
   espelho do Senado Federal.
2. **Corpo do art. 125** (`https://legis.senado.leg.br/norma/40180341/publicacao/40181429`,
   "Publicação Original" completa, consultado em 2026-07-28) — texto literal:
   > "Art. 125. Ficam reduzidas a zero as alíquotas do IBS e da CBS incidentes sobre as vendas de
   > produtos destinados à alimentação humana relacionados no Anexo I desta Lei Complementar, com
   > a especificação das respectivas classificações da NCM/SH, que compõem a Cesta Básica
   > Nacional de Alimentos, criada nos termos do art. 8º da Emenda Constitucional nº 132, de 20 de
   > dezembro de 2023."

   Este documento (a "Publicação Original" corrida) contém o corpo de artigos (Art. 1º a 544) mas
   **não** os Anexos I-XXIII em si — eles são publicados como documentos/páginas próprias do DOU
   e indexados separadamente pelo Senado (ver item 3). Registrado aqui para não repetir a
   investigação: quem for verificar outro artigo da LCP 214/2025 nesta mesma fonte deve buscar o
   texto do anexo pelo link de publicação específico do anexo, não pela publicação corrida da lei.
3. **Texto integral do Anexo I** (`https://legis.senado.leg.br/norma/40180341/publicacao/40180888`,
   "Publicação Original de Anexo", DOU Edição Extra nº 11-B de 16/01/2025, p. 47, col. 1,
   consultado em 2026-07-28) — tabela oficial com cabeçalho "ANEXO I — PRODUTOS DESTINADOS À
   ALIMENTAÇÃO HUMANA SUBMETIDOS À REDUÇÃO A ZERO DAS ALÍQUOTAS DO IBS E DA CBS (EXCLUSIVE
   PRODUTOS HORTÍCOLAS, FRUTAS E OVOS, RELACIONADOS NO ANEXO XV)", **26 itens numerados** — ver
   tabela completa na próxima seção.
4. **Verificação de republicação/errata do Anexo I**: a página de detalhe da norma
   (`https://legis.senado.leg.br/norma/40180341`) lista uma única "Republicação de Anexo"
   (`.../publicacao/40306317`, DOU de 23/01/2025). O rótulo do Senado para essa linha é
   ambíguo ("Seq. 1 / 001 - Anexo I"), mas **o conteúdo do próprio documento** se identifica
   explicitamente como: *"Republicação do Anexo XXIII a Lei Complementar nº 214, de 16 de janeiro
   de 2025, por ter sido constatada inexatidão material [...]"* — ou seja, a única republicação
   registrada é do **Anexo XXIII** (Imposto Seletivo), não do Anexo I. **Conclusão: o Anexo I não
   tem nenhuma republicação/errata registrada** — o texto do item 3 acima é o texto vigente.
5. **Achado do brainstorm sobre o Anexo XIV "revogado" — RESOLVIDO nesta sessão**: a mesma página
   de detalhe da norma lista, na seção "Normas alteradas ou referenciadas", que a **Lei
   Complementar nº 227, de 13 de janeiro de 2026** promoveu dezenas de alterações à LCP 214/2025
   (arts. 330 a 544 e Anexos 7, 14, 20 e 21), incluindo explicitamente **"Anexo 14 —
   Revogação"**. Confirmado por fonte primária: **o Anexo XIV foi de fato revogado**, pela LC
   227/2026. **O Anexo I não aparece nessa lista de alterações** — só o art. 126 (§6º acrescido)
   é tocado, e não o art. 125 nem o Anexo I. Esta pendência do brainstorm está fechada: Anexo XIV
   revogado (confirmado), Anexo I intacto.

**Achado fora de escopo desta feature, mas relevante ao projeto** — ver "Open Questions".

---

## Anexo I — Os 26 Itens (fonte primária, verificados nesta sessão)

Tabela completa, com classificação do tipo de correspondência por NCM/SH necessária para cada
item — informação central para o `/design`, que precisa decidir a estratégia de matching.

| Item | Descrição (resumida) | Códigos/posições NCM/SH citados | Tipo de correspondência |
|------|------------------------|----------------------------------|--------------------------|
| 1 | Arroz | subposições 1006.20, 1006.30 + código 1006.40.00 | **MISTO** (prefixo + exato) |
| 2 | Leite | 0401.10.10, 0401.10.90, 0401.20.10, 0401.20.90, 0401.40.10, 0401.50.10 | EXATO |
| 3 | Leite em pó | 0402.10.10, 0402.10.90, 0402.21.10, 0402.21.20, 0402.29.10, 0402.29.20 | EXATO |
| 4 | Fórmulas infantis | 1901.10.10, 1901.10.90, 2106.90.90 | EXATO |
| 5 | Manteiga | 0405.10.00 | EXATO |
| 6 | Margarina | 1517.10.00 | EXATO |
| 7 | Feijões | 0713.33.19, 0713.33.29, 0713.33.99, 0713.35.90 | EXATO |
| 8 | Café | posição 09.01 + subposição 2101.1 | **PREFIXO** (nenhum código de 8 dígitos) |
| 9 | Óleo de babaçu | 1513.21.20 | EXATO |
| 10 | Farinha de mandioca / tapioca | 1106.20.00, 1903.00.00 | EXATO |
| 11 | Farinha/grumos/sêmolas de milho | 1102.20.00, 1103.13.00 | EXATO |
| 12 | Grãos de milho | 1104.19.00, 1104.23.00 | EXATO |
| 13 | Farinha de trigo | 1101.00.10 | EXATO |
| 14 | Açúcar | 1701.14.00, 1701.99.00 | EXATO |
| 15 | Massas alimentícias | subposição 1902.1 | **PREFIXO** (nenhum código de 8 dígitos) |
| 16 | Pão francês (e pré-mistura) | 1905.90.90, 1901.20.10, 1901.20.90 | EXATO |
| 17 | Grãos de aveia | 1104.12.00, 1104.22.00 | EXATO |
| 18 | Farinha de aveia | 1102.90.00 | EXATO |
| 19 | Carnes (bovina, suína, ovina, caprina, aves) | a)-d): mistura de posições/subposições/códigos, **com exceção explícita** ("exceto os produtos dos códigos 0207.43.00 e 0207.53.00") | **PREFIXO + EXCEÇÃO** |
| 20 | Peixes e carnes de peixes | a)-c): posições **com exceção explícita** (salmonídeos, atuns, bacalhau, hadoque, saithe e outros excluídos por subposição) | **PREFIXO + EXCEÇÃO** |
| 21 | Queijos (mozarela, minas, prato, coalho, ricota, requeijão, provolone, parmesão, fresco, do reino) | 0406.10.10, 0406.10.90, 0406.20.00, 0406.90.10, 0406.90.20, 0406.90.30 | EXATO |
| 22 | Sal | 2501.00.20, 2501.00.90 | EXATO |
| 23 | Mate | posição 09.03 | **PREFIXO** (nenhum código de 8 dígitos) |
| 24 | Farinha de baixo teor de proteína (aminoacidopatias) | 1901.90.90 | EXATO |
| 25 | Massas de baixo teor de proteína (aminoacidopatias) | 1902.19.00 | EXATO (nota: já contido no prefixo do item 15) |
| 26 | Fórmulas Dietoterápicas (Erros Inatos do Metabolismo) | 2106.9090 (grafia sem pontos no texto oficial) | EXATO |

**Contagem por tipo:** 20 itens EXATO · 1 item MISTO (1) · 3 itens PREFIXO puro (8, 15, 23) · 2
itens PREFIXO+EXCEÇÃO (19, 20). **Total: 6 de 26 itens (23%) exigem algo além de igualdade exata
de um código de 8 dígitos** — corrige a estimativa do brainstorm, que havia identificado só os
itens 19/20 como não-triviais. Ver "Open Questions" sobre o impacto disso no tamanho da feature.

---

## Success Criteria

- [x] Conteúdo do Anexo I (26 itens, NCMs) verificado contra fonte oficial primária (Senado
      Federal/DOU), com URLs e data de acesso registrados neste documento — concluído nesta sessão
- [x] Schema novo (nome e forma a definir no `/design`) representa os 26 itens do Anexo I com
      `dispositivo_legal_ref` citando "LCP 214/2025, art. 125, Anexo I, item N" — `cesta_basica_anexo_i`
      + `cesta_basica_anexo_i_ncm` (migração 005); contagens verificadas em teste: 26/76/19
- [x] `/v1/tax/simulate` aplica alíquota zero de CBS/IBS a **100%** dos itens de mercadoria cujo
      NCM esteja entre os itens do Anexo I resolvidos por esta feature, em vez da alíquota geral
      da fase — as **76 inclusões** do Anexo resolvem `APLICADA` em teste exaustivo
      (`test_todas_as_76_inclusoes_do_anexo_resolvem_aplicada`); ⏳ contra o Cloud SQL real,
      pendente da Decisão 13
- [x] Decisão explícita e documentada sobre os 6 itens de correspondência não-trivial (1, 8, 15,
      19, 20, 23): resolvidos nesta feature (com a técnica usada) ou marcados como "não resolvido"
      sem promessa de zero silencioso — **os 6 são resolvidos**, ver Decisão 1 do DESIGN
      (correspondência é sempre prefixo de dígitos; "exato" é o prefixo de 8)
- [x] Achado do Anexo XIV possivelmente revogado — **resolvido**: confirmado como revogado pela
      LC 227/2026 contra fonte primária (Senado Federal); Anexo I não afetado
- [x] `motor_calculo/` não ganha dependência de infraestrutura — mesmo padrão da feature 1
      (lookup em `api/`/`db/repositorio.py`); `motor_calculo/reducoes.py` importa só `dataclasses`,
      `decimal` e `ResultadoCalculo`, e `engine.py` não foi tocado
- [x] `regras_tributarias_cache`/`buscar_regra_cache()` original: decisão explícita no `/design`
      sobre se são substituídas por schema novo, adaptadas, ou removidas — **removidas**
      (Decisão 12 do DESIGN, migração 006 com guarda de tabela vazia)
- [x] Zero regressão: itens de mercadoria com NCM fora do Anexo I continuam recebendo a alíquota
      geral da fase, idêntico ao comportamento hoje — AT-002 e AT-005; e as 126 asserções das
      suítes anteriores (incluindo toda a feature 1 do IPI) passam **sem uma linha de edição**

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — correspondência exata | Item de mercadoria com `natureza=MERCADORIA` e `ncm` igual a um código EXATO do Anexo I (ex.: manteiga, `0405.10.00`, item 5) | `POST /v1/tax/simulate` | 200; CBS e IBS daquele item são zero; fonte legal citada é "LCP 214/2025, art. 125, Anexo I, item 5" |
| AT-002 | Regressão — item fora do Anexo I | Item de mercadoria com `ncm` que não corresponde a nenhum item do Anexo I | `POST /v1/tax/simulate` | 200; CBS/IBS daquele item seguem a alíquota geral da fase, sem nenhuma referência ao Anexo I |
| AT-003 | Item de correspondência não-trivial (prefixo puro, ex.: item 8 café ou item 23 mate) | Item de mercadoria com `ncm` de 8 dígitos que começa com um prefixo do Anexo I (posição/subposição) | `POST /v1/tax/simulate` | Comportamento explícito conforme decisão do `/design`: zero com citação do item correto (se resolvido nesta feature) OU declarado "não resolvido" de forma explícita (nunca tratado como fora da cesta básica por omissão nem como zero por adivinhação) |
| AT-004 | Item de correspondência com exceção (item 19 ou 20 — carnes/peixes) | `ncm` dentro da faixa do item, mas coincidente com um dos códigos explicitamente **excluídos** pelo próprio Anexo I | `POST /v1/tax/simulate` | O item excluído **nunca** recebe alíquota zero por este mecanismo — mesmo que o design resolva a correspondência positiva do item 19/20, a exclusão deve ser respeitada |
| AT-005 | Falso positivo — vizinhança de prefixo | `ncm` de 8 dígitos que **não** pertence a nenhum prefixo do Anexo I mas compartilha os primeiros dígitos com um prefixo existente (ex.: outro código dentro de `1006` fora de `1006.20`/`1006.30`/`1006.40.00`) | `POST /v1/tax/simulate` | Não recebe alíquota zero — o teste prova que o matching por prefixo não é "contém a substring", mas respeita os limites reais da subposição/posição |

---

## Out of Scope

- Anexos II a XVII (educação, saúde, dispositivos médicos, acessibilidade, nutrição
  enteral/parenteral, alimentos com redução de 60%, higiene, insumos agropecuários, produções
  culturais, segurança nacional/cibersegurança, dispositivos médicos e medicamentos com redução a
  zero, hortícolas/frutas/ovos, piso de alíquota própria, Imposto Seletivo) — candidatos a
  features futuras próprias, fora da sequência de 11 já roteirizada
- Anexos XVIII a XXIII (dimensão "produção de efeitos futura")
- `API_EMPRESA_SKUS` (achado 3, próxima posição da sequência), `LLM_REAL_VERTEX_AI` (achado 5),
  `ORQUESTRACAO_NOS_REAIS` (achado 4), `REMOVER_FAKE_HISTORICO` (achado 6),
  `CLOUD_COMPOSER_PROVISIONAMENTO` (achado 7), `VERIFICACAO_FRONTEND_NAVEGADOR` (achado 8),
  `DIAGNOSTICO_BUSCA_HIBRIDA` (achado 9), `BIGQUERY_DATA_WAREHOUSE` (achado 10),
  `FILA_ASSINCRONA_CELERY_REDIS` (achado 11) — demais features da sequência
- Linha do tempo 2029-2033 (achado 12) — item de monitoramento, não uma feature executável
- **LC 227/2026 e seu impacto no restante da LCP 214/2025** (arts. 330-544, Anexos 7/14/20/21) —
  achado novo desta sessão, fora do escopo desta feature (que é só sobre o Anexo I, não afetado
  por essa lei); ver "Open Questions" para o encaminhamento recomendado
- Alterar o schema/migração da TIPI (`004_tipi.sql`) ou de `regras_tributarias_cache`
  (`001_schema_inicial.sql`) além do necessário para o Anexo I — sem tocar em tabelas de outras
  features já shipadas
- Fuzzy match ou heurística de aproximação além do que o próprio texto do Anexo I define
  (posição/subposição/código e exceções explícitas) — nenhuma inferência além do que a lei
  escreve literalmente
- Sincronização de eventuais alterações futuras ao Anexo I (ex.: se um novo item for incluído por
  lei posterior) — problema de atualização periódica, mesma decisão já registrada para SPED/IBPT
  e TIPI no CLAUDE.md

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura | O lookup do Anexo I vive em `api/`/`db/repositorio.py`, nunca em `motor_calculo/engine.py` |
| Technical | Sem RLS na nova tabela — dado legal público, igual para todos os tenants (mesmo padrão de `aliquotas_ipi_tipi`/`regras_tributarias_cache`) | Não introduzir tenant scoping onde a lei se aplica igualmente a todos |
| Technical | Hoje `AliquotasAplicadas` (`cbs_percentual`/`ibs_percentual`) é resolvida por **fase**, uniforme para todos os itens de um payload — não existe hoje nenhum conceito de "alíquota diferente por item" no cálculo de CBS/IBS da reforma | O `/design` precisa introduzir uma forma de **override por item**, aplicada depois de `engine.calcular()`, sem tocar `motor_calculo/engine.py` |
| Technical | Igualdade exata cobre só 20 dos 26 itens; 6 itens exigem prefixo (posição/subposição) com ou sem exceção | Estratégia de matching não pode ser um único `WHERE ncm_code = ANY(%s)` para o Anexo I inteiro, ao contrário da TIPI |
| Business | Escopo estritamente limitado ao Anexo I — nenhum dos outros 16 Anexos, nem o Imposto Seletivo (Anexo XVII), entram nesta feature | Mesmo se o `/design` decidir generalizar o schema, os dados carregados nesta feature são só os 26 itens do Anexo I |
| Legal | Nenhuma alíquota/NCM deve ser tratada como definitiva sem verificação contra fonte primária ou a coleção Qdrant já ingerida | Concluído nesta sessão para os 26 itens do Anexo I; qualquer expansão futura (outros Anexos) repete a mesma disciplina |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Nova migração em `db/migrations/` (ex.: `005_cesta_basica_anexo_i.sql`, nome exato a definir no `/design`) + nova função de lookup em `db/repositorio.py` + consumo em `api/routers/simulate.py` (aplicando override por item pós-`engine.calcular()`) | Nenhum diretório novo — reaproveita a estrutura de `SCHEMA_POSTGRESQL`/`IPI_TIPI_MOTOR_CALCULO` já shipadas |
| **KB Domains** | `python` (clean-architecture, error-handling), `pydantic` (novos campos de resposta em `schemas_simulate.py`, ex. indicar que um item está na cesta básica), `testing` (padrão `Protocol` real/fake já usado em `TabelaPisCofins`/`RawStorage`/`consultar_ipi_com_seguranca`), `data-modeling` (schema-migration — desenho de tabela nova para dado heterogêneo: exato + prefixo + exceção), `data-quality` (data-contract-authoring — o "contrato" de correspondência por item precisa ser explícito, não implícito) | Domínios do `${CLAUDE_PLUGIN_ROOT}/kb/`; os agentes de projeto equivalentes (`python-developer`, `database-reviewer`) já usados nas 9 features anteriores continuam aplicáveis |
| **IaC Impact** | Nova migração Postgres a aplicar via `migrar_banco.yml` (mesmo fluxo de `004_tipi.sql`); `GRANT SELECT` para `taxreformai_app` na nova tabela | Nenhuma mudança de Terraform — reaproveita o Cloud SQL já existente (`taxreformai-pg`) |

**Why This Matters:**

- **Location** → Evita reabrir a discussão arquitetural do brainstorm (motor_calculo/ vs. api/) durante o Design
- **KB Domains** → Design deve puxar o padrão `Protocol` real/fake já estabelecido, e tratar o desenho do schema (exato + prefixo + exceção) como uma decisão de modelagem de dados explícita, não uma tabela genérica
- **IaC Impact** → Nenhuma surpresa de infraestrutura — mesmo fluxo de migração já usado 4 vezes no projeto

---

## Data Contract

> Dado novo, pequeno (26 linhas) e estático — mas com heterogeneidade de forma (exato/prefixo/
> exceção) que o schema precisa representar explicitamente. Diferente da TIPI (9231 linhas, forma
> única), aqui o volume é trivial mas a modelagem não é.

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, art. 125 + Anexo I (verificado via `legis.senado.leg.br`, mirror oficial do DOU) | Texto legal (lei complementar federal) | 26 itens, lista fechada | Estático — só muda por nova lei complementar; verificado nesta sessão que **não** foi alterado pela LC 227/2026 (que alterou outros trechos da LCP 214/2025) | Legislativo Federal (Congresso Nacional / Presidência da República) |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Identificação do item | Número do item do Anexo I (1-26), citável isoladamente | Sim |
| Tipo de correspondência | Distinguir EXATO / PREFIXO / PREFIXO_COM_EXCECAO — os 3 tipos têm semântica de matching diferente | Sim |
| Código(s)/prefixo(s) NCM/SH | Um item pode ter múltiplos códigos ou prefixos (ex.: item 2 tem 6 códigos exatos; item 19 tem 4 grupos com exceções) | Sim — schema deve suportar cardinalidade 1:N entre item e código/prefixo |
| Exceções | Para itens 19/20, os códigos/subposições explicitamente excluídos precisam ser representáveis e consultáveis | Sim, para os itens 19/20 especificamente |
| `dispositivo_legal_ref` | Citação exata: "LCP 214/2025, art. 125, Anexo I, item N" | Sim |
| Descrição do produto | Texto literal do item (para auditoria/depuração, não para matching) | Sim |

### Freshness SLAs

Não aplicável — dado estático, sem pipeline de atualização recorrente nesta feature. Uma alteração
futura ao Anexo I (nova lei complementar) exigiria nova migração, fora deste escopo.

### Completeness Metrics

- 26/26 itens do Anexo I verificados contra fonte primária nesta sessão (100%)
- 20/26 itens (77%) são correspondência exata simples; 6/26 (23%) exigem prefixo, com 2/26 (8%)
  exigindo também exceção — nenhum desses 6 deve ser tratado como "resolvido" sem decisão
  explícita do `/design`

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto do Anexo I obtido via `legis.senado.leg.br` (mirror oficial do DOU, Publicação Original de 16/01/2025) é o texto vigente, sem alterações posteriores | Os 26 itens/códigos usados no `/design`/`/build` estariam errados, exigindo correção pós-build | [x] Validado nesta sessão — checada a existência de republicação/errata (só há uma, do Anexo XXIII, não do Anexo I) e a lista de alterações da LC 227/2026 (que não toca o art. 125 nem o Anexo I) |
| A-002 | O achado do brainstorm sobre o Anexo XIV "possivelmente revogado" está resolvido: o Anexo XIV foi de fato revogado, pela LC 227/2026 | N/A — já não é mais uma suposição, é fato confirmado por fonte primária | [x] Validado nesta sessão |
| A-003 | A estratégia de correspondência por NCM para os 6 itens não-triviais (1, 8, 15, 19, 20, 23) é uma decisão explícita do `/design`, não desta sessão — pode ser "resolver todos", "resolver um subconjunto documentado" ou "marcar todos como não resolvidos nesta iteração" | Se subestimado, o esforço de `/build` desta feature pode superar o padrão das demais 10 features já roteirizadas na sequência (a maioria delas é "conectar dado já existente a um consumidor", não "desenhar matching heterogêneo") — **risco sinalizado explicitamente**, não decidido aqui | [x] Decidido no `/design`: **resolver todos os 6**. A Decisão 1 mostra que prefixo e igualdade exata são o mesmo mecanismo (prefixo de dígitos de comprimento 4 a 8), então cobrir 20 ou 26 itens é o mesmo código — o esforço extra da feature vem do schema novo e do override por item, não dos 6 |
| A-004 | A LC 227/2026 (13/01/2026) altera extensivamente a LCP 214/2025 (dezenas de artigos entre 330-544, Anexos 7/14/20/21) e não está refletida na coleção Qdrant de produção nem no `CLAUDE.md` atual do projeto | Achado de projeto relevante além desta feature — o corpus legal ingerido (580 artigos da LCP 214/2025) pode estar desatualizado frente à LC 227/2026 para partes não relacionadas ao Anexo I; fora do escopo desta sessão resolver, mas merece atenção | [x] Descoberto e documentado nesta sessão; impacto completo não avaliado (fora de escopo) |
| A-005 | A abordagem técnica é a Approach A do brainstorm (schema novo dedicado ao Anexo I, sem reaproveitar `regras_tributarias_cache` como está) — já confirmada explicitamente pelo usuário no brainstorm | N/A — nada nesta sessão de `/define` contradiz essa escolha | [x] Confirmado no brainstorm |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, causa raiz identificada no código real (`AliquotasAplicadas` uniforme por fase, sem override por item) |
| Users | 3 | Dois usuários concretos com pain points específicos, mesmos já usados nas features anteriores |
| Goals | 3 | MoSCoW explícito; decisões deliberadamente deferidas ao `/design` são nomeadas, não implícitas |
| Success | 3 | Critérios testáveis e numéricos (26/26 itens verificados, 20/26 exatos, 6/26 não-triviais) |
| Scope | 3 | Out of scope extremamente explícito, incluindo o achado novo da LC 227/2026 explicitamente excluído desta feature |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** a investigação desta sessão corrigiu a
estimativa do brainstorm de "2 itens de exceção" para "6 de 26 itens (23%) com correspondência
não-trivial". A clareza sobre *o que* precisa ser decidido é alta (por isso a nota permanece
15/15) — o risco é sobre *tamanho*, não sobre entendimento. Ver "Open Questions" item 1.

---

## Open Questions

1. **Risco de tamanho de escopo (não bloqueante, mas registrado para avaliação do usuário)**: o
   brainstorm estimou 2 de 26 itens do Anexo I como "exceção por prefixo" (itens 19/20). A
   verificação contra fonte primária desta sessão encontrou **6 de 26 itens (23%)** exigindo
   correspondência por prefixo (itens 1, 8, 15, 19, 20, 23), com 2 desses também exigindo exclusão
   explícita. Isso é maior do que "plugar dado existente" (TIPI, feature 1) e maior do que a
   estimativa original do brainstorm para esta feature. O `/design` pode resolver isso mantendo o
   MUST de "decisão explícita, nunca zero por adivinhação" — mas o esforço de implementar
   correspondência por prefixo+exceção corretamente (com testes de falso positivo, AT-005) é
   qualitativamente diferente das demais features "de posição simples" da sequência de 11. Não
   decidido aqui reduzir escopo — só sinalizado, como pedido explicitamente para esta sessão.

2. **Achado fora de escopo desta feature, mas relevante ao projeto**: a **Lei Complementar nº
   227, de 13 de janeiro de 2026** altera extensivamente a LCP 214/2025 (dezenas de artigos entre
   330 e 544, revoga o Anexo XIV, altera os Anexos 7/20/21, e acrescenta dispositivos aos arts.
   344 e 348 — este último diretamente citado em `motor_calculo/regras_fiscais.py`/
   `AliquotaNaoDisponivelError`/`Compensacao`). Nem o `CLAUDE.md` atual nem (até onde é possível
   confirmar deste ambiente) a coleção Qdrant de produção parecem refletir essa lei. **Isto não
   afeta o Anexo I** (confirmado nesta sessão) e por isso não é resolvido aqui, mas é um achado
   maior que o achado 2 original e não mapeado em nenhuma das 11 features já roteirizadas.
   Recomenda-se ao usuário abrir uma sessão de brainstorm dedicada para avaliar o impacto da LC
   227/2026 assim que esta feature (ou a sequência de 11) permitir — possivelmente um "achado 14".

3. Nome final da tabela nova e destino de `regras_tributarias_cache`/`buscar_regra_cache()` —
   decisão do `/design`, já registrada como não-bloqueante desde o brainstorm.

Nenhum item acima bloqueia o avanço para `/design` — este documento está pronto.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | define-agent | Versão inicial, extraída de `BRAINSTORM_REGRAS_TRIBUTARIAS_CACHE.md`; verificação de fonte primária realizada nesta sessão (art. 125 e Anexo I via `legis.senado.leg.br`); achado do Anexo XIV resolvido (revogado pela LC 227/2026, confirmado); achado novo da LC 227/2026 registrado como fora de escopo mas relevante ao projeto; complexidade de correspondência por NCM corrigida de "2 exceções" para "6 de 26 itens" |
| 1.1 | 2026-07-28 | design-agent | Status → Designed. Os 6 itens não-triviais são **resolvidos** (Decisão 1: toda correspondência é prefixo de dígitos); `regras_tributarias_cache`/`buscar_regra_cache()` **removidos** (Decisão 12). O `/design` rebuscou a mesma fonte primária e transcreveu o Anexo I literalmente, com três achados que o DEFINE não tinha: a redução vale na fase de teste de 2026 (art. 348, III, "a"), os itens 19/20 têm 19 códigos de exceção e um prefixo de 7 dígitos (`0210.99.1`), e há uma **segunda** sobreposição entre itens — 4 e 26 citam o mesmo `2106.90.90`, além da 15/25 já registrada |

---

## Next Step

**Design concluído** — ver [DESIGN_REGRAS_TRIBUTARIAS_CACHE.md](./DESIGN_REGRAS_TRIBUTARIAS_CACHE.md).

**Ready for:** `/build .claude/sdd/features/DESIGN_REGRAS_TRIBUTARIAS_CACHE.md`
