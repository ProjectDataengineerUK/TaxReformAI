# BRAINSTORM: API de Catálogo de SKUs (empresa_skus)

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 3 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`). Primeira feature da "primeira
> leva" retomada depois da "segunda leva" (posições 12-17) ter sido concluída por completo em
> 2026-08-01.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_EMPRESA_SKUS |
| **Date** | 2026-08-01 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 3 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input (roadmap):** "Endpoints para tenant cadastrar/listar/upload de SKUs (`empresa_skus`
— schema e RLS já existem, zero rota)."

**Context Gathered nesta sessão:**

- **Schema já existe** (`db/migrations/001_schema_inicial.sql`): `empresa_skus(id, tenant_id,
  codigo_sku, descricao, ncm_code NOT NULL, nbs_code NULL, created_at)`, `UNIQUE(tenant_id,
  codigo_sku)`, índices por `tenant_id` e `(tenant_id, ncm_code)`.
- **RLS já existe** (`db/migrations/002_row_level_security.sql`): `ENABLE`+`FORCE ROW LEVEL
  SECURITY`, policy `tenant_isolation` via `current_setting('app.tenant_id')` — mesmo padrão já
  usado por `pareceres_audit_log`.
- **Zero rota**: `grep -rl empresa_skus api/` não retorna nada. `db/repositorio.py` já tem o
  utilitário certo para escrever com RLS, `sessao_do_tenant(conexao, tenant_id: UUID)`
  (`SET LOCAL app.tenant_id`, escopo de transação) e `resolver_tenant(conexao, identificador)`
  (aceita slug OU UUID — a mesma função que `api/audit.py` já usa).
- **Achado técnico não previsto pelo roadmap**: o schema atual força `ncm_code NOT NULL` para
  TODA SKU, mesmo de serviço — `ItemSimulacao` (`/v1/tax/simulate`) já modela
  `natureza: MERCADORIA | SERVICO` com NCM/NBS mutuamente exclusivos, mas `empresa_skus` não tem
  coluna `natureza` nenhuma. Sem correção, um SKU de serviço puro precisaria de um NCM
  placeholder/inventado — contra a disciplina do projeto.
- **`contexto.md` (blueprint original)** confirma o desenho original da tabela (idêntico ao
  schema aplicado) e cita, na seção 9 (modelo de negócio, NÃO implementada e fora de escopo):
  "Business: Upload de até 10.000 SKUs" e reserva **50.000+ SKUs** para "Fila Assíncrona
  (Celery + Memorystore/Redis)" — que é a posição 11 do roadmap
  (`FILA_ASSINCRONA_CELERY_REDIS`), ainda não construída. Isso desenha a fronteira de escala
  desta feature: upload síncrono, escala pequena/média; 50.000+ SKUs fica para a posição 11.
- **`/v1/tax/simulate` hoje não toca `empresa_skus` de forma alguma** — cada item do payload
  exige `ncm` explícito. O catálogo, sem esta feature, seria uma tabela morta (schema aplicado,
  nunca lida nem escrita).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Padrão de escrita com RLS já validado | `sessao_do_tenant`/`resolver_tenant` já existem e já são usados por `api/audit.py` | Reaproveitável sem mudança — primeira feature CRUD do projeto, mas a fundação já foi construída em `SCHEMA_POSTGRESQL` |
| `ncm_code NOT NULL` sem `natureza` | Gap real entre o schema de `empresa_skus` e o vocabulário já usado em `ItemSimulacao` | Exige migração nova (próximo número livre: `014_*.sql`) — primeira migração de schema desde a 013 |
| Primeiro endpoint de LISTAGEM do projeto | Toda API existente é `POST` de cálculo/consulta — nenhum precedente de paginação | `/design` decide o mecanismo (limit/offset é o mais simples e suficiente para o volume desta feature) |
| Primeiro upload de ARQUIVO do projeto | Toda API existente recebe JSON puro | Precisa de `python-multipart` (dependência nova, comum ao FastAPI) e parsing de CSV (stdlib `csv`, sem dependência nova) |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Só CRUD do catálogo, ou também conectar `/v1/tax/simulate` para resolver NCM/NBS a partir do SKU? | **CRUD + wiring em `/v1/tax/simulate`** | Maior escopo que o roadmap sugeria — toca o endpoint mais crítico do produto, exige decisão de precedência (ver Q4) |
| 2 | Quais operações de gerenciamento? | **CRUD completo** (criar, listar, editar, excluir) + upload em lote | Endpoint por SKU individual (`{codigo_sku}`) além de listagem/criação em lote |
| 3 | Formato/escala do upload em lote? | **Arquivo CSV, síncrono** | Precisa de parser CSV + validação por linha + relatório de erros por linha; escala limitada (posição 11 assume 50.000+ no futuro) |
| 4 | Como resolver o gap `ncm_code NOT NULL` sem `natureza`? | **Migração nova**: adiciona `natureza`, torna `ncm_code` opcional, `CHECK` garante exatamente um dos dois preenchido conforme a natureza | Primeira migração desde a 013; mesma disciplina de mutual exclusividade já usada em `ItemSimulacao` |

**Minimum Questions:** 3 ✅ (4 registradas, incluindo o achado técnico da coluna `natureza`)

**Decisão adicional, tomada por julgamento nesta sessão (ver nota abaixo)**: quando o item de
`/v1/tax/simulate` traz `sku` cadastrado E TAMBÉM `ncm`/`nbs` explícito, o valor EXPLÍCITO
sempre vence — o catálogo só preenche a lacuna quando `ncm` e `nbs` vierem ambos ausentes do
item. Mesma disciplina declaratória já usada em todo campo opcional deste projeto
(`comprador_tipo`, `bem_importado`, `embalagem_primaria_consumidor_final` etc.): um dado que o
cliente informou explicitamente nunca é silenciosamente sobrescrito por uma inferência do
sistema. **Nota:** esta pergunta seria idealmente confirmada com o usuário, mas a sessão pediu
para prosseguir com a melhor opção — fica registrada aqui, explícita, para revisão no
`/define` se o usuário discordar.

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth externo | N/A | 0 | Diferente de toda feature anterior (Anexos legais), esta feature não depende de nenhum texto legal — é gerenciamento de catálogo do próprio cliente. Nenhuma verificação de fonte primária é necessária |
| Schema/RLS já aplicados | `db/migrations/001`+`002` | 1 tabela, 1 policy | Verificados diretamente contra o código nesta sessão (não infraestrutura real — schema já está no Cloud SQL desde `SCHEMA_POSTGRESQL`) |
| Exemplo de payload (contexto.md, seção 8.1) | `contexto.md`, linha ~371 | 1 exemplo | `{"sku": "PROD-1092", "ncm": "8471.30.12", ...}` — confirma o vocabulário `sku`/`ncm` já em uso |

---

## Approaches Explored

### Approach A: Router novo (`api/routers/empresa_skus.py`) + migração 014 (natureza) + wiring mínimo em `/v1/tax/simulate` ⭐ Recomendada

**What:** Novo router FastAPI (`/v1/tax/skus`) com CRUD completo + upload CSV, reaproveitando
`sessao_do_tenant`/`resolver_tenant` já existentes. Migração 014 adiciona `natureza` e relaxa
`ncm_code`. Em `api/routers/simulate.py`, adiciona uma consulta em lote (mesmo padrão das 4 já
existentes — IPI/redução NCM/redução NBS/Imposto Seletivo) que resolve `ncm`/`nbs` a partir de
`sku`, só quando ambos vierem ausentes do item.

**Pros:**
- Reaproveita 100% da fundação de RLS já construída (`SCHEMA_POSTGRESQL`) — zero código novo de
  infraestrutura de tenant.
- Router isolado, mesmo padrão de todo endpoint novo deste projeto (schemas dedicados + router
  dedicado).
- Corrige um gap estrutural real (`natureza` ausente) em vez de ignorá-lo.

**Cons:**
- Maior escopo do que "só CRUD" — toca `/v1/tax/simulate`, o endpoint mais testado/crítico do
  projeto (precisa de disciplina extra de zero-regressão).
- Upload CSV é a primeira feature de parsing de arquivo do projeto — superfície nova de
  validação (linha malformada, encoding, tamanho de arquivo).

**Why Recommended:** É a única abordagem que faz o catálogo ser útil de verdade (sem o wiring em
`/v1/tax/simulate`, a tabela existe mas nunca é lida por nada) — e corrige o gap de schema em vez
de o herdar como dívida técnica silenciosa.

### Approach B: Só CRUD do catálogo, sem tocar `/v1/tax/simulate`

**What:** Router novo, só gerencia o catálogo. `/v1/tax/simulate` permanece exatamente como
está.

**Pros:**
- Escopo menor, zero risco de regressão no endpoint de cálculo.
- Mais fiel à literalidade do roadmap ("endpoints para... SKUs").

**Cons:**
- O catálogo fica sem consumidor — schema e RLS aplicados desde `SCHEMA_POSTGRESQL`, mas
  `empresa_skus` continuaria sendo uma tabela que ninguém lê, só escreve.
- Rejeitada pelo usuário nesta sessão (Discovery Question 1).

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — router novo + migração 014 + wiring mínimo em `/v1/tax/simulate` |
| **User Confirmation** | Confirmado nesta sessão (Discovery Questions 1-4) |
| **Reasoning** | Única abordagem que torna o catálogo funcionalmente útil e corrige o gap de schema (`natureza` ausente) em vez de o ignorar |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | CRUD completo (criar/listar/editar/excluir) + upload CSV, não só criar+listar | Decisão explícita do usuário | Só criar+listar — mais simples, mas roadmap já cita "listar" e o usuário pediu CRUD completo |
| 2 | Upload é CSV síncrono, não JSON em lote nem fila assíncrona | Decisão explícita do usuário; alinhado à fronteira de escala do blueprint (10.000 SKUs síncrono vs. 50.000+ na posição 11) | JSON em lote — mais simples de implementar, mas o usuário preferiu CSV, mais próximo da experiência real de upload de planilha |
| 3 | Migração 014 adiciona `natureza`, relaxa `ncm_code` para NULLABLE, `CHECK` de exclusividade | Decisão explícita do usuário — corrige o gap real entre o schema e o vocabulário de `ItemSimulacao` | Manter o schema como está (ncm_code sempre obrigatório) — rejeitada por contradizer a disciplina de "nunca inventar dado" |
| 4 | `/v1/tax/simulate` PASSA a resolver `ncm`/`nbs` a partir de `sku` cadastrado, só quando ambos ausentes no item | Decisão explícita do usuário (maior escopo escolhido na Q1) | Catálogo isolado, sem nenhuma conexão com `/v1/tax/simulate` — rejeitada |
| 5 | Valor explícito de `ncm`/`nbs` no payload de `/v1/tax/simulate` sempre vence sobre o catálogo | Julgamento desta sessão (usuário pediu "a melhor opção" em vez de responder) — mesma disciplina declaratória de todo campo opcional já existente no projeto | Catálogo sempre vence — mais rígido, mas remove flexibilidade de testar um NCM alternativo para o mesmo SKU numa simulação pontual; **usuário deve revisar no `/define`** |
| 6 | `POST /v1/tax/skus` (criação individual) é estritamente CREATE (409 em duplicata); upload CSV faz UPSERT por `(tenant_id, codigo_sku)` | Julgamento desta sessão: reenviar a mesma planilha (fluxo real de upload) forçando erro em toda linha repetida seria hostil ao usuário; a rota de edição explícita (`PATCH`) cobre a correção pontual de um SKU só | Upload também rejeita duplicata — mais simples, mas inviabiliza o caso de uso mais comum de upload (reenviar uma planilha atualizada); **usuário deve revisar no `/define`** |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Upload assíncrono (Celery/Redis) para 50.000+ SKUs | Já é a posição 11 do roadmap (`FILA_ASSINCRONA_CELERY_REDIS`), feature própria e ainda não construída | Sim — é literalmente a próxima etapa natural depois desta feature, se o volume real do cliente justificar |
| Enforcement de limite por plano (Professional/Business/Enterprise) | Seção 9 do blueprint (modelo de negócio/pricing) está deliberadamente fora de escopo do projeto até aqui (Achado 13 do roadmap) | Sim, se o produto decidir implementar billing/planos |
| Validação de que o NCM/NBS cadastrado EXISTE numa tabela oficial (TIPI, Anexos) | Fora de escopo — `empresa_skus` é o catálogo PRÓPRIO do cliente, pode conter um NCM que ainda não está em nenhuma tabela oficial ingerida; validar só o FORMATO (dígitos), não a existência, é a mesma disciplina de `api/ncm.py`/`api/nbs.py` | Não teria sentido — a intersecção com IPI/Anexos já acontece em `/v1/tax/simulate` no momento da simulação, não no cadastro |
| Histórico de alterações (audit trail por SKU) | Não pedido; `pareceres_audit_log` já registra cada chamada de `/v1/tax/simulate`, mas mudanças no catálogo em si não têm pedido de rastreamento | Sim, se o produto precisar de trilha de auditoria específica do catálogo |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Escopo: CRUD + wiring em `/v1/tax/simulate` | ✅ | Confirmado (opção de maior escopo escolhida) | Fechou o escopo maior |
| Operações: CRUD completo | ✅ | Confirmado | Fechou a superfície da API |
| Upload: CSV síncrono | ✅ | Confirmado | Fechou o formato |
| Migração para `natureza` | ✅ | Confirmado | Fechou a correção de schema |
| Precedência SKU vs. ncm/nbs explícito; upsert do upload | ⚠️ | Usuário pediu "a melhor opção" em vez de responder — resolvido por julgamento desta sessão, registrado como Decisões 5 e 6 acima, marcado para revisão no `/define` | Registrado como pendência de confirmação, não bloqueia o avanço |

**Minimum Validations:** 5 de 2 ✅ (2 delas resolvidas por julgamento, não por resposta direta —
sinalizadas explicitamente para o `/define`)

---

## Suggested Requirements for /define

### Problem Statement (Draft)
A tabela `empresa_skus` (catálogo de SKU→NCM/NBS por tenant) tem schema e RLS aplicados desde
`SCHEMA_POSTGRESQL`, mas nenhuma rota da API a lê ou escreve — é uma tabela morta. Além disso, o
schema força `ncm_code` em toda SKU, mesmo de serviço, um gap frente ao vocabulário
`natureza: MERCADORIA | SERVICO` que `/v1/tax/simulate` já usa.

### Success Criteria (Draft)
- [ ] Migração nova (`014_*.sql`) adiciona `natureza`, relaxa `ncm_code`, `CHECK` de
      exclusividade — sem regressão nos dados já existentes (se houver)
- [ ] CRUD completo do catálogo: criar (individual), listar (paginado), editar, excluir — todos
      escopados por tenant via `sessao_do_tenant`/RLS, nunca contornáveis
- [ ] Upload CSV: valida cada linha, relata erro POR LINHA (nunca rejeita o arquivo inteiro por
      uma linha ruim silenciosamente nem aceita o arquivo inteiro escondendo linhas ruins),
      UPSERT por `(tenant_id, codigo_sku)`
- [ ] `/v1/tax/simulate` resolve `ncm`/`nbs` a partir de `sku` cadastrado SÓ quando ambos vierem
      ausentes do item — explícito sempre vence
- [ ] Zero regressão em `/v1/tax/simulate` para todo payload que já funciona hoje (todos os
      campos de `ncm`/`nbs` continuam funcionando exatamente como antes quando informados)

### Constraints Identified
- RLS já aplicado — toda escrita/leitura PRECISA passar por `sessao_do_tenant`, nunca uma query
  direta sem o `SET LOCAL app.tenant_id`
- Upload síncrono, escala limitada (a posição 11 assume volumes muito maiores no futuro)
- `ncm_code`/`nbs_code`: validar só FORMATO (dígitos), nunca existência em tabela oficial

### Out of Scope (Confirmed)
- Upload assíncrono/fila (posição 11 do roadmap)
- Enforcement de limite por plano de assinatura (fora de escopo do projeto até aqui)
- Validação de existência do NCM/NBS cadastrado em qualquer tabela oficial
- Histórico de alterações do catálogo

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 (todas respondidas) + 1 decisão delegada ao julgamento da sessão |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 5 de 2 |
| Duration | Sessão única, 2026-08-01 |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_API_EMPRESA_SKUS.md`

**Nota para o `/define`:** duas decisões (precedência SKU vs. `ncm`/`nbs` explícito; upsert no
upload CSV) foram tomadas por julgamento desta sessão, não por confirmação direta do usuário —
seria prudente reconfirmá-las explicitamente no início do `/define`, já que mudam o
comportamento observável da API.
