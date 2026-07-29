# BRAINSTORM: Anexos IV, V, VI, VII, VIII e IX — Redução de 60% de CBS/IBS por NCM

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 13 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva").
> Diferente da posição 12 (redução a zero), esta feature introduz um mecanismo de cálculo
> **novo**: redução percentual (60%) sobre a alíquota de referência da fase, não "zera tudo".

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NCM |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 13 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** Dos 16 Anexos restantes da LCP 214/2025, o maior grupo aplica redução de 60%
(não zero) sobre as alíquotas de CBS/IBS. Esta feature cobre o subconjunto desse grupo cuja
chave de correspondência é predominantemente NCM/SH (bens), reaproveitando o vocabulário já
validado (`api/ncm.py`) mas exigindo uma função de cálculo nova.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/{id}` — IV=`40180906`, V=`40180912`,
  VI=`40180918`, VII=`40180967`, VIII=`40180973`, IX=`40180979`.
- **Anexo IV**: "DISPOSITIVOS MÉDICOS SUBMETIDOS À REDUÇÃO DE 60% (...)". NCM puro (ex. bolsa
  para drenagem, 3926.90.30). ~79 códigos observados (o maior dos 6 em volume).
- **Anexo V**: "DISPOSITIVOS DE ACESSIBILIDADE (...) REDUÇÃO DE 60%". NCM puro (ex. comando de
  embreagem manual para veículo adaptado, 8708.99.10). ~23 códigos.
- **Anexo VI**: "COMPOSIÇÕES PARA NUTRIÇÃO ENTERAL OU PARENTERAL (...) REDUÇÃO DE 60%". NCM
  puro (ex. acetato de dextroalfatocoferol, 2936.28.12). ~66 códigos.
- **Anexo VII**: "ALIMENTOS DESTINADOS AO CONSUMO HUMANO (...) REDUÇÃO DE 60%". NCM puro, com
  **exceções explícitas por subposição já no próprio texto** (ex. item 1: crustáceos/moluscos
  "exceto os produtos da subposição 0306.11 e dos códigos 0306.15.00, [...]") e **remissão
  cruzada ao Anexo I** (itens 4 e 5 citam "farinha [...]; ressalvados os produtos relacionados
  no Anexo I" — ou seja, um NCM pode aparecer no Anexo VII mas estar excluído dali
  especificamente porque já está no Anexo I com zero). ~51 códigos.
- **Anexo VIII**: "PRODUTOS DE HIGIENE PESSOAL E LIMPEZA (...) REDUÇÃO DE 60%". NCM puro (ex.
  sabão de toucador, 3401.11.90). ~9 códigos — o menor do grupo.
- **Anexo IX**: "INSUMOS AGROPECUÁRIOS E AQUÍCOLAS (...) REDUÇÃO DE 60%". Cabeçalho da tabela
  diz **"NBS / NCM/SH"** — é o Anexo **misto** que, por decisão do usuário, entra neste grupo
  porque a maioria dos itens observados é NCM (ex. biofertilizantes 3101.00.00, fertilizantes
  do Capítulo 31). ~94 códigos — o maior em volume observado dos 6.
- **Achado crítico de fonte primária**: o Anexo VII remete explicitamente ao Anexo I ("Anexo I
  já shipado tem prioridade sobre este Anexo para os mesmos NCMs") — isso não é um overlap
  acidental como o dos itens 4/26 do Anexo I; é uma regra de precedência **escrita na própria
  lei**. Qualquer resolução de conflito nesta feature precisa respeitar essa hierarquia
  legal (zero do Anexo I > 60% do Anexo VII), não só "o prefixo mais específico vence" (regra
  técnica do Anexo I, que resolvia conflito *dentro* de um mesmo Anexo, não *entre* Anexos com
  hierarquia normativa).
- **Mecanismo de cálculo não existe ainda**: `motor_calculo/reducoes.py` só tem
  `aplicar_reducao_a_zero`. Esta feature precisa de uma função nova (`aplicar_reducao_
  percentual` ou equivalente) que reduz CBS/IBS em 60% sobre o valor calculado pela fase, não
  zera. Isso é o núcleo técnico novo desta feature — o lookup por NCM em si (`api/ncm.py`,
  prefixo de dígitos) é 100% reaproveitável.
- **Risco herdado**: LC 227/2026 nunca foi checada contra nenhum destes 6 Anexos.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Cálculo novo | `aplicar_reducao_a_zero(resultado)` zera CBS/IBS incondicionalmente; a versão percentual precisa multiplicar por `(1 - 0.60)` mantendo o IS intocado, igual em espírito mas com um parâmetro a mais | `/design` decide se é uma função nova (`aplicar_reducao_percentual(resultado, percentual)`) ou uma generalização de `aplicar_reducao_a_zero` com `percentual=1.0` como caso especial — ambas resolvem, mas mudam a superfície de `motor_calculo/reducoes.py` |
| Hierarquia entre Anexos | Anexo VII cita "ressalvados os produtos relacionados no Anexo I" — precedência normativa explícita | O lookup precisa checar o Anexo I (zero) *antes* do Anexo VII (60%) para o mesmo NCM, não resolver por "mais específico" como dentro de um único Anexo |
| Anexo IX é misto | Cabeçalho "NBS / NCM/SH" — decisão do usuário: fica neste grupo (NCM dominante), itens de chave NBS ficam documentados como não resolvidos aqui | `/define` precisa identificar quais itens específicos do Anexo IX são NBS (prováveis: serviços agronômicos/veterinários, se existirem) e marcá-los explicitamente como fora de escopo desta feature, não como "não encontrado" silencioso |
| Volume | ~79 (IV) + ~94 (IX) são os maiores volumes de código observados em toda a leva — maior que os ~95 prefixos do Anexo I inteiro | `/design` deve estimar esforço de transcrição maior que o Anexo I, não assumir volume comparável |
| Relevant KB Domains | python-developer, database-reviewer | Reaproveita `api/ncm.py`; a função de redução percentual é o único código genuinamente novo |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Híbrido: mecanismo (zero vs. percentual) + chave (NCM vs. NBS) | Definiu esta feature como "percentual + NCM dominante" |
| 2 | Anexos mistos (IX, X, XI) — como tratar? | Dominante + pendência explícita | Anexo IX entra aqui; seus itens NBS ficam pendentes nesta feature |
| 3 | Onde esta leva entra na sequência? | Depois das 9 posições já roteirizadas | Posição 13 |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexos IV, V, VI, VII, VIII, IX) | `legis.senado.leg.br` | ~79+23+66+51+9+94 ≈ 322 códigos observados (aproximado) | Contagem aproximada desta sessão; transcrição item a item exata é trabalho do `/define`, mesma disciplina do Anexo I |
| Regra de precedência normativa | Anexo VII, itens 4 e 5 ("ressalvados os produtos relacionados no Anexo I") | ≥2 itens confirmados | Achado que muda o design: precedência entre Anexos, não só desempate por prefixo |
| Anexo misto | Anexo IX (cabeçalho "NBS / NCM/SH") | A quantificar no `/define` | Itens NBS ficam fora de escopo desta feature, documentados explicitamente |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design`, incluindo ao menos 1 caso de precedência Anexo I vs. VII |

