# BRAINSTORM: Anexos XII, XIII e XV — Redução a Zero/100% de CBS/IBS por NCM

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 12 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva").
> Uma de 6 features que cobrem os 16 Anexos restantes da LCP 214/2025 (o Anexo I foi shipado
> em `REGRAS_TRIBUTARIAS_CACHE`) mais o Simples Nacional. Esta é a mais simples das 6: mesmo
> mecanismo de cálculo do Anexo I (redução a zero), mesma chave (NCM).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_ZERO_XII_XIII_XV |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 12 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** `REGRAS_TRIBUTARIAS_CACHE` (posição 2) cobriu só o Anexo I da LCP 214/2025
(Cesta Básica Nacional, redução a zero por NCM). O usuário confirmou que os 16 Anexos
restantes precisam ser cobertos, não é opcional. Esta feature é o subconjunto que mais se
parece com o Anexo I: os Anexos XII, XIII e XV também aplicam redução a zero (XV é "100%",
tecnicamente redação diferente mas funcionalmente equivalente a zero) e usam exclusivamente
NCM/SH como chave.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/{id}` (DOU Edição Extra de 16/01/2025,
  nº 11-B) — mesma fonte já usada no `/design` do Anexo I. IDs: XII=`40180960`,
  XIII=`40180966`, XV=`40181038`.
- **Anexo XII**: "DISPOSITIVOS MÉDICOS SUBMETIDOS À REDUÇÃO A ZERO DAS ALÍQUOTAS DO IBS E DA
  CBS". Estrutura de itens numerados com sub-itens (ex. "1. Aparelhos de eletrodiagnóstico" →
  "1.1 Eletrocardiógrafos: 9018.11.00"), igual em forma ao Anexo I. ~31 códigos NCM distintos
  observados (contagem aproximada, não exaustiva — exata é trabalho do `/define`).
- **Anexo XIII**: "DISPOSITIVOS DE ACESSIBILIDADE PRÓPRIOS PARA PESSOAS COM DEFICIÊNCIA
  SUBMETIDOS À REDUÇÃO A ZERO DAS ALÍQUOTAS DO IBS E DA CBS". Mesma estrutura hierárquica
  (ex. item 2, "Cadeira de rodas...", com sub-itens 2.1/2.2). ~9 códigos observados.
- **Anexo XV**: "PRODUTOS HORTÍCOLAS, FRUTAS E OVOS SUBMETIDOS À REDUÇÃO DE 100% (CEM POR
  CENTO) DAS ALÍQUOTAS DO IBS E DA CBS". Sem coluna de código separada — os NCMs aparecem
  embutidos na descrição de cada item (ex. "Ovos da subposição 0407.2", "produtos hortícolas
  das posições 07.01, 07.02.00.00, [...], exceto os cogumelos [...] classificados na
  subposição 0709.5"). Já tem pelo menos uma exceção por subposição no próprio texto (item 2),
  do mesmo tipo que os itens 19/20 do Anexo I. ~26 códigos observados.
- Todos os três usam exclusivamente NCM/SH — nenhuma menção a NBS em nenhum dos três.
- **Mecanismo já existe e é reaproveitável sem alteração**: `motor_calculo/reducoes.py::
  aplicar_reducao_a_zero`, `api/ncm.py` (`digitos_ncm`/`prefixos_ncm`), o padrão de duas
  tabelas (item do Anexo + prefixo NCM 1:N) e a resolução por prefixo mais longo em caso de
  colisão (Decisões 1-4 do `DESIGN_REGRAS_TRIBUTARIAS_CACHE.md`). Essa é a única razão desta
  feature ser cotada como "mais simples" — não porque os Anexos em si sejam triviais (XII e
  XV têm hierarquia de sub-itens tão ou mais complexa que o Anexo I).
- **Risco herdado, não resolvido nesta sessão**: a investigação da LC 227/2026 nunca checou
  se ela alterou os Anexos XII, XIII ou XV — só os artigos 343-348. Precisa ser confirmado no
  `/define`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Mecanismo de cálculo | Idêntico ao Anexo I — `aplicar_reducao_a_zero` já existe e é agnóstico a qual Anexo populou a tabela | `/design` decide só entre estender a tabela do Anexo I (`cesta_basica_anexo_i`/`_ncm`, renomeando) ou criar 3 tabelas novas de mesma forma — decisão de nomenclatura/generalização, não de lógica nova |
| Estrutura de exceção | Anexo XV já tem pelo menos 1 item com exceção por subposição (item 2, cogumelos/trufas excluídos) | Mesma disciplina do Anexo I: resolver via prefixo+exclusão, nunca zero por adivinhação |
| Overlap entre Anexos | Não verificado nesta sessão se algum NCM aparece em mais de um dos três Anexos (XII/XIII/XV) ou repete um NCM já coberto pelo Anexo I | Item explícito para o `/define`: se um NCM está em dois Anexos zero diferentes, o resultado é o mesmo (zero), mas a citação da fonte (`dispositivo_legal_ref`) precisa apontar para o Anexo correto, não para o primeiro que bater |
| Relevant KB Domains | python-developer, database-reviewer | Mesmo padrão `Protocol` real/fake e vocabulário `api/ncm.py` já usado no Anexo I |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Abordagem híbrida: mecanismo de cálculo (zero vs. percentual) + tipo de chave (NCM vs. NBS), isolando à parte o que não é produto/serviço (XVI), o que é tributo diferente (XVII) e o Simples Nacional (XVIII-XXIII) | Definiu que XII/XIII/XV formam um grupo próprio (zero + NCM puro), coerente com o mecanismo já existente |
| 2 | Anexos que misturam chave NCM/NBS no mesmo Anexo (IX, X, XI) — como tratar? | Vão para o grupo da chave dominante; itens da chave minoritária ficam documentados como não resolvidos naquela feature | Não afeta esta feature diretamente (XII/XIII/XV são NCM puro), mas confirma que esta feature não herda nenhum item "pendente" de outro grupo |
| 3 | Onde esta leva de 6 features entra na sequência? | Depois das 9 posições já roteirizadas (3-11) — a sequência original mantém prioridade | Define a posição 12 (não antes de `API_EMPRESA_SKUS` etc.) |

**Minimum Questions:** 3 ✅ (decisões tomadas em nível de leva, aplicadas a esta feature específica)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexos XII, XIII, XV) | `legis.senado.leg.br` (DOU original, mesma fonte do Anexo I) | ~31 + ~9 + ~26 códigos observados (contagem aproximada) | Verificado nesta sessão só na forma estrutural (existe, é NCM puro, tem hierarquia); transcrição item a item completa é trabalho do `/define`, como foi feito para o Anexo I |
| Fonte legal | Anexos XII, XIII, XV, LCP 214/2025 | 3 anexos | Cada item é numerado e citável individualmente, mesmo padrão do Anexo I |
| Estrutura de exceção conhecida | Anexo XV, item 2 (cogumelos/trufas) | ≥1 de ~26 | Confirma que pelo menos um dos três Anexos precisa do mecanismo de exclusão, não só igualdade/prefixo simples |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design`, mesmo padrão do Anexo I (subconjunto pequeno incluindo o item com exceção) |

