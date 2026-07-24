# DESIGN: Pipeline de Ingestão Legal (ETL + AST + RAG Híbrido)

> Technical design for implementing o pipeline que raspa, estrutura em AST e indexa via embedding híbrido a legislação do Planalto para o RAG do TaxReform AI.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PIPELINE_INGESTAO_LEGAL |
| **Date** | 2026-07-22 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_PIPELINE_INGESTAO_LEGAL.md](./DEFINE_PIPELINE_INGESTAO_LEGAL.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│              PIPELINE DE INGESTÃO LEGAL — PLANALTO (MVP)             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Planalto HTML]                                                      │
│        │  scraper/planalto_scraper.py                                 │
│        ▼                                                              │
│  [GCS Bucket]  gs://{bucket}/raw/planalto/{documento_id}/{ts}.html    │
│        │  parser/ast_parser.py                                        │
│        ▼                                                              │
│  [AST Tree]  Lei → Título → Capítulo → Artigo → Parágrafo → Inciso    │
│        │  chunking/chunker.py (parent-child)                          │
│        ▼                                                              │
│  [Chunks + Metadata]  documento_id, dispositivo, esfera, vigência     │
│        │  embedding/hybrid_embedder.py                                │
│        ▼                                                              │
│  [Vetores Densos (BGE-M3) + Esparsos (BM25)]                          │
│        │  indexing/qdrant_indexer.py                                  │
│        ▼                                                              │
│  [Qdrant Cloud (GCP Marketplace)] ── busca híbrida (RRF) ──► [Agentes]│
│                                                                        │
│  Orquestração: pipeline.py (CLI) — Airflow DAG fica para ciclo futuro │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Scraper (Planalto) | Baixa o HTML da lei-alvo e envia para o GCS Storage | Python + `httpx` + `BeautifulSoup` |
| GCS Raw Storage | Guarda cópia imutável do HTML original, por auditabilidade | `google-cloud-storage` (bucket dedicado, região `southamerica-east1`) |
| AST Parser | Converte o HTML em árvore hierárquica (Lei→Título→Capítulo→Artigo→Parágrafo→Inciso) | Python + `BeautifulSoup`/`lxml`, dataclasses |
| Chunker | Percorre a árvore AST e gera chunks parent-child com metadados completos | Python + Pydantic |
| Hybrid Embedder | Gera vetor denso (BGE-M3) e esparso (BM25) por chunk | `fastembed` |
| Qdrant Indexer | Cria a coleção (se necessário) e faz upsert dos chunks + vetores | `qdrant-client` (Qdrant Cloud via GCP Marketplace) |
| Pipeline Orchestrator | CLI que encadeia scraper → parser → chunker → embedder → indexer | Python (`typer`) |

---

## Key Decisions

### Decision 1: Infraestrutura GCP real desde o MVP (GCS + Qdrant Cloud)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O DEFINE deixou em aberto se o MVP roda contra GCP real ou local. O usuário pediu explicitamente para já validar contra a infraestrutura real desde o primeiro ciclo, o que também é o que o blueprint já define nas seções 5.1/5.2 (GCS para raw storage, Qdrant Cloud via GCP Marketplace, região `southamerica-east1`).

**Choice:** Raw storage vai direto para um bucket GCS dedicado (`gs://{bucket}/raw/planalto/{documento_id}/{timestamp}.html`); indexação vai direto para uma instância Qdrant Cloud provisionada via GCP Marketplace. Para manter os testes automatizados rápidos e determinísticos sem depender de credenciais reais (mesma motivação da Decision 5), a camada de storage é abstraída atrás de um protocolo `RawStorage`, com `GCSRawStorage` como implementação real e uma `FakeInMemoryStorage` usada apenas nos testes.

**Rationale:** Elimina a necessidade de migrar de local para GCP depois — o que for validado no MVP já é o ambiente real de produção. A abstração `RawStorage` preserva a testabilidade sem exigir Docker/emulador local.

**Alternatives Rejected:**
1. Ambiente local-first com Qdrant via Docker e filesystem local — rejeitado a pedido explícito do usuário, que prioriza validar contra a infra real desde já.
2. Emulador GCS local (`fake-gcs-server`) para todo o desenvolvimento, não só testes — rejeitado, adiciona uma peça de infra extra sem necessidade real, já que o usuário já vai usar GCP em produção.

