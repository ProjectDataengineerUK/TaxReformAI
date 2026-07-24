# TaxReform AI

> Plataforma SaaS B2B Enterprise de Inteligência Tributária e Compliance em Tempo Real, para apoiar departamentos fiscais, controllers, CFOs e consultorias tributárias durante a transição do modelo tributário brasileiro (PIS, COFINS, IPI, ICMS, ISS) para o novo IVA Dual (CBS, IBS e Imposto Seletivo). Combina RAG Híbrido com AST de legislação, regras determinísticas de cálculo e guardrails contábeis em sandbox Python, garantindo simulações 100% auditáveis com citação de fontes oficiais.

---

## Status do projeto

`contexto.md` continua sendo o blueprint completo (produto, arquitetura multi-agente, infraestrutura GCP, modelagem de dados, API e modelo de negócio) que orienta a implementação. Seis features já foram construídas seguindo o workflow SDD (`/brainstorm` → `/define` → `/design` → `/build` → `/ship`), documentadas em `.claude/sdd/`:

| Feature | Status | O que faz |
|---------|--------|-----------|
| `PIPELINE_INGESTAO_LEGAL` (`ingestion/`) | ✅ Shipado (`.claude/sdd/archive/PIPELINE_INGESTAO_LEGAL/`) — `GCP_PROJECT_ID`/`GCS_BUCKET_NAME` já são reais (bucket `taxreformai-dev-legal-docs` provisionado via Terraform); `QDRANT_URL`/`QDRANT_API_KEY` também já configurados (Qdrant Cloud free tier), todos em GitHub Secrets. Busca híbrida real ainda não verificada E2E — só roda de fato via `dags/ingestao_legal_dag.py` num Cloud Composer real, pendente de provisionamento | Raspa o Planalto, estrutura a legislação em árvore AST (Lei→Título→Capítulo→Artigo→Parágrafo→Inciso→Alínea), gera chunks parent-child e indexa via embedding híbrido (BGE-M3+BM25) no Qdrant |
| `INGESTAO_TCU_E_ETL_AIRFLOW` (`ingestion/scraper/tcu_scraper.py`, `ingestion/parser/resolucao_parser.py`, `dags/`) | ✅ Shipado (`.claude/sdd/archive/INGESTAO_TCU_E_ETL_AIRFLOW/`) | Segunda fonte real (Resoluções TCU em PDF, via `pdftotext`) provando que `LegalSource`/`Lei.artigos_soltos`/`chunker.py` já eram genéricos o bastante sem modificação; `dags/ingestao_legal_dag.py` escreve a orquestração real do Airflow/Cloud Composer (TaskFlow API) que substitui a CLI — `apache-airflow` não instala neste sandbox, então a DAG é validada por revisão de código, não por teste automatizado (execução real pendente de Cloud Composer provisionado, decisão de negócio fora de escopo) |
| `MOTOR_DETERMINISTICO_CALCULO` (`motor_calculo/`) | ✅ Shipado (`.claude/sdd/archive/MOTOR_DETERMINISTICO_CALCULO/`) | Calcula CBS/IBS/IS/Split Payment por fase da transição (2026-2033), com alíquotas rastreáveis a fonte legal — só a fase de teste 2026 está confirmada; demais fases falham explicitamente em vez de estimar |
| `ORQUESTRACAO_MULTIAGENTE` (`orquestracao/`) | ✅ Shipado (`.claude/sdd/archive/ORQUESTRACAO_MULTIAGENTE/`) | Grafo LangGraph com os 5 agentes do blueprint (Classificador→Pesquisador Legal→Extrator→Determinístico→Sintetizador); PII real (regex) e integração real com `motor_calculo`, demais nós fake (sem Claude/Vertex AI configurado ainda); `langgraph` não instalável neste sandbox — wiring isolado e não exercitado, ver BUILD_REPORT |
| `API_HTTP_SIMULACAO` (`api/`) | ✅ Shipado (`.claude/sdd/archive/API_HTTP_SIMULACAO/`) | FastAPI com `POST /v1/tax/simulate` (estruturado, schema da seção 8, integração ERP) e `POST /v1/tax/query` (conversacional, expõe `orquestracao/` via novo `orquestracao/executor.py` — sequencial, sem depender de `langgraph`); auth via `X-API-Key`. Primeira feature sem nenhum blocker de dependência; testada com `uvicorn` real + `curl`, não só testes automatizados |
| `FRONTEND_SIMULADOR` (`frontend/`) | ✅ Shipado (`.claude/sdd/archive/FRONTEND_SIMULADOR/`) | Next.js 14 (App Router) com `/simulador` (formulário estruturado) e `/consulta` (conversacional), consumindo a API real; API key via `localStorage`. Corrigiu de quebra um bug crítico de CORS em `api/main.py` (a API não tinha `CORSMiddleware` — nenhuma chamada de um navegador real teria funcionado) |

