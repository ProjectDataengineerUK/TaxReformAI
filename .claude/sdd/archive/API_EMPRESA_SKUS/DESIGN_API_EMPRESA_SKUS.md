# DESIGN: API de Catálogo de SKUs (empresa_skus)

> Primeira feature CRUD-com-escrita multi-tenant do projeto desde `SCHEMA_POSTGRESQL` — toda a
> fundação de RLS (`sessao_do_tenant`/`resolver_tenant`) já existe e é reaproveitada sem
> modificação. Novo módulo de negócio (`api/empresa_skus.py`, mesmo padrão de `api/ipi.py`), novo
> router, migração 014, e um wiring cirúrgico em `/v1/tax/simulate` para resolver `ncm`/`nbs` a
> partir do `sku` quando ambos vierem ausentes do item.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | API_EMPRESA_SKUS |
| **Date** | 2026-08-01 |
| **Author** | design-agent |
| **Status** | ✅ Shipado 2026-08-03 (ver `SHIPPED_2026-08-03.md`) |

---

## Overview

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│ api/routers/empresa_skus.py │     │ api/empresa_skus.py            │
│  POST   /v1/tax/skus         │────▶│  validar_exclusividade()       │
│  GET    /v1/tax/skus         │     │  parsear_csv()                 │
│  GET    /v1/tax/skus/{cod}   │     │  ConsultaSkus (dataclass)       │
│  PATCH  /v1/tax/skus/{cod}   │     │  consultar_skus_com_seguranca() │
│  DELETE /v1/tax/skus/{cod}   │     │  resolver_ncm_nbs_do_item()      │
│  POST   /v1/tax/skus/upload  │     └───────────────┬──────────────────┘
└───────────────┬──────────────┘                     │
                │                                     │
                ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ db/repositorio.py — SkuCatalogo + criar/listar/buscar/atualizar/  │
│ excluir/upsert_sku + buscar_skus_por_codigo, TODOS via             │
│ sessao_do_tenant(conexao, tenant_id) — RLS obrigatório              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐
│ api/routers/simulate.py     │  ← MODIFICADO: nova consulta em lote
│  (endpoint existente)        │    (mesmo padrão das 4 já existentes:
│                              │    IPI/redução NCM/redução NBS/IS),
│                              │    ANTES do laço por item
└─────────────────────────────┘
```

**Por que `api/empresa_skus.py` (módulo próprio), não lógica direta no router**: mesmo padrão de
`api/ipi.py`/`api/reducao.py` — a resolução (com/sem catálogo, degradação seguro) é lógica de
NEGÓCIO testável isoladamente, o router só faz HTTP (parse do payload, chamar a função, montar a
resposta, traduzir exceção em status code).

---

## Key Decisions

### Decision 1: Migração adiciona `natureza` com `DEFAULT 'MERCADORIA'`, nunca quebra dado existente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** `empresa_skus.ncm_code` é `NOT NULL` hoje; não existe coluna `natureza`. Dois testes
já existentes (`tests/test_schema_postgres.py::test_sku_duplicado_no_mesmo_tenant_e_rejeitado` e
`test_mesmo_sku_em_tenants_diferentes_e_permitido`, da feature `SCHEMA_POSTGRESQL`) inserem linhas
SEM `natureza` (coluna não existe ainda) e SEMPRE com `ncm_code` preenchido.

**Choice:**
```sql
ALTER TABLE empresa_skus ADD COLUMN natureza VARCHAR(10) NOT NULL DEFAULT 'MERCADORIA'
    CHECK (natureza IN ('MERCADORIA', 'SERVICO'));