**Consequences:**
- Exige um GCP project com billing habilitado, um bucket GCS provisionado e uma instância Qdrant Cloud (GCP Marketplace) antes da primeira execução ponta-a-ponta
- Nenhuma migração futura de infraestrutura será necessária — o MVP já roda no ambiente real

---

### Decision 2: Fonte única (Planalto) com interface extensível

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O brainstorm mapeou 8 fontes públicas, mas o DEFINE restringe o MVP ao Planalto.

**Choice:** Implementar um protocolo `LegalSource` do qual `PlanaltoScraper` é a primeira implementação, mesmo que nenhuma outra fonte seja implementada neste ciclo.

**Rationale:** Custo baixo de definir a interface agora evita reescrever o pipeline inteiro quando DOU/RFB/CONFAZ entrarem em ciclos futuros.

**Alternatives Rejected:**
1. Codificar o scraper do Planalto diretamente no pipeline sem abstração — rejeitado, criaria acoplamento que exigiria refatoração grande ao adicionar a segunda fonte.

**Consequences:**
- Pequena camada de abstração extra no código deste ciclo
- Adicionar DOU/RFB/CONFAZ como fonte 2 deve ser incremental, não uma reescrita

---

### Decision 3: Chunking Parent-Child (Artigo como parent, Parágrafo/Inciso como child)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O blueprint (`contexto.md`, seção 4.3) afirma que "cada Child Chunk herda o contexto do Parent Chunk", mas o DEFINE não especificou a granularidade exata de chunking.

**Choice:** Cada Artigo vira um "parent chunk" (texto completo do artigo); cada Parágrafo/Inciso dentro dele vira um "child chunk" indexado separadamente, com o texto do parent prependado como contexto e o `dispositivo` granular (ex.: `"Art. 18, §2º, Inciso II"`) preservado nos metadados.

**Rationale:** Chunking só em nível de Artigo perde a precisão de citação que o Extrator de Regras exige; chunking só em nível de Inciso, sem contexto do parent, produz fragmentos curtos demais para embeddings densos de qualidade.

**Alternatives Rejected:**
1. Um chunk por Artigo inteiro — rejeitado, perde granularidade de citação.
2. Um chunk por Inciso sem contexto do parent — rejeitado, fragmentos curtos prejudicam a busca vetorial.

**Consequences:**
- Mais chunks por lei (maior custo de armazenamento/embedding)
- Citações precisas e busca semanticamente coerente ao mesmo tempo

---

### Decision 4: Busca híbrida nativa do Qdrant (named vectors dense+sparse)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O blueprint pede embedding híbrido (denso BGE-M3 + esparso BM25), mas não especifica a implementação técnica.

**Choice:** Uma única coleção Qdrant com dois named vectors por ponto — denso (BGE-M3 via `fastembed`) e esparso (BM25 via `fastembed`) — combinados via fusion query (RRF) do Qdrant no momento da busca.

**Rationale:** Evita manter dois sistemas de busca separados (ex.: Qdrant + Elasticsearch); Qdrant ≥ 1.10 suporta named vectors + sparse vectors nativamente na mesma coleção.

**Alternatives Rejected:**
1. Sistema de busca esparsa separado (Elasticsearch/OpenSearch) — rejeitado, adiciona um segundo banco de dados a operar no MVP.

**Consequences:**
- Depende de Qdrant ≥ 1.10 e da biblioteca `fastembed`
- Uma única fonte de verdade para busca, sem sincronização entre dois sistemas

---

### Decision 5: Fixture de teste em vez de chamadas de rede ao vivo em testes automatizados

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-22 |

**Context:** O Planalto é um site governamental externo; testes automatizados que dependem dele seriam frágeis (rate limiting, indisponibilidade, mudanças de HTML).

**Choice:** Salvar uma cópia HTML real (fixture) da lei de teste em `tests/fixtures/sample_lei.html` na primeira execução manual do scraper, e usar essa fixture em todos os testes automatizados de parser/chunker. Apenas o teste E2E manual roda contra a rede ao vivo.

