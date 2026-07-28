# DEFINE: LC 227/2026 — Atualização Legal da LCP 214/2025

> Catalogar com precisão o que a Lei Complementar nº 227/2026 muda na LCP 214/2025 (a lei em que
> todo `motor_calculo/` e a ingestão em `ingestion/`/Qdrant se baseiam), cruzar cada mudança contra
> o código real deste projeto, e avaliar a exposição real da coleção Qdrant já ingerida — **sem**
> decidir sozinho a estratégia de remediação (que este documento deixa em aberto, para decisão do
> usuário).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LC_227_2026_ATUALIZACAO_LEGAL |
| **Date** | 2026-07-28 |
| **Author** | define-agent |
| **Status** | **Resolvido sem feature — ver "Diagnóstico executado" abaixo** |
| **Clarity Score** | 9/15 (histórico — a pergunta que impedia o score mais alto foi respondida pela verificação real, não por mais análise) |

## Diagnóstico executado (2026-07-28)

A verificação recomendada na seção "Recomendação" foi rodada contra o Qdrant real via
`scripts/verificar_lc227_ingerida.py` (novo, `ingestao.yml` com `verificar_lc227=sim`,
`fonte=nenhuma` — só leitura, nenhuma reingestão). Run
[`30368697093`](https://github.com/ProjectDataengineerUK/TaxReformAI/actions/runs/30368697093):

```
Documento 'LCP_214_2025': 3375 chunks indexados
ACHOU artigo novo: dispositivo='Art. 341-A'
ACHOU inciso IV: dispositivo='Art. 344, Parágrafo único, Inciso IV'
VEREDITO: corpus JÁ REFLETE a LC 227/2026. Nenhuma reingestão necessária.
```

**Os dois marcadores confirmados contra fonte primária nesta investigação (art. 341-A, artigo
inteiramente novo; e o texto literal do Inciso IV do art. 344, acréscimo da LC 227/2026) já estão
indexados.** A hipótese levantada na seção anterior — de que a ingestão de 2026-07-25 já capturava
o texto pós-LC-227, com base na URL de texto compilado do Planalto e na contagem de 580 artigos —
está confirmada. Nenhuma reingestão é necessária por causa desta lei.

**Não vira uma feature no roadmap**: não há regressão para corrigir, nenhum dispositivo já
codificado em `motor_calculo/` ficou desatualizado (achado já registrado nesta sessão), e a
ingestão já reflete a lei vigente. Este documento fica arquivado como registro da investigação,
não avança para `/design`.

---

## Problem Statement

A **Lei Complementar nº 227, de 13 de janeiro de 2026** (sancionada pelo Presidente da República,
publicada no DOU de 14/01/2026) é a segunda lei complementar da reforma tributária — institui o
Comitê Gestor do IBS como entidade, o processo administrativo tributário do IBS, a distribuição da
arrecadação do IBS aos entes federativos, normas gerais do ITCMD, **e altera 244 dispositivos
efetivos da LCP 214/2025** (a lei que `motor_calculo/` e a ingestão em `ingestion/`/Qdrant tomam
como fonte única). Nem o `CLAUDE.md` do projeto nem a coleção Qdrant de produção citam essa lei em
nenhum lugar — mas a real necessidade de qualquer ação de remediação é menor do que o achado
original do brainstorm sugeria, e a direção de remediação (se houver alguma) não está decidida.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Depende de `fonte_legal`/`fonte_legal_compensacao` citarem o dispositivo vigente — se uma alteração legal relevante não for refletida, a citação "auditável" perde credibilidade |
| Controller/CFO usando o simulador | Consumidor indireto do produto | Toma decisão com base numa "alíquota fixada em lei" que precisa continuar sendo a alíquota realmente vigente, não uma versão desatualizada |
| Time do projeto (Jonatas) | Mantenedor | Precisa saber se há ação corretiva real a fazer, ou se o achado do brainstorm anterior superestimou o risco |

---

## Metodologia e Fontes Primárias Usadas Nesta Sessão

`planalto.gov.br` continua inacessível deste ambiente (handshake TLS completa, sem resposta — testado
novamente nesta sessão, mesmo padrão já registrado em sessões anteriores). **`legis.senado.leg.br`**
(mirror oficial do DOU mantido pelo Senado Federal) respondeu 200 e foi a fonte usada para tudo
abaixo. URLs e conteúdo exatos, para que qualquer verificação futura não precise repetir a busca:

| O quê | URL | O que confirma |
|-------|-----|-----------------|
| Detalhe da norma LCP 214/2025 | `https://legis.senado.leg.br/norma/40180341` | Seção "Dispositivos da presente norma que foram referenciados ou alterados" — lista estruturada, dispositivo por dispositivo, de toda alteração sofrida pela LCP 214/2025, com a lei alteradora e o tipo de ação (Acréscimo/Alteração/Revogação/Renumeração/Supressão/Ressalva/Vetado) |
| Detalhe da norma LC 227/2026 | `https://legis.senado.leg.br/norma/42042119` | Ementa completa, datas, existência de retificação e republicação parcial |
| Publicação Original da LC 227/2026 | `https://legis.senado.leg.br/norma/42042119/publicacao/42256084` | Texto integral (DOU de 14/01/2026, p.1) — usado para ler o texto exato dos dispositivos que interessam a este projeto |
| Retificação da LC 227/2026 | `https://legis.senado.leg.br/norma/42042119/publicacao/42694069` | DOU de 23/01/2026 — corrige só o art. 172 (Lei 1.079/1950, CGIBS), sem relação com LCP 214/2025 |
| Republicação parcial da LC 227/2026 | `https://legis.senado.leg.br/norma/42042119/publicacao/42528971` | DOU de 15/01/2026 — corrige só o art. 293, § 4º, I (VETADO), sem relação com os dispositivos usados neste projeto |
| Publicação Original da LCP 214/2025 (íntegra, corpo de artigos) | `https://legis.senado.leg.br/norma/40180341/publicacao/40181429` | Texto original (pré-LC 227) dos arts. 343-348, usado para comparar "antes x depois" |
| Lei 10.833/2003 (íntegra) | `https://legis.senado.leg.br/norma/552709/publicacao/15757515` | Texto do art. 69, revogado pela LC 227/2026 |

Consultado em 2026-07-28. Também verificado via `gh run view`/`gh api` (histórico real do
GitHub Actions deste repositório): os logs da execução real de ingestão em produção (workflow
`ingestao.yml`, run `30158978370`, 2026-07-25 13:01-13:22 UTC) — dados objetivos, não inferência.

---

## O Que a LC 227/2026 Realmente Altera na LCP 214/2025

### Correção de escala em relação ao achado do brainstorm anterior

O achado que motivou esta sessão (registrado em
`.claude/sdd/features/DEFINE_REGRAS_TRIBUTARIAS_CACHE.md`, Open Questions #2) estimava "dezenas de
artigos entre 330 e 544". A contagem real, extraída da própria base estruturada do Senado, é maior
e começa muito antes:

- **255 dispositivos** (artigos/parágrafos/incisos/alíneas/anexos) da LCP 214/2025 aparecem na
  lista oficial "alterados ou referenciados" pela LC 227/2026 — **do art. 3º ao art. 544 e aos
  Anexos VII, XIV, XX e XXI** (não só 330-544).
- Dessas 255, **11 foram VETADAS** pelo Presidente da República na sanção (Mensagem de Veto Parcial
  nº 36, de 13/01/2026) e **não estão em vigor** — sem registro de derrubada de veto pelo Congresso
  até a data desta consulta. Restam **244 alterações efetivamente em vigor**.
- Distribuição por tipo de ação: 119 Acréscimo, 80 Alteração, 37 Revogação, 5 Supressão,
  2 Renumeração, 1 Ressalva (mais os 11 vetados, já excluídos da contagem de 244).

**Catálogo completo (244 efetivos + 11 vetados, 255 no total)** — tabela integral por dispositivo,
extraída da seção "Dispositivos da presente norma que foram referenciados ou alterados" de
`https://legis.senado.leg.br/norma/40180341`:

<details>
<summary>Ver os 255 dispositivos (clique para expandir)</summary>

| Dispositivo (LCP 214/2025) | Ação (LC 227/2026) |
|---|---|
| Art. 3º, § 3º | Acréscimo |
| Art. 4º, § 4º | Alteração |
| Art. 4º, § 6º | Acréscimo |
| Art. 5º | Alteração |
| Art. 6º, caput, Inciso 12 | Acréscimo |
| Art. 7º-A | Acréscimo (artigo novo) |
| Art. 10 | Alteração |
| Art. 11 | Alteração |
| Art. 11, § 8º | Revogação |
| Art. 12, § 3º | **Vetada** |
| Art. 12, § 4º, Inciso 3 | **Vetada** |
| Art. 12, § 9º | Acréscimo |
| Art. 16, Parágrafo Único | Alteração |
| Art. 22 | Alteração |
| Art. 22, § 8º | Revogação |
| Art. 22, § 9º | Revogação |
| Art. 26 | Alteração |
| Art. 26, § 7º | Revogação |
| Art. 28 | Alteração |
| Art. 29, § 1º | Alteração |
| Art. 29, § 5º | Acréscimo |
| Art. 31 | Alteração |
| Art. 32 | Alteração |
| Art. 33 | Alteração |
| Art. 33, § 5º | Revogação |
| Art. 34, caput, Inciso 5, "a" | Alteração |
| Art. 47, § 8º | Alteração |
| Art. 47, § 12 | Acréscimo |
| Art. 47, § 13 | Acréscimo |
| Art. 57 | Alteração |
| Art. 57, § 4º | Revogação |
| Art. 57, § 6º | Revogação |
| Art. 57, § 7º | Revogação |
| Art. 58, § 4º | Acréscimo |
| Art. 58, § 5º | Acréscimo |
| Art. 59, § 5º | Alteração |
| Art. 60, § 7º | Acréscimo |
| Art. 64 | Alteração |
| Art. 64, § 5º, Inciso 1, "b" | Revogação |
| Art. 64, § 7º | Revogação |
| Art. 71, caput | Alteração |
| Art. 73, Parágrafo Único | Acréscimo |
| Art. 76, § 3º | Alteração |
| Art. 80 | Alteração |
| Art. 80, § 2º | Revogação |
| Art. 80, § 3º | Revogação |
| Art. 80, § 6º | Revogação |
| Art. 81-A, caput/§ 1º/§ 2º | Acréscimo (artigo novo) |
| Art. 89, § 4º (caput e Inciso 1) | Alteração |
| Art. 98-A | Acréscimo (artigo novo) |
| Art. 98-B | Acréscimo (artigo novo) |
| Art. 106, § 7º | Acréscimo |
| Art. 116, § 5º | **Vetada** |
| Art. 117, § 2º, Inciso 1 | Alteração |
| **Art. 126, § 6º** | Acréscimo |
| Art. 142, caput, Inciso 2 | Alteração |
| Art. 146 | Alteração |
| Art. 149, § 2º, Inciso 2 | Alteração |
| Art. 149, § 3º | Revogação |
| Art. 152, caput, Inciso 2 | Alteração |
| Art. 156, caput | Alteração |
| Art. 168, § 6º | Alteração |
| Art. 172 | Alteração |
| Art. 182, caput, Inciso 9 | Alteração |
| Art. 182, caput, Inciso 17 | Acréscimo |
| Art. 183, § 2º, Inciso 1 | Alteração |
| Art. 192, caput, Inciso 5 | Alteração |
| Art. 197, caput (+ Incisos 1 e 2 novos) | Alteração/Acréscimo |
| Art. 201, caput, Inciso 2, "c" | Revogação |
| Art. 212 | Alteração |
| Art. 214, § 3º | Alteração |
| Art. 214, § 6º | Acréscimo |
| Art. 217 (caput, incisos 1-2, parágrafo único) | **Revogação total do artigo** |
| Art. 218-A | Acréscimo (artigo novo) |
| Art. 219-A (caput, incisos 1-2, parágrafo único) | Acréscimo (artigo novo) |
| Art. 231, § 1º, Inciso 4 / § 3º | Acréscimo |
| Art. 233 (caput) | Alteração |
| Art. 233, §§ 1º, 2º, 4º, 5º, 7º, 8º | Revogação |
| Art. 238, Parágrafo Único (caput) | Alteração |
| Art. 252 | Alteração |
| Art. 253, §§ 1º e 2º | Acréscimo |
| Art. 258, caput (Inciso 2 "a" e Inciso 3) / § 10 | Alteração/Acréscimo |
| Art. 260, caput | Alteração |
| Art. 280, Parágrafo Único | Acréscimo |
| Art. 293 | Alteração |
| Art. 293, § 4º Inciso 1 / § 5º / § 8º | **Vetada** |
| Art. 293, § 9º / § 10 | **Vetada** (acréscimo) |
| Art. 321, Parágrafo Único | Renumeração |
| Art. 321, §§ 2º, 3º, 4º | Acréscimo |
| Art. 322, caput Inciso 2 / § 1º caput | Alteração |
| Arts. 323-A a 323-M | Acréscimo (13 artigos novos — regime de infrações/PNCT) |
| Art. 325, § 4º | Acréscimo |
| Art. 327-A, §§ 1º-2º | Acréscimo (artigo novo) |
| Art. 327-A, § 3º | **Vetada** (acréscimo) |
| Art. 330, Parágrafo Único | Renumeração |
| Art. 330, §§ 2º-3º | Acréscimo |
| Arts. 341-A a 341-H | Acréscimo (8 artigos novos — multas por descumprimento de obrigação acessória de CBS/IBS) |
| **Art. 344, Parágrafo Único, Inciso 4** | **Acréscimo** (ver análise abaixo) |
| **Art. 348, §§ 3º e 4º** | **Acréscimo** (ver análise abaixo) |
| Art. 350, § 3º, Inciso 1 | Revogação |
| Arts. 361-365 (parágrafo único de cada) | Alteração + Supressão do parágrafo único de cada um |
| Art. 384, caput / Parágrafo Único Inciso 4 | Alteração/Acréscimo |
| Art. 392, caput + Incisos 1-3 | Alteração/Acréscimo |
| Art. 408, §§ 1º-2º | Alteração |
| Art. 414, caput Inciso 3 "c" / Inciso 6 | Alteração/Acréscimo |
| Art. 422, §§ 2º e 5º | Alteração |
| Art. 424, caput, Inciso 1 | Alteração |
| Art. 434, § 2º-A | Acréscimo |
| Art. 440, caput, Inciso 2 | Alteração |
| Art. 442, caput, Incisos 1-2 | Alteração |
| Art. 450, caput / § 6º | Alteração/Acréscimo |
| Art. 460, caput, Incisos 1-2 | Alteração |
| Arts. 471-A a 471-F | Acréscimo (6 artigos novos — PNCT/conformidade) |
| Art. 472 | Alteração |
| Art. 473, §§ 4º-6º | Acréscimo |
| Art. 475, §§ 7º e 10 | Alteração |
| Art. 481 (caput) | Alteração |
| Art. 481, §§ 3º, 6º, 7º, 8º, 9º, 10 | Revogação |
| Art. 481, § 5º-A | Ressalva |
| Art. 482, § 2º Incisos 1-2 / § 5º | Revogação |
| Art. 482-A | Acréscimo (artigo novo) |
| Art. 483, § 1º Inciso 1 "b" / § 2º | Alteração |
| Art. 483, § 5º | Acréscimo |
| Art. 484 | Alteração |
| Art. 485 (caput, Incisos 1-2) / § 8º | Alteração/Acréscimo |
| Art. 486 | Alteração |
| Art. 487, § 2º | Alteração |
| Art. 487, § 12 | Acréscimo |
| Art. 493-A | Acréscimo (artigo novo) |
| Art. 517 | Alteração |
| Art. 542, caput, Inciso 36, "i" | Revogação |
| Art. 544, caput, Inciso 3 | Alteração |
| **Anexo VII** | **Vetada** (alteração) — permanece o texto original |
| **Anexo XIV** | **Revogação** (já resolvido em sessão anterior — ver `DEFINE_REGRAS_TRIBUTARIAS_CACHE.md`) |
| **Anexo XX** | Alteração (tabela de partilha do Simples Nacional, LC 123/2006, 2027-2028) |
| **Anexo XXI** | Alteração (tabela de partilha do Simples Nacional, LC 123/2006, 2029) |

</details>

---

## Análise Focada: Arts. 343, 344, 346, 347, 348 (citados por número no código real)

Estes são os únicos dispositivos desta lista que `motor_calculo/tabela_aliquotas.py`,
`motor_calculo/regras_fiscais.py` e `api/routers/simulate.py` citam por número hoje.

| Artigo | Aparece na lista de alterações da LC 227/2026? | Texto novo (fonte primária) | Impacto no código já escrito |
|--------|--------------------------------------------------|-------------------------------|-------------------------------|
| **Art. 343** (IBS 2026, 0,1%) | **Não** | — | Nenhum. Alíquota, artigo e texto continuam exatamente os mesmos |
| **Art. 346** (CBS 2026, 0,9%) | **Não** | — | Nenhum. Idem |
| **Art. 347** (CBS 2027-2028, alíquota de referência ainda não fixada) | **Não** | — | Nenhum. Continua corretamente `None` — a LC 227/2026 não fixa essa alíquota |
| **Art. 344** (IBS 2027-2028, 0,05%+0,05%) | **Sim** — ganha um **Inciso IV** novo no parágrafo único | *"IV – serão consideradas como alíquotas de referência do IBS para fins do disposto no § 2º do art. 189, no § 8º do art. 485, no § 13 do art. 486 e no § 12 do art. 487."* (texto integral, "(NR)") | **Nenhuma mudança no número.** O inciso IV não altera os 0,05%/0,05% do *caput* — ele **estende o uso jurídico** dessa alíquota: agora ela também conta como "alíquota de referência do IBS" para o cálculo de outros dispositivos (regimes específicos com redução proporcional). Nenhum desses 4 artigos (189, 485, 486, 487) está implementado neste projeto hoje — não há regressão, mas é um dispositivo novo, hoje não citado em lugar nenhum do código, que passaria a ser relevante se/quando esses regimes forem modelados |
| **Art. 348** (compensação IBS/CBS × PIS/COFINS em 2026) | **Sim** — ganha **§ 3º e § 4º** novos | § 3º: se houver auto de infração por descumprimento de obrigação acessória do **art. 341-G** (artigo novíssimo, também criado pela LC 227/2026), o contribuinte tem 60 dias para sanar; § 4º: sanando, a penalidade é extinta | **Nenhuma mudança na mecânica de compensação já codificada** (incisos I, II, III e §§ 1º/2º do art. 348, de onde vem `fonte_legal_compensacao`, **não foram tocados**). Os novos §§ 3º/4º tratam de um procedimento administrativo de multa **completamente diferente e não relacionado**, ligado a um regime de penalidades que este projeto não modela |

**Conclusão desta análise focada: nenhuma alíquota ou regra já codificada neste projeto ficou
numericamente errada por causa da LC 227/2026.** O que existe são dois dispositivos novos (art.
344, IV; art. 348, §§ 3º/4º) que ampliam o alcance jurídico de artigos já citados, sem contradizer
o que já está no código — e que só passam a importar quando/se este projeto modelar os regimes
específicos ou o regime de penalidades a que se referem (nenhum dos dois modelado hoje).

### Achado sobre uma citação pré-existente no código

`motor_calculo/tabela_aliquotas.py` (linha 13, desde o commit `7f78300`, 2026-07-25 — **três dias
antes** de este projeto ter qualquer registro formal de conhecer a LC 227/2026, no
`CLAUDE.md`/SDD) já contém a frase *"Alíquotas extraídas do texto real da LCP 214/2025 (com as
alterações da LCP 227/2026), conferido no HTML ingerido do Planalto."* Isso **antecipa
corretamente** a conclusão desta sessão (os números não mudaram), mas não há, nos SHIPPED/DEFINE
arquivados, nenhum registro de que a LC 227/2026 tenha sido efetivamente consultada antes de hoje —
o comentário parece coincidentemente certo, não auditavelmente verificado no momento em que foi
escrito. Não é um bug funcional (o número está correto), mas é uma inconsistência de rastreabilidade
que vale nomear: uma citação que *afirma* verificação que a trilha do projeto (CLAUDE.md, SDD) não
sustenta até esta sessão.

---

## Anexo I (Cesta Básica) — Não Afetado, Já Confirmado em Sessão Anterior

Confirmado por `DEFINE_REGRAS_TRIBUTARIAS_CACHE.md` (mesma investigação de fonte primária, sessão
anterior) e re-confirmado nesta sessão pela mesma lista oficial: **o Anexo I não aparece** na lista
de dispositivos alterados pela LC 227/2026. Não repetido em detalhe aqui — ver o documento citado.

## Demais Anexos (VII, XIV, XX, XXI) — Nenhum Usado no Código Deste Projeto

- **Anexo VII** (alimentos com redução de 60% de IBS/CBS): a alteração da LC 227/2026 foi **vetada**
  — o texto original permanece vigente. Não usado em nenhum lugar do código hoje.
- **Anexo XIV** (medicamentos com alíquota zero, art. 146): **revogado** — já resolvido na sessão
  anterior. Não usado no código hoje (fora de escopo de `REGRAS_TRIBUTARIAS_CACHE`, que cobre só o
  Anexo I).
- **Anexos XX e XXI**: confirmado por leitura do texto integral — são tabelas de **partilha de
  tributos do Simples Nacional** (reproduzindo o Anexo III e o Anexo IV da LC 123/2006, para os
  períodos de transição 2027-2028 e 2029) dentro da própria LCP 214/2025. **Não relacionados a
  CBS/IBS/IS do regime geral**, e o Simples Nacional não é modelado em nenhum lugar deste projeto
  hoje (`grep` confirma zero ocorrências de "Simples Nacional" em código de produção).

**Conclusão: nenhum dos quatro Anexos afetados pela LC 227/2026 (VII, XIV, XX, XXI) tem qualquer
uso hoje em `motor_calculo/`, `api/` ou `db/`.**

## Achado Adicional Fora do Escopo dos Artigos Já Codificados

A LC 227/2026 revoga o **art. 69 da Lei 10.833/2003** (texto confirmado: limita a 10% uma multa por
declaração de importação irregular, prevista no art. 84 da MP 2.158-35/2001 — também revogado pela
mesma LC 227/2026). **Não relacionado** ao art. 2º da Lei 10.833/2003 (alíquota de 7,6% de COFINS
não-cumulativa), que é o único dispositivo dessa lei citado em `motor_calculo/regime_atual.py`.
Ambas as revogações substituem esse mecanismo de multa por importação pelo novo regime de
penalidades para CBS/IBS (arts. 323-A a 341-H, já catalogados acima) — assunto não modelado neste
projeto.

---

## Vigência (Art. 182 da própria LC 227/2026)

A LC 227/2026 entra em vigor na data de publicação (14/01/2026), com efeitos:

- a partir de 1º/01/2027, só para o art. 76, II, "c" e o art. 169 da LCP 214/2025 (nenhum dos dois
  usado neste projeto);
- a partir da data de eleição do Presidente do CGIBS, só para os §§ 4º/5º do art. 52 **da própria
  LC 227/2026** (não da LCP 214/2025);
- **a partir da publicação, para todos os demais dispositivos** — o que inclui o art. 344, IV e o
  art. 348, §§ 3º/4º analisados acima. Ou seja: **já estão em vigor desde 14/01/2026**, mais de 6
  meses antes desta sessão.

---

## A Pergunta Que Este Documento NÃO Responde Sozinho: A Ingestão Está Desatualizada?

Esta era a preocupação central que motivou a tarefa. A resposta honesta, depois da investigação, é
**"provavelmente não, mas não confirmado com certeza a partir deste ambiente"** — o que já muda
significativamente o quadro de risco em relação à premissa inicial.

### Evidências a favor de "a ingestão provavelmente já reflete a LC 227/2026"

1. `dags/ingestao_legal_dag.py` usa como fonte `https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm`
   — **essa é a URL do "texto compilado"** do Planalto (padrão `ccivil_03`), que o próprio site
   mantém atualizado *in loco* com anotações "(Redação dada pela Lei Complementar nº XXX)" toda vez
   que uma lei sofre alteração — ao contrário da "Publicação Original" do DOU (que é um instantâneo
   imutável do texto como sancionado em 2025, sem as alterações de 2026).
2. Confirmado via `gh api .../actions/jobs/89681058748/logs` (log real do GitHub Actions, não
   suposição): a ingestão real rodou em **2026-07-25, 13:01-13:22 UTC** — mais de **6 meses** depois
   da LC 227/2026 entrar em vigor (14/01/2026). O parser extraiu **580 artigos**, número compatível
   com "544 (maior número original) + ~34 artigos novos inseridos pela LC 227/2026 com sufixo -A a
   -M" (contei 7-A, 81-A, 98-A, 98-B, 218-A, 219-A, 323-A a 323-M [13], 341-A a 341-H [8], 471-A a
   471-F [6], 482-A, 493-A = 34 artigos novos) — consistente com a hipótese de que o HTML raspado
   em julho já era o texto pós-LC 227/2026.
