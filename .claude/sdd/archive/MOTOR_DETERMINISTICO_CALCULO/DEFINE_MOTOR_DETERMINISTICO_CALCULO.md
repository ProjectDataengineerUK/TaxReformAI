# DEFINE: Motor Determinístico de Cálculo (IVA Dual / Split Payment)

> Motor Python puro que calcula CBS/IBS/IS e Split Payment por fase da transição tributária, aplicando apenas alíquotas rastreáveis a uma fonte legal real.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MOTOR_DETERMINISTICO_CALCULO |
| **Date** | 2026-07-22 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O produto precisa de um motor que calcule CBS/IBS/IS e Split Payment para qualquer ano da transição (2026-2033), aplicando sempre alíquotas rastreáveis a uma fonte legal real — nunca um número estimado ou inventado — mesmo que isso signifique recusar o cálculo quando a alíquota daquele ano ainda não estiver disponível.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Agente Determinístico (seção 3 do blueprint) | Componente interno do sistema multi-agente | Precisa executar o cálculo sem LLM, com zero alucinação numérica, mas hoje só existe um exemplo de código cobrindo a fase de 2028 |
| CFO / Head de Tax | Usuário final do produto | Precisa confiar que a simulação usa a alíquota realmente vigente para a data da operação, não uma estimativa de mercado |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Motor calcula CBS/IBS/IS/Split Payment corretamente para a fase de teste 2026 (única fase com alíquota 100% confirmada em lei) |
| **MUST** | `TabelaAliquotas` separada da matemática do cálculo, com cada entrada rastreável a uma fonte legal auditável |
| **MUST** | Motor recusa explicitamente o cálculo (erro claro) quando não há alíquota confirmada para o ano/fase solicitado — nunca usa estimativa como se fosse fato legal |
| **SHOULD** | Estrutura cobre todas as fases da linha do tempo (2026, 2027, 2029-2032, 2033), mesmo que só 2026 tenha dados reais nesta feature |
| **SHOULD** | Arredondamento com `Decimal`/`ROUND_HALF_UP`, conforme o padrão já usado no exemplo do blueprint (seção 6.1) |
| **COULD** | Interface CLI para rodar simulações manualmente, no mesmo espírito do `pipeline.py` da feature de ingestão |

---

## Success Criteria

- [ ] Motor calcula `valor_cbs`, `valor_ibs`, `valor_is` e valor líquido pós-Split Payment para uma operação de teste na fase 2026, batendo com a fórmula legal (CBS 0,9% + IBS 0,1% sobre a base)
- [ ] 100% das chamadas para anos/fases sem alíquota confirmada retornam erro explícito (não um número), verificável por teste automatizado
- [ ] Todos os valores monetários usam `Decimal`, nunca `float`

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path | Uma operação com `valor_base` conhecido na fase de teste 2026 | O motor calcula a transação | Retorna `valor_cbs = base × 0,009`, `valor_ibs = base × 0,001`, arredondados com `ROUND_HALF_UP`, e valor líquido com Split Payment subtraído |
| AT-002 | Error case | Uma operação com data em 2028 (fase sem alíquota confirmada na `TabelaAliquotas`) | O motor tenta calcular | Levanta um erro explícito informando que a alíquota não está disponível para aquele ano — nenhum valor numérico é retornado |
| AT-003 | Edge case | Split Payment desativado (`split_payment_active=False`) | O motor calcula a transação | O valor líquido retornado é igual ao `valor_base` (impostos calculados/reportados, mas não retidos) |

---

## Out of Scope

- Recalcular a metodologia de alíquota de referência do TCU (Média I = Média II, 16 módulos satélites) — permanentemente fora de escopo do produto, não só deste ciclo
- Popular a `TabelaAliquotas` para 2027-2033 — depende de uma feature futura de ingestão das Resoluções do Senado/TCU
- Transição gradual ICMS/ISS por UF/município (2029-2032) com dados reais — depende da fonte SPED/IBPT, feature futura de ingestão
- Integração com a API `/v1/tax/simulate` ou com o pipeline de ingestão legal — motor fica standalone nesta feature
- Frontend, billing, multi-tenancy

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Sem ground truth externo para validar os resultados numéricos | Testes validam a fórmula matemática do blueprint em si, não um "gabarito" de terceiros |
| Technical | Alíquotas de 2027+ não disponíveis nesta fase | `TabelaAliquotas` só populada com 2026; motor precisa lidar com dados incompletos sem quebrar de forma confusa |
| Scope | Motor não deve reimplementar a metodologia de cálculo da alíquota de referência do TCU | Fora de escopo permanente — evita scope creep para um trabalho de 78 páginas de regras federais |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `motor_calculo/` na raiz do repositório, paralelo a `ingestion/` | Componente independente, sem dependência do pipeline de ingestão |
| **KB Domains** | python-developer (Decimal, dataclasses), data-contracts-engineer (schema da `TabelaAliquotas`) | Padrões a consultar na fase de Design |
| **IaC Impact** | Nenhum | Motor é Python puro, sem infraestrutura externa (GCP/Qdrant) |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| TCU/Senado — Resoluções e Metodologia da Alíquota de Referência | PDF/Portal público (`sites.tcu.gov.br/reforma-tributaria`) | 1 valor confirmado (2026); demais fases pendentes | Sem SLA — atualização por evento (nova resolução publicada) | Fonte pública, sem dono interno |

### Schema Contract (`TabelaAliquotas`, uma entrada por fase/ano)
| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| ano_fase | str | NOT NULL | No |
| aliq_cbs | Decimal | NOT NULL | No |
| aliq_ibs | Decimal | NOT NULL | No |
| aliq_is | Decimal | NULL (nem toda operação tem Imposto Seletivo) | No |
| fonte_legal | str | NOT NULL — referência auditável (ex: "LC 214/2025, art. X" ou "Resolução Senado nº Y") | No |
| confirmado_em_lei | bool | NOT NULL | No |

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| `TabelaAliquotas` | Atualização manual por ciclo de feature (sem pipeline automatizado de Resoluções ainda) | Revisão manual a cada nova fonte confirmada |

### Completeness Metrics
- 100% das entradas da `TabelaAliquotas` devem ter `fonte_legal` preenchida — nenhuma alíquota "sem explicação"

### Lineage Requirements
- Toda alíquota usada num cálculo deve ser rastreável até seu `fonte_legal`

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A fase de teste 2026 (CBS 0,9%/IBS 0,1%) permanece válida durante o desenvolvimento desta feature | Se alterada por nova resolução, a `TabelaAliquotas` precisaria ser atualizada | [ ] |
| A-002 | Não há necessidade de simular anos além de 2033 nesta feature | Se precisar, a estrutura de fases precisaria ser estendida | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro e específico — cálculo correto + garantia de auditabilidade das alíquotas usadas |
| Users | 2 | Dois consumidores identificados, mas um é um componente interno do sistema, não uma persona humana observada diretamente |
| Goals | 3 | MUST/SHOULD/COULD explícitos, herdados diretamente das decisões do brainstorm |
| Success | 3 | Critérios mensuráveis e testáveis, incluindo o comportamento de erro explícito |
| Scope | 3 | Out of scope extremamente explícito, incluindo o que é permanentemente fora de escopo |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma — pronto para Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-22 | define-agent | Versão inicial, extraída de BRAINSTORM_MOTOR_DETERMINISTICO_CALCULO.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_MOTOR_DETERMINISTICO_CALCULO.md`
