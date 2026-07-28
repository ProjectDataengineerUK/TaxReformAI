# DEFINE: IPI/TIPI no Motor de Cálculo

> Conectar `aliquotas_ipi_tipi` (9231 NCM já ingeridos e verificados no Cloud SQL) a
> `/v1/tax/simulate`, para que IPI deixe de ser declarado "indisponível" quando o dado já
> existe, pago e pronto.
>
> **Posição na sequência:** 1 de 11 (ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).
> Esta sessão cobre só o escopo do achado original nº 1 — nenhuma decisão sobre as outras 10
> features da sequência foi tomada aqui.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | IPI_TIPI_MOTOR_CALCULO |
| **Date** | 2026-07-27 |
| **Author** | define-agent |
| **Status** | ✅ Shipped (ver `SHIPPED_2026-07-28.md`) |
| **Clarity Score** | 15/15 |

---

## Problem Statement

`aliquotas_ipi_tipi` tem 9231 códigos NCM → alíquota de IPI, ingeridos e verificados no Cloud
SQL (contagem real conferida pós-commit), mas `motor_calculo/regime_atual.py` declara
`TRIBUTOS_INDISPONIVEIS = ("IPI",)` e `api/routers/simulate.py` nunca consulta a tabela — o
dado real, verificado e pago está parado sem nenhum consumidor, e `/v1/tax/simulate` segue
subestimando a carga tributária do regime vigente.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Recebe uma simulação que declara IPI como "não incluído" mesmo quando o dado exato já existe e está verificado no banco do próprio produto |
| Controller/CFO usando o simulador | Consumidor indireto do produto (via ERP ou frontend) | Carga tributária do regime vigente fica subestimada sem IPI, distorcendo a comparação "hoje vs. IVA Dual" que é a proposta de valor central do produto |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Novo lookup em lote por NCM em `db/repositorio.py` (uma query por request, `WHERE ncm_code = ANY(...)`), reaproveitando o padrão de sessão/pool já usado pelo audit log em `api/routers/simulate.py` |
| **MUST** | `/v1/tax/simulate` inclui IPI no resumo financeiro do regime vigente e por item, só para itens com `natureza == "MERCADORIA"`, citando `dispositivo_legal_ref` da linha correspondente como fonte legal |
| **MUST** | Itens com NCM ausente da tabela, ou com `nao_tributado = true`, são tratados de forma explícita e nunca confundidos com alíquota zero silenciosa |
| **MUST** | `escopo.tributos_nao_incluidos` deixa de listar `"IPI"` quando o lookup é bem-sucedido para todos os itens de mercadoria do payload |
| **MUST** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura/banco — o lookup vive inteiramente em `api/`/`db/repositorio.py` |
| **SHOULD** | Teste cobrindo payload com múltiplos NCMs distintos resolvidos em exatamente 1 query (não N) |
| **SHOULD** | Mensagem/campo claro na resposta quando IPI não pôde ser resolvido para um subconjunto dos itens (falha parcial, não all-or-nothing por padrão) |
| **COULD** | Observabilidade de latência da nova query (fora do escopo funcional desta feature) |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Success Criteria

