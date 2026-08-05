-- PAINEL_OBSERVABILIDADE — registro de cada chamada real ao LLM
-- (classificador/extrator_regras/sintetizador), gravado best-effort por
-- orquestracao/llm/registrador.py (nunca bloqueia a resposta ao usuário —
-- Decision 4 do DESIGN).
--
-- Sem tenant_id/RLS de propósito (Decision 3 do DESIGN): é dado operacional
-- agregado do sistema inteiro, não dado de negócio por tenant — diferente de
-- toda outra tabela deste schema. Se um dia precisar de custo por tenant,
-- é uma migração aditiva, não uma reescrita.

CREATE TABLE IF NOT EXISTS uso_llm (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    no_origem       TEXT NOT NULL,
    modelo          TEXT NOT NULL,
    tokens_entrada  INT NOT NULL,
    tokens_saida    INT NOT NULL,
    sucesso         BOOLEAN NOT NULL,
    erro_detalhe    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uso_llm_created_at ON uso_llm (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_uso_llm_no_origem_created_at ON uso_llm (no_origem, created_at DESC);

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT, INSERT ON uso_llm TO taxreformai_app';
    END IF;
END $$;
