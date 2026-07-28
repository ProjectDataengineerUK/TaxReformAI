# BRAINSTORM: IPI/TIPI no Motor de Cálculo

> Exploratory session to clarify intent and approach before requirements capture
>
> **Esta é a feature 1 de uma sequência de ~11 features já roteirizada** a partir de uma
> auditoria profunda de 12 achados (achado 13 descartado, achado 12 registrado à parte como
> item de monitoramento). Ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`
> para a ordem completa e o racional de sequenciamento. Esta sessão cobre só o escopo do
> item 1 (achado original nº 1 do levantamento).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | IPI_TIPI_MOTOR_CALCULO |
| **Date** | 2026-07-27 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Shipped (ver `SHIPPED_2026-07-28.md`) |
| **Posição na sequência** | 1 de 11 (ver ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md) |

---

## Initial Idea

**Raw Input:** Auditoria profunda encontrou que dois commits recentes (`a2c889f`, `3158041`)
ingeriram de verdade ~9231 códigos NCM → alíquota de IPI na tabela `aliquotas_ipi_tipi` do
Cloud SQL, com contagem real conferida pós-commit (`scripts/ingerir_tipi.py` confere
`SELECT count(*)` contra a tabela, não só o que foi tentado gravar). Mas
`motor_calculo/regime_atual.py` continua declarando `TRIBUTOS_INDISPONIVEIS = ("IPI",)` e
`api/routers/simulate.py` nunca consulta a tabela — o dado real, verificado, pago, está
parado sem nenhum consumidor.

**Context Gathered (nesta sessão):**
- `aliquotas_ipi_tipi` (migração `004_tipi.sql`) já tem `ncm_code UNIQUE`, `aliquota_percentual`
  (`NUMERIC(7,5)`, nullable), `nao_tributado BOOLEAN`, constraint
  `aliquota_xor_nao_tributado`, e `dispositivo_legal_ref TEXT NOT NULL` — ou seja, a
  distinção "NT" vs. 0% explícita e a citação legal por linha já existem no schema, não
  precisam ser desenhadas do zero.
- Sem RLS de propósito (dado legal público, igual para todos os tenants) — mesmo padrão
  de `regras_tributarias_cache`.
- `taxreformai_app` (papel de runtime da API) já tem `GRANT SELECT` explícito sobre esta
  tabela (a migração 003 não é retroativa a tabelas criadas depois, então a 004 já cuidou
  disso) — a API já PODE ler a tabela hoje, só não o faz.
- `ItemSimulacao` (payload de `/v1/tax/simulate`) já carrega `ncm: str` e
  `natureza: Literal["MERCADORIA", "SERVICO"]` — o dado necessário para o lookup (NCM) já
  chega no payload, não precisa de campo novo no contrato da API.
- `api/routers/simulate.py` já injeta `db_pool` via `Depends(get_db_pool)` para o audit log
  — o mesmo padrão de acesso a banco já existe na rota, não é uma dependência nova.
- Achado importante para o /design: **conflito arquitetural real**. `motor_calculo/`
  hoje é deliberadamente livre de infraestrutura ("roda direto, local ou não" — CLAUDE.md,
  seção "Como rodar"). Buscar IPI por NCM exige uma consulta a banco. Isso não cabe dentro
  de `motor_calculo/engine.py`/`regime_atual.py` sem quebrar essa premissa — o lookup
  provavelmente precisa viver em `api/` (camada que já tem `db_pool`), não em
  `motor_calculo/`, análogo a como `db/repositorio.py` já é a única camada com acesso a
  Postgres.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo `db/repositorio.py::buscar_ipi_por_ncm()` (ou lote) + consumo em `api/routers/simulate.py`; `motor_calculo/regime_atual.py` só perde `"IPI"` de `TRIBUTOS_INDISPONIVEIS` se o lookup ficar fora dele | Faz `motor_calculo` continuar puro; a API vira a camada que "junta" cálculo determinístico + dado tabular do Postgres |
| Relevant KB Domains | python-developer, database-reviewer | Padrão `Protocol` real/fake (já usado em `RawStorage`/`LegalSource`/`TabelaAliquotas`) provavelmente se repete aqui para testar sem Postgres real |
| Payload Impact | Nenhum campo novo necessário (`ncm` já existe); só `natureza == "MERCADORIA"` dispara o lookup (`natureza == "SERVICO"` nunca paga IPI, mesma exclusão mútua já aplicada a ICMS/ISS) | Zero mudança de contrato externo, só de comportamento interno |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual é o objetivo principal do próximo ciclo — terminar dado já pago (achado 1/2/3), aprofundar LLM (4/5/6), estabilizar operação (7/8/9), ou outra combinação? | Nenhum candidato único — atacar os 12 achados (menos o 13) em sequência, um de cada vez | Não há "vencedor" entre os candidatos apresentados; toda a auditoria vira um roadmap sequencial, não uma escolha exclusiva |
| 2 | O achado 12 (linha do tempo 2029-2033) está bloqueado por lei que ainda não existe — pular, tratar como monitoramento, ou outra abordagem? | Mantém como item de monitoramento fora da sequência ativa, revisitado só se/quando a lei sair | 11 features ativas, não 12; achado 12 documentado à parte no ROADMAP |
| 3 | A ordem segue a numeração 1→11 estrita, ou reordena por dependência técnica? | Reordena por dependência (LLM real antes dos nós reais da orquestração, que resolve o vazamento de graça), usando a numeração original como desempate nos casos sem dependência | Achado 5 passa a vir antes do achado 4 na sequência; acomodado 6 logo depois; resto segue a ordem original |

**Minimum Questions:** 3 ✅ (as 3 perguntas acima definiram o roadmap; esta sessão de brainstorm em si, sobre a feature 1 específica, herda o escopo já validado)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth | `aliquotas_ipi_tipi` (Cloud SQL, `taxreformai-pg`) | 9231 códigos NCM | Já ingerido e verificado por contagem real pós-commit (`scripts/ingerir_tipi.py`); não precisa de nova coleta de dado, só de um consumidor |
| Fonte legal | `dispositivo_legal_ref` por linha | 9231 | Decreto 11.158/2022 (TIPI) + Ato Declaratório Executivo RFB nº 1/2026, já citado por linha na tabela |
| Fixture de teste | Nenhuma ainda para o consumo (API/motor) | 0 | A definir no /design — provavelmente um fake `TabelaIpiTipi` (Protocol), no padrão já usado por `TabelaPisCofins`/`TabelaAliquotas`, com um subconjunto pequeno de NCMs reais para teste determinístico sem depender do Postgres |

**Como os dados serão usados:** o payload de `/v1/tax/simulate` já traz `ncm` por item; o
lookup busca a linha correspondente em `aliquotas_ipi_tipi` (por igualdade exata de NCM, não
busca semântica) e aplica a alíquota (ou `nao_tributado`) só a itens com
`natureza == "MERCADORIA"`, replicando a disciplina de citação de fonte já usada em
`icms_interno`/`iss_faixa`.

---

## Approaches Explored

### Approach A: Lookup direto no `api/routers/simulate.py` via `db/repositorio.py` (query em lote) ⭐ Recomendada

**What:** Novo `buscar_ipi_por_ncm(sessao, ncms: list[str])` em `db/repositorio.py`, que
faz uma única query (`WHERE ncm_code = ANY(%s)`) para todos os NCMs distintos do payload,
devolvendo um dict `ncm -> LinhaIpi`. `api/routers/simulate.py` chama isso uma vez por
request (não por item) e usa o resultado no laço já existente, incluindo IPI em
`itens_regime_vigente`/`resumo_financeiro` só para itens com `natureza == "MERCADORIA"`.
`motor_calculo/regime_atual.py` perde `"IPI"` de `TRIBUTOS_INDISPONIVEIS`.

**Pros:**
- Mantém `motor_calculo/` livre de infraestrutura (a premissa documentada no CLAUDE.md
  continua verdadeira)
- Uma query por request, não uma por item — sustenta o limite de 100 itens/payload sem
  N+1
- Reaproveita o `db_pool`/padrão de sessão que a rota já usa para o audit log
- `db/repositorio.py` continua sendo a única camada de acesso a Postgres, mesmo padrão de
  `buscar_regra_cache` (achado 2) e `sessao_do_tenant`

**Cons:**
- IPI passa a depender de Postgres estar disponível — hoje o motor de cálculo inteiro
  roda sem nenhuma infraestrutura; esta seria a primeira exceção real (achado 2, sobre
  `regras_tributarias_cache`, mostra que o schema já antecipava isso, mas nunca foi
  exercitado)
- Testes de `api/routers/simulate.py` que hoje não precisam de Postgres passariam a
  precisar (ou de um fake), aumentando a superfície de setup de teste

**Why Recommended:** É a única abordagem que não força `motor_calculo/` a violar sua
premissa de zero infraestrutura, e reaproveita exatamente o padrão de acesso a dados que
`SCHEMA_POSTGRESQL` já estabeleceu (sessão/pool injetável, testável com fake).

---

### Approach B: Cache em memória no processo da API (padrão `TabelaAliquotasSeed`)

**What:** Um `TabelaIpiTipi` carregado uma vez (no startup da API ou lazy na primeira
chamada) com todos os 9231 códigos em memória, no mesmo espírito de
`TabelaAliquotasSeed`/`TabelaPisCofins` — sem tocar Postgres por request.

**Pros:**
- Zero latência de banco por request depois do carregamento inicial
- Mesma "forma" que o resto de `motor_calculo/` já usa (dicionário estático)

**Cons:**
- 9231 linhas com `dispositivo_legal_ref` de texto livre não é um "seed" pequeno como
  `TabelaAliquotasSeed` (poucas dezenas de linhas) — manter isso como literal Python seria
  reintroduzir o mesmo dado em dois lugares (Postgres + código), com risco real de
  divergência quando a TIPI for reeditada
  Carregar do Postgres para popular esse cache em memória ainda amarra a inicialização da
  API a Postgres estar disponível — só desloca o problema do Approach A para o momento de
  startup, sem eliminá-lo
- Foge do padrão que `SCHEMA_POSTGRESQL` já estabeleceu (ler de banco sob demanda, não
  duplicar em código)

---

### Approach C: Endpoint dedicado de consulta de IPI por NCM, fora de `/v1/tax/simulate`

**What:** Um `GET /v1/tax/ipi/{ncm}` separado, deixando `/v1/tax/simulate` como está hoje
(IPI continua "indisponível" na simulação principal).

**Pros:**
- Menor risco de regressão em `/v1/tax/simulate`, que já está em produção

**Cons:**
- Não resolve o achado real — o dado fica acessível, mas a simulação (o produto principal)
  continua sem IPI, que era exatamente o problema apontado na auditoria
- Fragmenta a experiência: cliente ERP teria que fazer uma segunda chamada e somar o
  resultado manualmente, quando o resto do motor já consolida tudo numa resposta

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — lookup em lote via `db/repositorio.py`, consumido em `api/routers/simulate.py` |
| **User Confirmation** | Pendente — a confirmar explicitamente no início do `/define` (esta sessão validou o roadmap e a posição desta feature na sequência; a abordagem técnica específica ainda não foi apresentada ao usuário até este documento) |
| **Reasoning** | Única abordagem que preserva a premissa de `motor_calculo/` sem infraestrutura e reaproveita o padrão de acesso a dados já validado em `SCHEMA_POSTGRESQL`, sem duplicar o dado da TIPI em dois lugares |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Sequência ativa de 11 features, uma de cada vez, seguindo `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` | Decisão explícita do usuário: não escolher um único candidato, atacar todos os achados relevantes em sequência | Escolher um único "candidato" (A-D) e tratar os demais achados como não priorizados — rejeitado, contradiz a resposta do usuário |
| 2 | Achado 12 (linha do tempo 2029-2033) vira item de monitoramento fora da sequência ativa | Bloqueado por lei que ainda não existe — não é uma feature executável, só uma espera pela norma | Incluir como 12ª feature ativa — rejeitado, não há nada a construir até a lei sair; forçaria uma feature vazia ou uma estimativa não fundamentada |
| 3 | Achado 5 (LLM real) reordenado para antes do achado 4 (nós reais da orquestração); achado 6 (vazamento `[FAKE]`) segue logo depois | Dependência técnica real: não dá para tornar os nós da orquestração reais sem o LLM já conectado; o vazamento de `[FAKE]` desaparece como efeito colateral de tornar os nós reais | Manter a numeração estrita 4, 5, 6 — rejeitado pelo próprio usuário por criar uma ordem tecnicamente inviável |
| 4 | Nesta feature (item 1), o lookup de IPI/TIPI fica em `api/`/`db/repositorio.py`, não em `motor_calculo/` | `motor_calculo/` é deliberadamente livre de infraestrutura (roda local, sem credenciais); IPI por NCM exige Postgres, então a "junção" acontece na camada que já tem `db_pool` | Mover o lookup para dentro de `motor_calculo/engine.py` — rejeitado, quebraria a premissa documentada de que o motor roda sem nenhuma infraestrutura |
| 5 | Lookup em lote (uma query por request, não uma por item) | Payload já suporta até 100 itens; uma query por item seria N+1 desnecessário quando um `WHERE ncm_code = ANY(...)` resolve em uma chamada | Query por item dentro do laço existente — rejeitado, não escala e não é necessário |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|-----------------|------------------|
| Cache em memória da tabela TIPI inteira no processo da API (Approach B) | Duplicaria o dado (Postgres + literal Python) com risco de divergência quando a TIPI for reeditada; ainda amarra o startup da API a Postgres, sem eliminar a dependência, só deslocá-la | Sim, se latência por request se provar um problema real medido em produção — não assumido agora |
| Endpoint dedicado `/v1/tax/ipi/{ncm}` (Approach C) | Não resolve o problema real apontado na auditoria (IPI ausente da simulação principal); fragmenta a experiência do cliente ERP | Sim, como complemento futuro para consulta avulsa, sem substituir a integração em `/simulate` |
| Popular `TabelaAliquotasSeed`/qualquer alíquota de 2027+ como parte desta feature | Fora de escopo — esta feature é só sobre IPI (regime vigente), não sobre CBS/IBS/IS da reforma; não é o mesmo achado | Não aplicável — são achados diferentes na auditoria |
| Resolver `regras_tributarias_cache` (achado 2) junto com esta feature | Usuário decidiu explicitamente tratar cada achado como uma feature sequencial própria, não agrupar livremente, mesmo quando "dado pronto sem consumidor" é um padrão comum aos dois | É a próxima feature da sequência (posição 2), não descartada — só não combinada com esta |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|----------------|-----------|
| Candidatos de priorização (A-E) a partir dos 13 achados | ✅ | Usuário rejeitou escolher um único candidato — quis sequência completa | Sim — todo o enquadramento mudou de "escolher 1" para "roteirizar os 12" |
| Tratamento do achado 12 (bloqueado por lei inexistente) | ✅ | Confirmado como item de monitoramento fora da sequência ativa | Não — proposta aceita como estava |
| Critério de reordenação (numeração estrita vs. dependência técnica) | ✅ | Confirmado: dependência técnica prevalece, numeração original como desempate | Não — proposta aceita como estava |

**Minimum Validations:** 3 de 2 ✅ (as 3 rodadas de pergunta/resposta desta sessão já cumprem a validação incremental mínima antes de gerar este documento)

---

## Suggested Requirements for /define

### Problem Statement (Draft)
`aliquotas_ipi_tipi` tem 9231 códigos NCM → alíquota de IPI, ingeridos e verificados no
Cloud SQL, mas `motor_calculo/regime_atual.py` e `api/routers/simulate.py` tratam IPI como
"indisponível", como se o dado não existisse. A feature conecta o dado já pago ao produto
real: `/v1/tax/simulate` passa a incluir IPI para itens com `natureza == "MERCADORIA"`,
citando `dispositivo_legal_ref` por linha, mantendo `motor_calculo/` livre de
infraestrutura ao colocar o lookup na camada de API/repositório.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Recebe uma simulação que declara IPI como "não incluído" mesmo quando o dado exato já existe e está verificado no banco do próprio produto |
| Controller/CFO usando o simulador | Carga tributária do regime vigente fica subestimada sem IPI, distorcendo a comparação "hoje vs. IVA Dual" que é a proposta de valor central do produto |

### Success Criteria (Draft)
- [ ] `aliquotas_ipi_tipi` tem um consumidor real em `db/repositorio.py` (função de lookup em lote por NCM)
- [ ] `/v1/tax/simulate` inclui IPI no resumo financeiro e por item, só para `natureza == "MERCADORIA"`, com `dispositivo_legal_ref` citado como fonte legal
- [ ] Itens com NCM não encontrado na tabela (ou `nao_tributado = true`) são tratados explicitamente — nunca como alíquota zero silenciosa
- [ ] `escopo.tributos_nao_incluidos` deixa de listar `"IPI"` quando o lookup é bem-sucedido
- [ ] `motor_calculo/` não ganha nenhuma dependência de banco — o lookup vive em `api/`/`db/`
- [ ] Teste cobre: NCM com alíquota, NCM `nao_tributado`, NCM ausente da tabela, payload com múltiplos NCMs (uma query, não N)

### Constraints Identified
- `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura — o lookup de IPI é
  responsabilidade de `api/`/`db/repositorio.py`, não de `motor_calculo/engine.py`