- [ ] `db/repositorio.py` ganha uma função de lookup em lote (ex.: `buscar_ipi_por_ncm(sessao, ncms: list[str])`) que resolve N NCMs distintos em **exatamente 1 query SQL**, testável com Postgres real (mesmo padrão dos testes de `db/`) e com fake para os demais testes
- [ ] `/v1/tax/simulate` inclui `total_ipi` no resumo do regime vigente e `ipi_percentual`/`fonte_legal_ipi` por item para **100% dos itens** com `natureza == "MERCADORIA"` cujo NCM existe na tabela
- [ ] NCM com `nao_tributado = true` é declarado explicitamente como tal na resposta (nunca como 0% implícito)
- [ ] NCM ausente da tabela é declarado explicitamente como "IPI indisponível para este NCM" — nunca omitido silenciosamente nem tratado como 0%
- [ ] `escopo.tributos_nao_incluidos` deixa de listar `"IPI"` quando todos os itens de mercadoria do payload tiveram IPI resolvido com sucesso
- [ ] Suite de teste cobre no mínimo **4 cenários**: NCM com alíquota, NCM `nao_tributado`, NCM ausente da tabela, payload com ≥2 NCMs distintos resolvidos em 1 query
- [ ] **Zero mudança de contrato externo obrigatório** no payload de entrada (`ncm` já existe hoje); `natureza == "SERVICO"` nunca dispara o lookup de IPI

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path | Item com `natureza=MERCADORIA` e `ncm` existente na tabela com `aliquota_percentual` preenchida | `POST /v1/tax/simulate` | 200, resposta inclui `total_ipi` coerente com `aliquota_percentual × valor_base_item`, `fonte_legal_ipi` = `dispositivo_legal_ref` da linha, e `escopo.tributos_nao_incluidos` não lista mais `"IPI"` |
| AT-002 | Edge case — NT | Item com `ncm` cujo `nao_tributado = true` | `POST /v1/tax/simulate` | 200, resposta declara explicitamente o item como não tributado (campo/flag distinto de alíquota 0%), sem somar valor de IPI para esse item |
| AT-003 | Edge case — NCM ausente | Item com `ncm` que não existe em `aliquotas_ipi_tipi` | `POST /v1/tax/simulate` | Resposta trata esse item especificamente como IPI indisponível para aquele NCM (comportamento exato — falha só do item vs. 422 do payload inteiro — a decidir no /design, mas nunca 0% silencioso) |
| AT-004 | Lote sem N+1 | Payload com itens de N NCMs distintos (N > 1), todos existentes na tabela | `POST /v1/tax/simulate` | Exatamente 1 query SQL resolve todos os NCMs distintos (verificável por spy/contagem de chamadas ao cursor em teste) |
| AT-005 | Exclusão mútua — serviço | Item com `natureza=SERVICO` | `POST /v1/tax/simulate` | Nenhum lookup de IPI é disparado para esse item — mesma exclusão mútua já aplicada a ICMS/ISS |

---

## Out of Scope

- `REGRAS_TRIBUTARIAS_CACHE` (achado 2 / posição 2 da sequência) — próxima feature, não combinada com esta
- `API_EMPRESA_SKUS` (achado 3), `LLM_REAL_VERTEX_AI` (achado 5), `ORQUESTRACAO_NOS_REAIS` (achado 4), `REMOVER_FAKE_HISTORICO` (achado 6), `CLOUD_COMPOSER_PROVISIONAMENTO` (achado 7), `VERIFICACAO_FRONTEND_NAVEGADOR` (achado 8), `DIAGNOSTICO_BUSCA_HIBRIDA` (achado 9), `BIGQUERY_DATA_WAREHOUSE` (achado 10), `FILA_ASSINCRONA_CELERY_REDIS` (achado 11) — demais features da sequência, fora de escopo desta sessão
- Linha do tempo 2029-2033 (achado 12) — item de monitoramento, não uma feature executável
- Alterar o schema/migração `004_tipi.sql` — já aplicado e verificado (9231 linhas); esta feature é só sobre criar um consumidor, não sobre o schema
- Fuzzy match, busca por prefixo de NCM ou qualquer heurística de aproximação — só igualdade exata de `ncm_code`
- Cache em memória da tabela TIPI inteira no processo da API (Approach B do brainstorm, rejeitada — duplicaria o dado e amarraria o startup a Postgres sem eliminar a dependência)
- Endpoint dedicado `GET /v1/tax/ipi/{ncm}` fora de `/v1/tax/simulate` (Approach C do brainstorm, rejeitada — não resolve o problema real, fragmenta a experiência do cliente ERP)
- Sincronização/reedição bimestral da TIPI — mesma decisão já registrada para SPED/IBPT no CLAUDE.md; problema de atualização periódica, não de ingestão ou consumo

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura (premissa documentada no CLAUDE.md, seção "Como rodar") | O lookup de IPI vive em `api/`/`db/repositorio.py`, nunca em `motor_calculo/engine.py` ou `regime_atual.py` |
| Technical | Sem RLS na tabela `aliquotas_ipi_tipi` — dado legal público, igual para todos os tenants (mesmo padrão de `regras_tributarias_cache`) | Não introduzir tenant scoping onde a própria migração 004 já decidiu que não existe |
| Technical | IPI tratado por igualdade exata de NCM | Sem fallback por prefixo de código nem fuzzy match |
| Technical | Payload já limitado a 100 itens (`API_HTTP_SIMULACAO`) | O lookup em lote deve ser 1 query por request, não 1 por item, para não introduzir N+1 |
| Business | `natureza == "SERVICO"` nunca paga IPI | Mesma exclusão mútua já aplicada a ICMS/ISS — nenhum lookup deve ser disparado para itens de serviço |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `db/repositorio.py` (nova função de lookup em lote) + `api/routers/simulate.py` (consumo) + `motor_calculo/regime_atual.py` (remoção de `"IPI"` de `TRIBUTOS_INDISPONIVEIS`, condicional ao lookup ter sucesso) | Nenhum diretório novo — reaproveita a estrutura de `SCHEMA_POSTGRESQL`/`API_HTTP_SIMULACAO` já shipadas |
| **KB Domains** | `python` (clean-architecture, error-handling), `testing` (fixtures/mocking — padrão `Protocol` real/fake já usado em `TabelaPisCofins`/`RawStorage`), `pydantic` (se novos campos de resposta forem necessários em `schemas_simulate.py`) | Domínios do `${CLAUDE_PLUGIN_ROOT}/kb/`; os agentes de projeto equivalentes (`python-developer`, `database-reviewer`) já usados nas 8 features anteriores continuam aplicáveis |
| **IaC Impact** | Nenhum | Migração 004 já aplicada e verificada (9231 linhas) no Cloud SQL real; `taxreformai_app` já tem `GRANT SELECT` na tabela; esta feature não cria nem altera schema |

