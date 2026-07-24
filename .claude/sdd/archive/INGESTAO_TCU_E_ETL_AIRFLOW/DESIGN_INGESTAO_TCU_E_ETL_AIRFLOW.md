# DESIGN: Segunda Fonte de Ingestão (TCU) + Camada ETL Real (Airflow)

> Technical design para adicionar o TCU (Resoluções em PDF) como segunda implementação de `LegalSource` e para escrever a DAG do Airflow/Cloud Composer que substitui `pipeline.py` como orquestrador oficial.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_TCU_E_ETL_AIRFLOW |
| **Date** | 2026-07-24 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md](./DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md) |
| **Status** | ✅ Shipped (2026-07-24) |

---

## Correção de Premissa (achado do Design)

O BRAINSTORM/DEFINE presumem que o PDF `resolucao-tcu-n389-de-24-junho-2026.pdf` já está disponível localmente ("baixado nesta sessão"). Verificação neste Design (`find` no repo e no sandbox atual) não encontrou esse arquivo — ele existiu numa sessão anterior cujo scratchpad já não está acessível. **O Build precisa baixar uma Resolução TCU real de novo** (`https://pesquisa.apps.tcu.gov.br/` ou portal de atos normativos do TCU) antes de escrever qualquer teste contra ela. Isso não muda a arquitetura, mas é a primeira tarefa do File Manifest (item 1) e deve rodar antes dos itens que dependem da fixture.

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│         INGESTÃO MULTI-FONTE + ETL REAL (Planalto + TCU via Airflow)      │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Planalto HTML]                    [TCU Resolução PDF]                   │
│        │ PlanaltoScraper                   │ TCUScraper                  │
│        ▼                                    ▼                             │
│  [GCS raw/planalto/...]            [GCS raw/tcu/...]                      │
│        │ ast_parser.parse_lei()             │ resolucao_parser.parse_     │
│        │ (BeautifulSoup)                    │ resolucao() (texto puro)    │
│        ▼                                    ▼                             │
│  [Lei: secoes + artigos]           [Lei: só artigos_soltos]               │
│        └──────────────┬──────────────────────┘                           │
│                        ▼                                                  │
│              chunker.gerar_chunks()  ◄── SEM modificação                 │
│                        ▼                                                  │
│              [Chunks + Metadata] ──► embedder ──► Qdrant                 │
│                                                                             │
│  Orquestração:                                                            │
│  dags/ingestao_legal_dag.py (Airflow TaskFlow API)                       │
│    @task fetch_planalto >> @task fetch_tcu >> @task parse >> @task       │
│    chunk >> @task embed_index                                            │
│  ⚠ apache-airflow não instala neste sandbox — escrita, não executada    │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `TCUScraper` | Baixa o PDF de uma Resolução TCU e converte para texto | `httpx` (download) + `subprocess` chamando `pdftotext -layout` (binário de sistema) |
| Parser de Resolução TCU | Estrutura o texto extraído em `Lei` (só `artigos_soltos`, sem `secoes`) | Python puro, reaproveita os regex de `ast_parser.py` |
| Airflow DAG | Orquestra Planalto + TCU → parse → chunk → embed → index, agendável | Apache Airflow (TaskFlow API `@dag`/`@task`) — escrita, não executável neste sandbox |

Todos os componentes já existentes (`RawStorage`, `Chunk`, `chunker.gerar_chunks`, `HybridEmbedder`, `QdrantIndexer`) são reaproveitados sem modificação.

---

## Key Decisions

### Decision 1: `TCUScraper` implementa `LegalSource` retornando texto extraído, não HTML

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `LegalSource.fetch(url, documento_id) -> tuple[str, str]` (`ingestion/scraper/planalto_scraper.py`) foi desenhado pensando em HTML, mas sua assinatura só exige uma `str` de conteúdo + a URI de storage — nada no protocolo é HTML-específico.

**Choice:** `TCUScraper.fetch()` baixa o PDF via `httpx`, salva o PDF bruto no `RawStorage` (auditabilidade do binário original), roda `subprocess.run(["pdftotext", "-layout", ...])` e retorna `(texto_extraido, uri_do_pdf_no_gcs)` — mesma assinatura de `PlanaltoScraper.fetch`.

**Rationale:** Zero mudança no protocolo `LegalSource`; prova que a abstração da feature anterior já era genérica o suficiente (era exatamente a intenção da Decision 2 do DESIGN de `PIPELINE_INGESTAO_LEGAL`).