**Rationale:** Testes determinísticos e rápidos, sem depender da disponibilidade do Planalto nem arriscar bloqueio por scraping excessivo durante desenvolvimento/CI.

**Alternatives Rejected:**
1. Mockar o HTTP client em vez de salvar uma fixture real — rejeitado, mocks sintéticos não capturam a complexidade real do HTML do Planalto, que é justamente o que o parser precisa lidar.

**Consequences:**
- Fixture precisa ser atualizada manualmente se o layout do Planalto mudar
- Testes rápidos, determinísticos, sem dependência de rede

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `ingestion/config.py` | Create | Configuração central (URLs, GCP project/bucket, nomes de coleção, modelos) | @python-developer | None |
| 2 | `ingestion/storage/raw_storage.py` | Create | Protocolo `RawStorage` + `GCSRawStorage` (real) e `FakeInMemoryStorage` (testes) | @gcp-data-architect | 1 |
| 3 | `ingestion/scraper/planalto_scraper.py` | Create | Implementa `LegalSource` para o Planalto; baixa HTML e delega a um `RawStorage` | @python-developer | 1, 2 |
| 4 | `ingestion/parser/ast_models.py` | Create | Dataclasses da árvore AST (Lei, Título, Capítulo, Artigo, Parágrafo, Inciso) | @python-developer | None |
| 5 | `ingestion/parser/ast_parser.py` | Create | Converte HTML salvo em árvore AST usando `ast_models` | @python-developer | 4 |
| 6 | `ingestion/chunking/chunk_models.py` | Create | Modelo Pydantic `Chunk`, validando o schema do Data Contract | @python-developer | None |
| 7 | `ingestion/chunking/chunker.py` | Create | Percorre a árvore AST (parent-child) e gera `list[Chunk]` | @python-developer | 4, 5, 6 |
| 8 | `ingestion/embedding/hybrid_embedder.py` | Create | Gera vetor denso (BGE-M3) + esparso (BM25) por chunk | @python-developer | 6 |
| 9 | `ingestion/indexing/qdrant_indexer.py` | Create | Conecta na Qdrant Cloud, garante a coleção e faz upsert dos chunks + vetores | @qdrant-specialist | 6, 8 |
| 10 | `ingestion/pipeline.py` | Create | CLI que orquestra scraper → parser → chunker → embedder → indexer | @python-developer | 3, 5, 7, 8, 9 |
| 11 | `infra/terraform/main.tf` | Create | Provisiona o bucket GCS de raw storage (região `southamerica-east1`) | @ci-cd-specialist | None |
| 12 | `infra/terraform/variables.tf` | Create | Variáveis Terraform: `project_id`, `region`, `bucket_name` | @ci-cd-specialist | None |
| 13 | `.env.example` | Create | Template de variáveis de ambiente: `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `QDRANT_URL`, `QDRANT_API_KEY` | @python-developer | None |
| 14 | `requirements.txt` | Create | Dependências Python (`httpx`, `beautifulsoup4`, `pydantic`, `qdrant-client`, `google-cloud-storage`, `fastembed`, `typer`) | @python-developer | None |
| 15 | `tests/fixtures/sample_lei.html` | Create | Cópia HTML real de uma lei do Planalto, usada como fixture de teste | @test-generator | 3 |
| 16 | `tests/test_ast_parser.py` | Create | Testes unitários do parser AST contra a fixture | @test-generator | 5, 15 |
| 17 | `tests/test_chunker.py` | Create | Testes unitários do chunker (estrutura parent-child, metadados completos) | @test-generator | 7, 16 |
| 18 | `tests/test_pipeline_integration.py` | Create | Teste de integração do pipeline completo contra a fixture, usando `FakeInMemoryStorage` (sem GCP real) | @test-generator | 10, 15 |

**Total Files:** 18

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @python-developer | 1, 3, 4, 5, 6, 7, 8, 10, 13, 14 | Especialista em código Python de data engineering — dataclasses, type hints, parsers e pipelines |
| @gcp-data-architect | 2 | Especialista em integração com GCS e padrões de acesso a dados no GCP |
| @qdrant-specialist | 9 | Especialista em coleções Qdrant Cloud e named vectors híbridos |
| @ci-cd-specialist | 11, 12 | Especialista em Terraform e provisionamento de infraestrutura GCP |
| @test-generator | 15, 16, 17, 18 | Especialista em testes pytest, fixtures e cobertura de casos de borda |
| @security-reviewer | (revisão final, foco em credenciais/IAM) | Scraping de site externo + credenciais GCP reais exigem checagem de segredo/least-privilege |
| @code-reviewer | (revisão final, todos os arquivos) | Revisão de qualidade geral antes de marcar a feature como concluída |

**Agent Discovery:**
- Agentes recomendados já listados em `CLAUDE.md` para este projeto (stack Python/GCP/Qdrant/RAG)
- Matched by: tipo de arquivo, domínio (parsing, indexação vetorial, testes)

---

## Code Patterns

### Pattern 1: Dataclasses da Árvore AST

```python
# ingestion/parser/ast_models.py
# Usado para representar a hierarquia Lei → Título → Capítulo → Artigo → Parágrafo → Inciso

