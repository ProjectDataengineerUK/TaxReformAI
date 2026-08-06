# DEFINE: COMPARATIVO_REGIME_ATUAL_IVA_DUAL

> Expor, no `/simulador` e no `/consulta`, a comparação regime atual x IVA Dual que a API já calcula mas nenhuma tela mostra.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMPARATIVO_REGIME_ATUAL_IVA_DUAL |
| **Date** | 2026-08-06 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## Problem Statement

`/v1/tax/simulate` já calcula e devolve, em `regime_vigente`/`itens_regime_vigente`, uma comparação completa entre o regime tributário atual (PIS/COFINS, ICMS, ISS, IPI) e o IVA Dual (CBS/IBS/IS) — mas o `/simulador` descarta esse dado silenciosamente (o tipo `RespostaSimulacao` do frontend nem declara os campos), e o `/consulta` conversacional nem chega a calcular o lado do regime atual, porque seu payload (`valor_base` agregado) não carrega UF/natureza/NCM por item. Controllers e CFOs usando a plataforma não têm hoje nenhuma visão "antes x depois" real da transição tributária.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Controller/CFO | Usuário do `/simulador` estruturado | Vê só o valor final do IVA Dual, sem referência de quanto pagaria hoje — perde o argumento de negócio central da transição |
| Consultor tributário | Usuário do `/consulta` conversacional | Recebe um parecer em texto sem nenhuma comparação estruturada; o backend desse fluxo nem calcula o regime atual hoje |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `/simulador` exibe tabela comparativa regime atual x IVA Dual (agregada + por item), citando a fonte legal de cada tributo |
| **MUST** | Tributos não calculados (falta de `regime_apuracao`/`natureza=SERVICO`) aparecem declarados como "não calculado" — nunca omitidos nem estimados |
| **MUST** | Lógica de cálculo de `api/routers/simulate.py::simular()` extraída para função compartilhada, sem duplicação, sem regressão no comportamento atual |
| **MUST** | `/consulta` aceita `itens: list[ItemSimulacao]`, calcula os dois lados (regime atual + IVA Dual) com a MESMA precisão do `/simulador` (Anexos de redução, IPI por item), e exibe a mesma tabela comparativa |
| **SHOULD** | `valor_base` de `PayloadConsulta` passa a ser derivado da soma dos itens, não mais campo manual |
| **SHOULD** | Formulários de `/simulador` e `/consulta` ganham seletor de `natureza` (por item) e `regime_apuracao` (por operação) |
| **COULD** | Mensagem de ajuda/tooltip explicando por que um tributo aparece como "não calculado" |

---

## Success Criteria

- [ ] `RespostaSimulacao` (frontend) declara `regime_vigente`/`itens_regime_vigente`, espelhando `api/schemas_simulate.py` campo a campo
- [ ] `ResultadoSimulacao.tsx` renderiza a tabela comparativa sem quebrar a renderização hoje existente (`resumo_financeiro`/`itens_detalhados`)
- [ ] `PayloadConsulta` aceita `itens` (mesmo shape de `ItemSimulacao`) e `ano_operacao`; `valor_base` deixa de existir como campo de entrada
- [ ] `RespostaConsulta` ganha os mesmos campos de comparação que `RespostaSimulacao` (itemizados, com fonte legal)
- [ ] `orquestracao/nos/deterministico.py` produz resultado idêntico ao que `api/routers/simulate.py` produziria para os mesmos itens (paridade verificada por teste automatizado comparando as duas saídas)
- [ ] Zero regressão nos ~640 testes de backend e 34 testes de frontend já existentes
- [ ] `ruff check .` limpo após a extração da função compartilhada

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Comparação aparece no `/simulador` (happy path) | Usuário logado, item MERCADORIA com NCM válido, `uf_origem="SP"`, `uf_destino="RJ"`, `ano_operacao=2026` | Envia a simulação | Tela mostra tabela com ICMS interestadual real (regime atual) ao lado de CBS/IBS/IS (IVA Dual), cada um citando o artigo/lei de origem |
| AT-002 | Tributo não calculado é declarado, nunca omitido | Item sem `regime_apuracao` informado no payload | Simulação roda | Linha de PIS/COFINS na tabela mostra "não calculado" com o motivo (`regime_apuracao` ausente), nunca um valor zerado ou omitido |
| AT-003 | `/consulta` itemizado calcula com paridade total | Payload `/v1/tax/query` com `itens` (mesmo NCM/UF do AT-001), sem mais `valor_base` manual | Consulta processada pela orquestração | `resultado_calculo`/`regime_vigente` da resposta são numericamente IDÊNTICOS ao que `/v1/tax/simulate` devolveria para os mesmos itens |
| AT-004 | `valor_base` derivado corretamente | 3 itens com `quantidade`/`valor_unitario` diferentes | Payload enviado ao `/consulta` | `valor_base` interno usado pelo motor de cálculo é exatamente a soma de `quantidade × valor_unitario` de todos os itens |
| AT-005 | Sem regressão em `ano_operacao >= 2027` | Payload com `ano_operacao=2027` em `/simulador` OU `/consulta` | Simulação/consulta enviada | Resposta continua 422 (`AliquotaNaoDisponivelError`), comportamento idêntico ao pré-feature |
| AT-006 | Item de serviço aciona ISS, não ICMS | Item com `natureza="SERVICO"` | Simulação processada | Tabela mostra faixa de ISS (piso/teto) no lado regime atual, nunca ICMS para esse item |
| AT-007 | Extração da função compartilhada não muda resposta do `/simulador` | Qualquer payload válido já coberto pelos testes existentes de `/v1/tax/simulate` | Suíte de testes de `test_api_simulate.py` (ou equivalente) roda após a refatoração | Todas as asserções existentes continuam passando byte a byte — mesma resposta antes e depois da extração |
| AT-008 | Comprador com condição especial (Anexos IV/V/VI) funciona igual nos dois endpoints | Item cujo Anexo vencedor tem condição de comprador, `comprador_tipo="ORGAO_PUBLICO"` enviado tanto em `/simulador` quanto em `/consulta` | Ambos processados | Os dois devolvem a MESMA alíquota reduzida (zero) e a MESMA dupla citação de dispositivo legal |

