# DEFINE: API de Catálogo de SKUs (empresa_skus)

> CRUD completo + upload CSV do catálogo SKU→NCM/NBS por tenant, mais o wiring de
> `/v1/tax/simulate` para resolver `ncm`/`nbs` a partir do `sku` cadastrado quando ambos vierem
> ausentes do item — o primeiro consumidor real da tabela `empresa_skus`, aplicada desde
> `SCHEMA_POSTGRESQL` mas nunca lida nem escrita por nenhuma rota até aqui.
>
> **Posição na sequência:** 3 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).
> Primeira feature da "primeira leva" retomada depois da "segunda leva" (posições 12-17) ter sido
> concluída em 2026-08-01. Sem dependência técnica de nenhuma feature anterior.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_EMPRESA_SKUS |
| **Date** | 2026-08-01 |
| **Author** | define-agent |
| **Status** | ✅ Shipado 2026-08-03 (ver `SHIPPED_2026-08-03.md`) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

A tabela `empresa_skus` (catálogo de SKU→NCM/NBS por tenant, com RLS multi-tenant já aplicado)
existe no Cloud SQL desde `SCHEMA_POSTGRESQL` (2026-07-27), mas nenhuma rota da API a lê ou
escreve — é uma tabela morta. Além disso, o schema atual força `ncm_code NOT NULL` em TODA SKU,
mesmo de serviço, um gap frente ao vocabulário `natureza: MERCADORIA | SERVICO` que
`ItemSimulacao` (`/v1/tax/simulate`) já usa desde `ANEXOS_REDUCAO_PERCENTUAL_NCM`. Sem esta
feature, um cliente com centenas ou milhares de SKUs precisa reenviar `ncm`/`nbs` explicitamente
em toda simulação, sem nenhum cadastro reutilizável — o oposto do fluxo real de um ERP (cadastra
o produto uma vez, simula muitas vezes).

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Departamento fiscal / controller de um tenant | Consumidor direto do CRUD e do upload CSV | Precisa manter um catálogo de produtos/serviços por SKU sem reenviar NCM/NBS em toda chamada de `/v1/tax/simulate` — hoje não existe onde cadastrar isso |
| Integração de ERP (Enterprise) | Consumidor de `/v1/tax/simulate` via API dedicada | Já mantém um cadastro de SKUs no próprio ERP; precisa que o simulador aceite `sku` como referência suficiente, sem duplicar NCM/NBS em cada chamada quando o cadastro já existe no TaxReform AI |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Migração nova (`014_*.sql`) adiciona `natureza` (`MERCADORIA`/`SERVICO`, mesmo vocabulário de `ItemSimulacao`) a `empresa_skus`, torna `ncm_code` `NULLABLE`, e um `CHECK` garante exatamente um dos dois (`ncm_code` XOR `nbs_code`) preenchido conforme `natureza` — nunca os dois, nunca nenhum |
| **MUST** | CRUD completo, escopado por tenant via `sessao_do_tenant`/RLS (nunca uma query direta sem `SET LOCAL app.tenant_id`): criar (POST, 409 em `codigo_sku` duplicado), listar (GET, paginado), consultar um (GET por `codigo_sku`), editar (PATCH), excluir (DELETE) |
| **MUST** | Upload CSV síncrono (`POST /v1/tax/skus/upload`, multipart): valida CADA linha independentemente, relata erro POR LINHA (nunca rejeita o arquivo inteiro por uma linha ruim, nunca aceita silenciando linhas ruins); faz UPSERT por `(tenant_id, codigo_sku)` — reenviar a mesma planilha atualiza, não quebra |
| **MUST** | Limite de linhas no upload CSV (ex. 10.000, mesmo teto citado no plano Business do `contexto.md`) — acima disso, 422 com mensagem explícita, nunca um upload parcial silencioso; volumes maiores ficam para a posição 11 (`FILA_ASSINCRONA_CELERY_REDIS`, ainda não construída) |
| **MUST** | `ItemSimulacao.ncm` passa a ser OPCIONAL (`str \| None = None`, hoje obrigatório) — campo aditivo-seguro: todo payload existente que já informa `ncm` continua funcionando IDENTICAMENTE |
| **MUST** | `/v1/tax/simulate` resolve `ncm`/`nbs` a partir do `sku` do item (já campo obrigatório de `ItemSimulacao`) SÓ quando `ncm` E `nbs` vierem ambos ausentes do item — valor explícito no payload SEMPRE vence sobre o catálogo, nunca é sobrescrito |
| **MUST** | Item cujo `sku` não está cadastrado E que não informou `ncm`/`nbs` explícito → 422 claro ("SKU não cadastrado; informe ncm/nbs ou cadastre o SKU antes"), nunca uma simulação com NCM vazio/inventado |
| **MUST** | Validação de FORMATO (dígitos), nunca de EXISTÊNCIA em tabela oficial — `ncm_code`/`nbs_code` cadastrados usam os validadores já existentes (`api/ncm.py::digitos_ncm`, `api/nbs.py::digitos_nbs`), mas o catálogo pode conter um código que ainda não está em nenhuma tabela oficial ingerida (TIPI, Anexos) — isso não é erro de cadastro |
| **MUST** | Zero regressão: toda a suíte de testes atual (551 testes) e todo payload de `/v1/tax/simulate` que já funciona hoje continuam funcionando exatamente como antes |
| **SHOULD** | Resposta do upload CSV lista, por linha, o resultado (`CRIADO`/`ATUALIZADO`/`ERRO` + motivo) — não só um total agregado |
| **COULD** | Endpoint de contagem total de SKUs cadastrados por tenant (`GET /v1/tax/skus/contagem` ou campo no envelope de listagem) — útil para UI, não pedido explicitamente |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Decisões Herdadas do `/brainstorm` (duas tomadas por julgamento, não por confirmação direta)

