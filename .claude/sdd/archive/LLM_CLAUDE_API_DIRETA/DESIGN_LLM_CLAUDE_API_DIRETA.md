# DESIGN: LLM_CLAUDE_API_DIRETA

> Arquitetura e especificação técnica do cliente LLM alternativo via API Claude direta, contorno ao bloqueio real de quota do Vertex AI

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_CLAUDE_API_DIRETA |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
orquestracao/nos/{classificador,extrator_regras,sintetizador}.py
   │  importam MODELO_HAIKU / MODELO_SONNET de cliente.py (SEM MUDANÇA)
   │  chamam deps.cliente_llm.gerar(modelo=MODELO_X, mensagens=[...])
   ▼
orquestracao/dependencias.py :: criar_dependencias_reais(settings)
   │
   ├─ settings.llm_provider == "vertex"  → ClienteVertexAI(project_id, region)
   └─ settings.llm_provider == "direto"  → ClienteAnthropicDireto(api_key)   [DEFAULT]
                                              │
                                              │ traduz MODELO_HAIKU (formato Vertex,
                                              │ "claude-haiku-4-5@20251001") para o
                                              │ formato da API direta
                                              │ ("claude-haiku-4-5-20251001") ANTES
                                              │ de chamar messages.create() —
                                              │ MODELO_SONNET já é idêntico nos dois
                                              ▼
                                    anthropic.Anthropic(api_key=...).messages.create(...)
                                              │
                                              ▼
                                  api.anthropic.com (Claude real, sem Vertex/GCP)
