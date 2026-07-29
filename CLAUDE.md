# TaxReform AI

> Plataforma SaaS B2B Enterprise de Inteligência Tributária e Compliance em Tempo Real, para apoiar departamentos fiscais, controllers, CFOs e consultorias tributárias durante a transição do modelo tributário brasileiro (PIS, COFINS, IPI, ICMS, ISS) para o novo IVA Dual (CBS, IBS e Imposto Seletivo). Combina RAG Híbrido com AST de legislação, regras determinísticas de cálculo e guardrails contábeis em sandbox Python, garantindo simulações 100% auditáveis com citação de fontes oficiais.

---

## Status do projeto

`contexto.md` continua sendo o blueprint completo (produto, arquitetura multi-agente, infraestrutura GCP, modelagem de dados, API e modelo de negócio) que orienta a implementação. Dez features já foram construídas seguindo o workflow SDD (`/brainstorm` → `/define` → `/design` → `/build` → `/ship`), documentadas em `.claude/sdd/`:

| Feature | Status | O que faz |
|---------|--------|-----------|
| `PIPELINE_INGESTAO_LEGAL` (`ingestion/`) | ✅ Shipado (`.claude/sdd/archive/PIPELINE_INGESTAO_LEGAL/`) — `GCP_PROJECT_ID`/`GCS_BUCKET_NAME` já são reais (bucket `taxreformai-dev-legal-docs` provisionado via Terraform); `QDRANT_URL`/`QDRANT_API_KEY` também já configurados (Qdrant Cloud free tier), todos em GitHub Secrets. Busca híbrida real ainda não verificada E2E — só roda de fato via `dags/ingestao_legal_dag.py` num Cloud Composer real, pendente de provisionamento | Raspa o Planalto, estrutura a legislação em árvore AST (Lei→Título→Capítulo→Artigo→Parágrafo→Inciso→Alínea), gera chunks parent-child e indexa via embedding híbrido (BGE-M3+BM25) no Qdrant |
| `INGESTAO_TCU_E_ETL_AIRFLOW` (`ingestion/scraper/tcu_scraper.py`, `ingestion/parser/resolucao_parser.py`, `dags/`) | ✅ Shipado (`.claude/sdd/archive/INGESTAO_TCU_E_ETL_AIRFLOW/`) | Segunda fonte real (Resoluções TCU em PDF, via `pdftotext`) provando que `LegalSource`/`Lei.artigos_soltos`/`chunker.py` já eram genéricos o bastante sem modificação; `dags/ingestao_legal_dag.py` escreve a orquestração real do Airflow/Cloud Composer (TaskFlow API) que substitui a CLI — `apache-airflow` não instala neste sandbox, então a DAG é validada por revisão de código, não por teste automatizado (execução real pendente de Cloud Composer provisionado, decisão de negócio fora de escopo) |
| `MOTOR_DETERMINISTICO_CALCULO` (`motor_calculo/`) | ✅ Shipado (`.claude/sdd/archive/MOTOR_DETERMINISTICO_CALCULO/`) | Calcula CBS/IBS/IS/Split Payment por fase da transição (2026-2033), com alíquotas rastreáveis ao artigo da LCP 214/2025. 2026 completo (CBS 0,9% art. 346 + IBS 0,1% art. 343); 2027-2028 **parcial** — o art. 344 fixa o IBS (0,05% estadual + 0,05% municipal), mas o art. 347 deixa a CBS dependente de alíquota de referência ainda não fixada, e o IS é fixado por lei ordinária por produto. Alíquota não fixada é `None`, nunca estimada: a recusa nomeia o tributo faltante e o dispositivo que o rege |
| `ORQUESTRACAO_MULTIAGENTE` (`orquestracao/`) | ✅ Shipado (`.claude/sdd/archive/ORQUESTRACAO_MULTIAGENTE/`) | Grafo LangGraph com os 5 agentes do blueprint (Classificador→Pesquisador Legal→Extrator→Determinístico→Sintetizador); PII real (regex) e integração real com `motor_calculo`, demais nós fake (sem Claude/Vertex AI configurado ainda); `langgraph` não instalável neste sandbox — wiring isolado e não exercitado, ver BUILD_REPORT |
| `API_HTTP_SIMULACAO` (`api/`) | ✅ Shipado (`.claude/sdd/archive/API_HTTP_SIMULACAO/`) | FastAPI com `POST /v1/tax/simulate` (estruturado, schema da seção 8, integração ERP) e `POST /v1/tax/query` (conversacional, expõe `orquestracao/` via novo `orquestracao/executor.py` — sequencial, sem depender de `langgraph`); auth via `X-API-Key`. Primeira feature sem nenhum blocker de dependência; testada com `uvicorn` real + `curl`, não só testes automatizados |
| `FRONTEND_SIMULADOR` (`frontend/`) | ✅ Shipado (`.claude/sdd/archive/FRONTEND_SIMULADOR/`) | Next.js 14 (App Router) com `/simulador` (formulário estruturado) e `/consulta` (conversacional), consumindo a API real; API key via `localStorage`. Corrigiu de quebra um bug crítico de CORS em `api/main.py` (a API não tinha `CORSMiddleware` — nenhuma chamada de um navegador real teria funcionado) |