Os 5 componentes centrais do blueprint (ingestão, motor, orquestração, API, frontend) existem agora, mais a segunda fonte de ingestão (TCU) e a camada ETL real (Airflow, escrita) — **todas as 6 features já shipadas**, `.claude/sdd/features/`/`reports/` vazios. CI/CD (`.github/workflows/ci.yml` roda pytest + testes de frontend a cada push/PR; `terraform.yml` faz plan/apply do GCS via `workflow_dispatch`) provisiona infraestrutura real — o bucket GCS já foi aplicado de verdade (`terraform.tfstate` local confirma). Candidatos para o próximo ciclo: (a) provisionar um Cloud Composer real para finalmente executar `dags/ingestao_legal_dag.py` (desbloqueia a verificação E2E da busca híbrida, pendente desde o ship de `PIPELINE_INGESTAO_LEGAL`), (b) **schema PostgreSQL** (seção 7 — multi-tenancy real, audit log, cache de regras), já que a API/frontend atuais só têm auth mínima sem tenant real por trás, ou (c) verificação manual em navegador real (a extensão Claude in Chrome não estava conectada durante o build do frontend).

## Stack planejada (extraída de `contexto.md`)

- **Frontend:** Next.js 14 (App Router) + TailwindCSS + Shadcn UI + TanStack Query
- **Backend/API:** FastAPI (Python 3.11+) + Pydantic v2 + Celery/Redis (fila assíncrona)
- **Orquestração multi-agente:** LangGraph / CrewAI + Anthropic Claude via Vertex AI (Claude 3.5 Sonnet e Haiku)
- **Motor determinístico:** Python puro (sandbox), sem LLM, para cálculos de IVA Dual/Split Payment
- **Banco relacional:** Cloud SQL (PostgreSQL 16)
- **Banco vetorial:** Qdrant Cloud (busca híbrida densa/esparsa, embeddings BGE-M3 + BM25 esparso)
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
│   ├── embedding/                 # Hybrid embedder (BGE-M3 + BM25)
│   ├── storage/                    # RawStorage (GCS real + fake para testes)
│   ├── indexing/                    # QdrantIndexer
│   └── pipeline.py                   # CLI de orquestração (executar_pipeline, parser injetável)
├── dags/                     # INGESTAO_TCU_E_ETL_AIRFLOW — DAG real do Airflow/Cloud Composer
│   └── ingestao_legal_dag.py  # TaskFlow API; não importável neste sandbox (apache-airflow ausente), só revisão de código
├── motor_calculo/            # MOTOR_DETERMINISTICO_CALCULO — cálculo de CBS/IBS/IS/Split Payment
│   ├── fases.py               # FaseTransicao + fase_para(ano)
│   ├── regras_fiscais.py       # RegraFiscal + AliquotaNaoDisponivelError
│   ├── tabela_aliquotas.py      # TabelaAliquotas (Protocol) + seed (só 2026)
│   └── engine.py                 # TaxCalculatorEngine
├── infra/terraform/         # Provisionamento do bucket GCS — aplicado de verdade (ver terraform.tfstate local, gitignored)
├── .github/workflows/        # ci.yml (pytest + testes frontend, a cada push/PR) + terraform.yml (plan/apply via workflow_dispatch)
├── tests/                    # 72 testes (pytest) cobrindo as cinco features com testes pytest (frontend usa vitest à parte)
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

## Convenções