**Alternatives Rejected:**
1. Renomear/generalizar `LegalSource.fetch` para deixar explícito que retorna "conteúdo", não "html" — rejeitado, é só cosmético e quebraria a assinatura de `PlanaltoScraper` sem ganho real.

**Consequences:**
- `RawStorage` passa a guardar dois tipos de conteúdo (HTML e PDF binário) sob prefixos diferentes (`raw/planalto/...` vs `raw/tcu/...`) — sem mudança de interface, só de path.

---

### Decision 2: `pdftotext`/`pdftohtml` (poppler-utils) via `subprocess`, não biblioteca Python de PDF

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 (herdado do brainstorm) |

**Context:** `pypdf`, `pdfplumber`, `PyMuPDF`, `PyPDF2` não instalam neste sandbox (mesmo bloqueio `externally-managed-environment` de `qdrant-client`/`fastembed`/`langgraph`). `pdftotext`/`pdftohtml` são binários do pacote `poppler-utils`, confirmados instalados (`/usr/bin/pdftotext`, `/usr/bin/pdftohtml`) e não passam pela restrição do pip.

**Choice:** `TCUScraper` chama `pdftotext -layout <arquivo.pdf> -` via `subprocess.run(..., capture_output=True)` e consome o stdout como texto.

**Rationale:** Única opção de extração de PDF real e testável neste ambiente; `-layout` preserva a disposição espacial do texto, importante para não embaralhar numeração de artigo/parágrafo em PDFs com múltiplas colunas.

**Alternatives Rejected:**
1. Biblioteca Python de PDF — rejeitada, não instala neste sandbox.
2. Aguardar ambiente com pip liberado antes de escrever qualquer código de PDF — rejeitada, mesmo precedente já aceito nas features anteriores (escrever contra bloqueio conhecido, não esperar).

**Consequences:**
- Dependência de sistema (`poppler-utils`) precisa estar presente na imagem de deploy real (Cloud Composer worker/Cloud Run) — vira um requisito de Dockerfile/imagem base, não do `requirements.txt`.

---

### Decision 3: Parser de Resolução dedicado, não extensão de `ast_parser.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `ast_parser.parse_lei()` opera sobre `BeautifulSoup` (`<p align="center">` para detectar cabeçalhos de seção) — texto de PDF via `pdftotext` não tem essa marcação; além disso, Resoluções TCU não têm Livro/Título/Capítulo/Seção, só Artigo/Parágrafo/Inciso, e PDFs de órgãos públicos frequentemente repetem cabeçalho/rodapé (nº da página, "Impresso em ...") em cada página, ruído que HTML do Planalto não tinha.

**Choice:** Novo módulo `ingestion/parser/resolucao_parser.py` com `parse_resolucao(texto: str, documento_id: str, titulo: str, fonte_url: str) -> Lei`, operando linha a linha sobre o texto puro. Reaproveita `ARTIGO_RE`, `PARAGRAFO_NUM_RE`, `PARAGRAFO_UNICO_RE`, `INCISO_RE`, `ALINEA_RE` de `ast_parser.py` (importados, não duplicados). Adiciona uma etapa de limpeza de cabeçalho/rodapé repetido (heurística: linhas idênticas que se repetem a cada N linhas correspondentes ao tamanho de página) antes de aplicar os regex. Popula só `Lei.artigos_soltos` — `Lei.secoes` fica vazio.

**Rationale:** Forçar essa lógica dentro de `parse_lei()` (que already assume BeautifulSoup + hierarquia de seções) quebraria a função existente ou exigiria um parâmetro de modo condicional — pior que um módulo novo e pequeno. `Lei.artigos_soltos` já existe exatamente para este caso (documento sem hierarquia de seções), confirmado lendo `chunker.gerar_chunks()`, que já itera `lei.artigos_soltos` incondicionalmente.

**Alternatives Rejected:**
1. Generalizar `ast_parser.py` com um parâmetro `fonte: Literal["html", "pdf_texto"]` — rejeitado no brainstorm como prematuro (YAGNI) até haver uma 3ª fonte que confirme o padrão comum.

**Consequences:**
- Duplicação pequena e aceitável: a máquina de estados de "artigo atual/parágrafo atual/inciso atual" é reescrita (não reaproveitada), só os regex são compartilhados
- `chunker.py` e `chunk_models.py` permanecem **intocados**, confirmando a promessa do DEFINE