O `BRAINSTORM_API_EMPRESA_SKUS.md` sinalizou explicitamente duas decisões tomadas por julgamento
desta sessão (o usuário pediu "a melhor opção" em vez de responder a pergunta de múltipla
escolha). Ambas são reafirmadas aqui como requisito, com o motivo, para que fiquem sujeitas a
revisão explícita antes do `/build` se o usuário discordar:

1. **Precedência**: `ncm`/`nbs` explícito no payload de `/v1/tax/simulate` sempre vence sobre o
   catálogo. Motivo: mesma disciplina declaratória já usada em TODO campo opcional deste projeto
   (`comprador_tipo`, `bem_importado`, `embalagem_primaria_consumidor_final`, `conteudo_nacional_
   majoritario` — nenhum deles jamais sobrescreve um valor que o cliente informou).
2. **Upsert no upload CSV**: reenviar uma planilha com o mesmo `codigo_sku` ATUALIZA o registro
   (não gera erro de duplicata); só o `POST` individual (criação avulsa) rejeita duplicata com
   409. Motivo: reenviar a mesma planilha (com correções) é o fluxo real mais comum de upload —
   forçar erro em toda linha repetida tornaria a feature inutilizável na prática.

---

## Success Criteria

- [ ] Migração 014 aplicada: `natureza` existe, `ncm_code` é `NULLABLE`, `CHECK` de exclusividade
      ativo, sem quebrar nenhuma linha pré-existente (se houver)
- [ ] `POST /v1/tax/skus` cria 1 SKU, 409 em `codigo_sku` duplicado dentro do mesmo tenant
- [ ] `GET /v1/tax/skus` lista paginado, escopado por RLS — tenant A nunca vê SKU de tenant B
- [ ] `GET /v1/tax/skus/{codigo_sku}` retorna 1 SKU ou 404 (inclusive se pertence a outro tenant —
      nunca vaza existência cross-tenant via 403 vs. 404 diferenciado)
- [ ] `PATCH /v1/tax/skus/{codigo_sku}` edita campos parciais
- [ ] `DELETE /v1/tax/skus/{codigo_sku}` remove; GET subsequente 404
- [ ] `POST /v1/tax/skus/upload` (CSV): upsert por linha, relatório por linha, rejeita acima do
      teto de linhas, nunca falha silenciosamente uma linha só
