# ROADMAP: Sequência Pós-Auditoria (Julho/2026)

> Registro de planejamento — não é um documento SDD por si só (não passa por /define,
> /design, /build, /ship). Serve de mapa para as sessões de brainstorm/define/design/
> build/ship que virão a seguir, uma feature de cada vez, na ordem definida aqui.
> Atualize a coluna **Status** conforme cada feature for shipada.
>
> **2026-07-28: adicionadas as posições 12-17** (segunda leva, ver seção dedicada abaixo) —
> os 16 Anexos restantes da LCP 214/2025 (I já shipado em `REGRAS_TRIBUTARIAS_CACHE`) mais o
> Simples Nacional. Nota de numeração: as posições ficam registradas como 12-17 (a tabela
> ativa já vai até a Ordem 11 e não é renumerada), mas isso é só rótulo — ver a **ordem de
> execução** abaixo, que é o que manda de fato.
>
> **2026-07-28 (correção, mesmo dia): ordem de EXECUÇÃO invertida.** A decisão original era
> a segunda leva (12-17) rodar *depois* das posições 3-11. O usuário reverteu isso na mesma
> sessão: as posições **12-17 rodam primeiro**, e só depois as posições 3-11 (`API_EMPRESA_SKUS`
> em diante) são retomadas. Os números de posição (Ordem) NÃO mudam — servem só de
> identificador, não de fila —, mas a ordem real de trabalho é: 1, 2 (já shipadas) → **12, 13,
> 14, 15, 16, 17** → 3, 4, 5, 6, 7, 8, 9, 10, 11.

## Origem

Duas rodadas de auditoria profunda (SHIPPED_*.md + CLAUDE.md vs. código/CI reais; depois
`contexto.md` — blueprint original de 9 seções — vs. o que existe) levantaram 13 achados.
O achado 13 foi descartado por baixa prioridade/fora de escopo. Dos 12 restantes, o
usuário (Jonatas) decidiu em 2026-07-27:

1. **Não escolher um único achado/candidato** — atacar os 12 (menos o 13) um de cada vez,
   em sequência, não em paralelo nem agrupados livremente.
2. **Achado 12** (linha do tempo da reforma 2029-2033) fica de fora da sequência ATIVA.
   Está estruturalmente bloqueado: a lei que fixaria CBS/IS nesse período ainda não existe
   no mundo real. Vira item de **monitoramento**, não uma feature no pipeline, até (e se)
   a norma for promulgada.
3. **Ordem**: respeitar dependência técnica onde existir; usar a numeração original do
   levantamento (1-11) como desempate nos casos sem dependência entre si. Isso move o
   achado 5 (LLM real) para antes do achado 4 (nós reais da orquestração), que por sua vez
   resolve o achado 6 (vazamento `"[FAKE]"`) como efeito colateral — sem essas trocas, a
   ordem segue a numeração original do levantamento.

## Sequência ativa (11 features)

