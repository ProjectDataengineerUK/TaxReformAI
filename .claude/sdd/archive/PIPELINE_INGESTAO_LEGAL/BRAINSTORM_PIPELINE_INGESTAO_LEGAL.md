# BRAINSTORM: Pipeline de Ingestão Legal (ETL + AST + RAG Híbrido)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PIPELINE_INGESTAO_LEGAL |
| **Date** | 2026-07-22 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Construir o TaxReform AI por completo, sem pressa de prazo, começando do zero, com o próprio Claude Code implementando sozinho. Após explorar a sequência de construção, o usuário escolheu atacar primeiro o componente de maior incerteza técnica — o pipeline de ingestão de dados legais (ETL) e o RAG híbrido — e forneceu o mapeamento completo das 8 fontes públicas reais a serem usadas.

**Context Gathered:**
- Repositório contém apenas `contexto.md` (blueprint completo do produto/arquitetura) e `CLAUDE.md` (gerado via `/start`); nenhum código implementado ainda.
- O blueprint já especifica a arquitetura de chunking hierárquico AST (seção 4.3: `Lei → Título → Capítulo → Artigo → Parágrafo → Inciso`) e o pipeline ETL (seção 4.2: `[DOU/RFB/Comitê IBS] → Scrapy/Playwright (Airflow DAGs) → GCS Raw Storage → Parsing AST → Hybrid Embedding (BGE-M3 + BM25) → Qdrant + PostgreSQL`).
- Stack planejada documentada em `CLAUDE.md`: Airflow (Cloud Composer) para orquestração, GCS para raw storage, Qdrant Cloud para busca híbrida, PostgreSQL 16 para metadados relacionais.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Repositório de código ainda vazio — sugerir criar `ingestion/` ou `pipeline/` na raiz | Onde o scraper, parser AST e indexador devem viver |
| Relevant KB Domains | data-engineering (ETL/Airflow), ai-data-engineer (RAG/embeddings híbridos), qdrant-specialist | Padrões a consultar na fase de design |
| IaC Patterns | N/A ainda — infraestrutura GCP (Cloud Composer, GCS, Cloud SQL, Qdrant Cloud) descrita no blueprint mas não provisionada | Precisa decidir Terraform vs. provisionamento manual para o MVP |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual resultado deve ser priorizado primeiro no MVP (simulação via API, parecer com RAG completo, ou upload em lote)? | Usuário optou por não escolher um resultado de produto e sim sequenciar por risco técnico — o pipeline de ingestão/RAG é o primeiro componente a construir, antes de qualquer produto-fim. | Define o escopo desta feature: não é um produto-fim, é infraestrutura de dados que os demais componentes vão consumir. |
| 2 | Qual o prazo/urgência do build? | Build completa, sem pressa de prazo. | Permite abordagem rigorosa (um parser AST validado por fonte) em vez de atalhos de demo. |
| 3 | Há dados reais/amostras disponíveis para grounding? | Inicialmente "partimos do zero sem nenhum dado de exemplo"; em seguida o usuário forneceu a lista completa de 8 fontes públicas reais (DOU, Normas RFB, Planalto, Siscomex/TIPI, CONFAZ, SPED, NF-e/NFS-e, Jurisprudência STF/STJ/CARF). | Muda a avaliação de risco da abordagem "ETL/RAG primeiro" de alto risco (sem nada pra validar) para risco administrável (fontes reais mapeadas, ainda que não baixadas). |
| 4 | Quem executa a implementação — só o Claude Code ou há times em paralelo? | Só o Claude Code, sozinho, sem paralelização de frentes. | Sequenciamento deve ser estritamente incremental — uma fonte/camada de cada vez, não várias frentes simultâneas. |

**Minimum Questions:** 3 ✅ (4 perguntas formais, mais validações incrementais)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | Nenhum arquivo baixado ainda — apenas URLs das fontes mapeadas (ver Data Engineering Context) | 0 | Ingestão será feita via scraping ao vivo das fontes públicas listadas abaixo |
| Output examples | Exemplo de chunk estruturado no blueprint (seção 4.3, JSON de metadados) | 1 | Usado como referência de schema alvo para o parser AST |
| Ground truth | N/A | 0 | Nenhuma validação de acurácia de extração legal definida ainda |
| Related code | N/A | 0 | Repositório sem código-fonte até o momento |

**Como as fontes serão usadas:**

- Fonte de conteúdo bruto para o pipeline de scraping (Scrapy/Playwright via Airflow DAGs)
- Insumo para o parser AST hierárquico (`Lei → Título → Capítulo → Artigo → Parágrafo → Inciso`)
- Base para os embeddings híbridos (denso BGE-M3 + esparso BM25) indexados no Qdrant

---

## Approaches Explored

### Approach A: Bottom-up por camada

**Description:** Motor determinístico → schema Postgres → API skeleton → pipeline ETL → orquestração multi-agente → frontend. Cada camada é finalizada e testada isoladamente antes de avançar para a próxima.

