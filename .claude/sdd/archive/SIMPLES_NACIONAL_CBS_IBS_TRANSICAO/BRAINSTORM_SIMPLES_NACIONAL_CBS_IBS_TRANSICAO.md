# BRAINSTORM: Integração de CBS/IBS à Partilha do Simples Nacional (Anexos XVIII-XXIII)

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 17 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva"). A
> maior correção de escopo desta sessão: o brainstorm original de `REGRAS_TRIBUTARIAS_CACHE`
> descreveu os Anexos XVIII-XXIII como "produção de efeitos futura" de 5 dos Anexos de
> redução (I-V, VII). **Essa descrição está errada** — verificado contra fonte primária
> nesta sessão. São os Anexos I, II, III, IV, V e VII do **Simples Nacional (LC 123/2006)**,
> um regime tributário inteiro que este projeto não modela hoje de nenhuma forma.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMPLES_NACIONAL_CBS_IBS_TRANSICAO |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 17 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** O brainstorm original de `REGRAS_TRIBUTARIAS_CACHE` (fontes secundárias,
não verificadas) descreveu "Anexos XVIII a XXIII, versões de 'produção de efeitos' futura de
5 [Anexos] (I-V, VII)" — uma dimensão temporal, análoga ao conceito de "fase" que
`TabelaAliquotasSeed` já tem. Esta sessão verificou o conteúdo real contra fonte primária e
encontrou algo estruturalmente diferente e maior.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/{id}` — XVIII=`40181079`,
  XIX=`40181111`, XX=`40181117`, XXI=`40181123`, XXII=`40181129`, XXIII=`40181135`.
- **Cada um dos 6 Anexos abre com a citação explícita**: `"(Lei Complementar nº 123, de 14 de
  dezembro de 2006)"`, seguida do número do Anexo *daquela* lei (não da LCP 214/2025):
  - Anexo XVIII → "ANEXO I" do Simples Nacional: *Alíquotas e Partilha — Comércio*
  - Anexo XIX → "ANEXO II": *Alíquotas e Partilha — Indústria*
  - Anexo XX → "ANEXO III": *Alíquotas e Partilha — Receitas de locação de bens móveis e de
    prestação de serviços não relacionados no § 5º-C do art. 18*
  - Anexo XXI → "ANEXO IV": *Alíquotas e Partilha — Receitas decorrentes da prestação de
    serviços relacionados no § 5º-C do art. 18*
  - Anexo XXII → "ANEXO V": *Alíquotas e Partilha — Receitas decorrentes da prestação de
    serviços relacionados no § 5º-I do art. 18*
  - Anexo XXIII → "ANEXO VII": *Valores fixos do Microempreendedor Individual (MEI)*
- **Não são Anexos de redução de CBS/IBS por produto** — são as tabelas do **Simples
  Nacional**, o regime tributário unificado e simplificado para micro/pequenas empresas
  (substitui PIS/COFINS/ICMS/ISS/IRPJ/CSLL/CPP por um único DAS mensal). A LCP 214/2025
  reproduz e atualiza essas tabelas para incorporar CBS e IBS na partilha do DAS.