ALTER TABLE empresa_skus ALTER COLUMN ncm_code DROP NOT NULL;
ALTER TABLE empresa_skus ADD CONSTRAINT empresa_skus_natureza_codigo_exclusivo CHECK (
    (natureza = 'MERCADORIA' AND ncm_code IS NOT NULL AND nbs_code IS NULL) OR
    (natureza = 'SERVICO' AND nbs_code IS NOT NULL AND ncm_code IS NULL)
);
```

**Rationale:** `DEFAULT 'MERCADORIA'` faz o Postgres backfillar toda linha pré-existente com
`natureza='MERCADORIA'` — e como `ncm_code` já era `NOT NULL` antes desta migração (toda linha
existente TEM `ncm_code`) e nenhuma rota jamais escreveu `nbs_code` (a coluna existe desde a 001,
mas zero rota a usava), o `CHECK` de exclusividade é satisfeito por TODA linha pré-existente sem
migração de dado nenhuma. Os dois testes antigos continuam passando sem modificação — nunca
declaram `natureza` explicitamente, e o `DEFAULT` cobre a lacuna.

**Alternatives Rejected:**
1. `natureza` sem `DEFAULT` (`NOT NULL` puro) — rejeitada: quebraria os dois testes existentes e
   qualquer linha real já cadastrada (nenhuma hoje em produção, mas o princípio vale).
2. Migração de dado explícita (`UPDATE empresa_skus SET natureza='MERCADORIA'` antes do `NOT
   NULL`) — desnecessária; `DEFAULT` no `ADD COLUMN` já faz isso atomicamente.

**Consequences:**
- API sempre exige `natureza` explícito no payload de criação (Pydantic `Field` obrigatório) — o
  `DEFAULT` do banco é uma rede de segurança para SQL direto/teste, nunca dependido pela API.

---

### Decision 2: Resolução de `ncm`/`nbs` em `/v1/tax/simulate` distingue 4 situações, nunca conflAta "não cadastrado" com "banco indisponível"

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O DEFINE exige que "SKU não cadastrado, sem `ncm`/`nbs` explícito" resulte em 422 —
mas o `db_pool` pode estar indisponível (`None`, mesmo caminho que IPI/reduções já tratam), o que
é uma causa DIFERENTE de "SKU realmente não existe". Confundir as duas faria o cliente pensar que
precisa cadastrar o SKU quando na verdade o banco está fora do ar (ou vice-versa).

**Choice:** `SituacaoResolucaoSku` com 4 valores: `NAO_NECESSARIO` (payload já trouxe `ncm`/`nbs`,
catálogo nunca consultado para aquele item), `RESOLVIDO_CATALOGO`, `NAO_CADASTRADO` (catálogo
consultado com sucesso, SKU não existe), `CONSULTA_INDISPONIVEL` (banco fora do ar ou
`resolver_tenant` falhou). Mesmo padrão de `SituacaoIpi`/5 estados já usado em `api/ipi.py`.

**Rationale:** Consistência com toda feature anterior deste projeto que já resolve dado externo
por item — nunca um enum de 2 valores (achou/não achou) quando existe uma terceira causa real
(infraestrutura).

**Alternatives Rejected:**
1. Booleano simples `resolvido: bool` — rejeitado, mesma razão de toda feature anterior: esconde
   a causa da falha do cliente que precisa decidir se deve reprocessar.

**Consequences:**
- Router precisa de 2 branches de 422 com mensagens DIFERENTES: uma para "cadastre o SKU ou
  informe ncm/nbs", outra para "consulta ao catálogo indisponível, tente novamente".

---

### Decision 3: `sku_resolvido_do_catalogo: bool` em `ItemDetalhado`, não um bloco novo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** O DEFINE (AT-014) exige que a resposta cite a ORIGEM do `ncm`/`nbs` usado (catálogo
vs. payload).

**Choice:** Um campo booleano simples em `ItemDetalhado`, não um bloco `ItemDetalhado.sku_
resolvido` estruturado como `ReducaoItem`/`ImpostoSeletivoItem`.

**Rationale:** A informação é binária e não carrega citação de dispositivo legal (não é uma
questão de fundamentação jurídica, é metadado técnico de origem de dado) — proporcional ao que
está sendo comunicado, ao contrário de `reducao`/`imposto_seletivo`, que citam artigo/Anexo.

**Consequences:**
- Campo aditivo, `default=False`, preenchido nos DOIS ramos do laço (mesma disciplina de
  `ipi_situacao`/`reducao` — nunca por default silencioso do modelo).

---

### Decision 4: CSV upload processa linha por linha, cada uma sua própria transação (via `upsert_sku`)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** AT-012 exige sucesso parcial (linhas válidas processadas mesmo com outras
inválidas). `sessao_do_tenant` faz commit/rollback por bloco `with`.

**Choice:** O router valida cada linha do CSV em Python (formato de `natureza`/`ncm_code`/
`nbs_code`, campos obrigatórios) ANTES de qualquer chamada ao banco; só linhas válidas chamam
`upsert_sku` (que abre sua PRÓPRIA `sessao_do_tenant`, logo seu próprio commit). Uma falha de
banco numa linha (ex. erro de conexão no meio do arquivo) não desfaz as linhas já commitadas
antes dela.

**Rationale:** Simplicidade sobre performance — para o teto de linhas desta versão (10.000,
síncrono), N round-trips independentes é aceitável e MUITO mais simples que uma transação
multi-linha com savepoints por linha. Se o volume real justificar otimização (batch/`COPY`), é
um problema de PERFORMANCE para revisitar depois, não de CORREÇÃO agora.

**Alternatives Rejected:**
1. Uma transação só para o arquivo inteiro, com `SAVEPOINT` por linha — mais rápido, mas
   complexidade real (gerenciar savepoints, decidir quando dar `RELEASE`/`ROLLBACK TO`) sem
   benefício claro no volume desta versão.

**Consequences:**
- Upload de 10.000 linhas faz até 10.000 round-trips ao Cloud SQL — aceitável para uma operação
  ocasional (cadastro inicial/atualização em lote), não uma chamada de alta frequência.

---

### Decision 5: `db_pool is None` faz TODO endpoint de `empresa_skus` responder 503, nunca degradar

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-08-01 |

**Context:** Em `/v1/tax/simulate`/`/v1/tax/query`, `db_pool is None` é tratado como "audit log
indisponível" — NUNCA derruba o request, porque o cálculo tributário é a função central e o
audit log é subordinado a ele. Em `empresa_skus`, o BANCO É a função central (não existe
"catálogo sem banco").

**Choice:** Todo endpoint do router novo levanta `HTTPException(503)` explicitamente quando
`db_pool is None`, com mensagem clara ("catálogo de SKUs indisponível — Cloud SQL não
configurado neste ambiente").

**Rationale:** Diferente de toda feature anterior deste projeto (todas eram LEITURA de tabela de
referência com degradação aceitável — "alíquota geral" ou "IPI não resolvido" são respostas
válidas), aqui não existe resposta parcial válida para "criar um SKU" sem banco.

**Alternatives Rejected:**
1. Seguir o padrão de degradação silenciosa de `/v1/tax/simulate` — rejeitado, não existe
   equivalente sensato de "CBS geral da fase" para "criar um SKU sem banco".

**Consequences:**
- Primeiro conjunto de endpoints do projeto que trata `db_pool is None` como ERRO do request
  (503), não como situação a declarar na resposta 200 — precedente novo, documentado aqui para
  não ser confundido com a disciplina de degradação das features anteriores.

---

## File Manifest

| # | File | Action | Purpose | Dependencies |
|---|------|--------|---------|--------------|
| 1 | `db/migrations/014_empresa_skus_natureza.sql` | Create | `natureza`, `ncm_code` nullable, `CHECK` de exclusividade | None |
| 2 | `db/repositorio.py` | Modify | `SkuCatalogo` + `criar_sku`/`listar_skus`/`buscar_sku`/`atualizar_sku`/`excluir_sku`/`upsert_sku`/`buscar_skus_por_codigo` | 1 |
| 3 | `api/empresa_skus.py` | Create | `validar_exclusividade`, `parsear_linha_csv`, `ConsultaSkus`, `consultar_skus_com_seguranca`, `SituacaoResolucaoSku`, `resolver_ncm_nbs_do_item` | 2 |
| 4 | `api/schemas_empresa_skus.py` | Create | Payloads/respostas do CRUD + upload | None |
| 5 | `api/routers/empresa_skus.py` | Create | 6 endpoints, `/v1/tax/skus` | 2, 3, 4 |
| 6 | `api/schemas_simulate.py` | Modify | `ItemSimulacao.ncm` opcional; `ItemDetalhado.sku_resolvido_do_catalogo` | None |
| 7 | `api/routers/simulate.py` | Modify | Consulta em lote de SKUs + resolução no laço por item | 3, 6 |
| 8 | `api/main.py` | Modify | `include_router` do novo router | 5 |
| 9 | `requirements-api.txt` | Modify | `python-multipart` (upload de arquivo) | None |
| 10 | `scripts/verificar_empresa_skus_producao.py` | Create | Prova RLS de escrita/leitura pelo papel de runtime contra Cloud SQL real | 2 |
| 11 | `tests/test_empresa_skus.py` | Create | Unit — validação de exclusividade, parsing CSV, resolução (com fakes) | 3, 4 |
| 12 | `tests/test_empresa_skus_db.py` | Create | Integração real contra Postgres (skip sem `DATABASE_URL`) — CRUD via `db/repositorio.py`, RLS de escrita | 2 |
| 13 | `tests/test_api_empresa_skus.py` | Create | E2E via `TestClient` — CRUD + upload | 5 |
| 14 | `tests/test_api_simulate_sku_resolution.py` | Create | E2E — wiring em `/v1/tax/simulate` (AT-014 a AT-017) | 7 |
| 15 | `.github/workflows/migrar_banco.yml` | Modify | +input `verificar_empresa_skus` +step | 10 |

---

## Code Patterns

### `db/migrations/014_empresa_skus_natureza.sql`

```sql
-- API_EMPRESA_SKUS: primeira feature a ESCREVER em empresa_skus (schema e RLS
-- aplicados desde SCHEMA_POSTGRESQL, tabela morta até aqui). Corrige o gap
-- entre o schema (ncm_code sempre obrigatório) e o vocabulário natureza já
-- usado por ItemSimulacao (MERCADORIA | SERVICO).