- [ ] `ItemSimulacao.ncm` opcional; todo payload existente com `ncm` explícito idêntico a antes
- [ ] `/v1/tax/simulate` resolve `ncm`/`nbs` do catálogo só quando ambos ausentes; explícito
      sempre vence; SKU não cadastrado sem `ncm`/`nbs` explícito → 422 claro
- [ ] Zero regressão: 551 testes existentes continuam passando

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Criar SKU de mercadoria | `codigo_sku` novo, `natureza=MERCADORIA`, `ncm_code` válido, sem `nbs_code` | `POST /v1/tax/skus` | 201; SKU retornado com `id`, `created_at` |
| AT-002 | Criar SKU de serviço | `natureza=SERVICO`, `nbs_code` válido, sem `ncm_code` | `POST /v1/tax/skus` | 201 |
| AT-003 | NCM e NBS juntos — rejeitado | `natureza=MERCADORIA`, `ncm_code` E `nbs_code` preenchidos | `POST /v1/tax/skus` | 422 — exclusividade violada |
| AT-004 | Nem NCM nem NBS — rejeitado | `natureza=MERCADORIA`, nem `ncm_code` nem `nbs_code` | `POST /v1/tax/skus` | 422 |
| AT-005 | Duplicata — rejeitada | `codigo_sku` já cadastrado no mesmo tenant | `POST /v1/tax/skus` | 409 |
| AT-006 | Listagem isolada por tenant | Tenant A tem 3 SKUs, tenant B tem 2 | `GET /v1/tax/skus` autenticado como tenant A | 200; só os 3 SKUs de A, nunca os de B |
| AT-007 | Consulta individual, SKU de outro tenant | `codigo_sku` existe, mas pertence a outro tenant | `GET /v1/tax/skus/{codigo_sku}` | 404 (nunca 403 — não confirma nem nega existência para quem não é dono) |
| AT-008 | Edição parcial | SKU existente | `PATCH /v1/tax/skus/{codigo_sku}` com só `descricao` | 200; só `descricao` muda, resto preservado |
| AT-009 | Exclusão | SKU existente | `DELETE` depois `GET` | 204 na exclusão; 404 na consulta seguinte |
| AT-010 | Upload CSV válido | Arquivo com 3 linhas válidas, `codigo_sku` novos | `POST /v1/tax/skus/upload` | 200; relatório com 3 `CRIADO` |
| AT-011 | Upload CSV upsert | Arquivo reenviado com 1 `codigo_sku` já existente (dado diferente) | `POST /v1/tax/skus/upload` | 200; aquela linha reporta `ATUALIZADO`, dado sobrescrito |
| AT-012 | Upload CSV parcialmente inválido | Arquivo com 2 linhas válidas + 1 linha com `ncm_code` malformado | `POST /v1/tax/skus/upload` | 200; 2 `CRIADO`/`ATUALIZADO` + 1 `ERRO` com motivo — nunca todo o arquivo rejeitado por 1 linha |
| AT-013 | Upload CSV acima do teto de linhas | Arquivo com mais linhas que o limite configurado | `POST /v1/tax/skus/upload` | 422, nenhuma linha processada, mensagem cita o limite |
| AT-014 | `/v1/tax/simulate` resolve do catálogo | Item com `sku` cadastrado (mercadoria), sem `ncm` no payload | `POST /v1/tax/simulate` | 200; usa o `ncm_code` do catálogo, resposta cita a origem (catálogo, não o payload) |
| AT-015 | `/v1/tax/simulate` — explícito vence | Item com `sku` cadastrado E `ncm` explícito DIFERENTE do catálogo | `POST /v1/tax/simulate` | 200; usa o `ncm` do PAYLOAD, catálogo ignorado |
| AT-016 | `/v1/tax/simulate` — SKU não cadastrado, sem `ncm`/`nbs` | Item com `sku` desconhecido, sem `ncm` nem `nbs` | `POST /v1/tax/simulate` | 422, mensagem clara — nunca simula com NCM vazio |
| AT-017 | Zero regressão | Qualquer payload de `/v1/tax/simulate` já testado antes desta feature, com `ncm` explícito | `POST /v1/tax/simulate` | Resposta idêntica à de antes da feature |

---

## Out of Scope