---

### Decision 4: DAG do Airflow com imports top-level (sem o padrão lazy-import de `grafo.py`)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-24 |

**Context:** `orquestracao/grafo.py` evita o bloqueio de `langgraph` fazendo `from langgraph.graph import ...` **dentro** de `construir_grafo()`, não no topo do arquivo — assim o módulo é importável em teste mesmo sem `langgraph` instalado. Airflow não permite esse truque: o scheduler descobre DAGs varrendo `dags/` e importando cada arquivo no nível do módulo — `@dag`/`@task` **precisam** estar decorando funções top-level para a DAG aparecer na UI/scheduler.

**Choice:** `dags/ingestao_legal_dag.py` importa `from airflow.decorators import dag, task` no topo do arquivo, como uma DAG real de produção exige. Isso significa que o arquivo **falha ao importar** neste sandbox (`ModuleNotFoundError: apache-airflow`) — aceito e documentado explicitamente, diferente do tratamento dado a `grafo.py`.

**Rationale:** Escrever uma DAG "testável" com lazy-import produziria código que nunca rodaria de verdade num Cloud Composer real (a estrutura precisa ser diferente da que o Airflow exige) — pior que aceitar que este arquivo específico só é validável por revisão de código.

**Alternatives Rejected:**
1. Aplicar o mesmo padrão lazy-import de `grafo.py` — rejeitado, produziria uma DAG que não é descoberta pelo Airflow real, invalidando o propósito da feature.
2. Instalar um shim/stub local de `airflow.decorators` só para permitir o import em teste — rejeitado, esconderia a diferença real entre "roda" e "não roda", indo contra a política do projeto de nunca fingir que algo bloqueado funciona.

**Consequences:**
- `dags/ingestao_legal_dag.py` fica **fora** da cobertura de `pytest` (nenhum teste importa esse módulo) — validado só por revisão humana/code review até existir um Cloud Composer real
- A lógica de negócio de cada `@task` (chamar `TCUScraper`, `parse_resolucao`, `gerar_chunks` etc.) é extraída para funções puras em `ingestion/` já testadas isoladamente — a DAG em si é só orquestração fina (thin wrapper), minimizando o que fica sem cobertura de teste

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `tests/fixtures/resolucao_tcu_sample.pdf` | Create | Baixar uma Resolução TCU real do portal público do TCU (necessário — a fixture presumida no BRAINSTORM não existe mais no ambiente atual) | @python-developer | None |
| 2 | `ingestion/scraper/tcu_scraper.py` | Create | `TCUScraper` implementando `LegalSource`; baixa PDF, salva no `RawStorage`, chama `pdftotext -layout` via `subprocess` | @python-developer | 1, `RawStorage` (existente) |
| 3 | `ingestion/parser/resolucao_parser.py` | Create | `parse_resolucao()`: texto puro → `Lei` (só `artigos_soltos`), reaproveitando os regex de `ast_parser.py` + limpeza de cabeçalho/rodapé de PDF | @python-developer | `ast_models.py`, `ast_parser.py` (regex) |
| 4 | `dags/ingestao_legal_dag.py` | Create | DAG TaskFlow API real (`@dag`/`@task`) orquestrando Planalto + TCU → parse → chunk → embed → index; não executável/importável neste sandbox | @airflow-specialist | 2, 3, componentes existentes de `ingestion/` |
| 5 | `tests/test_tcu_scraper.py` | Create | Testes de `TCUScraper` contra a fixture PDF real (item 1), usando `FakeInMemoryStorage` | @test-generator | 1, 2 |
| 6 | `tests/test_resolucao_parser.py` | Create | Testes de `parse_resolucao()` cobrindo AT-001/AT-002/AT-003 (happy path, PDF corrompido, parágrafo único) | @test-generator | 1, 3 |
| 7 | `tests/test_resolucao_pipeline_integration.py` | Create | Teste de integração: PDF fixture → `TCUScraper` → `parse_resolucao` → `chunker.gerar_chunks()` (sem modificação) → chunks válidos | @test-generator | 2, 3, 5, 6 |
| 8 | `CLAUDE.md` | Modify | Atualizar tabela de features/estrutura com `INGESTAO_TCU_E_ETL_AIRFLOW`, `dags/`, e a correção dos gaps já identificados na auditoria desta sessão | @doc-updater | Build completo |