3. Os artigos com sufixo "-A" etc. (ex.: `341-A`) **não existem** no texto da Publicação Original de
   16/01/2025 (confirmado por busca direta no texto baixado nesta sessão) — são exclusivos da
   LC 227/2026, o que reforça que, se o parser os contou, a fonte já era a versão atualizada.

### Por que isso NÃO está confirmado com certeza

- `planalto.gov.br` está bloqueado a partir deste ambiente — não há como buscar agora o HTML ao
  vivo e comparar diretamente.
- Não há acesso a `qdrant-client` neste sandbox nem credenciais locais do Qdrant Cloud (política do
  projeto: infraestrutura real só roda via GCP/CI) — não foi possível inspecionar diretamente o
  conteúdo de nenhum chunk já indexado para procurar, por exemplo, o texto literal do art. 341-A.
- Os logs de CI disponíveis (verificação de busca híbrida) confirmam a *contagem* de artigos (580) e
  testam recuperação de 5 dispositivos que **não mudaram** com a LC 227/2026 (art. 11 §3º I "a",
  art. 66 II, art. 388 parágrafo único, art. 28 II, art. 348 III "b") — nenhum desses é uma boa
  prova de que o texto pós-LC-227 foi ingerido, porque são idênticos nas duas versões.

**Recomendação objetiva para fechar esta pergunta com certeza** (não executada nesta sessão, pois
runa contra infraestrutura real): rodar uma consulta de busca híbrida contra a coleção
`legislacao_tributaria` já em produção, buscando por um trecho que **só existe na versão pós-LC
227/2026** — por exemplo o texto literal do art. 341-A, ou o Inciso IV do parágrafo único do art.
344 catalogado acima. Se o texto for encontrado, a ingestão está atualizada; se não, está
desatualizada e precisa de reingestão. Isso é uma consulta de leitura, rodável como um passo
adicional no próprio workflow `ingestao.yml` (ou um script novo `scripts/verificar_lc227_ingerida.py`
no mesmo padrão de `scripts/verificar_busca_hibrida.py`) — **decisão de próxima etapa**, não
executada aqui.