| Ordem | Achado original | Feature | Descrição resumida | Status |
|-------|------------------|---------|---------------------|--------|
| 1 | 1 | `IPI_TIPI_MOTOR_CALCULO` | Conectar `aliquotas_ipi_tipi` (9231 NCM já ingeridos) ao `motor_calculo`/`api/routers/simulate.py` — IPI deixa de ser "indisponível" quando o dado já existe | ✅ Shipado 2026-07-28 (`.claude/sdd/archive/IPI_TIPI_MOTOR_CALCULO/`) |
| 2 | 2 | `REGRAS_TRIBUTARIAS_CACHE` | Decidir destino de `regras_tributarias_cache`/`buscar_regra_cache()` — plugar num consumidor real ou remover como código morto | ✅ Shipado 2026-07-28 (`.claude/sdd/archive/REGRAS_TRIBUTARIAS_CACHE/`) — removida; substituída pela Cesta Básica Nacional (Anexo I) |
| 3 | 3 | `API_EMPRESA_SKUS` | Endpoints para tenant cadastrar/listar/upload de SKUs (`empresa_skus` — schema e RLS já existem, zero rota) | ⚪ Não iniciado |
| 4 | 5 | `LLM_REAL_VERTEX_AI` | Conectar Claude via Vertex AI de verdade (`anthropic`/`google-cloud-aiplatform` ausentes hoje) — pré-requisito técnico do item 5 | ⚪ Não iniciado |
| 5 | 4 | `ORQUESTRACAO_NOS_REAIS` | Tornar `classificador`/`pesquisador_legal`/`extrator_regras`/`sintetizador` reais (hoje fake), incluindo busca real no Qdrant — depende do item 4 (LLM conectado) | ⚪ Não iniciado |
| 6 | 6 | `REMOVER_FAKE_HISTORICO` | Eliminar o vazamento de `"[FAKE]"` em `/v1/tax/query` — resolvido como efeito colateral do item 5, mas registrado como feature própria para garantir verificação explícita | ⚪ Não iniciado |
| 7 | 7 | `CLOUD_COMPOSER_PROVISIONAMENTO` | Provisionar Cloud Composer real e executar `dags/ingestao_legal_dag.py` de verdade (hoje só revisão de código) | ⚪ Não iniciado |
| 8 | 8 | `VERIFICACAO_FRONTEND_NAVEGADOR` | Verificação manual do frontend num navegador real (pendência aberta desde o SHIPPED do `FRONTEND_SIMULADOR`) | ⚪ Não iniciado |
| 9 | 9 | `DIAGNOSTICO_BUSCA_HIBRIDA` | Root-cause do miss 4/5 no Bloco A de `ingestao.yml` (near-duplicado/boilerplate dentro da Resolução CGIBS nº 6/2026) | ⚪ Não iniciado |
| 10 | 10 | `BIGQUERY_DATA_WAREHOUSE` | Provisionar BigQuery para consultas analíticas em histórico de simulações (seção 5 do blueprint) | ⚪ Não iniciado |
| 11 | 11 | `FILA_ASSINCRONA_CELERY_REDIS` | Fila assíncrona (Celery/Redis) para sustentar 50.000+ SKUs dos planos Business/Enterprise | ⚪ Não iniciado |

## Segunda leva: os 16 Anexos restantes da LCP 214/2025 + Simples Nacional (posições 12-17)

### Origem

`REGRAS_TRIBUTARIAS_CACHE` (posição 2, shipada em 2026-07-28) cobriu só o Anexo I (Cesta
Básica Nacional, art. 125). Os outros 16 Anexos (II-XVII, já excluído o XIV — revogado pela
LC 227/2026, ver `.claude/sdd/archive/LC_227_2026_ATUALIZACAO_LEGAL/`) ficaram fora de escopo
por decisão explícita daquela sessão. O usuário confirmou que cobrir os 16 restantes não é
opcional, e pediu uma sessão de `/brainstorm` dedicada só a decidir como agrupá-los em
features (mesma disciplina que já levou a quebrar a auditoria original em 11 features
sequenciais, não uma feature monolítica).

Essa sessão (2026-07-28) verificou os 21 Anexos restantes (II-XIII, XV-XXIII) contra fonte
primária real (`legis.senado.leg.br/norma/40180341/publicacao/{id}`, DOU Edição Extra de
16/01/2025, nº 11-B — mesma fonte já usada no `/design` do Anexo I) e encontrou uma correção
relevante ao brainstorm original: os Anexos **XVIII-XXIII não são "produção de efeitos
futura" dos Anexos I-V/VII de redução**, como uma fonte secundária levou a crer. São os
**Anexos I, II, III, IV, V e VII do Simples Nacional (LC 123/2006)**, reproduzidos dentro da
LCP 214/2025 com tabelas de partilha (IRPJ/CSLL/CBS/CPP/ICMS/IBS) por faixa de receita, ano a
ano de 2027 a pelo menos 2033 — um regime tributário à parte, que `motor_calculo/
regime_atual.py` não modela hoje de nenhuma forma, sem nenhuma dependência técnica dos
Anexos de redução.

**Aviso herdado para o `/define` de cada uma das 6 features abaixo**: a investigação da LC
227/2026 (`.claude/sdd/archive/LC_227_2026_ATUALIZACAO_LEGAL/`) catalogou alterações só nos
artigos já citados no código (343, 344, 346, 347, 348) — **nunca verificou se a LC 227/2026
também alterou algum dos Anexos II-XXIII**. Cada `/define` desta leva deve confirmar isso
contra fonte primária antes de aceitar qualquer conteúdo de Anexo como definitivo.

### Decisão de agrupamento (usuário, 2026-07-28)

