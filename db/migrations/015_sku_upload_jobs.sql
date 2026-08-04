-- FILA_ASSINCRONA_CELERY_REDIS (nome do roadmap preservado; mecanismo real é
-- Cloud Tasks, não Celery/Redis — ver DEFINE_FILA_ASSINCRONA_CELERY_REDIS.md).
--
-- Status de job de upload assíncrono de SKUs. Sem Redis (rejeitado no
-- /brainstorm por exigir VPC), o status precisa de um lugar persistente e
-- isolado por tenant — mesma disciplina de RLS já auditada em
-- empresa_skus/pareceres_audit_log, não um mecanismo novo.

CREATE TABLE IF NOT EXISTS sku_upload_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE', 'PROCESSANDO', 'CONCLUIDO', 'ERRO')),
    gcs_uri_arquivo TEXT NOT NULL,
    resultado_json  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sku_upload_jobs_tenant
    ON sku_upload_jobs (tenant_id, created_at DESC);

ALTER TABLE sku_upload_jobs ENABLE ROW LEVEL SECURITY;

-- FORCE: mesma razão da migração 002 — sem isto, o papel dono da tabela
-- (quem roda as migrações) ignoraria a RLS em silêncio.
ALTER TABLE sku_upload_jobs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON sku_upload_jobs;
CREATE POLICY tenant_isolation ON sku_upload_jobs
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::uuid);

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON sku_upload_jobs TO taxreformai_app';
    END IF;
END $$;
