-- Anexos II (art. 129, Educação), III (art. 130, Saúde), X (art. 139,
-- produções artísticas/culturais/audiovisuais) e XI (art. 142, soberania e
-- segurança nacional/cibernética) da LCP 214/2025 — redução de 60% de CBS/IBS,
-- primeiro vocabulário do projeto por NBS (Nomenclatura Brasileira de
-- Serviços), não por NCM/SH.
--
-- Fonte primária (consultada em 2026-07-31, DOU Edição Extra nº 11-B de
-- 16/01/2025, espelho legis.senado.leg.br):
--   Anexo II   https://legis.senado.leg.br/norma/40180341/publicacao/40180894
--   Anexo III  https://legis.senado.leg.br/norma/40180341/publicacao/40180900
--   Anexo X    https://legis.senado.leg.br/norma/40180341/publicacao/40180985
--   Anexo XI   https://legis.senado.leg.br/norma/40180341/publicacao/40180991
--   Corpo (arts. 129, 130, 142) https://legis.senado.leg.br/norma/40180341/publicacao/40181429
-- Os 4 Anexos e os arts. 129, 130 e 142 foram lidos e conferidos nesta sessão.
--
-- GAP DOCUMENTADO — Anexo X (art. 139) NÃO é semeado nesta migração: os 47
-- itens NBS do Anexo X foram lidos e transcritos (ver api/reducao_nbs.py e o
-- BUILD_REPORT desta feature para a lista completa), mas o texto do PRÓPRIO
-- art. 139 — que define a quais incisos (I a VIII) cada item pertence, e
-- portanto QUAIS itens exigem nacionalidade de conteúdo (§§1º-3º) — não pôde
-- ser lido nesta sessão: o corpo integral da LCP 214/2025 (544 artigos) excede
-- o que a ferramenta de leitura web deste ambiente processa de uma vez, e não
-- há âncora por artigo na página do Senado. Mesma classe de limitação de
-- acesso já registrada para planalto.gov.br e nbs.economia.gov.br no /define.
-- Semear os itens do Anexo X sem essa classificação arriscaria conceder 60%
-- incondicional a produções estrangeiras que a lei não beneficia (o "risco
-- oposto" que o /define nomeia) — por isso o Anexo X entra no CATÁLOGO (a
-- ordem/percentual/assunto/artigo já estão verificados), mas fica com ZERO
-- itens em `anexos_reducao_nbs` até uma sessão futura conseguir ler o art. 139
-- por completo. Ver Decisão 5 do DESIGN e o BUILD_REPORT.

-- 1) Catálogo: 4 Anexos novos, mesma tabela vocabulário-agnóstica que já
--    descreve os 10 Anexos NCM (migração 009). `zero_por_comprador_ref` fica
--    NULL nos quatro: nenhum tem o mecanismo de upgrade 60%→zero (IV/V/VI) —
--    as condições de X e XI são de GATING (geral→60%), modeladas por ITEM em
--    `anexos_reducao_nbs`, não por Anexo no catálogo (Decisão 4 do DESIGN).
ALTER TABLE anexos_reducao_catalogo DROP CONSTRAINT catalogo_conhecido;
ALTER TABLE anexos_reducao_catalogo ADD CONSTRAINT catalogo_conhecido CHECK (
    (anexo, anexo_ordem, percentual_reducao) IN (
        ('I',1,1.0), ('II',2,0.6), ('III',3,0.6), ('IV',4,0.6), ('V',5,0.6),
        ('VI',6,0.6), ('VII',7,0.6), ('VIII',8,0.6), ('IX',9,0.6),
        ('X',10,0.6), ('XI',11,0.6),
        ('XII',12,1.0), ('XIII',13,1.0), ('XV',15,1.0))
);

INSERT INTO anexos_reducao_catalogo
       (anexo, anexo_ordem, percentual_reducao, assunto, artigo_ref, zero_por_comprador_ref) VALUES
 ('II',  2, 0.6, 'Educação',                                     'LCP 214/2025, art. 129', NULL),
 ('III', 3, 0.6, 'Saúde',                                        'LCP 214/2025, art. 130', NULL),
 ('X',  10, 0.6, 'Produções artísticas, culturais e audiovisuais','LCP 214/2025, art. 139', NULL),
 ('XI', 11, 0.6, 'Soberania e segurança nacional/cibernética',   'LCP 214/2025, art. 142', NULL)
