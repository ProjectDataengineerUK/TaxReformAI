-- Anexos XII (art. 144, I), XIII (art. 145, I) e XV (art. 148) da LCP 214/2025
-- — redução a ZERO das alíquotas do IBS e da CBS, por NCM/SH.
--
-- Fonte primária desta transcrição (consultada em 2026-07-28, DOU Edição Extra
-- nº 11-B de 16/01/2025):
--   Anexo XII  https://legis.senado.leg.br/norma/40180341/publicacao/40180960 (p. 54)
--   Anexo XIII https://legis.senado.leg.br/norma/40180341/publicacao/40180966 (p. 54)
--   Anexo XV   https://legis.senado.leg.br/norma/40180341/publicacao/40181038 (p. 58)
--   Corpo      https://legis.senado.leg.br/norma/40180341/publicacao/40181429 (arts. 143-148)
-- Nenhum dos três tem republicação/errata, e a LC 227/2026 não alterou nem os
-- Anexos nem os arts. 144/145/148 — verificado item a item no /design.
--
-- O art. 148 diz "reduzidas a ZERO" ainda que o cabeçalho do Anexo XV diga
-- "redução de 100%": vale o dispositivo, e por isso o Anexo XV entra AQUI.
--
-- CLÁUSULAS "EXCETO" — três classes, e só uma vira linha:
--   XII/1.3  9 códigos          DESCRITIVA      0 linhas (nenhum desce de 90181980)
--   XII/5    "os dentários"     NÃO CODIFICÁVEL 0 linhas (sem código; limitação declarada)
--   XII/5    9021.39.91/.99     OPERANTE        2 linhas (descem de 90213)
--   XII/7    9022.19.91         OPERANTE        1 linha  (desce de 902219)
--   XII/11   9022.21.10/.20     DESCRITIVA      0 linhas (são os itens 8 e 10)
--   XIII/4   "partes e acess."  NÃO CODIFICÁVEL 0 linhas (item próprio: XIII/5)
--   XV/2     0709.5, 0710.80.00 OPERANTE        2 linhas (descem de 0709 e 0710)
-- Regra: uma exceção só é OPERANTE se descende de uma inclusão DO MESMO item.
-- O bloco de asserções no fim recusa qualquer exceção que não descenda — as
-- DESCRITIVAS foram consideradas e descartadas, não esquecidas.
--
-- Os itens XII/1 e XIII/2 são CABEÇALHOS: o DOU não lhes dá célula de NCM, e os
-- sub-itens abaixo são ininteligíveis sozinhos (a descrição do XIII/2.1 é
-- literalmente "Sem mecanismo de propulsão"). Entram como item, sem prefixo, e
-- a resposta recupera o contexto pelo pai — sub_item = 0 da mesma chave.
--
-- Contagens: XII 20 itens/24 linhas · XIII 8/7 · XV 6/25.

