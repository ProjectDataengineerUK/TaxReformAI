# DEFINE: Segunda Fonte de Ingestão (TCU) + Camada ETL Real (Airflow)

> Adicionar o TCU (Resoluções em PDF) como segunda fonte de ingestão legal real e escrever a DAG do Airflow/Cloud Composer prevista no blueprint (seção 4.2/5.2), substituindo a CLI manual como orquestrador oficial do pipeline.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_TCU_E_ETL_AIRFLOW |
| **Date** | 2026-07-24 |
| **Author** | define-agent |
| **Status** | ✅ Shipped (2026-07-24) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O sistema hoje só ingeriu 1 das 9 fontes legais mapeadas (Planalto) e não tem nenhuma camada de orquestração ETL real — `ingestion/pipeline.py` é uma CLI disparada manualmente, não uma DAG do Airflow/Cloud Composer como o blueprint exige (seção 4.2/5.2). Sem uma segunda fonte real e sem orquestração agendável, a arquitetura `LegalSource` construída na feature anterior permanece não comprovadamente extensível, e o pipeline não pode rodar de forma recorrente e auditável em produção.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Agente Pesquisador Legal (RAG) | Consumidor interno do sistema multi-agente | Precisa citar a metodologia oficial de cálculo da alíquota de referência (Resoluções TCU), hoje inexistente na base indexada — só tem Planalto |
| Operador do pipeline | Responsável por manter a ingestão atualizada | Precisa de uma DAG agendável e monitorável em vez de rodar a CLI manualmente para cada fonte a cada atualização legislativa |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `TCUScraper` baixa uma Resolução TCU real em PDF e extrai o texto via `subprocess` chamando `pdftotext -layout` (binário de sistema, não pip) |
| **MUST** | Novo parser estrutura o texto extraído em `Artigo`/`Paragrafo`/`Inciso` (classes já existentes em `ingestion/parser/ast_models.py`, reaproveitadas sem modificação), removendo cabeçalho/rodapé repetido do PDF |
| **MUST** | Chunks gerados a partir do TCU passam pelo `ingestion/chunking/chunker.py` já existente sem nenhuma modificação nele |
| **MUST** | `dags/ingestao_legal_dag.py` escrito com sintaxe real da API do Airflow (TaskFlow API, `@dag`/`@task`), orquestrando Planalto + TCU, documentado explicitamente como não executável neste sandbox (mesmo tratamento já aceito para `orquestracao/grafo.py`/LangGraph) |
| **SHOULD** | Testes automatizados (pytest, mesmo padrão de `tests/`) cobrindo `TCUScraper` e o novo parser contra o PDF real já baixado nesta sessão |
| **COULD** | Estrutura de projeto para múltiplas DAGs (`dags/`) já prevista para acomodar as 7 fontes restantes em ciclos futuros, sem forçar abstração prematura agora |

---

## Success Criteria

- [ ] `TCUScraper` baixa uma Resolução TCU real (PDF) e extrai texto via `pdftotext -layout`, validado por teste automatizado contra o arquivo — **nota do Design**: o PDF de exemplo citado no brainstorm não está mais disponível neste ambiente; o Build precisa baixar uma Resolução real do zero antes de escrever os testes
- [ ] 100% dos artigos/parágrafos/incisos identificáveis no PDF de teste são estruturados corretamente pelo novo parser, sem achatar a hierarquia
- [ ] Chunks do TCU indexados pelo `chunker.py` existente contêm os mesmos campos obrigatórios (`texto`, `parent_texto`) já validados para o Planalto
- [ ] `dags/ingestao_legal_dag.py` existe com sintaxe válida da TaskFlow API do Airflow (revisão de código confirma `@dag`/`@task` corretos), com nota explícita de que não é executável neste sandbox (`apache-airflow` não instala — confirmado via `pip3 install --dry-run`)

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path | O PDF real `resolucao-tcu-n389-de-24-junho-2026.pdf` já baixado | `TCUScraper` + novo parser processam o arquivo | Chunks corretos são gerados, com hierarquia Artigo/Parágrafo/Inciso preservada e metadados de origem (`documento_id`, URL do TCU) presentes |
| AT-002 | Error case | Um PDF corrompido ou sem texto extraível via `pdftotext` | O scraper tenta processá-lo | O pipeline registra o erro em log, sem quebrar silenciosamente nem indexar chunk vazio/corrompido |
| AT-003 | Edge case | Resolução com parágrafo único (sem numeração de §) | O parser processa o texto | A estrutura é reconhecida corretamente, sem confundir com "sem parágrafos" |

---

## Out of Scope

