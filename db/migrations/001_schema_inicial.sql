-- Schema inicial: multi-tenancy, cache de regras tributárias e audit log.
-- Base: contexto.md seção 7. Desvios deliberados documentados em
-- .claude/sdd/features/DESIGN_SCHEMA_POSTGRESQL.md.

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- Tenants. Não está no blueprint, mas a Decisão 2 (tenant_id UUID) precisa de
-- um lugar para traduzir o slug que a API usa hoje ("taxreformai-dev") no UUID
-- que o schema exige, sem quebrar o serviço em produção durante a transição.
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT NOT NULL UNIQUE,
    nome        TEXT NOT NULL,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS empresa_skus (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    codigo_sku  VARCHAR(64) NOT NULL,
    descricao   TEXT NOT NULL,
    ncm_code    VARCHAR(10) NOT NULL,
    nbs_code    VARCHAR(10),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- O SKU é a chave do cliente; repetido dentro do mesmo tenant seria
    -- ambiguidade na simulação, não dado duplicado inofensivo.
    UNIQUE (tenant_id, codigo_sku)
);

CREATE INDEX IF NOT EXISTS idx_empresa_skus_tenant ON empresa_skus (tenant_id);
CREATE INDEX IF NOT EXISTS idx_empresa_skus_ncm ON empresa_skus (tenant_id, ncm_code);

-- Cache de regras tributárias por NCM/ano.
--
-- As alíquotas são ANULÁVEIS, contra o blueprint, que as declara NOT NULL.
-- A LC 214/2025 fixa o IBS de 2027-2028 (art. 344: 0,05% estadual + 0,05%
-- municipal) mas NÃO a CBS do mesmo período (art. 347 remete à alíquota de
-- referência do art. 14, ainda não fixada). NOT NULL forçaria inventar um
-- número — o oposto do que AliquotaNaoDisponivelError existe para impedir.
-- NULL aqui significa "a lei não fixou", não "ninguém preencheu ainda", e
-- fonte_legal_* diz qual dispositivo rege cada caso.
CREATE TABLE IF NOT EXISTS regras_tributarias_cache (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncm_code            VARCHAR(10) NOT NULL,
    ano_vigencia        INT NOT NULL,
    aliquota_cbs        NUMERIC(6, 5),
    aliquota_ibs        NUMERIC(6, 5),
    aliquota_is         NUMERIC(6, 5),
    fonte_legal_cbs     TEXT,
    fonte_legal_ibs     TEXT,
    fonte_legal_is      TEXT,
    confirmado_em_lei   BOOLEAN NOT NULL DEFAULT FALSE,
    regime_especial     VARCHAR(64) NOT NULL DEFAULT 'GERAL',
    dispositivo_legal_ref TEXT NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ncm_code, ano_vigencia, regime_especial)
);

CREATE INDEX IF NOT EXISTS idx_regras_ncm_ano
    ON regras_tributarias_cache (ncm_code, ano_vigencia);

-- Trilha de auditoria. É o que sustenta "simulação 100% auditável": sem ela,
-- nenhuma resposta emitida pode ser reconstituída depois.
--
-- user_id é anulável, contra o blueprint. Não existe conceito de usuário no
-- sistema — a autenticação é chave de API -> tenant. NOT NULL obrigaria
-- inventar um UUID a cada gravação, o que é pior que registrar a ausência.
CREATE TABLE IF NOT EXISTS pareceres_audit_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id                 UUID,
    prompt_consulta         TEXT NOT NULL,
    contexto_recuperado_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload_calculo_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
    resposta_parecer_md     TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_data
    ON pareceres_audit_log (tenant_id, created_at DESC);
