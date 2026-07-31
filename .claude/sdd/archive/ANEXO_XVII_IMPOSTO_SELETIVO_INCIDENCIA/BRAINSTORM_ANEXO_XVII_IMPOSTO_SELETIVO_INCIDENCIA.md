# BRAINSTORM: Anexo XVII — Base de Incidência do Imposto Seletivo

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 16 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva").
> Diferente de todas as outras 5 features desta leva: o Anexo XVII não é sobre CBS/IBS — é
> sobre o **Imposto Seletivo (IS)**, um tributo diferente que `motor_calculo/tabela_
> aliquotas.py` já trata como "fixado por lei ordinária, variável por produto".

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 16 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** O brainstorm original de `REGRAS_TRIBUTARIAS_CACHE` já suspeitava que "o
Anexo XVII pode ser justamente essa lei [que fixa o IS por produto]" mas não verificou.
Esta sessão verificou o conteúdo real contra fonte primária.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/40181073`.
- Título real: **"BENS E SERVIÇOS SUJEITOS AO IMPOSTO SELETIVO"**.
- **Achado central**: o Anexo XVII lista **categorias** e seus códigos NCM (veículos,
  aeronaves/embarcações, produtos fumígenos, bebidas alcoólicas, bebidas açucaradas, bens
  minerais, "concursos de prognósticos e fantasy sport"), **sem nenhuma coluna de alíquota**.
  Ou seja: o Anexo XVII define **o que é a base de incidência** do IS (o "gatilho"), **não a
  alíquota** do IS. Isso confirma — em vez de contradizer — o que `motor_calculo/tabela_
  aliquotas.py` já registra: a alíquota do IS é fixada por lei ordinária, por produto, e
  continua pendente. O Anexo XVII não resolve essa pendência; ele só nomeia o universo de
  bens/serviços que, quando essa lei ordinária existir, será tributado.
- **Confirma "bens E serviços"**: a maioria das categorias é NCM puro (veículos: `87.03`,
  `8704.21` etc., excetuados caminhões e uso das Forças Armadas/Segurança Pública; aeronaves/
  embarcações: `8802`, exceto `8802.60.00`; fumígenos: `2401-2404`; bebidas alcoólicas:
  `2203-2208`; bebidas açucaradas: `2202.10.00`; bens minerais: `2601`, `2709.00.10`,
  `2711.11.00`, `2711.21.00`) — mas a última categoria observada, **"Concursos de
  prognósticos e Fantasy sport"**, é um serviço puro, **sem nenhum código NCM** — apostas/
  loterias/fantasy sport não têm classificação de mercadoria.
- **Exceções explícitas por uso**: várias categorias têm ressalva ("ressalvados os veículos
  com características técnicas específicas para uso operacional das Forças Armadas ou dos
  órgãos de Segurança Pública") — não é uma exceção por subposição NCM como no Anexo I, é uma
  exceção por **finalidade de uso**, que nenhum campo de `ItemSimulacao` capturaria hoje (não
  há como o payload informar "este veículo é para uso militar").
- **Risco herdado**: LC 227/2026 nunca foi checada contra o Anexo XVII.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Não resolve a alíquota do IS | Anexo XVII é só a base de incidência | `/define` deve deixar claro que esta feature **não** desbloqueia o cálculo do IS em si — só permite que `/v1/tax/simulate` **identifique** se um item está sujeito ao IS, mantendo a alíquota como `None`/indisponível, mesma disciplina do achado sobre 2027+ |
| Item sem código NCM | "Concursos de prognósticos e Fantasy sport" é um serviço sem classificação de mercadoria | `/define` precisa decidir como representar esse item — não é NCM nem NBS necessariamente (seria preciso confirmar se apostas/loterias têm código NBS próprio) |
| Exceção por finalidade de uso | Várias ressalvas dependem do uso do bem (militar/segurança pública), não do código em si | `ItemSimulacao` não tem hoje nenhum campo para capturar finalidade de uso — mesma classe de limitação que o projeto já reconhece para regras de exceção por mercadoria específica (cesta básica, combustíveis) |
| Relação com `motor_calculo/tabela_aliquotas.py` | Confirma, não contradiz, o texto atual: "IS fixado por lei ordinária, variável por produto" | Esta feature é sobre identificar a base de incidência, não sobre fixar valores — a recusa de calcular IS continua correta e deve continuar nomeando o dispositivo pendente |
| Relevant KB Domains | python-developer, database-reviewer | Reaproveita parcialmente `api/ncm.py` para os itens NCM; o item de serviço sem código exige tratamento à parte |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Híbrido: mecanismo + chave, isolando o que é tributo diferente | Confirmou que o Anexo XVII merece feature própria isolada |
| 2 | Onde esta leva entra na sequência? | Depois das 9 posições já roteirizadas | Posição 16 |
| 3 | O Anexo XVII fixa a alíquota do IS ou só a base de incidência? | Verificado nesta sessão: só a base de incidência, sem coluna de alíquota | Evita a expectativa equivocada de que esta feature "resolveria" o IS por completo |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexo XVII) | `legis.senado.leg.br` | ~7 categorias observadas (veículos, aeronaves/embarcações, fumígenos, bebidas alcoólicas, bebidas açucaradas, bens minerais, concursos de prognósticos), ~14 códigos NCM distintos | Lista completa e literal (incluindo todas as ressalvas) é trabalho do `/define` |
| Fonte legal | Anexo XVII, LCP 214/2025 | 1 anexo | Cada categoria é citável individualmente |
| Item sem código | "Concursos de prognósticos e Fantasy sport" | 1 | Precisa de tratamento especial — sem NCM nem confirmação de NBS nesta sessão |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design` |

