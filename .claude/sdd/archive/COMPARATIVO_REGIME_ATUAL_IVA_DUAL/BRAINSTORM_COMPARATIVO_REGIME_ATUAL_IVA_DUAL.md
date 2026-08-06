# BRAINSTORM: COMPARATIVO_REGIME_ATUAL_IVA_DUAL

> Sessão exploratória para esclarecer intenção e abordagem antes da captura de requisitos

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMPARATIVO_REGIME_ATUAL_IVA_DUAL |
| **Date** | 2026-08-06 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** "outra pergunta . foi ingerido a legislacao atual e nao tem nenhuma tewla trazendo a comparacao" — usuário perguntou se a legislação do regime atual foi ingerida e notou que não existe nenhuma tabela comparando regime atual x IVA Dual na interface.

**Context Gathered:**
- `api/schemas_simulate.py:401` (`RegimeVigenteResumo`) e `:357` (`ItemRegimeVigente`) já existem e são preenchidos por `/v1/tax/simulate` desde `SCHEMA_POSTGRESQL`/`IPI_TIPI_MOTOR_CALCULO` — PIS/COFINS, ICMS interestadual, ICMS interno+FECP, faixa de ISS, IPI, cada um citando a fonte legal.
- `frontend/lib/types.ts` (`RespostaSimulacao`) nunca declarou esses campos — o dado chega na resposta HTTP e é descartado sem nunca aparecer na tela.
- `frontend/components/ResultadoSimulacao.tsx` renderiza só `resumo_financeiro` (CBS/IBS/IS/líquido, lado IVA Dual) e `itens_detalhados` — nada do regime atual.
- `frontend/components/SimuladorForm.tsx` já envia `uf_origem`/`uf_destino` por item (então ICMS já calcularia hoje) mas NUNCA envia `regime_apuracao` nem `natureza="SERVICO"` — PIS/COFINS e ISS sempre voltariam "não calculado" mesmo depois da feature, a menos que o formulário também ganhe esses campos.
- `/v1/tax/query` (`api/schemas_query.py::PayloadConsulta`) tem um shape totalmente diferente — `texto_consulta` + `ano_operacao` + `valor_base` (agregado, não itemizado) — sem nenhum campo estruturado equivalente a `regime_vigente`.
- `orquestracao/nos/deterministico.py` hoje só chama `TaxCalculatorEngine.calcular()` (lado IVA Dual, agregado) — nunca toca `motor_calculo/regime_atual.py` nem os Anexos de redução/IPI que `api/routers/simulate.py::simular()` aplica por item.
- `api/routers/simulate.py::simular()` tem ~700 linhas de lógica de cálculo (Anexos de redução, IPI, regime atual por item) inline dentro do handler do endpoint — não fatorada em função reaproveitável.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Likely Location | `frontend/lib/types.ts`, `frontend/components/`, `api/schemas_simulate.py`, `api/schemas_query.py`, `api/routers/simulate.py`, `api/routers/query.py`, `orquestracao/` | Toca as duas pontas (frontend + backend) e o núcleo da orquestração |
| Relevant KB Domains | N/A (projeto sem KBs configurados) | — |
| IaC Patterns | Nenhum — feature 100% aplicação (schemas Pydantic, componentes React, função Python) | Sem migração de banco, sem Terraform, sem workflow novo |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Escopo: só `/simulador` ou também `/consulta`? | `/simulador` + `/consulta` | Amplia o escopo para incluir redesenho do payload conversacional |
| 2 | Dado que `/consulta` exigiria payload itemizado, reduzir escopo ou seguir com os dois? | Seguir com os dois nesta feature | Confirma escopo maior, apesar do custo |
| 3 | Como o usuário informa UF/natureza/NCM no `/consulta` itemizado? | Campos explícitos novos (não extração por LLM) | Preserva a disciplina "nunca inventar dado exato" já usada em `valor_base`/`ano_operacao` |
| 4 | `PayloadConsulta` ganha um item só ou lista, como `/simulador`? | Lista de itens, como `/simulador` | `PayloadConsulta` converge estruturalmente para o mesmo shape de item de `PayloadSimulacao` |
| 5 | O que fazer com `valor_base` agora que `itens` existe? | Derivar da soma dos itens (calculado, não mais campo manual) | Remove risco de divergência entre valor manual e soma dos itens — mesma disciplina de `valor_bruto_total` do `/simulador` |
| 6 | O lado IVA Dual do `/consulta` também vira itemizado (paridade com `/simulador`) ou continua agregado? | Itemizado, paridade total | Exige reaproveitar a MESMA lógica de cálculo do `/simulador` (Anexos de redução, IPI por item) dentro da orquestração — maior peça de trabalho da feature |
| 7 | Formulários ganham campos de `natureza`/`regime_apuracao` para PIS/COFINS e ISS aparecerem de verdade? | Sim, adicionar os dois campos | Sem isso a tabela fica incompleta por padrão em todo simulador — ISS e PIS/COFINS sempre "não calculado" |
| 8 | Arquitetura de reaproveitamento: extrair função compartilhada vs. chamada HTTP interna | Extrair função compartilhada, chamada direta | Sem salto de rede — orquestração e router do `/simulador` já rodam no mesmo processo |

