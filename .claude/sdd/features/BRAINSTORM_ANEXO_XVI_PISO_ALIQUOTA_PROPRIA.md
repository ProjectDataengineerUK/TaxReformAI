# BRAINSTORM: Anexo XVI — Piso da Alíquota Própria de Estados e Municípios

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 15 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva").
> Estruturalmente diferente de todas as outras 5 features desta leva: não é sobre produto nem
> serviço — é um piso percentual por ano, aplicável à alíquota que Estados/Municípios podem
> fixar para o IBS.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVI_PISO_ALIQUOTA_PROPRIA |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 15 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** O brainstorm original de `REGRAS_TRIBUTARIAS_CACHE` já tinha notado que o
Anexo XVI "não é sobre produto — é o piso de alíquota própria dos entes federativos" e
assumiu, sem verificar, que seria "por Estado/Município". Esta sessão verificou o conteúdo
real contra fonte primária.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/40181067`.
- Título real: **"LIMITE INFERIOR PARA FIXAÇÃO DA ALÍQUOTA PRÓPRIA EM PROPORÇÃO DA ALÍQUOTA
  DE REFERÊNCIA"**.
- **Correção ao entendimento anterior**: não é uma tabela por Estado/Município — é uma
  **tabela única nacional, indexada por ano**, começando em 2029:

  | Ano | Limite Inferior (% da Alíquota de Referência) |
  |-----|------------------------------------------------|
  | 2029 | 81,0% |
  | 2030 | 81,0% |
  | 2031 | 81,0% |
  | 2032 | 81,0% |
  | 2033 | 90,5% |
  | (continua além de 2033, não capturado nesta sessão — trabalho do `/define`) |

  O mesmo limite vale para **todos** os entes — é um piso nacional, não uma tabela de 27
  linhas (UFs) como o `icms_interno()` de `motor_calculo/regime_atual.py`.
- **Relação com o "achado 12" do roadmap** (linha do tempo da reforma 2029-2033, item de
  monitoramento fora da sequência ativa, bloqueado porque a lei que fixaria CBS/IS nesse
  período ainda não existe): esse limite **já está fixado** por esta mesma LCP 214/2025 — não
  é um dado bloqueado como o achado 12. São coisas diferentes: o achado 12 é sobre a
  **alíquota de referência em si** (art. 347, ainda pendente de lei ordinária para 2027-2028
  em diante); o Anexo XVI é sobre **quanto abaixo dessa alíquota de referência** um Estado ou
  Município pode fixar sua própria fatia do IBS, **como proporção** — não é um valor absoluto
  independente. Ou seja, o Anexo XVI é utilizável, mas seu resultado prático (um valor em %)
  só tem sentido depois que a alíquota de referência (achado 12) for conhecida — há uma
  dependência de dado real entre os dois, mesmo sem serem a mesma feature.
- **Não é por produto/serviço**: nenhum NCM, nenhum NBS. Não reaproveita `api/ncm.py` nem o
  padrão de lookup por prefixo de nenhuma das outras 5 features desta leva.
- Nenhuma alíquota de CBS foi observada no Anexo XVI — é especificamente sobre a fatia do IBS
  (Estados/Municípios), consistente com o IBS ser o tributo subnacional do IVA Dual.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Estrutura de dado | Tabela simples (ano → percentual), sem chave de produto/serviço | Schema mais simples que qualquer outra feature desta leva — provavelmente uma tabela de 1 coluna-chave (ano) + 1 valor, sem tabela de junção 1:N como o Anexo I |
| Dependência real com o achado 12 | O valor do Anexo XVI só produz um número de alíquota concreto depois que a alíquota de referência (bloqueada, achado 12) for conhecida | `/define` precisa decidir: expor só o percentual do piso (útil por si só, ex. para compliance/auditoria de quanto um Estado pode ou não fixar) sem tentar calcular a alíquota final enquanto a referência não existir — mesma disciplina de "nunca estimar" já usada para 2027-2028 |
| Nenhum consumidor óbvio em `/v1/tax/simulate` hoje | O endpoint simula CBS/IBS por item de mercadoria/serviço; este dado é sobre a **faculdade normativa** de um ente fixar sua própria alíquota, não sobre o cálculo de uma operação específica | `/define` precisa decidir se isso vira um campo informativo na resposta (ex. um "limite legal" exposto junto ao resultado) ou um endpoint/consulta separada — decisão de produto, não só técnica |
| Relevant KB Domains | database-reviewer (schema simples), python | Nenhum reaproveitamento de código das outras 5 features — Anexo XVI é independente |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Híbrido: mecanismo + chave, isolando o que não é produto/serviço | Confirmou que o Anexo XVI merece feature própria isolada |
| 2 | Onde esta leva entra na sequência? | Depois das 9 posições já roteirizadas | Posição 15 |
| 3 | O Anexo XVI é por Estado/Município ou nacional? | Verificado nesta sessão contra fonte primária: é uma tabela única nacional por ano, não por ente | Corrige a suposição do brainstorm original de `REGRAS_TRIBUTARIAS_CACHE`; simplifica o schema esperado |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexo XVI) | `legis.senado.leg.br` | 5 anos observados nesta sessão (2029-2033), tabela provavelmente continua além | Contagem completa (todos os anos até o fim da tabela) é trabalho do `/define` |
| Fonte legal | Anexo XVI, LCP 214/2025 | 1 anexo | Cada linha (ano) é citável individualmente |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design` |