ON CONFLICT (anexo) DO NOTHING;

-- 2) Tabelas dedicadas ao vocabulário NBS — NUNCA comingladas com
--    anexos_reducao/anexos_reducao_ncm (Decisão 1 do DESIGN, Achado crítico 4
--    do /define: um prefixo NBS truncado de 5 dígitos tem o MESMO comprimento
--    que um prefixo NCM válido de 5 dígitos; só tabelas/consultas separadas
--    tornam a colisão estruturalmente impossível).
CREATE TABLE anexos_reducao_nbs (
    anexo    VARCHAR(4) NOT NULL REFERENCES anexos_reducao_catalogo (anexo),
    item     SMALLINT   NOT NULL CHECK (item >= 1),
    sub_item SMALLINT   NOT NULL DEFAULT 0 CHECK (sub_item >= 0),
    descricao TEXT NOT NULL,
    dispositivo_legal_ref TEXT NOT NULL,
    -- Ver Decisão 4 do DESIGN — nulas quando o item NÃO exige a condição
    -- (Anexo II e III inteiros; e o próprio cabeçalho, nunca casado direto).
    condicao_nacionalidade_ref TEXT,  -- Anexo X, art. 139, §§1º-3º
    condicao_comprador_ref     TEXT,  -- Anexo XI, art. 142, I
    condicao_vendedor_ref      TEXT,  -- Anexo XI, art. 142, II (subconjunto)
    -- A citação legal precisa terminar com o Anexo e o item da PRÓPRIA chave
    -- — mesma família de `dispositivo_cita_o_proprio_item` (migração 007).
    CONSTRAINT dispositivo_cita_o_proprio_item_nbs CHECK (
        dispositivo_legal_ref LIKE '%Anexo ' || anexo || ', item '
            || CASE WHEN sub_item = 0 THEN item::text
                    ELSE item::text || '.' || sub_item::text END
    ),
    PRIMARY KEY (anexo, item, sub_item)
);

CREATE TABLE anexos_reducao_nbs_prefixo (
    anexo     VARCHAR(4) NOT NULL,
    item      SMALLINT   NOT NULL,
    sub_item  SMALLINT   NOT NULL DEFAULT 0,
    -- Ver Decisão 2 do DESIGN — só os 4 comprimentos observados nos 90
    -- códigos NBS; espelha api/nbs.py::_COMPRIMENTOS_PREFIXO_NBS (os dois
    -- mudam JUNTOS). Classificador de topo sempre "1" (Assunção A-002).
    prefixo   VARCHAR(9) NOT NULL
        CHECK (prefixo ~ '^1[0-9]*$' AND length(prefixo) IN (5, 6, 7, 9)),
    texto_nbs TEXT NOT NULL,
    FOREIGN KEY (anexo, item, sub_item)
        REFERENCES anexos_reducao_nbs (anexo, item, sub_item) ON DELETE CASCADE,
    UNIQUE (anexo, item, sub_item, prefixo),
    -- `prefixo` é DERIVADO de `texto_nbs` — nenhum dígito digitado duas vezes
    -- sem o banco conferir (mesma família de `prefixo_bate_com_texto`,
    -- migração 005). ÚNICA exceção documentada: o item 29 do Anexo III
    -- publica "1.2301.99.0" (8 dígitos, 1 a menos que o padrão — anomalia
    -- literal da fonte, confirmada no HTML bruto, não erro de transcrição
    -- desta sessão). `texto_nbs` preserva a grafia LITERAL publicada;
    -- `prefixo` é completado para 9 dígitos assumindo que o dígito faltante
    -- é o "0" final do par de item — mesma convenção dos 11 itens irmãos
    -- que citam "1.2301.99.00" (Achado crítico 3). É uma completude
    -- DOCUMENTADA (este comentário + a exceção nomeada na CHECK), nunca uma
    -- correção silenciosa — ver Decisão 6 do DESIGN.
    CONSTRAINT prefixo_bate_com_texto_nbs CHECK (
        (anexo, item, sub_item) = ('III', 29, 0)
        OR prefixo = regexp_replace(texto_nbs, '[^0-9]', '', 'g')
    )
);

