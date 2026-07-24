# BRAINSTORM: Motor Determinístico de Cálculo (IVA Dual / Split Payment)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MOTOR_DETERMINISTICO_CALCULO |
| **Date** | 2026-07-22 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Depois de construir o pipeline de ingestão legal (feature anterior, `PIPELINE_INGESTAO_LEGAL`, build completo mas com execução real ainda bloqueada por credenciais GCP/Qdrant), o usuário pediu para seguir para o próximo componente do blueprint. Foi recomendado o motor determinístico de cálculo (seção 6 do `contexto.md`) por ser independente de infraestrutura externa (Qdrant/GCS) e testável imediatamente.

**Context Gathered:**
- `contexto.md` (seção 6.1) mostra um exemplo de código Python (`TaxCalculatorEngine.calculate_transaction_2028`) cobrindo apenas uma fórmula fixa para o regime pleno (CBS+IBS+IS com Split Payment), sem cobrir as fases de transição.
- A linha do tempo da reforma (seção 2) tem 4 fases distintas: 2026 (teste), 2027 (extinção PIS/COFINS, entrada do IS), 2029-2032 (transição gradual ICMS/ISS), 2033 (regime pleno).
- O pipeline de ingestão legal (feature anterior) só indexou 10 artigos de 1 lei (LC 214/2025) — não cobre as tabelas de alíquotas por NCM/UF/ano nem os 17 anexos da lei.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo diretório `motor_calculo/` na raiz, paralelo a `ingestion/` | Componente independente, sem dependência do pipeline de ingestão |
| Relevant KB Domains | python-developer (Decimal, dataclasses), data-contracts-engineer (schema de alíquotas) | Padrões a consultar no /design |
| IaC Impact | Nenhum — motor é Python puro, sem infraestrutura externa | Pode ser desenvolvido e testado sem GCP/Qdrant |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual fase da linha do tempo o motor deve cobrir no MVP (só a fórmula fixa de 2027+, todas as fases 2026-2033, ou um subconjunto)? | Todas as fases (2026 a 2033) | Motor precisa de uma abstração de regras por ano/fase, não uma fórmula única hardcoded |
| 2 | De onde vêm as alíquotas (`aliq_cbs`, `aliq_ibs`, `aliq_is`) — parâmetro de entrada livre, ou baseado na legislação? | Com base na legislação | Motor não pode aceitar alíquotas arbitrárias como "corretas" — precisa de uma fonte de dados rastreável e auditável, não just um parâmetro qualquer |
| 3 | Existe ground truth (caso de cálculo já validado por terceiros) para verificar o motor? | Não — sem verificação externa, apenas as fórmulas do blueprint | Aumenta a importância de tornar a fonte das alíquotas explicitamente auditável, já que não há como cross-checar o resultado final contra um caso conhecido |
| 4 | Vale a pena buscar as bases/fontes reais de alíquota antes de definir o escopo? | Sim | Motivou a pesquisa que revelou a real complexidade da "alíquota de referência" (ver Key Decisions) |

**Minimum Questions:** 3 ✅ (4 perguntas, incluindo validação incremental)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | 3 PDFs baixados do TCU (`resolucao-tcu-n389-de-24-junho-2026.pdf`, `Metodologia CBS Aliquota de Referencia e Redutor.pdf`, página `aliquotas-referencia.html`) | 3 | Ver Data Engineering Context |
| Ground truth | Nenhum caso de cálculo validado | 0 | Confirmado pelo usuário — motor não terá verificação externa nesta fase |
| Related code | `contexto.md` seção 6.1 (`TaxCalculatorEngine.calculate_transaction_2028`) | 1 | Único exemplo de código de cálculo disponível — cobre só uma fase |

**Como as fontes serão usadas:**

- A Resolução TCU nº 389/2026 e a Metodologia CBS foram lidas para entender **como** a alíquota de referência é calculada oficialmente — não para extrair um número a ser hardcoded
- A tabela "por setor" da página `aliquotas-referencia.html` foi **descartada como fonte confiável** (ver Key Decisions) — os números não batem com a metodologia real descrita no PDF oficial

---

## Approaches Explored

### Approach A: Fórmula única fixa (só o exemplo do blueprint, 2027+)

**Description:** Implementar exatamente `calculate_transaction_2028` como está na seção 6.1, sem cobrir as demais fases.

**Pros:**
- Mais rápido de entregar
- Zero ambiguidade — o código já existe no blueprint

**Cons:**
- Não atende ao requisito confirmado pelo usuário (todas as fases 2026-2033)
- Ignora completamente a fase de teste 2026, que é a única com alíquota realmente confirmada em lei

