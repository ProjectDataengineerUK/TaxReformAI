-- Base de incidência do Imposto Seletivo (IS) — LCP 214/2025, art. 409,
-- §§1º-2º, Anexo XVII. NUNCA uma alíquota: motor_calculo/tabela_aliquotas.py
-- permanece intocado, `aliq_is` continua exatamente como antes desta
-- migração (Decisão 1 do DESIGN_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md).
--
-- Fonte primária (consultada em 2026-07-31): legis.senado.leg.br/norma/
-- 40180341/publicacao/40181073 (Anexo XVII), conferida contra o "Texto
-- Atualizado" da Câmara dos Deputados (mesmo PDF já usado nas 2 features
-- anteriores desta sessão) — as 6 categorias com código conferem dígito a
-- dígito nas duas fontes. Confirmado que a LC 227/2026 não alterou nem o
-- art. 409 nem o Anexo XVII (alterou os arts. 408/414/422-434, mecânica de
-- base de cálculo/alíquotas — não a base de incidência em si).
--
-- Achado crítico do /define — art. 409, §2º: produtos fumígenos (inciso III)
-- e bebidas alcoólicas (inciso IV) só entram na base do IS "quando
-- acondicionados em embalagem primária... destinada ao consumidor final".
-- Não constava no brainstorm original. Modelado como condição de GATING
-- (Decisão 3 do DESIGN) — mesmo nome de situação `CONDICAO_NAO_SATISFEITA`
-- já usado em api/reducao_nbs.py para o Anexo X, para consistência de
-- linguagem entre features do mesmo tipo de problema.
--
-- Achado adicional — exceção por FINALIDADE DE USO (veículos/aeronaves para
-- uso operacional das Forças Armadas/Segurança Pública, incisos I e II):
-- nenhum campo de ItemSimulacao captura isso (decisão YAGNI herdada do
-- brainstorm) — a coluna excecao_uso_ref garante que a resposta SEMPRE
-- declara essa limitação quando relevante, nunca a esconde (Decisão 4).
--
-- Inciso VII ("concursos de prognósticos e fantasy sport") NUNCA é inserido:
-- célula vazia no Anexo XVII, sem código NCM nem NBS — mesma disciplina de
-- todo item "sem código" já documentado nas features anteriores.

CREATE TABLE imposto_seletivo_incidencia (
    inciso                           SMALLINT PRIMARY KEY CHECK (inciso BETWEEN 1 AND 7),
    categoria                        TEXT NOT NULL,
    dispositivo_legal_ref            TEXT NOT NULL,
    -- Não-nulo só nos incisos III (fumígenos) e IV (bebidas alcoólicas).
    condicao_embalagem_primaria_ref  TEXT,
    -- Não-nulo só nos incisos I (veículos) e II (aeronaves/embarcações).
    excecao_uso_ref                  TEXT
);

CREATE TABLE imposto_seletivo_incidencia_ncm (
    inciso    SMALLINT   NOT NULL REFERENCES imposto_seletivo_incidencia (inciso),
    -- Mesmos comprimentos de api/ncm.py::_COMPRIMENTOS_PREFIXO, restritos aos
    -- 3 níveis observados nesta feature (posição, subposição, item completo)
    -- — os dois mudam JUNTOS se um novo nível aparecer.
    prefixo   VARCHAR(8)  NOT NULL CHECK (prefixo ~ '^[0-9]+$' AND length(prefixo) IN (4, 6, 8)),
    -- TRUE só para 8802.60.00 — exclusão por CÓDIGO específico (diferente da
    -- exceção por finalidade de uso, que não tem código próprio). Reaproveita
    -- o mesmo booleano já validado nos 10 Anexos NCM de redução (Decisão 5).
    excecao   BOOLEAN    NOT NULL DEFAULT FALSE,
    texto_ncm TEXT       NOT NULL,
    UNIQUE (inciso, prefixo)
);

CREATE INDEX idx_imposto_seletivo_incidencia_ncm_prefixo
    ON imposto_seletivo_incidencia_ncm (prefixo);

INSERT INTO imposto_seletivo_incidencia
       (inciso, categoria, dispositivo_legal_ref, condicao_embalagem_primaria_ref, excecao_uso_ref) VALUES
 (1, 'Veículos', 'LCP 214/2025, art. 409, §1º, I, Anexo XVII', NULL,
  'LCP 214/2025, Anexo XVII — ressalvados veículos com características técnicas específicas para uso operacional das Forças Armadas ou dos órgãos de Segurança Pública'),
 (2, 'Embarcações e aeronaves', 'LCP 214/2025, art. 409, §1º, II, Anexo XVII', NULL,
  'LCP 214/2025, Anexo XVII — ressalvadas aeronaves e embarcações com características técnicas específicas para uso operacional das Forças Armadas ou dos órgãos de Segurança Pública'),
 (3, 'Produtos fumígenos', 'LCP 214/2025, art. 409, §1º, III, Anexo XVII',
  'LCP 214/2025, art. 409, §2º — sujeito ao IS somente quando acondicionado em embalagem primária destinada ao consumidor final', NULL),
 (4, 'Bebidas alcoólicas', 'LCP 214/2025, art. 409, §1º, IV, Anexo XVII',
  'LCP 214/2025, art. 409, §2º — sujeito ao IS somente quando acondicionada em embalagem primária destinada ao consumidor final', NULL),
 (5, 'Bebidas açucaradas', 'LCP 214/2025, art. 409, §1º, V, Anexo XVII', NULL, NULL),
 (6, 'Bens minerais', 'LCP 214/2025, art. 409, §1º, VI, Anexo XVII', NULL, NULL)