```

**Fronteira dura:** os 5 nós da orquestração e o `Protocol` `ClienteLLM` não mudam. Só o que
existe DENTRO de `orquestracao/llm/`, `orquestracao/config.py` e a fiação de
`orquestracao/dependencias.py` muda.

---

## Components

| Component | Responsibility |
|-----------|-----------------|
| `orquestracao/llm/cliente.py` :: `ClienteAnthropicDireto` | Implementa `ClienteLLM` via `anthropic.Anthropic` (API direta, sem GCP/Vertex); traduz o ID de modelo internamente |
| `orquestracao/llm/cliente.py` :: `_extrair_texto` (novo helper privado) | Elimina a duplicação de extração de bloco de texto entre `ClienteVertexAI` e `ClienteAnthropicDireto` |
| `orquestracao/config.py` :: `OrquestracaoSettings` | Ganha `llm_provider` (`LLM_PROVIDER`, default `"direto"`) e `anthropic_api_key` (`ANTHROPIC_API_KEY`, obrigatória só quando `llm_provider == "direto"`); `GCP_PROJECT_ID` passa a ser obrigatório só quando `llm_provider == "vertex"` |
| `orquestracao/dependencias.py` :: `criar_dependencias_reais` | Escolhe qual `ClienteLLM` instanciar com base em `settings.llm_provider` |
| `.github/workflows/deploy.yml` | Injeta `LLM_PROVIDER`/`ANTHROPIC_API_KEY` no Cloud Run da API |

---

## Decisions (Inline ADRs)

### Decision: Tradução de ID de modelo dentro de `ClienteAnthropicDireto`, não nos nós

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Ao explorar o código real (não assumido no BRAINSTORM/DEFINE), descobri que
`orquestracao/nos/classificador.py`, `extrator_regras.py` e `sintetizador.py` importam
`MODELO_HAIKU`/`MODELO_SONNET` diretamente de `cliente.py` e passam esse literal como o parâmetro
`modelo` de `cliente_llm.gerar(...)`. `MODELO_HAIKU` está no formato Model Garden do Vertex
(`"claude-haiku-4-5@20251001"`, com `@`) — a API direta da Anthropic não reconhece esse formato,
exige `"claude-haiku-4-5-20251001"` (sem `@`). Isso é um conflito real com a constraint do DEFINE
("zero mudança em `orquestracao/nos/`"): se os nós continuam passando o literal Vertex e nada
traduzir, `ClienteAnthropicDireto` chamaria a API direta com um ID de modelo inválido.

**Choice:** `ClienteAnthropicDireto.gerar()` traduz o `modelo` recebido através de um dicionário
privado (`_MAPA_MODELO_PARA_API_DIRETA = {MODELO_HAIKU: "claude-haiku-4-5-20251001"}`) ANTES de
chamar `messages.create()`. `MODELO_SONNET` (`"claude-sonnet-5"`) já é idêntico nos dois formatos,
então não precisa de entrada no mapa — o `.get(modelo, modelo)` cai no próprio valor.

**Rationale:** É a única forma de honrar "zero mudança em `orquestracao/nos/`" com dois formatos
de ID diferentes — a tradução tem que morar no único lugar que já sabe qual provider está ativo:
o próprio cliente concreto.

**Alternatives Rejected:**
1. Mudar `MODELO_HAIKU`/`MODELO_SONNET` para um formato "canônico" neutro (ex.: `"haiku"`) e
   traduzir para o formato de CADA provider — mais simétrico, mas quebraria a constraint
   "zero mudança em `orquestracao/nos/`" indiretamente: os testes existentes
   (`tests/test_nos.py`, `tests/test_grafo_integration.py`) usam `MODELO_HAIKU`/`MODELO_SONNET`
   como chave de `ClienteLLMFake.respostas_por_modelo` — mudar o VALOR da constante já quebraria
   esses testes sem tocar uma linha de código de produção neles, mas ainda seria uma mudança de
   contrato observável não pedida pelo DEFINE.
2. Traduzir no nível de `criar_dependencias_reais` — não funciona, porque o `modelo` só existe no
   momento da chamada (`gerar()`), não na construção do cliente.

**Consequences:**
- Um `modelo` desconhecido (não presente no mapa) passa através sem tradução — se for inválido
  para a API direta, a própria API Anthropic rejeita com um erro real, capturado pelo `except`
  existente e relançado como `LLMIndisponivelError`. Nunca inventa uma tradução, nunca falha em
  silêncio — mesma disciplina de todo o projeto.

---

### Decision: `_extrair_texto` como helper compartilhado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** `ClienteVertexAI.gerar()` e `ClienteAnthropicDireto.gerar()` têm a mesma lógica de
extrair o bloco de texto da resposta (`next((b for b in resposta.content if b.type == "text"),
None)` + levantar `LLMIndisponivelError` se ausente) — os dois SDKs (`AnthropicVertex` e
`Anthropic`) devolvem o mesmo formato de resposta (`resposta.content`, lista de blocos).

**Choice:** Extrair essa lógica para uma função privada `_extrair_texto(resposta, nome_provider)`
no módulo, reusada pelos dois clientes.

**Rationale:** Duas cópias idênticas de 4 linhas já é duplicação real, não hipotética — extrair
agora custa menos do que deixar as duas implementações divergirem silenciosamente no futuro.

**Alternatives Rejected:**
1. Manter a duplicação — rejeitada porque a lógica é IDÊNTICA hoje entre os dois clientes, não
   apenas parecida; não é abstração prematura, é remover cópia real.

**Consequences:**
- `ClienteVertexAI` ganha uma mudança de refactor não pedida pelo DEFINE, mas de baixíssimo risco
  (comportamento idêntico, coberto pelos testes existentes de `ClienteVertexAI` sem alteração).

---

### Decision: `GCP_PROJECT_ID` vira condicional em `OrquestracaoSettings.from_env()`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-04 |

**Context:** Hoje `from_env()` exige `GCP_PROJECT_ID` incondicionalmente. Esse valor só é usado
por `ClienteVertexAI` (confirmado por `grep` — nenhum outro uso em `orquestracao/`). Com
`LLM_PROVIDER=direto` como novo default, exigir `GCP_PROJECT_ID` seria uma barreira artificial
para o caminho que a própria feature existe para destravar.

**Choice:** `GCP_PROJECT_ID` só entra na lista de variáveis obrigatórias quando
`llm_provider == "vertex"`. Da mesma forma, `ANTHROPIC_API_KEY` só é obrigatória quando
`llm_provider == "direto"`. `QDRANT_URL`/`QDRANT_API_KEY` continuam sempre obrigatórias (usadas
por `pesquisador_legal`, independente do provider de LLM).

**Rationale:** Em produção (`deploy.yml`), `GCP_PROJECT_ID` já é injetado incondicionalmente por
outros motivos (bucket GCS, Cloud SQL) — essa mudança não afeta o deploy real, só remove uma
barreira desnecessária para uso local/teste com `LLM_PROVIDER=direto`.

**Alternatives Rejected:**
1. Manter `GCP_PROJECT_ID` sempre obrigatório — mais simples, mas contradiz o próprio objetivo da
   feature (rodar sem depender de nada específico do Vertex quando o provider é `direto`).

**Consequences:**
- `OrquestracaoSettings.gcp_project_id` muda de `str` para `str | None`.

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|---------------|
| 1 | `orquestracao/llm/cliente.py` | Modify | `_extrair_texto` helper, `_MAPA_MODELO_PARA_API_DIRETA`, `ClienteAnthropicDireto` | None |
| 2 | `orquestracao/config.py` | Modify | `llm_provider`/`anthropic_api_key`, `GCP_PROJECT_ID` condicional | None |
| 3 | `orquestracao/dependencias.py` | Modify | `criar_dependencias_reais` escolhe o cliente pelo provider | 1, 2 |
| 4 | `.env.example` | Modify | Documenta `LLM_PROVIDER`/`ANTHROPIC_API_KEY` | None |
| 5 | `.github/workflows/deploy.yml` | Modify | `--set-env-vars` do deploy da API ganha as 2 vars novas | None |
| 6 | `tests/test_llm_cliente.py` | Modify | Testes de `ClienteAnthropicDireto` + tradução de modelo | 1 |
| 7 | `tests/test_dependencias.py` | Create | Testes da seleção de provider em `criar_dependencias_reais` | 2, 3 |

---

## Code Patterns

### `orquestracao/llm/cliente.py` (trechos novos/alterados)

```python
MODELO_HAIKU = "claude-haiku-4-5@20251001"
MODELO_SONNET = "claude-sonnet-5"