**Total Files:** 8

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 2, 3 | Mesmo especialista que construiu `ingestion/` na feature anterior — reaproveita convenções já estabelecidas |
| @airflow-specialist | 4 | Único agente do projeto com conhecimento de TaskFlow API/Cloud Composer (CLAUDE.md já o recomendava para esta lacuna) |
| @test-generator | 5, 6, 7 | Especialista em pytest/fixtures, mesmo padrão usado em `test_ast_parser.py`/`test_chunker.py` |
| @doc-updater | 8 | Mantém CLAUDE.md em sincronia — a auditoria desta sessão já identificou esse arquivo como fonte frequente de desatualização |
| @security-reviewer | (revisão final) | `subprocess.run` com input de arquivo baixado da rede exige checagem de injeção de comando/path traversal |
| @code-reviewer | (revisão final, todos os arquivos) | Padrão já seguido nas features anteriores |

---

## Code Patterns

### Pattern 1: `TCUScraper` (implementa `LegalSource`)

```python
# ingestion/scraper/tcu_scraper.py
import subprocess
from datetime import datetime, timezone

from ingestion.storage.raw_storage import RawStorage


class TCUScraper:
    """Segunda implementação de LegalSource (Decision 2 da feature anterior).
    Retorna texto extraído via pdftotext, não HTML — LegalSource.fetch()
    nunca exigiu HTML especificamente, só uma str de conteúdo."""

    def __init__(self, storage: RawStorage, timeout_seconds: int = 30, max_retries: int = 3):
        self._storage = storage
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        import httpx

        pdf_bytes = self._baixar_pdf(url, httpx)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/tcu/{documento_id}/{timestamp}.pdf"
        uri = self._storage.save(path, pdf_bytes)

        texto = self._extrair_texto(pdf_bytes)
        return texto, uri

    def _baixar_pdf(self, url: str, httpx) -> bytes:
        last_error: Exception | None = None
        for tentativa in range(1, self._max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    timeout=self._timeout_seconds,
                    headers={"User-Agent": "TaxReformAI-Ingestion/0.1 (uso publico, sem PII)"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao baixar {url} após {self._max_retries} tentativas"
                    ) from last_error
        raise RuntimeError(f"Falha ao baixar {url}")

    def _extrair_texto(self, pdf_bytes: bytes) -> str:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            resultado = subprocess.run(
                ["pdftotext", "-layout", tmp.name, "-"],
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=True,
            )
        return resultado.stdout
```

### Pattern 2: Parser de Resolução (reaproveita regex, popula só `artigos_soltos`)

