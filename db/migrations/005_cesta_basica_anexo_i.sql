-- Cesta Básica Nacional de Alimentos — LCP 214/2025, art. 125 e Anexo I.
--
-- Fonte primária desta transcrição (consultada em 2026-07-28):
--   https://legis.senado.leg.br/norma/40180341/publicacao/40180888
--   "Publicação Original de Anexo", DOU Edição Extra nº 11-B de 16/01/2025, p. 47.
-- O Anexo I NÃO tem republicação/errata (a única registrada na norma é do Anexo
-- XXIII) e NÃO foi alterado pela LC 227/2026 — verificado no /define.
--
-- Toda correspondência por NCM/SH é PREFIXO DE DÍGITOS: "posição 09.01" (4),
-- "subposição 1902.1" (5), "subposição 1006.20" (6), "0210.99.1" (7) e
-- "código 0405.10.00" (8) são todos prefixos do código de 8 dígitos da
-- mercadoria. Não há duas semânticas de match, só comprimentos diferentes.
--
-- Sem RLS: como aliquotas_ipi_tipi, é dado legal público, igual para todo tenant.
--
-- Contagens de fechamento (asseguradas por tests/test_cesta_basica_db.py):
-- 26 itens · 95 linhas de prefixo · 76 inclusões · 19 exceções.