CREATE INDEX idx_anexos_reducao_nbs_prefixo ON anexos_reducao_nbs_prefixo (prefixo);

-- 3) Seed — Anexo II (art. 129), 9 itens: 8 NBS + 1 sem código citável (item
--    9, "Educação especial" — célula vazia na fonte, NUNCA inserida: mesma
--    disciplina do item 34 do Anexo IX, migração 010).
INSERT INTO anexos_reducao_nbs (anexo, item, sub_item, descricao, dispositivo_legal_ref) VALUES
 ('II', 1, 0, 'Ensino Infantil, inclusive creche e pré-escola',
  'LCP 214/2025, art. 129, Anexo II, item 1'),
 ('II', 2, 0, 'Ensino Fundamental',
  'LCP 214/2025, art. 129, Anexo II, item 2'),
 ('II', 3, 0, 'Ensino Médio',
  'LCP 214/2025, art. 129, Anexo II, item 3'),
 ('II', 4, 0, 'Ensino Técnico de Nível Médio',
  'LCP 214/2025, art. 129, Anexo II, item 4'),
 ('II', 5, 0, 'Ensino para jovens e adultos destinado àqueles que não tiveram acesso ou continuidade de estudos no ensino fundamental e médio na idade própria',
  'LCP 214/2025, art. 129, Anexo II, item 5'),
 ('II', 6, 0, 'Ensino Superior, compreendidos os cursos e programas de graduação, pós-graduação, de extensão e cursos sequenciais',
  'LCP 214/2025, art. 129, Anexo II, item 6'),
 ('II', 7, 0, 'Ensino de sistemas linguísticos de natureza visomotora e de escrita tátil',
  'LCP 214/2025, art. 129, Anexo II, item 7'),
 ('II', 8, 0, 'Ensino de línguas nativas de povos originários',
  'LCP 214/2025, art. 129, Anexo II, item 8')
ON CONFLICT DO NOTHING;

INSERT INTO anexos_reducao_nbs_prefixo (anexo, item, sub_item, prefixo, texto_nbs) VALUES
 ('II', 1, 0, '122011',    '1.2201.1'),      -- prefixo parcial (1 dígito da subposição)
 ('II', 2, 0, '122012000', '1.2201.20.00'),
 ('II', 3, 0, '122013000', '1.2201.30.00'),
 ('II', 4, 0, '122020000', '1.2202.00.00'),
 ('II', 5, 0, '12203',     '1.2203'),
 ('II', 6, 0, '12204',     '1.2204'),
 ('II', 7, 0, '122051300', '1.2205.13.00'),  -- mesmo código do item 8
 ('II', 8, 0, '122051300', '1.2205.13.00')
ON CONFLICT DO NOTHING;

