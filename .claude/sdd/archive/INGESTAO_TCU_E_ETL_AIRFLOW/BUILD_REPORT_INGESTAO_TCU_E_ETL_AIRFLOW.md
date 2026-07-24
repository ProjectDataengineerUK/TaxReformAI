# BUILD REPORT: Segunda Fonte de Ingestão (TCU) + Camada ETL Real (Airflow)

> Implementation report for INGESTAO_TCU_E_ETL_AIRFLOW

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_TCU_E_ETL_AIRFLOW |
| **Date** | 2026-07-24 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md](../features/DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md) |
| **DESIGN** | [DESIGN_INGESTAO_TCU_E_ETL_AIRFLOW.md](../features/DESIGN_INGESTAO_TCU_E_ETL_AIRFLOW.md) |
| **Status** | Complete (código) / Blocked (execução real da DAG — falta Cloud Composer) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 8/8 do manifest + 1 extra (`.github/workflows/ci.yml`, poppler-utils) |
| **Files Created** | 6 novos + 3 modificados |
| **Lines of Code** | ~430 (Python) + ~110 (DAG Airflow) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 13/13 novos (72/72 na suíte inteira) |
| **Agents Used** | 0 (execução direta — mesmo raciocínio da feature anterior: validar contra o PDF real exigiu iteração compartilhada entre parser/scraper/testes) |

---

## Files Created / Modified

| File | Action | Lines | Verified | Notes |
| ---- | ------ | ----- | -------- | ----- |
| `tests/fixtures/resolucao_tcu_sample.pdf` | Create | 78KB, 4 páginas | ✅ | **PDF real** baixado de `rotadajurisprudencia.com.br` — Resolução TCU nº 388/2026 (não a 389 presumida no brainstorm, que não existia mais neste ambiente) |
| `ingestion/parser/resolucao_parser.py` | Create | 108 | ✅ | `parse_resolucao()`; reaproveita `ALINEA_RE`/`HEADER_RE`/`INCISO_RE`/`PARAGRAFO_*_RE` de `ast_parser.py`; define `ARTIGO_DEFINICAO_RE` case-sensitive próprio — ver Deviations |
| `ingestion/scraper/tcu_scraper.py` | Create | 76 | ✅ | `TCUScraper` implementa `LegalSource`; `_extrair_texto()` via `subprocess` + `pdftotext -layout` |
| `ingestion/pipeline.py` | Modify | +6/-3 | ✅ | `executar_pipeline()` ganhou parâmetro `parser: Callable[..., Lei] = parse_lei` (keyword-only, default preserva comportamento do Planalto) — não estava no File Manifest original, necessário para a DAG reaproveitar a mesma orquestração para TCU sem duplicá-la (ver Deviations) |
| `dags/ingestao_legal_dag.py` | Create | 110 | ⚠️ | Sintaxe real TaskFlow API (`@dag`/`@task`); `ModuleNotFoundError: apache-airflow` confirmado ao tentar importar — esperado (Decision 4) |
| `tests/test_resolucao_parser.py` | Create | 79 | ✅ | 7/7 passam, contra o PDF real |
| `tests/test_tcu_scraper.py` | Create | 47 | ✅ | 4/4 passam; não mocka a chamada HTTP (mesmo precedente de `PlanaltoScraper`, nunca testado isoladamente) |
| `tests/test_resolucao_pipeline_integration.py` | Create | 84 | ✅ | 2/2 passam; PDF real → `TCUScraper`-like fake → `parse_resolucao` → `chunker.gerar_chunks()` **sem nenhuma modificação** |
| `.github/workflows/ci.yml` | Modify | +3 | ✅ | Adicionado step `apt-get install poppler-utils` — necessário pros testes do `TCUScraper` passarem em CI; não estava no File Manifest original |
| `CLAUDE.md` | Modify | — | ✅ | Tabela de features, estrutura, contagem de testes, status de `@airflow-specialist`/`@gcp-data-architect` atualizados |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass (1 erro corrigido durante o build: `E741` variável ambígua `l` em `_remover_rodape_repetido`)

### Tests

```text
$ python3 -m pytest tests/ -q
........................................................................ [100%]
72 passed, 1 warning in 3.93s
```

**Status:** ✅ 72/72 Pass (59 pré-existentes + 13 novos desta feature)