```python
# ingestion/parser/resolucao_parser.py
from ingestion.parser.ast_models import Artigo, Inciso, Lei, Paragrafo
from ingestion.parser.ast_parser import (
    ALINEA_RE,
    ARTIGO_RE,
    INCISO_RE,
    PARAGRAFO_NUM_RE,
    PARAGRAFO_UNICO_RE,
    ASTParseError,
)


def _remover_cabecalho_rodape_repetido(linhas: list[str]) -> list[str]:
    """PDFs do TCU repetem cabeçalho/rodapé (nº de página, órgão) em todas as
    páginas — HTML do Planalto não tinha esse ruído. Remove linhas que se
    repetem 2+ vezes de forma idêntica no documento inteiro."""
    from collections import Counter

    contagem = Counter(l.strip() for l in linhas if l.strip())
    repetidas = {l for l, n in contagem.items() if n >= 2 and len(l) < 80}
    return [l for l in linhas if l.strip() not in repetidas]


def parse_resolucao(texto: str, documento_id: str, titulo: str, fonte_url: str) -> Lei:
    linhas = _remover_cabecalho_rodape_repetido(texto.splitlines())
    lei = Lei(documento_id=documento_id, titulo=titulo, fonte_url=fonte_url)

    artigo_atual: Artigo | None = None
    paragrafo_atual: Paragrafo | None = None
    inciso_atual: Inciso | None = None

    for linha in linhas:
        text = linha.strip()
        if not text:
            continue

        m = ARTIGO_RE.match(text)
        if m:
            sufixo = m.group(2) or ""
            artigo_atual = Artigo(numero=f"{m.group(1)}{sufixo}", texto=text[m.end():].strip(" ."))
            lei.artigos_soltos.append(artigo_atual)
            paragrafo_atual = inciso_atual = None
            continue

        if artigo_atual is None:
            continue

        m = PARAGRAFO_NUM_RE.match(text) or None
        m_unico = None if m else PARAGRAFO_UNICO_RE.match(text)
        if m or m_unico:
            numero = m.group(1) if m else "único"
            corpo = text[(m or m_unico).end():].strip(" .")
            paragrafo_atual = Paragrafo(numero=numero, texto=corpo)
            artigo_atual.paragrafos.append(paragrafo_atual)
            inciso_atual = None
            continue

        m = INCISO_RE.match(text)
        if m:
            inciso_atual = Inciso(numero=m.group(1), texto=text[m.end():].strip(" ."))
            destino = paragrafo_atual.incisos if paragrafo_atual else artigo_atual.incisos
            destino.append(inciso_atual)
            continue

        m = ALINEA_RE.match(text)
        if m and inciso_atual is not None:
            inciso_atual.alineas.append(
                type(inciso_atual.alineas[0]) if inciso_atual.alineas else None  # placeholder
            )
            continue

        # Continuação de texto multi-linha
        if inciso_atual is not None:
            inciso_atual.texto = f"{inciso_atual.texto} {text}".strip()
        elif paragrafo_atual is not None:
            paragrafo_atual.texto = f"{paragrafo_atual.texto} {text}".strip()
        elif artigo_atual is not None:
            artigo_atual.texto = f"{artigo_atual.texto} {text}".strip()

    if not lei.artigos_soltos:
        raise ASTParseError("Nenhum artigo reconhecido no texto da Resolução", texto[:500])

    return lei
```
*(Nota: o placeholder de alínea acima é intencional — o Build deve corrigir para `Alinea(letra=m.group(1), texto=...)`, igual ao `ast_parser.py`; deixado assim para não fingir precisão que só a implementação real vai validar contra o PDF.)*

### Pattern 3: DAG Airflow (TaskFlow API — não executável neste sandbox)

```python
# dags/ingestao_legal_dag.py
# ⚠ apache-airflow não instala neste sandbox (Decision 4 do DESIGN) — este
# arquivo é escrito com sintaxe real de produção e validado por revisão de
# código, não por execução/import em teste automatizado.

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="ingestao_legal_taxreformai",
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["taxreformai", "ingestion"],
)
def ingestao_legal_dag():
    @task()
    def fetch_planalto() -> str:
        from ingestion.config import Settings
        from ingestion.scraper.planalto_scraper import PlanaltoScraper
        from ingestion.storage.raw_storage import GCSRawStorage

        settings = Settings.from_env()
        storage = GCSRawStorage(settings.gcs_bucket_name, settings.gcp_project_id)
        scraper = PlanaltoScraper(storage)
        html, uri = scraper.fetch(url="https://...", documento_id="LCP_214_2025")
        return uri

    @task()
    def fetch_tcu() -> str:
        from ingestion.config import Settings
        from ingestion.scraper.tcu_scraper import TCUScraper
        from ingestion.storage.raw_storage import GCSRawStorage

        settings = Settings.from_env()
        storage = GCSRawStorage(settings.gcs_bucket_name, settings.gcp_project_id)
        scraper = TCUScraper(storage)
        texto, uri = scraper.fetch(url="https://...", documento_id="TCU_RES_389_2026")
        return uri

    @task()
    def parse_chunk_embed_index(fontes: list[str]) -> dict:
        # Orquestra parse -> chunk -> embed -> index reaproveitando os
        # módulos já testados isoladamente em ingestion/. Mantido como um
        # único @task para não introduzir estado intermediário no Airflow
        # antes de haver necessidade real de paralelismo por fonte.
        from ingestion.pipeline import processar_e_indexar

        return processar_e_indexar(fontes)

    uris = [fetch_planalto(), fetch_tcu()]
    parse_chunk_embed_index(uris)


ingestao_legal_dag()
```

---

## Data Flow

