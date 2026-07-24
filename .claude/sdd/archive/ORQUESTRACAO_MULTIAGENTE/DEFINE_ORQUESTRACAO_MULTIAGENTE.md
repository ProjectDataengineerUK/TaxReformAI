# DEFINE: Orquestração Multi-Agente (LangGraph)

> Grafo LangGraph que conecta os 5 agentes especialistas do blueprint (Classificador, Pesquisador Legal, Extrator de Regras, Determinístico, Sintetizador) numa pipeline fixa e auditável, com LLMs simulados e integração real com o motor de cálculo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ORQUESTRACAO_MULTIAGENTE |
| **Date** | 2026-07-23 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O sistema precisa de um grafo de orquestração (LangGraph) que conecte os 5 agentes especialistas do blueprint numa pipeline fixa e auditável — hoje, `ingestion/` e `motor_calculo/` existem como componentes isolados, sem nada que os invoque em conjunto para responder a uma consulta de usuário.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Sistema TaxReform AI (consumidor interno futuro, ex: API `/v1/tax/simulate`) | Componente interno do sistema | Precisa de um ponto de entrada único que rode os 5 agentes em ordem e produza um resultado auditável — hoje não existe nenhum orquestrador |
| CFO / Head de Tax | Usuário final do produto (indireto) | Eventualmente vai consumir o parecer produzido pelo Sintetizador — a estrutura de dados já deve refletir o formato real, mesmo com o conteúdo ainda fake |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Grafo LangGraph com 5 nós (Classificador, Pesquisador Legal, Extrator de Regras, Determinístico, Sintetizador) executando em ordem fixa |
| **MUST** | Nó Classificador mascara CPF/CNPJ de verdade via regex — não fake; a classificação de intenção nesse mesmo nó continua fake |
| **MUST** | Nó Determinístico integra de verdade com `motor_calculo.engine.TaxCalculatorEngine` — não fake |
| **MUST** | Estado final do grafo contém histórico auditável de todas as transições (o que cada nó recebeu e retornou) |
| **SHOULD** | Pesquisador Legal, Extrator de Regras e Sintetizador com fakes que respeitam o schema real de dado esperado, não apenas retornam qualquer valor |
| **COULD** | Script de exemplo que roda uma consulta sintética ponta a ponta e imprime o estado final |

---

## Success Criteria

- [ ] Grafo executa os 5 nós em ordem para 1 consulta de teste sintética, sem exceções não tratadas
- [ ] CPF/CNPJ presentes no texto de entrada são mascarados no estado antes de chegar aos demais nós (verificável por teste automatizado com um CPF de exemplo)
- [ ] Resultado do nó Determinístico bate exatamente com uma chamada direta equivalente ao `TaxCalculatorEngine` (mesmo valor, mesma fonte legal)
- [ ] Estado final do grafo permite reconstruir, para auditoria, o que cada nó recebeu e retornou

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path | Uma consulta sintética de simulação tributária (ano 2026, `valor_base` conhecido) | O grafo é invocado | Os 5 nós executam em ordem e o estado final contém um `ResultadoCalculo` real do `motor_calculo` e um parecer fake do Sintetizador |
| AT-002 | Error case | Uma consulta cujo ano de operação não tem alíquota confirmada (ex: 2028) | O grafo chega ao nó Determinístico | O grafo propaga o `AliquotaNaoDisponivelError` de forma explícita, sem produzir um parecer com número inventado |
| AT-003 | Edge case | Uma consulta contendo um CPF/CNPJ no texto de entrada | O nó Classificador processa a consulta | O CPF/CNPJ é mascarado no estado antes de qualquer nó subsequente processar o texto |

---

## Out of Scope

- Chamadas reais a Claude/Vertex AI para qualquer nó — feature futura, quando houver credenciais configuradas
- Busca real no Qdrant — depende do `/ship` de `PIPELINE_INGESTAO_LEGAL` (credenciais GCP/Qdrant ainda pendentes)
- Retry/recuperação de erro dentro do grafo, streaming de resposta, checkpointing de estado entre sessões, human-in-the-loop
- Kafka ou qualquer fila assíncrona — não é o padrão de acesso desta feature (requisição-resposta, não pub/sub)
- Integração com uma API HTTP (`/v1/tax/simulate`) — o grafo fica invocável como função Python nesta feature, sem endpoint exposto

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Sem acesso a Claude/Vertex AI configurado para este projeto | Classificador (intent), Pesquisador Legal, Extrator de Regras e Sintetizador ficam fakes nesta feature |
| Technical | Sem Qdrant Cloud real disponível | Pesquisador Legal simula o formato de retorno (chunks), não busca de verdade |
| Scope | Motor Determinístico é a única integração real desta feature | Demais nós usam fakes que respeitam o schema real de dado, conforme o Goal SHOULD |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `orquestracao/` na raiz do repositório, paralelo a `ingestion/` e `motor_calculo/` | Terceiro componente independente do sistema |
| **KB Domains** | genai-architect (orquestração multi-agente, LangGraph), python-developer | Padrões a consultar na fase de Design |
| **IaC Impact** | Nenhum | Tudo roda com fakes nesta feature; `motor_calculo` já é Python puro sem infraestrutura |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O exemplo sintético de consulta (baseado na seção 8 do blueprint) é suficiente para validar a forma do grafo, mesmo sem dado real | Se a forma real de consulta divergir muito, o grafo pode precisar de ajustes quando a API real for construída | [ ] |
| A-002 | Não há necessidade de paralelismo entre nós nesta feature (pipeline é estritamente sequencial, conforme o diagrama do blueprint) | Se precisar paralelizar (ex: buscar em múltiplas fontes ao mesmo tempo), a estrutura do grafo precisaria mudar | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro e específico — falta de orquestrador conectando componentes já existentes |
| Users | 2 | Um consumidor interno (sistema) e um usuário final indireto (CFO) — ainda abstrato por não haver API/UI real ainda |
| Goals | 3 | MUST/SHOULD/COULD explícitos, herdados diretamente das decisões do brainstorm |
| Success | 3 | Critérios mensuráveis e testáveis, incluindo verificação de paridade com o motor real |
| Scope | 3 | Out of scope extremamente explícito, incluindo o que foi deliberadamente descartado (Kafka, API HTTP) |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma — pronto para Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-23 | define-agent | Versão inicial, extraída de BRAINSTORM_ORQUESTRACAO_MULTIAGENTE.md |
| 1.1 | 2026-07-23 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ORQUESTRACAO_MULTIAGENTE.md`