---

### Approach B: Motor com alíquotas hardcoded para todas as fases

**Description:** Implementar o motor para 2026-2033, mas com uma tabela de alíquotas fixas no código, usando as estimativas de mercado (~8,8-9,4% CBS, ~17-18,7% IBS) encontradas na pesquisa.

**Pros:**
- Cobre todas as fases pedidas
- Rápido — não exige uma abstração de fonte de dados

**Cons:**
- As alíquotas de 2027+ **não são fixadas em lei** — são calculadas anualmente por metodologia do TCU/Comitê Gestor do IBS e publicadas por Resolução do Senado. Hardcodar uma estimativa de imprensa como se fosse oficial quebra a garantia de auditabilidade que é a proposta de valor central do produto
- A tabela "por setor" encontrada numa página do TCU não bateu com a metodologia real (Média I = Média II, 16 módulos satélites) descrita no PDF oficial — não é uma fonte confiável para hardcode

---

### Approach C: Motor com fonte de alíquotas abstraída e auditável ⭐ Recomendada

**Description:** Separar a **matemática do cálculo** (Decimal, Split Payment, arredondamento, por fase) de uma abstração `TabelaAliquotas` — no mesmo espírito do `RawStorage`/`LegalSource` já criados na feature de ingestão. A tabela vem populada apenas com o que é **realmente confirmado em lei** (2026: CBS 0,9% + IBS 0,1%); para as demais fases, o motor falha explicitamente ("alíquota não disponível para o ano X — requer Resolução do Senado/TCU ainda não ingerida") em vez de calcular com um número não verificado.

**Pros:**
- Cobre a matemática de todas as fases (2026-2033) imediatamente, que é testável sem depender de nenhuma fonte externa
- Nunca apresenta um número não verificável como se fosse legalmente correto
- Mesmo padrão arquitetural já validado na feature anterior — reduz risco de design

**Cons:**
- Simulações de 2027 em diante ficam incompletas até a `TabelaAliquotas` ser alimentada de uma fonte real (Resolução do Senado, ou a metodologia do TCU aplicada)
- Exige uma segunda feature futura (extração das alíquotas oficiais) para o produto ficar realmente útil para 2027+