- **Linter:** `ruff` (`ruff check .` — configurado e limpo)
- **Formatter:** não configurado explicitamente (código segue `ruff format` implicitamente)
- **Testes:** `pytest` — `python3 -m pytest tests/ -v` (72 testes, todos passando)

## Como rodar

```bash
pip install -r requirements.txt   # qdrant-client, google-cloud-storage, fastembed, typer, apache-airflow não instaláveis neste sandbox — ver BUILD_REPORTs
python3 -m pytest tests/ -v        # roda os 72 testes sem precisar de nenhuma credencial (usa fakes); exige poppler-utils (pdftotext) no sistema para os testes do TCUScraper
```

**Política do projeto: infraestrutura real nunca roda local.** `.env` local é só para o que os testes fake precisam (hoje, nada de credencial real) — nunca para disparar a pipeline de ingestão contra GCS/Qdrant reais na sua máquina. Credenciais reais (`GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `GCP_SA_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`) vivem em **GitHub Secrets** do repositório e são consumidas por workflows (`terraform.yml` já aplicou o bucket GCS real; a execução da pipeline de ingestão em si ainda depende de `dags/ingestao_legal_dag.py` rodar num Cloud Composer real, ou de um workflow `workflow_dispatch` equivalente). O motor de cálculo (`motor_calculo/`) não precisa de nenhuma infraestrutura — roda direto, local ou não.

---

## Agentes recomendados (agentcode)

| Agente | Quando usar | Status |
|--------|-------------|--------|
| `@brainstorm-agent` | Explorar e refinar decisões de arquitetura ainda em aberto antes de começar a implementar | ✅ Usado nas 6 features shipadas |
| `@design-agent` | Detalhar a especificação técnica de cada componente antes do build | ✅ Usado nas 6 features shipadas |
| `@python-developer` | Implementar o motor determinístico e o pipeline de ingestão | ✅ `motor_calculo/` shipado; `ingestion/` (Planalto + TCU) com build completo |
| `@qdrant-specialist` | Configurar a coleção Qdrant para busca híbrida (densa BGE-M3 + esparsa BM25) | 🔄 Código pronto (`qdrant_indexer.py`); credenciais reais já em GitHub Secrets, ainda não exercitado contra Qdrant Cloud de verdade |
| `@gcp-data-architect` / `@ai-data-engineer-gcp` | Implementar a infraestrutura GCP (GCS, bucket) | ✅ Terraform aplicado de verdade — bucket `taxreformai-dev-legal-docs` real no projeto `taxreformai-dev` |
| `@genai-architect` | Desenhar/evoluir a orquestração multi-agente (LangGraph) e o roteamento de modelos Claude (seção 3) | ✅ Grafo shipado com fakes; falta conectar LLMs reais e instalar `langgraph` de verdade |
| `@airflow-specialist` | Construir as DAGs de scraping do DOU/RFB/Comitê IBS (seção 4.2) — hoje o pipeline roda como CLI simples, não como DAG | 🔄 `dags/ingestao_legal_dag.py` escrito com TaskFlow API real (Planalto + TCU); `apache-airflow` não instala neste sandbox — não executável, só revisão de código até haver Cloud Composer real |
| `@database-reviewer` | Schema PostgreSQL (multi-tenancy, audit log, cache de regras tributárias, seção 7) | ⏳ Não iniciado |
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

_Gerado por `/start` em 2026-07-22. Atualizado em 2026-07-23 após o build/ship de `MOTOR_DETERMINISTICO_CALCULO`, `ORQUESTRACAO_MULTIAGENTE`, `API_HTTP_SIMULACAO` e `FRONTEND_SIMULADOR`. Atualizado em 2026-07-24 após auditoria completa (CLAUDE.md/contexto.md vs. estado real do repo), CI/CD real (`.github/workflows/`), aplicação real do Terraform (bucket GCS), migração de credenciais para GitHub Secrets, e build de `INGESTAO_TCU_E_ETL_AIRFLOW`. Segunda auditoria (mesmo dia) encontrou e corrigiu o CI quebrado desde a criação — `requirements.txt` nunca listou `fastapi`/`uvicorn` (mascarado por estarem instalados globalmente neste sandbox); `gh run list` mostrava falha nos dois runs anteriores e ninguém tinha checado. CI está verde pela primeira vez desde que foi criado._
