# BUILD REPORT: Pipeline de Ingestão Legal (ETL + AST + RAG Híbrido)

> Implementation report for PIPELINE_INGESTAO_LEGAL

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PIPELINE_INGESTAO_LEGAL |
| **Date** | 2026-07-22 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_PIPELINE_INGESTAO_LEGAL.md](../features/DEFINE_PIPELINE_INGESTAO_LEGAL.md) |
| **DESIGN** | [DESIGN_PIPELINE_INGESTAO_LEGAL.md](../features/DESIGN_PIPELINE_INGESTAO_LEGAL.md) |
| **Status** | Complete (código) / Blocked (execução real contra GCP) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 18/18 arquivos do manifest + 2 extras (`.gitignore`, fixture real) |
| **Files Created** | 20 |
| **Lines of Code** | ~1.074 (Python) + 70 (Terraform) + fixture real de 975 linhas (LC 214/2025) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 16/16 |
| **Agents Used** | 0 (execução direta — ver nota abaixo) |

**Nota sobre agentes:** o DESIGN atribuiu arquivos a @python-developer, @gcp-data-architect, @qdrant-specialist, @ci-cd-specialist e @test-generator. Todo o código foi escrito diretamente nesta sessão (sem delegação via Task) porque o trabalho exigia validação iterativa contra HTML real do Planalto (baixado e inspecionado ao vivo) — delegar por arquivo isolado teria perdido esse contexto compartilhado entre parser/chunker/testes.

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `ingestion/config.py` | 45 | ✅ | `Settings.from_env()`, falha explícita se faltar env var obrigatória |
| `ingestion/storage/raw_storage.py` | 39 | ✅ | `RawStorage` protocol + `GCSRawStorage` + `FakeInMemoryStorage` (Decision 1) |
| `ingestion/scraper/planalto_scraper.py` | 55 | ✅ | `LegalSource` protocol + `PlanaltoScraper` (Decision 2), retry com backoff |
| `ingestion/parser/ast_models.py` | 57 | ✅ | Alterado do DESIGN: `Secao` recursiva (nivel LIVRO/TITULO/CAPITULO/SECAO/SUBSECAO) em vez de dataclasses fixas por nível — ver Deviations |
| `ingestion/parser/ast_parser.py` | 159 | ✅ | Testado contra HTML real da LC 214/2025 (11 artigos, 5 níveis de hierarquia) |
| `ingestion/chunking/chunk_models.py` | 21 | ✅ | `Chunk` Pydantic + `qdrant_point_id()` determinístico |
| `ingestion/chunking/chunker.py` | 122 | ✅ | Parent-child (Decision 3); gera 117 chunks a partir dos 11 artigos de teste |
| `ingestion/embedding/hybrid_embedder.py` | 49 | ⚠️ | Código correto (API real do `fastembed`), não executável neste sandbox — ver Blockers |
| `ingestion/indexing/qdrant_indexer.py` | 71 | ⚠️ | Código correto (API real do `qdrant-client`, named vectors + RRF), não executável neste sandbox |
| `ingestion/pipeline.py` | 167 | ✅ | Refatorado do DESIGN: `executar_pipeline()` puro (injeção de dependências) + `_build_cli()` isolando o `typer` — ver Deviations |
| `infra/terraform/main.tf` | 55 | ✅ | `terraform validate` passou (bucket GCS + service account least-privilege) |
| `infra/terraform/variables.tf` | 15 | ✅ | `terraform validate` passou |
| `.env.example` | 16 | ✅ | Todas as vars obrigatórias documentadas |
| `requirements.txt` | 9 | ✅ | |
| `tests/fixtures/sample_lei.html` | 975 | ✅ | **HTML real** da LC 214/2025 (Planalto), não sintético — Art. 1 a 10, 5 níveis de hierarquia, inclui texto revogado riscado e alíneas reais |
| `tests/test_ast_parser.py` | 102 | ✅ | 7/7 passam |
| `tests/test_chunker.py` | 75 | ✅ | 6/6 passam |
| `tests/test_pipeline_integration.py` | 112 | ✅ | 3/3 passam — cobre AT-001, AT-002, e falha parcial de embedding |
| `.gitignore` | 6 | ✅ | Extra além do manifest — necessário para não commitar `.env` |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass

### Type Check

Não configurado neste ciclo (mypy não estava nos KB domains do DESIGN). `ruff` cobre erros óbvios de tipagem via `F`/`E` rules.

**Status:** ⏭️ Skipped

### Tests

