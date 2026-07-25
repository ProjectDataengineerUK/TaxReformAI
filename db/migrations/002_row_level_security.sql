-- Isolamento entre tenants no banco, não na aplicação.
--
-- Multi-tenancy garantida por `WHERE tenant_id = ?` depende de todo
-- desenvolvedor lembrar do WHERE em toda consulta, para sempre. RLS move a
-- garantia para o PostgreSQL: um SELECT sem filtro devolve apenas as linhas do
-- tenant corrente, e um esquecimento vira zero linhas em vez de vazamento
-- entre clientes.
--
-- A conexão declara o tenant com `SET LOCAL app.tenant_id = '<uuid>'`, dentro
-- da transação. `current_setting(..., true)` devolve NULL em vez de erro
-- quando a variável não foi definida — e nesse caso a policy não casa com
-- linha nenhuma, que é o padrão seguro: sem tenant declarado, nada é visível.

ALTER TABLE empresa_skus ENABLE ROW LEVEL SECURITY;
ALTER TABLE pareceres_audit_log ENABLE ROW LEVEL SECURITY;

-- FORCE faz a policy valer inclusive para o dono da tabela. Sem isto, o papel
-- que roda as migrações (normalmente o dono) ignoraria o RLS em silêncio — e é
-- justamente com ele que a aplicação costuma acabar conectando.
ALTER TABLE empresa_skus FORCE ROW LEVEL SECURITY;
ALTER TABLE pareceres_audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON empresa_skus;
CREATE POLICY tenant_isolation ON empresa_skus
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid);

DROP POLICY IF EXISTS tenant_isolation ON pareceres_audit_log;
CREATE POLICY tenant_isolation ON pareceres_audit_log
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid);

-- ATENÇÃO: SUPERUSUÁRIOS DO POSTGRESQL IGNORAM RLS POR COMPLETO. `FORCE ROW
-- LEVEL SECURITY` acima resolve só o caso do dono da tabela; um papel
-- superusuário atravessa toda policy sem erro nenhum. É fato genérico do
-- PostgreSQL, comprovado contra o container postgres:16 do CI (conectar como
-- `postgres` ali produziu 3 falsos verdes nos testes de isolamento).
--
-- NÃO se aplica ao Cloud SQL: diagnosticado contra a instância real em
-- 2026-07-25, nenhum papel — nem `postgres` — tem rolsuper=true ou
-- rolbypassrls=true lá; o Cloud SQL nunca concede esse bit a papel nenhum.
-- A tentativa de "reforçar" isso na migração 003 (ALTER ROLE ... NOSUPERUSER)
-- falhava com "permission denied to alter role": só quem já é superusuário
-- pode tocar esse atributo, então nem confirmar o óbvio era possível — ver
-- histórico de 003_papel_da_aplicacao.sql.
--
-- Os testes seguem conectando com um papel não-superusuário criado só para
-- eles, porque continua sendo a forma correta de testar RLS no CI (onde o
-- container É um PostgreSQL genérico, sujeito à regra geral).

-- regras_tributarias_cache NÃO tem RLS de propósito: é dado legal público,
-- igual para todos os tenants. Aplicar isolamento ali obrigaria duplicar a
-- mesma alíquota por cliente, o que é errado e caro.
