-- Privilégio mínimo para o papel com que a aplicação conecta.
--
-- Esta migração existe por causa da descoberta mais cara do build do schema:
-- superusuários do PostgreSQL IGNORAM Row-Level Security por completo, e
-- `FORCE ROW LEVEL SECURITY` só cobre o dono da tabela. Rodando os testes como
-- `postgres`, as três asserções de isolamento passaram falsamente — os tenants
-- enxergavam as linhas uns dos outros sem erro nenhum.
--
-- No Cloud SQL o usuário `taxreformai_app` é criado pelo Terraform e nasce
-- membro de `cloudsqlsuperuser`. Se ficasse assim, todo o arquivo 002 seria
-- decoração. Aqui ele é rebaixado ao que a aplicação de fato precisa: ler e
-- escrever dados, nunca alterar schema nem desligar policy.
--
-- Idempotente: pode rodar em base onde o papel ainda não existe (ambientes de
-- teste criam o próprio) sem falhar.

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        -- Tira o papel de cloudsqlsuperuser, se estiver lá. É essa herança que
        -- daria BYPASSRLS na prática.
        IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'cloudsqlsuperuser') THEN
            EXECUTE 'REVOKE cloudsqlsuperuser FROM taxreformai_app';
        END IF;

        EXECUTE 'ALTER ROLE taxreformai_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS';

        EXECUTE 'GRANT USAGE ON SCHEMA public TO taxreformai_app';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO taxreformai_app';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO taxreformai_app';

        -- Sem CREATE no schema: a aplicação não altera estrutura. Se pudesse,
        -- poderia derrubar as policies que a protegem.
        EXECUTE 'REVOKE CREATE ON SCHEMA public FROM taxreformai_app';
    END IF;
END $$;
