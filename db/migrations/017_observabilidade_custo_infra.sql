-- PAINEL_OBSERVABILIDADE — espelho diário do custo de infra, sincronizado de
-- GCP Billing Export → BigQuery por scripts/sincronizar_custo_infra.py
-- (Decision 2 do DESIGN — não existe Billing API que dê custo real por
-- serviço/dia diretamente; o mecanismo real do GCP é o export detalhado).
--
-- UNIQUE (servico, data) é a chave de upsert (staging+MERGE), mesmo padrão de
-- scripts/sincronizar_bigquery.py.

CREATE TABLE IF NOT EXISTS custo_infra_diario (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    servico         TEXT NOT NULL,
    data            DATE NOT NULL,
    custo_usd       NUMERIC(12, 4) NOT NULL CHECK (custo_usd >= 0),
    sincronizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (servico, data)
);

CREATE INDEX IF NOT EXISTS idx_custo_infra_diario_data ON custo_infra_diario (data DESC);

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON custo_infra_diario TO taxreformai_app';
    END IF;
END $$;