| `SCHEMA_POSTGRESQL` (`db/`, `motor_calculo/regime_atual.py`) | ✅ Shipado (`.claude/sdd/archive/SCHEMA_POSTGRESQL/`) | Schema da seção 7 (multi-tenancy via RLS, audit log, cache de regras) **aplicado no Cloud SQL real** e conectado à API deployada — audit log gravando de verdade, provado por consulta separada. Mais o regime tributário vigente (PIS/COFINS, ICMS interestadual) com todas as alíquotas citadas por artigo real do Planalto/LexML, nunca de memória |
| `IPI_TIPI_MOTOR_CALCULO` (`api/ipi.py`, `db/repositorio.py`, `api/routers/simulate.py`) | ✅ Shipado (`.claude/sdd/archive/IPI_TIPI_MOTOR_CALCULO/`) — duas verificações reais: `migrar_banco.yml` com `verificar_ipi=sim` (run `30299629790`) provou que o papel de runtime `taxreformai_app` lê `aliquotas_ipi_tipi` (9231 linhas), distinguindo alíquota 0% real de "NT"; `deploy.yml` (run `30300917434`) confirmou `total_ipi=3.90` no smoke test contra a API pública | Liga a tabela `aliquotas_ipi_tipi` (9231 NCMs já ingeridos) ao `/v1/tax/simulate`: lookup em lote (1 query por request, `= ANY(%s)`), IPI por item com o `dispositivo_legal_ref` da própria linha como fonte. `ipi_situacao` é um enum de 5 estados — NT nunca vira 0%, NCM ausente nunca vira omissão, banco fora do ar nunca vira 5xx. Primeira das 11 features de `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` a ser shipada |

| `REGRAS_TRIBUTARIAS_CACHE` (`db/migrations/005`+`006`, `api/cesta_basica.py`, `api/ncm.py`, `motor_calculo/reducoes.py`) | ✅ Shipado (`.claude/sdd/archive/REGRAS_TRIBUTARIAS_CACHE/`) — duas verificações reais: `migrar_banco.yml` com `verificar_cesta_basica=sim` (run `30383959322`) provou que o papel de runtime lê o Anexo I (26 itens, 76 inclusões, 19 exceções) e confirmou os 3 mecanismos — correspondência exata (manteiga, `04051000`), por prefixo/posição (`09012100`) e exclusão (`02074300`, excluído pelo item 19); `deploy.yml` (run `30384142935`) confirmou `situacao=APLICADA, cbs dispensado=9.00` no smoke test contra a API pública | Cesta Básica Nacional (LCP 214/2025, art. 125 e Anexo I, 26 itens transcritos do DOU): `/v1/tax/simulate` aplica alíquota **zero** de CBS/IBS por item, citando "art. 125, Anexo I, item N". Toda correspondência por NCM é prefixo de dígitos de 4 a 8 ("exato" é o prefixo de 8), o que resolve os 26 itens com um só mecanismo, inclusive as 19 exceções dos itens 19/20 (foie gras, salmonídeos, atuns). Remove `regras_tributarias_cache`/`buscar_regra_cache()` — código morto desde `SCHEMA_POSTGRESQL`. Degradação **conservadora**: falha de infra aplica a alíquota geral (nunca zero indevido) — segunda das 11 features de `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` |

| `ANEXOS_REDUCAO_ZERO_XII_XIII_XV` (`db/migrations/007`+`008`, `api/reducao_zero.py`, `api/ncm.py`) | 🔄 Construída e verificada contra o Cloud SQL real (`migrar_banco.yml` com `verificar_reducao_zero=sim`, run `30445357996`, 2026-07-29 — 7 casos reais, incluindo o desempate de 3 vias do Anexo XII e o prefixo de 2 dígitos do Anexo XV, sem regressão no Anexo I) — falta só o deploy com o smoke test novo | Generaliza o schema do Anexo I para os **4 Anexos de redução a ZERO** da LCP 214/2025 e carrega os 3 que faltavam: XII (art. 144, dispositivos médicos), XIII (art. 145, acessibilidade) e XV (art. 148, hortícolas/frutas/ovos). `cesta_basica_anexo_i*` → `anexos_reducao_zero*`, chave `(anexo, item, sub_item)`, 60 itens / 151 prefixos. Prefixo passa a aceitar **capítulo (2 dígitos)** — `{2,4,5,6,7,8}`, sem o 3, que a NCM não tem. Bloco da resposta renomeado de `cesta_basica` para `reducao_zero`, sem alias. Nenhuma linha nova em `motor_calculo/`: o art. 148 diz "reduzidas a zero", então `aplicar_reducao_a_zero` serve os 4 — 12ª posição do roadmap, primeira da "segunda leva" |

Os 5 componentes centrais do blueprint (ingestão, motor, orquestração, API, frontend) existem agora, mais a segunda fonte de ingestão (TCU), a camada ETL real (Airflow, escrita), o CD para Cloud Run, o schema PostgreSQL real e conectado, o IPI consumindo a TIPI já ingerida, e a Cesta Básica Nacional zerando CBS/IBS por item — 10 features shipadas, mais a 11ª construída e pendente de verificação real. A `DEPLOY_CLOUD_RUN` (2026-07-25, `.claude/sdd/archive/DEPLOY_CLOUD_RUN/`) tem **7/7 acceptance tests verificados contra infraestrutura real** — a primeira feature do projeto nesse patamar, seguida por `SCHEMA_POSTGRESQL`, `IPI_TIPI_MOTOR_CALCULO` e `REGRAS_TRIBUTARIAS_CACHE`. A aplicação está pública, funcionando, e agora persiste dados de verdade.

### Fontes legais ingeridas (verificado em produção, 2026-07-25)

Coleção Qdrant `legislacao_tributaria` com **6866 pontos**; verificação E2E da busca híbrida
**APROVADA** (Bloco A 5/5, Bloco B 2/2) — o critério pendente desde o ship de
`PIPELINE_INGESTAO_LEGAL` está fechado.

| Fonte | Documento | Artigos | Chunks |
|-------|-----------|---------|--------|
| Planalto (DOU) | LCP 214/2025 | 580 | 3417 |
| CGIBS | Resolução 6/2026 (regulamenta o IBS) | 617 | 3443 |
| RFB (SIJUT2) | Soluções de Consulta — ementas | 28 | 28 |
| TCU | Resolução 388/2026 | 16 | 27 |