**Why This Matters:**

- **Location** → Evita reabrir a discussão arquitetural do brainstorm (motor_calculo/ vs. api/) durante o Design
- **KB Domains** → Design deve puxar o padrão `Protocol` real/fake já estabelecido em 3 features anteriores, não reinventar
- **IaC Impact** → Nenhuma surpresa de infraestrutura — o dado e o grant já existem em produção

---

## Data Contract (dado já ingerido — sem nova pipeline)

> Esta feature consome uma tabela já ingerida (`aliquotas_ipi_tipi`, migração `004_tipi.sql`,
> aplicada e verificada no Cloud SQL). Não há nova ingestão nem novo contrato de dados —
> a seção documenta o contrato **existente** para orientar o /design.

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| `aliquotas_ipi_tipi` | Postgres (Cloud SQL `taxreformai-pg`) | 9231 linhas (estático), já ingerido e verificado por `scripts/ingerir_tipi.py` (`SELECT count(*)` pós-commit) | Sem SLA de atualização nesta feature — reedição bimestral é problema de sincronização separado, fora de escopo | `taxreformai_admin` (ingestão/escrita); `taxreformai_app` só tem `GRANT SELECT` |

### Schema Contract

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `ncm_code` | VARCHAR(10) | NOT NULL, UNIQUE | Não |
| `aliquota_percentual` | NUMERIC(7,5) | NULL quando `nao_tributado = true`; NOT NULL caso contrário (`CHECK aliquota_xor_nao_tributado`) | Não |
| `nao_tributado` | BOOLEAN | NOT NULL, default false | Não |
| `dispositivo_legal_ref` | TEXT | NOT NULL | Não |

### Freshness SLAs

Não aplicável nesta feature — a tabela é estática do ponto de vista do consumo aqui descrito.

### Completeness Metrics