Abordagem híbrida: agrupar por mecanismo de cálculo (zero vs. percentual) **e** por tipo de
chave de correspondência (NCM/bens vs. NBS/serviços), isolando à parte o que não é nem
produto nem serviço (XVI) e o que é um tributo diferente (XVII) ou um regime diferente
(Simples Nacional, XVIII-XXIII). Anexos que misturam as duas chaves no mesmo Anexo (IX, X,
XI) vão para o grupo da chave **dominante**; os itens da chave minoritária ficam
documentados como não resolvidos naquela feature — mesmo padrão já usado para os itens 19/20
do Anexo I.

### Classificação por Anexo (verificada contra fonte primária nesta sessão)

| Anexo | Assunto | Redução/Natureza | Chave | Vai para |
|-------|---------|-------------------|-------|----------|
| XII | Dispositivos médicos | zero | NCM puro | Posição 12 |
| XIII | Acessibilidade (pessoas com deficiência) | zero | NCM puro | Posição 12 |
| XV | Hortícolas, frutas e ovos | 100% (= zero) | NCM puro | Posição 12 |
| IV | Dispositivos médicos | 60% | NCM puro | Posição 13 |
| V | Acessibilidade | 60% | NCM puro | Posição 13 |
| VI | Nutrição enteral/parenteral | 60% | NCM puro | Posição 13 |
| VII | Alimentos | 60% | NCM puro | Posição 13 |
| VIII | Higiene pessoal/limpeza | 60% | NCM puro | Posição 13 |
| IX | Insumos agropecuários/aquícolas | 60% | **misto** (NCM dominante) | Posição 13 (itens NBS ficam pendentes) |
| II | Educação | 60% | NBS puro | Posição 14 |
| III | Saúde | 60% | NBS puro | Posição 14 |
| X | Produções artísticas/culturais/audiovisuais | 60% | **misto** (NBS dominante) | Posição 14 (itens NCM ficam pendentes) |
| XI | Segurança/cibersegurança | 60% | **misto** (NBS dominante) | Posição 14 (itens NCM ficam pendentes) |
| XVI | Piso da alíquota própria dos entes federativos | tabela por ano (2029-2033+), valor nacional único, não por ente | nenhuma (não é produto/serviço) | Posição 15 |
| XVII | Base de incidência do Imposto Seletivo | bens (NCM) + 1 categoria de serviço sem código | mista, tributo diferente (IS, não CBS/IBS) | Posição 16 |
| XVIII-XXIII | Anexos I, II, III, IV, V, VII do Simples Nacional (LC 123/2006), com partilha CBS/IBS 2027-2033+ | regime tributário à parte | nenhuma (regime, não produto/serviço) | Posição 17 |
| XIV | — | **Revogado pela LC 227/2026** | — | Fora de escopo (já resolvido, ver `LC_227_2026_ATUALIZACAO_LEGAL/`) |

### Sequência (posições 12-17)