from dataclasses import dataclass, field


@dataclass
class Inciso:
    numero: str          # ex: "II"
    texto: str


@dataclass
class Paragrafo:
    numero: str          # ex: "2º" ou "único"
    texto: str
    incisos: list[Inciso] = field(default_factory=list)


@dataclass
class Artigo:
    numero: str           # ex: "18"
    texto: str
    paragrafos: list[Paragrafo] = field(default_factory=list)


@dataclass
class Capitulo:
    titulo: str
    artigos: list[Artigo] = field(default_factory=list)


@dataclass
class Lei:
    documento_id: str      # ex: "LC_214_2025"
    titulo: str
    capitulos: list[Capitulo] = field(default_factory=list)
```

### Pattern 2: Modelo de Chunk (Data Contract)

```python
# ingestion/chunking/chunk_models.py
# Espelha o schema definido na Data Contract do DEFINE

from datetime import date
from pydantic import BaseModel


class Chunk(BaseModel):
    documento_id: str
    dispositivo: str                     # ex: "Art. 18, §2º, Inciso II"
    esfera: str                          # ex: "SUBNACIONAL_IBS"
    data_vigencia_inicio: date
    data_vigencia_fim: date | None = None
    ncm_relacionadas: list[str] = []
    regime: str | None = None
    texto: str                            # conteúdo do chunk (child, com contexto do parent)
    parent_texto: str | None = None       # texto completo do Artigo (contexto herdado)
    fonte_url: str                        # URL de origem, para lineage/auditabilidade
```

### Pattern 3: Abstração de Raw Storage (GCS real + fake para testes)

```python
# ingestion/storage/raw_storage.py
# Permite trocar GCS real por uma implementação em memória nos testes,
# sem exigir credenciais GCP para rodar a suíte automatizada.

from typing import Protocol


class RawStorage(Protocol):
    def save(self, path: str, content: bytes) -> str:
        """Salva o conteúdo e retorna a URI final (gs://... ou chave in-memory)."""
        ...

    def read(self, path: str) -> bytes:
        ...


class GCSRawStorage:
    def __init__(self, bucket_name: str, project_id: str):
        from google.cloud import storage
        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def save(self, path: str, content: bytes) -> str:
        blob = self._bucket.blob(path)
        blob.upload_from_string(content)
        return f"gs://{self._bucket.name}/{path}"

    def read(self, path: str) -> bytes:
        return self._bucket.blob(path).download_as_bytes()