```text
$ python3 -m pytest tests/ -v
collected 16 items

tests/test_ast_parser.py::test_happy_path_estrutura_completa PASSED
tests/test_ast_parser.py::test_todos_os_artigos_de_teste_sao_capturados PASSED
tests/test_ast_parser.py::test_art1_tem_incisos_diretos_no_caput PASSED
tests/test_ast_parser.py::test_edge_case_paragrafo_unico_com_incisos PASSED
tests/test_ast_parser.py::test_edge_case_inciso_com_alineas PASSED
tests/test_ast_parser.py::test_texto_revogado_riscado_e_excluido PASSED
tests/test_ast_parser.py::test_error_case_html_sem_estrutura_reconhecida PASSED
tests/test_chunker.py::test_gera_ao_menos_um_chunk_por_artigo PASSED
tests/test_chunker.py::test_todos_os_chunks_tem_metadados_obrigatorios PASSED
tests/test_chunker.py::test_chunk_parent_child_artigo_sem_filhos PASSED
tests/test_chunker.py::test_chunk_inciso_herda_contexto_do_artigo_parent PASSED
tests/test_chunker.py::test_chunk_alinea_tem_dispositivo_granular PASSED
tests/test_chunker.py::test_pontos_qdrant_tem_id_deterministico_e_unico PASSED
tests/test_pipeline_integration.py::test_at001_happy_path_ponta_a_ponta PASSED
tests/test_pipeline_integration.py::test_at002_html_invalido_aborta_sem_indexar PASSED
tests/test_pipeline_integration.py::test_falha_de_embedding_por_chunk_nao_aborta_o_restante PASSED

============================== 16 passed in 0.74s ==============================
```

**Status:** ✅ 16/16 Pass

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `python3 -m venv` falhou (`ensurepip` ausente) e `pip install --user` bloqueado por `externally-managed-environment` | Não forcei `--break-system-packages` (modificaria o ambiente Python global do usuário sem autorização) — segui com as libs já instaladas (`bs4`, `pydantic`, `httpx`, `pytest`) e isolei `typer`/`qdrant-client`/`fastembed`/`google-cloud-storage` atrás de imports internos, para que o core do pipeline permaneça testável mesmo sem essas libs no sandbox | +15m |
| 2 | Fixture inicial decodificada como `latin-1` produzia aspas tipográficas corrompidas (`\x93a\x94` em vez de `"a"`) | Identifiquei que o Planalto usa `cp1252` (Windows-1252), não ISO-8859-1 puro; reencodei a fixture | +5m |
| 3 | Parágrafos duplicados no parse (`§4º` e um inciso apareciam duas vezes) | Investigando o HTML original descobri que o Planalto mantém a **redação revogada riscada** (`text-decoration:line-through`) antes da redação vigente — um problema real de qualidade de dados que, se ignorado, faria o RAG citar lei morta. Adicionei `_e_texto_revogado()` para excluir esses parágrafos | +10m |
| 4 | `Art. 7º-A` (artigo incluído por emenda posterior) virava `numero="7"` com `"-A."` sobrando no início do texto | Corrigi `ARTIGO_RE` para capturar o sufixo alfabético (`-A`) separadamente do ordinal (`º`), já que a ordem real no HTML é `7º-A`, não `7-A` | +5m |
| 5 | Seção IV ("Do Local da Operação") estava engolindo o Art. 10 como se fosse continuação do título | A linha do Art. 10 tinha `align="center"` por inconsistência do HTML original; adicionei uma guarda para nunca tratar uma linha que casa com `ARTIGO_RE` como continuação de título de seção | +5m |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `ast_models.py`: `Secao` genérica recursiva (`nivel` + `subsecoes`) em vez das dataclasses fixas `Titulo`/`Capitulo` do Pattern 1 do DESIGN | Ao inspecionar o HTML real da LC 214/2025, a hierarquia tem **5 níveis** (Livro > Título > Capítulo > Seção > Subseção), não os 2 do blueprint original (seção 4.3). Uma estrutura recursiva generaliza sem precisar de uma dataclass por nível | Nenhum — o schema de `Chunk` (Data Contract) não muda; `dispositivo` continua granular por Artigo/§/Inciso/alínea |
| `pipeline.py`: função pura `executar_pipeline()` com dependências injetadas (`scraper`, `embedder`, `indexer`), CLI isolada em `_build_cli()` | Necessário para que `tests/test_pipeline_integration.py` exercite o fluxo completo com fakes, sem exigir `typer`/GCP/Qdrant reais instalados no ambiente de teste | Nenhum no comportamento do CLI; melhora testabilidade, consistente com o padrão `RawStorage`/`LegalSource` já adotado no DESIGN |
| Exclusão de parágrafos com `text-decoration:line-through` (texto revogado/vetado) | Descoberta durante o build: sem isso, o pipeline indexaria redação legal já superada, quebrando a garantia de auditabilidade do produto | Nova regra de qualidade de dados, não estava no DESIGN original — deve ser preservada em qualquer refatoração futura do parser |

---

## Blockers

