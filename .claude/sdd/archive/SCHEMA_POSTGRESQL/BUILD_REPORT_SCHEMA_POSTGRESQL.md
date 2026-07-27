# BUILD REPORT: Schema PostgreSQL + Regime Vigente + Cloud SQL Real

> Relatório de implementação do schema da seção 7, do regime tributário vigente
> (PIS/COFINS/ICMS interestadual) e da conexão real da API ao Cloud SQL

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SCHEMA_POSTGRESQL (com escopo estendido para regime vigente) |
| **Date** | 2026-07-25 a 2026-07-27 |
| **DESIGN** | [DESIGN_SCHEMA_POSTGRESQL.md](../features/DESIGN_SCHEMA_POSTGRESQL.md) |
| **Fases SDD puladas** | BRAINSTORM e DEFINE — o blueprint (seção 7) já especifica as tabelas e as decisões abertas foram resolvidas em conversa direta com o usuário |

---

## Summary

Três entregas amarradas por uma pergunta do usuário — *"por se tratar de transição, não precisa documentação e alíquotas vigentes?"* — que expôs uma lacuna real: a API simulava CBS/IBS/IS isoladamente, e para 2026 isso é **materialmente enganoso**: o art. 348 da LCP 214/2025 torna o valor recolhido compensável com PIS/COFINS do mesmo período, e sem calcular PIS/COFINS a compensação não tinha contra o que ser lida.

1. **Schema PostgreSQL** (multi-tenancy via RLS, audit log, cache de regras) — seção 7 do blueprint, com dois desvios deliberados (alíquotas anuláveis, `tenant_id` UUID).
2. **Regime tributário vigente** (PIS/COFINS, ICMS interestadual) — todas as alíquotas lidas do texto oficial do Planalto/LexML, nunca de memória.
3. **Cloud SQL real, provisionado e conectado** — a API em produção agora grava audit log de verdade, provado por uma consulta separada ao banco depois do smoke test.

---

## O que foi construído

### Schema (db/)

| Arquivo | Conteúdo |
|---------|----------|
| `db/migrations/001_schema_inicial.sql` | `tenants`, `empresa_skus`, `regras_tributarias_cache` (alíquotas anuláveis), `pareceres_audit_log` |
| `db/migrations/002_row_level_security.sql` | RLS + FORCE em `empresa_skus`/`pareceres_audit_log`, policy por `app.tenant_id` |
| `db/migrations/003_papel_da_aplicacao.sql` | Privilégio mínimo do papel `taxreformai_app` (GRANT/REVOKE de objeto, não de atributo — ver Blockers) |
| `db/migrador.py` | Runner de migrações idempotente, sem ORM |
| `db/repositorio.py` | `sessao_do_tenant`, `registrar_parecer`, `resolver_tenant`, `buscar_regra_cache` |

### Regime vigente (motor_calculo/regime_atual.py)

Todas as alíquotas conferidas contra o texto oficial, não de memória:

| Tributo | Alíquota | Fonte |
|---------|----------|-------|
| PIS não-cumulativo | 1,65% | Lei 10.637/2002, art. 2º |
| COFINS não-cumulativo | 7,6% | Lei 10.833/2003, art. 2º |
| PIS cumulativo | 0,65% | Lei 9.715/1998, art. 8º, I |
| COFINS cumulativo | 3% | Lei 9.718/1998, art. 8º |
| ICMS interestadual geral | 12% | Resolução do Senado 22/1989, art. 1º |
| ICMS interestadual reduzido | 7% | Resolução do Senado 22/1989, art. 1º, § único |
| ICMS interestadual, bem importado | 4% | Resolução do Senado 13/2012, art. 1º |

Deliberadamente fora de escopo, mesma decisão já registrada para SPED/IBPT: **IPI** (tabela TIPI por NCM, milhares de linhas — dado tabular, não alíquota codificável) e **ICMS interno/ISS** (27 estados e milhares de municípios, sem norma única para citar).

### API (`api/`)

- `regime_apuracao` **opcional, sem default** no payload — `None` significa "não informado", nunca "presume-se X".
- `EscopoSimulacao`/`Compensacao`/`RegimeVigenteResumo` na resposta: o que foi calculado, o que não foi, e por quê.
- `api/db.py` + `api/audit.py`: pool de conexão via `Depends` (mesmo padrão de `get_settings`), audit log que **nunca** propaga exceção — falha de banco não pode derrubar um cálculo tributário.

### Infraestrutura (Terraform + workflows)