- 9231/9231 NCMs já verificados por contagem real na ingestão (não uma responsabilidade desta feature)
- Um NCM do payload não constar na tabela é um caso normal a tratar explicitamente (AT-003), não uma falha de completude da tabela

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Postgres estar disponível durante `/v1/tax/simulate` é uma dependência aceitável (já existe implicitamente hoje via audit log, ainda que o audit log em si nunca propague falha) | Precisaria de um caminho de fallback/circuit breaker explícito para a consulta de IPI — não coberto nesta feature | [ ] |
| A-002 | Uma única query em lote (`WHERE ncm_code = ANY(...)`) escala bem para até 100 itens por request (limite já existente do payload) | Se NCMs duplicados dominarem o payload, pode precisar de `DISTINCT` antes da query — ajuste simples, não muda a abordagem | [ ] |
| A-003 | NCM ausente da tabela deve ser tratado como "IPI indisponível para este item" (falha granular por item), não como erro 422 do payload inteiro | Se a decisão for all-or-nothing, o contrato de resposta e os testes de AT-003 mudam — fica para o /design decidir explicitamente, nunca por omissão | [ ] |
| A-004 | A abordagem técnica é a Approach A do brainstorm (lookup em lote via `db/repositorio.py`, consumido em `api/routers/simulate.py`, `motor_calculo/` livre de infraestrutura) | N/A — confirmado diretamente pelo usuário via `AskUserQuestion`; Approach B (cache em memória na API) e Approach C (endpoint dedicado `GET /v1/tax/ipi/{ncm}`) foram explicitamente descartadas, não apenas por eliminação técnica do brainstorm | [x] Confirmado por Jonatas via `AskUserQuestion` — ver Open Questions |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, causa raiz já identificada no código real (`TRIBUTOS_INDISPONIVEIS`, ausência de consulta) |
| Users | 3 | Dois usuários concretos com pain points específicos e já existentes no produto (não hipotéticos) |
| Goals | 3 | MoSCoW explícito, herdado quase integralmente do brainstorm já validado |
| Success | 3 | Critérios testáveis e majoritariamente numéricos (1 query, 100% dos itens, 4 cenários mínimos) |
| Scope | 3 | Out of scope extremamente explícito, referenciando as 10 outras features da sequência por nome |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15** ✅ (score não é o bloqueio desta feature — ver Status/Open Questions)

---

## Open Questions

**Confirmação da abordagem técnica — RESOLVIDA.** Jonatas confirmou explicitamente, via
`AskUserQuestion`, a Approach A do brainstorm: lookup em lote (1 query por request) em
`db/repositorio.py`, consumido por `api/routers/simulate.py`, mantendo `motor_calculo/`
livre de dependência de infraestrutura/banco. Approach B (cache em memória da tabela
inteira no processo da API) e Approach C (endpoint dedicado `GET /v1/tax/ipi/{ncm}`, fora
de `/simulate`) foram apresentadas como alternativas e não escolhidas — ambas continuam
listadas em "Out of Scope" pelo mesmo motivo original (duplicação de dado / não resolve o
problema real), agora reforçado por rejeição explícita do usuário, não só por eliminação
técnica do brainstorm. `A-004` foi atualizada de acordo. Nenhuma seção deste documento
(Technical Context, Acceptance Tests, Constraints) precisou mudar como resultado — todas já
assumiam a Approach A.

Restam apenas duas perguntas, ambas **não bloqueantes para o `/design`** — são decisões de
comportamento que o próprio `/design` deve responder explicitamente (não por omissão), não
pendências de escopo ou de abordagem:

1. Comportamento exato quando um NCM do payload não existe na tabela: falha só aquele item
   (parcial, resposta 200 com o item marcado) ou falha a requisição inteira (422)? Registrado
   como `A-003`; fica para o `/design` decidir explicitamente.

2. Comportamento quando a própria consulta de IPI falhar por indisponibilidade do Postgres
   (diferente do audit log, que deliberadamente nunca propaga falha) — qual código de erro
   HTTP exato, fica para o `/design`.

Nenhum outro item desta seção é bloqueante — **este documento está pronto para `/design`.**

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-27 | define-agent | Versão inicial, extraída de `BRAINSTORM_IPI_TIPI_MOTOR_CALCULO.md`; Status = Needs Clarification até a confirmação explícita da abordagem técnica (Open Question 1) |
| 1.1 | 2026-07-27 | define-agent | Jonatas confirmou a Approach A via `AskUserQuestion`; `A-004` atualizada, Open Questions revisada (só restam 2 decisões não bloqueantes, deferidas ao `/design`), Status → Ready for Design |
| 1.2 | 2026-07-27 | design-agent | Status → Designed. As 2 Open Questions foram resolvidas explicitamente no DESIGN: NCM ausente falha só o item com 200 (Decisão 1, `A-003` confirmada) e falha do Postgres degrada graciosamente sem código de erro (Decisão 2, `A-001` confirmada) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_IPI_TIPI_MOTOR_CALCULO.md`