**Atualização 2026-07-24 (pós-auditoria):** os blockers de credenciais abaixo foram resolvidos — `GCP_PROJECT_ID`/`GCS_BUCKET_NAME` são reais (Terraform aplicado, bucket `taxreformai-dev-legal-docs`) e `QDRANT_URL`/`QDRANT_API_KEY` (Qdrant Cloud free tier) também. Todos vivem em GitHub Secrets, não em `.env` local — política do projeto é que infraestrutura real só roda em GCP/CI, nunca localmente (ver `CLAUDE.md`, "Como rodar"). Isso significa que o blocker de *credenciais* está resolvido, mas o de *execução E2E* persiste por um motivo diferente: `qdrant-client`/`google-cloud-storage`/`fastembed` não instalam neste sandbox, e a execução real não pode simplesmente rodar aqui mesmo com credenciais — precisa rodar via `dags/ingestao_legal_dag.py` num Cloud Composer real (feature `INGESTAO_TCU_E_ETL_AIRFLOW`, já shipada) ou um workflow de CI equivalente, nenhum dos dois ainda executado de fato.

| Blocker | Status | Required Action | Owner |
|---------|--------|-----------------|-------|
| ~~`GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `QDRANT_URL`, `QDRANT_API_KEY` ainda não fornecidos~~ | ✅ Resolvido | — | — |
| `qdrant-client`, `google-cloud-storage`, `fastembed`, `typer` não instaláveis neste sandbox | Ainda bloqueado | Instalar num ambiente com controle (fora deste sandbox) — Cloud Composer/Cloud Run já resolvem isso via imagem própria | Usuário |
| `ingestion/embedding/hybrid_embedder.py` e `ingestion/indexing/qdrant_indexer.py` nunca exercitados contra libs reais | Ainda pendente | Disparar `dags/ingestao_legal_dag.py` num Cloud Composer real (ou workflow de CI equivalente) — não rodar localmente, mesmo com credenciais disponíveis | Usuário |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path — lei do Planalto em HTML → chunks no Qdrant com metadados corretos | ✅ Pass (via fakes) | `test_at001_happy_path_ponta_a_ponta`: 11 artigos → 117 chunks, `indexer.upserted` com 117 pontos, todos com metadados obrigatórios. **E2E contra GCS/Qdrant Cloud reais ainda pendente** (bloqueado por credenciais) |
| AT-002 | Error case — HTML fora do padrão não quebra silenciosamente nem indexa dado corrompido | ✅ Pass | `test_at002_html_invalido_aborta_sem_indexar`: `ASTParseError` levantado, `indexer.upserted` permanece vazio |
| AT-003 | Edge case — estrutura aninhada complexa (parágrafo único + incisos, inciso + alíneas) preservada | ✅ Pass | `test_edge_case_paragrafo_unico_com_incisos` (Art. 7º-A) e `test_edge_case_inciso_com_alineas` (Art. 3, Inciso I) — ambos contra a **lei real**, não fixture sintética |

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| Estrutura AST completa para 100% dos artigos de 1 Lei Complementar de teste | ✅ | 11/11 artigos (1 a 10, mais 7-A) capturados com hierarquia completa |
| 100% dos chunks com metadados obrigatórios do schema (seção 4.3) | ✅ | `test_todos_os_chunks_tem_metadados_obrigatorios` — 117/117 chunks |
| Busca híbrida retorna o dispositivo correto (top-3) para 5 perguntas de teste | ⏳ Pendente | Requer Qdrant Cloud real populado — não executável neste sandbox |

---

## Final Status

### Overall: 🔄 IN PROGRESS (código completo e testado; execução real contra GCP pendente de credenciais)

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados (18/18) + 2 extras justificados
- [x] Lint (`ruff`) passa
- [x] Testes automatizados passam (16/16, usando fakes conforme Decision 5)
- [x] Terraform validado (`terraform validate`)
- [x] AT-001, AT-002, AT-003 verificados via fakes
- [ ] Execução E2E real contra GCS + Qdrant Cloud (bloqueado — falta `.env` preenchido)
- [ ] `pip install -r requirements.txt` confirmado num ambiente com `qdrant-client`/`fastembed`/`google-cloud-storage`/`typer` instaláveis

---

## Next Step

**Para desbloquear o E2E real:**
1. Preencher `.env` com `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `QDRANT_URL`, `QDRANT_API_KEY`
2. `cd infra/terraform && terraform init && terraform apply` (provisiona o bucket)
3. `pip install -r requirements.txt` num ambiente Python gerenciável (venv/pipx)
4. `python -m ingestion.pipeline run --url https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm --documento-id LCP_214_2025 --titulo "Lei Complementar 214/2025" --esfera FEDERAL_CBS_IBS --data-vigencia-inicio 2027-01-01`

**Depois disso:** `/ship .claude/sdd/features/DEFINE_PIPELINE_INGESTAO_LEGAL.md`