---

## Out of Scope

- Gráficos ou visualização não-tabular da comparação
- Exportação da comparação (PDF/CSV)
- Comparação histórica multi-ano (2026-2033) na mesma tela — a API já recusa `ano_operacao >= 2027` com 422
- Incluir Simples Nacional na mesma tabela comparativa (`POST /v1/tax/simulate-simples-nacional` continua endpoint/schema independente)
- Mudança de contrato de `/v1/tax/simulate` (já correto) — só consumo no frontend e reaproveitamento de lógica
- Extração de UF/NCM/natureza do texto livre via LLM no `/consulta` — sempre campo explícito
- Ingestão de nova legislação — a pergunta original do usuário já foi respondida: `motor_calculo/regime_atual.py` já cita artigo real de cada alíquota, não há gap de ingestão

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Sem mudança de schema de banco — feature 100% aplicação (Pydantic + React + função Python) | Nenhuma migração, nenhum `migrar_banco.yml` novo |
| Technical | `AliquotaNaoDisponivelError` continua interrompendo o fluxo (422/503) para `ano_operacao >= 2027` | Comparação só tem dado real para 2026 nesta feature |
| Technical | UF/natureza/NCM no `/consulta` são sempre campos explícitos — LLM nunca infere esses valores | `extrator_regras.py` mantém a mesma disciplina já usada para `valor_base`/`ano_operacao` |
| Technical | `regime_apuracao`/`natureza` continuam opcionais/com default — mudança aditiva | Nenhum payload existente pode quebrar (mesma disciplina de todo campo novo já visto no projeto) |
| Technical | `PayloadConsulta` perde o campo `valor_base` como entrada — mudança BREAKING para quem já chama `/v1/tax/query` com `valor_base` | Precisa ser documentado explicitamente; sem cliente externo conhecido além do próprio frontend do projeto |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `api/schemas_simulate.py`, `api/schemas_query.py`, `api/simulacao.py` (novo), `api/routers/simulate.py`, `api/routers/query.py`, `orquestracao/estado.py`, `orquestracao/nos/deterministico.py`, `orquestracao/executor.py`, `frontend/lib/types.ts`, `frontend/components/ResultadoSimulacao.tsx`, `frontend/components/SimuladorForm.tsx`, `frontend/app/consulta/` | Toca as duas pontas (backend + frontend) e o núcleo da orquestração |
| **KB Domains** | N/A — projeto sem KBs configurados | — |
| **IaC Impact** | Nenhum | Sem Terraform, sem workflow novo, sem migração |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Nenhum cliente externo real depende de `PayloadConsulta.valor_base` como está hoje (só o próprio frontend do projeto chama `/v1/tax/query`) | Mudança breaking quebraria integração externa não documentada | [ ] |
| A-002 | A extração de `simular()` para função pura é mecanicamente segura (mesma lógica, só movida de lugar) — sem efeito colateral escondido em variáveis de estado do request/response FastAPI | Refatoração poderia introduzir bug sutil de comportamento | [ ] |
| A-003 | `orquestracao/estado.py::State` pode crescer para carregar `itens`/`regime_apuracao`/`comprador_tipo` sem quebrar os nós existentes (`classificador`, `pesquisador_legal`, `extrator_regras`, `sintetizador`) que não usam esses campos | Nós existentes poderiam falhar com state mais rico | [ ] |
| A-004 | O guardrail do `sintetizador` (que rejeita parecer sem reproduzir TODOS os valores calculados) consegue lidar com um `resultado_calculo` agora itemizado, não mais um valor agregado único | Guardrail poderia rejeitar todo parecer real após a mudança, quebrando `/consulta` por completo | [ ] |

**Note:** A-004 é a mais arriscada — precisa ser validada explicitamente no `/design`, já que `sintetizador.py` tem um guardrail rígido documentado (`LLM_REAL_VERTEX_AI`) que já causou um incidente real de rejeição em produção (`project_sintetizador_guardrail_reprovando_llm_direto.md`).

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Gap concreto e verificado no código (campos existem no backend, ausentes no frontend/consulta) |
| Users | 3 | Dois personas claras, com dor específica e diferenciada |
| Goals | 3 | MUST/SHOULD/COULD explícitos, todos rastreáveis ao brainstorm |
| Success | 3 | Critérios testáveis, com referência a arquivos/campos reais |
| Scope | 3 | Out of Scope extenso e específico, todo item com razão documentada |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15**

---

## Open Questions

Nenhuma pendente para o `/design` — mas a Assumption A-004 (guardrail do sintetizador com resultado itemizado) deve ser a PRIMEIRA coisa investigada no `/design`, antes de desenhar o resto, porque pode mudar a forma da resposta do `/consulta`.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-06 | define-agent | Versão inicial, extraída do BRAINSTORM já validado (8 perguntas, 8 validações) |
| 1.1 | 2026-08-06 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md`
