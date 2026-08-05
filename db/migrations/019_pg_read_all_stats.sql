-- PAINEL_OBSERVABILIDADE — sem isto, `taxreformai_app` só enxerga suas
-- PRÓPRIAS conexões em pg_stat_activity (comportamento padrão do Postgres
-- para papéis não-superusuário), tornando o cálculo de "% de max_connections
-- em uso" (Decision 1/Pattern 1 do DESIGN) subestimado — nunca veria as
-- conexões de outras sessões da própria API.
--
-- pg_read_all_stats é um papel PREDEFINIDO do Postgres (desde a versão 10),
-- não um atributo de superusuário — GRANT de papel para papel é a mesma
-- classe de operação de objeto já discutida na migração 003 (sem a
-- restrição de "só superusuário pode conceder" que bloqueou aquela).

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT pg_read_all_stats TO taxreformai_app';
    END IF;
END $$;
