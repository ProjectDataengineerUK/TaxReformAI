# DEFINE: Pipeline de Ingestão Legal (ETL + AST + RAG Híbrido)

> Raspar, estruturar em árvore AST e indexar via embedding híbrido a legislação tributária brasileira — começando pelo Planalto — para alimentar o RAG dos agentes do TaxReform AI.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PIPELINE_INGESTAO_LEGAL |
| **Date** | 2026-07-22 |
| **Author** | define-agent |
| **Status** | ✅ Shipped (2026-07-24) |
| **Clarity Score** | 13/15 |

---

## Problem Statement

Os agentes do TaxReform AI (Pesquisador Legal e Extrator de Regras) não têm hoje nenhuma base legal estruturada e indexada para consultar — sem um pipeline que transforme o texto bruto da legislação em chunks hierárquicos com metadados de vigência, é impossível fazer RAG confiável ou gerar pareceres auditáveis com citação de fonte.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Agente Pesquisador Legal (RAG) | Consumidor interno do sistema multi-agente | Precisa recuperar dispositivos legais válidos para a data da operação, com metadados de vigência confiáveis — hoje não existe nenhuma base indexada para buscar |
| Agente Extrator de Regras | Consumidor interno do sistema multi-agente | Precisa de chunks bem estruturados (artigo/parágrafo/inciso) para montar payloads JSON estritos — texto legal não-estruturado quebra a extração determinística |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Scraper funcional para o Planalto (legislação compilada) capaz de baixar o texto de uma Lei Complementar específica |
| **MUST** | Parser AST hierárquico que estrutura o texto em `Lei → Título → Capítulo → Artigo → Parágrafo → Inciso` |
| **MUST** | Indexação híbrida (embedding denso BGE-M3 + esparso BM25) dos chunks no Qdrant, com metadados de vigência conforme schema da seção 4.3 do blueprint |
| **SHOULD** | Armazenamento do HTML/texto bruto original no GCS (raw storage) antes do parsing, para auditabilidade |
| **SHOULD** | Orquestração do pipeline via Airflow DAG (pode ser simplificado/local no MVP, sem exigir Cloud Composer provisionado) |
| **COULD** | Suporte a atualização incremental (detectar mudanças em lei já indexada) em vez de reindexação completa |

---

## Success Criteria

- [ ] Estrutura AST completa (`Lei → Título → Capítulo → Artigo → Parágrafo → Inciso`) extraída corretamente para 100% dos artigos de 1 Lei Complementar de teste do Planalto
- [ ] 100% dos chunks gerados contêm os metadados obrigatórios do schema da seção 4.3 (`documento_id`, `dispositivo`, `esfera`, `data_vigencia_inicio`, `data_vigencia_fim`)
- [ ] Busca híbrida no Qdrant retorna o dispositivo legal correto entre os top-3 resultados para pelo menos 5 perguntas de teste conhecidas

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path | Uma Lei Complementar publicada no Planalto em HTML | O pipeline executa scraping + parsing AST + indexação | Os chunks aparecem no Qdrant com todos os metadados obrigatórios corretos |
| AT-002 | Error case | Uma página do Planalto fora do ar ou com HTML fora do padrão esperado | O scraper tenta processá-la | O pipeline registra o erro em log, sem quebrar silenciosamente e sem indexar dados corrompidos |
| AT-003 | Edge case | Um artigo com estrutura aninhada complexa (parágrafo único, incisos com alíneas) | O parser AST processa o texto | A hierarquia é preservada corretamente nos metadados do chunk (não achata a estrutura) |

---

## Out of Scope

