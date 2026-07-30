-- Generaliza o schema dos 4 Anexos de redução A ZERO para os 10 Anexos de
-- redução por NCM/SH da LCP 214/2025 — porque a verificação do /design provou
-- que os dois grupos NÃO são independentes: 117 pares de prefixo em
-- sobreposição, inclusive o MESMO código de 8 dígitos (9018.90.99 é XII/9 a
-- zero e é 9 itens do Anexo IV a 60%). Resolver em separado responderia 60%
-- onde a lei dá zero.
--
-- Nada de dado é reescrito: as 60 linhas de item e as 151 de prefixo já
-- carregadas só mudam de nome de tabela. O seed dos 6 Anexos novos é a 010.
--
-- O rename não é cosmético (terceiro e último desta família): uma linha do
-- Anexo VIII (sabão de toucador, 60%) gravada numa tabela chamada
-- `anexos_reducao_zero` é uma afirmação falsa dentro de um produto cujo valor
-- inteiro é auditabilidade — e a migração é o documento de auditoria.
-- `ALTER TABLE ... RENAME` preserva dados, índices e PRIVILÉGIOS.
--
-- Decisões 1 e 2 do DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NCM.md.

-- 1) O catálogo: o que é verdade sobre o ANEXO mora numa linha só.
--    Percentual, ordinal, artigo que institui e — novidade desta feature — o
--    dispositivo que zera a alíquota conforme QUEM compra. Guardá-los por item
--    os repetiria 321 vezes; guardá-los em Python os tiraria do alcance do
--    banco, que é quem precisa poder recusar uma linha inconsistente.
CREATE TABLE IF NOT EXISTS anexos_reducao_catalogo (
    anexo                  VARCHAR(4)   PRIMARY KEY,
    anexo_ordem            SMALLINT     NOT NULL UNIQUE,
    -- Fração da ALÍQUOTA que é removida: 1.0 = "reduzidas a zero" (arts. 125,
    -- 144, 145, 148); 0.6 = "reduzidas em 60%" (arts. 131 a 138). O nome diz
    -- "reducao" e não "aliquota" de propósito: 0.6 aqui significa que RESTAM
    -- 40% da alíquota da fase.
    percentual_reducao     NUMERIC(5,4) NOT NULL,
    assunto                TEXT NOT NULL,
    artigo_ref             TEXT NOT NULL,
    -- Só os Anexos IV, V e VI: a lei zera a alíquota deles conforme QUEM
    -- compra (arts. 144, II; 145, II; 146, § 2º — órgão da administração
    -- pública direta/autarquia/fundação, ou entidade de saúde imune com CEBAS
    -- comprovando serviço ao SUS).
    zero_por_comprador_ref TEXT,

    -- O conjunto fechado declara os TRÊS fatos no mesmo lugar. Carregar o
    -- Anexo IV com percentual 1.0 (ou o XII com 0.6) falha aqui, no INSERT.
    CONSTRAINT catalogo_conhecido CHECK (
        (anexo, anexo_ordem, percentual_reducao) IN (
            ('I',1,1.0), ('IV',4,0.6), ('V',5,0.6), ('VI',6,0.6), ('VII',7,0.6),
            ('VIII',8,0.6), ('IX',9,0.6), ('XII',12,1.0), ('XIII',13,1.0), ('XV',15,1.0))
    ),
    -- Anexo já reduzido a zero não pode ter condição de comprador: seria uma
    -- condição para chegar onde ele já está.
    CONSTRAINT so_percentual_tem_condicao_de_comprador CHECK (
        percentual_reducao < 1 OR zero_por_comprador_ref IS NULL
    )
);

INSERT INTO anexos_reducao_catalogo
       (anexo, anexo_ordem, percentual_reducao, assunto, artigo_ref, zero_por_comprador_ref) VALUES
 ('I',    1, 1.0, 'Cesta Básica Nacional de Alimentos',        'LCP 214/2025, art. 125',        NULL),
 ('IV',   4, 0.6, 'Dispositivos médicos',                      'LCP 214/2025, art. 131',        'LCP 214/2025, art. 144, II'),
 ('V',    5, 0.6, 'Dispositivos de acessibilidade',            'LCP 214/2025, art. 132',        'LCP 214/2025, art. 145, II'),
 ('VI',   6, 0.6, 'Nutrição enteral e parenteral',             'LCP 214/2025, art. 133, § 1º',  'LCP 214/2025, art. 146, § 2º'),
 ('VII',  7, 0.6, 'Alimentos destinados ao consumo humano',    'LCP 214/2025, art. 135',        NULL),
 ('VIII', 8, 0.6, 'Produtos de higiene pessoal e limpeza',     'LCP 214/2025, art. 136',        NULL),
 ('IX',   9, 0.6, 'Insumos agropecuários e aquícolas',         'LCP 214/2025, art. 138',        NULL),
 ('XII', 12, 1.0, 'Dispositivos médicos',                      'LCP 214/2025, art. 144, I',     NULL),
 ('XIII',13, 1.0, 'Dispositivos de acessibilidade',            'LCP 214/2025, art. 145, I',     NULL),
 ('XV',  15, 1.0, 'Produtos hortícolas, frutas e ovos',        'LCP 214/2025, art. 148',        NULL)
