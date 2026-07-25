-- Privilégio mínimo para o papel com que a aplicação conecta.
--
-- Escrita originalmente para revogar SUPERUSER/BYPASSRLS/cloudsqlsuperuser de
-- `taxreformai_app` — a descoberta cara do build do schema foi que
-- superusuários do PostgreSQL ignoram Row-Level Security por completo, e o
-- container postgres:16 do CI provou isso (conectar como `postgres` real fazia
-- as três asserções de isolamento passarem falsamente).
--
-- Contra o Cloud SQL real essa migração falhava com "permission denied to
-- alter role — Only roles with the SUPERUSER attribute may change the
-- SUPERUSER attribute" (2026-07-25). Diagnóstico contra a instância real:
--
--   rolname            rolsuper  rolbypassrls
--   postgres           false     false
--   taxreformai_admin  false     false
--   taxreformai_app    false     false
--   cloudsqlsuperuser  false     false
--
-- NENHUM papel no Cloud SQL — nem `postgres` — é superusuário de verdade nem
-- tem BYPASSRLS, `cloudsqlsuperuser` inclusive. É assim desde a criação: o
-- Cloud SQL nunca concede o bit real de SUPERUSER a nenhum papel conectável,
-- diferente de uma instância PostgreSQL autogerida. A proteção que esta
-- migração tentava adicionar já é garantida pela plataforma — e é por isso
-- que tentar reforçá-la esbarra numa checagem do próprio Postgres que exige
-- ser superusuário de verdade só para confirmar o óbvio.
--
-- O que continua aqui é privilégio de OBJETO (GRANT/REVOKE), que é operação
-- diferente de atributo de papel e não tem essa restrição: a aplicação lê e
-- escreve dados, nunca altera schema.
--
-- Idempotente: pode rodar em base onde o papel ainda não existe (ambientes de
-- teste criam o próprio) sem falhar.

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA public TO taxreformai_app';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO taxreformai_app';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO taxreformai_app';

        -- Sem CREATE no schema: a aplicação não altera estrutura. Se pudesse,
        -- poderia derrubar as policies que a protegem.
        EXECUTE 'REVOKE CREATE ON SCHEMA public FROM taxreformai_app';
    END IF;
END $$;