class FakeInMemoryStorage:
    """Usado apenas em tests/ — evita depender de credenciais GCP reais."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def save(self, path: str, content: bytes) -> str:
        self._data[path] = content
        return f"memory://{path}"

    def read(self, path: str) -> bytes:
        return self._data[path]
```

### Pattern 4: Configuração Estrutural

```yaml
# ingestion/config.py expõe estas variáveis como constantes/env vars

planalto_base_url: "https://www.planalto.gov.br"
gcp_project_id: "${GCP_PROJECT_ID}"          # obrigatório, sem default
gcs_bucket_name: "${GCS_BUCKET_NAME}"        # obrigatório, sem default
gcp_region: "southamerica-east1"
qdrant_url: "${QDRANT_URL}"                  # endpoint da instância Qdrant Cloud
qdrant_api_key: "${QDRANT_API_KEY}"          # secret — nunca hardcoded
qdrant_collection_name: "legislacao_tributaria"
dense_embedding_model: "BAAI/bge-m3"
chunk_parent_level: "artigo"
request_timeout_seconds: 30
max_retries: 3
```

---

## Data Flow

```text
1. Operador executa `python -m ingestion.pipeline --url <url-da-lei>`
   │
   ▼
2. Scraper baixa o HTML e salva via `GCSRawStorage` em gs://{bucket}/raw/planalto/{documento_id}/{timestamp}.html
   │
   ▼
3. AST Parser lê o HTML salvo e constrói a árvore hierárquica em memória
   │
   ▼
4. Chunker percorre a árvore (parent-child) e gera list[Chunk] com metadados completos
   │
   ▼
5. Hybrid Embedder gera vetor denso + esparso para o texto de cada chunk
   │
   ▼
6. Qdrant Indexer garante que a coleção existe e faz upsert dos pontos (vetores + payload)
   │
   ▼
7. Pipeline registra métricas de execução (artigos, chunks, erros) em log estruturado
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Planalto (planalto.gov.br) | Scraping HTTP (GET, sem API oficial) | Nenhuma — página pública |
| Google Cloud Storage | SDK Python (`google-cloud-storage`) | Service account com papel `Storage Object Admin` escopado só ao bucket, via Application Default Credentials |
| Qdrant Cloud (GCP Marketplace) | SDK Python (`qdrant-client`) | API key via variável de ambiente `QDRANT_API_KEY` (nunca hardcoded) |
| Modelo de embedding (BGE-M3 / BM25) | Biblioteca local (`fastembed`), inferência local | N/A — sem chamada de API externa |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|----------------|
| Unit | Parser e Chunker | `tests/test_ast_parser.py`, `tests/test_chunker.py` | pytest | 80% |
| Integration | Pipeline completo contra fixture local, usando `FakeInMemoryStorage` (sem GCP real) | `tests/test_pipeline_integration.py` | pytest + fixture HTML | AT-001, AT-002, AT-003 |
| E2E | Execução manual contra Planalto ao vivo + GCS + Qdrant Cloud reais | Manual | - | Happy path (AT-001) |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| Página indisponível/timeout (Planalto fora do ar) | Retry com backoff exponencial (3 tentativas); se falhar, log de erro e aborta sem indexar dados parciais | Yes |
| HTML fora do padrão esperado (estrutura mudou) | Parser levanta `ASTParseError` com contexto do trecho problemático; pipeline aborta sem indexar dados corrompidos | No |
| Falha ao gerar embedding (erro de inferência) | Log de erro por chunk; chunk é pulado e reportado no resumo final, pipeline continua para os demais | No |
| Falha ao conectar no Qdrant | Retry com backoff (3 tentativas); se falhar, aborta e reporta erro claro — chunks já gerados ficam salvos em arquivo intermediário, não se perdem | Yes |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|--------------|
| `planalto_base_url` | string | `"https://www.planalto.gov.br"` | Base URL do Planalto para montar a URL da lei-alvo |
| `gcp_project_id` | string | *(sem default — obrigatório)* | ID do projeto GCP; vem de `GCP_PROJECT_ID` |
| `gcs_bucket_name` | string | *(sem default — obrigatório)* | Bucket GCS de raw storage; vem de `GCS_BUCKET_NAME` |
| `gcp_region` | string | `"southamerica-east1"` | Região GCP, conforme blueprint (seção 5.1) |
| `qdrant_url` | string | *(sem default — obrigatório)* | Endpoint da instância Qdrant Cloud; vem de `QDRANT_URL` |
| `qdrant_api_key` | string (secret) | *(sem default — obrigatório)* | API key da Qdrant Cloud; vem de `QDRANT_API_KEY`, nunca hardcoded |
| `qdrant_collection_name` | string | `"legislacao_tributaria"` | Nome da coleção Qdrant |
| `dense_embedding_model` | string | `"BAAI/bge-m3"` | Modelo usado para o vetor denso |
| `chunk_parent_level` | string | `"artigo"` | Nível da árvore AST usado como parent chunk |
| `request_timeout_seconds` | int | `30` | Timeout de rede para o scraper |
| `max_retries` | int | `3` | Número de tentativas em falhas de rede/GCS/Qdrant |

---

## Security Considerations

- Scraping deve respeitar `robots.txt` e usar delay entre requisições — evita banimento de IP e é boa prática ética ao acessar um site governamental
- Nenhum dado pessoal (PII) é processado neste pipeline — legislação é conteúdo público, então controles de LGPD/anonimização não se aplicam a esta feature
- Service account do GCS deve ter apenas o papel `Storage Object Admin` escopado ao bucket específico (least privilege), nunca `Owner`/`Editor` do projeto
- API key da Qdrant Cloud e credenciais GCP vêm exclusivamente de variáveis de ambiente/Secret Manager — nunca hardcoded, nunca commitadas (`.env` deve estar no `.gitignore`; só `.env.example` vai para o repositório)
- HTML de origem deve ser tratado como não-confiável na análise (parsing defensivo), mesmo sem risco de XSS já que o conteúdo nunca é renderizado em navegador

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | Logging estruturado (JSON) por etapa — nº de artigos encontrados, chunks gerados, erros por chunk, tempo de execução |
| Metrics | Resumo impresso ao final da execução (contagem de sucesso/erro); métricas formais (Prometheus/Cloud Monitoring) ficam para quando a orquestração migrar para Airflow |
| Tracing | Fora de escopo neste ciclo — pipeline roda como script único, sem necessidade de tracing distribuído ainda |

---

## Pipeline Architecture

### DAG Diagram

```text
[Planalto HTML] ──scrape──→ [GCS Bucket] ──parse AST──→ [AST Tree]
                                                                     │
                                                          chunk (parent-child)
                                                                     ▼
                                                          [Chunks + Metadata]
                                                                     │
                                                          embed (dense + sparse)
                                                                     ▼
                                                  [Qdrant Cloud Collection] ──► Agentes RAG
```

### Partition Strategy

N/A neste ciclo — coleção única no Qdrant sem particionamento físico. O payload `data_vigencia_inicio`/`data_vigencia_fim` é indexado como campo filtrável do Qdrant, substituindo a necessidade de particionamento no MVP.

### Incremental Strategy

| Model | Strategy | Key Column | Lookback |
|-------|----------|-------------|-----------|
| Coleção `legislacao_tributaria` | `full_refresh` por lei (reprocessa a lei inteira a cada execução) | `documento_id` | N/A — atualização incremental por diff de conteúdo é um COULD, fora do MVP |

### Schema Evolution Plan

| Change Type | Handling | Rollback |
|-------------|----------|-----------|
| Novo campo de metadado | Adicionar como campo opcional no payload (Qdrant é schemaless), sem quebrar pontos existentes | Remover o campo dos próximos upserts |
| Mudança de tipo de campo | Reindexação completa da coleção (Qdrant não suporta migração de tipo in-place) | Restaurar do raw storage e reindexar com o schema anterior |
| Remoção de campo | Deprecar no Data Contract, parar de popular em novos upserts | Reindexar a partir do raw storage |

### Data Quality Gates

| Gate | Tool | Threshold | Action on Failure |
|------|------|-----------|---------------------|
| Zero chunks sem metadados obrigatórios | Validação Pydantic na criação do `Chunk` | 0 chunks inválidos | Bloqueia a indexação daquele chunk específico, loga erro |
| 100% dos artigos geram ao menos 1 chunk | Contagem pós-chunking comparada à contagem de `<Artigo>` no AST | 100% cobertura | Alerta no log final; não bloqueia (permite indexação parcial revisável) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-22 | design-agent | Versão inicial, a partir de DEFINE_PIPELINE_INGESTAO_LEGAL.md |
| 1.1 | 2026-07-22 | design-agent | Decision 1 revertida de "local-first" para "GCP real desde o MVP" (GCS + Qdrant Cloud), a pedido explícito do usuário. Adicionada abstração `RawStorage` para manter os testes automatizados sem dependência de credenciais reais. File Manifest atualizado (Terraform, `.env.example`, storage module) — 15 → 18 arquivos. |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_PIPELINE_INGESTAO_LEGAL.md`
