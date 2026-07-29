-- Generaliza o schema do Anexo I para os 4 Anexos de REDUÇÃO A ZERO da
-- LCP 214/2025: I (art. 125), XII (art. 144), XIII (art. 145) e XV (art. 148).
--
-- Nada de dado é reescrito aqui: as 26 linhas de item e as 95 de prefixo do
-- Anexo I ganham colunas com DEFAULT que é verdade sobre elas, e os defaults
-- caem em seguida para não valerem sobre as próximas. O seed dos 3 Anexos
-- novos é a migração 008 — esta migração só muda a FORMA.
--
-- ALTER TABLE ... RENAME preserva dados, índices e PRIVILÉGIOS; o GRANT do
-- final é redundante de propósito (custo zero, torna a migração autocontida).
--
-- O rename não é cosmético: um tomógrafo gravado numa tabela chamada
-- `cesta_basica_anexo_i` é uma afirmação falsa dentro de um produto cujo valor
-- inteiro é auditabilidade — e a migração é o documento de auditoria.

ALTER TABLE cesta_basica_anexo_i     RENAME TO anexos_reducao_zero;
ALTER TABLE cesta_basica_anexo_i_ncm RENAME TO anexos_reducao_zero_ncm;
ALTER INDEX idx_cesta_basica_prefixo RENAME TO idx_anexos_reducao_zero_prefixo;

-- 1) Colunas novas. 'I'/1/0 descrevem o conteúdo atual, não uma regra futura.
ALTER TABLE anexos_reducao_zero
    ADD COLUMN anexo       VARCHAR(4) NOT NULL DEFAULT 'I',
    ADD COLUMN anexo_ordem SMALLINT   NOT NULL DEFAULT 1,
    ADD COLUMN sub_item    SMALLINT   NOT NULL DEFAULT 0;
ALTER TABLE anexos_reducao_zero_ncm
    ADD COLUMN anexo    VARCHAR(4) NOT NULL DEFAULT 'I',
    ADD COLUMN sub_item SMALLINT   NOT NULL DEFAULT 0;

ALTER TABLE anexos_reducao_zero
    ALTER COLUMN anexo       DROP DEFAULT,
    ALTER COLUMN anexo_ordem DROP DEFAULT;
ALTER TABLE anexos_reducao_zero_ncm
    ALTER COLUMN anexo DROP DEFAULT;
-- sub_item MANTÉM o default 0: "item sem sub-item" é regra geral da tabela,
-- não um fato sobre o Anexo I.

-- 2) Chave. Os nomes abaixo são os que o Postgres gerou na migração 005
--    (tabela_pkey / tabela_coluna_fkey / tabela_colunas_key) e sobrevivem ao
--    RENAME da tabela — constraint não é renomeada junto.
ALTER TABLE anexos_reducao_zero_ncm
    DROP CONSTRAINT cesta_basica_anexo_i_ncm_item_fkey,
    DROP CONSTRAINT cesta_basica_anexo_i_ncm_item_prefixo_excecao_key;
ALTER TABLE anexos_reducao_zero
    DROP CONSTRAINT cesta_basica_anexo_i_pkey,
    DROP CONSTRAINT cesta_basica_anexo_i_item_check;   -- era "item BETWEEN 1 AND 26"

ALTER TABLE anexos_reducao_zero
    ADD PRIMARY KEY (anexo, item, sub_item),
    ADD CONSTRAINT item_positivo     CHECK (item >= 1),
    ADD CONSTRAINT sub_item_positivo CHECK (sub_item >= 0),
    -- O ordinal mora ao lado do rótulo: nenhum mapa romano→número em Python.
    -- Numeral romano NÃO ordena lexicograficamente ('IV' < 'IX' < 'V' como
    -- texto, mas 4 < 5 < 9 como número), e o desempate precisa de ordem total.
    -- Conjunto fechado também declara o significado da tabela: quem tentar
    -- carregar aqui o Anexo IV (60%, art. 131) falha no INSERT.
    ADD CONSTRAINT anexo_conhecido CHECK (
        (anexo, anexo_ordem) IN (('I', 1), ('XII', 12), ('XIII', 13), ('XV', 15))
    ),
    -- A citação legal precisa terminar com o Anexo e o item da PRÓPRIA chave:
    -- transcrever "item 13" numa linha cujo item é 14 falha no INSERT. Mesma
    -- família de `prefixo_bate_com_texto`: dado transcrito duas vezes é
    -- conferido pelo banco. O LIKE é ancorado no fim (sem '%' final), então
    -- '...item 15' não casa com o padrão de item 5.
    ADD CONSTRAINT dispositivo_cita_o_proprio_item CHECK (
        dispositivo_legal_ref LIKE '%Anexo ' || anexo || ', item '
            || CASE WHEN sub_item = 0 THEN item::text
                    ELSE item::text || '.' || sub_item::text END
    );

ALTER TABLE anexos_reducao_zero_ncm
    ADD FOREIGN KEY (anexo, item, sub_item)
        REFERENCES anexos_reducao_zero (anexo, item, sub_item) ON DELETE CASCADE,
    ADD UNIQUE (anexo, item, sub_item, prefixo, excecao);
-- sub_item é NOT NULL porque uma FK MATCH SIMPLE (o padrão) com coluna NULL é
-- satisfeita TRIVIALMENTE — seria integridade referencial desligada, sem erro
-- e sem sintoma. Pelo mesmo motivo o sentinela é 0, e não NULL: a lei numera
-- sub-itens a partir de 1 e jamais escreve "item 1.0".

-- 3) Comprimento de prefixo: passa a aceitar CAPÍTULO (2 dígitos), exigido pelo
--    Anexo XV, item 4 ("Capítulo 6"). Lista, não intervalo: 3 dígitos não é
--    nível da NCM/SH e nunca casaria com nada (falso negativo mudo).
--    Espelha api/ncm.py::_COMPRIMENTOS_PREFIXO — os dois mudam JUNTOS.
ALTER TABLE anexos_reducao_zero_ncm
    DROP CONSTRAINT prefixo_comprimento_valido,
    ADD  CONSTRAINT prefixo_comprimento_valido
         CHECK (prefixo ~ '^[0-9]+$' AND length(prefixo) IN (2, 4, 5, 6, 7, 8));

CREATE INDEX IF NOT EXISTS idx_anexos_reducao_zero_ncm_item
    ON anexos_reducao_zero_ncm (anexo, item, sub_item);

-- 4) O Anexo I atravessou intacto? (MUST "zero regressão" do DEFINE, provado
--    pela própria migração, não só por teste.)
DO $$
DECLARE itens int; prefixos int;
BEGIN
    SELECT count(*) INTO itens    FROM anexos_reducao_zero     WHERE anexo = 'I';
    SELECT count(*) INTO prefixos FROM anexos_reducao_zero_ncm WHERE anexo = 'I';
    IF (itens, prefixos) <> (26, 95) THEN
        RAISE EXCEPTION 'Anexo I não sobreviveu à generalização: % itens / % prefixos (esperado 26/95)',
            itens, prefixos;
    END IF;
END $$;

-- Mesmo padrão da 004/005: GRANT ... ON ALL TABLES não é retroativo. O RENAME
-- preserva o privilégio já concedido, mas reemitir custa zero e torna a
-- migração autocontida — e, pela degradação conservadora, um GRANT faltando
-- NÃO gera erro: gera CONSULTA_INDISPONIVEL silencioso com a alíquota geral.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao_zero     TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_zero_ncm TO taxreformai_app';
    END IF;
END $$;
