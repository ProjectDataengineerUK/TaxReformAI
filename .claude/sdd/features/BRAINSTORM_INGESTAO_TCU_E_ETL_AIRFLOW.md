# BRAINSTORM: Segunda Fonte de Ingestão (TCU) + Camada ETL Real (Airflow)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_TCU_E_ETL_AIRFLOW |
| **Date** | 2026-07-24 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Depois da auditoria de estado do projeto (`taxreform-ai-recap.html`), o usuário apontou as duas lacunas mais sérias identificadas: (1) só 1 das 9 fontes legais mapeadas foi ingerida (Planalto) e (2) não existe camada ETL real — `ingestion/pipeline.py` é uma CLI manual, não uma DAG do Airflow/Cloud Composer como o blueprint pede (seção 4.2/5.2).

**Context Gathered:**
- `apache-airflow` bate no mesmo bloqueio de instalação (`externally-managed-environment`) já visto com `langgraph`/`qdrant-client`/`fastembed`/`google-cloud-storage` — confirmado via `pip3 install --dry-run apache-airflow`.
- DOU (candidato inicial para segunda fonte) é um portal moderno renderizado via JavaScript (SPA) — nenhuma API JSON encontrada via `curl` simples na página de consulta (`in.gov.br/consulta`). Confirma por que o blueprint já previa Playwright (não HTTP simples) para esse tipo de fonte — mas Playwright também bateria no mesmo bloqueio de instalação.
- TCU já tem PDFs reais baixados nesta sessão (da pesquisa da feature `MOTOR_DETERMINISTICO_CALCULO`): `resolucao-tcu-n389-de-24-junho-2026.pdf` e `Metodologia CBS Aliquota de Referencia e Redutor.pdf`.
- `pypdf`/`pdfplumber`/`PyMuPDF`/`PyPDF2` não instalam neste sandbox (mesmo bloqueio). **Mas `pdftotext`/`pdftohtml` (poppler-utils) já estão instalados como binários de sistema** — não passam pela restrição do pip. Testado com sucesso via `pdftotext -layout` nos dois PDFs reais do TCU.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Novo `ingestion/scraper/tcu_scraper.py` + novo parser para texto de PDF; `dags/` na raiz para o Airflow | Extensão de `ingestion/`, mais um componente novo (`dags/`) |
| Relevant KB Domains | python-developer, airflow-specialist | Padrões a consultar no /design |
| IaC Impact | Nenhum novo — Airflow real ficaria não executável neste sandbox, mesmo padrão do `langgraph` | |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | DOU ou TCU como segunda fonte de ingestão? | TCU — DOU é uma SPA sem API descoberta; TCU já tem PDFs reais comprovadamente baixáveis nesta sessão | Escopo migra de "replicar o parser HTML" para "construir um parser de texto de PDF" |
| 2 | Dado que nenhum PDF do TCU baixado tem uma alíquota numérica confirmada (a resolução é procedural; a metodologia explicitamente exclui o valor final — ver seção 6 desta pesquisa), o que a ingestão do TCU realmente destrava? | Alimenta o RAG/Pesquisador Legal com a metodologia oficial (para o Sintetizador poder citar "como" a alíquota é calculada) — **não** desbloqueia novos anos em `TabelaAliquotasSeed`, que continua correta em só ter 2026 | Evita a falsa impressão de que esta feature resolve o motor de cálculo para 2027+ |
| 3 | Resoluções TCU (Art./Parágrafo/Inciso) e o PDF de Metodologia (parágrafos numerados + apêndices) têm estruturas diferentes — ambos entram neste ciclo? | Só as Resoluções — a Metodologia é uma estrutura de documento técnico genuinamente diferente (não é "lei"), forçar isso no mesmo parser seria gambiarra | Chunker/parser reaproveitam `Artigo`/`Paragrafo`/`Inciso` já existentes; Metodologia fica para um parser futuro dedicado |
| 4 | O DAG do Airflow deve ser só desenhado/escrito ou também executado? | Escrito com a API real (TaskFlow API `@dag`/`@task`), mas **não executável neste sandbox** — mesmo padrão já aceito para `orquestracao/grafo.py` (LangGraph) | Consistente com o precedente já estabelecido nas features anteriores |