-- 4) Seed — Anexo III (art. 130), 30 itens, todos NBS (nenhum "sem código").
--    Achado crítico 3: 11 itens compartilham "1.2301.99.00" — os 10 já
--    identificados no /define (18,19,20,21,22,23,24,25,26,28) MAIS o item 29
--    (ver a completude documentada na CHECK acima). O desempate por
--    especificidade elege o de MENOR número (18) como citação principal.
INSERT INTO anexos_reducao_nbs (anexo, item, sub_item, descricao, dispositivo_legal_ref) VALUES
 ('III', 1, 0, 'Serviços cirúrgicos', 'LCP 214/2025, art. 130, Anexo III, item 1'),
 ('III', 2, 0, 'Serviços ginecológicos e obstétricos', 'LCP 214/2025, art. 130, Anexo III, item 2'),
 ('III', 3, 0, 'Serviços psiquiátricos', 'LCP 214/2025, art. 130, Anexo III, item 3'),
 ('III', 4, 0, 'Serviços prestados em Unidades de Terapia Intensiva', 'LCP 214/2025, art. 130, Anexo III, item 4'),
 ('III', 5, 0, 'Serviços de atendimento de urgência', 'LCP 214/2025, art. 130, Anexo III, item 5'),
 ('III', 6, 0, 'Serviços hospitalares não classificados em subposições anteriores', 'LCP 214/2025, art. 130, Anexo III, item 6'),
 ('III', 7, 0, 'Serviços de clínica médica', 'LCP 214/2025, art. 130, Anexo III, item 7'),
 ('III', 8, 0, 'Serviços médicos especializados', 'LCP 214/2025, art. 130, Anexo III, item 8'),
 ('III', 9, 0, 'Serviços odontológicos', 'LCP 214/2025, art. 130, Anexo III, item 9'),
 ('III', 10, 0, 'Serviços de enfermagem', 'LCP 214/2025, art. 130, Anexo III, item 10'),
 ('III', 11, 0, 'Serviços de fisioterapia', 'LCP 214/2025, art. 130, Anexo III, item 11'),
 ('III', 12, 0, 'Serviços laboratoriais', 'LCP 214/2025, art. 130, Anexo III, item 12'),
 ('III', 13, 0, 'Serviços de diagnóstico por imagem', 'LCP 214/2025, art. 130, Anexo III, item 13'),
 ('III', 14, 0, 'Serviços de bancos de material biológico humano', 'LCP 214/2025, art. 130, Anexo III, item 14'),
 ('III', 15, 0, 'Serviços de ambulância', 'LCP 214/2025, art. 130, Anexo III, item 15'),
 ('III', 16, 0, 'Serviços de assistência ao parto e pós-parto', 'LCP 214/2025, art. 130, Anexo III, item 16'),
 ('III', 17, 0, 'Serviços de psicologia', 'LCP 214/2025, art. 130, Anexo III, item 17'),
 ('III', 18, 0, 'Serviços de vigilância sanitária', 'LCP 214/2025, art. 130, Anexo III, item 18'),
 ('III', 19, 0, 'Serviços de epidemiologia', 'LCP 214/2025, art. 130, Anexo III, item 19'),
 ('III', 20, 0, 'Serviços de vacinação', 'LCP 214/2025, art. 130, Anexo III, item 20'),
 ('III', 21, 0, 'Serviços de fonoaudiologia', 'LCP 214/2025, art. 130, Anexo III, item 21'),
 ('III', 22, 0, 'Serviços de nutrição', 'LCP 214/2025, art. 130, Anexo III, item 22'),
 ('III', 23, 0, 'Serviços de optometria', 'LCP 214/2025, art. 130, Anexo III, item 23'),
 ('III', 24, 0, 'Serviços de instrumentação cirúrgica', 'LCP 214/2025, art. 130, Anexo III, item 24'),
 ('III', 25, 0, 'Serviços de biomedicina', 'LCP 214/2025, art. 130, Anexo III, item 25'),
 ('III', 26, 0, 'Serviços farmacêuticos', 'LCP 214/2025, art. 130, Anexo III, item 26'),
 ('III', 27, 0, 'Serviços de cuidado e assistência a idosos e pessoas com deficiência em unidades de acolhimento', 'LCP 214/2025, art. 130, Anexo III, item 27'),
 ('III', 28, 0, 'Serviços domiciliares de apoio a pessoas adultas, idosas, crianças, adolescentes, pessoas com transtornos mentais e com deficiências', 'LCP 214/2025, art. 130, Anexo III, item 28'),
 ('III', 29, 0, 'Serviços de esterilização', 'LCP 214/2025, art. 130, Anexo III, item 29'),
 ('III', 30, 0, 'Serviços funerários, de cremação e de embalsamamento', 'LCP 214/2025, art. 130, Anexo III, item 30')
ON CONFLICT DO NOTHING;