- **Upload assíncrono / fila (Celery/Redis) para 50.000+ SKUs** — posição 11 do roadmap
  (`FILA_ASSINCRONA_CELERY_REDIS`), feature própria, ainda não construída.
- **Enforcement de limite de SKUs por plano de assinatura** (Professional/Business/Enterprise) —
  seção 9 do blueprint (modelo de negócio/pricing/billing) permanece fora de escopo do projeto
  (Achado 13 do roadmap).
- **Validação de que o NCM/NBS cadastrado EXISTE em alguma tabela oficial** (TIPI, Anexos de
  redução) — só formato é validado; o catálogo é do PRÓPRIO cliente, pode conter código ainda
  não ingerido em nenhuma tabela oficial.
- **Histórico de alterações do catálogo (audit trail por SKU)** — não pedido; diferente do audit
  log de `/v1/tax/simulate`/`/v1/tax/query`, que já existe e não muda com esta feature.
- **Endpoint de contagem/dashboard agregado** — fora do MUST, ver Goals (COULD).

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Toda escrita/leitura de `empresa_skus` PRECISA passar por `sessao_do_tenant` (RLS) — nunca uma query direta sem `SET LOCAL app.tenant_id` | Reaproveita 100% o utilitário já existente em `db/repositorio.py`; nenhuma exceção aceitável |
| Technical | `ItemSimulacao.ncm` vira opcional — mudança de contrato ADITIVA (payload existente não muda de comportamento), mas o TIPO do campo muda (`str` → `str \| None`) | `/design` decide onde a resolução do catálogo entra no fluxo de `api/routers/simulate.py` — antes ou dentro do laço por item |
| Technical | Upload CSV é a primeira feature de parsing de ARQUIVO do projeto — precisa de `python-multipart` (dependência nova para o FastAPI aceitar `UploadFile`) | `/design` decide se usa `csv` da stdlib (recomendado, sem dependência nova) ou uma lib de terceiros |
| Legal | Nenhuma — primeira feature do projeto sem nenhuma verificação de fonte primária legal | N/A |
| Business | Teto de linhas do upload CSV (sugestão: 10.000, mesmo número do plano Business no blueprint) não é imposto por lógica de negócio/plano — é só um limite técnico de segurança/UX desta versão síncrona | `/design` confirma o número exato |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Router novo (`api/routers/empresa_skus.py`), schemas novos (`api/schemas_empresa_skus.py`), migração nova (`db/migrations/014_*.sql`), funções novas em `db/repositorio.py`, modificação em `api/routers/simulate.py` + `api/schemas_simulate.py` | Primeira feature CRUD do projeto — mas toda a fundação de RLS/multi-tenancy já existe desde `SCHEMA_POSTGRESQL` |
| **KB Domains** | `database-reviewer` (migração + CRUD com RLS), `python-developer`, `security-reviewer` (multi-tenancy é dado sensível — vazamento cross-tenant é o risco central desta feature) | Primeira feature desde `ORQUESTRACAO_MULTIAGENTE` a merecer revisão de segurança dedicada, por tocar RLS diretamente em CRUD (não só leitura de tabela de referência pública) |
| **IaC Impact** | Nova migração Postgres via `migrar_banco.yml` (mesmo fluxo de sempre); nenhuma mudança de Terraform | Primeira migração desde a 013 |

**Why This Matters:**

- **Location** → Diferente de toda feature de Anexo (leitura de tabela pública, sem tenant), esta
  é a primeira feature CRUD com ESCRITA por tenant desde `SCHEMA_POSTGRESQL` — o risco de
  vazamento cross-tenant é real e novo (RLS cobre `SELECT`/`INSERT`/`UPDATE`/`DELETE` igualmente,
  mas o `/design` precisa provar isso com teste, não presumir).
- **KB Domains** → `security-reviewer` deveria revisar antes do `/ship`, dado que é a primeira
  feature onde um bug de isolamento afetaria dados que o CLIENTE cadastrou (não legislação
  pública).

---

## Data Contract

### Source Inventory

Não aplicável — esta feature não depende de nenhuma fonte de dado externa/legal. O "dado" é o
catálogo que o próprio tenant cadastra.