CREATE TABLE IF NOT EXISTS cesta_basica_anexo_i (
    item                  SMALLINT PRIMARY KEY CHECK (item BETWEEN 1 AND 26),
    descricao             TEXT NOT NULL,   -- texto literal do item no DOU
    dispositivo_legal_ref TEXT NOT NULL,   -- "LCP 214/2025, art. 125, Anexo I, item N"
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cesta_basica_anexo_i_ncm (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item      SMALLINT NOT NULL REFERENCES cesta_basica_anexo_i (item) ON DELETE CASCADE,
    prefixo   VARCHAR(8) NOT NULL,          -- só dígitos
    excecao   BOOLEAN NOT NULL DEFAULT FALSE,
    alinea    CHAR(1),                      -- 'a'..'d' nos itens 19 e 20; NULL nos demais
    texto_ncm TEXT NOT NULL,                -- grafia literal do DOU: "02.07", "0210.99.1"

    UNIQUE (item, prefixo, excecao),

    -- O prefixo é DERIVADO da grafia literal, não digitado à parte: transcrever
    -- "0210.99.1" e digitar "02109910" passa a falhar no INSERT, em vez de virar
    -- uma mercadoria a mais na cesta básica descoberta por um cliente.
    CONSTRAINT prefixo_bate_com_texto
        CHECK (prefixo = regexp_replace(texto_ncm, '[^0-9]', '', 'g')),

    -- 4 = posição (o nível mais amplo que o Anexo I usa), 8 = subitem.
    -- api/ncm.py::prefixos_ncm gera EXATAMENTE estes comprimentos: uma linha
    -- fora da faixa jamais casaria com nada e seria um falso negativo mudo.
    -- Se um Anexo futuro citar capítulo (2 dígitos), os DOIS mudam juntos.
    CONSTRAINT prefixo_comprimento_valido CHECK (prefixo ~ '^[0-9]{4,8}$')
);

CREATE INDEX IF NOT EXISTS idx_cesta_basica_prefixo ON cesta_basica_anexo_i_ncm (prefixo);

INSERT INTO cesta_basica_anexo_i (item, descricao, dispositivo_legal_ref) VALUES
 (1,  'Arroz das subposições 1006.20 e 1006.30 e do código 1006.40.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 1'),
 (2,  'Leite, em conformidade com os requisitos da legislação específica relativos ao consumo direto pela população, classificado nos códigos 0401.10.10, 0401.10.90, 0401.20.10, 0401.20.90, 0401.40.10 e 0401.50.10 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 2'),
 (3,  'Leite em pó, em conformidade com os requisitos da legislação específica, classificado nos códigos 0402.10.10, 0402.10.90, 0402.21.10, 0402.21.20, 0402.29.10 e 0402.29.20 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 3'),
 (4,  'Fórmulas infantis, em conformidade com os requisitos da legislação específica, classificadas nos códigos 1901.10.10, 1901.10.90 e 2106.90.90 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 4'),
 (5,  'Manteiga do código 0405.10.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 5'),
 (6,  'Margarina do código 1517.10.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 6'),
 (7,  'Feijões dos códigos 0713.33.19, 0713.33.29, 0713.33.99 e 0713.35.90 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 7'),
 (8,  'Café da posição 09.01 e da subposição 2101.1, ambos da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 8'),
 (9,  'Óleo de babaçu do código 1513.21.20 da NCM/SH, em conformidade com os requisitos da legislação específica relativos ao consumo como alimento',
      'LCP 214/2025, art. 125, Anexo I, item 9'),
 (10, 'Farinha de mandioca classificada no código 1106.20.00 da NCM/SH e tapioca e seus sucedâneos do código 1903.00.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 10'),
 (11, 'Farinha, grumos e sêmolas, de milho, dos códigos 1102.20.00 e 1103.13.00 da NCM',
      'LCP 214/2025, art. 125, Anexo I, item 11'),
 (12, 'Grãos de milho classificados no código 1104.19.00 e do código 1104.23.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 12'),
 (13, 'Farinha de trigo do código 1101.00.10 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 13'),
 (14, 'Açúcar classificado nos códigos 1701.14.00 e 1701.99.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 14'),
 (15, 'Massas alimentícias da subposição 1902.1 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 15'),
 (16, 'Pão comumente denominado pão francês, de formato cilíndrico e alongado, com miolo branco creme e macio, e casca dourada e crocante, elaborado a partir da mistura ou pré-mistura de farinha de trigo, fermento biológico, água, sal, açúcar, aditivos alimentares e produtos de fortificação de farinhas, em conformidade com a legislação vigente, classificado no código 1905.90.90 da NCM/SH e a pré-mistura ou massa, para preparação do pão comumente denominado pão francês, dos códigos 1901.20.10 e 1901.20.90 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 16'),
 (17, 'Grãos de aveia dos códigos 1104.12.00 e 1104.22.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 17'),
 (18, 'Farinha de aveia classificada no código 1102.90.00 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 18'),
 (19, 'Carnes bovina, suína, ovina, caprina e de aves e produtos de origem animal (exceto foies gras) dos seguintes códigos, subposições e posições da NCM/SH: a) 02.01, 02.02, 0206.10.00, 0206.2 e 0210.20.00; b) 02.03, 0206.30.00, 0206.4, 0209.10 e 0210.1; c) 02.04 e 0210.99.20, carne caprina classificada no código 0210.99.90 e miudezas comestíveis de ovinos e caprinos classificadas nos códigos 0206.80.00 e 0206.90.00; d) 02.07, 0209.90.00 e 0210.99.1, exceto os produtos dos códigos 0207.43.00 e 0207.53.00',
      'LCP 214/2025, art. 125, Anexo I, item 19'),
 (20, 'Peixes e carnes de peixes (exceto salmonídeos, atuns, bacalhaus, hadoque, saithe e ovas e outros subprodutos) dos seguintes códigos, subposições e posições da NCM/SH: a) 03.02; exceto os produtos das subposições e dos códigos 0302.1, 0302.3, 0302.51.00, 0302.52.00, 0302.53.00 e 0302.9 da NCM/SH; b) 03.03; exceto os produtos das subposições e dos códigos 0303.1, 0303.4, 0303.63.00, 0303.64.00, 0303.65.00 e 0303.9 da NCM/SH; c) 03.04; exceto os salmonídeos, atuns, bacalhaus, hadoque e saithe classificados nas subposições 0304.4, 0304.5, 0304.7, 0304.8 e 0304.9 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 20'),
 (21, 'Queijos tipo mozarela, minas, prato, queijo de coalho, ricota, requeijão, queijo provolone, queijo parmesão, queijo fresco não maturado e queijo do reino classificados nos códigos 0406.10.10, 0406.10.90, 0406.20.00, 0406.90.10, 0406.90.20 e 0406.90.30 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 21'),
 (22, 'Sal em conformidade com os requisitos da legislação específica relativos ao teor de iodo enquadrado nos limites próprios para consumo humano classificado nos códigos 2501.00.20 e 2501.00.90 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 22'),
 (23, 'Mate da posição 09.03 da NCM/SH',
      'LCP 214/2025, art. 125, Anexo I, item 23'),
 (24, 'Farinha com baixo teor de proteína para pessoas com aminoacidopatias, acidemias e defeitos do ciclo da uréia da NCM 1901.90.90',
      'LCP 214/2025, art. 125, Anexo I, item 24'),
 (25, 'Massas com baixo teor de proteína para pessoas com aminoacidopatias, acidemias e defeitos do ciclo da uréia da NCM 1902.19.00',
      'LCP 214/2025, art. 125, Anexo I, item 25'),
 (26, 'Fórmulas Dietoterápicas para Erros Inatos do Metabolismo da NCM 2106.9090',
      'LCP 214/2025, art. 125, Anexo I, item 26')
ON CONFLICT (item) DO NOTHING;

-- 95 linhas: 76 inclusões (excecao = FALSE) + 19 exceções (excecao = TRUE).
-- `texto_ncm` é a grafia literal do DOU; `prefixo` é derivado dela e conferido
-- pela CHECK prefixo_bate_com_texto — nenhum dígito é digitado duas vezes sem
-- que o banco compare os dois.
INSERT INTO cesta_basica_anexo_i_ncm (item, prefixo, excecao, alinea, texto_ncm) VALUES
 -- Item 1 — arroz (2 subposições de 6 + 1 código de 8)
 (1,  '100620',   FALSE, NULL, '1006.20'),
 (1,  '100630',   FALSE, NULL, '1006.30'),
 (1,  '10064000', FALSE, NULL, '1006.40.00'),
 -- Item 2 — leite
 (2,  '04011010', FALSE, NULL, '0401.10.10'),
 (2,  '04011090', FALSE, NULL, '0401.10.90'),
 (2,  '04012010', FALSE, NULL, '0401.20.10'),
 (2,  '04012090', FALSE, NULL, '0401.20.90'),
 (2,  '04014010', FALSE, NULL, '0401.40.10'),
 (2,  '04015010', FALSE, NULL, '0401.50.10'),
 -- Item 3 — leite em pó
 (3,  '04021010', FALSE, NULL, '0402.10.10'),
 (3,  '04021090', FALSE, NULL, '0402.10.90'),
 (3,  '04022110', FALSE, NULL, '0402.21.10'),
 (3,  '04022120', FALSE, NULL, '0402.21.20'),
 (3,  '04022910', FALSE, NULL, '0402.29.10'),
 (3,  '04022920', FALSE, NULL, '0402.29.20'),
 -- Item 4 — fórmulas infantis (2106.90.90 também é citado pelo item 26)
 (4,  '19011010', FALSE, NULL, '1901.10.10'),
 (4,  '19011090', FALSE, NULL, '1901.10.90'),
 (4,  '21069090', FALSE, NULL, '2106.90.90'),
 -- Item 5 — manteiga
 (5,  '04051000', FALSE, NULL, '0405.10.00'),
 -- Item 6 — margarina
 (6,  '15171000', FALSE, NULL, '1517.10.00'),
 -- Item 7 — feijões
 (7,  '07133319', FALSE, NULL, '0713.33.19'),
 (7,  '07133329', FALSE, NULL, '0713.33.29'),
 (7,  '07133399', FALSE, NULL, '0713.33.99'),
 (7,  '07133590', FALSE, NULL, '0713.35.90'),
 -- Item 8 — café: nenhum código de 8 dígitos, só posição e subposição
 (8,  '0901',     FALSE, NULL, '09.01'),
 (8,  '21011',    FALSE, NULL, '2101.1'),
 -- Item 9 — óleo de babaçu
 (9,  '15132120', FALSE, NULL, '1513.21.20'),
 -- Item 10 — farinha de mandioca e tapioca
 (10, '11062000', FALSE, NULL, '1106.20.00'),
 (10, '19030000', FALSE, NULL, '1903.00.00'),
 -- Item 11 — farinha, grumos e sêmolas de milho
 (11, '11022000', FALSE, NULL, '1102.20.00'),
 (11, '11031300', FALSE, NULL, '1103.13.00'),
 -- Item 12 — grãos de milho
 (12, '11041900', FALSE, NULL, '1104.19.00'),
 (12, '11042300', FALSE, NULL, '1104.23.00'),
 -- Item 13 — farinha de trigo
 (13, '11010010', FALSE, NULL, '1101.00.10'),
 -- Item 14 — açúcar
 (14, '17011400', FALSE, NULL, '1701.14.00'),
 (14, '17019900', FALSE, NULL, '1701.99.00'),
 -- Item 15 — massas alimentícias (contém o código do item 25)
 (15, '19021',    FALSE, NULL, '1902.1'),
 -- Item 16 — pão francês e pré-mistura
 (16, '19059090', FALSE, NULL, '1905.90.90'),
 (16, '19012010', FALSE, NULL, '1901.20.10'),
 (16, '19012090', FALSE, NULL, '1901.20.90'),
 -- Item 17 — grãos de aveia
 (17, '11041200', FALSE, NULL, '1104.12.00'),
 (17, '11042200', FALSE, NULL, '1104.22.00'),
 -- Item 18 — farinha de aveia
 (18, '11029000', FALSE, NULL, '1102.90.00'),
 -- Item 19, alínea a — bovinos
 (19, '0201',     FALSE, 'a',  '02.01'),
 (19, '0202',     FALSE, 'a',  '02.02'),
 (19, '02061000', FALSE, 'a',  '0206.10.00'),
 (19, '02062',    FALSE, 'a',  '0206.2'),
 (19, '02102000', FALSE, 'a',  '0210.20.00'),
 -- Item 19, alínea b — suínos
 (19, '0203',     FALSE, 'b',  '02.03'),
 (19, '02063000', FALSE, 'b',  '0206.30.00'),
 (19, '02064',    FALSE, 'b',  '0206.4'),
 (19, '020910',   FALSE, 'b',  '0209.10'),
 (19, '02101',    FALSE, 'b',  '0210.1'),
 -- Item 19, alínea c — ovinos e caprinos
 (19, '0204',     FALSE, 'c',  '02.04'),
 (19, '02109920', FALSE, 'c',  '0210.99.20'),
 (19, '02109990', FALSE, 'c',  '0210.99.90'),
 (19, '02068000', FALSE, 'c',  '0206.80.00'),
 (19, '02069000', FALSE, 'c',  '0206.90.00'),
 -- Item 19, alínea d — aves. Único prefixo de 7 dígitos do Anexo I.
 (19, '0207',     FALSE, 'd',  '02.07'),
 (19, '02099000', FALSE, 'd',  '0209.90.00'),
 (19, '0210991',  FALSE, 'd',  '0210.99.1'),
 -- Item 19, alínea d — EXCEÇÕES (foies gras), escopadas a este item
 (19, '02074300', TRUE,  'd',  '0207.43.00'),
 (19, '02075300', TRUE,  'd',  '0207.53.00'),
 -- Item 20, alínea a — peixes frescos/refrigerados, menos salmonídeos e atuns
 (20, '0302',     FALSE, 'a',  '03.02'),
 (20, '03021',    TRUE,  'a',  '0302.1'),
 (20, '03023',    TRUE,  'a',  '0302.3'),
 (20, '03025100', TRUE,  'a',  '0302.51.00'),
 (20, '03025200', TRUE,  'a',  '0302.52.00'),
 (20, '03025300', TRUE,  'a',  '0302.53.00'),
 (20, '03029',    TRUE,  'a',  '0302.9'),
 -- Item 20, alínea b — peixes congelados
 (20, '0303',     FALSE, 'b',  '03.03'),
 (20, '03031',    TRUE,  'b',  '0303.1'),
 (20, '03034',    TRUE,  'b',  '0303.4'),
 (20, '03036300', TRUE,  'b',  '0303.63.00'),
 (20, '03036400', TRUE,  'b',  '0303.64.00'),
 (20, '03036500', TRUE,  'b',  '0303.65.00'),
 (20, '03039',    TRUE,  'b',  '0303.9'),
 -- Item 20, alínea c — filés e outras carnes de peixe
 (20, '0304',     FALSE, 'c',  '03.04'),
 (20, '03044',    TRUE,  'c',  '0304.4'),
 (20, '03045',    TRUE,  'c',  '0304.5'),
 (20, '03047',    TRUE,  'c',  '0304.7'),
 (20, '03048',    TRUE,  'c',  '0304.8'),
 (20, '03049',    TRUE,  'c',  '0304.9'),
 -- Item 21 — queijos
 (21, '04061010', FALSE, NULL, '0406.10.10'),
 (21, '04061090', FALSE, NULL, '0406.10.90'),
 (21, '04062000', FALSE, NULL, '0406.20.00'),
 (21, '04069010', FALSE, NULL, '0406.90.10'),
 (21, '04069020', FALSE, NULL, '0406.90.20'),
 (21, '04069030', FALSE, NULL, '0406.90.30'),
 -- Item 22 — sal
 (22, '25010020', FALSE, NULL, '2501.00.20'),
 (22, '25010090', FALSE, NULL, '2501.00.90'),
 -- Item 23 — mate
 (23, '0903',     FALSE, NULL, '09.03'),
 -- Item 24 — farinha de baixo teor de proteína
 (24, '19019090', FALSE, NULL, '1901.90.90'),
 -- Item 25 — massas de baixo teor de proteína (contido no prefixo do item 15)
 (25, '19021900', FALSE, NULL, '1902.19.00'),
 -- Item 26 — fórmulas dietoterápicas. Grafia SEM pontos no texto oficial;
 -- mesmo código do item 4, por isso o desempate da Decisão 4 é obrigatório.
 (26, '21069090', FALSE, NULL, '2106.9090')
ON CONFLICT DO NOTHING;

-- Mesmo padrão da migração 004: GRANT ... ON ALL TABLES não é retroativo, então
-- sem este bloco o papel de runtime ficaria sem SELECT — e, pela Decisão 8, isso
-- NÃO gera erro: gera CONSULTA_INDISPONIVEL silencioso com a alíquota geral,
-- que é indistinguível do comportamento de antes desta feature. Ver Decisão 13.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON cesta_basica_anexo_i TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON cesta_basica_anexo_i_ncm TO taxreformai_app';
    END IF;
END $$;