INSERT INTO anexos_reducao_zero (anexo, anexo_ordem, item, sub_item, descricao, dispositivo_legal_ref) VALUES
 -- Anexo XII — dispositivos médicos (art. 144, I)
 ('XII', 12, 1, 0, 'Aparelhos de eletrodiagnóstico (incluídos os aparelhos de exploração funcional e os de verificação de parâmetros fisiológicos)',
  'LCP 214/2025, art. 144, Anexo XII, item 1'),
 ('XII', 12, 1, 1, 'Eletrocardiógrafos',
  'LCP 214/2025, art. 144, Anexo XII, item 1.1'),
 ('XII', 12, 1, 2, 'Eletroencefalógrafos',
  'LCP 214/2025, art. 144, Anexo XII, item 1.2'),
 ('XII', 12, 1, 3, 'Aparelhos de eletrodiagnóstico, exceto os produtos classificados nos códigos 9018.11.00, 9018.12.10, 9018.12.90, 9018.13.00, 9018.14.10, 9018.14.20, 9018.14.90, 9018.19.10 e 9018.19.20',
  'LCP 214/2025, art. 144, Anexo XII, item 1.3'),
 ('XII', 12, 2, 0, 'Aparelhos de raios ultravioleta ou infravermelhos',
  'LCP 214/2025, art. 144, Anexo XII, item 2'),
 ('XII', 12, 3, 0, 'Artigos e aparelhos ortopédicos',
  'LCP 214/2025, art. 144, Anexo XII, item 3'),
 ('XII', 12, 4, 0, 'Artigos e aparelhos para fraturas',
  'LCP 214/2025, art. 144, Anexo XII, item 4'),
 ('XII', 12, 5, 0, 'Artigos e aparelhos de prótese, exceto os dentários e os produtos classificados nos códigos 9021.39.91 e 9021.39.99',
  'LCP 214/2025, art. 144, Anexo XII, item 5'),
 ('XII', 12, 6, 0, 'Tomógrafo computadorizado',
  'LCP 214/2025, art. 144, Anexo XII, item 6'),
 ('XII', 12, 7, 0, 'Aparelhos de raio X, móveis, exceto os produtos classificados no código 9022.19.91',
  'LCP 214/2025, art. 144, Anexo XII, item 7'),
 ('XII', 12, 8, 0, 'Aparelho de radiocobalto (bomba de cobalto)',
  'LCP 214/2025, art. 144, Anexo XII, item 8'),
 ('XII', 12, 9, 0, 'Aparelho de crioterapia',
  'LCP 214/2025, art. 144, Anexo XII, item 9'),
 ('XII', 12, 10, 0, 'Aparelho de gamaterapia',
  'LCP 214/2025, art. 144, Anexo XII, item 10'),
 ('XII', 12, 11, 0, 'Aparelhos que utilizem radiações alfa, beta, gama ou outras radiações ionizantes, para usos médicos, cirúrgicos, odontológicos ou veterinários, incluídos os aparelhos de radiofotografia ou de radioterapia, exceto os produtos classificados nos códigos 9022.21.10 e 9022.21.20',
  'LCP 214/2025, art. 144, Anexo XII, item 11'),
 ('XII', 12, 12, 0, 'Densímetros, areômetros, pesa-líquidos e instrumentos flutuantes semelhantes, termômetros, pirômetros, barômetros, higrômetros e psicômetros, registradores ou não, mesmo combinados entre si',
  'LCP 214/2025, art. 144, Anexo XII, item 12'),
 ('XII', 12, 13, 0, 'Respirador',
  'LCP 214/2025, art. 144, Anexo XII, item 13'),
 ('XII', 12, 14, 0, 'Monitor multiparâmetros',
  'LCP 214/2025, art. 144, Anexo XII, item 14'),
 ('XII', 12, 15, 0, 'Bomba de infusão',
  'LCP 214/2025, art. 144, Anexo XII, item 15'),
 ('XII', 12, 16, 0, 'Aparelhos de diagnóstico por visualização de ressonância magnética',
  'LCP 214/2025, art. 144, Anexo XII, item 16'),
 ('XII', 12, 17, 0, 'Aparelhos de ultrassom',
  'LCP 214/2025, art. 144, Anexo XII, item 17'),
 -- Anexo XIII — dispositivos de acessibilidade (art. 145, I)
 ('XIII', 13, 1, 0, 'Barra de apoio para pessoa com deficiência física',
  'LCP 214/2025, art. 145, Anexo XIII, item 1'),
 ('XIII', 13, 2, 0, 'CADEIRA DE RODAS E OUTROS VEÍCULOS PARA DEFICIENTES, MESMO COM MOTOR OU OUTRO MECANISMO DE PROPULSÃO',
  'LCP 214/2025, art. 145, Anexo XIII, item 2'),
 ('XIII', 13, 2, 1, 'Sem mecanismo de propulsão',
  'LCP 214/2025, art. 145, Anexo XIII, item 2.1'),
 ('XIII', 13, 2, 2, 'Cadeiras de rodas com motor ou outro mecanismo de propulsão e outros veículos para pessoas com incapacidade, mesmo com motor ou outro mecanismo de propulsão',
  'LCP 214/2025, art. 145, Anexo XIII, item 2.2'),
 ('XIII', 13, 3, 0, 'Partes e acessórios destinados exclusivamente a aplicação em cadeiras de rodas ou em outros veículos para deficientes',
  'LCP 214/2025, art. 145, Anexo XIII, item 3'),
 ('XIII', 13, 4, 0, 'Aparelhos para facilitar a audição dos surdos, exceto partes e acessórios',
  'LCP 214/2025, art. 145, Anexo XIII, item 4'),
 ('XIII', 13, 5, 0, 'Partes e acessórios de aparelhos para facilitar a audição dos surdos',
  'LCP 214/2025, art. 145, Anexo XIII, item 5'),
 ('XIII', 13, 6, 0, 'Implantes cocleares',
  'LCP 214/2025, art. 145, Anexo XIII, item 6'),
 -- Anexo XV — produtos hortícolas, frutas e ovos (art. 148). A tabela do DOU
 -- tem 2 colunas: os códigos vêm embutidos na prosa da própria descrição.
 ('XV', 15, 1, 0, 'Ovos da subposição 0407.2 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 1'),
 ('XV', 15, 2, 0, 'Produtos hortícolas das posições 07.01, 07.02.00.00, 07.03, 07.04, 07.05, 07.06, 0707.00.00, 07.08, 07.09 e 07.10, exceto os cogumelos e trufas classificados na subposição 0709.5 e no código 0710.80.00 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 2'),
 ('XV', 15, 3, 0, 'Frutas frescas ou refrigeradas e frutas congeladas sem adição de açúcar ou de outros edulcorantes classificadas nas posições 08.03, 08.04, 08.05, 08.06, 08.07, 08.08, 08.09, 08.10 e 08.11 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 3'),
 ('XV', 15, 4, 0, 'Plantas e produtos de floricultura relativos à horticultura e cultivados para fins alimentares, ornamentais ou medicinais classificados no Capítulo 6 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 4'),
 ('XV', 15, 5, 0, 'Raízes e tubérculos da posição 07.14 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 5'),
 ('XV', 15, 6, 0, 'Cocos da subposição 0801.1 da NCM/SH',
  'LCP 214/2025, art. 148, Anexo XV, item 6')