_MAPA_MODELO_PARA_API_DIRETA = {
    MODELO_HAIKU: "claude-haiku-4-5-20251001",
}


def _extrair_texto(resposta, nome_provider: str) -> str:
    bloco_texto = next((b for b in resposta.content if b.type == "text"), None)
    if bloco_texto is None:
        raise LLMIndisponivelError(f"Resposta d{nome_provider} sem bloco de texto")
    return bloco_texto.text


class ClienteVertexAI:
    def __init__(self, project_id: str, region: str = "global"):
        from anthropic import AnthropicVertex

        self._client = AnthropicVertex(project_id=project_id, region=region)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        try:
            resposta = self._client.messages.create(
                model=modelo, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            raise LLMIndisponivelError(f"Vertex AI indisponível: {exc}") from exc
        return _extrair_texto(resposta, "o Vertex AI")


class ClienteAnthropicDireto:
    """Real — chama Claude via API direta da Anthropic (console.anthropic.com).
    Contorno ao bloqueio real de quota do Vertex AI Model Garden
    (`LLM_REAL_VERTEX_AI`, 429 RESOURCE_EXHAUSTED sem previsão). Traduz o ID de
    modelo do formato Vertex para o formato da API direta — os nós continuam
    importando MODELO_HAIKU/MODELO_SONNET sem saber qual provider está ativo."""

    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def gerar(self, modelo: str, mensagens: list[dict], max_tokens: int = 1024) -> str:
        modelo_real = _MAPA_MODELO_PARA_API_DIRETA.get(modelo, modelo)
        try:
            resposta = self._client.messages.create(
                model=modelo_real, max_tokens=max_tokens, messages=mensagens
            )
        except Exception as exc:
            raise LLMIndisponivelError(f"API Claude direta indisponível: {exc}") from exc
        return _extrair_texto(resposta, "a API Claude direta")
```

### `orquestracao/config.py` (trecho alterado de `from_env`)

```python
@classmethod
def from_env(cls) -> "OrquestracaoSettings":
    from ingestion.embedding.hybrid_embedder import MODELO_DENSO_PADRAO

    llm_provider = os.environ.get("LLM_PROVIDER", "direto")

    missing = [var for var in ("QDRANT_URL", "QDRANT_API_KEY") if not os.environ.get(var)]
    if llm_provider == "vertex" and not os.environ.get("GCP_PROJECT_ID"):
        missing.append("GCP_PROJECT_ID")
    if llm_provider == "direto" and not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        raise RuntimeError(f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}.")

    return cls(
        gcp_project_id=os.environ.get("GCP_PROJECT_ID"),
        vertex_ai_region=os.environ.get("VERTEX_AI_REGION", "global"),
        qdrant_url=os.environ["QDRANT_URL"],
        qdrant_api_key=os.environ["QDRANT_API_KEY"],
        qdrant_collection_name=os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria"),
        dense_embedding_model=os.environ.get("DENSE_EMBEDDING_MODEL", MODELO_DENSO_PADRAO),
        llm_provider=llm_provider,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
```

### `orquestracao/dependencias.py` (trecho alterado de `criar_dependencias_reais`)

```python
def criar_dependencias_reais(settings: OrquestracaoSettings) -> DependenciasOrquestracao:
    from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
    from ingestion.indexing.qdrant_indexer import QdrantIndexer

    cliente_llm: ClienteLLM
    if settings.llm_provider == "vertex":
        cliente_llm = ClienteVertexAI(
            project_id=settings.gcp_project_id, region=settings.vertex_ai_region
        )
    else:
        cliente_llm = ClienteAnthropicDireto(api_key=settings.anthropic_api_key)

    return DependenciasOrquestracao(
        cliente_llm=cliente_llm,
        qdrant_indexer=QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        ),
        embedder=FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model),
    )