**Minimum Questions:** 3 ✅ (4 perguntas, todas com pesquisa real por trás)

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `resolucao-tcu-n389-de-24-junho-2026.pdf` (real, já baixado) | 1 | Usado como fixture de teste real, convertido via `pdftotext -layout` |
| Related code | `ingestion/parser/ast_models.py` (`Artigo`, `Paragrafo`, `Inciso`, `Lei.artigos_soltos`) | 4 classes | Reaproveitadas sem modificação — resoluções não têm Livro/Título/Capítulo |
| Related code | `ingestion/scraper/planalto_scraper.py` (`LegalSource` protocol) | 1 | Padrão de implementação para `TCUScraper` |

**Como as fontes serão usadas:**

- O texto extraído via `pdftotext -layout` é processado por um novo parser, linha a linha, reaproveitando os mesmos regex de `Art\.`/`§`/inciso do `ast_parser.py` — mas com uma lógica de remoção de cabeçalho/rodapé repetido (que HTML não tinha) em vez do sinal `align="center"` usado para HTML

---

## Approaches Explored

### Approach A: TCU (resoluções) + DAG Airflow escrito mas não executável ⭐ Recomendada

**Description:** `TCUScraper` baixa a resolução em PDF e usa `subprocess` para chamar `pdftotext -layout`, convertendo o binário do sistema em texto puro. Um novo parser consome esse texto (reaproveitando `Artigo`/`Paragrafo`/`Inciso`, sem `Secao`) e alimenta o mesmo `chunker.py`/`Chunk` já existentes. Uma DAG real do Airflow (`dags/ingestao_legal_dag.py`) usa `@dag`/`@task` para orquestrar Planalto + TCU, mas fica marcada como não executável neste sandbox (mesmo tratamento do `langgraph`).

**Pros:**
- A parte de parsing de PDF é 100% real e testável (`pdftotext` não depende de pip)
- Prova a extensibilidade do `LegalSource` (2ª implementação real) sem forçar um parser genérico prematuro
- DAG real ainda é valiosa como código revisável, mesmo sem execução — mesmo padrão já aceito

**Cons:**
- A camada Airflow continua sendo "escrita, não verificada" — não resolve de fato a lacuna de execução real de ETL

**Why Recommended:** É a única abordagem que entrega pelo menos uma parte (o parser de PDF via TCU) com verificação real de ponta a ponta, em vez de acumular mais código nunca executado.

---

### Approach B: DOU como segunda fonte, aceitando que o scraper fique não testável

**Description:** Insistir em DOU, escrevendo um scraper best-effort sem confirmar a estrutura real (já que é uma SPA).

**Pros:**
- DOU é, em tese, a fonte mais valiosa (onde toda mudança legal nova é publicada primeiro)

**Cons:**
- Sem a API real descoberta, o scraper seria pura suposição — alto risco de código que nunca funcionaria mesmo com credenciais, diferente do padrão "não executado mas correto" já aceito para bibliotecas bloqueadas

---

### Approach C: Só a DAG do Airflow, sem nova fonte de dados

**Description:** Focar só em construir a camada ETL (DAG real envolvendo o Planalto já existente), sem adicionar TCU.

**Pros:**
- Menor escopo