### Schema Contract

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| `empresa_skus.natureza` | `MERCADORIA` \| `SERVICO`, mesmo vocabulário de `ItemSimulacao.natureza` | Sim |
| `empresa_skus.ncm_code` | `NULLABLE` (era `NOT NULL`) | Sim |
| `CHECK` de exclusividade | Exatamente um de `ncm_code`/`nbs_code` preenchido, conforme `natureza` | Sim |
| Endpoint de upload | `multipart/form-data`, um arquivo `.csv` | Sim |
| Colunas do CSV | `codigo_sku`, `descricao`, `natureza`, `ncm_code`, `nbs_code` (cabeçalho obrigatório, mesma nomenclatura da API) | Sim |

### Freshness SLAs

Não aplicável — dado do cliente, sem cláusula de revisão periódica.

### Completeness Metrics

Não aplicável — não há um "total esperado" de SKUs a verificar contra fonte externa (diferente
de toda feature de Anexo legal).

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `sessao_do_tenant`/`resolver_tenant` (já existentes) cobrem o caso de escrita (`INSERT`/`UPDATE`/`DELETE`) tão bem quanto o de leitura já usado por `api/audit.py` | Se não cobrirem, precisaria de um mecanismo novo de RLS para escrita | [ ] A confirmar no `/design` — a policy já usa `USING`+`WITH CHECK`, então a expectativa é que cubra, mas nunca testado com INSERT/UPDATE/DELETE reais neste projeto até aqui |
| A-002 | Precedência (explícito vence sobre catálogo) é o comportamento que o usuário quer | Se o usuário preferir o catálogo sempre vencer, seria uma mudança de comportamento observável | [ ] Tomada por julgamento no `/brainstorm`, não confirmada diretamente — ver seção "Decisões Herdadas" acima |
| A-003 | Upsert no upload CSV (nunca erro de duplicata) é o comportamento que o usuário quer | Se o usuário preferir que duplicata seja erro também no upload, mudaria o contrato do endpoint | [ ] Tomada por julgamento no `/brainstorm`, não confirmada diretamente — ver seção "Decisões Herdadas" acima |
| A-004 | Teto de 10.000 linhas no upload CSV é adequado | Se o cliente típico precisar de mais, o teto frustraria o caso de uso antes da posição 11 existir | [x] Baseado no número já citado no blueprint (`contexto.md`, plano Business) — não inventado |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Frase clara, cita o gap real (`natureza` ausente) e a tabela morta |
| Users | 3 | Dois usuários com pain points específicos e diferenciados |
| Goals | 3 | MoSCoW explícito; as duas decisões de julgamento são reafirmadas como requisito, não escondidas |
| Success | 3 | Critérios testáveis e numéricos (17 acceptance tests) |
| Scope | 2 | Duas assumptions (A-002, A-003) ficam pendentes de confirmação DIRETA do usuário — corretas por não esconder a incerteza, mas reduzem a nota porque não foram fechadas por resposta explícita |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma bloqueia o `/design`:

1. **Confirmação direta das Decisões Herdadas (A-002, A-003)** — o usuário pode revisar e
   corrigir a qualquer momento; até lá, o `/design`/`/build` seguem com o comportamento
   documentado acima.
2. **Nome exato dos endpoints** (`/v1/tax/skus` vs. outro prefixo) — decisão do `/design`.
3. **Mecanismo exato de paginação** (`page`/`page_size` vs. `limit`/`offset`) — decisão do
   `/design`; primeira feature do projeto com listagem, sem precedente a seguir.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-01 | define-agent | Versão inicial, extraída de `BRAINSTORM_API_EMPRESA_SKUS.md`. Reafirma as duas decisões tomadas por julgamento no brainstorm (precedência SKU vs. explícito; upsert no upload) como requisito explícito, com as duas marcadas como não confirmadas diretamente pelo usuário (A-002, A-003) — reduz a nota de Scope para 2/3, mas não bloqueia o avanço. Primeira feature do projeto identificada como merecedora de `security-reviewer` dedicado antes do `/ship`, por ser a primeira com escrita multi-tenant desde `SCHEMA_POSTGRESQL`. |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_API_EMPRESA_SKUS.md`