ALTER TABLE empresa_skus ADD COLUMN natureza VARCHAR(10) NOT NULL DEFAULT 'MERCADORIA'
    CHECK (natureza IN ('MERCADORIA', 'SERVICO'));

ALTER TABLE empresa_skus ALTER COLUMN ncm_code DROP NOT NULL;

ALTER TABLE empresa_skus ADD CONSTRAINT empresa_skus_natureza_codigo_exclusivo CHECK (
    (natureza = 'MERCADORIA' AND ncm_code IS NOT NULL AND nbs_code IS NULL) OR
    (natureza = 'SERVICO' AND nbs_code IS NOT NULL AND ncm_code IS NULL)
);

-- GRANT já concedido pela migração 003 (privilégio mínimo do papel app cobre
-- SELECT/INSERT/UPDATE/DELETE em toda tabela de aplicação, empresa_skus
-- incluída desde a 001) — nenhum GRANT novo necessário aqui.
```

### `db/repositorio.py` — adições

```python
@dataclass(frozen=True)
class SkuCatalogo:
    id: UUID
    tenant_id: UUID
    codigo_sku: str
    descricao: str
    natureza: str
    ncm_code: str | None
    nbs_code: str | None
    created_at: datetime


def criar_sku(
    conexao, tenant_id: UUID, codigo_sku: str, descricao: str,
    natureza: str, ncm_code: str | None, nbs_code: str | None,
) -> SkuCatalogo:
    """Levanta psycopg.errors.UniqueViolation em codigo_sku duplicado no
    mesmo tenant — o router traduz para 409, não esta função."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            """,
            (str(tenant_id), codigo_sku, descricao, natureza, ncm_code, nbs_code),
        )
        return SkuCatalogo(*cur.fetchone())