- **Estrutura confirmada (Anexo XVIII, Comércio)**: cada Anexo tem (a) uma tabela de faixas
  de receita bruta em 12 meses (6 faixas, de "até R$ 180.000,00" a "de R$ 3.600.000,01 a
  R$ 4.800.000,00"), com alíquota nominal e valor a deduzir — **vigente só para 2027-2028**
  (`"Vigência: 1º/1/2027 a 31/12/2028"`); e (b) uma tabela de partilha percentual do DAS entre
  IRPJ/CSLL/CBS/CPP/ICMS/IBS, **por faixa e por ano**, de 2027 até **pelo menos 2033**
  (`"Vigência: 1º/1/2033"`, tabela continua além do que esta sessão capturou). Exemplo (1ª
  faixa, 2027-2028): CBS=15,33%, ICMS=34,00%, IBS=0,17% da arrecadação do DAS daquela faixa;
  em 2029: CBS=15,50%, ICMS=30,60%, IBS=3,40% — a fatia do IBS cresce ano a ano (mesmo
  espírito de transição gradual do regime geral), **e esses percentuais já estão
  integralmente fixados por esta lei**, ano a ano, sem depender de nenhuma alíquota de
  referência pendente.
- **Anexo XXIII (MEI) tem estrutura diferente**: valores fixos em R$ (não percentuais), por
  ano, também com CBS/IBS discriminados (ex. 2027-2028: ICMS R$ 1,00, ISS R$ 5,00, CBS
  R$ 0,994, IBS R$ 0,006, total R$ 7,00; 2029: total R$ 6,60; 2030: R$ 6,20; 2031: R$ 5,80 —
  tendência de queda do valor total observado).
- **Achado central**: este dado **resolve, só para o Simples Nacional**, exatamente o tipo de
  informação que o "achado 12" do roadmap (linha do tempo da reforma 2029-2033) trata como
  bloqueada para o regime geral. Ou seja, para uma empresa optante pelo Simples Nacional, a
  fatia de CBS/IBS na partilha do DAS **já é conhecida** ano a ano até 2033 — só o regime
  geral (não-Simples) continua bloqueado pelo achado 12. Isso não desbloqueia o achado 12 (que
  continua sendo sobre a alíquota de referência do regime geral), mas é um dado real e
  independente, disponível hoje.
- **Nenhuma dependência técnica dos Anexos I-V/VII de redução (posições 12-14)**: a suposta
  relação "produção de efeitos futura" do brainstorm original não existe — os números do
  Simples Nacional não se derivam de nenhum daqueles Anexos.
- **`motor_calculo/regime_atual.py` não modela o Simples Nacional de nenhuma forma hoje** —
  só PIS/COFINS (regime não-cumulativo/cumulativo do lucro real/presumido) e ICMS
  interestadual/interno/ISS. Simples Nacional é um regime inteiro à parte, com sua própria
  lógica de faixas de receita bruta acumulada em 12 meses, alíquota efetiva (nominal menos
  dedução, dividido pela receita), e partilha entre tributos — não existe nenhum ponto de
  entrada no motor de cálculo para isso.
- **`ItemSimulacao`/`PayloadSimulacao` não têm nenhum campo para "regime Simples Nacional" ou
  "receita bruta acumulada em 12 meses"** — dados necessários para determinar a faixa
  aplicável.
- **Risco herdado**: LC 227/2026 nunca foi checada contra estes 6 Anexos, nem contra a LC
  123/2006 em si.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Regime inteiro, não um lookup por produto | Simples Nacional precisa de receita bruta acumulada em 12 meses, atividade (comércio/indústria/serviço), e a faixa correspondente | Escopo muito maior que qualquer outra feature desta leva — mais próximo em complexidade de ter sido `regime_atual.py` (PIS/COFINS) do que de qualquer Anexo de redução |
| 6 tabelas distintas (Comércio, Indústria, 3 tipos de serviço, MEI) | Cada uma com sua própria tabela de faixas e sua própria evolução de partilha ano a ano | `/design` precisa decidir se todas as 6 entram nesta única feature ou se há uma subdivisão interna (esta sessão não subdividiu, por decisão do usuário: "1 feature própria") |
| Dados já fixados até 2033 | Diferente do achado 12 (regime geral, bloqueado) | Esta feature pode entregar um cálculo real e completo para Simples Nacional 2027-2033, sem nenhuma restrição de "alíquota indisponível" — ao contrário de todas as outras features do motor de cálculo pós-2026 |
| Nenhum campo de payload existente | `PayloadSimulacao`/`ItemSimulacao` não capturam receita bruta, atividade ou opção pelo Simples | Mudança de contrato de API maior que qualquer uma das outras 5 features desta leva — precisa de campos novos no nível do payload (não por item) |
| Relevant KB Domains | python-developer, database-reviewer; nenhum domínio de KB específico para Simples Nacional | Feature mais nova e mais distante de qualquer precedente do projeto |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Híbrido: mecanismo + chave, isolando o que é regime diferente | Confirmou que XVIII-XXIII merecem tratamento à parte |
| 2 | Simples Nacional (XVIII-XXIII) vira 1 feature própria ou fica fora desta rodada de 6? | 1 feature própria, posição 6 desta leva, sem dependência técnica das outras 5 | Fechou o escopo: 1 feature cobrindo os 6 Anexos, não subdividida nesta sessão |
| 3 | Onde esta leva entra na sequência? | Depois das 9 posições já roteirizadas | Posição 17 (última da leva) |
| 4 | Os Anexos XVIII-XXIII são mesmo "produção de efeitos futura" dos Anexos I-V/VII de redução, como o brainstorm original assumiu? | **Não** — verificado nesta sessão: são os Anexos I-V e VII do Simples Nacional (LC 123/2006), um regime tributário à parte | Correção de escopo mais significativa desta leva; muda completamente o que esta feature precisa entregar |

**Minimum Questions:** 3 ✅ (4 registradas, incluindo a correção técnica central)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexos XVIII-XXIII) | `legis.senado.leg.br` | 6 anexos, cada um com 2 tabelas (faixas 2027-2028 + partilha ano a ano até ≥2033); Anexo XVIII (Comércio) transcrito com maior profundidade nesta sessão como amostra | Transcrição completa dos 6 (todas as faixas, todos os anos) é trabalho do `/define` — volume comparável ou maior que qualquer feature anterior do motor de cálculo |
| Fonte legal | Anexos XVIII-XXIII, LCP 214/2025, remetendo aos Anexos I-V/VII da LC 123/2006 | 6 anexos | Cada tabela (faixa × ano) é citável individualmente |
| Regime referenciado mas não modelado | LC 123/2006 (Simples Nacional) em si — arts. 18, §§ 5º-C e 5º-I | 0 (não ingerido/modelado hoje) | `/define` precisa decidir se a LC 123/2006 integral precisa ser ingerida no Qdrant (busca semântica) ou se só os Anexos XVIII-XXIII da LCP 214/2025 (já no corpus, ver `SHIPPED_2026-07-28.md` da posição 2) bastam para o cálculo determinístico |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design` |

**Como os dados serão usados (se aprovado no /define):** um novo ponto de entrada de cálculo
(análogo a `TabelaPisCofins`/`icms_interestadual` de `motor_calculo/regime_atual.py`, não ao
`engine.py` do IVA Dual) receberia receita bruta acumulada em 12 meses + atividade + ano, e
devolveria a partilha entre tributos, incluindo CBS/IBS — provavelmente um módulo novo
(`motor_calculo/simples_nacional.py` ou equivalente), não uma extensão de `reducoes.py`
(mecanismo totalmente diferente, não é uma redução sobre CBS/IBS calculado pelo `engine.py`).

---

## Approaches Explored

### Approach A: Módulo novo e isolado (`motor_calculo/simples_nacional.py`), consumido como opção alternativa ao `engine.py`, não como redução sobre ele ⭐ Recomendada

**What:** Simples Nacional não é uma redução aplicada ao resultado de `TaxCalculatorEngine`
— é um regime **substituto**. O módulo novo replicaria o padrão já usado em
`TabelaPisCofins`/`icms_interestadual` (tabela + função pura de busca), mas com uma dimensão a
mais (faixa de receita) e uma tabela de partilha por ano. `/v1/tax/simulate` ganharia um
campo de payload novo (ex. `regime_tributario: "simples_nacional"` + `receita_bruta_12_meses`
+ `atividade`), e quando presente, o cálculo desviaria para este módulo em vez do `engine.py`.

**Pros:**
- Reflete a realidade legal: Simples Nacional substitui, não reduz, os outros tributos
- Reaproveita o padrão arquitetural já validado em `regime_atual.py` (tabela + função pura,
  sem infraestrutura)
- Não força o Simples Nacional a caber no vocabulário de "redução sobre CBS/IBS" das outras 5
  features desta leva, que não se aplica aqui

**Cons:**
- Maior mudança de contrato de API de toda a leva (novos campos no payload, não só por item)
- Volume de dado a transcrever (6 tabelas × faixas × anos) é o maior de toda a leva

**Why Recommended:** É a única abordagem que respeita a natureza real do Simples Nacional
(regime substitutivo, não redução) em vez de tentar encaixá-lo no mesmo mecanismo das outras
5 features.

### Approach B: Tratar como mais um "Anexo de redução", reaproveitando `aplicar_reducao_percentual`

**What:** Forçar os percentuais de partilha do Simples Nacional a se comportarem como
"reduções" sobre o CBS/IBS calculado pelo `engine.py` do regime geral.

**Pros:**
- Reaproveitaria código das posições 12/13

**Cons:**
- Semanticamente errado: o Simples Nacional não calcula CBS/IBS a partir da alíquota do
  regime geral reduzida por um percentual — ele calcula a partir de uma **base de cálculo
  diferente** (receita bruta em faixas, DAS unificado). Aplicar o mecanismo de redução aqui
  produziria números sem nenhuma relação com o texto legal real
- Rejeitada por criar uma aparência de reaproveitamento que esconde um erro de cálculo

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — módulo novo e isolado, consumido como regime alternativo ao `engine.py`, não como redução |
| **User Confirmation** | Confirmado nesta sessão: feature própria, sem dependência técnica das outras 5 |
| **Reasoning** | Único approach que não distorce a natureza legal real do Simples Nacional para caber num mecanismo que não se aplica a ele |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo é os 6 Anexos (XVIII-XXIII), 1 feature só, sem subdivisão nesta sessão | Decisão explícita do usuário | Subdividir em Comércio/Indústria/Serviços/MEI — não descartado, mas adiado para o `/design`, se o volume de dado justificar |
| 2 | Correção de escopo: XVIII-XXIII são os Anexos I-V/VII do Simples Nacional (LC 123/2006), não "produção de efeitos futura" dos Anexos de redução | Verificado contra fonte primária nesta sessão — o brainstorm original de `REGRAS_TRIBUTARIAS_CACHE` estava incorreto neste ponto | Manter a descrição original — rejeitada, contradiz o texto oficial |
| 3 | Simples Nacional é um regime substitutivo, modelado como módulo novo, não como redução sobre `engine.py` | Natureza legal real (substitui, não reduz) | Approach B (reaproveitar `aplicar_reducao_percentual`) — rejeitada por produzir números sem base legal real |
| 4 | Sem dependência técnica das posições 12-16 desta leva | Confirmado pelo usuário e pela análise de conteúdo (nenhum Anexo de redução é citado nos Anexos XVIII-XXIII) | Assumir dependência de "produção de efeitos futura" como o brainstorm original propunha — corrigida |
| 5 | Verificar se a LC 227/2026 alterou algum dos 6 Anexos ou a própria LC 123/2006 | Mesma disciplina das outras features desta leva | Assumir que não — rejeitado |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Subdividir em várias features (Comércio, Indústria, Serviços I/II, MEI) | Usuário decidiu manter como 1 feature nesta rodada | Sim, se o `/design` encontrar volume/complexidade que justifique subdividir |
| Ingerir a LC 123/2006 completa no Qdrant nesta feature | O cálculo determinístico usa só os Anexos XVIII-XXIII da LCP 214/2025 (já no corpus); ingerir a LC 123/2006 inteira é uma decisão de busca semântica separada | Sim, como feature própria de ingestão, se o produto precisar de busca semântica sobre o Simples Nacional em si |
| Tentar usar este dado para desbloquear o achado 12 (regime geral) | Achado 12 é sobre a alíquota de referência do regime geral — o dado do Simples Nacional é independente e não a resolve | Não aplicável — são dados de regimes diferentes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Correção "não é produção de efeitos futura, é Simples Nacional" | ✅ | Reconhecida, sem objeção | Registrada como achado central da sessão |
| Simples Nacional como feature própria (não subdividida) | ✅ | Confirmado | Fechou o escopo |
| Sequência (posição 17, sem dependência das outras 5) | ✅ | Confirmado | Registrado no roadmap |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
A LCP 214/2025 (Anexos XVIII-XXIII) integra CBS e IBS à partilha do Simples Nacional
(LC 123/2006), com tabelas de faixa de receita e partilha percentual já fixadas ano a ano até
2033 — mas `motor_calculo/` não modela o Simples Nacional de nenhuma forma, e `/v1/tax/
simulate` não tem como identificar uma empresa optante desse regime.

### Success Criteria (Draft)
- [ ] Conteúdo completo dos 6 Anexos (todas as faixas, todos os anos, MEI) verificado contra
      fonte primária
- [ ] Módulo novo de cálculo do Simples Nacional (receita bruta 12 meses → faixa → alíquota
      efetiva → partilha entre tributos, incluindo CBS/IBS)
- [ ] Payload de `/v1/tax/simulate` ganha campos para sinalizar opção pelo Simples Nacional,
      receita bruta acumulada e atividade (comércio/indústria/serviço)
- [ ] Resultado cita o Anexo/tabela exata usada (por faixa e por ano)
- [ ] Confirmado se a LC 227/2026 alterou algum dos 6 Anexos ou a LC 123/2006
- [ ] `motor_calculo/` continua sem dependência de infraestrutura

### Constraints Identified
- Maior mudança de contrato de API de toda a leva — campos novos no nível do payload, não
  por item
- Não é redução sobre `engine.py` — é regime alternativo completo
- Sem dependência técnica das posições 12-16

### Out of Scope (Confirmed)
- Ingestão da LC 123/2006 completa no Qdrant (decisão separada)
- Desbloqueio do achado 12 (regime geral) — dados independentes
- Qualquer Anexo de redução de CBS/IBS por produto/serviço (posições 12-14), Anexo XVI, XVII
  (posições 15-16)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 (nível de leva + a correção técnica central) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 3 de 2 |
| Duration | Parte da sessão única desta leva; a mais extensa verificação de fonte primária das 6 (Anexo XVIII transcrito com profundidade, os outros 5 confirmados estruturalmente) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`

**Posição na sequência:** 17 de 17 (última desta leva) — depende de prioridade das posições
3-11 e das posições 12-16 conforme `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, mas **não** tem
nenhuma dependência técnica das posições 12-16 (poderia, em tese, ser adiantada se o usuário
decidisse reordenar dentro desta leva).