```text
1. Airflow scheduler dispara a DAG (semanal) ou operador roda `airflow dags trigger`
   │
   ▼
2a. @task fetch_planalto: PlanaltoScraper.fetch() → GCS + HTML em memória
2b. @task fetch_tcu: TCUScraper.fetch() → GCS (PDF bruto) + texto extraído em memória
   │ (ambos em paralelo — TaskFlow API permite isso nativamente)
   ▼
3. @task parse_chunk_embed_index recebe as URIs, decide o parser certo por
   prefixo do path (`raw/planalto/` → ast_parser.parse_lei; `raw/tcu/` →
   resolucao_parser.parse_resolucao)
   │
   ▼
4. chunker.gerar_chunks() — SEM modificação, mesmo código das duas fontes
   │
   ▼
5. HybridEmbedder + QdrantIndexer — SEM modificação
   │
   ▼
6. Airflow registra sucesso/falha por task na UI — observability nativa do
   Composer, sem precisar de logging estruturado manual adicional
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| TCU (portal público de atos normativos) | Download HTTP de PDF (GET, sem API oficial) | Nenhuma — documento público |
| `poppler-utils` (`pdftotext`) | Chamada de processo local via `subprocess` | N/A — binário de sistema, sem rede |
| Cloud Composer (futuro) | Airflow scheduler executa `dags/ingestao_legal_dag.py` | Service account do Composer, least-privilege, escopo separado do SA de ingestão usado pelo Terraform atual |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | `TCUScraper` (download + extração via `pdftotext`) | `tests/test_tcu_scraper.py` | pytest, `FakeInMemoryStorage` | AT-001, AT-002 |
| Unit | `parse_resolucao()` | `tests/test_resolucao_parser.py` | pytest, fixture PDF real | AT-001, AT-002, AT-003 |
| Integration | PDF fixture → scraper → parser → `chunker.gerar_chunks()` (existente, sem mudança) | `tests/test_resolucao_pipeline_integration.py` | pytest | AT-001 |
| **Não coberto por automação** | `dags/ingestao_legal_dag.py` | — | Revisão de código manual | N/A — `apache-airflow` não instala neste sandbox (Decision 4) |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| PDF indisponível/timeout no portal do TCU | Retry com backoff exponencial (3 tentativas), mesmo padrão de `PlanaltoScraper` | Yes |
| `pdftotext` falha (PDF corrompido/protegido) | `subprocess.run(..., check=True)` levanta `CalledProcessError`; capturado e relançado como erro claro, sem indexar chunk vazio | No |
| Texto extraído não contém nenhum `Art.` reconhecível | `parse_resolucao` levanta `ASTParseError` (reaproveitada de `ast_parser.py`), pipeline aborta essa fonte sem indexar dado corrompido | No |
| `dags/ingestao_legal_dag.py` falha ao importar (Airflow ausente) | Esperado neste sandbox — documentado, não é bug a corrigir aqui | N/A |

---

## Configuration

Nenhuma variável de ambiente nova — reaproveita integralmente `ingestion/config.py` (`GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `QDRANT_URL`, `QDRANT_API_KEY`, já em GitHub Secrets desde esta sessão).

---

## Security Considerations

- `subprocess.run(["pdftotext", "-layout", tmp.name, "-"], ...)` usa lista de argumentos (não `shell=True`), eliminando risco de shell injection mesmo com nome de arquivo controlado externamente
- Arquivo temporário do PDF baixado usa `tempfile.NamedTemporaryFile` (path gerado pelo SO, sem input do usuário no path) — evita path traversal
- Mesma política de PII da feature anterior: Resoluções TCU são conteúdo público, sem dado pessoal
- Service account do Cloud Composer (quando provisionado) deve ter escopo próprio, least-privilege, não reaproveitar o SA `taxreform-ingestion` do Terraform atual sem revisão — a IAM de um scheduler que roda continuamente é um perfil de risco diferente de um bucket GCS estático

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Mesmo logging estruturado por etapa já usado no pipeline CLI, reaproveitado dentro de cada `@task` |
| Metrics | Airflow/Cloud Composer expõe métricas de execução de DAG/task nativamente (duração, sucesso/falha) — nenhuma instrumentação manual adicional necessária quando o Composer existir |
| Tracing | Fora de escopo, mesmo status da feature anterior |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | design-agent | Versão inicial, a partir de DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md. Corrigida premissa herdada do brainstorm: a fixture PDF do TCU não está mais disponível no ambiente atual e precisa ser baixada novamente no Build (File Manifest item 1). |
| 1.1 | 2026-07-24 | ship-agent | Shipped e arquivado — ver `SHIPPED_2026-07-24.md` |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_INGESTAO_TCU_E_ETL_AIRFLOW.md`