def listar_skus(conexao, tenant_id: UUID, pagina: int, tamanho_pagina: int) -> tuple[list[SkuCatalogo], int]:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute("SELECT count(*) FROM empresa_skus")
        total = cur.fetchone()[0]
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus ORDER BY created_at DESC, id LIMIT %s OFFSET %s
            """,
            (tamanho_pagina, (pagina - 1) * tamanho_pagina),
        )
        itens = [SkuCatalogo(*linha) for linha in cur.fetchall()]
    return itens, total


def buscar_sku(conexao, tenant_id: UUID, codigo_sku: str) -> SkuCatalogo | None:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus WHERE codigo_sku = %s
            """,
            (codigo_sku,),
        )
        linha = cur.fetchone()
    return SkuCatalogo(*linha) if linha else None


def atualizar_sku(
    conexao, tenant_id: UUID, codigo_sku: str, descricao: str,
    natureza: str, ncm_code: str | None, nbs_code: str | None,
) -> SkuCatalogo | None:
    """Substituição TOTAL das colunas mutáveis — o router monta os valores
    finais (merge do payload PATCH sobre o registro existente) antes de
    chamar esta função, para nunca precisar de SQL dinâmico."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            UPDATE empresa_skus SET descricao=%s, natureza=%s, ncm_code=%s, nbs_code=%s
            WHERE codigo_sku=%s
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            """,
            (descricao, natureza, ncm_code, nbs_code, codigo_sku),
        )
        linha = cur.fetchone()
    return SkuCatalogo(*linha) if linha else None