**Como os dados serão usados (se aprovado no /define):** `/v1/tax/simulate` passaria a
identificar se um item de mercadoria/serviço está sujeito ao IS (informativo — "este item
está na base de incidência do IS, mas a alíquota permanece indisponível: [dispositivo]"),
sem alterar o valor calculado hoje (que já não inclui IS quando a alíquota não está fixada).

---

## Approaches Explored

### Approach A: Tabela de incidência (categoria + NCM/prefixo), sem tentar calcular valor de IS ⭐ Recomendada

**What:** Schema análogo ao das outras Anexos por NCM (prefixo de dígitos, `api/ncm.py`
reaproveitado), mas o resultado do lookup é só um sinalizador ("sujeito ao IS: sim/não, por
qual dispositivo") — nunca um valor monetário, já que a alíquota continua indisponível. O
item sem código (concursos de prognósticos) fica marcado como "não resolvido por NCM/NBS
nesta iteração", mesmo padrão de honestidade já usado para exceções não resolvidas.

**Pros:**
- Reaproveita a maior parte da infraestrutura de NCM já validada
- Não promete resolver o IS além do que a lei permite hoje — consistente com a disciplina do
  projeto
- Torna visível ao usuário do simulador que aquele item tem IS pendente, em vez de omitir

**Cons:**
- Exceções por finalidade de uso (militar/segurança pública) não são resolvidas — ficam como
  limitação estrutural declarada, análoga à já existente para IPI/ICMS por mercadoria
  específica
- O item de serviço sem código fica sem solução nesta feature

**Why Recommended:** Entrega valor real (visibilidade sobre a base de incidência do IS) sem
inflar o escopo para tentar resolver a alíquota, que depende de lei ordinária fora do
controle do projeto.

### Approach B: Não fazer nada até a alíquota do IS existir

**What:** Adiar completamente qualquer trabalho sobre o Anexo XVII até uma lei ordinária
fixar as alíquotas do IS por produto.

**Pros:**
- Evita construir infraestrutura para um cálculo que ainda não pode ser feito

**Cons:**
- Descarta o valor real de simplesmente **nomear** o que está sujeito ao IS, que é
  informação pública e citável hoje, independente da alíquota existir
- Contradiz o padrão do projeto de "nunca estimar, mas sempre nomear o que falta" (mesmo
  espírito de `AliquotaNaoDisponivelError`)

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — tabela de incidência, sinalizador informativo, alíquota permanece indisponível e nomeada |
| **User Confirmation** | Escopo/posicionamento confirmados nesta sessão |
| **Reasoning** | Entrega o valor real disponível (base de incidência) sem simular resolver o que só uma lei ordinária resolve |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo é só o Anexo XVII, feature isolada | Tributo diferente (IS, não CBS/IBS) | Agrupar com as features de CBS/IBS — rejeitado, mecanismo de cálculo e tributo são diferentes |
| 2 | Esta feature não fixa nem estima a alíquota do IS | Anexo XVII não tem coluna de alíquota — confirma que `motor_calculo/tabela_aliquotas.py` está certo em tratar isso como pendente | Estimar a alíquota do IS a partir de alguma fonte externa — rejeitado, seria uma invenção sem base legal |
| 3 | O item sem código ("concursos de prognósticos") fica marcado como não resolvido, não descartado silenciosamente | Mesma disciplina de honestidade sobre exceções não resolvidas já usada no Anexo I | Ignorar esse item — rejeitado |
| 4 | Verificar se a LC 227/2026 alterou o Anexo XVII | Mesma disciplina das outras features desta leva | Assumir que não — rejeitado |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Resolver exceções por finalidade de uso (uso militar/segurança pública) | `ItemSimulacao` não tem campo para capturar finalidade de uso hoje — mudança de contrato maior que o escopo desta feature | Sim, como extensão futura se o produto precisar |
| Calcular valor de IS | Depende de lei ordinária inexistente | Sim, automaticamente, quando a lei existir — sem precisar de nova feature além de plugar a alíquota na tabela já existente |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Isolamento do Anexo XVII como feature própria | ✅ | Confirmado | Mantido |
| Sequência (posição 16) | ✅ | Depois das 9 restantes | Registrado no roadmap |
| Confirmação de que XVII é só base de incidência | ✅ | N/A (achado técnico desta sessão) | Registrado como Key Decision 2 |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O Anexo XVII da LCP 214/2025 lista os bens e serviços sujeitos ao Imposto Seletivo, mas
`/v1/tax/simulate` não identifica hoje se um item está ou não nessa base de incidência — só
sabe que a alíquota do IS está indisponível de forma geral.

### Success Criteria (Draft)
- [ ] Conteúdo completo do Anexo XVII (todas as categorias, códigos e ressalvas) verificado
      contra fonte primária
- [ ] `/v1/tax/simulate` sinaliza se um item está na base de incidência do IS, citando a
      categoria e o dispositivo
- [ ] Alíquota do IS continua `None`/indisponível — esta feature não estima nem fixa valor
- [ ] Item sem código (concursos de prognósticos) documentado como não resolvido
- [ ] Exceções por finalidade de uso documentadas como limitação estrutural declarada
- [ ] Confirmado se a LC 227/2026 alterou o Anexo XVII

### Constraints Identified
- Não depende tecnicamente de nenhuma das outras 5 features desta leva
- Não deve introduzir nenhum valor monetário de IS sem base legal de alíquota

### Out of Scope (Confirmed)
- Cálculo de valor de IS (aguarda lei ordinária)
- Exceção por finalidade de uso
- Qualquer Anexo de CBS/IBS (posições 12-14), Anexo XVI, Simples Nacional (posições 15, 17)

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

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md`

**Posição na sequência:** 16 de 17 — depende de prioridade das posições 3-11 e das posições
12-15 conforme `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.