**Why Recommended:** É a única abordagem que não force a escolha entre "não cobre todas as fases" (rejeitando o requisito confirmado) ou "inventa alíquota" (quebrando a garantia de auditabilidade, que é a proposta de valor #1 do produto segundo a seção 1.1 do blueprint). Adia honestamente o que ainda não pode ser feito com confiança.

---

## Data Engineering Context

### Source Systems (atualização — nova fonte descoberta)

| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| TCU — Metodologia e Resoluções da Alíquota de Referência (`sites.tcu.gov.br/reforma-tributaria`) | Portal + PDFs técnicos (metodologia de 78 páginas, resoluções) | Dezenas de documentos técnicos e resoluções | Atualização por evento (nova resolução/homologação) |

**Nota:** esta fonte não estava nas 8 originais mapeadas no brainstorm de `PIPELINE_INGESTAO_LEGAL` — deve ser adicionada ao registro de fontes do produto. É a origem oficial da alíquota de referência de CBS/IBS, sem a qual o motor não pode calcular nada além da fase de teste 2026.

### Key Data Questions Explored

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | A alíquota de referência de CBS/IBS é um número simples fixado em lei? | Não — é resolvida por uma equação de equilíbrio (Média I = Média II) com 16 módulos satélites, usando dados reais de arrecadação 2012-2021 e PIB, homologada pelo TCU e publicada por Resolução do Senado | O motor de cálculo não deve tentar reimplementar essa metodologia — só aplicar o valor já homologado, quando disponível |
| 2 | A tabela "por setor" encontrada numa página do TCU é confiável? | Não verificável — não bate com a metodologia real descrita no PDF oficial (que não é uma tabela setorial simples) | Não deve ser usada como fonte de dados no motor |
| 3 | Que alíquota é 100% confirmada em lei, sem depender de resolução futura? | Apenas a fase de teste 2026 (CBS 0,9% + IBS 0,1%) — confirmada por múltiplas fontes independentes | É o único valor que a `TabelaAliquotas` pode conter com confiança nesta fase |

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach C — Motor com fonte de alíquotas abstraída e auditável |
| **User Confirmation** | 2026-07-22 |
| **Reasoning** | Única abordagem que cobre todas as fases pedidas sem comprometer a garantia de auditabilidade do produto |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Separar matemática (`motor_calculo`) de fonte de alíquotas (`TabelaAliquotas`) | Alíquotas de 2027+ não são fixas em lei — são recalculadas anualmente por metodologia oficial (TCU/Senado); hardcodar seria inventar dado legal | Approach B (hardcode de estimativas de mercado) — rejeitada por quebrar auditabilidade |
| 2 | `TabelaAliquotas` só populada com 2026 (0,9%/0,1%) nesta feature; demais fases falham explicitamente | É o único número confirmado em múltiplas fontes independentes como fixado em lei, não sujeito a resolução futura | Usar a tabela setorial da página do TCU — rejeitada, não bate com a metodologia oficial descrita no PDF, não é confiável |
| 3 | Motor não reimplementa a metodologia de cálculo da alíquota de referência do TCU (Média I = Média II, 16 módulos satélites) | Isso é trabalho do TCU/RFB, não do produto — o TaxReform AI deve *aplicar* a alíquota homologada, não recalculá-la do zero | Replicar a metodologia completa — descartada por escopo (78 páginas de regras, dados de arrecadação federal não públicos em granularidade suficiente) |
| 4 | TCU adicionado como nova fonte de dados do produto | Não estava mapeado nas 8 fontes originais, mas é a origem oficial da alíquota de referência | — |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Recalcular a metodologia de alíquota de referência do TCU (Média I = Média II) | Fora do escopo do produto — é o cálculo que o TCU/RFB fazem, não algo que o TaxReform AI deveria reproduzir | Não — o produto deve sempre consumir o valor já homologado, nunca recalculá-lo |
| Popular `TabelaAliquotas` com estimativas de mercado para 2027+ | Quebraria a garantia de auditabilidade — estimativa de imprensa não é fonte legal verificável | Sim — quando a Resolução do Senado para 2027 for publicada e ingerida |
| Cobertura completa de ICMS/ISS por UF/município para a transição 2029-2032 | Exige uma base de dados massiva (26 estados + DF + 5.000+ municípios) — corresponde à fonte SPED/IBPT já mapeada, é trabalho de ingestão, não deste motor | Sim — como extensão futura do pipeline de ingestão |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Necessidade de dados reais do TCU para simular de verdade | ✅ | Usuário confirmou ("para simular seria importante dados do tcu certo?") | Motivou a pesquisa que gerou a Key Decision 1-4 |
| Síntese final (escopo Approach C + ressalva sobre tabela setorial não confiável + TCU como nova fonte) | ✅ | Usuário confirmou ("sim") | Nenhum — aprovado como apresentado |

**Minimum Validations:** 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O produto precisa de um motor que calcule CBS/IBS/IS e Split Payment para qualquer ano da transição (2026-2033), aplicando sempre alíquotas rastreáveis a uma fonte legal real — nunca um número estimado ou inventado — mesmo que isso signifique recusar o cálculo quando a alíquota daquele ano ainda não estiver disponível.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Agente Determinístico (motor, seção 3 do blueprint) | Precisa executar o cálculo sem LLM, com zero alucinação numérica, mas hoje não tem nenhuma implementação além do exemplo de 2028 |
| CFO / Head de Tax (usuário final, via produto) | Precisa confiar que a simulação usa a alíquota realmente vigente para a data da operação, não uma estimativa |

### Success Criteria (Draft)
- [ ] Motor calcula corretamente CBS+IBS+IS+Split Payment para a fase de teste 2026 (único ano com alíquota 100% confirmada em lei)
- [ ] Motor recusa explicitamente (erro claro, não um número inventado) o cálculo para anos sem alíquota confirmada na `TabelaAliquotas`
- [ ] Arredondamento segue `ROUND_HALF_UP` com `Decimal`, conforme o exemplo do blueprint (seção 6.1)

### Constraints Identified
- Sem ground truth externo para validar os resultados numéricos
- Alíquotas de 2027+ não estão disponíveis nesta fase — dependem de uma feature futura de ingestão das Resoluções do Senado/TCU
- Motor não deve reimplementar a metodologia de cálculo da alíquota de referência (fora de escopo permanente, não só deste ciclo)

### Out of Scope (Confirmed)
- Recalcular a alíquota de referência (metodologia TCU) — permanentemente fora de escopo do produto
- Popular `TabelaAliquotas` para 2027-2033 nesta feature — requer ingestão de Resoluções do Senado (feature futura)
- Transição gradual ICMS/ISS por UF/município (2029-2032) — requer base SPED/IBPT (feature futura de ingestão)
- Integração com a API `/v1/tax/simulate` ou com o pipeline de ingestão legal — motor fica standalone nesta feature

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | 1 sessão de diálogo, incluindo pesquisa em fontes reais (TCU) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_MOTOR_DETERMINISTICO_CALCULO.md`