**Como os dados serão usados (se aprovado no /define):** mesmo fluxo do Anexo I —
`/v1/tax/simulate` já teria (a partir da posição 12) uma tabela de itens zero-rated maior;
o lookup por NCM passa a checar múltiplas fontes de zero (Anexo I + XII + XIII + XV), cada
uma citando seu próprio `dispositivo_legal_ref`.

---

## Approaches Explored

### Approach A: Estender o schema do Anexo I (tabelas `cesta_basica_anexo_i*` generalizadas ou renomeadas) ⭐ Recomendada

**What:** Reaproveitar a forma exata de `cesta_basica_anexo_i` / `cesta_basica_anexo_i_ncm`
(migração 005), adicionando os itens de XII/XIII/XV nas mesmas tabelas (com uma coluna
`anexo` para diferenciar a origem) ou em tabelas irmãs de mesma forma. `motor_calculo/
reducoes.py::aplicar_reducao_a_zero` não muda.

**Pros:**
- Zero código de cálculo novo — só dado novo na mesma forma
- Consistente com o princípio "nomear explicitamente o dispositivo" já validado
- Decisão de design pequena: só schema (uma tabela vs. quatro) e nomenclatura

**Cons:**
- Precisa decidir se renomeia `cesta_basica_anexo_i` para algo mais genérico (ex.
  `reducao_zero_ncm`) — muda nome de tabela já em produção, exige migração cuidadosa
- Overlap entre Anexos (mesmo NCM em dois Anexos zero) precisa de regra de desempate para a
  citação da fonte, não só para o valor (que já é zero nos dois)

**Why Recommended:** É a única abordagem que não duplica lógica de cálculo já provada em
produção; o único trabalho real é popular dado novo e decidir nomenclatura.

### Approach B: Tabelas completamente novas e isoladas por Anexo (`anexo_xii_ncm`, `anexo_xiii_ncm`, `anexo_xv_ncm`)

**What:** Não tocar nas tabelas do Anexo I; criar três tabelas novas, uma por Anexo, cada uma
com sua própria lógica de lookup.

**Pros:**
- Isolamento total — nenhum risco de regressão no Anexo I

**Cons:**
- Triplica uma tabela cuja forma já é idêntica — motor de cálculo (`aplicar_reducao_a_zero`)
  teria que consultar 4 fontes em vez de 1, ou o router precisaria agregar manualmente