**Minimum Questions:** 3 — 8 perguntas feitas, todas com decisão explícita do usuário.

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | N/A | 0 | — |
| Output examples | `api/schemas_simulate.py:357-419` (schemas Pydantic reais, já em produção) | 2 classes | `RegimeVigenteResumo`/`ItemRegimeVigente` são a fonte de verdade do formato dos dados |
| Ground truth | N/A | 0 | — |
| Related code | `api/routers/simulate.py::simular()` (~700 linhas, lógica de cálculo completa) | 1 | Base para a extração da função compartilhada |

**How samples will be used:**

- `RegimeVigenteResumo`/`ItemRegimeVigente` definem exatamente quais campos a tabela comparativa precisa renderizar (nenhum campo novo inventado no frontend).
- A extração de `simular()` reaproveita a lógica JÁ VERIFICADA em produção (Anexos de redução, IPI, regime atual) — o `/define`/`/design` devem tratar isso como refatoração de comportamento existente, não como reescrita.

---

## Approaches Explored

### Approach A: Função compartilhada, chamada direta (sem HTTP interno) ⭐ Recomendado

**Description:** Extrair a lógica de `api/routers/simulate.py::simular()` para uma função pura (ex: `api/simulacao.py::calcular_simulacao_completa()`), que recebe `itens`/`ano_operacao`/`regime_apuracao`/`comprador_tipo` e devolve `(itens_detalhados, resumo_financeiro, regime_vigente, itens_regime_vigente)`. O router do `/simulador` vira uma casca fina (validar → chamar → audit log → responder); o nó `deterministico` da orquestração do `/consulta` chama a MESMA função, dentro do mesmo processo.

**Pros:**
- Reaproveita lógica já verificada em produção (Anexos, IPI, regime atual) sem duplicar
- Sem latência de rede extra — chamada de função Python, não HTTP
- Um só lugar para corrigir bugs de cálculo no futuro

**Cons:**
- Refatoração real de ~700 linhas de um endpoint que já está em produção — precisa de testes de não-regressão fortes
- `orquestracao/estado.py` (`State`) precisa crescer para carregar `itens`/`regime_apuracao`/`comprador_tipo`, não só `valor_base`

**Why Recommended:** Mesmo padrão já estabelecido no projeto (`db/repositorio.py` reaproveitado por API e scripts) — extrair função pura em vez de duplicar lógica ou adicionar uma chamada de rede desnecessária.

---

### Approach B: Chamada HTTP interna (nó da orquestração chama `/v1/tax/simulate`)

**Description:** O nó `deterministico` do `/consulta` faria uma requisição HTTP para o próprio `/v1/tax/simulate`, como o endpoint interno protegido por OIDC já usado em `FILA_ASSINCRONA_CELERY_REDIS` para Cloud Tasks.

**Pros:**
- Zero duplicação de código Python — reusa o endpoint como está, sem tocar `api/routers/simulate.py`