**Pros:**
- Cada componente é validado com rigor técnico antes de integrar
- Reduz retrabalho de integração

**Cons:**
- Nenhuma demo end-to-end até muito tarde no processo
- Risco de over-engineering em camadas isoladas sem feedback do sistema completo

---

### Approach B: Walking skeleton (vertical fina)

**Description:** Construir um caminho fino atravessando todas as camadas desde o início (endpoint `/v1/tax/simulate` real, motor de cálculo real, mas regras tributárias hardcoded/seed para 1-2 NCMs), depois aprofundar camada por camada substituindo partes "fake" por reais.

**Pros:**
- Sistema demonstrável ponta-a-ponta em dias, não semanas
- Cada camada subsequente troca uma peça fake por uma real sem redesenhar a integração

**Cons:**
- Exige dados hardcoded que precisam ser descartados/substituídos depois
- Adia a parte de maior incerteza técnica (ingestão de fontes públicas heterogêneas) para depois

---

### Approach C: Risco primeiro (ETL/RAG) ⭐ Escolhida

**Description:** Atacar primeiro o pipeline de ingestão legal e o RAG híbrido — por ser a parte de maior incerteza técnica (scraping de fontes gov.br heterogêneas, chunking AST, qualidade de embeddings) — antes do motor determinístico e da API.

**Pros:**
- Prova a parte mais incerta do sistema primeiro, quando ainda há tempo/flexibilidade para pivotar
- Com fontes reais mapeadas (ao contrário da avaliação inicial), há material concreto para validar contra
- Gera o ativo de dados (base legal indexada) que todos os outros componentes (motor, API, agentes) vão eventualmente consumir

**Cons:**
- Sem demo de produto-fim até essa camada estar madura
- 8 fontes com formatos heterogêneos (HTML compilado, PDF, bases de busca de jurisprudência, XML de schemas) exigem parsers distintos — não dá para tratar como uma tarefa única

**Why Recommended:** A avaliação de risco mudou depois que o usuário forneceu as 8 fontes reais — sem elas, C teria sido descartada por falta de material para validar. Com elas, atacar a parte de maior incerteza primeiro (em vez de adiá-la, como em A e B) é a escolha mais alinhada com "build completa sem pressa de prazo": há tempo para fazer essa camada corretamente antes de depender dela.

---

## Data Engineering Context

### Source Systems

| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| DOU — Diário Oficial da União (in.gov.br) | Portal governamental, publicação diária (PDF/HTML) | Milhares de atos/ano | Diária |
| Soluções de Consulta COSIT/DISIT & Normas RFB (normas.receita.fazenda.gov.br) | Portal de busca / HTML | Milhares de soluções acumuladas | Atualização contínua |
| Legislação Compilada — Presidência da República (planalto.gov.br/legislacao) | HTML de texto legal compilado | Centenas de leis/complementares relevantes ao IVA Dual | Atualizada por alteração legislativa |
| Portal Único Siscomex & Nomenclaturas (gov.br/siscomex) | Tabelas estruturadas (NCM/NBS) | ~10.000+ códigos NCM | Atualização esporádica |
| Tabela TIPI/NCM (Orientação Tributária RFB) | Tabela estruturada | Alinhada ao Siscomex | Atualização esporádica |
| CONFAZ — Conselho Nacional de Política Fazendária (confaz.fazenda.gov.br) | Portal de convênios/atos estaduais | Dezenas de convênios/ano | Atualização contínua |
| Página informativa CONFAZ (gov.br/pgfn) | Portal informativo | N/A | Atualização contínua |
| Portal do SPED — EFD-ICMS/IPI, EFD-Contribuições (sped.rfb.gov.br) | Documentação técnica de schemas | Poucas atualizações/ano | Baixa frequência |
| Portal Nacional da NF-e (nfe.fazenda.gov.br) | Notas técnicas e schemas XML | Dezenas de notas técnicas | Por versão de schema |
| Portal Nacional da NFS-e (nfse.gov.br/EmissorNacional) | Notas técnicas e schemas XML | Dezenas de notas técnicas | Por versão de schema |
| STF — Jurisprudência & Repercussão Geral (jurisprudencia.stf.jus.br) | Base de busca de acórdãos | Milhares de decisões | Atualização contínua, alto volume |
| STJ — Súmulas & Recursos Repetitivos (scon.stj.jus.br) | Base de busca de acórdãos/súmulas | Milhares de decisões | Atualização contínua, alto volume |
| CARF — Conselho Administrativo de Recursos Fiscais (gov.br/carf) | Base de busca de acórdãos | Milhares de decisões | Atualização contínua, alto volume |

### Data Flow Sketch
```text
[DOU / RFB / Planalto / Siscomex / CONFAZ / SPED / NFe / Jurisprudência]
        → (Scrapy / Playwright via Airflow DAGs)
        → Raw Storage (GCS)
        → Parsing AST Legal & Chunking Hierárquico
        → Hybrid Embedding (BGE-M3 denso + BM25 esparso)
        → Qdrant (vetorial) + PostgreSQL (metadados/cache)
```