ON CONFLICT (anexo) DO NOTHING;

-- 2) O rename. Os índices vão junto: um índice chamado
--    `idx_anexos_reducao_zero_prefixo` sobre uma tabela que guarda 60% seria a
--    mesma afirmação falsa, num lugar que ninguém relê.
ALTER TABLE anexos_reducao_zero     RENAME TO anexos_reducao;
ALTER TABLE anexos_reducao_zero_ncm RENAME TO anexos_reducao_ncm;
ALTER INDEX idx_anexos_reducao_zero_prefixo   RENAME TO idx_anexos_reducao_prefixo;
ALTER INDEX idx_anexos_reducao_zero_ncm_item  RENAME TO idx_anexos_reducao_ncm_item;

-- 3) O ordinal passa a viver SÓ no catálogo: dois lugares declarando a mesma
--    verdade divergem no primeiro Anexo novo (Decisão 3 da feature anterior,
--    agora levada às últimas consequências). E a FK substitui a CHECK
--    `anexo_conhecido` COM VANTAGEM: a garantia "ninguém carrega aqui um Anexo
--    que esta tabela não declara" continua existindo, mas agora quem quiser
--    acrescentar um Anexo precisa INSERIR uma linha dizendo qual é o percentual
--    e qual artigo o institui.
ALTER TABLE anexos_reducao DROP CONSTRAINT anexo_conhecido;
ALTER TABLE anexos_reducao DROP COLUMN anexo_ordem;
ALTER TABLE anexos_reducao
    ADD CONSTRAINT anexo_no_catalogo FOREIGN KEY (anexo)
        REFERENCES anexos_reducao_catalogo (anexo);

-- A tabela de prefixos também passa a referenciar o catálogo: sem isso um
-- prefixo com `anexo` inexistente seria pego só pela FK composta
-- (anexo, item, sub_item), cuja mensagem de erro não diz que o problema é o
-- Anexo. Custa um índice de 10 linhas.
ALTER TABLE anexos_reducao_ncm
    ADD CONSTRAINT anexo_no_catalogo FOREIGN KEY (anexo)
        REFERENCES anexos_reducao_catalogo (anexo);

-- 4) Os 4 Anexos zero atravessaram intactos? (MUST "zero regressão" do DEFINE,
--    provado pela própria migração, não só por teste.)
DO $$
DECLARE itens int; prefixos int; catalogo int;
BEGIN
    SELECT count(*) INTO itens    FROM anexos_reducao;
    SELECT count(*) INTO prefixos FROM anexos_reducao_ncm;
    SELECT count(*) INTO catalogo FROM anexos_reducao_catalogo;
    IF (itens, prefixos) <> (60, 151) THEN
        RAISE EXCEPTION 'Anexos zero não sobreviveram ao rename: % itens / % prefixos (esperado 60/151)',
            itens, prefixos;
    END IF;
    IF catalogo <> 10 THEN
        RAISE EXCEPTION 'catálogo com % linhas (esperado 10)', catalogo;
    END IF;
    -- O percentual dos 4 já carregados TEM de ser 1.0: se a 010 for aplicada
    -- sobre um catálogo errado, todo o Anexo I viraria 60% sem nenhum sintoma.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao i
        JOIN anexos_reducao_catalogo c ON c.anexo = i.anexo
        WHERE c.percentual_reducao <> 1.0
    ) THEN
        RAISE EXCEPTION 'item já carregado apontando para Anexo que não é de redução a zero';
    END IF;
END $$;

-- Mesmo padrão da 004/005/007: GRANT ... ON ALL TABLES não é retroativo. O
-- RENAME preserva o privilégio já concedido, mas a tabela de catálogo é NOVA e
-- precisa do seu — e, pela degradação conservadora, um GRANT faltando NÃO gera
-- erro: gera CONSULTA_INDISPONIVEL silencioso com a alíquota geral.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao          TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_ncm      TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_catalogo TO taxreformai_app';
    END IF;
END $$;