**Cons:**
- Adiciona latência e um modo de falha novo (timeout, erro de rede) para algo que já roda no mesmo processo
- O padrão de endpoint interno + OIDC existe porque Cloud Tasks é um contexto de execução GENUINAMENTE separado (worker assíncrono) — aqui não há essa separação, então o mecanismo seria desproporcional ao problema

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-08-06 |
| **Reasoning** | Reaproveitamento direto, sem rede — a orquestração e o router do `/simulador` já rodam no mesmo processo da API |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo cobre `/simulador` E `/consulta` | Usuário confirmou explicitamente após ver o custo real de ampliar `/consulta` | Restringir só ao `/simulador` (mais barato, mas deixava o `/consulta` sem a comparação) |
| 2 | `/consulta` ganha `itens: list[ItemSimulacao]` reaproveitando o MESMO tipo do `/simulador` | Evita duplicar schema/validação; consistente com a decisão de paridade total | Payload de item único (mais simples, mas divergiria do `/simulador` sem necessidade) |
| 3 | `valor_base` de `PayloadConsulta` passa a ser DERIVADO (soma dos itens), não mais campo manual | Elimina risco de inconsistência entre valor digitado e soma dos itens — mesma disciplina já usada em `valor_bruto_total` | Manter os dois campos, aceitando divergência possível |
| 4 | Lado IVA Dual do `/consulta` fica itemizado, com paridade total ao `/simulador` (Anexos de redução, IPI) | Plataforma se posiciona como "100% auditável" — um lado detalhado e outro aproximado confundiria o usuário | Manter IVA Dual agregado no `/consulta` (menor escopo, mas precisão desigual entre os dois lados da tabela) |
| 5 | Formulários (`/simulador` e `/consulta`) ganham seletor de `natureza` por item e `regime_apuracao` por operação | Sem isso, ISS e PIS/COFINS sempre apareceriam como "não calculado" — a comparação ficaria incompleta por padrão | Deixar como está, aceitando comparação sempre parcial |
| 6 | UF/natureza/NCM no `/consulta` são campos EXPLÍCITOS, nunca extraídos do texto livre por LLM | Mesma disciplina já aplicada a `valor_base`/`ano_operacao` em `extrator_regras.py` — dado exato nunca vem de inferência de LLM | Extração via LLM do texto da pergunta (risco real de erro silencioso em código de UF/NCM) |
| 7 | Lógica de cálculo extraída para função compartilhada, chamada direta (não HTTP interno) | Orquestração e router do `/simulador` já rodam no mesmo processo — HTTP interno seria desproporcional | Chamada HTTP interna ao próprio `/v1/tax/simulate` (padrão certo para Cloud Tasks, errado aqui) |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Gráficos/visualização da comparação | Tabela textual já entrega o valor central (números + fonte legal); gráfico é polimento, não o problema relatado pelo usuário | Yes |
| Exportação da comparação (PDF/CSV) | Ninguém pediu; o problema relatado foi "a comparação não existe", não "não dá pra exportar" | Yes |
| Comparação histórica multi-ano (2026-2033) na mesma tela | Fora do problema relatado; a API já recusa `ano_operacao >= 2027` com 422 (`ANEXO_XVI_PISO_ALIQUOTA_PROPRIA`/`SIMPLES_NACIONAL_CBS_IBS_TRANSICAO`), então só 2026 teria dado real hoje | Yes, quando mais anos tiverem alíquota fixada |
| Incluir Simples Nacional na mesma tabela comparativa | `POST /v1/tax/simulate-simples-nacional` já é um endpoint/schema independente, com público e fluxo diferentes | Yes, como extensão separada |
| Mudar o formato/contrato de `/v1/tax/simulate` | A API já devolve o dado certo — o gap é só de CONSUMO no frontend; nenhuma mudança de backend necessária para o `/simulador` sozinho | N/A — não é uma feature, é um não-problema |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|----------------|-----------|
| Escopo (`/simulador` vs `/simulador`+`/consulta`) | ✅ | Confirmou escopo maior | — |
| Redesenho de `PayloadConsulta` (itemizado) | ✅ | Confirmou, mesmo após custo explicado | — |
| Origem de UF/natureza/NCM (campo explícito vs. LLM) | ✅ | Campo explícito, disciplina preservada | — |
| Cardinalidade de `itens` no `/consulta` (um vs. lista) | ✅ | Lista, como `/simulador` | — |
| Origem de `valor_base` (manual vs. derivado) | ✅ | Derivado da soma dos itens | Sim — muda o schema de `PayloadConsulta` |
| Precisão do lado IVA Dual no `/consulta` (agregado vs. itemizado) | ✅ | Itemizado, paridade total | Sim — amplia bastante o escopo de backend |
| Campos novos de `natureza`/`regime_apuracao` nos formulários | ✅ | Confirmado, os dois campos | Sim — adiciona telas aos dois formulários |
| Arquitetura de reaproveitamento (função vs. HTTP interno) | ✅ | Função compartilhada, chamada direta | — |