| Ordem | Feature | Anexos | Descrição resumida | Status |
|-------|---------|--------|----------------------|--------|
| 12 | `ANEXOS_REDUCAO_ZERO_XII_XIII_XV` | XII, XIII, XV | Redução a zero/100% de CBS/IBS por NCM — reaproveita o mecanismo já validado do Anexo I (`aplicar_reducao_a_zero`, `api/ncm.py`, prefixo de dígitos), sem função de cálculo nova | ✅ Shipado 2026-07-29 (`.claude/sdd/archive/ANEXOS_REDUCAO_ZERO_XII_XIII_XV/`) |
| 13 | `ANEXOS_REDUCAO_PERCENTUAL_NCM` | IV, V, VI, VII, VIII, IX | Redução de 60% de CBS/IBS por NCM — exige função nova (`aplicar_reducao_percentual` ou equivalente, já que hoje só existe a versão "zera tudo"); itens de chave NBS do Anexo IX documentados como não resolvidos nesta feature. **Achado do `/design` de `ANEXOS_REDUCAO_ZERO_XII_XIII_XV` (2026-07-28): os Anexos IV e V não são "60% universal"** — os arts. 144-II e 145-II da LCP 214/2025 reduzem a **zero** os Anexos IV e V quando o adquirente é órgão público ou entidade CEBAS, condição sobre o *comprador* que o payload atual de `/v1/tax/simulate` não expressa. O `/define` desta feature deve tratar essa condição explicitamente para IV/V, em vez de aplicar 60% de forma incondicional a esses dois Anexos | ✅ Shipado 2026-07-30 (`.claude/sdd/archive/ANEXOS_REDUCAO_PERCENTUAL_NCM/`) |
| 14 | `ANEXOS_REDUCAO_PERCENTUAL_NBS` | II, III, X, XI | Redução de 60% de CBS/IBS por NBS — infraestrutura de lookup por `nbs_code` inteiramente nova (schema, chave, tabela); itens de chave NCM dos Anexos X/XI documentados como não resolvidos nesta feature | ✅ Shipado 2026-07-31, **completo** (`.claude/sdd/archive/ANEXOS_REDUCAO_PERCENTUAL_NBS/`) — os 4 Anexos (II, III, X, XI); o Anexo X ficou vazio no ship original (art. 139 ilegível pela ferramenta de leitura web) e foi fechado no MESMO DIA via migração 012, depois de obter o texto integral do art. 139 por uma rota alternativa (PDF da Câmara dos Deputados) |
| 15 | `ANEXO_XVI_PISO_ALIQUOTA_PROPRIA` | XVI | Piso nacional (por ano, 2029-2077) da alíquota própria de Estados/Municípios em proporção à alíquota de referência — estrutura isolada, não é produto/serviço | ✅ Shipado 2026-07-31 (`.claude/sdd/archive/ANEXO_XVI_PISO_ALIQUOTA_PROPRIA/`) — primeira feature da leva sem NENHUMA infraestrutura (Python puro); achado real do `/build`: `/v1/tax/simulate` já 422 para todo ano ≥ 2027, exigiu endpoint dedicado (`GET /v1/tax/piso-aliquota-ibs/{ano}`) além do campo embutido |
| 16 | `ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA` | XVII | Base de incidência do Imposto Seletivo (bens NCM + 1 categoria de serviço) — só define O QUE é tributado; a alíquota continua pendente de lei ordinária, já modelada como `None` em `motor_calculo/tabela_aliquotas.py` | ✅ Shipado 2026-07-31 (`.claude/sdd/archive/ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA/`) — 6 categorias com código (veículos, aeronaves/embarcações, fumígenos, bebidas alcoólicas, bebidas açucaradas, bens minerais); condição de embalagem primária (art. 409, §2º) e exceção de uso militar/segurança pública documentadas; categoria VII (concursos de prognósticos) sem código, nunca inserida |
| 17 | `SIMPLES_NACIONAL_CBS_IBS_TRANSICAO` | XVIII-XXIII | Integração de CBS/IBS à partilha do Simples Nacional (Anexos I/II/III/IV/V/VII da LC 123/2006, tabelas ano a ano 2027-2033+) — regime tributário inteiro, inexistente hoje em `motor_calculo/regime_atual.py`; sem dependência técnica das 5 features anteriores desta leva | ✅ Shipado 2026-08-01 (`.claude/sdd/archive/SIMPLES_NACIONAL_CBS_IBS_TRANSICAO/`) — endpoint dedicado `POST /v1/tax/simulate-simples-nacional` (achado: `/v1/tax/simulate` já 422 para todo `ano_operacao` >= 2027, mesma classe do Anexo XVI), módulo Python puro (`motor_calculo/simples_nacional.py`) com os 6 Anexos completos e a fórmula do art. 18 da LC 123/2006 (achado ausente do brainstorm — a fórmula não está na LCP 214/2025). Última feature da "segunda leva" — as 6 estão 100% completas |

Documentos de brainstorm de cada uma, com o detalhamento completo (aprovadas nesta sessão,
prontas para `/define`):

- `.claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`
- `.claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NCM.md`
- `.claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NBS.md`
- `.claude/sdd/features/BRAINSTORM_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md`
- `.claude/sdd/features/BRAINSTORM_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md`
- `.claude/sdd/features/BRAINSTORM_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`

## Item de monitoramento (fora da sequência ativa)

| Achado original | Item | Condição de reativação |
|------------------|------|-------------------------|
| 12 | Linha do tempo da reforma 2029-2033 (`motor_calculo/tabela_aliquotas.py`) | Só volta a ser uma feature executável quando a lei ordinária que fixa CBS/IS nesse período (ou a alíquota de referência do art. 347) for promulgada. Até lá, nenhuma alíquota deve ser estimada — mesma disciplina já aplicada a 2027-2028 |

## Achado 13 (não incluído na sequência)

Cosméticos, já marcados como baixa prioridade no levantamento original: Shadcn UI não é
dependência formal do frontend; modelo de negócio/pricing/billing (seção 9) sem
implementação (esperado nesta fase). Revisitar só se o usuário pedir explicitamente.