- DOU e as demais 6 fontes ainda não iniciadas (RFB/COSIT, Siscomex/TIPI, CONFAZ, SPED, NF-e/NFS-e, jurisprudência STF/STJ/CARF) — DOU especificamente rejeitado nesta sessão por ser SPA sem API descoberta (exigiria Playwright, também bloqueado neste sandbox)
- Parser para o PDF de Metodologia do TCU (documento técnico, estrutura genuinamente diferente de Lei/Resolução — forçá-lo no mesmo parser seria gambiarra)
- Popular `motor_calculo/tabela_aliquotas.py` (`TabelaAliquotasSeed`) com qualquer dado do TCU — nenhum PDF real baixado confirma uma alíquota numérica para 2027+; a Resolução é procedural e a Metodologia exclui o valor final explicitamente
- Execução real da DAG em Cloud Composer — provisionar e rodar o ambiente Composer é um passo de infraestrutura separado (pago), fora deste ciclo de código
- Autenticação, multi-tenancy, billing (já fora de escopo desde a feature de ingestão original)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `apache-airflow` não instala neste sandbox (`externally-managed-environment`, mesmo bloqueio de `langgraph`/`qdrant-client`/`fastembed`) | DAG escrita com sintaxe real, mas não executável/testável neste ambiente — só validável por revisão de código até haver um Cloud Composer real |
| Technical | Bibliotecas Python de PDF (`pypdf`, `pdfplumber`, `PyMuPDF`, `PyPDF2`) também não instalam neste sandbox | Extração de texto via `pdftotext`/`pdftohtml` (poppler-utils, binário de sistema) em vez de biblioteca Python — já testado com sucesso nos PDFs reais do TCU |
| Scope | Só Resoluções TCU processadas nesta feature, não a Metodologia | Metodologia é estrutura de documento técnico genuinamente diferente; parser genérico demais seria prematuro (YAGNI) |
| Data | Nenhum PDF do TCU baixado confirma alíquota numérica para 2027+ | Esta feature não pode e não deve alimentar `TabelaAliquotasSeed` — evita popular o motor de cálculo com dado inventado |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Novo `ingestion/scraper/tcu_scraper.py` + novo parser (`ingestion/parser/` — reaproveitando `ast_models.py`); novo diretório `dags/` na raiz do repo para `ingestao_legal_dag.py` | Extensão de `ingestion/` já existente + 1 componente novo (`dags/`) |
| **KB Domains** | python-developer, airflow-specialist | Consultar padrões TaskFlow API e estrutura de parser de PDF no Design |
| **IaC Impact** | Nenhum novo recurso Terraform nesta feature — Cloud Composer fica para quando a DAG for de fato implantada/executada | `infra/terraform/` já provisiona o bucket GCS usado; Composer é decisão de infraestrutura separada e futura |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| TCU — Resoluções (PDF público) | PDF público, extraído via `pdftotext -layout` | 1 Resolução real de teste neste ciclo (`resolucao-tcu-n389-de-24-junho-2026.pdf`) | Sob demanda/batch, sem SLA de tempo real | Fonte pública (sem dono interno) |

### Schema Contract
Reaproveita integralmente o schema de `Chunk` já validado na feature `PIPELINE_INGESTAO_LEGAL` (`ingestion/chunking/chunk_models.py`) — nenhum campo novo introduzido. Sem PII em nenhum campo.

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| Raw / Staging (GCS) | Sob demanda — sem SLA de tempo real neste ciclo | Timestamp de execução do scraper |
| Índice Qdrant | Atualizado a cada execução completa (batch), mesmo padrão do Planalto | Timestamp de indexação por chunk |

### Completeness Metrics
- 100% dos artigos/parágrafos/incisos da Resolução de teste devem gerar ao menos 1 chunk indexado
- Zero chunks sem metadados obrigatórios de origem (`documento_id`, URL do TCU)

### Lineage Requirements
- Cada chunk do TCU deve referenciar a URL/identificador da Resolução de origem, mesmo padrão de auditabilidade já usado para o Planalto

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `pdftotext`/`pdftohtml` (poppler-utils) estarão disponíveis em qualquer ambiente onde o scraper rodar de verdade (Cloud Composer/Cloud Run), não só neste sandbox | Precisaria adicionar poppler-utils como dependência de sistema explícita na imagem de container | [ ] |
| A-002 | O TCU mantém o formato de Resolução (Art./Parágrafo/Inciso) consistente entre publicações futuras | Parser quebraria silenciosamente ou exigiria manutenção a cada mudança de formato do TCU | [ ] |
| A-003 | Um Cloud Composer real será provisionado em ciclo futuro para executar a DAG escrita nesta feature | Até lá, a DAG permanece código revisável mas nunca executado de fato — mesmo tratamento aceito para `orquestracao/grafo.py` | [ ] |

**Note:** A-001 e A-002 só são validáveis fora deste sandbox — registradas aqui para revisão quando a feature for promovida a produção.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro e específico — herda diretamente da lacuna identificada na auditoria de estado do projeto |
| Users | 3 | Dois consumidores internos identificados com pain points diretamente ligados às lacunas apontadas |
| Goals | 3 | MUST/SHOULD/COULD explícitos, herdados das decisões já validadas no brainstorm |
| Success | 2 | Critérios majoritariamente testáveis automaticamente, exceto a validação da sintaxe da DAG (revisão de código, não execução — limitação reconhecida, não falha de clareza) |
| Scope | 3 | Out of scope extremamente explícito, incluindo a rejeição justificada de DOU e da Metodologia TCU |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

- Nenhuma pendente para o Design — todas as decisões relevantes (TCU vs. DOU, escopo de Resoluções vs. Metodologia, DAG escrita-mas-não-executável) já foram validadas explicitamente no brainstorm.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | define-agent | Versão inicial, extraída de `BRAINSTORM_INGESTAO_TCU_E_ETL_AIRFLOW.md` |
| 1.1 | 2026-07-24 | ship-agent | Shipped e arquivado — ver `SHIPPED_2026-07-24.md` |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md`
