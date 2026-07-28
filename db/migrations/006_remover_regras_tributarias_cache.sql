-- Remove `regras_tributarias_cache` — código morto de schema (Decisão 12).
--
-- A tabela existe desde a migração 001 sem nenhum consumidor, sem nenhuma linha
-- gravada e sem script de carga. O achado 2 da auditoria pedia decisão explícita
-- entre substituir, adaptar ou remover; a resposta é remover, porque a FORMA
-- dela está errada para o dado real, não só incompleta:
--
--   * guarda alíquotas ABSOLUTAS (aliquota_cbs/ibs/is) quando os regimes
--     diferenciados da LCP 214/2025 são REDUÇÕES PERCENTUAIS sobre uma alíquota
--     de referência;
--   * `ncm_code` é único por linha, e um item do Anexo I tem até 18 códigos;
--   * não representa exceção (os itens 19 e 20 do Anexo I têm 19 códigos
--     excluídos);
--   * não tem `nbs_code` para os Anexos de serviço.
--
-- O papel que ela pretendia cumprir passa a ser de `cesta_basica_anexo_i` e
-- `cesta_basica_anexo_i_ncm` (migração 005), com a forma que o texto legal
-- exigiu. Manter a tabela vazia "para os outros Anexos" seria trocar código
-- morto por schema morto — e convidar alguém a populá-la com a forma errada.
--
-- Separada da 005 de propósito: reverter a remoção não deve implicar reverter o
-- Anexo I, e cada migração faz uma coisa só.

-- A afirmação "a tabela nunca teve linhas" vira VERIFICAÇÃO, não crença. Se
-- alguém tiver gravado algo entre o build e a aplicação desta migração, o
-- EXCEPTION aborta a transação inteira (db/migrador.py roda cada migração na
-- sua própria transação) e nada é perdido.
DO $$
BEGIN
    IF to_regclass('public.regras_tributarias_cache') IS NOT NULL
       AND EXISTS (SELECT 1 FROM regras_tributarias_cache) THEN
        RAISE EXCEPTION 'regras_tributarias_cache não está vazia: DROP abortado';
    END IF;
END $$;

DROP TABLE IF EXISTS regras_tributarias_cache;