def excluir_sku(conexao, tenant_id: UUID, codigo_sku: str) -> bool:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute("DELETE FROM empresa_skus WHERE codigo_sku=%s", (codigo_sku,))
        apagado = cur.rowcount > 0
    return apagado


def upsert_sku(
    conexao, tenant_id: UUID, codigo_sku: str, descricao: str,
    natureza: str, ncm_code: str | None, nbs_code: str | None,
) -> tuple[SkuCatalogo, bool]:
    """`(xmax = 0)` é o truque padrão do Postgres para distinguir INSERT de
    UPDATE num só INSERT ... ON CONFLICT — evita um SELECT prévio (condição
    de corrida) só para saber se o SKU já existia."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, codigo_sku) DO UPDATE SET
                descricao = EXCLUDED.descricao, natureza = EXCLUDED.natureza,
                ncm_code = EXCLUDED.ncm_code, nbs_code = EXCLUDED.nbs_code
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at,
                      (xmax = 0) AS foi_criado
            """,
            (str(tenant_id), codigo_sku, descricao, natureza, ncm_code, nbs_code),
        )
        *campos, foi_criado = cur.fetchone()
    return SkuCatalogo(*campos), foi_criado


def buscar_skus_por_codigo(conexao, tenant_id: UUID, codigos_sku: list[str]) -> dict[str, SkuCatalogo]:
    """Lookup em LOTE, escopado por RLS — consumido por `api/empresa_skus.py`
    para o wiring de `/v1/tax/simulate`."""
    if not codigos_sku:
        return {}
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus WHERE codigo_sku = ANY(%s)
            """,
            (list(codigos_sku),),
        )
        linhas = cur.fetchall()
    return {linha[2]: SkuCatalogo(*linha) for linha in linhas}
```

### `api/empresa_skus.py`

```python
"""Resolução de SKU→NCM/NBS sem nunca derrubar /v1/tax/simulate, mesma
disciplina de api/ipi.py. `db_pool is None` aqui É indisponibilidade (nunca
"não cadastrado") — ver Decisão 2 do DESIGN."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm
from api.nbs import digitos_nbs

logger = logging.getLogger("api.empresa_skus")


class SituacaoResolucaoSku(StrEnum):
    NAO_NECESSARIO = "NAO_NECESSARIO"
    RESOLVIDO_CATALOGO = "RESOLVIDO_CATALOGO"
    NAO_CADASTRADO = "NAO_CADASTRADO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"


@dataclass(frozen=True)
class ConsultaSkus:
    disponivel: bool
    por_codigo: dict[str, Any] = field(default_factory=dict)


def consultar_skus_com_seguranca(pool: Any, tenant_identificador: str, codigos_sku: list[str]) -> ConsultaSkus:
    if pool is None:
        return ConsultaSkus(disponivel=False)
    if not codigos_sku:
        return ConsultaSkus(disponivel=True)
    try:
        from db.repositorio import buscar_skus_por_codigo, resolver_tenant

        with pool.connection() as conexao:
            tenant_id = resolver_tenant(conexao, tenant_identificador)
            if tenant_id is None:
                return ConsultaSkus(disponivel=False)
            return ConsultaSkus(
                disponivel=True, por_codigo=buscar_skus_por_codigo(conexao, tenant_id, codigos_sku)
            )
    except Exception:
        logger.exception("Falha ao consultar catálogo de SKUs — declarado na resposta")
        return ConsultaSkus(disponivel=False)


@dataclass(frozen=True)
class ResolucaoSku:
    situacao: SituacaoResolucaoSku
    ncm_efetivo: str | None
    nbs_efetivo: str | None