**Como os dados serão usados (se aprovado no /define):** `/v1/tax/simulate` checaria, para
cada item de mercadoria: (1) está em algum Anexo zero (I/XII/XIII/XV)? se sim, zero, fim; (2)
senão, está em algum destes 6 Anexos de 60%? se sim, aplica a redução percentual, citando o
Anexo correto.

---

## Approaches Explored

### Approach A: Função de redução percentual nova, lookup em NCM reaproveitado, precedência explícita entre grupos de Anexos ⭐ Recomendada

**What:** `motor_calculo/reducoes.py` ganha `aplicar_reducao_percentual(resultado, percentual)`
como função pura irmã de `aplicar_reducao_a_zero`. O router de `/v1/tax/simulate` consulta
primeiro o(s) Anexo(s) zero (posição 12, já shipada quando esta feature rodar) e só then os
Anexos de 60% desta feature, respeitando a precedência normativa encontrada no Anexo VII.

**Pros:**
- Reaproveita 100% do vocabulário NCM já validado
- Precedência explícita entre grupos evita o erro de aplicar 60% a um item que a lei já zera
- Função nova é pequena e isolada, testável sem infraestrutura

**Cons:**
- Depende da posição 12 já estar shipada (ou pelo menos definida) para a precedência
  funcionar de verdade — esta feature não pode assumir que só ela existe
- Itens NBS do Anexo IX ficam explicitamente não resolvidos, exigindo comunicação clara ao
  usuário do simulador (mesmo padrão de "nunca zero/redução silenciosa" já estabelecido)

**Why Recommended:** É a única abordagem que respeita a hierarquia normativa real encontrada
no texto (Anexo VII citando o Anexo I) em vez de tratar os grupos como independentes.

### Approach B: Um percentual genérico configurável por Anexo, sem hierarquia entre grupos

**What:** Tratar cada Anexo de 60% de forma independente, sem checar cruzamento com os Anexos
zero — se um NCM está em mais de um Anexo, aplicar o que for encontrado primeiro na ordem de
consulta.

**Pros:**
- Mais simples de implementar