Das 4 famílias mapeadas no blueprint (seção 4.1), **3 estão cobertas**: DOU (via Planalto),
Comitê Gestor do IBS e RFB. Mais o TCU, que não estava mapeado.

**SPED / IBPT — decisão de 2026-07-25: fora do pipeline de ingestão.** São dados **tabulares**
(NCM → alíquota aproximada, Lei 12.741/2012), não legislação: consulta é por chave exata, não
semântica, então embedá-los no Qdrant seria a ferramenta errada. Pertencem ao schema PostgreSQL
e são consultados deterministicamente — o padrão que `aliquotas_ipi_tipi` (migração 004) e
`anexos_reducao_zero` (migrações 005→007→008) já concretizaram. (A tabela genérica `regras_tributarias_cache`
que a seção 7 do blueprint previa para isso **foi removida** pela migração 006: sua forma —
alíquota absoluta, um NCM por linha, sem exceções — não serve para nenhum regime diferenciado real.)
Além disso a tabela IBPT exige **cadastro de empresa** e é produto licenciado de um instituto
privado — não legislação em domínio público como as outras três. É decisão de licenciamento,
não técnica. A tabela ainda tem vigência de ~2 meses e é reeditada bimestralmente, o que a torna
um problema de sincronização periódica, não de ingestão documental.

CI/CD: `ci.yml` roda pytest (com **container de serviço PostgreSQL real** — os testes de schema/RLS
executam contra Postgres de verdade, não SQLite) + testes de frontend a cada push/PR;
`terraform.yml` faz plan/apply via `workflow_dispatch`; `deploy.yml` publica no Cloud Run e liga a
API ao Cloud SQL via `workflow_dispatch`; `ingestao.yml` roda a ingestão real + verificação E2E da
busca híbrida via `workflow_dispatch` (guarda `INGERIR`, também usado por `verificar_lc227` para
diagnósticos de leitura pontuais contra o Qdrant); `migrar_banco.yml` aplica migrações e
prova RLS + a leitura de IPI e dos 4 Anexos de alíquota zero (I, XII, XIII, XV) pelo papel de
runtime contra o Cloud SQL real via `workflow_dispatch` (guarda `MIGRAR`). O bucket GCS e o
Cloud SQL já foram aplicados de verdade; o state do Terraform é remoto (`gs://taxreformai-dev-tfstate`).

Próximo ciclo: aplicar as migrações 007/008 e deployar (nessa ordem — ver "Banco de dados"), depois
conectar LLMs reais (Vertex AI) — 4 dos 5 nós da orquestração ainda são fake — e verificação manual
em navegador, agora possível porque há URL pública (a extensão do Chrome não estava conectada nas
últimas tentativas). **SPED/IBPT** seguem fora de escopo — ver decisão abaixo.

**Achado do `/design` de `ANEXOS_REDUCAO_ZERO_XII_XIII_XV` que muda a próxima feature (posição 13):**
os arts. 144, **II** e 145, **II** da LCP 214/2025 reduzem a **zero** os Anexos **IV** e **V** quando
o adquirente é órgão público ou entidade CEBAS. Ou seja, IV e V **não são apenas "60%"**, como o
roadmap os classifica: têm uma alíquota zero condicionada ao *comprador*, condição que o payload
atual de `/v1/tax/simulate` não expressa. Nada foi feito a respeito nesta feature (IV e V estão
explicitamente fora do escopo dela); entra no `/define` da posição 13.

## Stack planejada (extraída de `contexto.md`)

- **Frontend:** Next.js 14 (App Router) + TailwindCSS + Shadcn UI + TanStack Query
- **Backend/API:** FastAPI (Python 3.11+) + Pydantic v2 + Celery/Redis (fila assíncrona)
- **Orquestração multi-agente:** LangGraph / CrewAI + Anthropic Claude via Vertex AI (Claude 3.5 Sonnet e Haiku)
- **Motor determinístico:** Python puro (sandbox), sem LLM, para cálculos de IVA Dual/Split Payment
- **Banco relacional:** Cloud SQL (PostgreSQL 16) — **real, aplicado e conectado** desde `SCHEMA_POSTGRESQL` (2026-07-27)
- **Banco vetorial:** Qdrant Cloud (busca híbrida densa/esparsa, embeddings `intfloat/multilingual-e5-large` + BM25 esparso — o blueprint pede BGE-M3, mas o `fastembed` não o suporta; ver `ingestion/embedding/hybrid_embedder.py`)
- **Data lake:** Google Cloud Storage (GCS)
- **Ingestão/ETL:** Scrapy / Playwright orquestrados via Airflow (Cloud Composer)
- **Infraestrutura:** GCP — Cloud Run (serverless), Cloud Composer, BigQuery, região `southamerica-east1`

## Estrutura

