# DESIGN: Schema PostgreSQL (multi-tenancy, audit log, cache de regras)

| Attribute | Value |
|-----------|-------|
| **Feature** | SCHEMA_POSTGRESQL |
| **Date** | 2026-07-25 |
| **Base** | `contexto.md`, seção 7 |
| **Fases SDD puladas** | BRAINSTORM e DEFINE — o blueprint já especifica as tabelas e as decisões abertas foram resolvidas em conversa. Refazê-los seria cerimônia sem conteúdo novo. |

---

## Por que agora

A API está no ar e **não persiste nada**. Cada simulação some ao responder. O
`pareceres_audit_log` é o que sustenta a promessa central do produto — "simulação 100%
auditável" — e hoje ela não existe: não há trilha nenhuma. A validação de tenant devolve 403
mas não registra a tentativa em lugar algum.

É também pré-requisito de SPED/IBPT, que são dados tabulares e pertencem ao
`regras_tributarias_cache`, não ao Qdrant (decisão registrada no CLAUDE.md em 2026-07-25).

---

## Decisões

### Decisão 1 — Alíquotas são NULLABLE, contra o blueprint

O blueprint declara `aliquota_cbs NUMERIC(5,4) NOT NULL`. **Não vamos seguir.**

Lendo o texto real da LC 214/2025 estabelecemos que a CBS de 2027-2028 não tem número fixado:
o art. 347 manda aplicar a alíquota de referência do art. 14 reduzida em 0,1 p.p., e essa
alíquota de referência ainda não foi fixada. O art. 344, por outro lado, fixa o IBS do mesmo
período em 0,05% estadual + 0,05% municipal.

`NOT NULL` forçaria inventar um número para a CBS — exatamente o que `RegraFiscal` se recusa a
fazer, e o que `AliquotaNaoDisponivelError` existe para impedir. Um percentual inventado num
produto de compliance fiscal é indistinguível de um correto na tela do usuário.

O schema espelha o modelo em memória: cada alíquota é anulável, com uma coluna de fonte legal
por tributo, e `confirmado_em_lei` como flag.

### Decisão 2 — `tenant_id` é UUID

O blueprint usa UUID no schema **e** no exemplo de request da seção 8.1. Hoje a API mapeia
`API_KEYS` para strings livres (`"taxreformai-dev"`).

Consequência: o secret `API_KEYS` passa a mapear chave → UUID, e a API precisa de novo deploy.
Para não quebrar o serviço que está no ar, a transição aceita os dois formatos: se o valor for
um UUID válido, usa; senão, resolve pelo slug na tabela `tenants`.

### Decisão 3 — Migrações em SQL puro, sem ORM

O projeto não tem ORM em lugar nenhum e usa `Protocol` + implementação real/fake em todas as
camadas (`RawStorage`, `LegalSource`, `TabelaAliquotas`). Introduzir SQLAlchemy/Alembic aqui
criaria um segundo estilo de acesso a dados por uma feature só.

Arquivos versionados `db/migrations/NNN_*.sql`, aplicados em ordem por um runner mínimo que
registra o que já rodou numa tabela `schema_migrations`. É o suficiente para um schema deste
tamanho e não esconde o SQL de quem precisa auditá-lo.

### Decisão 4 — Isolamento de tenant por Row-Level Security, não só por WHERE

Multi-tenancy garantida por `WHERE tenant_id = ?` depende de todo desenvolvedor lembrar do
`WHERE`. RLS do PostgreSQL move a garantia para o banco: a policy é obrigatória, e um `SELECT`
sem filtro devolve só as linhas do tenant corrente.

Custo: a conexão precisa declarar o tenant (`SET LOCAL app.tenant_id`). Ganho: um esquecimento
vira zero linhas em vez de vazamento entre clientes.

### Decisão 5 — Testes contra PostgreSQL real no CI, e Cloud SQL para produção

Não são alternativas. O CI sobe um container de serviço `postgres` — de graça, efêmero — onde
`NUMERIC(5,4)`, `JSONB`, `gen_random_uuid()` e RLS funcionam de verdade. SQLite daria confiança
falsa: não tem RLS nem JSONB.

O Cloud SQL serve a aplicação e é provisionado depois que o schema estiver construído —
provisionar antes é pagar por instância ociosa enquanto o código que a usa não existe.

---

## Schema

Três tabelas do blueprint, mais `tenants` (exigida pela Decisão 2) e `schema_migrations`
(Decisão 3).

Desvios do blueprint, todos deliberados:

| Blueprint | Aqui | Por quê |
|-----------|------|---------|
| `aliquota_* NOT NULL` | anulável + `fonte_legal_*` por tributo | Decisão 1 |
| sem tabela de tenants | `tenants (id UUID, slug TEXT)` | Decisão 2 |
| `pareceres_audit_log.user_id UUID NOT NULL` | anulável | Não existe conceito de usuário — só chave de API → tenant. `NOT NULL` obrigaria inventar um UUID |
| sem índices declarados | índices em `(tenant_id)`, `(ncm_code, ano_vigencia)` | Toda consulta filtra por tenant; o cache é lido por NCM+ano |
| sem RLS | RLS em todas as tabelas com `tenant_id` | Decisão 4 |

---

## Verificação

O que precisa ser provado contra PostgreSQL real, não revisado:

| # | Asserção | Por quê |
|---|----------|---------|
| 1 | RLS impede um tenant de ler linhas de outro, mesmo em `SELECT` sem `WHERE` | É a garantia inteira da Decisão 4 |
| 2 | Alíquota `NULL` é aceita e recuperada como `None` | Se `NOT NULL` sobreviver numa migração, o motor quebra ao gravar 2027 |
| 3 | Migrações aplicam em ordem e são idempotentes | Rodar duas vezes não pode duplicar nem falhar |
| 4 | `NUMERIC(5,4)` preserva `0.0009` sem virar float | Alíquota arredondada errado é erro de cálculo tributário |
| 5 | Audit log grava e recupera `JSONB` | É a trilha de auditoria; um JSON corrompido a inutiliza |