INSERT INTO anexos_reducao_nbs_prefixo (anexo, item, sub_item, prefixo, texto_nbs) VALUES
 ('III', 1, 0, '123011100', '1.2301.11.00'),
 ('III', 2, 0, '123011200', '1.2301.12.00'),
 ('III', 3, 0, '123011300', '1.2301.13.00'),
 ('III', 4, 0, '123011400', '1.2301.14.00'),
 ('III', 5, 0, '123011500', '1.2301.15.00'),
 ('III', 6, 0, '123011900', '1.2301.19.00'),
 ('III', 7, 0, '123012100', '1.2301.21.00'),
 ('III', 8, 0, '123012200', '1.2301.22.00'),
 ('III', 9, 0, '123012300', '1.2301.23.00'),
 ('III', 10, 0, '123019100', '1.2301.91.00'),
 ('III', 11, 0, '123019200', '1.2301.92.00'),
 ('III', 12, 0, '123019300', '1.2301.93.00'),
 ('III', 13, 0, '123019400', '1.2301.94.00'),
 ('III', 14, 0, '123019500', '1.2301.95.00'),
 ('III', 15, 0, '123019600', '1.2301.96.00'),
 ('III', 16, 0, '123019700', '1.2301.97.00'),
 ('III', 17, 0, '123019800', '1.2301.98.00'),
 ('III', 18, 0, '123019900', '1.2301.99.00'),
 ('III', 19, 0, '123019900', '1.2301.99.00'),
 ('III', 20, 0, '123019900', '1.2301.99.00'),
 ('III', 21, 0, '123019900', '1.2301.99.00'),
 ('III', 22, 0, '123019900', '1.2301.99.00'),
 ('III', 23, 0, '123019900', '1.2301.99.00'),
 ('III', 24, 0, '123019900', '1.2301.99.00'),
 ('III', 25, 0, '123019900', '1.2301.99.00'),
 ('III', 26, 0, '123019900', '1.2301.99.00'),
 ('III', 27, 0, '12302',     '1.2302'),
 ('III', 28, 0, '123019900', '1.2301.99.00'),
 ('III', 29, 0, '123019900', '1.2301.99.0'),   -- anomalia de 1 dígito, ver CHECK acima
 ('III', 30, 0, '126030000', '1.2603.00.00')
ON CONFLICT DO NOTHING;