- Sem RLS na tabela (dado público, mesmo para todos os tenants) — não introduzir tenant
  scoping onde a própria migração já decidiu que não existe
- IPI segue sendo tratado por igualdade exata de NCM — sem tentativa de fuzzy match ou
  fallback por prefixo de código
- `natureza == "SERVICO"` nunca dispara lookup de IPI, mesma exclusão mútua já aplicada a
  ICMS/ISS

### Out of Scope (Confirmed)
- `regras_tributarias_cache` (achado 2) — próxima feature da sequência, não combinada com esta
- API de `empresa_skus` (achado 3)
- Qualquer trabalho de LLM/orquestração (achados 4, 5, 6)
- Cloud Composer, verificação de frontend, diagnóstico de busca híbrida, BigQuery, fila assíncrona (achados 7-11)
- Linha do tempo 2029-2033 (achado 12) — item de monitoramento, não uma feature

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 (nível roadmap) |
| Approaches Explored | 3 (nível desta feature) |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 3 de 2 |
| Duration | 1 sessão de diálogo, incluindo leitura de código real (`regime_atual.py`, `simulate.py`, `db/tipi.py`, `scripts/ingerir_tipi.py`, migrações 001/004) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_IPI_TIPI_MOTOR_CALCULO.md`

**Depois desta feature ser shipada**, a próxima da sequência é a posição 2:
`REGRAS_TRIBUTARIAS_CACHE` (ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).