ON CONFLICT DO NOTHING;

-- 56 linhas: 51 inclusões (excecao = FALSE) + 5 exceções (excecao = TRUE).
-- `texto_ncm` é a grafia literal do DOU; `prefixo` é derivado dela e conferido
-- pela CHECK prefixo_bate_com_texto — nenhum dígito é digitado duas vezes sem
-- que o banco compare os dois.
INSERT INTO anexos_reducao_zero_ncm (anexo, item, sub_item, prefixo, excecao, alinea, texto_ncm) VALUES
 -- Anexo XII. O item 1 é cabeçalho e NÃO tem linha aqui.
 ('XII', 1, 1, '90181100', FALSE, NULL, '9018.11.00'),
 ('XII', 1, 2, '90181980', FALSE, NULL, '9018.19.80'),  -- mesmo código de 1.3 e 14
 ('XII', 1, 3, '90181980', FALSE, NULL, '9018.19.80'),
 ('XII', 2, 0, '901820',   FALSE, NULL, '9018.20'),
 ('XII', 3, 0, '90211010', FALSE, NULL, '9021.10.10'),
 ('XII', 4, 0, '90211020', FALSE, NULL, '9021.10.20'),
 -- Item 5: UMA inclusão de 5 dígitos e DUAS exceções que descem dela. A outra
 -- cláusula do item ("exceto os dentários") não nomeia código: não vira linha.
 ('XII', 5, 0, '90213',    FALSE, NULL, '9021.3'),
 ('XII', 5, 0, '90213991', TRUE,  NULL, '9021.39.91'),
 ('XII', 5, 0, '90213999', TRUE,  NULL, '9021.39.99'),
 ('XII', 6, 0, '90221200', FALSE, NULL, '9022.12.00'),
 -- Item 7: TRÊS células de NCM num item só, e a exceção do caput desce de 902219.
 ('XII', 7, 0, '902213',   FALSE, NULL, '9022.13'),
 ('XII', 7, 0, '902214',   FALSE, NULL, '9022.14'),
 ('XII', 7, 0, '902219',   FALSE, NULL, '9022.19'),
 ('XII', 7, 0, '90221991', TRUE,  NULL, '9022.19.91'),
 ('XII', 8, 0, '90222110', FALSE, NULL, '9022.21.10'),
 ('XII', 9, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('XII', 10, 0, '90222120', FALSE, NULL, '9022.21.20'),
 -- Item 11: o "exceto 9022.21.10 e 9022.21.20" é DESCRITIVO — nenhum dos dois
 -- desce de 90222190 (são os itens 8 e 10). Zero linha de exceção.
 ('XII', 11, 0, '90222190', FALSE, NULL, '9022.21.90'),
 ('XII', 12, 0, '9025',     FALSE, NULL, '90.25'),
 ('XII', 13, 0, '90192040', FALSE, NULL, '9019.20.40'),
 ('XII', 14, 0, '90181980', FALSE, NULL, '9018.19.80'),  -- terceiro item no mesmo código
 ('XII', 15, 0, '90189010', FALSE, NULL, '9018.90.10'),
 ('XII', 16, 0, '90181300', FALSE, NULL, '9018.13.00'),
 ('XII', 17, 0, '901812',   FALSE, NULL, '9018.12'),
 -- Anexo XIII. O item 2 é cabeçalho e NÃO tem linha aqui.
 ('XIII', 1, 0, '83024100', FALSE, NULL, '8302.41.00'),
 ('XIII', 2, 1, '87131000', FALSE, NULL, '8713.10.00'),  -- "Sem mecanismo de propulsão"
 ('XIII', 2, 2, '87139000', FALSE, NULL, '8713.90.00'),
 ('XIII', 3, 0, '87142000', FALSE, NULL, '8714.20.00'),
 ('XIII', 4, 0, '90214000', FALSE, NULL, '9021.40.00'),
 ('XIII', 5, 0, '90219092', FALSE, NULL, '9021.90.92'),
 ('XIII', 6, 0, '90219019', FALSE, NULL, '9021.90.19'),
 -- Anexo XV.
 ('XV', 1, 0, '04072',    FALSE, NULL, '0407.2'),
 ('XV', 2, 0, '0701',     FALSE, NULL, '07.01'),
 ('XV', 2, 0, '07020000', FALSE, NULL, '07.02.00.00'),
 ('XV', 2, 0, '0703',     FALSE, NULL, '07.03'),
 ('XV', 2, 0, '0704',     FALSE, NULL, '07.04'),
 ('XV', 2, 0, '0705',     FALSE, NULL, '07.05'),
 ('XV', 2, 0, '0706',     FALSE, NULL, '07.06'),
 ('XV', 2, 0, '07070000', FALSE, NULL, '0707.00.00'),
 ('XV', 2, 0, '0708',     FALSE, NULL, '07.08'),
 ('XV', 2, 0, '0709',     FALSE, NULL, '07.09'),
 ('XV', 2, 0, '0710',     FALSE, NULL, '07.10'),
 ('XV', 2, 0, '07095',    TRUE,  NULL, '0709.5'),
 ('XV', 2, 0, '07108000', TRUE,  NULL, '0710.80.00'),
 ('XV', 3, 0, '0803',     FALSE, NULL, '08.03'),
 ('XV', 3, 0, '0804',     FALSE, NULL, '08.04'),
 ('XV', 3, 0, '0805',     FALSE, NULL, '08.05'),
 ('XV', 3, 0, '0806',     FALSE, NULL, '08.06'),
 ('XV', 3, 0, '0807',     FALSE, NULL, '08.07'),
 ('XV', 3, 0, '0808',     FALSE, NULL, '08.08'),
 ('XV', 3, 0, '0809',     FALSE, NULL, '08.09'),
 ('XV', 3, 0, '0810',     FALSE, NULL, '08.10'),
 ('XV', 3, 0, '0811',     FALSE, NULL, '08.11'),
 -- Anexo XV, item 4: ÚNICO prefixo de 2 dígitos do projeto. `texto_ncm` é '06',
 -- e não 'Capítulo 6', porque a coluna guarda a grafia do CÓDIGO e o DOU não
 -- escreve código aqui — a prosa fica na `descricao`, literal. Escrever
 -- 'Capítulo 6' faria prefixo_bate_com_texto derivar '6' e a migração falhar.
 -- É a linha mais AMPLA do projeto: concede zero a todo o Capítulo 6, enquanto
 -- o item qualifica ("relativos à horticultura e cultivados para fins
 -- alimentares, ornamentais ou medicinais"). A qualificação restringe e não é
 -- verificável a partir do payload — limitação declarada na resposta.
 ('XV', 4, 0, '06',       FALSE, NULL, '06'),
 ('XV', 5, 0, '0714',     FALSE, NULL, '07.14'),
 ('XV', 6, 0, '08011',    FALSE, NULL, '0801.1')
ON CONFLICT DO NOTHING;

DO $$
DECLARE r RECORD; n int;
BEGIN
    -- (1) Contagem por Anexo: uma migração truncada passa em toda CHECK e falha
    --     aqui. Por Anexo, e não global, para que a falha diga ONDE.
    FOR r IN SELECT * FROM (VALUES ('I',26,95),('XII',20,24),('XIII',8,7),('XV',6,25))
                          AS e(anexo, itens, prefixos) LOOP
        IF (SELECT count(*) FROM anexos_reducao_zero     WHERE anexo = r.anexo) <> r.itens
        OR (SELECT count(*) FROM anexos_reducao_zero_ncm WHERE anexo = r.anexo) <> r.prefixos THEN
            RAISE EXCEPTION 'Anexo %: contagem não bate com a transcrição do DESIGN', r.anexo;
        END IF;
    END LOOP;

    -- (2) Inclusões/exceções no total.
    SELECT count(*) INTO n FROM anexos_reducao_zero_ncm WHERE excecao IS TRUE;
    IF n <> 24 THEN RAISE EXCEPTION 'exceções: % (esperado 24 = 19 do Anexo I + 5 novas)', n; END IF;

    SELECT count(*) INTO n FROM anexos_reducao_zero_ncm WHERE excecao IS FALSE;
    IF n <> 127 THEN RAISE EXCEPTION 'inclusões: % (esperado 127 = 76 do Anexo I + 51 novas)', n; END IF;

    -- (3) Exceção órfã: ou erro de transcrição, ou "exceto" DESCRITIVO virado
    --     linha. Nos dois casos a linha seria inerte — ruído indistinguível de
    --     erro, que só apareceria no dia em que colidisse com outro item.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero_ncm e
        WHERE e.excecao IS TRUE AND NOT EXISTS (
            SELECT 1 FROM anexos_reducao_zero_ncm i
            WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
              AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%')
    ) THEN RAISE EXCEPTION 'exceção que não desce de nenhuma inclusão do próprio item'; END IF;

    -- (4) Item sem prefixo só é legítimo se for CABEÇALHO (tem sub-itens); e
    --     todo sub-item precisa do seu cabeçalho.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero i
        WHERE NOT EXISTS (SELECT 1 FROM anexos_reducao_zero_ncm p
                          WHERE p.anexo = i.anexo AND p.item = i.item AND p.sub_item = i.sub_item)
          AND NOT EXISTS (SELECT 1 FROM anexos_reducao_zero f
                          WHERE f.anexo = i.anexo AND f.item = i.item AND f.sub_item > 0)
    ) THEN RAISE EXCEPTION 'item sem linha de prefixo e sem sub-item: INSERT truncado'; END IF;

    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero f
        WHERE f.sub_item > 0 AND NOT EXISTS (SELECT 1 FROM anexos_reducao_zero c
                                             WHERE c.anexo = f.anexo AND c.item = f.item AND c.sub_item = 0)
    ) THEN RAISE EXCEPTION 'sub-item sem linha de cabeçalho'; END IF;

    -- (5) Comprimentos presentes ⊆ {2,4,5,6,7,8}. Redundante com a CHECK de
    --     propósito: prova que a CHECK da migração 007 está de fato ativa.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_zero_ncm WHERE length(prefixo) NOT IN (2,4,5,6,7,8)
    ) THEN RAISE EXCEPTION 'prefixo com comprimento que a NCM/SH não tem'; END IF;
END $$;