### DAG import (esperado falhar)

```text
$ python3 -c "import dags.ingestao_legal_dag"
ModuleNotFoundError: No module named 'airflow'
```

**Status:** ⚠️ Esperado — confirma a premissa da Decision 4 do DESIGN; `dags/` não está em nenhum caminho de import de `tests/`.

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | O PDF citado no BRAINSTORM (`resolucao-tcu-n389-de-24-junho-2026.pdf`) não existe mais neste ambiente — era de uma sessão anterior com scratchpad diferente | Busquei e baixei um PDF real equivalente (Resolução TCU nº 388/2026, mesmo tema — homologação de metodologia CBS/IBS) via `curl`, já corrigido no DEFINE/DESIGN antes do build começar | +5m |
| 2 | Reaproveitar `ARTIGO_RE` (case-insensitive) de `ast_parser.py` causou falso positivo: "art. 353" (referência cruzada em minúsculo, dentro do Art. 11) virou um "Art. 353" fantasma porque `pdftotext -layout` quebra linha por largura de página, não por parágrafo semântico — HTML nunca tinha esse problema (cada `<p>` já é uma unidade completa) | Criei `ARTIGO_DEFINICAO_RE` case-sensitive (exige "Art" maiúsculo) só para este parser; confirmado por inspeção linha a linha do PDF real que o documento usa "Art. N" maiúsculo só para definição e "art. N" minúsculo só para referência cruzada | +10m |
| 3 | Título de Seção (`Seção I` / `Da homologação das metodologias`) usa Title Case, não all-caps como o título de Capítulo — uma heurística "linha toda maiúscula = descartar" não pegaria esses títulos de Seção, que vazariam para dentro do texto do artigo anterior | Reaproveitei o mesmo padrão `aguardando_titulo_para` já usado em `ast_parser.py` para o HTML: qualquer linha logo após um header (`HEADER_RE`) que não seja um novo Artigo é descartada, independente de maiúscula/minúscula | +8m |
| 4 | Bloco de assinatura final ("TCU, Sala das Sessões..." / "VITAL DO RÊGO" / "Presidente") vazava para dentro do texto do Art. 16 (nenhum header/artigo novo vem depois dele para encerrar a captura) | Adicionado um `break` explícito ao detectar "sala das sess" (case-insensitive) — fim do conteúdo normativo | +5m |
| 5 | `executar_pipeline()` estava hardcoded para `parse_lei` (Planalto/HTML) — a DAG precisava de uma forma de usar `parse_resolucao` para o TCU sem duplicar toda a orquestração scrape→parse→chunk→embed→index | Adicionei `parser: Callable[..., Lei] = parse_lei` como parâmetro keyword-only com default — mudança aditiva, backward-compatible, todos os testes/chamadas existentes de `executar_pipeline` continuam passando sem alteração | +5m |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `ingestion/pipeline.py` modificado (não estava no File Manifest do DESIGN) | Descoberto durante o build: sem parametrizar o `parser`, a DAG precisaria duplicar `executar_pipeline()` inteira só para trocar uma chamada — pior que uma mudança aditiva de 1 parâmetro | Nenhum no comportamento do Planalto (default preserva `parse_lei`); permite reaproveitar 100% da orquestração para TCU |
| `dags/ingestao_legal_dag.py`: `ingest_planalto()`/`ingest_tcu()` chamam `executar_pipeline()` diretamente (duas tasks paralelas independentes) em vez do único `@task parse_chunk_embed_index` esboçado no Pattern 3 do DESIGN | O pseudocódigo do DESIGN referenciava uma função `processar_e_indexar()` que não existe no código real — corrigido durante o build para usar a função que de fato existe (`executar_pipeline`), evitando inventar uma API fictícia só para a DAG parecer mais enxuta | Nenhum — mais simples e mais correto; cada task já é testável indiretamente via `executar_pipeline`, que tem cobertura de teste real |
| `.github/workflows/ci.yml` modificado (não estava no File Manifest) | Os novos testes de `TCUScraper` exercitam `pdftotext` de verdade — sem `poppler-utils` instalado explicitamente, CI poderia falhar dependendo da imagem do runner | Nenhum risco — passo idempotente, só adiciona uma dependência de sistema já documentada no DESIGN (Decision 2) |

---