**Minimum Validations:** 2 — 8 validações completadas.

---

## Suggested Requirements for /define

### Problem Statement (Draft)

A API já calcula e devolve, em `/v1/tax/simulate`, uma comparação completa entre o regime tributário atual (PIS/COFINS, ICMS, ISS, IPI) e o IVA Dual (CBS/IBS/IS) — mas nenhuma tela do frontend exibe esse dado, e o endpoint conversacional (`/v1/tax/query`) nem sequer calcula o lado do regime atual. O usuário não tem hoje nenhuma visão "antes x depois" real da transição tributária.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| Controller/CFO usando `/simulador` | Vê só o valor final do IVA Dual, sem referência de quanto pagaria hoje pelo regime atual — perde o argumento de negócio da transição |
| Usuário do `/consulta` conversacional | Recebe um parecer em texto sem nenhuma comparação estruturada, e o próprio backend nunca calcula o regime atual nesse fluxo |

### Success Criteria (Draft)

- [ ] `/simulador` exibe uma tabela comparativa regime atual x IVA Dual, por item e agregada, citando a fonte legal de cada tributo
- [ ] Tributos não calculados (por falta de `regime_apuracao`/`natureza=SERVICO`) aparecem declarados como "não calculado", nunca omitidos silenciosamente ou estimados
- [ ] `/consulta` aceita `itens` (mesmo shape de `ItemSimulacao`), calcula os dois lados com a MESMA precisão do `/simulador` (Anexos de redução, IPI por item), e exibe a mesma tabela comparativa
- [ ] `valor_base` de `/consulta` deixa de ser campo manual e passa a ser derivado da soma dos itens
- [ ] Lógica de cálculo do `/simulador` extraída para função compartilhada, sem duplicação entre router e orquestração
- [ ] Formulários de `/simulador` e `/consulta` ganham seletor de `natureza` (por item) e `regime_apuracao` (por operação)
- [ ] Nenhuma regressão nos ~640 testes existentes (backend) nem nos 34 testes de frontend

### Constraints Identified

- Sem mudança de schema de banco — feature 100% aplicação (Pydantic + React + função Python)
- `AliquotaNaoDisponivelError` continua interrompendo o fluxo (422/503) para `ano_operacao >= 2027` — a comparação só tem dado real para 2026 hoje
- UF/natureza/NCM no `/consulta` são sempre campos explícitos — LLM nunca infere esses valores
- `regime_apuracao`/`natureza` continuam opcionais/com default — nenhum payload existente pode quebrar (mudança aditiva, mesma disciplina de todo campo novo já visto no projeto)

### Out of Scope (Confirmed)

- Gráficos, exportação (PDF/CSV), comparação histórica multi-ano, Simples Nacional na mesma tabela — ver seção YAGNI acima
- Mudança de contrato de `/v1/tax/simulate` (já correto) — só consumo no frontend
- Ingestão de nova legislação — a pergunta original do usuário ("foi ingerido a legislação atual?") já foi respondida: sim, `motor_calculo/regime_atual.py` cita artigo real de cada alíquota; não há gap de ingestão, só de exibição

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 8 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 8 |
| Duration | ~1 sessão de diálogo |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_COMPARATIVO_REGIME_ATUAL_IVA_DUAL.md`