- Cloud SQL `taxreformai-pg` (PostgreSQL 16, `db-f1-micro`, backup diário, `deletion_protection`).
- Dois papéis (`taxreformai_admin`, `taxreformai_app`), senhas no Secret Manager.
- `migrar_banco.yml`: aplica migrações via Cloud SQL Auth Proxy, popula `tenants`, prova RLS contra o banco real (não só infere).
- `deploy.yml`: `--add-cloudsql-instances` + `--set-secrets`, e um passo pós-smoke-test que confirma, via consulta separada, que o audit log foi gravado.

---

## Verification Results

```text
ruff check .   → All checks passed (select explícito desde esta feature)
pytest         → 141 passed, 1 skipped (schema só roda com Postgres real)
CI (Postgres real, container de serviço) → 129+ testes incluindo RLS
```

### Contra infraestrutura real

| Verificação | Resultado |
|-------------|-----------|
| Migrações aplicadas no Cloud SQL real | ✅ `migrar_banco.yml`, run verde |
| RLS isola tenants no Cloud SQL real | ✅ `verificar_rls_producao.py` — não só diagnóstico, prova com 2 tenants reais |
| API deployada conecta ao Cloud SQL | ✅ smoke test `POST /v1/tax/simulate` → 200 |
| Audit log gravado pelo serviço real | ✅ parecer `fdd34fc7-4acd-4b81-a3b6-1dc1fbec079b`, confirmado por consulta separada |

---

## Issues Encontrados (todos só apareceram contra infraestrutura real)

| # | Issue | Onde apareceu | Resolução |
|---|-------|----------------|-----------|
| 1 | `SET LOCAL app.tenant_id = %s` — `SET` é comando utilitário, não aceita parâmetro vinculado | CI, testes de schema | `set_config('app.tenant_id', %s, true)` |
| 2 | Testar RLS como superusuário dá falso-positivo (superusuário ignora RLS) | CI, container `postgres:16` | Testes conectam com papel não-superusuário criado só para eles |
| 3 | Migração 003 tentava `ALTER ROLE ... NOSUPERUSER` — impossível no Cloud SQL: nenhum papel lá tem `rolsuper=true`, nem `postgres` | `migrar_banco.yml` no Cloud SQL real | Diagnóstico empírico (`rolsuper=false` para todos); linhas de `ALTER ROLE`/`REVOKE cloudsqlsuperuser` removidas — a proteção já é garantida pela plataforma |
| 4 | SA do Terraform sem `cloudsql.admin`/`secretmanager.admin` | `terraform.yml apply` | Concedido via `gcloud` (ação administrativa pontual, documentada) |
| 5 | `api/Dockerfile` não copiava `db/` | Primeiro deploy real com API ligada ao banco — 500 em `/simulate` | `COPY db/ ./db/` |
| 6 | SA de deploy sem `cloudsql.client` | `deploy.yml`, passo de verificação | Concedido via Terraform |
| 7 | SA de deploy sem acesso ao secret de senha do Postgres | `deploy.yml`, mesmo passo | Concedido — usando a senha do **app**, não do admin (least privilege: a verificação só faz SELECT) |
| 8 | Runner do `deploy.yml` sem Python/`psycopg` | `deploy.yml`, mesmo passo | `actions/setup-python@v5` + `pip install psycopg[binary]` (não `-r requirements.txt` inteiro) |

Os itens 5-8 só apareceram na primeira execução real do deploy com o banco conectado — nenhum teste local ou de CI os teria pego, porque dependem da imagem Docker real e das permissões IAM reais entre SAs distintas.

---

## Deviations from Design

| Deviation | Reason |
|-----------|--------|
| Escopo estendido para regime vigente (não estava no DESIGN original) | Pergunta do usuário expôs que a simulação de 2026 era materialmente enganosa sem PIS/COFINS calculado |
| Migração 003 perdeu as linhas de `ALTER ROLE`/`REVOKE cloudsqlsuperuser` | Impossíveis de executar no Cloud SQL e desnecessárias — a plataforma nunca concede SUPERUSER a papel nenhum |
| Verificação do audit log usa a senha do papel `app`, não `admin` | Descoberto durante o debug: a tarefa só precisa de SELECT, então least privilege é a escolha certa, não só a mais fácil |

---

## Final Status

### Overall: ✅ COMPLETE — verificado contra infraestrutura real de ponta a ponta

- [x] Schema aplicado no Cloud SQL real
- [x] RLS provado contra o banco real (não só inferido)
- [x] Regime vigente com todas as alíquotas citáveis por artigo
- [x] API deployada conectada, audit log gravando de verdade
- [x] CI verde com Postgres real (container de serviço)

## Recomendação

Pronto para `/ship`.