## Blockers

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| `apache-airflow` não instalável neste sandbox | Nenhuma ação local possível — `dags/ingestao_legal_dag.py` só será exercitado de fato num Cloud Composer real (decisão explícita, não um blocker a resolver aqui) | Usuário (decisão de negócio: quando provisionar Composer) |
| `dags/ingestao_legal_dag.py` nunca foi executado, só revisado | Provisionar um ambiente Cloud Composer real (fora de escopo desta feature, custo de infraestrutura contínuo) e fazer o primeiro `airflow dags trigger ingestao_legal_taxreformai` | Usuário |
| `QdrantIndexer`/`FastEmbedHybridEmbedder` (herdados da feature anterior) continuam não exercitados contra Qdrant Cloud/`fastembed` reais | Mesmo blocker de `PIPELINE_INGESTAO_LEGAL` — `qdrant-client`/`fastembed`/`google-cloud-storage` não instaláveis neste sandbox | Usuário |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path — PDF real do TCU → chunks corretos, hierarquia preservada, metadados de origem presentes | ✅ Pass | `test_at001_pdf_tcu_ate_qdrant_sem_modificar_chunker`: 16 artigos, chunks > 0, 0 erros; `test_at001_happy_path_todos_os_16_artigos_capturados` confirma os 16 números exatos |
| AT-002 | Error case — PDF corrompido não quebra silenciosamente nem indexa chunk vazio | ✅ Pass | `test_at002_pdf_corrompido_levanta_erro_claro` (scraper) + `test_at002_error_case_texto_sem_nenhum_artigo` (parser) |
| AT-003 | Edge case — parágrafo único (sem numeração de §) reconhecido corretamente | ✅ Pass | `test_at003_edge_case_paragrafo_unico_com_incisos` (Art. 2) + `test_at003_edge_case_multiplos_paragrafos_numerados` (Art. 9, §§1-3) — ambos contra o PDF real |

---

## Success Criteria (do DEFINE) — Verificação

| Critério | Status | Evidência |
|----------|--------|-----------|
| `TCUScraper` baixa/processa uma Resolução TCU real e extrai texto via `pdftotext -layout` | ✅ | `test_at001_extrai_texto_real_do_pdf_via_pdftotext` — PDF real de 388/2026 |
| 100% dos artigos/parágrafos/incisos do PDF de teste estruturados corretamente, sem achatar hierarquia | ✅ | 16/16 artigos, incisos e parágrafos corretos (incluindo o caso de referência cruzada que quase corrompeu o parsing) |
| Chunks do TCU passam pelo `chunker.py` existente sem modificação | ✅ | `chunker.py` não foi tocado nesta feature — `git diff` confirma zero alteração no arquivo |
| `dags/ingestao_legal_dag.py` existe com sintaxe real do Airflow, documentado como não executável neste sandbox | ✅ | Arquivo criado; `ModuleNotFoundError: apache-airflow` confirmado; comentário no topo do arquivo documenta a decisão |

---

## Final Status

### Overall: 🔄 IN PROGRESS (código completo e testado; execução real da DAG pendente de Cloud Composer)

**Completion Checklist:**

- [x] Todos os arquivos do manifest criados (8/8) + 1 extra justificado (`ci.yml`)
- [x] Lint (`ruff`) passa
- [x] Testes automatizados passam (13/13 novos, 72/72 na suíte inteira)
- [x] AT-001, AT-002, AT-003 verificados contra PDF real (não fixture sintética)
- [x] `chunker.py`/`chunk_models.py` confirmados intocados (promessa do DEFINE)
- [ ] Execução real de `dags/ingestao_legal_dag.py` num Cloud Composer (bloqueado — infraestrutura não provisionada, decisão de negócio pendente)

---

## Next Step

**Para desbloquear a execução real da DAG:**
1. Decidir se/quando provisionar um Cloud Composer real (custo contínuo — decisão do usuário, não técnica)
2. Se sim: `pip install apache-airflow` num ambiente com controle (fora deste sandbox), validar `dags/ingestao_legal_dag.py` localmente antes do deploy
3. Deploy da DAG no bucket do Composer, `airflow dags trigger ingestao_legal_taxreformai`

**Independente disso:** `/ship .claude/sdd/features/DEFINE_INGESTAO_TCU_E_ETL_AIRFLOW.md`