**Cons:**
- Usuário apontou as duas lacunas juntas; deixar uma de fora não responde à pergunta original

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — TCU (resoluções) + DAG Airflow escrito mas não executável |
| **User Confirmation** | 2026-07-24 (usuário escolheu "tcu" após a comparação com DOU) |
| **Reasoning** | Única abordagem com uma parte totalmente verificável (parsing de PDF via `pdftotext`), evitando acumular mais código nunca executado |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | TCU em vez de DOU como segunda fonte | DOU é SPA sem API descoberta via `curl`; TCU já tem PDFs reais comprovadamente baixáveis | DOU — rejeitado, exigiria Playwright (também bloqueado) e suposições sem verificação |
| 2 | `pdftotext`/`pdftohtml` (binários de sistema, poppler-utils) em vez de biblioteca Python de PDF | `pypdf`/`pdfplumber`/`PyMuPDF` não instalam neste sandbox; binários de sistema não passam pela restrição do pip e já foram testados com sucesso nos PDFs reais | Bibliotecas Python de PDF — rejeitadas, mesmo bloqueio de `externally-managed-environment` |
| 3 | Só Resoluções TCU neste ciclo, não o PDF de Metodologia | Resoluções têm estrutura Art./Parágrafo/Inciso compatível com o parser já existente; Metodologia é um documento técnico com estrutura genuinamente diferente | Forçar a Metodologia no mesmo parser — rejeitado, seria gambiarra que quebraria na primeira mudança de formato |
| 4 | Ingestão do TCU não desbloqueia novos anos em `TabelaAliquotasSeed` | Nenhum PDF baixado tem uma alíquota numérica confirmada — a resolução é procedural, a metodologia exclui o valor final explicitamente | Popular `TabelaAliquotasSeed` com base nesta ingestão — rejeitado, inventaria dado legal que os documentos reais não confirmam |
| 5 | DAG do Airflow escrita com a API real (TaskFlow), mas não executável neste sandbox | `apache-airflow` bate no mesmo bloqueio de instalação já visto com `langgraph` | Esperar o Airflow instalar para escrever qualquer código — rejeitado, mesmo precedente já aceito nas features anteriores |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| DOU como fonte nesta feature | SPA sem API descoberta — exigiria Playwright (bloqueado) ou engenharia reversa sem ferramenta de inspeção de rede disponível | Sim, quando houver acesso a navegador real ou a API do portal for descoberta |
| Parser genérico para "qualquer documento legal" (leis + resoluções + metodologias) | Prematuro — só 2 estruturas reais foram vistas até agora (lei compilada, resolução); um parser genérico demais quebraria silenciosamente | Sim, conforme mais fontes forem adicionadas e os padrões comuns ficarem claros |
| Popular `TabelaAliquotasSeed` com dado do TCU | Nenhum documento real baixado confirma um número — inventaria dado legal | Sim, quando uma Resolução com o valor final for publicada e ingerida |
| Execução real da DAG do Airflow | `apache-airflow` não instala neste sandbox | Sim, em ambiente com controle do usuário |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| DOU vs. TCU como segunda fonte (com achado técnico do SPA) | ✅ | Usuário escolheu "tcu" | Sim — abordagem original (DOU) descartada |
| Escopo restrito a Resoluções (não Metodologia) + TCU não alimenta TabelaAliquotas | ✅ | Registrado nesta sessão, a confirmar no /define | Pendente |

**Minimum Validations:** 1 de 2 — segunda validação ocorre implicitamente ao prosseguir para `/define`

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O sistema precisa de uma segunda fonte de ingestão legal real (TCU, via PDFs de Resoluções) e de uma camada de orquestração ETL real (Airflow), provando que a arquitetura `LegalSource` já construída se estende a fontes em formato diferente (PDF, não HTML) e a um orquestrador real além da CLI manual atual.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Agente Pesquisador Legal (RAG) | Precisa citar documentos do TCU sobre a metodologia de alíquota de referência, hoje inexistentes na base indexada |
| Operador do pipeline | Precisa de uma DAG agendável em vez de rodar a CLI manualmente para cada fonte |

### Success Criteria (Draft)
- [ ] `TCUScraper` baixa uma Resolução TCU real e extrai o texto via `pdftotext -layout`
- [ ] Novo parser estrutura o texto em `Artigo`/`Paragrafo`/`Inciso` (reaproveitados), testado contra o PDF real já baixado
- [ ] Chunks gerados a partir do TCU passam pelo mesmo `chunker.py` sem modificação
- [ ] `dags/ingestao_legal_dag.py` existe com sintaxe real do Airflow (TaskFlow API), documentado como não executável neste sandbox

### Constraints Identified
- `apache-airflow` não instalável neste sandbox — DAG escrita mas não executada
- Só Resoluções TCU neste ciclo, não a Metodologia (estrutura diferente)
- Ingestão do TCU não popula `TabelaAliquotasSeed` — nenhum documento real confirma uma alíquota numérica para 2027+

### Out of Scope (Confirmed)
- DOU e as demais 6 fontes ainda não iniciadas (RFB/COSIT, Siscomex/TIPI, CONFAZ, SPED, NF-e/NFS-e, jurisprudência STF/STJ/CARF)
- Parser para o PDF de Metodologia (documento técnico, estrutura diferente)
- Popular `TabelaAliquotasSeed` com qualquer dado do TCU
- Execução real da DAG do Airflow

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 1 de 2 |
| Duration | 1 sessão de diálogo, incluindo pesquisa técnica real (DOU, poppler-utils) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_INGESTAO_TCU_E_ETL_AIRFLOW.md`