**Como os dados serão usados (se aprovado no /define):** ainda em aberto — depende da decisão
de produto sobre onde esse dado aparece (campo informativo vs. endpoint próprio), a resolver
no `/define`.

---

## Approaches Explored

### Approach A: Tabela simples (ano → percentual), exposta como dado informativo em `/v1/tax/simulate` ⭐ Recomendada

**What:** Uma tabela nova, pequena, sem chave de produto/serviço. `/v1/tax/simulate` (quando
a fase calculada for ≥ 2029) inclui o limite inferior do ano correspondente como campo
informativo na resposta — não afeta o cálculo de CBS/IBS em si (que já está bloqueado pelo
achado 12 para o regime geral em 2029+), só documenta a faculdade normativa.

**Pros:**
- Schema mais simples de toda a leva
- Não promete calcular algo que a lei ainda não permite calcular (a alíquota de referência
  em si) — respeita a mesma disciplina do achado 12
- Ainda assim entrega valor informativo real e citável

**Cons:**
- Valor prático limitado enquanto a alíquota de referência (achado 12) não for conhecida —
  é mais um dado de compliance do que um número de cálculo até lá

**Why Recommended:** É a única abordagem que não tenta contornar o bloqueio já reconhecido do
achado 12 fingindo que o Anexo XVI resolve algo que ele não resolve sozinho.

### Approach B: Endpoint dedicado de consulta ao piso, fora de `/v1/tax/simulate`

**What:** Endpoint separado (ex. `GET /v1/tax/piso-aliquota-propria?ano=2030`) em vez de
embutir no resultado da simulação.

**Pros:**
- Não polui o payload de simulação com um dado que não afeta o cálculo do item

**Cons:**
- Menos descoberta para o usuário — exige saber que o endpoint existe
- Adiciona uma rota nova para um dado que poderia perfeitamente ser um campo informativo

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — campo informativo em `/v1/tax/simulate`, sem tentar calcular a alíquota final enquanto o achado 12 permanecer bloqueado |
| **User Confirmation** | Escopo/posicionamento confirmados nesta sessão; escolha final entre A e B fica para o `/define` |
| **Reasoning** | Consistente com a disciplina já estabelecida de nunca estimar o que a lei ainda não fixa |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo é só o Anexo XVI, feature isolada | Não é produto/serviço, não reaproveita nenhum mecanismo das outras 5 features | Agrupar com o Anexo XVII (também "isolado") — rejeitado, XVII é outro tributo (IS), sem relação de dado com XVI |
| 2 | O Anexo XVI é uma tabela nacional única por ano, não por Estado/Município | Verificado contra fonte primária nesta sessão | Manter a suposição original (por ente) — corrigida |
| 3 | Não calcular a alíquota final do IBS subnacional enquanto a alíquota de referência (achado 12) não existir | Mesma disciplina de "nunca estimar" já aplicada a 2027-2028 e ao achado 12 | Estimar usando a alíquota de 2026 como proxy — rejeitado, seria uma aproximação não autorizada por nenhuma fonte |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Calcular a alíquota final do IBS por ente usando o piso do Anexo XVI | Depende da alíquota de referência (achado 12), ainda bloqueada | Sim, automaticamente, quando o achado 12 for desbloqueado — sem precisar de nova feature, só um consumidor a mais do mesmo dado |
| Agrupar com Anexo XVII | Tributos e naturezas de dado diferentes | Não aplicável |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Isolamento do Anexo XVI como feature própria | ✅ | Confirmado (parte da decisão de agrupamento híbrido) | Mantido |
| Sequência (posição 15) | ✅ | Depois das 9 restantes | Registrado no roadmap |
| Correção "nacional, não por ente" | ✅ | N/A (achado técnico desta sessão) | Registrado como Key Decision 2 |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O Anexo XVI da LCP 214/2025 fixa, ano a ano a partir de 2029, o limite inferior que
Estados/Municípios podem usar para fixar sua própria alíquota de IBS, como proporção da
alíquota de referência. Esse dado não está representado em lugar nenhum do projeto hoje.

### Success Criteria (Draft)
- [ ] Tabela completa do Anexo XVI (todos os anos, não só 2029-2033 observados nesta sessão)
      verificada contra fonte primária
- [ ] Decisão de produto tomada: campo informativo em `/v1/tax/simulate` vs. endpoint próprio
- [ ] Nenhuma alíquota final calculada usando este dado enquanto o achado 12 (alíquota de
      referência) permanecer bloqueado
- [ ] Confirmado se a LC 227/2026 alterou o Anexo XVI

### Constraints Identified
- Não depende tecnicamente de nenhuma das outras 5 features desta leva
- Valor prático condicionado ao desbloqueio do achado 12 (fora do controle desta feature)

### Out of Scope (Confirmed)
- Cálculo da alíquota final do IBS subnacional (depende do achado 12)
- Qualquer Anexo de produto/serviço (posições 12-14)
- Anexo XVII, Simples Nacional (posições 16-17)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 (nível de leva + 1 verificação técnica específica) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 3 de 2 |
| Duration | Parte da sessão única desta leva |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md`

**Posição na sequência:** 15 de 17 — depende de prioridade das posições 3-11 e das posições
12-14 conforme `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.
