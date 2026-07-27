-- Tabela TIPI (IPI por NCM) — Decreto 11.158/2022 e atualizações.
--
-- Dado tabular determinístico, não legislação com hierarquia de artigos —
-- mesma razão pela qual SPED/IBPT ficam fora do pipeline de ingestão para o
-- Qdrant (decisão registrada no CLAUDE.md em 2026-07-25): consulta é por
-- chave exata (NCM), não semântica. Diferente do IBPT, a TIPI é decreto
-- público, sem exigir cadastro nem licenciamento — por isso entra aqui.
--
-- `nao_tributado` é campo de primeira classe, não convenção de valor: a TIPI
-- usa "NT" (não tributado) como classificação tributária real e distinta de
-- uma alíquota explícita de 0% — tratar os dois como a mesma coisa perderia
-- a distinção que a própria norma faz. `aliquota_percentual` é NULL quando
-- `nao_tributado` é true.
--
-- Sem RLS: como regras_tributarias_cache, é dado legal público, igual para
-- todos os tenants.

CREATE TABLE IF NOT EXISTS aliquotas_ipi_tipi (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncm_code              VARCHAR(10) NOT NULL UNIQUE,
    descricao             TEXT NOT NULL,
    aliquota_percentual   NUMERIC(7, 5),
    nao_tributado         BOOLEAN NOT NULL DEFAULT FALSE,
    dispositivo_legal_ref TEXT NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT aliquota_xor_nao_tributado CHECK (
        (nao_tributado AND aliquota_percentual IS NULL) OR
        (NOT nao_tributado AND aliquota_percentual IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_aliquotas_ipi_ncm ON aliquotas_ipi_tipi (ncm_code);

-- taxreformai_app só ganhou GRANT sobre as tabelas que já existiam quando a
-- migração 003 rodou (`GRANT ... ON ALL TABLES IN SCHEMA public` não é
-- retroativo). Sem este grant explícito, o papel de runtime ficaria sem
-- SELECT nesta tabela — um buraco que só apareceria quando o /simulate
-- tentasse consultar IPI por NCM, não agora. Só SELECT: a ingestão grava
-- como admin (scripts/ingerir_tipi.py), a API nunca escreve aqui.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON aliquotas_ipi_tipi TO taxreformai_app';
    END IF;
END $$;