```

### `deploy.yml` (trecho alterado do deploy da API)

```yaml
env:
  API_KEYS: ${{ secrets.API_KEYS }}
  # ... existentes ...
  LLM_PROVIDER: ${{ vars.LLM_PROVIDER || 'direto' }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
run: |
  # ...
  gcloud run deploy "$SERVICE_API" \
    # ... flags existentes ...
    --set-env-vars="^|^API_KEYS=${API_KEYS}|...|LLM_PROVIDER=${LLM_PROVIDER}|ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
```

---

## Environment Variables (novas)

| Variável | Onde vive | Local | Produção |
|----------|-----------|-------|----------|
| `LLM_PROVIDER` | Runtime, Cloud Run API | `direto` (default, não precisa setar) | GitHub Variable ou fixo `direto` no workflow — não é segredo, pode ficar em texto plano |
| `ANTHROPIC_API_KEY` | Runtime, Cloud Run API | valor fictício local (`sk-ant-fake-local`) | GitHub Secret `ANTHROPIC_API_KEY` — criado manualmente pelo usuário no Console da Anthropic (console.anthropic.com), nunca pelo agente |

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `ClienteAnthropicDireto.gerar` — extrai texto, traduz `MODELO_HAIKU`, passa `MODELO_SONNET` sem alteração, erro de rede vira `LLMIndisponivelError`, resposta sem bloco de texto vira `LLMIndisponivelError` | `pytest` + `unittest.mock.patch("anthropic.Anthropic")`, mesmo padrão já usado para `ClienteVertexAI` |
| Unit (regressão) | `ClienteVertexAI` continua funcionando após o refactor de `_extrair_texto` | Testes existentes de `tests/test_llm_cliente.py`, sem alteração de asserção |
| Unit | `criar_dependencias_reais` escolhe `ClienteAnthropicDireto` por default e `ClienteVertexAI` com `LLM_PROVIDER=vertex` | `tests/test_dependencias.py` novo, com `OrquestracaoSettings` construído diretamente (sem `from_env()`, sem precisar de env vars reais) |
| Unit | `OrquestracaoSettings.from_env()` — `GCP_PROJECT_ID` exigido só com `vertex`, `ANTHROPIC_API_KEY` exigido só com `direto` | Reaproveita o padrão de `monkeypatch.setenv` já usado no projeto |
| Real/Manual | `POST /v1/tax/query` respondendo 200 via API Claude direta | Só verificável contra infraestrutura real, pós-deploy — mesma disciplina de `LLM_REAL_VERTEX_AI` |

---

## Quality Gate

```text
[x] Arquitetura clara (diagrama ASCII)
[x] Decisões documentadas com rationale (3 ADRs inline)
[x] File manifest completo (7 arquivos)
[x] Padrões de código prontos para copiar
[x] Estratégia de teste cobre os requisitos do DEFINE
[x] Sem dependência circular
```

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_LLM_CLAUDE_API_DIRETA.md`
