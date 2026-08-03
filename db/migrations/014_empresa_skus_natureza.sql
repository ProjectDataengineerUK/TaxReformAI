-- API_EMPRESA_SKUS: primeira feature a ESCREVER em empresa_skus (schema e RLS
-- aplicados desde SCHEMA_POSTGRESQL, tabela morta até aqui). Corrige o gap
-- entre o schema (ncm_code sempre obrigatório) e o vocabulário natureza já
-- usado por ItemSimulacao (MERCADORIA | SERVICO).
--
-- DEFAULT 'MERCADORIA' no ADD COLUMN faz o Postgres backfillar toda linha
-- pré-existente atomicamente; como ncm_code já era NOT NULL antes desta
-- migração e nenhuma rota jamais escreveu nbs_code, o CHECK de exclusividade
-- abaixo é satisfeito por toda linha pré-existente sem migração de dado
-- explícita. Os dois testes de tests/test_schema_postgres.py que inserem em
-- empresa_skus sem declarar natureza continuam passando sem modificação.

ALTER TABLE empresa_skus ADD COLUMN natureza VARCHAR(10) NOT NULL DEFAULT 'MERCADORIA'
    CHECK (natureza IN ('MERCADORIA', 'SERVICO'));

ALTER TABLE empresa_skus ALTER COLUMN ncm_code DROP NOT NULL;

ALTER TABLE empresa_skus ADD CONSTRAINT empresa_skus_natureza_codigo_exclusivo CHECK (
    (natureza = 'MERCADORIA' AND ncm_code IS NOT NULL AND nbs_code IS NULL) OR
    (natureza = 'SERVICO' AND nbs_code IS NOT NULL AND ncm_code IS NULL)
);

-- GRANT já concedido pela migração 003 (privilégio mínimo do papel app cobre
-- SELECT/INSERT/UPDATE/DELETE em toda tabela de aplicação, empresa_skus
-- incluída desde a 001) — nenhum GRANT novo necessário aqui.