- As outras 7 fontes mapeadas no brainstorm (DOU, RFB/COSIT, Siscomex/TIPI, CONFAZ, SPED, NF-e/NFS-e, jurisprudência STF/STJ/CARF) — documentadas, mas não implementadas neste ciclo
- Parser específico de jurisprudência (estrutura de acórdão/ementa, distinta da árvore legislativa Lei→Artigo→Inciso)
- Motor determinístico de cálculo, API FastAPI, orquestração multi-agente (LangGraph/CrewAI), frontend — ficam para ciclos posteriores
- Atualização incremental automática / detecção contínua de mudanças legislativas (marcada como COULD, não MVP)
- Autenticação, multi-tenancy, billing

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Sem dados de exemplo pré-existentes — tudo vem de scraping ao vivo do Planalto | O pipeline deve lidar com HTML real desde o primeiro teste, sem fixtures sintéticas |
| Resource | Execução solo (Claude Code), sem paralelização de frentes | Sequenciamento deve ser estritamente incremental — uma fonte/camada por vez |
| Timeline | Sem prazo definido | Permite abordagem rigorosa (parser validado) em vez de atalhos de demo |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `ingestion/` na raiz do repositório (scraper, parser AST, indexador) | Repositório ainda sem código-fonte; esta é a primeira pasta de código do projeto |
| **KB Domains** | data-engineering (ETL/Airflow), ai-data-engineer (RAG/embeddings híbridos), qdrant-specialist | Padrões a consultar na fase de Design |
| **IaC Impact** | New resources — coleção Qdrant, bucket GCS (raw storage), possivelmente schema Postgres (cache de metadados) | Nenhuma infraestrutura provisionada ainda; Design precisa decidir local/dev vs. GCP real para o MVP |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| Planalto — Legislação Compilada (planalto.gov.br/legislacao) | HTML público | Centenas de leis relevantes ao IVA Dual; 1 lei de teste neste ciclo | Sem SLA — execução sob demanda/batch | Fonte pública (sem dono interno) |

### Schema Contract
| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| documento_id | VARCHAR | NOT NULL | No |
| dispositivo | VARCHAR | NOT NULL | No |
| esfera | VARCHAR | NOT NULL | No |
| data_vigencia_inicio | DATE | NOT NULL | No |
| data_vigencia_fim | DATE | NULL (vigência pode estar em aberto) | No |
| ncm_relacionadas | ARRAY\<VARCHAR\> | NULL | No |
| regime | VARCHAR | NULL | No |

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| Raw / Staging (GCS) | Sob demanda — sem SLA de tempo real neste ciclo | Timestamp de execução do scraper |
| Índice Qdrant | Atualizado a cada execução completa do pipeline (batch) | Timestamp de indexação por chunk |

### Completeness Metrics
- 100% dos artigos da lei de teste devem gerar ao menos 1 chunk indexado
- Zero chunks sem os metadados obrigatórios do schema AST

### Lineage Requirements
- Cada chunk deve referenciar o `documento_id` de origem e a URL do Planalto de onde foi extraído, para auditabilidade

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O Planalto mantém a legislação compilada em HTML parseável de forma consistente (sem exigir OCR) | Seria necessário adicionar parsing de PDF/OCR, aumentando o escopo | [ ] |
| A-002 | Existe pelo menos uma Lei Complementar do IVA Dual já publicada e disponível no Planalto para uso como caso de teste | Sem material real para validar o pipeline neste ciclo | [ ] |
| A-003 | Qdrant (Cloud ou instância local/dev) está disponível para uso durante o desenvolvimento | Seria necessário rodar Qdrant localmente via Docker para o MVP | [ ] |

**Note:** Validar A-001 e A-002 no início do Design/Build — determinam se o parser precisa lidar com PDF desde o início.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro, específico — falta de base legal indexada bloqueia RAG e extração de regras |
| Users | 2 | Dois consumidores internos bem identificados, mas são agentes do sistema, não personas humanas com pain points diretamente observados |
| Goals | 3 | MUST/SHOULD/COULD explícitos e específicos, herdados diretamente das decisões do brainstorm |
| Success | 2 | Critérios mensuráveis definidos, mas alguns números (ex: "5 perguntas de teste") são estimativas razoáveis, não SLAs formais |
| Scope | 3 | Out of scope extremamente explícito, incluindo as 7 fontes deferidas e os componentes de ciclos futuros |
| **Total** | **13/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

- Qual Lei Complementar específica usar como caso de teste (ex: a LC do IVA Dual mais recente)? A decidir no início do Design/Build, validando a Assumption A-002.
- O MVP deve rodar Qdrant e GCS localmente (Docker/emulador) ou já contra a infraestrutura GCP real? A decidir no Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-22 | define-agent | Versão inicial, extraída de BRAINSTORM_PIPELINE_INGESTAO_LEGAL.md |
| 1.1 | 2026-07-24 | ship-agent | Shipped e arquivado (com 2 dias de atraso — credenciais GCP/Qdrant resolvidas em 2026-07-24) — ver `SHIPPED_2026-07-24.md` |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_PIPELINE_INGESTAO_LEGAL.md`