### Key Data Questions Explored

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual o volume esperado por fonte? | Varia de dezenas (CONFAZ) a milhares (jurisprudência STF/STJ/CARF) de documentos | Reforça a decisão de priorizar a fonte estruturalmente mais simples primeiro |
| 2 | Qual freshness SLA é necessário? | Não definido ainda — a decidir na fase `/define` | Afeta se o DAG roda em batch diário ou sob demanda |
| 3 | Quem consome a saída? | Os 5 agentes especialistas do blueprint (Classificador, Pesquisador Legal, Extrator, Determinístico, Sintetizador), via RAG híbrido no Qdrant | Modelagem de metadados deve seguir o schema AST já definido na seção 4.3 do blueprint |

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach C — Risco primeiro (ETL/RAG) |
| **User Confirmation** | 2026-07-22 |
| **Reasoning** | Fontes reais mapeadas eliminam o risco de "sem dado pra validar"; ataca a parte de maior incerteza técnica primeiro, aproveitando a folga de prazo. |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Sequenciar o build por risco técnico (C), em vez de bottom-up (A) ou walking skeleton fino (B) | Fontes reais existem; adiar motor determinístico/API é aceitável dado "sem pressa de prazo" | B foi descartada por exigir dados hardcoded que seriam descartados depois |
| 2 | Priorizar uma única fonte (Planalto — legislação compilada) como primeiro alvo de implementação do pipeline | Bate 1:1 com a árvore AST do blueprint (seção 4.3); é HTML estruturado, não PDF escaneado nem base de busca de jurisprudência | Começar pela jurisprudência (STF/STJ/CARF) foi descartado — alto volume, mas estrutura de acórdão exige um segundo parser AST diferente |
| 3 | Registrar as 8 fontes completas no brainstorm desde já, mesmo que a implementação comece por apenas uma | Usuário pediu explicitamente para não perder o mapeamento já levantado | Documentar só a fonte inicial foi descartado — perderia contexto valioso para as fases seguintes |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Ingestão simultânea das 8 fontes no primeiro ciclo | Formatos heterogêneos (HTML, PDF, XML, bases de busca) tornariam o primeiro ciclo grande demais para validar corretamente | Yes — cada fonte entra como uma extensão incremental do mesmo pipeline |
| Parser AST único e genérico para todas as fontes | Jurisprudência (STF/STJ/CARF) tem estrutura de acórdão/ementa, distinta da árvore Lei→Artigo→Inciso da legislação compilada | Yes — parser específico de jurisprudência fica para uma fase posterior |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Sequenciamento (A/B/C) | ✅ | Usuário rejeitou a recomendação inicial (B) após fornecer fontes reais, e escolheu C | Yes — recomendação mudou de B para C |
| Fonte inicial única (Planalto) vs. todas simultâneas | ✅ | Usuário não contestou a priorização, mas pediu para registrar todas as fontes no documento | No — priorização mantida, apenas documentação ampliada |

**Minimum Validations:** 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Construir um pipeline que raspa, estrutura em árvore AST e indexa via embedding híbrido a legislação tributária brasileira relevante à Reforma Tributária — começando pelo Planalto — para alimentar o RAG híbrido dos agentes do TaxReform AI.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Agente Pesquisador Legal (RAG) | Precisa recuperar dispositivos legais válidos para a data da operação, com metadados de vigência confiáveis |
| Agente Extrator de Regras | Precisa de chunks bem estruturados (artigo/parágrafo/inciso) para montar payloads JSON estritos |

### Success Criteria (Draft)
- [ ] Pipeline consegue raspar e parsear ao menos 1 Lei Complementar do Planalto em estrutura AST completa (`Lei → Título → Capítulo → Artigo → Parágrafo → Inciso`)
- [ ] Chunks resultantes são indexados no Qdrant com metadados de vigência (`data_vigencia_inicio`/`fim`, `ncm_relacionadas`, `esfera`) conforme schema da seção 4.3 do blueprint
- [ ] Uma busca híbrida (densa + esparsa) retorna o dispositivo legal correto para uma pergunta de teste conhecida

### Constraints Identified
- Sem dados de exemplo pré-existentes — tudo vem de scraping ao vivo das fontes públicas listadas
- Execução solo (Claude Code), sem paralelização de frentes
- Sem prazo definido, mas sequenciamento deve ser estritamente incremental (uma fonte/camada por vez)

### Out of Scope (Confirmed)
- As outras 7 fontes (DOU, RFB/COSIT, Siscomex/TIPI, CONFAZ, SPED, NF-e/NFS-e, jurisprudência STF/STJ/CARF) — mapeadas neste documento, mas não implementadas neste primeiro ciclo
- Motor determinístico, API, orquestração multi-agente e frontend — ficam para ciclos posteriores, após o pipeline de ingestão estar validado

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 2 |
| Duration | 1 sessão de diálogo |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_PIPELINE_INGESTAO_LEGAL.md`
