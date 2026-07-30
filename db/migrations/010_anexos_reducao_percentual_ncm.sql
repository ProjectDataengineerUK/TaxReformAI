-- Anexos IV (art. 131), V (art. 132), VI (art. 133, § 1º), VII (art. 135),
-- VIII (art. 136) e IX (art. 138) da LCP 214/2025 — redução de 60% (SESSENTA
-- POR CENTO) das alíquotas do IBS e da CBS, por NCM/SH.
--
-- O percentual NÃO está aqui: vem de `anexos_reducao_catalogo` (migração 009),
-- uma linha por Anexo. Uma constante de código, ou uma coluna por item,
-- divergiria no primeiro Anexo novo.
--
-- Fonte primária desta transcrição (consultada em 2026-07-29, DOU Edição Extra
-- nº 11-B de 16/01/2025), extraída da estrutura <tr>/<td> da tabela, não do
-- texto renderizado:
--   Anexo IV   https://legis.senado.leg.br/norma/40180341/publicacao/40180906 (p. 48)
--   Anexo V    https://legis.senado.leg.br/norma/40180341/publicacao/40180912 (p. 50)
--   Anexo VI   https://legis.senado.leg.br/norma/40180341/publicacao/40180918 (p. 50)
--   Anexo VII  https://legis.senado.leg.br/norma/40180341/publicacao/40180967 (p. 51)
--   Anexo VIII https://legis.senado.leg.br/norma/40180341/publicacao/40180973 (p. 51)
--   Anexo IX   https://legis.senado.leg.br/norma/40180341/publicacao/40180979 (p. 51-52)
--   Corpo      https://legis.senado.leg.br/norma/40180341/publicacao/40181429 (arts. 129-148)
--
-- LC 227/2026: entre os arts. 129-148 alterou SÓ o art. 146 (categoria
-- terapêutica de medicamentos + revogação do Anexo XIV), e entre Anexos tocou
-- 7 (alteração VETADA), 14 (revogação), 20 e 21. Ou seja: a nova redação
-- proposta ao ITEM 2 DO ANEXO VII nunca entrou em vigor, e o texto transcrito
-- abaixo é o ORIGINAL. Nenhum dos arts. 131, 132, 133, 135, 136, 138, 144 e
-- 145 foi tocado. A cláusula do art. 146, § 2º (zero para o Anexo VI conforme o
-- comprador) é substancialmente idêntica antes e depois.
--
-- A `descricao` é o texto LITERAL da célula do DOU, com a grafia dela —
-- inclusive as que parecem erro de digitação do próprio Diário ("Fórmula para
-- dieta isenta demetionina", Anexo VI, item 40). Corrigir a fonte é
-- editorializar um documento de auditoria.
--
--
-- CLÁUSULAS "EXCETO"/"RESSALVADO" — quatro classes, e só uma vira linha:
--
--   A cláusula nomeia código(s) NCM?
--   ├─ NÃO  → NÃO CODIFICÁVEL. Zero linhas. Vira limitação declarada.
--   └─ SIM  → nomeia um ANEXO inteiro em vez de códigos?
--             ├─ SIM → REMISSÃO. Zero linhas — resolvida pelo desempate por
--             │         especificidade, e provada pela asserção (6) no fim.
--             └─ NÃO → o código nomeado desce de uma INCLUSÃO do MESMO item?
--                       ├─ SIM → OPERANTE.    1 linha com excecao = TRUE.
--                       └─ NÃO → DESCRITIVA.  Zero linhas (seria inerte).
--
--   IV/48   "exceto as preparadas como medicamentos..."   NÃO CODIFICÁVEL  0
--   IV/49   "exceto os da posição 30.06"                  DESCRITIVA       0
--   IV/51   "exceto cimentos"                             NÃO CODIFICÁVEL  0
--   IV/54   "exceto bolsas para colostomia..."            NÃO CODIFICÁVEL  0
--   IV/61   "exceto as de metal e as para suturas"        NÃO CODIFICÁVEL  0
--   IV/68   "excluídas seringas e agulhas, das posições
--            9018.31 e 9018.32"                           DESCRITIVA       0
--   VII/1   "(exceto lagostas e lagostim)"                NÃO CODIFICÁVEL  0
--   VII/1   "exceto 0306.11, 0306.15.00, 0306.31.00,
--            0306.34.00, 0306.39.10"                      OPERANTE         5
--   VII/4,5,6,15 "ressalvados os produtos do Anexo I"     REMISSÃO         0
--   VII/14  "ressalvadas as frutas de casca rija não
--            regionais"                                   NÃO CODIFICÁVEL  0
--   VII/14  "os produtos relacionados nos Anexos I e XV"  REMISSÃO (dupla) 0
--   VII/14  "excetuadas as posições 07.11, 08.12 e
--            0814.00.00"                                  OPERANTE         3
--   IX/12,13,18,19,20,21 "exceto de animais domésticos" /
--           "exceto as ornamentais"                       NÃO CODIFICÁVEL  0
--   V, VI, VIII  (nenhuma cláusula em todo o Anexo)       —                0
--
-- Total: 8 linhas de exceção, todas no Anexo VII, todas OPERANTES.
--
--
-- ANEXO IX — OS 13 ITENS QUE **NÃO** ENTRAM NA TABELA, considerados e
-- descartados (não esquecidos). Doze têm chave NBS, que é vocabulário de
-- SERVIÇO e depende dos Anexos II/III/X/XI (posição 14 do roadmap); o item 34
-- não tem chave nenhuma — célula vazia na fonte — e não é resolvível por
-- nenhuma feature futura, porque não há o que casar.
--
--   22 Serviços agronômicos                                 NBS 1.1410.90.00
--   23 Serviços de técnico agrícola, agropecuário ou em
--      agroecologia                                         NBS 1.1410.90.00
--   24 Serviços veterinários para produção animal            NBS 1.1405.21.00,
--                                                               1.1405.22.00,
--                                                               1.1405.90.00
--   25 Serviços de zootecnistas                              NBS 1.1410.90.00
--   26 Serviços de inseminação e fertilização de animais
--      de criação                                           NBS 1.1405.22.00
--   27 Serviços de engenharia florestal                      NBS 1.1403.10.00
--   28 Serviços de pulverização e controle de pragas         NBS 1.1901.10.00
--   29 Serviços de semeadura, adubação, inclusive mistura
--      de adubos, reparação de solo, plantio e colheita      NBS 1.1901.10.00
--   30 Serviços de projetos para irrigação e fertirrigação   NBS 1.1403.29.00
--   31 Serviços de análise laboratorial de solos, sementes
--      e outros materiais propagativos, fitossanitários,
--      água de produção, bromatologia e sanidade animal      NBS 1.1404.41.00
--   32 Licenciamento de direitos sobre cultivares            NBS 1.1105.10.00
--   33 Cessão definitiva de direitos sobre cultivares        NBS 1.1109.10.00
--   34 Melhoramento genético de animais e plantas e
--      biotecnologia, inclusive seus royalties               NENHUMA
--
-- Observação que vale registrar: um código NBS sem pontuação tem NOVE dígitos
-- (1.1410.90.00 -> 114109000) e a CHECK `prefixo_comprimento_valido` só admite
-- {2,4,5,6,7,8}. O banco RECUSARIA uma transcrição de NBS nesta tabela, mesmo
-- que alguém tentasse.
--
--
-- AS 4 SOBREPOSIÇÕES EM QUE O 60% VENCE A REDUÇÃO A ZERO — lista fechada,
-- fixada por teste (Decisão 4). Em todas, o legislador escreveu um código MAIS
-- PRECISO no Anexo de 60% e um mais amplo no de zero, e o erro é na direção
-- SEGURA (cobra mais tributo, não menos):
--
--   0601.10.00  XV/4  `06`      (capítulo)  perde para  IX/11 `06.01`
--   0602.90.90  XV/4  `06`      (capítulo)  perde para  IX/11 `06.02`
--   9025.19.90  XII/12 `90.25`  (posição)   perde para  V/2.3 `9025.19.90`
--   9018.20.10  XII/2  `9018.20`(subpos.)   perde para  IV/70 `9018.20.10`
--
-- Se aparecer um quinto, `tests/test_reducao_db.py` falha.
--
--
-- LIMITAÇÃO DECLARADA, a única desta migração cujo erro é tributo A MENOS:
-- 13 prefixos de 2 dígitos concedem 60% a CAPÍTULOS INTEIROS da NCM enquanto o
-- texto do item restringe por destinação ou conformidade. O pior é o Capítulo
-- 25 (IX/3, "corretivos de solo"), que na NCM inclui cimento, mármore e gesso.
-- Mitigação: a resposta marca `tipo_correspondencia = 'CAPITULO'` e devolve a
-- `descricao` literal. Não carregar os capítulos foi considerado e recusado:
-- negaria uma redução que a lei concede, em cima de código que a lei escreveu.
--
-- Contagens: IV 105 itens/112 linhas · V 29/30 · VI 81/86 · VII 17/53 ·
-- VIII 7/7 · IX 22/101 — total 261 itens, 389 linhas (381 inclusões + 8
-- exceções).

INSERT INTO anexos_reducao (anexo, item, sub_item, descricao, dispositivo_legal_ref) VALUES
 -- ANEXO IV — dispositivos médicos (art. 131; zero por comprador: art. 144, II)
 ('IV', 1, 0, 'Bolsa para drenagem', 'LCP 214/2025, art. 131, Anexo IV, item 1'),
 ('IV', 2, 0, 'Sistema para drenagem com conjunto intermediário para medição contínua da diurese', 'LCP 214/2025, art. 131, Anexo IV, item 2'),
 ('IV', 3, 0, 'Chapas e filmes para raios-X, sensibilizados em uma face', 'LCP 214/2025, art. 131, Anexo IV, item 3'),
 ('IV', 4, 0, 'Cimentos para reconstituição óssea', 'LCP 214/2025, art. 131, Anexo IV, item 4'),
 ('IV', 5, 0, 'Substitutos de enxerto ósseo', 'LCP 214/2025, art. 131, Anexo IV, item 5'),
 ('IV', 6, 0, 'Coletor para unidade de drenagem externa', 'LCP 214/2025, art. 131, Anexo IV, item 6'),
 ('IV', 7, 0, 'Conector completo com tampa', 'LCP 214/2025, art. 131, Anexo IV, item 7'),
 ('IV', 8, 0, 'Conector em Y', 'LCP 214/2025, art. 131, Anexo IV, item 8'),
 ('IV', 9, 0, 'Conjuntos de troca e concentrados polieletrolíticos para diálise', 'LCP 214/2025, art. 131, Anexo IV, item 9'),
 ('IV', 10, 0, 'Conjunto para autotransfusão', 'LCP 214/2025, art. 131, Anexo IV, item 10'),
 ('IV', 11, 0, 'Conjunto para hidrocefalia de baixo perfil', 'LCP 214/2025, art. 131, Anexo IV, item 11'),
 ('IV', 12, 0, 'Conjunto para hidrocefalia standard', 'LCP 214/2025, art. 131, Anexo IV, item 12'),
 ('IV', 13, 0, 'Eletrodo endocárdico definitivo', 'LCP 214/2025, art. 131, Anexo IV, item 13'),
 ('IV', 14, 0, 'Eletrodo epicárdico definitivo', 'LCP 214/2025, art. 131, Anexo IV, item 14'),
 ('IV', 15, 0, 'Eletrodo para marcapasso temporário endocárdico', 'LCP 214/2025, art. 131, Anexo IV, item 15'),
 ('IV', 16, 0, 'Eletrodo para marcapasso temporário epicárdico', 'LCP 214/2025, art. 131, Anexo IV, item 16'),
 ('IV', 17, 0, 'Espaçador de tendão', 'LCP 214/2025, art. 131, Anexo IV, item 17'),
 ('IV', 18, 0, 'Filmes especiais para raios-X sensibilizados em ambas as faces', 'LCP 214/2025, art. 131, Anexo IV, item 18'),
 ('IV', 19, 0, 'Filmes especiais para raios-X sensibilizados em uma face', 'LCP 214/2025, art. 131, Anexo IV, item 19'),
 ('IV', 20, 0, 'Filtro de linha arterial e venoso', 'LCP 214/2025, art. 131, Anexo IV, item 20'),
 ('IV', 21, 0, 'Filtro de sangue arterial e venoso para recirculação', 'LCP 214/2025, art. 131, Anexo IV, item 21'),
 ('IV', 22, 0, 'Filtro para cardioplegia', 'LCP 214/2025, art. 131, Anexo IV, item 22'),
 ('IV', 23, 0, 'Categutes esterilizados, materiais esterilizados semelhantes para suturas cirúrgicas (incluídos os fios absorvíveis esterilizados para cirurgia ou odontologia) e adesivos esterilizados para tecidos orgânicos, utilizados em cirurgia para fechar ferimentos; laminárias esterilizadas; hemostáticos absorvíveis esterilizados para cirurgia ou odontologia; barreiras antiaderentes esterilizadas para cirurgia ou odontologia, absorvíveis ou não', 'LCP 214/2025, art. 131, Anexo IV, item 23'),
 ('IV', 24, 0, 'Hemoconcentrador para circulação extracorpórea', 'LCP 214/2025, art. 131, Anexo IV, item 24'),
 ('IV', 25, 0, 'Hemodialisador capilar', 'LCP 214/2025, art. 131, Anexo IV, item 25'),
 ('IV', 26, 0, 'Marcapasso cardíaco câmara dupla', 'LCP 214/2025, art. 131, Anexo IV, item 26'),
 ('IV', 27, 0, 'Marcapasso cardíaco multiprogramável com telemetria', 'LCP 214/2025, art. 131, Anexo IV, item 27'),
 ('IV', 28, 0, 'Outras chapas e filmes para raios-X', 'LCP 214/2025, art. 131, Anexo IV, item 28'),
 ('IV', 29, 0, 'Oxigenador de bolha com tubos para circulação extracorpórea', 'LCP 214/2025, art. 131, Anexo IV, item 29'),
 ('IV', 30, 0, 'Oxigenador de membrana com tubos para circulação extracorpórea', 'LCP 214/2025, art. 131, Anexo IV, item 30'),
 ('IV', 31, 0, 'Reservatório de cardiotomia', 'LCP 214/2025, art. 131, Anexo IV, item 31'),
 ('IV', 32, 0, 'Reservatório para cardioplegia com tubo sem filtro', 'LCP 214/2025, art. 131, Anexo IV, item 32'),
 ('IV', 33, 0, 'Rins artificiais', 'LCP 214/2025, art. 131, Anexo IV, item 33'),
 ('IV', 34, 0, 'Shunt lombo-peritonal', 'LCP 214/2025, art. 131, Anexo IV, item 34'),
 ('IV', 35, 0, 'Substituto temporário de pele (biológica/sintética) (por cm2)', 'LCP 214/2025, art. 131, Anexo IV, item 35'),
 ('IV', 36, 0, 'Tela inorgânica', 'LCP 214/2025, art. 131, Anexo IV, item 36'),
 ('IV', 37, 0, 'Válvula para hidrocefalia', 'LCP 214/2025, art. 131, Anexo IV, item 37'),
 ('IV', 38, 0, 'Válvula para tratamento de ascite', 'LCP 214/2025, art. 131, Anexo IV, item 38'),
 ('IV', 39, 0, 'Fonte de irídio 192', 'LCP 214/2025, art. 131, Anexo IV, item 39'),
 ('IV', 40, 0, 'Stent vascular', 'LCP 214/2025, art. 131, Anexo IV, item 40'),
 ('IV', 41, 0, 'Reprocessador de filtros utilizados em hemodiálise', 'LCP 214/2025, art. 131, Anexo IV, item 41'),
 ('IV', 42, 0, 'Implantes osseointegráveis, na forma de parafuso, e seus componentes manufaturados, tais como tampas de proteção, montadores, conjuntos, pilares (cicatrizador, conector, de transferência ou temporário), cilindros, seus acessórios, destinados a sustentar, amparar, acoplar ou fixar próteses dentárias', 'LCP 214/2025, art. 131, Anexo IV, item 42'),
 ('IV', 43, 0, 'Cardiodesfibrilador implantável', 'LCP 214/2025, art. 131, Anexo IV, item 43'),
 ('IV', 44, 0, 'Espiral para embolização', 'LCP 214/2025, art. 131, Anexo IV, item 44'),
 ('IV', 45, 0, 'Imunoglobulina anti-Rh', 'LCP 214/2025, art. 131, Anexo IV, item 45'),
 ('IV', 46, 0, 'Outras imunoglobulinas séricas', 'LCP 214/2025, art. 131, Anexo IV, item 46'),
 ('IV', 47, 0, 'Concentrado de fator VIII', 'LCP 214/2025, art. 131, Anexo IV, item 47'),
 ('IV', 48, 0, 'Outras frações do sangue, exceto as preparadas como medicamentos, as imunoglobulinas séricas, o concentrado de fator VIII e a soroalbumina sob a forma de gel para preparação de reagentes de diagnóstico', 'LCP 214/2025, art. 131, Anexo IV, item 48'),
 ('IV', 49, 0, 'Reagentes de diagnóstico ou de laboratório em qualquer suporte e reagentes de diagnóstico ou de laboratório preparados, mesmo em um suporte, mesmo apresentados sob a forma de estojos, exceto os da posição 30.06; materiais de referência certificados', 'LCP 214/2025, art. 131, Anexo IV, item 49'),
 ('IV', 50, 0, 'Reagentes de diagnóstico concebidos para serem administrados ao paciente, à base de somatoliberina', 'LCP 214/2025, art. 131, Anexo IV, item 50'),
 ('IV', 51, 0, 'Produtos para obturação dentária, exceto cimentos', 'LCP 214/2025, art. 131, Anexo IV, item 51'),
 ('IV', 52, 0, 'Preparações em gel, concebidas para uso em medicina humana ou veterinária como lubrificante para certas partes do corpo em intervenções cirúrgicas ou exames médicos ou como agente de ligação entre o corpo e os instrumentos médicos', 'LCP 214/2025, art. 131, Anexo IV, item 52'),
 ('IV', 53, 0, 'Bolsas para uso em colostomia, ileostomia e urostomia', 'LCP 214/2025, art. 131, Anexo IV, item 53'),
 ('IV', 54, 0, 'Equipamentos identificáveis para ostomia, exceto bolsas para uso em colostomia, ileostomia e urostomia', 'LCP 214/2025, art. 131, Anexo IV, item 54'),
 ('IV', 55, 0, 'Bolsas para uso em medicina (hemodiálise e usos semelhantes)', 'LCP 214/2025, art. 131, Anexo IV, item 55'),
 ('IV', 56, 0, 'Artigos exclusivamente de laboratório de análises clínicas', 'LCP 214/2025, art. 131, Anexo IV, item 56'),
 ('IV', 57, 0, 'Acessórios de plástico do tipo utilizado em linhas de sangue para hemodiálise, tais como: obturadores, incluídos os reguláveis (clamps), clipes e similares', 'LCP 214/2025, art. 131, Anexo IV, item 57'),
 ('IV', 58, 0, 'Luvas cirúrgicas e luvas de procedimento', 'LCP 214/2025, art. 131, Anexo IV, item 58'),
 ('IV', 59, 0, 'Seringas, mesmo com agulhas', 'LCP 214/2025, art. 131, Anexo IV, item 59'),
 ('IV', 60, 0, 'Agulhas tubulares de metal e agulhas para suturas', 'LCP 214/2025, art. 131, Anexo IV, item 60'),
 ('IV', 61, 0, 'Agulhas, exceto as de metal e as para suturas', 'LCP 214/2025, art. 131, Anexo IV, item 61'),
 ('IV', 62, 0, 'Sondas, cateteres e cânulas, individualmente ou em conjunto', 'LCP 214/2025, art. 131, Anexo IV, item 62'),
 ('IV', 63, 0, 'Lancetas para vacinação e cautérios', 'LCP 214/2025, art. 131, Anexo IV, item 63'),
 ('IV', 64, 0, 'Instrumentos semelhantes a seringas, a agulhas, a cateteres e a cânulas', 'LCP 214/2025, art. 131, Anexo IV, item 64'),
 ('IV', 65, 0, 'Brocas para odontologia', 'LCP 214/2025, art. 131, Anexo IV, item 65'),
 ('IV', 66, 0, 'Limas', 'LCP 214/2025, art. 131, Anexo IV, item 66'),
 ('IV', 67, 0, 'Grampos e clipes, seus aplicadores e extratores', 'LCP 214/2025, art. 131, Anexo IV, item 67'),
 ('IV', 68, 0, 'Outros instrumentos e aparelhos para medicina, cirurgia e odontologia, excluídas seringas e agulhas, das posições 9018.31 e 9018.32', 'LCP 214/2025, art. 131, Anexo IV, item 68'),
 ('IV', 69, 0, 'Mesas de operação e para exames, camas hospitalares e de uso clínico', 'LCP 214/2025, art. 131, Anexo IV, item 69'),
 ('IV', 70, 0, 'Fotocoagulador a laser', 'LCP 214/2025, art. 131, Anexo IV, item 70'),
 ('IV', 71, 0, 'Bisturi elétrico', 'LCP 214/2025, art. 131, Anexo IV, item 71'),
 ('IV', 72, 0, 'Aparelho de anestesia com monitor multiparâmetros', 'LCP 214/2025, art. 131, Anexo IV, item 72'),
 ('IV', 73, 0, 'Autoclave', 'LCP 214/2025, art. 131, Anexo IV, item 73'),
 ('IV', 74, 0, 'Retinógrafo', 'LCP 214/2025, art. 131, Anexo IV, item 74'),
 ('IV', 75, 0, 'Meios de cultura', 'LCP 214/2025, art. 131, Anexo IV, item 75'),
 ('IV', 76, 0, 'Termocicladores utilizados em diagnóstico e na pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 76'),
 ('IV', 77, 0, 'Partes e peças de termocicladores', 'LCP 214/2025, art. 131, Anexo IV, item 77'),
 ('IV', 78, 0, 'Pipetadores laboratoriais para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 78'),
 ('IV', 79, 0, 'Cromatógrafo de fase líquida', 'LCP 214/2025, art. 131, Anexo IV, item 79'),
 ('IV', 80, 0, 'Sequenciadores automáticos de ADN mediante eletroforese capilar', 'LCP 214/2025, art. 131, Anexo IV, item 80'),
 ('IV', 81, 0, 'Aparelhos de eletroforese para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 81'),
 ('IV', 82, 0, 'Analisadores por espectrofotometria para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 82'),
 ('IV', 83, 0, 'Analisadores por fotometria para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 83'),
 ('IV', 84, 0, 'Citômetro de fluxo', 'LCP 214/2025, art. 131, Anexo IV, item 84'),
 ('IV', 85, 0, 'Analisadores por radiações ópticas para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 85'),
 ('IV', 86, 0, 'Outros analisadores para diagnóstico e pesquisa científica', 'LCP 214/2025, art. 131, Anexo IV, item 86'),
 ('IV', 87, 0, 'Espectrômetro de massa', 'LCP 214/2025, art. 131, Anexo IV, item 87'),
 ('IV', 88, 0, 'Outros analisadores para diagnóstico', 'LCP 214/2025, art. 131, Anexo IV, item 88'),
 ('IV', 89, 0, 'Micrótomo', 'LCP 214/2025, art. 131, Anexo IV, item 89'),
 ('IV', 90, 0, 'Partes e peças de equipamentos analisadores laboratoriais', 'LCP 214/2025, art. 131, Anexo IV, item 90'),
 ('IV', 91, 0, 'Preservativo', 'LCP 214/2025, art. 131, Anexo IV, item 91'),
 ('IV', 92, 0, 'Dispositivo intrauterino (DIU)', 'LCP 214/2025, art. 131, Anexo IV, item 92'),
 ('IV', 93, 0, 'Substância para conservação de órgãos e tecidos', 'LCP 214/2025, art. 131, Anexo IV, item 93'),
 ('IV', 94, 0, 'Introdutor de punção para implante de eletrodo endocárdico', 'LCP 214/2025, art. 131, Anexo IV, item 94'),
 ('IV', 95, 0, 'Enxerto tubular de politetrafluoretileno - PTFE (por cm2)', 'LCP 214/2025, art. 131, Anexo IV, item 95'),
 ('IV', 96, 0, 'Enxerto arterial e venoso tubular inorgânico', 'LCP 214/2025, art. 131, Anexo IV, item 96'),
 ('IV', 97, 0, 'Botão para crânio', 'LCP 214/2025, art. 131, Anexo IV, item 97'),
 ('IV', 98, 0, 'Guia metálico para introdução de cateter duplo lumen', 'LCP 214/2025, art. 131, Anexo IV, item 98'),
 ('IV', 99, 0, 'Dilatador para implante de cateter duplo lumen', 'LCP 214/2025, art. 131, Anexo IV, item 99'),
 ('IV', 100, 0, 'Guia de troca para angioplastia', 'LCP 214/2025, art. 131, Anexo IV, item 100'),
 ('IV', 101, 0, 'Introdutor para cateter com e sem válvula', 'LCP 214/2025, art. 131, Anexo IV, item 101'),
 ('IV', 102, 0, 'Kit cânula', 'LCP 214/2025, art. 131, Anexo IV, item 102'),
 ('IV', 103, 0, 'Dreno para sucção', 'LCP 214/2025, art. 131, Anexo IV, item 103'),
 ('IV', 104, 0, 'Sistema de drenagem mediastinal', 'LCP 214/2025, art. 131, Anexo IV, item 104'),
 ('IV', 105, 0, 'Conjunto descartável de balão intra-aórtico', 'LCP 214/2025, art. 131, Anexo IV, item 105'),

 -- ANEXO V — acessibilidade (art. 132; zero por comprador: art. 145, II).
 -- Os itens 1, 2 e 3 são CABEÇALHOS: o DOU não lhes dá célula de NCM e sem
 -- eles a descrição de 1.1 ("Comando de embreagem manual...") perde o sujeito.
 ('V', 1, 0, 'ACESSÓRIOS E ADAPTAÇÕES ESPECIAIS PARA SEREM INSTALADOS EM VEÍCULOS AUTOMOTORES PERTENCENTES OU QUE FOREM DESTINADOS A PESSOAS COM DEFICIÊNCIA FÍSICA', 'LCP 214/2025, art. 132, Anexo V, item 1'),
 ('V', 1, 1, 'Comando de embreagem manual, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.1'),
 ('V', 1, 2, 'Comando de freio manual, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.2'),
 ('V', 1, 3, 'Comando de acelerador manual, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.3'),
 ('V', 1, 4, 'Inversão do pedal do acelerador, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.4'),
 ('V', 1, 5, 'Prolongamento de pedais, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.5'),
 ('V', 1, 6, 'Empunhadura, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.6'),
 ('V', 1, 7, 'Servo acionadores de volante, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.7'),
 ('V', 1, 8, 'Deslocamento de comandos do painel, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.8'),
 ('V', 1, 9, 'Plataforma giratória para deslocamento giratório do assento de veículo, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.9'),
 ('V', 1, 10, 'Trilho elétrico para deslocamento do assento dianteiro para outra parte do interior do veículo, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.10'),
 ('V', 1, 11, 'Plataforma de elevação para cadeira de rodas, manual, eletro-hidráulica ou eletromecânica', 'LCP 214/2025, art. 132, Anexo V, item 1.11'),
 ('V', 1, 12, 'Rampa para cadeira de rodas, suas partes e acessórios', 'LCP 214/2025, art. 132, Anexo V, item 1.12'),
 ('V', 1, 13, 'Guincho para transportar cadeira de rodas', 'LCP 214/2025, art. 132, Anexo V, item 1.13'),
 ('V', 2, 0, 'PRODUTOS DESTINADOS A USO DE PESSOA COM DEFICIÊNCIA VISUAL', 'LCP 214/2025, art. 132, Anexo V, item 2'),
 ('V', 2, 1, 'Bengala inteiriça, dobrável ou telescópica, com ponteira de náilon', 'LCP 214/2025, art. 132, Anexo V, item 2.1'),
 ('V', 2, 2, 'Relógio em braille, com sintetizador de voz e mostrador ampliado', 'LCP 214/2025, art. 132, Anexo V, item 2.2'),
 ('V', 2, 3, 'Termômetro digital com sistema de voz', 'LCP 214/2025, art. 132, Anexo V, item 2.3'),
 ('V', 2, 4, 'Calculadora digital com sistema de voz, com verbalização dos ajustes de minutos e horas, tanto no modo horário, como no modo alarme, e comunicação por voz dos dígitos de cálculo e resultados', 'LCP 214/2025, art. 132, Anexo V, item 2.4'),
 ('V', 2, 5, 'Agenda eletrônica com teclado em braille, com ou sem sintetizador de voz', 'LCP 214/2025, art. 132, Anexo V, item 2.5'),
 ('V', 2, 6, 'Reglete para escrita em braille', 'LCP 214/2025, art. 132, Anexo V, item 2.6'),
 ('V', 2, 7, 'Display braille e teclado em Braille para uso em microcomputador, com sistema interativo para introdução e leitura de dados por meio de tabelas de caracteres Braille', 'LCP 214/2025, art. 132, Anexo V, item 2.7'),
 ('V', 2, 8, 'Máquina de escrever para escrita em braille, manual ou elétrica, com teclado de datilografia comum ou na formação Braille', 'LCP 214/2025, art. 132, Anexo V, item 2.8'),
 ('V', 2, 9, 'Impressora de caracteres em braille para uso com microcomputadores, com sistema de folha solta ou dois lados da folha, com ou sem sistema de comando de voz ou sistema acústico', 'LCP 214/2025, art. 132, Anexo V, item 2.9'),
 ('V', 2, 10, 'Equipamento sintetizador para reprodução em voz de sinais gerados por microcomputadores, permitida a leitura de dados de arquivos, de uso interno ou externo, com padrão de protocolo SSIL de interface com softwares leitores de tela', 'LCP 214/2025, art. 132, Anexo V, item 2.10'),
 ('V', 3, 0, 'PRODUTOS DESTINADOS AO USO DE PESSOAS COM DEFICIÊNCIA AUDITIVA', 'LCP 214/2025, art. 132, Anexo V, item 3'),
 ('V', 3, 1, 'Aparelho telefônico com teclado alfanumérico e visor luminoso, com ou sem impressora embutida, que permite converter sinais transmitidos por sistema telefônico em caracteres e símbolos', 'LCP 214/2025, art. 132, Anexo V, item 3.1'),
 ('V', 3, 2, 'Relógio despertador vibratório e/ou luminoso', 'LCP 214/2025, art. 132, Anexo V, item 3.2'),
 ('V', 3, 3, 'Unidades de entrada de dados tipo mouse controláveis pelo movimento dos olhos para deficientes', 'LCP 214/2025, art. 132, Anexo V, item 3.3'),

 -- ANEXO VI — nutrição enteral e parenteral. O dispositivo é o art. 133, § 1º,
 -- NÃO o art. 133: o caput trata dos medicamentos em geral e não menciona o
 -- Anexo VI. Zero por comprador: art. 146, § 2º.
 ('VI', 1, 0, 'Acetato de dextroalfatocoferol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 1'),
 ('VI', 2, 0, 'Acetato de lisina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 2'),
 ('VI', 3, 0, 'Acetato de potássio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 3'),
 ('VI', 4, 0, 'Acetato de sódio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 4'),
 ('VI', 5, 0, 'Acetato de zinco', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 5'),
 ('VI', 6, 0, 'Acetiltirosina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 6'),
 ('VI', 7, 0, 'Ácido acético', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 7'),
 ('VI', 8, 0, 'Ácido ascórbico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 8'),
 ('VI', 9, 0, 'Ácido aspártico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 9'),
 ('VI', 10, 0, 'Ácido cítrico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 10'),
 ('VI', 11, 0, 'Ácido fólico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 11'),
 ('VI', 12, 0, 'Ácido glutâmico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 12'),
 ('VI', 13, 0, 'Ácido málico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 13'),
 ('VI', 14, 0, 'Ácido selenioso', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 14'),
 ('VI', 15, 0, 'Água para injeção', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 15'),
 ('VI', 16, 0, 'Alanilglutamina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 16'),
 ('VI', 17, 0, 'Alanina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 17'),
 ('VI', 18, 0, 'Albumina humana', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 18'),
 ('VI', 19, 0, 'Arginina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 19'),
 ('VI', 20, 0, 'Asparagina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 20'),
 ('VI', 21, 0, 'Bicarbonato de sódio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 21'),
 ('VI', 22, 0, 'Biotina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 22'),
 ('VI', 23, 0, 'Cianocobalamina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 23'),
 ('VI', 24, 0, 'Cistina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 24'),
 ('VI', 25, 0, 'Cloreto crômico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 25'),
 ('VI', 26, 0, 'Cloreto de cálcio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 26'),
 ('VI', 27, 0, 'Cloreto de magnésio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 27'),
 ('VI', 28, 0, 'Cloreto de manganês', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 28'),
 ('VI', 29, 0, 'Cloreto de potássio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 29'),
 ('VI', 30, 0, 'Cloreto de sódio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 30'),
 ('VI', 31, 0, 'Cloreto de zinco', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 31'),
 ('VI', 32, 0, 'Cloridrato de piridoxina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 32'),
 ('VI', 33, 0, 'Cloridrato de tiamina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 33'),
 ('VI', 34, 0, 'Cocarboxilase', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 34'),
 ('VI', 35, 0, 'Colecalciferol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 35'),
 ('VI', 36, 0, 'Ergocalciferol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 36'),
 ('VI', 37, 0, 'Fenilalanina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 37'),
 ('VI', 38, 0, 'Fitomenadiona', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 38'),
 ('VI', 39, 0, 'Fórmula para dieta isenta de fenilalanina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 39'),
 -- "isenta demetionina" é a grafia LITERAL do DOU (aparente erro de digitação
 -- do próprio Diário). Corrigir a fonte é editorializar prova documental.
 ('VI', 40, 0, 'Fórmula para dieta isenta demetionina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 40'),
 ('VI', 41, 0, 'Fórmula para dieta isenta de lisina e pobre de triptofano', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 41'),
 ('VI', 42, 0, 'Fórmula para dieta isenta de leucina, de isoleucina ou de valina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 42'),
 ('VI', 43, 0, 'Fórmula para dieta isenta de fenilalanina e de metionina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 43'),
 ('VI', 44, 0, 'Fórmula para dieta isenta de aminoácidos não essenciais', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 44'),
 ('VI', 45, 0, 'Fórmula para dieta isenta de metionina, de treonina, de valina e restrita de isoleucina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 45'),
 ('VI', 46, 0, 'Fórmula para dieta cetogênica, na proporção de 4 g de gordura para cada 1 g de carboidratos e proteínas', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 46'),
 ('VI', 47, 0, 'Fórmula hiperlipídica, para suplementação de triglicerídios de cadeia média ou triheptanoína', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 47'),
 ('VI', 48, 0, 'Preparação líquida, de quatro partes de trioleato de glicerol de ácido para uma parte de trierucato de glicerol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 48'),
 ('VI', 49, 0, 'Fosfato de potássio dibásico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 49'),
 ('VI', 50, 0, 'Fosfato de potássio monobásico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 50'),
 ('VI', 51, 0, 'Fosfato de sódio monobásico', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 51'),
 ('VI', 52, 0, 'Fosfato de tiamina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 52'),
 ('VI', 53, 0, 'Fosfato sódico de riboflavina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 53'),
 ('VI', 54, 0, 'Frutose', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 54'),
 ('VI', 55, 0, 'Glicerofosfato de sódio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 55'),
 ('VI', 56, 0, 'Glicina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 56'),
 ('VI', 57, 0, 'Gliconato de cálcio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 57'),
 ('VI', 58, 0, 'Glicose', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 58'),
 ('VI', 59, 0, 'Histidina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 59'),
 ('VI', 60, 0, 'Icodextrina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 60'),
 ('VI', 61, 0, 'Iodeto de potássio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 61'),
 ('VI', 62, 0, 'Isoleucina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 62'),
 ('VI', 63, 0, 'Lecitina de ovo', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 63'),
 ('VI', 64, 0, 'Leucina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 64'),
 ('VI', 65, 0, 'Levovalina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 65'),
 ('VI', 66, 0, 'Lisina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 66'),
 ('VI', 67, 0, 'Metionina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 67'),
 ('VI', 68, 0, 'Nicotinamida', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 68'),
 ('VI', 69, 0, 'Palmitato de retinol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 69'),
 ('VI', 70, 0, 'Prolina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 70'),
 ('VI', 71, 0, 'Riboflavina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 71'),
 ('VI', 72, 0, 'Selenito de sódio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 72'),
 ('VI', 73, 0, 'Serina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 73'),
 ('VI', 74, 0, 'Sorbitol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 74'),
 ('VI', 75, 0, 'Sulfato de magnésio', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 75'),
 ('VI', 76, 0, 'Sulfato de zinco', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 76'),
 ('VI', 77, 0, 'Taurina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 77'),
 ('VI', 78, 0, 'Tirosina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 78'),
 ('VI', 79, 0, 'Tocoferol', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 79'),
 ('VI', 80, 0, 'Treonina', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 80'),
 ('VI', 81, 0, 'Triglicerídeos de cadeia média', 'LCP 214/2025, art. 133, § 1º, Anexo VI, item 81'),

 -- ANEXO VII — alimentos destinados ao consumo humano (art. 135). Tabela de 2
 -- colunas: os códigos vêm embutidos na prosa, como no Anexo XV. É o único dos
 -- seis com exceção operante, com alínea, e com remissão expressa a Anexo zero.
 ('VII', 1, 0, 'Crustáceos (exceto lagostas e lagostim) e moluscos dos seguintes códigos e subposições da NCM/SH: a) 0306.1 e 0306.3, exceto os produtos da subposição 0306.11 e dos códigos 0306.15.00, 0306.31.00, 0306.34.00, 0306.39.10; e b) 0307.31.00, 0307.32.00, 0307.42.00, 0307.43, 0307.51.00, 0307.52.00, 0307.91.00 e 0307.92.00', 'LCP 214/2025, art. 135, Anexo VII, item 1'),
 -- Item 2: alvo da alteração da LC 227/2026, INTEGRALMENTE VETADA. O texto
 -- abaixo é o ORIGINAL, que permanece vigente.
 ('VII', 2, 0, 'Leite fermentado, bebidas e compostos lácteos, em conformidade com os requisitos da legislação específica, classificados nos códigos 0403.20.00, 0403.90.00 e 2202.99.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 2'),
 ('VII', 3, 0, 'Mel natural do código 0409.00.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 3'),
 ('VII', 4, 0, 'Farinha das posições 1101.00, 11.02, 11.05, 11.06 e 12.08 da NCM/SH; ressalvados os produtos relacionados no Anexo I', 'LCP 214/2025, art. 135, Anexo VII, item 4'),
 ('VII', 5, 0, 'Grumos e sêmolas de cereais dos códigos 1103.11.00 e 1103.19.00 da NCM/SH; ressalvados os produtos relacionados no Anexo I', 'LCP 214/2025, art. 135, Anexo VII, item 5'),
 ('VII', 6, 0, 'Grãos de cereais das subposições 1104.1 e 1104.2 da NCM/SH; ressalvados os produtos relacionados no Anexo I', 'LCP 214/2025, art. 135, Anexo VII, item 6'),
 ('VII', 7, 0, 'Amido de milho do código 1108.12.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 7'),
 ('VII', 8, 0, 'Óleos de soja, de milho, canola e demais óleos vegetais, em conformidade com os requisitos da legislação específica relativos ao consumo como alimento, classificados na subposição 1507.90 e nas posições 15.08, 15.11, 15.12, 15.13, 15.14 e 15.15 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 8'),
 ('VII', 9, 0, 'Massas alimentícias dos códigos 1902.20.00 e 1902.30.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 9'),
 ('VII', 10, 0, 'Sucos naturais de fruta ou de produtos hortícolas sem adição de açúcar ou de outros edulcorantes e sem conservantes classificados na posição 20.09 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 10'),
 ('VII', 11, 0, 'Polpas de frutas ou de produtos hortícolas sem adição de açúcar ou de outros edulcorantes e sem conservantes classificadas na posição 20.08 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 11'),
 ('VII', 12, 0, 'Pão de Forma do código 1905.90.10 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 12'),
 ('VII', 13, 0, 'Extrato de tomate classificado no código 2002.90.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 13'),
 ('VII', 14, 0, 'Frutas, produtos hortícolas e demais produtos vegetais, sem adição de açúcar ou de outros edulcorantes, classificados nos capítulos 7 e 8 da NCM/SH, ressalvados as frutas de casca rija não regionais e os produtos relacionados nos Anexos I e XV e excetuadas as posições 07.11, 08.12 e 0814.00.00', 'LCP 214/2025, art. 135, Anexo VII, item 14'),
 ('VII', 15, 0, 'Cereais do capítulo 10 e sementes e frutos oleaginosos classificados no capítulo 12, ambos da NCM/SH, ressalvados os produtos relacionados no Anexo I', 'LCP 214/2025, art. 135, Anexo VII, item 15'),
 ('VII', 16, 0, 'Produtos hortícolas, mesmo misturados entre si, apenas pré-cozidos ou cozidos em água ou vapor, sem adição de sal ou de quaisquer outros produtos e substâncias, classificados nas posições 20.04 e 20.05 e no código 2002.10.00 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 16'),
 ('VII', 17, 0, 'Fruta de casca rija regional, amendoins e outras sementes, mesmo misturados entre si, apenas torrados ou cozidos, sem adição de sal ou de quaisquer outros produtos e substâncias, classificados na subposição 2008.1 da NCM/SH', 'LCP 214/2025, art. 135, Anexo VII, item 17'),

 -- ANEXO VIII — higiene pessoal e limpeza (art. 136). O menor e mais simples.
 -- O item 7 (9619.00.00) é o conflito declarado: o art. 147, que não tem
 -- Anexo e por isso está fora desta tabela, reduz a ZERO tampões, absorventes,
 -- calcinhas absorventes e coletores menstruais — MESMO código. Indecidível
 -- por NCM; aplica-se 60% (direção segura) e declara-se.
 ('VIII', 1, 0, 'Sabões de toucador classificados no código 3401.11.90 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 1'),
 ('VIII', 2, 0, 'Dentifrícios do código 3306.10.00 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 2'),
 ('VIII', 3, 0, 'Escovas de dentes do código 9603.21.00 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 3'),
 ('VIII', 4, 0, 'Papel higiênico do código 4818.10.00 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 4'),
 ('VIII', 5, 0, 'Água sanitária classificada no código 3808.94.19 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 5'),
 ('VIII', 6, 0, 'Sabões em barra classificados no código 3401.19.00 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 6'),
 ('VIII', 7, 0, 'Fraldas e artigos higiênicos semelhantes, de qualquer matéria classificadas no código 9619.00.00 da NCM/SH', 'LCP 214/2025, art. 136, Anexo VIII, item 7'),

 -- ANEXO IX — insumos agropecuários e aquícolas (art. 138). Cabeçalho oficial
 -- de coluna: "NBS / NCM/SH". Só os 22 itens de chave NCM entram (1-21 e 35);
 -- os 13 restantes estão no cabeçalho desta migração.
 ('IX', 1, 0, 'Biofertilizantes, em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 1'),
 ('IX', 2, 0, 'Fertilizantes (adubos), em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 2'),
 ('IX', 3, 0, 'Corretivos de solo (inclusive condicionadores), remineralizadores e substratos para plantas; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 3'),
 ('IX', 4, 0, 'Inoculantes, meios de cultura e outros microorganismos para uso agrícola; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 4'),
 ('IX', 5, 0, 'Bioestimulantes e bioinsumos para controle fitossanitário, em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 5'),
 ('IX', 6, 0, 'Inseticidas, fungicidas, formicidas, herbicidas, parasiticidas, germicidas, acaricidas, nematicidas, raticidas, desfolhantes, dessecantes, espalhantes adesivos, estimuladores e inibidores de crescimento (reguladores); todos destinados diretamente ao uso agropecuário ou destinados diretamente à fabricação de defensivo agropecuário; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 6'),
 ('IX', 7, 0, 'Calcário, casca de coco triturada, turfa; tortas, bagaços e demais resíduos e desperdícios vegetais das indústrias alimentares; cascas, serragens e demais resíduos e desperdícios de madeira; resíduos da indústria de celulose (dregs e grits), ossos, borra de carnaúba, cinzas, resíduos agroindustriais orgânicos, DL-Metionina e seus análogos, vermiculita e argilas expandidas, palhas e cascas de produtos vegetais, fibra de coco e outras fibras vegetais, silicatos de potássio ou de magnésio, resinas e oleorresinas naturais, sucos e extratos vegetais, aminoácidos e microrganismos mortos, óleos essenciais, argilas e terras, carvão vegetal e pastas mecânicas de madeira; todos destinados diretamente à fabricação de biofertilizantes, fertilizantes, corretivos de solo (inclusive condicionadores), remineralizadores, substratos para plantas, bioestimulantes ou biodefensivos para controle fitossanitário ou utilizados diretamente como biofertilizantes, fertilizantes, corretivos de solo (inclusive condicionadores), remineralizadores, substratos para plantas, bioestimulantes ou biodefensivos para controle fitossanitário; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 7'),
 ('IX', 8, 0, 'Ácido nítrico, ácido sulfúrico, ácido fosfórico, fosfatos de cálcio naturais, enxofre, ácido clorídrico, ácido fosforoso, ácido acético, hidróxido de sódio e carbonato dissódico; todos destinados diretamente à fabricação de fertilizantes', 'LCP 214/2025, art. 138, Anexo IX, item 8'),
 ('IX', 9, 0, 'Enzimas preparadas para decomposição de matéria orgânica animal e vegetal', 'LCP 214/2025, art. 138, Anexo IX, item 9'),
 ('IX', 10, 0, 'Semente genética, semente básica, semente nativa in natura, semente certificada de primeira geração (C1), semente certificada de segunda geração (C2), semente não certificada de primeira geração (S1), semente não certificada de segunda geração (S2) e sementes de cultivar local, tradicional ou crioula; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 10'),
 ('IX', 11, 0, 'Mudas de plantas e demais materiais propagativos de plantas e fungos, inclusive plantas e fungos nativos de espécies florestais; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 11'),
 ('IX', 12, 0, 'Vacinas, soros e medicamentos, de uso veterinário, exceto de animais domésticos', 'LCP 214/2025, art. 138, Anexo IX, item 12'),
 ('IX', 13, 0, 'Aves de um dia, exceto as ornamentais', 'LCP 214/2025, art. 138, Anexo IX, item 13'),
 ('IX', 14, 0, 'Embriões e sêmen, congelado ou resfriado', 'LCP 214/2025, art. 138, Anexo IX, item 14'),
 ('IX', 15, 0, 'Reprodutores de raça pura, inclusive matrizes de animais puros de origem com registro genealógico; em conformidade com as definições e demais requisitos da legislação específica', 'LCP 214/2025, art. 138, Anexo IX, item 15'),
 ('IX', 16, 0, 'Ovos fertilizados', 'LCP 214/2025, art. 138, Anexo IX, item 16'),
 ('IX', 17, 0, 'Girinos e alevinos', 'LCP 214/2025, art. 138, Anexo IX, item 17'),
 ('IX', 18, 0, 'Rações para animais, concentrados, suplementos, aditivos, premix ou núcleo, exceto para animais domésticos', 'LCP 214/2025, art. 138, Anexo IX, item 18'),
 ('IX', 19, 0, 'Sementes e cereais, mesmo triturados, em grãos esmagados ou trabalhados de outro modo; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos', 'LCP 214/2025, art. 138, Anexo IX, item 19'),
 ('IX', 20, 0, 'Farelos e tortas de produtos vegetais e demais resíduos e desperdícios das indústrias alimentares; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos', 'LCP 214/2025, art. 138, Anexo IX, item 20'),
 ('IX', 21, 0, 'Alho em pó, sal mineralizado, farinhas de peixe, de ostra, de carne, de osso, de pena, de sangue e de víscera, calcário calcítico, gorduras e óleos animais, resíduos de óleo e de gordura de origem animal ou vegetal descartados por empresas do ramo alimentício, e DL-Metionina e seus análogos; todos destinados diretamente à fabricação de ração para animais ou diretamente à alimentação animal, exceto de animais domésticos', 'LCP 214/2025, art. 138, Anexo IX, item 21'),
 ('IX', 35, 0, 'Vinhaça', 'LCP 214/2025, art. 138, Anexo IX, item 35')
ON CONFLICT DO NOTHING;

-- 389 linhas: 381 inclusões (excecao = FALSE) + 8 exceções (excecao = TRUE),
-- estas últimas todas no Anexo VII.
-- `texto_ncm` é a grafia literal do DOU; `prefixo` é derivado dela e conferido
-- pela CHECK prefixo_bate_com_texto — nenhum dígito é digitado duas vezes sem
-- que o banco compare os dois.
INSERT INTO anexos_reducao_ncm (anexo, item, sub_item, prefixo, excecao, alinea, texto_ncm) VALUES
 -- Anexo IV. 13 das 112 linhas NÃO são de 8 dígitos: escrever '39174000' onde
 -- a lei diz '3917.40' criaria um código que não existe e nunca casaria.
 ('IV', 1, 0, '39269030', FALSE, NULL, '3926.90.30'),
 ('IV', 2, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 3, 0, '37011010', FALSE, NULL, '3701.10.10'),
 ('IV', 4, 0, '30064020', FALSE, NULL, '3006.40.20'),
 ('IV', 5, 0, '30049099', FALSE, NULL, '3004.90.99'),
 ('IV', 6, 0, '39269040', FALSE, NULL, '3926.90.40'),
 ('IV', 7, 0, '391740',   FALSE, NULL, '3917.40'),
 ('IV', 8, 0, '391740',   FALSE, NULL, '3917.40'),
 ('IV', 9, 0, '30049099', FALSE, NULL, '3004.90.99'),
 ('IV', 10, 0, '90189010', FALSE, NULL, '9018.90.10'),
 ('IV', 11, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 12, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 12, 0, '90219080', FALSE, NULL, '9021.90.80'),
 ('IV', 13, 0, '90219091', FALSE, NULL, '9021.90.91'),
 ('IV', 14, 0, '90219091', FALSE, NULL, '9021.90.91'),
 ('IV', 15, 0, '90219091', FALSE, NULL, '9021.90.91'),
 ('IV', 16, 0, '90219091', FALSE, NULL, '9021.90.91'),
 ('IV', 17, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 18, 0, '37021020', FALSE, NULL, '3702.10.20'),
 ('IV', 19, 0, '37021010', FALSE, NULL, '3702.10.10'),
 ('IV', 20, 0, '84212990', FALSE, NULL, '8421.29.90'),
 ('IV', 21, 0, '84212990', FALSE, NULL, '8421.29.90'),
 ('IV', 22, 0, '84212990', FALSE, NULL, '8421.29.90'),
 ('IV', 23, 0, '300610',   FALSE, NULL, '3006.10'),
 ('IV', 24, 0, '90189040', FALSE, NULL, '9018.90.40'),
 ('IV', 25, 0, '84212911', FALSE, NULL, '8421.29.11'),
 ('IV', 26, 0, '90215000', FALSE, NULL, '9021.50.00'),
 ('IV', 27, 0, '90215000', FALSE, NULL, '9021.50.00'),
 ('IV', 28, 0, '37011029', FALSE, NULL, '3701.10.29'),
 ('IV', 29, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 30, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 31, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 32, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 33, 0, '90189040', FALSE, NULL, '9018.90.40'),
 ('IV', 34, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 35, 0, '30059090', FALSE, NULL, '3005.90.90'),
 ('IV', 36, 0, '30061090', FALSE, NULL, '3006.10.90'),
 ('IV', 37, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 37, 0, '90219089', FALSE, NULL, '9021.90.89'),
 ('IV', 38, 0, '90219019', FALSE, NULL, '9021.90.19'),
 ('IV', 39, 0, '28444390', FALSE, NULL, '2844.43.90'),
 ('IV', 40, 0, '90219012', FALSE, NULL, '9021.90.12'),
 ('IV', 41, 0, '84798999', FALSE, NULL, '8479.89.99'),
 ('IV', 42, 0, '90212900', FALSE, NULL, '9021.29.00'),
 ('IV', 42, 0, '90211010', FALSE, NULL, '9021.10.10'),
 ('IV', 42, 0, '90211020', FALSE, NULL, '9021.10.20'),
 ('IV', 43, 0, '90219011', FALSE, NULL, '9021.90.11'),
 ('IV', 44, 0, '90219012', FALSE, NULL, '9021.90.12'),
 ('IV', 45, 0, '30021221', FALSE, NULL, '3002.12.21'),
 ('IV', 46, 0, '30021222', FALSE, NULL, '3002.12.22'),
 ('IV', 47, 0, '30021223', FALSE, NULL, '3002.12.23'),
 ('IV', 48, 0, '30021221', FALSE, NULL, '3002.12.21'),
 ('IV', 48, 0, '30021229', FALSE, NULL, '3002.12.29'),
 ('IV', 49, 0, '38221',    FALSE, NULL, '3822.1'),
 ('IV', 50, 0, '30063021', FALSE, NULL, '3006.30.21'),
 ('IV', 51, 0, '30064012', FALSE, NULL, '3006.40.12'),
 ('IV', 52, 0, '30067000', FALSE, NULL, '3006.70.00'),
 ('IV', 53, 0, '30069110', FALSE, NULL, '3006.91.10'),
 ('IV', 54, 0, '30069190', FALSE, NULL, '3006.91.90'),
 ('IV', 55, 0, '39269030', FALSE, NULL, '3926.90.30'),
 ('IV', 56, 0, '39269040', FALSE, NULL, '3926.90.40'),
 ('IV', 57, 0, '39269050', FALSE, NULL, '3926.90.50'),
 ('IV', 58, 0, '40151',    FALSE, NULL, '4015.1'),
 ('IV', 59, 0, '901831',   FALSE, NULL, '9018.31'),
 ('IV', 60, 0, '901832',   FALSE, NULL, '9018.32'),
 ('IV', 61, 0, '90183910', FALSE, NULL, '9018.39.10'),
 ('IV', 62, 0, '9018392',  FALSE, NULL, '9018.39.2'),
 ('IV', 63, 0, '90183930', FALSE, NULL, '9018.39.30'),
 ('IV', 64, 0, '9018399',  FALSE, NULL, '9018.39.9'),
 ('IV', 65, 0, '9018491',  FALSE, NULL, '9018.49.1'),
 ('IV', 66, 0, '90184920', FALSE, NULL, '9018.49.20'),
 ('IV', 67, 0, '90189095', FALSE, NULL, '9018.90.95'),
 ('IV', 68, 0, '90183999', FALSE, NULL, '9018.39.99'),
 ('IV', 68, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 69, 0, '940290',   FALSE, NULL, '9402.90'),
 -- Item 70: um dos 4 casos em que o 60% VENCE a redução a zero — o Anexo XII,
 -- item 2 cita `9018.20` (subposição de 6) e este cita o código de 8.
 ('IV', 70, 0, '90182010', FALSE, NULL, '9018.20.10'),
 ('IV', 71, 0, '90189021', FALSE, NULL, '9018.90.21'),
 ('IV', 72, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 73, 0, '84198110', FALSE, NULL, '8419.81.10'),
 ('IV', 74, 0, '90185090', FALSE, NULL, '9018.50.90'),
 ('IV', 75, 0, '38210000', FALSE, NULL, '3821.00.00'),
 ('IV', 76, 0, '84198999', FALSE, NULL, '8419.89.99'),
 ('IV', 77, 0, '84199040', FALSE, NULL, '8419.90.40'),
 ('IV', 78, 0, '84798912', FALSE, NULL, '8479.89.12'),
 ('IV', 79, 0, '90272012', FALSE, NULL, '9027.20.12'),
 ('IV', 80, 0, '90272021', FALSE, NULL, '9027.20.21'),
 ('IV', 81, 0, '90272029', FALSE, NULL, '9027.20.29'),
 ('IV', 82, 0, '902730',   FALSE, NULL, '9027.30'),
 ('IV', 83, 0, '90275020', FALSE, NULL, '9027.50.20'),
 ('IV', 84, 0, '90275050', FALSE, NULL, '9027.50.50'),
 ('IV', 85, 0, '90275090', FALSE, NULL, '9027.50.90'),
 ('IV', 86, 0, '90278999', FALSE, NULL, '9027.89.99'),
 ('IV', 87, 0, '90278100', FALSE, NULL, '9027.81.00'),
 ('IV', 88, 0, '90278999', FALSE, NULL, '9027.89.99'),
 ('IV', 89, 0, '90279010', FALSE, NULL, '9027.90.10'),
 ('IV', 90, 0, '9027909',  FALSE, NULL, '9027.90.9'),
 ('IV', 91, 0, '40141000', FALSE, NULL, '4014.10.00'),
 ('IV', 92, 0, '90189099', FALSE, NULL, '9018.90.99'),
 ('IV', 93, 0, '38249989', FALSE, NULL, '3824.99.89'),
 ('IV', 94, 0, '90219091', FALSE, NULL, '9021.90.91'),
 ('IV', 95, 0, '90219099', FALSE, NULL, '9021.90.99'),
 ('IV', 96, 0, '90219099', FALSE, NULL, '9021.90.99'),
 ('IV', 97, 0, '90219099', FALSE, NULL, '9021.90.99'),
 ('IV', 98, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 99, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 100, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 101, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 102, 0, '90183999', FALSE, NULL, '9018.39.99'),
 ('IV', 102, 0, '90183991', FALSE, NULL, '9018.39.91'),
 ('IV', 103, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 104, 0, '90183929', FALSE, NULL, '9018.39.29'),
 ('IV', 105, 0, '90189099', FALSE, NULL, '9018.90.99'),

 -- Anexo V. Os itens 1, 2 e 3 são cabeçalhos e NÃO têm linha aqui.
 ('V', 1, 1, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 2, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 3, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 4, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 5, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 6, '87082999', FALSE, NULL, '8708.29.99'),
 ('V', 1, 7, '87089910', FALSE, NULL, '8708.99.10'),
 ('V', 1, 8, '87082999', FALSE, NULL, '8708.29.99'),
 ('V', 1, 9, '87082999', FALSE, NULL, '8708.29.99'),
 ('V', 1, 10, '87082999', FALSE, NULL, '8708.29.99'),
 ('V', 1, 11, '84289090', FALSE, NULL, '8428.90.90'),
 ('V', 1, 12, '87082999', FALSE, NULL, '8708.29.99'),
 ('V', 1, 13, '84253110', FALSE, NULL, '8425.31.10'),
 ('V', 2, 1, '66020000', FALSE, NULL, '6602.00.00'),
 ('V', 2, 2, '91021110', FALSE, NULL, '9102.11.10'),
 ('V', 2, 2, '91021190', FALSE, NULL, '9102.11.90'),
 ('V', 2, 2, '91029100', FALSE, NULL, '9102.91.00'),
 -- Item 2.3: um dos 4 casos em que o 60% vence o zero (XII/12 cita `90.25`).
 ('V', 2, 3, '90251990', FALSE, NULL, '9025.19.90'),
 ('V', 2, 4, '84701000', FALSE, NULL, '8470.10.00'),
 ('V', 2, 4, '84702900', FALSE, NULL, '8470.29.00'),
 ('V', 2, 5, '85437099', FALSE, NULL, '8543.70.99'),
 ('V', 2, 6, '90172000', FALSE, NULL, '9017.20.00'),
 ('V', 2, 7, '84716090', FALSE, NULL, '8471.60.90'),
 ('V', 2, 8, '84729099', FALSE, NULL, '8472.90.99'),
 ('V', 2, 9, '84433222', FALSE, NULL, '8443.32.22'),
 ('V', 2, 10, '84718000', FALSE, NULL, '8471.80.00'),
 ('V', 3, 1, '85171',    FALSE, NULL, '8517.1'),
 ('V', 3, 2, '91031000', FALSE, NULL, '9103.10.00'),
 ('V', 3, 2, '91051100', FALSE, NULL, '9105.11.00'),
 ('V', 3, 3, '84716053', FALSE, NULL, '8471.60.53'),

 -- Anexo VI. Todos de 8 dígitos, nenhuma exceção.
 ('VI', 1, 0, '29362812', FALSE, NULL, '2936.28.12'),
 ('VI', 2, 0, '29224190', FALSE, NULL, '2922.41.90'),
 ('VI', 3, 0, '29152990', FALSE, NULL, '2915.29.90'),
 ('VI', 4, 0, '29152910', FALSE, NULL, '2915.29.10'),
 ('VI', 5, 0, '29152990', FALSE, NULL, '2915.29.90'),
 ('VI', 6, 0, '29225039', FALSE, NULL, '2922.50.39'),
 ('VI', 7, 0, '29152100', FALSE, NULL, '2915.21.00'),
 ('VI', 8, 0, '29362710', FALSE, NULL, '2936.27.10'),
 ('VI', 9, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 10, 0, '29181400', FALSE, NULL, '2918.14.00'),
 ('VI', 11, 0, '29362911', FALSE, NULL, '2936.29.11'),
 ('VI', 12, 0, '29224210', FALSE, NULL, '2922.42.10'),
 ('VI', 13, 0, '29181990', FALSE, NULL, '2918.19.90'),
 ('VI', 14, 0, '28111990', FALSE, NULL, '2811.19.90'),
 ('VI', 15, 0, '20021000', FALSE, NULL, '2002.10.00'),
 ('VI', 16, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 17, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 18, 0, '30021236', FALSE, NULL, '3002.12.36'),
 ('VI', 19, 0, '29252919', FALSE, NULL, '2925.29.19'),
 ('VI', 20, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 21, 0, '28363000', FALSE, NULL, '2836.30.00'),
 ('VI', 22, 0, '29362931', FALSE, NULL, '2936.29.31'),
 ('VI', 23, 0, '29362610', FALSE, NULL, '2936.26.10'),
 ('VI', 24, 0, '29309039', FALSE, NULL, '2930.90.39'),
 ('VI', 25, 0, '28273993', FALSE, NULL, '2827.39.93'),
 ('VI', 26, 0, '28272010', FALSE, NULL, '2827.20.10'),
 ('VI', 26, 0, '28272090', FALSE, NULL, '2827.20.90'),
 ('VI', 27, 0, '28273110', FALSE, NULL, '2827.31.10'),
 ('VI', 27, 0, '28273190', FALSE, NULL, '2827.31.90'),
 ('VI', 28, 0, '28273995', FALSE, NULL, '2827.39.95'),
 ('VI', 29, 0, '31042010', FALSE, NULL, '3104.20.10'),
 ('VI', 29, 0, '31042090', FALSE, NULL, '3104.20.90'),
 ('VI', 30, 0, '25010090', FALSE, NULL, '2501.00.90'),
 ('VI', 31, 0, '28273998', FALSE, NULL, '2827.39.98'),
 ('VI', 32, 0, '29362520', FALSE, NULL, '2936.25.20'),
 ('VI', 33, 0, '29362210', FALSE, NULL, '2936.22.10'),
 ('VI', 34, 0, '29362290', FALSE, NULL, '2936.22.90'),
 ('VI', 35, 0, '29362921', FALSE, NULL, '2936.29.21'),
 ('VI', 36, 0, '29362929', FALSE, NULL, '2936.29.29'),
 ('VI', 37, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 38, 0, '29362940', FALSE, NULL, '2936.29.40'),
 ('VI', 39, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 40, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 41, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 42, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 43, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 44, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 45, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 46, 0, '21069090', FALSE, NULL, '2106.90.90'),
 ('VI', 47, 0, '22029900', FALSE, NULL, '2202.99.00'),
 ('VI', 48, 0, '22029900', FALSE, NULL, '2202.99.00'),
 ('VI', 49, 0, '28352400', FALSE, NULL, '2835.24.00'),
 ('VI', 50, 0, '28352400', FALSE, NULL, '2835.24.00'),
 ('VI', 51, 0, '28352200', FALSE, NULL, '2835.22.00'),
 ('VI', 52, 0, '29362290', FALSE, NULL, '2936.22.90'),
 ('VI', 53, 0, '29362320', FALSE, NULL, '2936.23.20'),
 ('VI', 54, 0, '17025000', FALSE, NULL, '1702.50.00'),
 ('VI', 55, 0, '29199090', FALSE, NULL, '2919.90.90'),
 ('VI', 56, 0, '29224910', FALSE, NULL, '2922.49.10'),
 ('VI', 57, 0, '29181610', FALSE, NULL, '2918.16.10'),
 ('VI', 58, 0, '17023011', FALSE, NULL, '1702.30.11'),
 ('VI', 59, 0, '29332992', FALSE, NULL, '2933.29.92'),
 ('VI', 60, 0, '35051000', FALSE, NULL, '3505.10.00'),
 ('VI', 61, 0, '28276012', FALSE, NULL, '2827.60.12'),
 ('VI', 62, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 63, 0, '29232000', FALSE, NULL, '2923.20.00'),
 ('VI', 64, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 65, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 66, 0, '29224110', FALSE, NULL, '2922.41.10'),
 ('VI', 67, 0, '29304010', FALSE, NULL, '2930.40.10'),
 ('VI', 67, 0, '29304090', FALSE, NULL, '2930.40.90'),
 ('VI', 68, 0, '29362952', FALSE, NULL, '2936.29.52'),
 ('VI', 69, 0, '29362113', FALSE, NULL, '2936.21.13'),
 ('VI', 70, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 71, 0, '29362310', FALSE, NULL, '2936.23.10'),
 ('VI', 72, 0, '28429000', FALSE, NULL, '2842.90.00'),
 ('VI', 73, 0, '29225099', FALSE, NULL, '2922.50.99'),
 ('VI', 74, 0, '29054400', FALSE, NULL, '2905.44.00'),
 ('VI', 75, 0, '28332100', FALSE, NULL, '2833.21.00'),
 ('VI', 76, 0, '28332970', FALSE, NULL, '2833.29.70'),
 ('VI', 77, 0, '29224990', FALSE, NULL, '2922.49.90'),
 ('VI', 78, 0, '29225039', FALSE, NULL, '2922.50.39'),
 ('VI', 79, 0, '29362811', FALSE, NULL, '2936.28.11'),
 ('VI', 80, 0, '29225099', FALSE, NULL, '2922.50.99'),
 ('VI', 81, 0, '15131900', FALSE, NULL, '1513.19.00'),
 ('VI', 81, 0, '15132911', FALSE, NULL, '1513.29.11'),

 -- Anexo VII. As 8 exceções do Anexo inteiro estão aqui, todas OPERANTES:
 -- as 5 do item 1 descem de `03061`/`03063`; as 3 do item 14 descem de `07`/`08`.
 -- As remissões ("ressalvados os produtos relacionados no Anexo I", itens 4, 5,
 -- 6, 14 e 15) NÃO viram linha: são honradas pelo desempate por especificidade,
 -- e a asserção (6) no fim desta migração prova que continuam sendo.
 ('VII', 1, 0, '03061',    FALSE, 'a', '0306.1'),
 ('VII', 1, 0, '03063',    FALSE, 'a', '0306.3'),
 ('VII', 1, 0, '030611',   TRUE,  'a', '0306.11'),
 ('VII', 1, 0, '03061500', TRUE,  'a', '0306.15.00'),
 ('VII', 1, 0, '03063100', TRUE,  'a', '0306.31.00'),
 ('VII', 1, 0, '03063400', TRUE,  'a', '0306.34.00'),
 ('VII', 1, 0, '03063910', TRUE,  'a', '0306.39.10'),
 ('VII', 1, 0, '03073100', FALSE, 'b', '0307.31.00'),
 ('VII', 1, 0, '03073200', FALSE, 'b', '0307.32.00'),
 ('VII', 1, 0, '03074200', FALSE, 'b', '0307.42.00'),
 ('VII', 1, 0, '030743',   FALSE, 'b', '0307.43'),
 ('VII', 1, 0, '03075100', FALSE, 'b', '0307.51.00'),
 ('VII', 1, 0, '03075200', FALSE, 'b', '0307.52.00'),
 ('VII', 1, 0, '03079100', FALSE, 'b', '0307.91.00'),
 ('VII', 1, 0, '03079200', FALSE, 'b', '0307.92.00'),
 ('VII', 2, 0, '04032000', FALSE, NULL, '0403.20.00'),
 ('VII', 2, 0, '04039000', FALSE, NULL, '0403.90.00'),
 ('VII', 2, 0, '22029900', FALSE, NULL, '2202.99.00'),
 ('VII', 3, 0, '04090000', FALSE, NULL, '0409.00.00'),
 ('VII', 4, 0, '110100',   FALSE, NULL, '1101.00'),
 ('VII', 4, 0, '1102',     FALSE, NULL, '11.02'),
 ('VII', 4, 0, '1105',     FALSE, NULL, '11.05'),
 ('VII', 4, 0, '1106',     FALSE, NULL, '11.06'),
 ('VII', 4, 0, '1208',     FALSE, NULL, '12.08'),
 ('VII', 5, 0, '11031100', FALSE, NULL, '1103.11.00'),
 ('VII', 5, 0, '11031900', FALSE, NULL, '1103.19.00'),
 ('VII', 6, 0, '11041',    FALSE, NULL, '1104.1'),
 ('VII', 6, 0, '11042',    FALSE, NULL, '1104.2'),
 ('VII', 7, 0, '11081200', FALSE, NULL, '1108.12.00'),
 ('VII', 8, 0, '150790',   FALSE, NULL, '1507.90'),
 ('VII', 8, 0, '1508',     FALSE, NULL, '15.08'),
 ('VII', 8, 0, '1511',     FALSE, NULL, '15.11'),
 ('VII', 8, 0, '1512',     FALSE, NULL, '15.12'),
 ('VII', 8, 0, '1513',     FALSE, NULL, '15.13'),
 ('VII', 8, 0, '1514',     FALSE, NULL, '15.14'),
 ('VII', 8, 0, '1515',     FALSE, NULL, '15.15'),
 ('VII', 9, 0, '19022000', FALSE, NULL, '1902.20.00'),
 ('VII', 9, 0, '19023000', FALSE, NULL, '1902.30.00'),
 ('VII', 10, 0, '2009',    FALSE, NULL, '20.09'),
 ('VII', 11, 0, '2008',    FALSE, NULL, '20.08'),
 ('VII', 12, 0, '19059010', FALSE, NULL, '1905.90.10'),
 ('VII', 13, 0, '20029000', FALSE, NULL, '2002.90.00'),
 -- Itens 14 e 15: 4 dos 14 prefixos de CAPÍTULO do projeto. `texto_ncm` guarda
 -- a grafia do CÓDIGO ('07'), não a prosa do DOU ('capítulos 7 e 8'), senão
 -- prefixo_bate_com_texto derivaria '78'.
 ('VII', 14, 0, '07',      FALSE, NULL, '07'),
 ('VII', 14, 0, '08',      FALSE, NULL, '08'),
 ('VII', 14, 0, '0711',    TRUE,  NULL, '07.11'),
 ('VII', 14, 0, '0812',    TRUE,  NULL, '08.12'),
 ('VII', 14, 0, '08140000', TRUE, NULL, '0814.00.00'),
 ('VII', 15, 0, '10',      FALSE, NULL, '10'),
 ('VII', 15, 0, '12',      FALSE, NULL, '12'),
 ('VII', 16, 0, '2004',    FALSE, NULL, '20.04'),
 ('VII', 16, 0, '2005',    FALSE, NULL, '20.05'),
 ('VII', 16, 0, '20021000', FALSE, NULL, '2002.10.00'),
 ('VII', 17, 0, '20081',   FALSE, NULL, '2008.1'),

 -- Anexo VIII. Sete linhas, todas de 8 dígitos, nenhuma exceção.
 ('VIII', 1, 0, '34011190', FALSE, NULL, '3401.11.90'),
 ('VIII', 2, 0, '33061000', FALSE, NULL, '3306.10.00'),
 ('VIII', 3, 0, '96032100', FALSE, NULL, '9603.21.00'),
 ('VIII', 4, 0, '48181000', FALSE, NULL, '4818.10.00'),
 ('VIII', 5, 0, '38089419', FALSE, NULL, '3808.94.19'),
 ('VIII', 6, 0, '34011900', FALSE, NULL, '3401.19.00'),
 ('VIII', 7, 0, '96190000', FALSE, NULL, '9619.00.00'),

 -- Anexo IX. 9 prefixos de capítulo em 5 itens; o item 7 sozinho cita 29
 -- códigos e o item 8 cita 18 — densidade sem precedente no projeto.
 ('IX', 1, 0, '31010000', FALSE, NULL, '3101.00.00'),
 ('IX', 2, 0, '31',       FALSE, NULL, '31'),
 ('IX', 2, 0, '38249977', FALSE, NULL, '3824.99.77'),
 ('IX', 2, 0, '38249979', FALSE, NULL, '3824.99.79'),
 ('IX', 2, 0, '38249989', FALSE, NULL, '3824.99.89'),
 -- Capítulo 25: a linha mais AMPLA e mais perigosa desta feature. A NCM usa o
 -- capítulo 25 para sal, enxofre, cimento, mármore e gesso; o item fala de
 -- corretivos de solo "em conformidade com a legislação específica". A resposta
 -- devolve tipo_correspondencia = 'CAPITULO' para que o cliente possa filtrar.
 ('IX', 3, 0, '25',       FALSE, NULL, '25'),
 ('IX', 4, 0, '300249',   FALSE, NULL, '3002.49'),
 ('IX', 4, 0, '30029000', FALSE, NULL, '3002.90.00'),
 ('IX', 4, 0, '38210000', FALSE, NULL, '3821.00.00'),
 ('IX', 5, 0, '3824',     FALSE, NULL, '38.24'),
 ('IX', 5, 0, '38070000', FALSE, NULL, '3807.00.00'),
 ('IX', 5, 0, '1211',     FALSE, NULL, '12.11'),
 ('IX', 5, 0, '3808',     FALSE, NULL, '38.08'),
 ('IX', 6, 0, '3808',     FALSE, NULL, '38.08'),
 ('IX', 6, 0, '38249989', FALSE, NULL, '3824.99.89'),
 ('IX', 7, 0, '0506',     FALSE, NULL, '05.06'),
 ('IX', 7, 0, '12011000', FALSE, NULL, '1201.10.00'),
 ('IX', 7, 0, '12130000', FALSE, NULL, '1213.00.00'),
 ('IX', 7, 0, '13019090', FALSE, NULL, '1301.90.90'),
 ('IX', 7, 0, '1302199',  FALSE, NULL, '1302.19.9'),
 ('IX', 7, 0, '14019000', FALSE, NULL, '1401.90.00'),
 ('IX', 7, 0, '14049090', FALSE, NULL, '1404.90.90'),
 ('IX', 7, 0, '21022000', FALSE, NULL, '2102.20.00'),
 ('IX', 7, 0, '2302',     FALSE, NULL, '23.02'),
 ('IX', 7, 0, '2303',     FALSE, NULL, '23.03'),
 ('IX', 7, 0, '230400',   FALSE, NULL, '2304.00'),
 ('IX', 7, 0, '23050000', FALSE, NULL, '2305.00.00'),
 ('IX', 7, 0, '2306',     FALSE, NULL, '23.06'),
 ('IX', 7, 0, '23080000', FALSE, NULL, '2308.00.00'),
 ('IX', 7, 0, '27030000', FALSE, NULL, '2703.00.00'),
 ('IX', 7, 0, '28399010', FALSE, NULL, '2839.90.10'),
 ('IX', 7, 0, '28399050', FALSE, NULL, '2839.90.50'),
 ('IX', 7, 0, '29224',    FALSE, NULL, '2922.4'),
 ('IX', 7, 0, '293040',   FALSE, NULL, '2930.40'),
 ('IX', 7, 0, '3301',     FALSE, NULL, '33.01'),
 ('IX', 7, 0, '38029040', FALSE, NULL, '3802.90.40'),
 ('IX', 7, 0, '380400',   FALSE, NULL, '3804.00'),
 ('IX', 7, 0, '38249971', FALSE, NULL, '3824.99.71'),
 ('IX', 7, 0, '44013900', FALSE, NULL, '4401.39.00'),
 ('IX', 7, 0, '44014',    FALSE, NULL, '4401.4'),
 ('IX', 7, 0, '44029000', FALSE, NULL, '4402.90.00'),
 ('IX', 7, 0, '47010000', FALSE, NULL, '4701.00.00'),
 ('IX', 7, 0, '53050090', FALSE, NULL, '5305.00.90'),
 ('IX', 7, 0, '68062000', FALSE, NULL, '6806.20.00'),
 ('IX', 8, 0, '25030010', FALSE, NULL, '2503.00.10'),
 ('IX', 8, 0, '25030090', FALSE, NULL, '2503.00.90'),
 ('IX', 8, 0, '25101010', FALSE, NULL, '2510.10.10'),
 ('IX', 8, 0, '25101090', FALSE, NULL, '2510.10.90'),
 ('IX', 8, 0, '25102010', FALSE, NULL, '2510.20.10'),
 ('IX', 8, 0, '25102090', FALSE, NULL, '2510.20.90'),
 ('IX', 8, 0, '28020000', FALSE, NULL, '2802.00.00'),
 ('IX', 8, 0, '28061020', FALSE, NULL, '2806.10.20'),
 ('IX', 8, 0, '28070010', FALSE, NULL, '2807.00.10'),
 ('IX', 8, 0, '28080010', FALSE, NULL, '2808.00.10'),
 ('IX', 8, 0, '28092011', FALSE, NULL, '2809.20.11'),
 ('IX', 8, 0, '28092019', FALSE, NULL, '2809.20.19'),
 ('IX', 8, 0, '28111920', FALSE, NULL, '2811.19.20'),
 ('IX', 8, 0, '28151100', FALSE, NULL, '2815.11.00'),
 ('IX', 8, 0, '28151200', FALSE, NULL, '2815.12.00'),
 ('IX', 8, 0, '28362010', FALSE, NULL, '2836.20.10'),
 ('IX', 8, 0, '28362090', FALSE, NULL, '2836.20.90'),
 ('IX', 8, 0, '29152100', FALSE, NULL, '2915.21.00'),
 ('IX', 9, 0, '3507904',  FALSE, NULL, '3507.90.4'),
 ('IX', 10, 0, '07',      FALSE, NULL, '07'),
 ('IX', 10, 0, '10',      FALSE, NULL, '10'),
 ('IX', 10, 0, '12',      FALSE, NULL, '12'),
 -- Item 11: dois dos 4 casos em que o 60% vence o zero — o Anexo XV, item 4
 -- cita o Capítulo 6 inteiro (`06`) e este cita as posições 06.01 e 06.02.
 ('IX', 11, 0, '0601',    FALSE, NULL, '06.01'),
 ('IX', 11, 0, '0602',    FALSE, NULL, '06.02'),
 ('IX', 12, 0, '300212',  FALSE, NULL, '3002.12'),
 ('IX', 12, 0, '300215',  FALSE, NULL, '3002.15'),
 ('IX', 12, 0, '300242',  FALSE, NULL, '3002.42'),
 ('IX', 12, 0, '30029000', FALSE, NULL, '3002.90.00'),
 ('IX', 12, 0, '3004',    FALSE, NULL, '30.04'),
 ('IX', 13, 0, '01051',   FALSE, NULL, '0105.1'),
 ('IX', 14, 0, '05111000', FALSE, NULL, '0511.10.00'),
 ('IX', 14, 0, '05119',   FALSE, NULL, '0511.9'),
 ('IX', 15, 0, '0102',    FALSE, NULL, '01.02'),
 ('IX', 15, 0, '0103',    FALSE, NULL, '01.03'),
 ('IX', 15, 0, '0104',    FALSE, NULL, '01.04'),
 ('IX', 16, 0, '04071',   FALSE, NULL, '0407.1'),
 ('IX', 17, 0, '01069000', FALSE, NULL, '0106.90.00'),
 ('IX', 18, 0, '230990',  FALSE, NULL, '2309.90'),
 ('IX', 19, 0, '10',      FALSE, NULL, '10'),
 ('IX', 19, 0, '11',      FALSE, NULL, '11'),
 ('IX', 19, 0, '12',      FALSE, NULL, '12'),
 ('IX', 20, 0, '2301',    FALSE, NULL, '23.01'),
 ('IX', 20, 0, '2302',    FALSE, NULL, '23.02'),
 ('IX', 20, 0, '2303',    FALSE, NULL, '23.03'),
 ('IX', 20, 0, '230400',  FALSE, NULL, '2304.00'),
 ('IX', 20, 0, '23050000', FALSE, NULL, '2305.00.00'),
 ('IX', 20, 0, '2306',    FALSE, NULL, '23.06'),
 ('IX', 20, 0, '23080000', FALSE, NULL, '2308.00.00'),
 ('IX', 21, 0, '0210',    FALSE, NULL, '02.10'),
 ('IX', 21, 0, '0309',    FALSE, NULL, '03.09'),
 ('IX', 21, 0, '07129010', FALSE, NULL, '0712.90.10'),
 ('IX', 21, 0, '15',      FALSE, NULL, '15'),
 ('IX', 21, 0, '250100',  FALSE, NULL, '2501.00'),
 ('IX', 21, 0, '25210000', FALSE, NULL, '2521.00.00'),
 ('IX', 21, 0, '293040',  FALSE, NULL, '2930.40'),
 ('IX', 35, 0, '23033000', FALSE, NULL, '2303.30.00'),
 ('IX', 35, 0, '23032000', FALSE, NULL, '2303.20.00')
ON CONFLICT DO NOTHING;

DO $$
DECLARE r RECORD; n int;
BEGIN
    -- (1) Contagem por Anexo nos DEZ. Uma migração truncada passa em toda
    --     CHECK e falha aqui. Por Anexo, e não global, para que a falha diga
    --     ONDE.
    FOR r IN SELECT * FROM (VALUES
            ('I',26,95), ('IV',105,112), ('V',29,30), ('VI',81,86),
            ('VII',17,53), ('VIII',7,7), ('IX',22,101),
            ('XII',20,24), ('XIII',8,7), ('XV',6,25))
                          AS e(anexo, itens, prefixos) LOOP
        IF (SELECT count(*) FROM anexos_reducao     WHERE anexo = r.anexo) <> r.itens
        OR (SELECT count(*) FROM anexos_reducao_ncm WHERE anexo = r.anexo) <> r.prefixos THEN
            RAISE EXCEPTION 'Anexo %: contagem não bate com a transcrição do DESIGN', r.anexo;
        END IF;
    END LOOP;

    -- (2) Inclusões/exceções no total.
    SELECT count(*) INTO n FROM anexos_reducao_ncm WHERE excecao IS TRUE;
    IF n <> 32 THEN RAISE EXCEPTION 'exceções: % (esperado 32 = 24 já carregadas + 8 do Anexo VII)', n; END IF;

    SELECT count(*) INTO n FROM anexos_reducao_ncm WHERE excecao IS FALSE;
    IF n <> 508 THEN RAISE EXCEPTION 'inclusões: % (esperado 508 = 127 já carregadas + 381 novas)', n; END IF;

    -- (3) Exceção órfã: ou erro de transcrição, ou "exceto" DESCRITIVO virado
    --     linha. Nos dois casos a linha seria inerte — ruído indistinguível de
    --     erro, que só apareceria no dia em que colidisse com outro item.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_ncm e
        WHERE e.excecao IS TRUE AND NOT EXISTS (
            SELECT 1 FROM anexos_reducao_ncm i
            WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
              AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%')
    ) THEN RAISE EXCEPTION 'exceção que não desce de nenhuma inclusão do próprio item'; END IF;

    -- (4) Item sem prefixo só é legítimo se for CABEÇALHO (tem sub-itens); e
    --     todo sub-item precisa do seu cabeçalho. São 5: XII/1, XIII/2 e os
    --     três do Anexo V.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao i
        WHERE NOT EXISTS (SELECT 1 FROM anexos_reducao_ncm p
                          WHERE p.anexo = i.anexo AND p.item = i.item AND p.sub_item = i.sub_item)
          AND NOT EXISTS (SELECT 1 FROM anexos_reducao f
                          WHERE f.anexo = i.anexo AND f.item = i.item AND f.sub_item > 0)
    ) THEN RAISE EXCEPTION 'item sem linha de prefixo e sem sub-item: INSERT truncado'; END IF;

    IF EXISTS (
        SELECT 1 FROM anexos_reducao f
        WHERE f.sub_item > 0 AND NOT EXISTS (SELECT 1 FROM anexos_reducao c
                                             WHERE c.anexo = f.anexo AND c.item = f.item AND c.sub_item = 0)
    ) THEN RAISE EXCEPTION 'sub-item sem linha de cabeçalho'; END IF;

    -- (5) Comprimentos presentes ⊆ {2,4,5,6,7,8}. Redundante com a CHECK de
    --     propósito: prova que ela está de fato ativa. É também o que garante
    --     que nenhum código NBS (9 dígitos sem pontuação) entrou aqui.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao_ncm WHERE length(prefixo) NOT IN (2,4,5,6,7,8)
    ) THEN RAISE EXCEPTION 'prefixo com comprimento que a NCM/SH não tem'; END IF;

    -- (6) A ÚNICA asserção que protege uma regra JURÍDICA, e não uma contagem.
    --     Os itens 4, 5, 6, 14 e 15 do Anexo VII dizem, no próprio texto,
    --     "ressalvados os produtos relacionados no Anexo I" (e, no 14, também
    --     no XV). O desempate por especificidade honra essa ressalva SEM regra
    --     própria — mas só enquanto todo prefixo de Anexo zero que se sobrepõe
    --     for ESTRITAMENTE mais longo. Se um dado novo quebrar isso, a Decisão
    --     3 do DESIGN deixa de ser válida sem quebrar mais nada de visível.
    IF EXISTS (
        SELECT 1
        FROM anexos_reducao_ncm sete
        JOIN anexos_reducao_ncm zero_ ON zero_.prefixo LIKE sete.prefixo || '%'
        JOIN anexos_reducao izero
          ON izero.anexo = zero_.anexo AND izero.item = zero_.item
         AND izero.sub_item = zero_.sub_item
        JOIN anexos_reducao_catalogo czero ON czero.anexo = izero.anexo
        WHERE sete.anexo = 'VII' AND sete.item IN (4,5,6,14,15) AND sete.excecao IS FALSE
          AND zero_.excecao IS FALSE AND czero.percentual_reducao = 1
          AND length(zero_.prefixo) <= length(sete.prefixo)
    ) THEN
        RAISE EXCEPTION 'Anexo VII: a ressalva expressa aos Anexos I/XV deixou de ser honrada pelo desempate por especificidade — ver Decisão 3 do DESIGN';
    END IF;

    -- (7) Todo item aponta para um Anexo do catálogo, com o percentual
    --     esperado. Redundante com a FK e a CHECK `catalogo_conhecido` DE
    --     PROPÓSITO: prova que as duas estão ativas nesta instância.
    IF EXISTS (
        SELECT 1 FROM anexos_reducao i
        LEFT JOIN anexos_reducao_catalogo c ON c.anexo = i.anexo
        WHERE c.anexo IS NULL
           OR (i.anexo IN ('IV','V','VI','VII','VIII','IX') AND c.percentual_reducao <> 0.6)
           OR (i.anexo IN ('I','XII','XIII','XV')           AND c.percentual_reducao <> 1.0)
    ) THEN RAISE EXCEPTION 'item apontando para Anexo ausente do catálogo ou com percentual errado'; END IF;

    -- (8) Só os Anexos IV, V e VI têm condição de comprador — e os TRÊS têm.
    SELECT count(*) INTO n FROM anexos_reducao_catalogo WHERE zero_por_comprador_ref IS NOT NULL;
    IF n <> 3 THEN
        RAISE EXCEPTION 'Anexos com condição de comprador: % (esperado 3 — IV, V e VI, arts. 144 II, 145 II e 146 § 2º)', n;
    END IF;
END $$;