```
TaxReformAI/
├── contexto.md              # Blueprint completo: produto, arquitetura, infra, DB, API, pricing
├── CLAUDE.md                 # Este arquivo
├── ingestion/                # PIPELINE_INGESTAO_LEGAL + INGESTAO_TCU — scraper, parser AST, chunker, embedder, indexador Qdrant
│   ├── scraper/               # PlanaltoScraper + TCUScraper (LegalSource)
│   ├── parser/                 # AST hierárquica (Secao recursiva + Artigo/Parágrafo/Inciso/Alínea) + resolucao_parser.py (PDF/TCU)
│   ├── chunking/                # Chunk (Pydantic) + chunker parent-child
│   ├── embedding/                 # Hybrid embedder (multilingual-e5-large + BM25)
│   ├── storage/                    # RawStorage (GCS real + fake para testes)
│   ├── indexing/                    # QdrantIndexer
│   └── pipeline.py                   # CLI de orquestração (executar_pipeline, parser injetável)
├── dags/                     # INGESTAO_TCU_E_ETL_AIRFLOW — DAG real do Airflow/Cloud Composer
│   └── ingestao_legal_dag.py  # TaskFlow API; não importável neste sandbox (apache-airflow ausente), só revisão de código
├── motor_calculo/            # MOTOR_DETERMINISTICO_CALCULO + SCHEMA_POSTGRESQL — cálculo tributário
│   ├── fases.py               # FaseTransicao + fase_para(ano)
│   ├── regras_fiscais.py       # RegraFiscal (alíquota `Decimal | None` + fonte por tributo) + AliquotaNaoDisponivelError
│   ├── tabela_aliquotas.py      # TabelaAliquotas (Protocol) + seed com artigos reais (2026 completo, 2027-28 parcial)
│   ├── engine.py                 # TaxCalculatorEngine — CBS/IBS/IS (reforma)
│   ├── reducoes.py                 # aplicar_reducao_a_zero — override por ITEM depois de calcular(); CBS/IBS a zero, IS intacto, líquido recomposto. Python puro, zero infra
│   └── regime_atual.py            # PIS/COFINS + ICMS interestadual + ICMS interno (27 UFs) + ISS piso/teto (regime VIGENTE) — cada alíquota citada por artigo real; IPI NÃO mora aqui (precisa de banco), vive em api/ipi.py
├── db/                        # SCHEMA_POSTGRESQL — schema real no Cloud SQL (taxreformai-pg)
│   ├── migrations/              # 001 (tabelas) → 002 (RLS) → 003 (privilégio mínimo do papel app) → 004 (aliquotas_ipi_tipi + GRANT) → 005 (Cesta Básica/Anexo I: 2 tabelas + seed dos 26 itens/95 prefixos + GRANT) → 006 (DROP guardado de regras_tributarias_cache) → 007 (RENAME para anexos_reducao_zero* + chave (anexo,item,sub_item) + prefixo de 2 dígitos) → 008 (seed dos Anexos XII/XIII/XV: 34 itens/56 prefixos + asserções)
│   ├── migrador.py               # Runner idempotente, sem ORM
│   └── repositorio.py             # sessao_do_tenant, registrar_parecer, resolver_tenant, buscar_ipi_por_ncm e buscar_reducao_zero_por_prefixo (ambos em lote, 1 query)
├── api/db.py                # Pool de conexão (Depends, overridável em teste — mesmo padrão de api/config.get_settings)
├── api/audit.py              # registrar_com_seguranca — audit log que NUNCA propaga exceção
├── api/ipi.py                # IPI_TIPI — normalizar_ncm + resolver_item (5 situações) + consultar_ipi_com_seguranca; gêmeo de LEITURA do audit.py, também nunca propaga
├── api/ncm.py                # Vocabulário da NCM/SH — digitos_ncm (8 dígitos canônicos) + prefixos_ncm ({2,4,5,6,7,8}, sem o 3, que a NCM não tem); UMA noção de "NCM válido" para IPI e redução a zero
├── api/reducao_zero.py       # ANEXOS_REDUCAO_ZERO — resolver_item (6 situações) nos 4 Anexos + consultar_com_seguranca + formatar_item; degradação CONSERVADORA (alíquota geral, nunca null)
├── api/Dockerfile           # DEPLOY_CLOUD_RUN — build context é a RAIZ do repo; copia api/, motor_calculo/, orquestracao/, ingestion/ E db/
├── frontend/Dockerfile       # DEPLOY_CLOUD_RUN — multi-stage (deps→builder→runner), Next.js standalone, usuário não-root
├── requirements-api.txt      # Deps de runtime SÓ da API (fastapi/uvicorn/pydantic/psycopg) — o que vai para a imagem; requirements.txt inclui via `-r`
├── infra/terraform/         # Bucket GCS + Artifact Registry + SA de deploy + Cloud SQL (taxreformai-pg) — state remoto em gs://taxreformai-dev-tfstate
├── .github/workflows/        # ci.yml (pytest + frontend, com Postgres real de serviço) + terraform.yml + deploy.yml (Cloud Run + Cloud SQL) + ingestao.yml + migrar_banco.yml — os 4 últimos só por workflow_dispatch
├── scripts/                  # verificar_busca_hibrida.py, aplicar_migracoes.py, popular_tenants.py, verificar_rls_producao.py, verificar_audit_log_gravado.py, ingerir_tipi.py, verificar_ipi_producao.py, verificar_reducao_zero_producao.py — todos rodam só via workflow, nunca local
├── tests/                    # 371 testes (368 passed + 3 skipped local, pytest) — os de schema/RLS/TIPI/Anexos pulam sem DATABASE_URL, rodam de verdade no CI
├── .env.example              # Template de variáveis — .env local fica só com config não-sensível (ex: FRONTEND_ORIGINS); credenciais reais vivem em GitHub Secrets
└── .claude/sdd/               # Documentos do workflow SDD (features/, reports/, archive/)
```

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `contexto.md` | Fonte única de verdade do projeto: visão de produto, ICP/personas, linha do tempo da reforma tributária, arquitetura multi-agente (5 agentes especialistas + matriz de modelos Claude), pipeline ETL de dados públicos, chunking hierárquico AST, stack GCP, motor de cálculo (exemplo), modelagem PostgreSQL, spec da API `/v1/tax/simulate`, modelo de negócio SaaS |
| `ingestion/pipeline.py` | Ponto de entrada do pipeline de ingestão — `executar_pipeline()` é testável com fakes (`parser` injetável, reaproveitado pelo TCU); execução real só via `dags/ingestao_legal_dag.py` num Cloud Composer real, nunca local |
| `motor_calculo/engine.py` | Ponto de entrada do motor de cálculo — `TaxCalculatorEngine(tabela).calcular(...)`, sem dependências externas |
| `.claude/sdd/archive/MOTOR_DETERMINISTICO_CALCULO/SHIPPED_2026-07-23.md` | Lições aprendidas da feature já shipada — vale ler antes de iniciar a próxima |
| `.claude/sdd/archive/PIPELINE_INGESTAO_LEGAL/SHIPPED_2026-07-24.md` | Lições da primeira feature de ingestão — padrão `Protocol` real/fake (`RawStorage`/`LegalSource`) que se repetiu em todas as features seguintes |
| `.claude/sdd/archive/INGESTAO_TCU_E_ETL_AIRFLOW/SHIPPED_2026-07-24.md` | Lições aprendidas da feature TCU/Airflow — bugs reais de parsing de PDF (referência cruzada, bloco de assinatura) só apareceram contra o documento real |
| `dags/ingestao_legal_dag.py` | DAG real do Airflow/Cloud Composer que substitui `pipeline.py` como orquestrador — não executável neste sandbox, só revisão de código |
| `.claude/sdd/archive/SCHEMA_POSTGRESQL/SHIPPED_2026-07-27.md` | Lições da feature do schema — a mais cara: nenhum papel no Cloud SQL (nem `postgres`) é superusuário de verdade, diferente de Postgres autogerido; qualquer config de papel testada só contra Postgres genérico merece diagnóstico direto contra o serviço gerenciado antes de assumir paridade |
| `motor_calculo/regime_atual.py` | PIS/COFINS + ICMS interestadual — ponto de entrada do regime vigente, `TabelaPisCofins().buscar(regime)` e `icms_interestadual(uf_origem, uf_destino, bem_importado=...)` |
| `db/repositorio.py` | Ponto de entrada do acesso a dados — `sessao_do_tenant()` é o único jeito correto de tocar tabelas com RLS |
| `db/migrations/005_cesta_basica_anexo_i.sql` | A transcrição literal do Anexo I (26 itens, 95 prefixos) com a URL da fonte primária no cabeçalho — é o documento de auditoria da Cesta Básica, não só um script. A CHECK `prefixo = regexp_replace(texto_ncm, '[^0-9]', '', 'g')` impede transcrição inconsistente. **Não se edita**: migração aplicada é histórico, e a forma dela foi generalizada pela 007 |
| `db/migrations/008_anexos_reducao_zero_xii_xiii_xv.sql` | A transcrição literal dos Anexos XII, XIII e XV (34 itens, 56 prefixos), com URL da fonte, o **catálogo das 7 cláusulas "exceto"** (operante × descritiva × não codificável) e um bloco de asserções que faz rollback se a transcrição não fechar — inclusive se uma exceção ficar órfã |
| `api/reducao_zero.py` | Ponto de entrada dos 4 Anexos de alíquota zero — `resolver_item(natureza, ncm, consulta)`, função pura com 6 situações; `EXCLUIDA_EXPRESSAMENTE` (o Anexo exclui o código) NÃO é `FORA_DO_ANEXO`. O desempate é `(len(prefixo), -anexo_ordem, -item, -sub_item)` |