**Cons:**
- Ignora a precedência normativa explícita achada no Anexo VII — poderia aplicar 60% a um
  item que a lei já reduz a zero, dependendo da ordem arbitrária de consulta, um erro de
  cálculo real, não cosmético
- Rejeitada por violar a disciplina de "nunca aproximar/adivinhar" já estabelecida no projeto

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — função de redução percentual nova + precedência explícita entre Anexo(s) zero e Anexo(s) de 60% |
| **User Confirmation** | Decisão de agrupamento e tratamento de Anexos mistos confirmadas pelo usuário nesta sessão |
| **Reasoning** | Único approach que reflete a hierarquia normativa real (Anexo VII vs. Anexo I) em vez de tratá-la como coincidência |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo é IV, V, VI, VII, VIII e IX — os 6 Anexos de 60% com chave NCM dominante | Mesmo mecanismo de cálculo (percentual), mesma chave (NCM) | Incluir II, III, X, XI (chave NBS dominante) — vão para a posição 14 |
| 2 | Anexo IX entra aqui (NCM dominante); itens de chave NBS ficam pendentes, documentados explicitamente | Decisão do usuário sobre Anexos mistos | Excluir Anexo IX inteiro até um grupo "misto" existir — rejeitado, adiaria dado real sem necessidade |
| 3 | Precedência normativa entre Anexo I (zero) e Anexo VII (60%) deve ser resolvida explicitamente, não por ordem arbitrária de consulta | Achado de fonte primária: o próprio Anexo VII remete ao Anexo I | Tratar os grupos como independentes (Approach B) — rejeitada |
| 4 | Verificar se a LC 227/2026 alterou algum dos 6 Anexos | Investigação da LC 227/2026 não cobriu Anexos II-XXIII | Assumir que não foram tocados — rejeitado |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Resolver os itens NBS do Anexo IX nesta mesma feature | Exigiria a infraestrutura de lookup por NBS que só a posição 14 constrói | Sim — quando a posição 14 (`ANEXOS_REDUCAO_PERCENTUAL_NBS`) estiver pronta, ou como extensão futura desta feature |
| Generalizar `aplicar_reducao_a_zero` para aceitar qualquer percentual nesta feature, tocando a feature já shipada do Anexo I | Risco de regressão numa feature já verificada em produção | Sim, como refactor explícito e isolado, se o `/design` decidir que vale a pena |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Agrupamento híbrido | ✅ | Confirmado | Definiu esta feature como "percentual + NCM" |
| Anexos mistos (IX) | ✅ | Dominante + pendência explícita | Anexo IX incluído com ressalva |
| Sequência (posição 13) | ✅ | Depois das 9 restantes | Registrado no roadmap |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Seis Anexos da LCP 214/2025 (IV, V, VI, VII, VIII, IX) aplicam redução de 60% de CBS/IBS a
dispositivos médicos, acessibilidade, nutrição enteral/parenteral, alimentos, higiene/limpeza
e insumos agropecuários — mas `/v1/tax/simulate` não tem nenhum conceito de redução
percentual (só a redução a zero do Anexo I). Itens desses Anexos são simulados com a
alíquota cheia da fase, superestimando a carga tributária.

### Success Criteria (Draft)
- [ ] Conteúdo completo dos 6 Anexos verificado contra fonte primária
- [ ] `aplicar_reducao_percentual` (ou equivalente) implementada em `motor_calculo/reducoes.py`
- [ ] Precedência explícita entre Anexos zero e estes 6 Anexos de 60% (nunca aplicar 60% a um
      item já zerado por outro Anexo)
- [ ] Itens de chave NBS do Anexo IX documentados como não resolvidos nesta feature, nunca
      tratados como "NCM não encontrado" silencioso
- [ ] Confirmado se a LC 227/2026 alterou algum dos 6 Anexos
- [ ] `motor_calculo/` continua sem dependência de infraestrutura

### Constraints Identified
- Depende logicamente (não tecnicamente bloqueante, mas semanticamente) da posição 12 (Anexos
  zero) já estar definida, para a regra de precedência funcionar
- Sem RLS na(s) tabela(s) nova(s)

### Out of Scope (Confirmed)
- Anexos de chave NBS dominante (posição 14)
- Anexo XVI, XVII, Simples Nacional (posições 15-17)
- Itens NBS do próprio Anexo IX

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 (nível de leva) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 3 de 2 |
| Duration | Parte da sessão única desta leva, incluindo verificação real dos 6 Anexos contra `legis.senado.leg.br` |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NCM.md`

**Posição na sequência:** 13 de 17 — depende de prioridade das posições 3-11 e da posição 12
(Anexos zero) conforme `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.
