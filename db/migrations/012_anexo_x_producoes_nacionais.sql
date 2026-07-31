-- Anexo X (art. 139, Produções Nacionais Artísticas, Culturais, de Eventos,
-- Jornalísticas e Audiovisuais) da LCP 214/2025 — continuação de
-- ANEXOS_REDUCAO_PERCENTUAL_NBS (posição 14/17), que shipou em 2026-07-31 com
-- este Anexo deliberadamente vazio: o corpo de 544 artigos da LCP 214/2025
-- excedia o que a ferramenta de leitura web daquele build processava de uma
-- vez, sem âncora por artigo na fonte.
--
-- Fonte primária desta migração (consultada em 2026-07-31): o mesmo texto já
-- usado nas features anteriores (legis.senado.leg.br) não pôde ser lido por
-- inteiro; o art. 139 foi obtido do mirror oficial da Câmara dos Deputados
-- (LegIn), "Texto Atualizado" (já incorpora a LC 227/2026 — confirmado pela
-- mesma nota "(Inciso com redação dada pela Lei Complementar nº 227...)" que
-- o /define já tinha achado no art. 142, II, provando que é o texto vigente):
--   https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.pdf
-- Baixado como PDF (298 páginas) e lido com `pdftotext -layout`, contornando
-- o limite de tamanho da ferramenta de leitura web — não uma fonte diferente,
-- o mesmo texto oficial, extraído por uma rota diferente.
--
-- TEXTO INTEGRAL DO ART. 139 (transcrito para auditoria; rege as condições
-- desta migração):
--   "Art. 139. Ficam reduzidas em 60% (sessenta por cento) as alíquotas do
--   IBS e da CBS incidentes sobre o fornecimento dos bens e serviços listados
--   no Anexo X desta Lei Complementar, com a especificação das respectivas
--   classificações da NCM/SH e NBS, nos casos relacionados com as seguintes
--   produções nacionais artísticas, culturais, de eventos, jornalísticas e
--   audiovisuais:
--   I - espetáculos teatrais, circenses e de dança;
--   II - shows musicais;
--   III - desfiles carnavalescos ou folclóricos;
--   IV - eventos acadêmicos e científicos, como congressos, conferências e
--        simpósios;
--   V - feiras de negócios;
--   VI - exposições, feiras, galerias e mostras culturais, artísticas e
--        literárias;
--   VII - programas de auditório ou jornalísticos, filmes, documentários,
--        séries, novelas, entrevistas e clipes musicais; e
--   VIII - obras de arte.
--   § 1º O disposto nos incisos I, II, III e VII do caput deste artigo
--   somente se aplica a produções realizadas no País que contenham
--   majoritariamente obras artísticas, musicais, literárias ou jornalísticas
--   de autores brasileiros ou interpretadas majoritariamente por artistas
--   brasileiros.
--   § 2º No caso das obras cinematográficas ou videofonográficas de que
--   trata o inciso VII do caput deste artigo, considera-se produção nacional
--   aquela que atenda aos requisitos para obras audiovisuais nacionais
--   definidos na legislação específica.
--   § 3º O fornecimento de obras de arte de que trata o inciso VIII do caput
--   deste artigo contempla apenas aqueles produzidos por artistas
--   brasileiros."
--
-- MAPEAMENTO ITEM → INCISO (o Anexo X, conferido linha a linha contra o PDF,
-- NÃO tem coluna de inciso — cada item precisou ser lido contra a lista de
-- categorias do caput. Achado desta sessão: a correspondência NÃO é 1:1
-- perfeita para todos os 47 itens; três grupos, do mais ao menos certo):
--
--   GRUPO A — incisos I/II/III/VII, nacionalidade EXIGIDA (§1º):
--   - Itens 1-21, 46-48 (22 itens): licenciamento/cessão de direitos de
--     autor e conexos de obras literárias/cinematográficas/jornalísticas/
--     audiovisuais(TV)/musicais, mais agências de notícias. O inciso mais
--     próximo é o VII ("filmes, documentários, séries, novelas, jornalísticos
--     [...] e clipes musicais") — é o ÚNICO inciso que menciona obras
--     gravadas/publicadas. RESSALVA HONESTA: "obras literárias" (itens 2, 9,
--     16) e "obras musicais e fonogramas" em sentido amplo (itens 8, 15, 19)
--     não aparecem literalmente em NENHUM dos 8 incisos (VII só cita "clipes
--     musicais", não fonogramas em geral; nenhum inciso cita literatura) —
--     tratados como VII por ser o único inciso da família "obras
--     gravadas/publicadas", mas é uma INFERÊNCIA, não uma citação literal.
--     Itens 1 e 47 (prefixos genéricos "1.1103"/"1.1106", cabeçalhos de
--     posição) herdam a mesma classificação dos seus itens mais específicos.
--   - Itens 23-35, 41 (13 itens): serviços de suporte à produção audiovisual
--     (gravação, edição, efeitos, dublagem, animação, projeção, ingressos) —
--     a PRÓPRIA descrição já diz "destinados diretamente às produções
--     nacionais artísticas, culturais e audiovisuais" ou equivalente: a
--     nacionalidade está EMBUTIDA no texto do item, não só no §1º. Tratados
--     como inciso VII pela mesma proximidade textual.
--   - Itens 36-39 (4 itens): atuações artísticas ao vivo e artistas (autores,
--     compositores, escultores, pintores). Ambíguo entre I (teatro/circo/
--     dança) e II (shows musicais) — mas os DOIS exigem nacionalidade, então
--     a ambiguidade não muda a resposta.
--   - Itens 55-57 (3 itens): sonorização/iluminação/palco/apresentação,
--     "destinados às produções de que trata o art. 139" — SEM specificar
--     qual inciso, porque servem a QUALQUER produção do artigo (inclusive as
--     que NÃO exigem nacionalidade, IV/V/VI). Decisão CONSERVADORA: exigir a
--     condição mesmo assim — o código NBS não distingue qual produção está
--     sendo servida, e a direção seria do erro perigoso caso se assumisse
--     "sem condição" (conceder 60% incondicional a um evento de teatro só
--     porque o mesmo código também atende feiras de negócios).
--
--   GRUPO B — sem condição (não é I/II/III/VII):
--   - Item 22: convenções/feiras de negócios/exposições/eventos — incisos V/VI.
--   - Item 40: museus, mostras e coleções de arte — inciso VI.
--
--   GRUPO C — fora desta migração (já documentado no /build original):
--   - Itens 42-45 (chave NCM, obras de arte — inciso VIII): fora de escopo.
--   - Itens 49-54 (obras teatrais, sem código citável): nunca inseridos.
--
-- Este mapeamento é uma leitura de boa-fé, não uma certeza jurisprudencial —
-- documentado aqui para que qualquer revisão futura saiba exatamente qual
-- premissa está revisando, e por quê.

INSERT INTO anexos_reducao_nbs (anexo, item, sub_item, descricao, dispositivo_legal_ref, condicao_nacionalidade_ref) VALUES
 ('X', 1, 0, 'Licenciamento de direitos de autor e de direitos conexos', 'LCP 214/2025, art. 139, Anexo X, item 1', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 2, 0, 'Licenciamento de direitos de obras literárias', 'LCP 214/2025, art. 139, Anexo X, item 2', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 3, 0, 'Licenciamento de direitos de autor de obras cinematográficas', 'LCP 214/2025, art. 139, Anexo X, item 3', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 4, 0, 'Licenciamento de direitos de autor de obras jornalísticas', 'LCP 214/2025, art. 139, Anexo X, item 4', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 5, 0, 'Licenciamento de direitos conexos de artistas intérpretes ou executantes em obras audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 5', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 6, 0, 'Licenciamento de direitos conexos de produtores de obras audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 6', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 7, 0, 'Licenciamento de direitos de obras audiovisuais destinadas à televisão', 'LCP 214/2025, art. 139, Anexo X, item 7', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 8, 0, 'Licenciamento de direitos de obras musicais e fonogramas', 'LCP 214/2025, art. 139, Anexo X, item 8', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 9, 0, 'Cessão temporária de direitos de obras literárias', 'LCP 214/2025, art. 139, Anexo X, item 9', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 10, 0, 'Cessão temporária de direitos de autor de obras cinematográficas', 'LCP 214/2025, art. 139, Anexo X, item 10', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 11, 0, 'Cessão temporária de direitos de autor de obras jornalísticas', 'LCP 214/2025, art. 139, Anexo X, item 11', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 12, 0, 'Cessão temporária de direitos conexos de artistas intérpretes ou executantes em obras audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 12', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 13, 0, 'Cessão temporária de direitos conexos de produtores de obras audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 13', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 14, 0, 'Cessão temporária de direitos de obras audiovisuais destinadas à televisão', 'LCP 214/2025, art. 139, Anexo X, item 14', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 15, 0, 'Cessão temporária de direitos de obras musicais e fonogramas', 'LCP 214/2025, art. 139, Anexo X, item 15', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 16, 0, 'Cessão definitiva de direitos de obras literárias', 'LCP 214/2025, art. 139, Anexo X, item 16', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 17, 0, 'Cessão definitiva de direitos de obras cinematográficas', 'LCP 214/2025, art. 139, Anexo X, item 17', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 18, 0, 'Cessão definitiva de direitos de obras jornalísticas', 'LCP 214/2025, art. 139, Anexo X, item 18', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 19, 0, 'Cessão definitiva de direitos de obras musicais e fonogramas', 'LCP 214/2025, art. 139, Anexo X, item 19', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 20, 0, 'Serviços de agências de notícias para jornais e periódicos', 'LCP 214/2025, art. 139, Anexo X, item 20', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 21, 0, 'Serviços de agências de notícias para mídia audiovisual', 'LCP 214/2025, art. 139, Anexo X, item 21', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 22, 0, 'Serviços de assistência e organização de convenções, feiras de negócios, exposições e outros eventos', 'LCP 214/2025, art. 139, Anexo X, item 22', NULL),
 ('X', 23, 0, 'Serviços de gravação de som em estúdio destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 23', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 24, 0, 'Serviços de gravação de som ao vivo destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 24', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 25, 0, 'Serviços de produção de programas de televisão, videoteipes e filmes', 'LCP 214/2025, art. 139, Anexo X, item 25', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 26, 0, 'Serviços de produção de programas de rádio', 'LCP 214/2025, art. 139, Anexo X, item 26', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 27, 0, 'Serviços de edição de obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 27', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 28, 0, 'Serviços de duplicação e transferência de obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 28', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 29, 0, 'Serviços de correção de cor e restauração digital de obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 29', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 30, 0, 'Serviços de efeitos visuais em obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 30', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 31, 0, 'Serviços de animação destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 31', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 32, 0, 'Serviços de legendas, títulos e dublagem em obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 32', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 33, 0, 'Serviços de projeto e edição de som em obras audiovisuais destinados diretamente às produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 33', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 34, 0, 'Serviços de projeção de filmes', 'LCP 214/2025, art. 139, Anexo X, item 34', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 35, 0, 'Serviços de produção audiovisual, de apoio e relacionados não classificados em subposições anteriores', 'LCP 214/2025, art. 139, Anexo X, item 35', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 36, 0, 'Serviços de organização e promoção de atuações artísticas ao vivo', 'LCP 214/2025, art. 139, Anexo X, item 36', 'LCP 214/2025, art. 139, §1º c/c incisos I ou II'),
 ('X', 37, 0, 'Serviços de produção e apresentação de atuações artísticas ao vivo, inclusive os ingressos relativos a estes serviços', 'LCP 214/2025, art. 139, Anexo X, item 37', 'LCP 214/2025, art. 139, §1º c/c incisos I ou II'),
 ('X', 38, 0, 'Serviços de atuação artística', 'LCP 214/2025, art. 139, Anexo X, item 38', 'LCP 214/2025, art. 139, §1º c/c incisos I ou II'),
 ('X', 39, 0, 'Serviços de autores, compositores, escultores, pintores e outros artistas, exceto os de atuação artística', 'LCP 214/2025, art. 139, Anexo X, item 39', 'LCP 214/2025, art. 139, §1º c/c incisos I ou II'),
 ('X', 40, 0, 'Serviços de museus, inclusive serviços relativos a mostras e coleções de arte', 'LCP 214/2025, art. 139, Anexo X, item 40', NULL),
 ('X', 41, 0, 'Serviços de reservas de ingressos para eventos de produções nacionais artísticas, culturais e audiovisuais', 'LCP 214/2025, art. 139, Anexo X, item 41', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 46, 0, 'Licenciamento de direitos conexos de artistas intérpretes ou executantes', 'LCP 214/2025, art. 139, Anexo X, item 46', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 47, 0, 'Cessão temporária de direitos de autor e de direitos conexos', 'LCP 214/2025, art. 139, Anexo X, item 47', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 48, 0, 'Cessão temporária de direitos conexos de artistas intérpretes ou executantes', 'LCP 214/2025, art. 139, Anexo X, item 48', 'LCP 214/2025, art. 139, §1º c/c inciso VII'),
 ('X', 55, 0, 'Serviços de sonorização, iluminação, figurino, videografia e cenografia para atuações artísticas ao vivo, destinados às produções de que trata o art. 139 desta Lei Complementar', 'LCP 214/2025, art. 139, Anexo X, item 55', 'LCP 214/2025, art. 139, §1º'),
 ('X', 56, 0, 'Serviços de locação, montagem e desmontagem de palcos, destinados às produções de que trata o art. 139 desta Lei Complementar', 'LCP 214/2025, art. 139, Anexo X, item 56', 'LCP 214/2025, art. 139, §1º'),
 ('X', 57, 0, 'Serviços de apresentação e promoção de atuações artísticas, inclusive gestão de espaços destinados a apresentações de exposições de artes cênicas, espetáculos e demais produções de que trata o art. 139 desta Lei Complementar', 'LCP 214/2025, art. 139, Anexo X, item 57', 'LCP 214/2025, art. 139, §1º')
ON CONFLICT DO NOTHING;

INSERT INTO anexos_reducao_nbs_prefixo (anexo, item, sub_item, prefixo, texto_nbs) VALUES
 ('X', 1, 0, '11103', '1.1103'),
 ('X', 2, 0, '111031000', '1.1103.10.00'),
 ('X', 3, 0, '111033100', '1.1103.31.00'),
 ('X', 4, 0, '111033200', '1.1103.32.00'),
 ('X', 5, 0, '111033400', '1.1103.34.00'),
 ('X', 6, 0, '111033500', '1.1103.35.00'),
 ('X', 7, 0, '1110336', '1.1103.36'),
 ('X', 8, 0, '111034', '1.1103.4'),
 ('X', 9, 0, '111061000', '1.1106.10.00'),
 ('X', 10, 0, '111063100', '1.1106.31.00'),
 ('X', 11, 0, '111063200', '1.1106.32.00'),
 ('X', 12, 0, '111063400', '1.1106.34.00'),
 ('X', 13, 0, '111063500', '1.1106.35.00'),
 ('X', 14, 0, '1110636', '1.1106.36'),
 ('X', 15, 0, '111064', '1.1106.4'),
 ('X', 16, 0, '111071000', '1.1107.10.00'),
 ('X', 17, 0, '111073100', '1.1107.31.00'),
 ('X', 18, 0, '111073200', '1.1107.32.00'),
 ('X', 19, 0, '111074000', '1.1107.40.00'),
 ('X', 20, 0, '117041000', '1.1704.10.00'),
 ('X', 21, 0, '117042000', '1.1704.20.00'),
 ('X', 22, 0, '118066', '1.1806.6'),
 ('X', 23, 0, '125011100', '1.2501.11.00'),
 ('X', 24, 0, '125011200', '1.2501.12.00'),
 ('X', 25, 0, '125012100', '1.2501.21.00'),
 ('X', 26, 0, '125012200', '1.2501.22.00'),
 ('X', 27, 0, '125013100', '1.2501.31.00'),
 ('X', 28, 0, '125013200', '1.2501.32.00'),
 ('X', 29, 0, '125013300', '1.2501.33.00'),
 ('X', 30, 0, '125013400', '1.2501.34.00'),
 ('X', 31, 0, '125013500', '1.2501.35.00'),
 ('X', 32, 0, '125013600', '1.2501.36.00'),
 ('X', 33, 0, '125013700', '1.2501.37.00'),
 ('X', 34, 0, '125015000', '1.2501.50.00'),
 ('X', 35, 0, '125019000', '1.2501.90.00'),
 ('X', 36, 0, '125021000', '1.2502.10.00'),
 ('X', 37, 0, '125022000', '1.2502.20.00'),
 ('X', 38, 0, '125031000', '1.2503.10.00'),
 ('X', 39, 0, '125032000', '1.2503.20.00'),
 ('X', 40, 0, '125041100', '1.2504.11.00'),
 ('X', 41, 0, '118053200', '1.1805.32.00'),
 ('X', 46, 0, '111034200', '1.1103.42.00'),
 ('X', 47, 0, '11106', '1.1106'),
 ('X', 48, 0, '111064200', '1.1106.42.00'),
 ('X', 55, 0, '125023000', '1.2502.30.00'),
 ('X', 56, 0, '101057000', '1.0105.70.00'),
 ('X', 57, 0, '125029000', '1.2502.90.00')
ON CONFLICT DO NOTHING;

-- O Anexo X sobreviveu? (47 itens, 47 prefixos — nenhum é cabeçalho puro
-- desta vez, diferente do Anexo XI, então itens = prefixos aqui.)
DO $$
DECLARE itens int; prefixos int; nacionalidade int;
BEGIN
    SELECT count(*) INTO itens    FROM anexos_reducao_nbs        WHERE anexo = 'X';
    SELECT count(*) INTO prefixos FROM anexos_reducao_nbs_prefixo WHERE anexo = 'X';
    IF (itens, prefixos) <> (47, 47) THEN
        RAISE EXCEPTION 'Anexo X: % itens / % prefixos (esperado 47/47)', itens, prefixos;
    END IF;

    SELECT count(*) INTO nacionalidade FROM anexos_reducao_nbs
        WHERE anexo = 'X' AND condicao_nacionalidade_ref IS NOT NULL;
    IF nacionalidade <> 45 THEN
        RAISE EXCEPTION 'Anexo X: % itens com condição de nacionalidade (esperado 45 = 47 - itens 22 e 40)',
            nacionalidade;
    END IF;

    -- Os Anexos II/III/XI (migração 011) e os 10 Anexos NCM permanecem intactos.
    IF (SELECT count(*) FROM anexos_reducao_nbs WHERE anexo IN ('II','III','XI')) <> 44 THEN
        RAISE EXCEPTION 'Anexos II/III/XI regrediram com a chegada do Anexo X';
    END IF;
    IF (SELECT count(*) FROM anexos_reducao) <> 321
    OR (SELECT count(*) FROM anexos_reducao_ncm) <> 540 THEN
        RAISE EXCEPTION 'Anexos NCM regrediram com a chegada do Anexo X';
    END IF;
END $$;