def resolver_ncm_nbs_do_item(
    natureza: str, ncm_payload: str | None, nbs_payload: str | None,
    sku: str, consulta: ConsultaSkus,
) -> ResolucaoSku:
    """Explícito SEMPRE vence — o catálogo só preenche quando ambos vierem
    ausentes (Decisão herdada do /brainstorm, reafirmada no /define)."""
    if (natureza == "MERCADORIA" and ncm_payload) or (natureza == "SERVICO" and nbs_payload):
        return ResolucaoSku(SituacaoResolucaoSku.NAO_NECESSARIO, ncm_payload, nbs_payload)

    if not consulta.disponivel:
        return ResolucaoSku(SituacaoResolucaoSku.CONSULTA_INDISPONIVEL, ncm_payload, nbs_payload)

    registro = consulta.por_codigo.get(sku)
    if registro is None:
        return ResolucaoSku(SituacaoResolucaoSku.NAO_CADASTRADO, ncm_payload, nbs_payload)

    return ResolucaoSku(
        SituacaoResolucaoSku.RESOLVIDO_CATALOGO,
        ncm_payload or registro.ncm_code,
        nbs_payload or registro.nbs_code,
    )


def validar_exclusividade(natureza: str, ncm_code: str | None, nbs_code: str | None) -> str | None:
    """Devolve a mensagem de erro, ou None se válido. Reaproveitada pelo
    schema Pydantic (criação/edição) E pelo parser de CSV (linha a linha) —
    uma única fonte da regra, nunca duplicada."""
    if natureza == "MERCADORIA":
        if not ncm_code or nbs_code:
            return "natureza=MERCADORIA exige ncm_code preenchido e nbs_code ausente"
    elif natureza == "SERVICO":
        if not nbs_code or ncm_code:
            return "natureza=SERVICO exige nbs_code preenchido e ncm_code ausente"
    return None


@dataclass(frozen=True)
class LinhaCsvValidada:
    numero_linha: int
    codigo_sku: str | None
    descricao: str | None
    natureza: str | None
    ncm_code: str | None
    nbs_code: str | None
    erro: str | None


def parsear_linha_csv(numero_linha: int, linha: dict[str, str]) -> LinhaCsvValidada:
    codigo_sku = (linha.get("codigo_sku") or "").strip()
    descricao = (linha.get("descricao") or "").strip()
    natureza = (linha.get("natureza") or "").strip().upper()
    ncm_bruto = (linha.get("ncm_code") or "").strip()
    nbs_bruto = (linha.get("nbs_code") or "").strip()

    if not codigo_sku or not descricao:
        return LinhaCsvValidada(numero_linha, codigo_sku or None, None, None, None, None, "codigo_sku e descricao são obrigatórios")
    if natureza not in ("MERCADORIA", "SERVICO"):
        return LinhaCsvValidada(numero_linha, codigo_sku, descricao, None, None, None, "natureza deve ser MERCADORIA ou SERVICO")

    ncm_code = digitos_ncm(ncm_bruto) if ncm_bruto else None
    nbs_code = digitos_nbs(nbs_bruto) if nbs_bruto else None
    if ncm_bruto and ncm_code is None:
        return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, None, None, f"ncm_code {ncm_bruto!r} não tem 8 dígitos válidos")
    if nbs_bruto and nbs_code is None:
        return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, None, None, f"nbs_code {nbs_bruto!r} inválido")

    erro = validar_exclusividade(natureza, ncm_code, nbs_code)
    if erro:
        return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, ncm_code, nbs_code, erro)

    return LinhaCsvValidada(numero_linha, codigo_sku, descricao, natureza, ncm_code, nbs_code, None)
```

### `api/routers/simulate.py` — wiring (inserção, não reescrita)

```python
# Quinta consulta, domínio de falha SEPARADO das 4 anteriores — ESCOPADA POR
# TENANT (RLS), diferente de IPI/reduções/IS, que são tabelas públicas. Só os
# SKUs de itens que ainda PRECISAM de resolução entram no lote (ver Decisão 2).
codigos_sku_a_resolver = sorted(
    {
        item.sku
        for item in payload.itens
        if (item.natureza == "MERCADORIA" and not item.ncm)
        or (item.natureza == "SERVICO" and not item.nbs)
    }
)
consulta_skus = consultar_skus_com_seguranca(db_pool, tenant_id, codigos_sku_a_resolver)