## Convenções

- **Linter:** `ruff` (`ruff check .` — configurado e limpo; `pyproject.toml` declara `select` explícito desde 2026-07-25, para não depender do default de cada versão instalada)
- **Formatter:** não configurado explicitamente (código segue `ruff format` implicitamente)
- **Testes:** `pytest` — `python3 -m pytest tests/ -v` (334 testes: 331 passed + 3 skipped local; os de `db/` pulam sem `DATABASE_URL`, rodam de verdade no CI contra um container `postgres:16`)

## Como rodar

```bash
pip install -r requirements.txt   # set completo (dev/CI); qdrant-client, google-cloud-storage, fastembed, typer, apache-airflow não instaláveis neste sandbox — ver BUILD_REPORTs
pip install -r requirements-api.txt # só o runtime da API (fastapi/uvicorn/pydantic/psycopg) — é o que a imagem do Cloud Run instala
python3 -m pytest tests/ -v        # roda os testes sem precisar de nenhuma credencial (usa fakes, e pula os de schema sem DATABASE_URL); exige poppler-utils (pdftotext) no sistema para os testes do TCUScraper
```

**Política do projeto: infraestrutura real nunca roda local.** `.env` local é só para o que os testes fake precisam (hoje, nada de credencial real) — nunca para disparar a pipeline de ingestão contra GCS/Qdrant reais na sua máquina. Credenciais reais (`GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `GCP_SA_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`) vivem em **GitHub Secrets** do repositório e são consumidas por workflows (`terraform.yml` já aplicou o bucket GCS real; a execução da pipeline de ingestão em si ainda depende de `dags/ingestao_legal_dag.py` rodar num Cloud Composer real, ou de um workflow `workflow_dispatch` equivalente). O motor de cálculo (`motor_calculo/`) não precisa de nenhuma infraestrutura — roda direto, local ou não.

## Deploy (Cloud Run)

`.github/workflows/deploy.yml`, **só por `workflow_dispatch`** (nunca no push) com `target` = `api` | `frontend` | `both` e `confirm` = `DEPLOY`. Publica imagens no Artifact Registry tagueadas pelo SHA do commit e atualiza dois serviços em `southamerica-east1`: `taxreformai-api` e `taxreformai-frontend`.

**Ordem importa, por uma dependência circular real:** `NEXT_PUBLIC_API_BASE_URL` é embutida no bundle JS em *build time*, enquanto `FRONTEND_ORIGINS` é lida pela API em *runtime*. O workflow resolve isso lendo as URLs existentes primeiro, deployando a API, buildando o frontend com a URL real da API, e por fim reconciliando o `FRONTEND_ORIGINS` da API (só cria revisão nova se o valor mudou).

**O smoke test reprova o job** — e isso não é redundante: os defaults de `api/main.py` (`FRONTEND_ORIGINS=localhost:3000`) e `api/config.py` (`API_KEYS={}`) fazem um deploy incompleto subir um serviço que responde **200 em `/health`** e falha 100% das requisições reais. Por isso o smoke test também faz um `POST /v1/tax/simulate` com chave real e confere o header `access-control-allow-origin`.

Secrets necessários: `GCP_PROJECT_ID`, `GCP_DEPLOYER_SA_KEY` (SA `taxreformai-deployer`, escopada — não reusar `GCP_SA_KEY`, que é do Terraform) e `API_KEYS` (JSON `{"chave":"tenant_id"}`). O `tenant_id` do corpo de `POST /v1/tax/simulate` precisa bater com o da credencial, senão a resposta é **403**.

## Estado do runbook

**A aplicação está no ar e persiste dados de verdade.** Serviços públicos:

| Serviço | URL |
|---------|-----|
| API | `https://taxreformai-api-as2g43xasa-rj.a.run.app` |
| Frontend | `https://taxreformai-frontend-as2g43xasa-rj.a.run.app` |

Identidade de runtime: `taxreformai-runtime@taxreformai-dev.iam.gserviceaccount.com`,
deliberadamente **sem role de projeto** — só `roles/cloudsql.client` e leitura do próprio secret
de senha, o mínimo para falar com o Cloud SQL. Nem API nem frontend acessam mais nada no GCP em
runtime.

## Banco de dados (Cloud SQL)

Instância `taxreformai-pg` (PostgreSQL 16, `db-f1-micro`, `southamerica-east1`), schema aplicado e
API conectada — ver `.claude/sdd/archive/SCHEMA_POSTGRESQL/`.

- **Dois papéis**: `taxreformai_admin` (migrações — `migrar_banco.yml`, guarda `MIGRAR`) e
  `taxreformai_app` (runtime da API, privilégio mínimo — `db/migrations/003_papel_da_aplicacao.sql`).
  Senhas geradas pelo Terraform, vivem no Secret Manager (`taxreformai-pg-admin-password`,
  `taxreformai-pg-app-password`), nunca em texto plano em workflow.
- **RLS isola tenants de verdade**, provado contra o Cloud SQL real (não só inferido) por
  `scripts/verificar_rls_producao.py`, rodável via `migrar_banco.yml` (`verificar_rls=sim`).
- **Achado que vale lembrar**: nenhum papel no Cloud SQL — nem `postgres` — tem `rolsuper=true`.
  A migração 003 tentou originalmente revogar `SUPERUSER`/`BYPASSRLS`, o que é impossível de
  executar lá (só quem já é superusuário pode tocar esse atributo) e desnecessário (a plataforma
  nunca concede o bit). Ver a Lição 3 do SHIPPED da feature antes de portar qualquer config de
  papel testada só contra Postgres genérico.
- **Audit log gravando em produção**, confirmado por consulta separada depois do smoke test do
  deploy (`deploy.yml`, passo "Verificar que o audit log foi gravado de verdade").
- **`aliquotas_ipi_tipi`** (migração 004, 9231 NCMs) é lida em runtime pelo `/v1/tax/simulate`.
  O `GRANT SELECT` ao papel `taxreformai_app` **nunca havia sido exercitado por nenhum SELECT** —
  e, como a falha degrada silenciosamente (200 com `total_ipi: null`), só um teste ativo a
  detecta: `scripts/verificar_ipi_producao.py`, via `migrar_banco.yml` (`verificar_ipi=sim`),
  conecta com o papel de RUNTIME e falha ruidosamente. O smoke test do `deploy.yml` fecha o E2E
  exigindo `regime_vigente.total_ipi` não-nulo.
- **`anexos_reducao_zero` / `anexos_reducao_zero_ncm`** (migrações 005 → 007 → 008; 60 itens + 151
  prefixos) guardam os **4 Anexos de alíquota ZERO** da LCP 214/2025: I (art. 125), XII (art. 144),
  XIII (art. 145) e XV (art. 148). Nasceram como `cesta_basica_anexo_i*` e foram **renomeadas** pela
  007 — um tomógrafo gravado numa tabela chamada "cesta básica" seria uma afirmação falsa num
  produto cujo valor é auditabilidade. Mesmo modo de falha silencioso do IPI, e **pior**: um `GRANT`
  faltando não gera erro nem campo nulo — gera a **alíquota geral da fase**, que é exatamente a
  resposta de antes da feature. Ela "funciona" verde sem fazer nada. Só dois testes ativos detectam:
  `scripts/verificar_reducao_zero_producao.py` (`migrar_banco.yml`, `verificar_reducao_zero=sim`,
  7 casos) e a **segunda e terceira** chamadas do smoke test do `deploy.yml` — deliberadamente
  separadas da do IPI, porque juntar os payloads faria `total_ipi` depender de `0405.10.00`/
  `06031100` estarem na TIPI ingerida.
- **A migração 007 renomeia tabelas em uso**, então a ordem é `migrar_banco.yml` → `deploy.yml`,
  nessa sequência. A janela entre as duas é declarada e aceita: a API antiga consulta um nome que
  não existe mais, cai no `except` de `consultar_com_seguranca` e devolve 200 com a alíquota geral.
  Nenhum 5xx, nenhum cálculo errado para menos.
- **`regras_tributarias_cache` não existe mais** (migração 006, `DROP` guardado por uma checagem
  de "está vazia?"). Era código morto de schema desde a 001.

## Regime tributário vigente (`motor_calculo/regime_atual.py`)

Ao lado do IVA Dual da reforma (`engine.py`), calcula o que já é devido hoje — necessário porque a
compensação do art. 348 (2026, ver `AliquotaNaoDisponivelError`/`Compensacao` na API) só faz
sentido se PIS/COFINS também estiverem calculados. Todas as alíquotas foram lidas do texto oficial
do Planalto/LexML (PIS/COFINS, ICMS interestadual) ou do RICMS/lei de cada UF (ICMS interno), nunca
de memória (Leis 10.637/2002, 10.833/2003, 9.715/1998, 9.718/1998; Resoluções do Senado 22/1989 e
13/2012). `regime_apuracao` no payload de `/v1/tax/simulate` é opcional sem default — `None`
significa "não informado", nunca "presume-se X".

**ICMS interno e ISS — adicionados em 2026-07-27**, revertendo a premissa original de que eram um
"limite estrutural" sem fonte citável: `icms_interno(uf)` cobre a alíquota GERAL/modal das 27 UFs
(verificação individual contra o RICMS/lei de cada estado — não existe agregador federal tipo
CONFAZ), incluindo FECP separado onde existe (RJ +2%, SE +1%, com base legal própria distinta do
ICMS); `iss_faixa()` cobre o piso (2%) e teto (5%) federais do ISS (LC 116/2003, arts. 8º-A e 8º).
Nenhum dos dois cobre exceção por mercadoria/serviço específico (cesta básica, combustíveis etc.),
e para essas não há fonte única citável (seriam 27 regulamentos e 5.570 leis municipais). **Já
plugados em `/v1/tax/simulate`**: o endpoint escolhe interno x interestadual por
`uf_origem == uf_destino` e ICMS x ISS por `natureza` do item, e o escopo da resposta é dinâmico —
declara em `tributos_incluidos` só o que aquele payload de fato disparou.

**IPI — deixou de estar fora de escopo em 2026-07-27** (`IPI_TIPI_MOTOR_CALCULO`). A premissa
antiga ("dado tabular sem alíquota única para citar", mesma razão do SPED/IBPT) foi refutada na
prática: a TIPI é **um decreto federal só** (11.158/2022), foi ingerida em `aliquotas_ipi_tipi`
(9231 códigos NCM, cada linha com seu `dispositivo_legal_ref`) e agora é consultada por
`api/ipi.py`. O que continua valendo é o motivo pelo qual ele **não** mora em
`motor_calculo/regime_atual.py`: esse módulo é Python puro, sem I/O, e o IPI precisa de banco.
`TRIBUTOS_INDISPONIVEIS` ficou vazia — o IPI entra/sai do escopo pelo mesmo mecanismo dinâmico de
ICMS_INTERNO/ISS. SPED/IBPT seguem fora, por razão diferente e ainda válida (licenciamento e
reedição bimestral, não formato).

---

## Agentes recomendados (agentcode)

| Agente | Quando usar | Status |
|--------|-------------|--------|
| `@brainstorm-agent` | Explorar e refinar decisões de arquitetura ainda em aberto antes de começar a implementar | ✅ Usado nas 6 features shipadas |
| `@design-agent` | Detalhar a especificação técnica de cada componente antes do build | ✅ Usado nas 6 features shipadas |
| `@python-developer` | Implementar o motor determinístico e o pipeline de ingestão | ✅ `motor_calculo/` shipado; `ingestion/` (Planalto + TCU) com build completo |
| `@qdrant-specialist` | Configurar a coleção Qdrant para busca híbrida (densa e5-large + esparsa BM25) | 🔄 Código pronto (`qdrant_indexer.py`); credenciais reais já em GitHub Secrets, ainda não exercitado contra Qdrant Cloud de verdade |
| `@gcp-data-architect` / `@ai-data-engineer-gcp` | Implementar a infraestrutura GCP (GCS, bucket) | ✅ Terraform aplicado de verdade — bucket `taxreformai-dev-legal-docs` real no projeto `taxreformai-dev` |
| `@genai-architect` | Desenhar/evoluir a orquestração multi-agente (LangGraph) e o roteamento de modelos Claude (seção 3) | ✅ Grafo shipado com fakes; falta conectar LLMs reais e instalar `langgraph` de verdade |
| `@airflow-specialist` | Construir as DAGs de scraping do DOU/RFB/Comitê IBS (seção 4.2) — hoje o pipeline roda como CLI simples, não como DAG | 🔄 `dags/ingestao_legal_dag.py` escrito com TaskFlow API real (Planalto + TCU); `apache-airflow` não instala neste sandbox — não executável, só revisão de código até haver Cloud Composer real |
| `@database-reviewer` | Schema PostgreSQL (multi-tenancy, audit log, cache de regras tributárias, seção 7) | ✅ Shipado — RLS provado contra Cloud SQL real, conectado à API |
| `@typescript-reviewer` | Frontend Next.js | ⏳ Não iniciado |
| **`@security-reviewer`** | **Sempre que houver manuseio de dados sensíveis (PII, CNPJ/CPF, multi-tenancy)** | **Já relevante** — `orquestracao/nos/classificador.py` mascara CPF/CNPJ; um bug de vazamento de PII no histórico auditável já foi encontrado e corrigido durante o build (ver `.claude/sdd/archive/ORQUESTRACAO_MULTIAGENTE/SHIPPED_2026-07-23.md`) — vale uma revisão de segurança dedicada antes de conectar dados reais de usuários |
| `@code-reviewer` | Sempre, após qualquer implementação de código | Recomendado para a próxima feature também |

## Comandos úteis

| Comando | Quando usar |
|---------|-------------|
| `/brainstorm` | Explorar decisões de arquitetura ainda em aberto (ex: próxima feature de orquestração multi-agente) |
| `/define` | Capturar requisitos estruturados a partir do brainstorm |
| `/design` (via Skill `agentcode:workflow:design` — o comando puro `/design` colide com um recurso nativo do Claude Code) | Criar a especificação técnica antes de implementar |
| `/build` | Executar a implementação a partir do DESIGN |
| `/ship` | Arquivar a feature completa com lições aprendidas |
| `/status` | Gerar relatório de status do projeto conforme o código for sendo criado |
| `/preflight` | Checar prontidão do projeto antes de builds/deploys futuros |

---

_Gerado por `/start` em 2026-07-22. Atualizado em 2026-07-23 após o build/ship de `MOTOR_DETERMINISTICO_CALCULO`, `ORQUESTRACAO_MULTIAGENTE`, `API_HTTP_SIMULACAO` e `FRONTEND_SIMULADOR`. Atualizado em 2026-07-24 após auditoria completa (CLAUDE.md/contexto.md vs. estado real do repo), CI/CD real (`.github/workflows/`), aplicação real do Terraform (bucket GCS), migração de credenciais para GitHub Secrets, e build de `INGESTAO_TCU_E_ETL_AIRFLOW`. Segunda auditoria (mesmo dia) encontrou e corrigiu o CI quebrado desde a criação — `requirements.txt` nunca listou `fastapi`/`uvicorn`. Revisão pós-build de `DEPLOY_CLOUD_RUN` (2026-07-25) achou 4 defeitos reais — point id do Qdrant que não era UUID, CLI `typer` achatada, `COPY /app/public` sobre diretório inexistente e a discordância de identidade de runtime entre Terraform e `deploy.yml` — e o primeiro deploy real ficou verde no mesmo dia, junto com o ship do CGIBS/RFB como 3ª e 4ª fontes legais e a verificação E2E da busca híbrida (6866 pontos indexados, Bloco A 5/5 filtrado por documento). Atualizado em 2026-07-27 após o build/ship de `SCHEMA_POSTGRESQL`: schema da seção 7 aplicado no Cloud SQL real, RLS provado (não só inferido) contra a instância real, regime tributário vigente (PIS/COFINS/ICMS interestadual) com 7 alíquotas citadas por artigo, e a API deployada gravando audit log de verdade — achado mais caro da feature foi que nenhum papel no Cloud SQL, nem `postgres`, é superusuário de verdade, ao contrário de Postgres autogerido. Ver `.claude/sdd/archive/SCHEMA_POSTGRESQL/SHIPPED_2026-07-27.md`. Atualizado em 2026-07-28 após o build/ship de `IPI_TIPI_MOTOR_CALCULO`, primeira das 11 features de `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` (auditoria pós-`SCHEMA_POSTGRESQL` que levantou 12 achados): a TIPI (9231 NCM), ingerida desde a feature anterior mas sem consumidor, passou a alimentar `/v1/tax/simulate` via `api/ipi.py`, com um enum de 5 estados que nunca confunde NT com alíquota zero nem NCM ausente com omissão silenciosa — verificado em duas camadas de infraestrutura real (`migrar_banco.yml` run `30299629790`, `deploy.yml` run `30300917434`). Ver `.claude/sdd/archive/IPI_TIPI_MOTOR_CALCULO/SHIPPED_2026-07-28.md`. Atualizado em 2026-07-28 após o build/ship de `REGRAS_TRIBUTARIAS_CACHE` (2ª das 11): a Cesta Básica Nacional (LCP 214/2025, art. 125 e Anexo I, 26 itens transcritos da publicação oficial do DOU espelhada pelo Senado) passou a zerar CBS/IBS por item em `/v1/tax/simulate`, com o item do Anexo citado em cada um; toda correspondência por NCM virou prefixo de dígitos de 4 a 8, o que resolveu num só mecanismo os 20 itens "exatos", os 6 não-triviais e as 19 exceções dos itens 19/20; `regras_tributarias_cache`/`buscar_regra_cache()` foram removidos como código morto. Verificado em duas camadas de infraestrutura real — `migrar_banco.yml` (run `30383959322`) e `deploy.yml` (run `30384142935`) —, o que aqui importa mais do que nas features anteriores porque o único modo de falha desta feature (migração não aplicada, `GRANT` faltando) é indistinguível do sucesso: degrada para a alíquota geral da fase, a mesma resposta de antes da feature existir. Ver `.claude/sdd/archive/REGRAS_TRIBUTARIAS_CACHE/SHIPPED_2026-07-28.md`. De passagem, esta sessão também resolveu (sem virar feature, sem `/design`/`/build`) a investigação sobre a LC 227/2026 aberta durante o `/define` desta feature: um diagnóstico de leitura contra o Qdrant real (`ingestao.yml`, run `30368697093`) confirmou que o corpus já reflete a lei (encontrou o art. 341-A e o Inciso IV do art. 344, ambos exclusivos da LC 227/2026), sem necessidade de reingestão — arquivado em `.claude/sdd/archive/LC_227_2026_ATUALIZACAO_LEGAL/`. Atualizado em 2026-07-28 após o `/build` de `ANEXOS_REDUCAO_ZERO_XII_XIII_XV` (12ª do roadmap, primeira da "segunda leva"): o schema do Anexo I foi **generalizado por `ALTER`** para os 4 Anexos de redução a zero da LCP 214/2025 — `cesta_basica_anexo_i*` → `anexos_reducao_zero*`, chave `(anexo, item, sub_item)` — e os Anexos XII (art. 144), XIII (art. 145) e XV (art. 148) foram transcritos do DOU (34 itens, 56 prefixos, 60/151 no total). O prefixo de NCM passou a aceitar **capítulo (2 dígitos)**, exigido pelo "Capítulo 6" do Anexo XV, e o bloco `cesta_basica` da resposta virou `reducao_zero` **sem alias** (confirmado diretamente com o Jonatas), porque o mesmo bloco agora responde por um tomógrafo e por uma cadeira de rodas. `motor_calculo/` não ganhou uma linha: o art. 148 escreve "reduzidas a zero" mesmo com o cabeçalho do Anexo dizendo "100%", então `aplicar_reducao_a_zero` serve os 4 por texto de lei, não por analogia. **Ainda não verificado contra infraestrutura real** — `migrar_banco.yml` e depois `deploy.yml`, nessa ordem, são pré-requisito do `/ship`, porque a migração 007 renomeia tabelas em uso. Ver `.claude/sdd/features/BUILD_REPORT_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md`._