- Contradiz a lição do próprio `SHIPPED_2026-07-28.md` (Anexo I): "código morto" e duplicação
  de vocabulário já compartilhado (`api/ncm.py`) foi explicitamente evitado antes

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — estender/generalizar o schema do Anexo I, sem lógica de cálculo nova |
| **User Confirmation** | Decisão de agrupamento confirmada pelo usuário nesta sessão (nível de leva); a escolha entre A e B fica para o `/design`, com recomendação registrada aqui |
| **Reasoning** | Reaproveita 100% do mecanismo já provado em produção; o esforço real está em popular dado novo, não em desenhar lógica nova |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo desta feature é XII, XIII e XV — os 3 Anexos de redução a zero/100% restantes | Mesmo mecanismo de cálculo do Anexo I, menor risco técnico das 6 features desta leva | Incluir também Anexos de 60% (posições 13/14) — rejeitado, mecanismo de cálculo diferente |
| 2 | Nenhuma alíquota/NCM tratada como definitiva sem verificação contra fonte primária no `/define` | Mesma disciplina do resto do projeto | Aceitar a contagem aproximada desta sessão como final — rejeitado, é só um indicador de escala |
| 3 | Verificar explicitamente se a LC 227/2026 alterou XII, XIII ou XV | A investigação da LC 227/2026 nunca cobriu os Anexos, só os artigos 343-348 | Assumir que os Anexos não foram tocados — rejeitado, seria uma suposição não verificada |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Resolver overlap entre todos os 4 Anexos zero (I, XII, XIII, XV) nesta sessão | Exige transcrição item a item completa dos 4, que é trabalho do `/define`, não do `/brainstorm` | Sim, no `/define` |
| Unificar em uma única feature com os Anexos de 60% | Mecanismo de cálculo diferente (zero vs. percentual sobre a alíquota de referência) — decisão de agrupamento já tomada pelo usuário | Não aplicável — decisão já tomada |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Agrupamento híbrido (mecanismo + chave) | ✅ | Confirmado | Definiu esta feature como grupo "zero + NCM" |
| Tratamento de Anexos mistos (IX/X/XI) | ✅ | Dominante + pendência explícita | Não se aplica a esta feature (XII/XIII/XV são NCM puro) |
| Posição na sequência (antes/depois das 9 restantes) | ✅ | Depois — posição 12 | Registrado no roadmap |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Os Anexos XII (dispositivos médicos), XIII (acessibilidade) e XV (hortícolas/frutas/ovos) da
LCP 214/2025 aplicam redução a zero/100% de CBS/IBS por NCM, no mesmo mecanismo já shipado
para o Anexo I — mas `/v1/tax/simulate` só conhece o Anexo I hoje. Itens desses 3 Anexos são
simulados com a alíquota geral da fase, superestimando a carga tributária projetada.

### Success Criteria (Draft)
- [ ] Conteúdo completo dos 3 Anexos (todos os itens, todos os códigos, todas as exceções)
      verificado contra fonte primária (`legis.senado.leg.br`)
- [ ] Decisão explícita sobre schema: generalizar as tabelas do Anexo I ou criar novas
- [ ] `/v1/tax/simulate` aplica zero a itens cujo NCM esteja em qualquer um dos 4 Anexos zero
      (I, XII, XIII, XV), citando o Anexo correto
- [ ] Exceções por subposição (confirmadas no Anexo XV, item 2; a verificar nos outros 2)
      resolvidas com o mesmo mecanismo de prefixo+exclusão do Anexo I, nunca zero por
      adivinhação
- [ ] Overlap entre os 4 Anexos zero resolvido com regra de desempate explícita
- [ ] Confirmado se a LC 227/2026 alterou algum dos 3 Anexos
- [ ] `motor_calculo/` continua sem dependência de infraestrutura

### Constraints Identified
- Mesmo mecanismo de `aplicar_reducao_a_zero` — nenhuma função de cálculo nova
- Sem RLS na(s) tabela(s) (dado legal público)
- Verificação de fonte primária obrigatória, mesma disciplina do Anexo I

### Out of Scope (Confirmed)
- Anexos de redução percentual (posições 13-14)
- Anexo XVI, XVII, Simples Nacional (posições 15-17)
- Qualquer trabalho fora desta leva (posições 3-11 do roadmap original)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 (nível de leva, aplicadas a esta feature) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 3 de 2 |
| Duration | Parte de uma sessão única cobrindo as 6 features desta leva, incluindo verificação real contra `legis.senado.leg.br` para os 21 Anexos restantes |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`

**Posição na sequência:** 12 de 17 — depende de `API_EMPRESA_SKUS` (posição 3) e demais
posições 4-11 terem prioridade, conforme decisão do usuário registrada no
`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.