ON CONFLICT DO NOTHING;

-- Veículos (inciso 1) — "87.03" + subposições de 8704 "(exceto os
-- caminhões)". A ressalva "exceto os caminhões" é TEXTUAL (não há um código
-- NCM próprio de "caminhão" a excluir nestas subposições) — preservada
-- literalmente em texto_ncm para auditoria, não modelada como uma segunda
-- linha de exceção (não há código a apontar).
INSERT INTO imposto_seletivo_incidencia_ncm (inciso, prefixo, excecao, texto_ncm) VALUES
 (1, '8703',     FALSE, '87.03'),
 (1, '870421',   FALSE, '8704.21 (exceto os caminhões)'),
 (1, '870431',   FALSE, '8704.31 (exceto os caminhões)'),
 (1, '87044100', FALSE, '8704.41.00 (exceto os caminhões)'),
 (1, '87045100', FALSE, '8704.51.00 (exceto os caminhões)'),
 (1, '87046000', FALSE, '8704.60.00 (exceto os caminhões)'),
 (1, '87049000', FALSE, '8704.90.00 (exceto os caminhões)'),
 -- Embarcações e aeronaves (inciso 2) — 8802 inteiro, exceto 8802.60.00
 -- (exclusão por CÓDIGO, ver Decisão 5); embarcações com motor em 8903.
 (2, '8802',     FALSE, '8802'),
 (2, '88026000', TRUE,  '8802.60.00 (excluído expressamente)'),
 (2, '8903',     FALSE, '8903 (embarcações com motor)'),
 -- Produtos fumígenos (inciso 3).
 (3, '2401',     FALSE, '24.01'),
 (3, '2402',     FALSE, '24.02'),
 (3, '2403',     FALSE, '24.03'),
 (3, '2404',     FALSE, '24.04'),
 -- Bebidas alcoólicas (inciso 4).
 (4, '2203',     FALSE, '22.03'),
 (4, '2204',     FALSE, '22.04'),
 (4, '2205',     FALSE, '22.05'),
 (4, '2206',     FALSE, '22.06'),
 (4, '2208',     FALSE, '22.08'),
 -- Bebidas açucaradas (inciso 5) — um código só, 8 dígitos.
 (5, '22021000', FALSE, '2202.10.00'),
 -- Bens minerais (inciso 6).
 (6, '2601',     FALSE, '26.01'),
 (6, '27090010', FALSE, '2709.00.10'),
 (6, '27111100', FALSE, '2711.11.00'),
 (6, '27112100', FALSE, '2711.21.00')
ON CONFLICT DO NOTHING;

-- Prova de não-sobreposição (Decisão 2 do DESIGN): as 6 categorias cobrem
-- faixas de NCM disjuntas — sem isso, a ausência de desempate cross-
-- categoria em api/imposto_seletivo.py seria uma afirmação, não um fato
-- provado pela própria migração.
DO $$
DECLARE conflitos int; itens int; prefixos int;
BEGIN
    SELECT count(*) INTO conflitos
    FROM imposto_seletivo_incidencia_ncm a
    JOIN imposto_seletivo_incidencia_ncm b
      ON a.inciso <> b.inciso
     AND (b.prefixo LIKE a.prefixo || '%' OR a.prefixo LIKE b.prefixo || '%');
    IF conflitos > 0 THEN
        RAISE EXCEPTION 'Categorias do Anexo XVII se sobrepõem (% pares/linhas) — a Decisão 2 '
            'do DESIGN presumia faixas disjuntas, provar antes de generalizar o desempate',
            conflitos;
    END IF;

    SELECT count(*) INTO itens    FROM imposto_seletivo_incidencia;
    SELECT count(*) INTO prefixos FROM imposto_seletivo_incidencia_ncm;
    IF itens <> 6 THEN
        RAISE EXCEPTION 'esperadas 6 categorias com código (I-VI); encontradas %', itens;
    END IF;
    IF prefixos <> 24 THEN
        RAISE EXCEPTION 'esperados 24 prefixos (7+3+4+5+1+4); encontrados %', prefixos;
    END IF;
END $$;

-- Mesmo padrão de sempre: GRANT ... ON ALL TABLES não é retroativo; tabelas
-- novas precisam do seu. Degradação conservadora: um GRANT faltando NÃO gera
-- erro — gera CONSULTA_INDISPONIVEL silencioso e o item simplesmente não é
-- classificado (nunca afeta CBS/IBS/IPI).
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON imposto_seletivo_incidencia     TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON imposto_seletivo_incidencia_ncm TO taxreformai_app';
    END IF;
END $$;
