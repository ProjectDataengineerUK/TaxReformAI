-- PAINEL_OBSERVABILIDADE — heartbeat de jobs agendados (hoje: sync do
-- BigQuery e sync de custo de infra). O painel deriva o status do sync do
-- BigQuery (verde/amarelo/vermelho) da última linha por `job`, comparando
-- com a janela esperada (Decision 1 do DESIGN) — sem isto não havia nenhum
-- registro consultável de "quando rodou pela última vez e se deu certo".

CREATE TABLE IF NOT EXISTS observabilidade_execucoes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job          TEXT NOT NULL,
    executado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sucesso      BOOLEAN NOT NULL,
    detalhe      TEXT
);

CREATE INDEX IF NOT EXISTS idx_observabilidade_execucoes_job
    ON observabilidade_execucoes (job, executado_em DESC);

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT, INSERT ON observabilidade_execucoes TO taxreformai_app';
    END IF;
END $$;