# ... dentro do laço `for item in payload.itens:`, ANTES de qualquer uso de
# item.ncm/item.nbs para cálculo:
resolucao_sku = resolver_ncm_nbs_do_item(
    item.natureza, item.ncm, item.nbs, item.sku, consulta_skus
)
if resolucao_sku.situacao is SituacaoResolucaoSku.NAO_CADASTRADO:
    raise HTTPException(422, detail=f"SKU {item.sku!r} não cadastrado e ncm/nbs ausente do item — cadastre o SKU em POST /v1/tax/skus ou informe ncm/nbs explicitamente.")
if resolucao_sku.situacao is SituacaoResolucaoSku.CONSULTA_INDISPONIVEL:
    raise HTTPException(422, detail=f"Catálogo de SKUs indisponível e item {item.sku!r} não informou ncm/nbs — tente novamente ou informe ncm/nbs explicitamente.")

ncm_efetivo = resolucao_sku.ncm_efetivo
nbs_efetivo = resolucao_sku.nbs_efetivo
# Toda leitura de `item.ncm`/`item.nbs` DAQUI EM DIANTE no corpo do laço vira
# `ncm_efetivo`/`nbs_efetivo` — normalizar_ncm/digitos_ncm, resolver_reducao,
# resolver_item (IPI), resolver_imposto_seletivo. `ItemDetalhado.ncm` na
# resposta também usa `ncm_efetivo` (o valor DE FATO usado no cálculo).
```

**Nota para o `/build`**: `codigos_sku_a_resolver`/`consulta_skus` são calculados FORA do laço
(mesmo padrão das outras 4 consultas); a decisão 422 e a substituição `item.ncm→ncm_efetivo`
acontecem DENTRO do laço, na posição mais cedo possível — antes de `normalizar_ncm(item.ncm)` e
`digitos_ncm(item.ncm)`, que hoje são os dois primeiros lugares que leem o campo.

### `api/schemas_simulate.py` — diffs

```python
class ItemSimulacao(BaseModel):
    sku: str
    ncm: str | None = None  # ERA `ncm: str` (obrigatório) — mudança ADITIVA de tipo
    ...

class ItemDetalhado(BaseModel):
    sku: str
    ncm: str
    ...
    # Preenchido nos DOIS ramos (RESOLVIDO_CATALOGO vs. qualquer outra
    # situação) — nunca por default silencioso, mesma disciplina de
    # ipi_situacao/reducao.
    sku_resolvido_do_catalogo: bool = False
```

---

## Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | `api/empresa_skus.py` — `validar_exclusividade`, `parsear_linha_csv` (linhas válidas/inválidas), `resolver_ncm_nbs_do_item` (4 situações, com `ConsultaSkus` fake) | `pytest` |
| Integration (real DB) | `db/repositorio.py` — CRUD completo via as 7 funções novas, RLS de escrita/leitura entre 2 tenants (reafirma A-001 do DEFINE, agora via as funções da API, não só SQL cru como os 2 testes antigos) | `pytest`, skip sem `DATABASE_URL`, roda de verdade no CI |
| E2E | `POST/GET/PATCH/DELETE /v1/tax/skus` + upload CSV via `TestClient` + pool fake | `pytest` + `TestClient` |
| E2E | Wiring em `/v1/tax/simulate` — AT-014 a AT-017 | `pytest` + `TestClient` |
| Regression | Suíte completa (551 testes) sem nenhuma mudança de comportamento em payload que já informa `ncm` explícito | `pytest` |
| Segurança | `security-reviewer` antes do `/ship` (recomendado pelo `/define`) — foco em vazamento cross-tenant no CRUD de escrita | Revisão dedicada |

---

## Quality Gate

```text
[x] Arquitetura clara — módulo de negócio + router + wiring cirúrgico
[x] 5 decisões documentadas com rationale
[x] File manifest completo (15 arquivos)
[x] Padrões de código prontos para copiar
[x] Estratégia de teste cobre os 17 acceptance tests do DEFINE
[x] Sem dependência circular — api/empresa_skus.py não importa api/routers/simulate.py
```

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_API_EMPRESA_SKUS.md`