---

## O Que Este Documento Não Decide (e Por Quê)

Esta investigação confirma que:
- a LC 227/2026 é maior e mais abrangente do que o achado original sugeria (244 alterações efetivas
  em 231 artigos/parágrafos distintos + 4 Anexos, não "dezenas entre 330-544");
- **nenhuma alíquota ou regra já codificada está numericamente errada** por causa dela;
- a exposição real (corpus desatualizado) é **plausível mas não confirmada** — pode já não existir.

Isso muda a natureza da decisão que o usuário pediu para este documento resolver. As perguntas que
ficam em aberto não são de clareza de requisito (a lei está bem catalogada agora), mas de
**estratégia**, e nenhuma delas foi decidida em brainstorm ainda:

1. **Vale a pena tratar isso como uma feature agora?** Dado que (a) nenhum número codificado está
   errado e (b) a suspeita de corpus desatualizado é só plausível, não confirmada — o esforço pode
   ser desproporcional ao risco real hoje. Uma alternativa mínima seria só fechar a pergunta acima
   (rodar uma consulta de verificação) antes de decidir se compensa qualquer coisa maior.
2. **Se a ingestão estiver desatualizada, qual é a estratégia?** Três caminhos distintos, com custo e
   arquitetura muito diferentes, nenhum escolhido:
   - (a) **Só reingerir** `LCP_214_2025` a partir da mesma URL do Planalto (`Lcp214.htm`) — mais
     simples, mas assume que o Planalto já atualizou o texto compilado (evidência a favor, não
     certeza).
   - (b) **Ingerir a LC 227/2026 como fonte própria**, seguindo o mesmo padrão `LegalSource` já usado
     para TCU/CGIBS — mais correto do ponto de vista de proveniência (cada norma citável por si),
     mas maior (a LC 227/2026 é uma lei de ~5.100 linhas de texto extraído, cobrindo CGIBS, ITCMD,
     CTN, penalidades — não é um "patch" pequeno).
   - (c) **Não reingerir nada agora**, e só documentar a LC 227/2026 como fonte adicional citável
     diretamente no código (`fonte_legal` passa a citar "LCP 214/2025, art. 344, § único, IV,
     acrescido pela LC 227/2026" sem depender do Qdrant refletir isso) — mais barato, mas não
     resolve a citação para *nenhum outro* trecho da lei que a busca híbrida/RAG conversacional
     possa recuperar desatualizado.
3. **O achado é maior que uma "feature simples"** — ele toca 8 subseções inteiramente novas de
   penalidades (arts. 323-A a 341-H), instituição do CGIBS, ITCMD, e mudanças no CTN — assuntos que
   não têm relação alguma com o que este projeto modela hoje (CBS/IBS/IS/Split Payment). Decidir
   "o que disso realmente importa a este produto" é uma pergunta de **escopo de produto**, não só de
   dado técnico — mais adequada a uma conversa de brainstorm do que a uma extração de requisitos.

---

## Recomendação

**Esta sessão não deveria fechar direto para `/design`.** Os itens acima (1-3) são decisões de
direção, não lacunas de clareza sobre o que a lei diz — e o próprio brainstorm anterior
(`REGRAS_TRIBUTARIAS_CACHE`) já tinha sinalizado explicitamente: *"Recomenda-se ao usuário abrir uma
sessão de brainstorm dedicada para avaliar o impacto da LC 227/2026"*. Esta sessão de `/define`
cumpriu a parte que só uma investigação factual resolve (catalogar com precisão, cruzar contra o
código, avaliar a exposição real) — mas a pergunta "o que fazer com isso" continua sem uma resposta
óbvia, e non há como um `/define` decidir sozinho entre "não fazer nada agora" e "uma feature de
reingestão" e "uma feature de nova fonte legal" sem faltar com a disciplina que o próprio projeto já
demonstrou (nunca estimar o que a lei não fixa, nunca decidir arquitetura sem o usuário).

**Sugestão concreta para destravar rapidamente, sem reabrir todo o brainstorm:** a Pergunta 1 acima
("vale a pena tratar isso como feature agora, dado que nada está numericamente errado?") poderia ser
respondida com uma única verificação técnica barata — rodar a consulta de busca híbrida sugerida
acima contra a produção — antes de decidir se as Perguntas 2 e 3 (que são de arquitetura e escopo de
produto) merecem uma sessão de brainstorm dedicada.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | A lei está catalogada com precisão total (255 dispositivos, fonte primária, URLs) |
| Users | 2 | Usuários corretos, mas o "pain point" real depende da resposta ainda não confirmada sobre a ingestão |
| Goals | 1 | Não há um objetivo MoSCoW definido — a "meta" depende de uma decisão de estratégia (reingerir? recodificar? nada?) ainda não tomada |
| Success | 1 | Sem critério de sucesso definido além da própria investigação — não há "feature" com critério de aceite ainda |
| Scope | 2 | Escopo do que a lei toca está claro; escopo do que fazer a respeito não está |
| **Total** | **9/15** | Abaixo do mínimo de 12/15 — **não avançar para `/design` sem decisão do usuário** |

---

## Open Questions

1. Ver "O Que Este Documento Não Decide" acima — as 3 perguntas de estratégia não foram respondidas
   nesta sessão, deliberadamente (fora do mandato de uma extração de requisitos objetiva).
2. Se o usuário decidir seguir para uma feature: qual das 3 estratégias (reingerir / nova fonte
   legal / só citar no código) e com qual prioridade relativa às outras 10 features já roteirizadas
   em `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`?
3. Vale rodar, como passo isolado e barato, a verificação de busca híbrida sugerida (buscar o texto
   do art. 341-A ou do art. 344, IV na coleção já em produção) antes de qualquer decisão maior?

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | define-agent | Versão inicial — catálogo completo dos 255 dispositivos alterados pela LC 227/2026, análise focada nos artigos já codificados (343/344/346/347/348), Anexos (I/VII/XIV/XX/XXI), achado sobre Lei 10.833/2003 art. 69, avaliação (não conclusiva) da exposição da ingestão, e recomendação explícita de não avançar para `/design` sem decisão de estratégia do usuário |

---

## Next Step

**NÃO pronto para `/design`.** Recomendado: decisão do usuário sobre as 3 perguntas de estratégia
acima — possivelmente uma sessão de `/brainstorm` dedicada, como o próprio
`DEFINE_REGRAS_TRIBUTARIAS_CACHE.md` já havia sugerido.