-- 5) Seed — Anexo XI (art. 142), Bloco 1 "SERVIÇOS": só os 5 itens NBS
--    resolvíveis nesta feature (1.1, 1.2, 1.3, 1.13, 1.14). Os vetados
--    (1.4, 1.5, 1.8, 1.9 — Mensagem de Veto Parcial nº 88/2025) e os "sem
--    código atribuído" (1.6, 1.7, 1.10, 1.11, 1.12) NUNCA são inseridos —
--    tratados como se não existissem no Anexo, nunca como "excluído
--    expressamente" nem como célula vazia. O item 1 é CABEÇALHO (o DOU não
--    lhe dá código próprio; existe só para numerar 1.1-1.14) — entra como
--    item sem prefixo, mesmo padrão dos cabeçalhos dos Anexos XII/XIII/V.
--
--    Eixo COMPRADOR (art. 142, I — administração pública direta, autarquia
--    ou fundação pública): vale para QUALQUER item do Anexo XI — os 5
--    recebem `condicao_comprador_ref`. Reaproveita a MESMA definição textual
--    de `CompradorTipo.ORGAO_PUBLICO`; `ENTIDADE_CEBAS_SUS` NUNCA satisfaz
--    esta condição (nenhuma base no art. 142 — AT-012).
--
--    Eixo VENDEDOR (art. 142, II — sócio brasileiro ≥20% do capital, só para
--    serviços de segurança da informação/cibernética): só o item 1.1
--    ("Segurança em Tecnologia da Informação") recebe `condicao_vendedor_ref`
--    nesta feature — sua descrição é a única, das 5, inequivocamente
--    "segurança da informação/cibernética". Os itens 1.2 ("projeto e
--    desenvolvimento de aplicativos", posição 1502) e 1.3 ("TI não
--    classificados", posição 1510, catch-all da família 15xx) são
--    genuinely ambíguos sem a nomenclatura NBS oficial (inacessível —
--    nbs.economia.gov.br, NXDOMAIN) para confirmar se contam como "segurança
--    da informação/cibernética" — decisão conservadora documentada aqui, não
--    presumida a favor do benefício. 1.13/1.14 (manutenção de veículos e
--    equipamentos militares) claramente não se qualificam.
INSERT INTO anexos_reducao_nbs (anexo, item, sub_item, descricao, dispositivo_legal_ref,
                                 condicao_comprador_ref, condicao_vendedor_ref) VALUES
 ('XI', 1, 0, 'Serviços',
  'LCP 214/2025, art. 142, Anexo XI, item 1', NULL, NULL),
 ('XI', 1, 1, 'Segurança em Tecnologia da Informação (TI)',
  'LCP 214/2025, art. 142, Anexo XI, item 1.1',
  'LCP 214/2025, art. 142, I', 'LCP 214/2025, art. 142, II'),
 ('XI', 1, 2, 'Serviços de projeto e desenvolvimento de aplicativos e programas em TI não classificados em subposições anteriores',
  'LCP 214/2025, art. 142, Anexo XI, item 1.2',
  'LCP 214/2025, art. 142, I', NULL),
 ('XI', 1, 3, 'Serviços de Tecnologia da Informação (TI) não classificados em subposições anteriores',
  'LCP 214/2025, art. 142, Anexo XI, item 1.3',
  'LCP 214/2025, art. 142, I', NULL),
 ('XI', 1, 13, 'Serviços de manutenção e reparação de veículos militares para uso pela segurança nacional',
  'LCP 214/2025, art. 142, Anexo XI, item 1.13',
  'LCP 214/2025, art. 142, I', NULL),
 ('XI', 1, 14, 'Serviços de manutenção e reparação de equipamentos militares para uso pela segurança nacional',
  'LCP 214/2025, art. 142, Anexo XI, item 1.14',
  'LCP 214/2025, art. 142, I', NULL)
ON CONFLICT DO NOTHING;

INSERT INTO anexos_reducao_nbs_prefixo (anexo, item, sub_item, prefixo, texto_nbs) VALUES
 ('XI', 1, 1, '115012000', '1.1501.20.00'),
 ('XI', 1, 2, '115029000', '1.1502.90.00'),
 ('XI', 1, 3, '115100000', '1.1510.00.00'),
 ('XI', 1, 13, '120013500', '1.2001.35.00'),
 ('XI', 1, 14, '120018300', '1.2001.83.00')
ON CONFLICT DO NOTHING;

-- 6) Contagens (MUST "zero regressão" do DEFINE, provado pela própria
--    migração — mesmo padrão das 5 anteriores).
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT * FROM (VALUES ('II',8,8), ('III',30,30), ('XI',6,5))
                          AS e(anexo, itens, prefixos) LOOP
        IF (SELECT count(*) FROM anexos_reducao_nbs        WHERE anexo = r.anexo) <> r.itens
        OR (SELECT count(*) FROM anexos_reducao_nbs_prefixo WHERE anexo = r.anexo) <> r.prefixos THEN
            RAISE EXCEPTION 'Anexo % (NBS): contagem não bate com a transcrição do BUILD_REPORT', r.anexo;
        END IF;
    END LOOP;

    IF (SELECT count(*) FROM anexos_reducao_nbs WHERE anexo = 'X') <> 0 THEN
        RAISE EXCEPTION 'Anexo X deveria ter 0 itens nesta migração (gap documentado — ver cabeçalho)';
    END IF;

    IF (SELECT count(*) FROM anexos_reducao_catalogo) <> 14 THEN
        RAISE EXCEPTION 'catálogo com contagem inesperada (esperado 14 = 10 + 4 novos)';
    END IF;

    -- Os 10 Anexos NCM já shipados sobreviveram intactos (a ALTER do
    -- catálogo é aditiva; nenhuma linha existente foi tocada).
    IF (SELECT count(*) FROM anexos_reducao) <> 321
    OR (SELECT count(*) FROM anexos_reducao_ncm) <> 540 THEN
        RAISE EXCEPTION 'Anexos NCM não sobreviveram à extensão do catálogo — regressão';
    END IF;
END $$;

-- Mesmo padrão da 004/005/007/009: GRANT ... ON ALL TABLES não é retroativo;
-- as tabelas NBS são NOVAS e precisam do seu. Degradação conservadora: um
-- GRANT faltando não gera erro — gera CONSULTA_INDISPONIVEL silencioso com a
-- alíquota geral, mesma disciplina do lado NCM.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON anexos_reducao_nbs         TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON anexos_reducao_nbs_prefixo TO taxreformai_app';
    END IF;
END $$;
