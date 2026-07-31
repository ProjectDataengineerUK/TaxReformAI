# DESIGN: Anexo XVII — Base de Incidência do Imposto Seletivo

> Technical design for implementing ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA (posição 16/17 do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA |
| **Date** | 2026-07-31 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md](./DEFINE_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md) |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│      /v1/tax/simulate — bloco NOVO por item, natureza=MERCADORIA só      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ItemSimulacao.ncm + .embalagem_primaria_consumidor_final (campo novo)    │
│         │                                                                 │
│         ▼                                                                 │
│  api/ncm.py :: digitos_ncm/prefixos_ncm   REAPROVEITADO sem mudança       │
│         │                                                                 │
│         ▼                                                                 │
│  db/repositorio.py :: buscar_incidencia_is_por_prefixo()   1 query, lote  │
│         │            (JOIN imposto_seletivo_incidencia_ncm →             │
│         │             imposto_seletivo_incidencia)                       │
│         ▼                                                                 │
│  api/imposto_seletivo.py :: consultar_com_seguranca()   nunca propaga     │
│         │                                                                 │
│         ▼                                                                 │
│  api/imposto_seletivo.py :: resolver_item()   função PURA                 │
│    ├─ casa prefixo → agrupa por inciso → longest-prefix-wins             │
│    ├─ exceção de código (8802.60.00) exclui, não compete com outro anexo │
│    ├─ avalia condição de embalagem primária (incisos III/IV)             │
│    └─ devolve ResolucaoImpostoSeletivo (situação + categoria + refs)      │
│         │                                                                 │
│         ▼                                                                 │
│  ItemDetalhado.imposto_seletivo (NOVO bloco)   NUNCA um valor monetário   │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘

   motor_calculo/tabela_aliquotas.py INTOCADO — aliq_is continua None/0
   conforme a fase, exatamente como antes desta feature (Decisão 1)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `db/migrations/013_imposto_seletivo_incidencia.sql` | Duas tabelas novas (`imposto_seletivo_incidencia` + `_ncm`) — 6 categorias com código (I-VI), a VII documentada mas nunca inserida | SQL puro, mesmo runner idempotente |
| `api/imposto_seletivo.py` | Política de resolução — irmã de `api/reducao.py`, mas SEM percentual e SEM competição entre categorias (não há sobreposição de NCM entre as 6) | Python puro + 1 import tardio de `db.repositorio` |
| `db/repositorio.py` (extensão) | `PrefixoIncidenciaIS` (dataclass) + `buscar_incidencia_is_por_prefixo` | psycopg |
| `api/schemas_simulate.py` (extensão) | Campo novo `ItemSimulacao.embalagem_primaria_consumidor_final`; novo model `ImpostoSeletivoItem`; campo novo `ItemDetalhado.imposto_seletivo` | Pydantic v2 |
| `api/routers/simulate.py` (extensão) | 4ª consulta em lote (domínio de falha separado das 3 já existentes); resolução só para `natureza=MERCADORIA` | FastAPI |
| `motor_calculo/tabela_aliquotas.py` | **Nenhuma mudança** — `aliq_is` continua exatamente como hoje | Python puro (intocado, ver Decisão 1) |

---

## Key Decisions

### Decisão 1: `motor_calculo/` permanece INTOCADO — esta feature nunca produz um valor de IS

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` já MUST'ou isso, mas a arquitetura precisa tornar essa garantia
estrutural, não só uma promessa de código. `RegraFiscal.aliq_is` já existe e já é usada por
`TaxCalculatorEngine` — o risco é um `/build` "conectar" a nova classificação de incidência a
`aliq_is` por engano (ex. "já que sei que é sujeito ao IS, posso aplicar `aliq_is` da fase").

**Choice:** `api/imposto_seletivo.py` e `ResolucaoImpostoSeletivo` não importam `motor_calculo`
nem `TaxCalculatorEngine`, e `ImpostoSeletivoItem` (o model de resposta) não tem NENHUM campo de
valor monetário ou percentual — só `situacao`, `categoria`, `dispositivo_legal_ref` e as duas
notas de condição. A mesma disciplina de "campo que não existe, não campo `None`" já usada na
Decisão 3 de `ANEXO_XVI_PISO_ALIQUOTA_PROPRIA`.

**Rationale:** Um campo `is_percentual_aplicavel: Decimal | None = None` convidaria a ser
preenchido com `regra.aliq_is` (que hoje é `Decimal(0)` na fase de teste e `None`/indisponível
depois) — o que ASSOCIARIA uma classificação de incidência real a um placeholder de fase que não
tem relação nenhuma com o produto específico. Não ter o campo é a única garantia forte.

**Alternatives Rejected:**
1. Adicionar `is_percentual_aplicavel` sempre `None` por enquanto — rejeitada pelo mesmo motivo da
   Decisão 3 do Anexo XVI: um campo `None` é um convite a ser preenchido errado depois.

**Consequences:**
- Quando uma lei ordinária futura fixar a alíquota do IS para alguma categoria, ESSA feature
  futura decide como conectar o valor — nunca esta.

---

### Decisão 2: Sem competição entre categorias — desempate simplificado (sem `anexo_ordem`/percentual)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** As 10 features de redução por NCM precisaram de um desempate de até 6 componentes
porque os Anexos competem entre si (117 pares de sobreposição). O `/define` verificou que as 6
categorias com código do Anexo XVII (veículos, aeronaves/embarcações, fumígenos, bebidas
alcoólicas, bebidas açucaradas, bens minerais) cobrem faixas de NCM inteiramente disjuntas
(capítulos 87, 88, 24, 22, 26/27 — sem sobreposição observada).

**Choice:** O desempate é só DENTRO de uma categoria (prefixo mais longo vence, mesmo mecanismo de
sempre) — nunca ENTRE categorias. A única "competição" real é a exceção de código (8802.60.00
excluindo uma aeronave/embarcação específica da categoria II) — resolvida com o MESMO booleano
`excecao` já usado nos 10 Anexos NCM, mas sem precisar de catálogo, percentual nem `anexo_ordem`.

**Rationale:** Construir um desempate de 6 componentes para um dado que nunca precisou disso
seria complexidade especulativa — exatamente o tipo de escopo que o projeto evita. Se uma
sobreposição real aparecer no futuro (ex. uma emenda que adicione categoria nova), o `/build`
dessa feature futura pode generalizar o desempate então, com o precedente já estabelecido pelas
Anexos NCM de redução.

**Alternatives Rejected:**
1. Reaproveitar o desempate de 6 componentes das Anexos de redução por antecipação — rejeitada:
   nenhuma sobreposição real existe hoje, e o código extra não teria nenhum caso de teste real
   para provar que funciona.

**Consequences:**
- `resolver_item` é uma função mais simples que `api/reducao.py::resolver_item` — sem
  `anexo_ordem`, sem `percentual_reducao`, sem `itens_correspondentes` cross-categoria.
- Uma asserção na migração 013 confirma programaticamente que os 24 prefixos das 6 categorias não
  se sobrepõem (mesma disciplina de prova, não afirmação, já usada nas migrações anteriores).

---

### Decisão 3: Condição de embalagem primária — GATING, reaproveitando `CONDICAO_NAO_SATISFEITA`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O art. 409, §2º condiciona a sujeição ao IS dos incisos III (fumígenos) e IV
(bebidas alcoólicas) a estarem "acondicionados em embalagem primária... destinada ao consumidor
final". Sem essa informação, nem "sujeito" nem "não sujeito" é uma afirmação segura.

**Choice:** Novo campo declaratório `ItemSimulacao.embalagem_primaria_consumidor_final: bool |
None`, mesmo padrão de `comprador_tipo`/`conteudo_nacional_majoritario`. Quando o NCM casa com
inciso III/IV e o campo é `None` ou `False`, a situação é `CONDICAO_NAO_SATISFEITA` — mesmo nome
de situação já usado em `api/reducao_nbs.py` para o gating do Anexo X/XI, e mesma polaridade
(ausência de informação NUNCA vira "sujeito" nem "não sujeito", vira "não confirmado").

**Rationale:** Reaproveitar o NOME `CONDICAO_NAO_SATISFEITA` (não só o conceito) mantém uma
linguagem consistente entre features que modelam a mesma classe de problema (condição
declaratória que gateia um resultado, sem valor-padrão presumido) — um desenvolvedor que já
conhece `api/reducao_nbs.py` reconhece o padrão aqui sem reaprender.

**Alternatives Rejected:**
1. Presumir `embalagem_primaria=True` por padrão (já que a maioria dos fumígenos/bebidas vendidos
   a consumidor final está em embalagem primária) — rejeitada: seria estimar, exatamente o que o
   projeto nunca faz; um fumígeno vendido a granel para outra indústria não estaria.
2. Não declarar a condição, tratando III/IV como sempre sujeitos — rejeitada: superestimaria a
   incidência para casos legítimos fora da embalagem primária.

**Consequences:**
- `ImpostoSeletivoItem` tem uma situação a mais que um simples booleano "sujeito/não sujeito" —
  mesma disciplina de "nunca colapsar situações diferentes num booleano" já usada em todo o
  projeto desde o Anexo I.

---

### Decisão 4: Exceção de finalidade de uso — NUNCA verificada, mas SEMPRE declarada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` já decidiu (YAGNI, herdado do brainstorm) que a exceção por uso militar/
segurança pública (incisos I e II) não ganha campo de payload nesta feature — mudança de contrato
maior que o escopo pede. Mas isso não pode virar silêncio: um veículo/aeronave marcado como
"sujeito ao IS" sem nenhuma ressalva pareceria uma afirmação mais forte do que o projeto pode
garantir.

**Choice:** As linhas de categoria I e II em `imposto_seletivo_incidencia` carregam uma coluna
`excecao_uso_ref` (texto, não-nula só para I e II) citando o dispositivo da ressalva. Quando o
item resolve como `SUJEITO` e a categoria tem essa coluna preenchida, a resposta inclui uma nota
fixa: a classificação NÃO verifica finalidade de uso, e o item poderia estar isento se fosse
para uso operacional das Forças Armadas/Segurança Pública.

**Rationale:** Mesma disciplina do `tipo_correspondencia=CAPITULO` do lado NCM (a única classe de
correspondência cujo erro é "tributo a menos" é sinalizada explicitamente para revisão manual) —
aqui o erro possível é "declarar sujeito um item que a lei isenta por uso", então a nota existe
para o auditor/controller saber que precisa checar manualmentte, não para o sistema decidir
sozinho.

**Alternatives Rejected:**
1. Adicionar um campo `uso_operacional_forcas_armadas_seguranca_publica: bool | None` — rejeitada
   nesta feature (decisão já tomada no `/define`/brainstorm), mas deixada registrada como extensão
   natural e de baixo custo para uma feature futura, se o produto precisar.

**Consequences:**
- `SituacaoImpostoSeletivo.SUJEITO` para veículos/aeronaves nunca é uma afirmação absoluta — é
  "sujeito, sem verificar a exceção de uso", e a resposta deixa isso textualmente claro.

---

### Decisão 5: Exceção de código (8802.60.00) modelada com o MESMO booleano `excecao` do lado NCM

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** A categoria II inclui `8802` "exceto o código `8802.60.00`" — uma exclusão por CÓDIGO
específico, diferente da exceção de USO (Decisão 4). Isso é estruturalmente idêntico ao mecanismo
`excecao` já usado nos 10 Anexos NCM (ex. foie gras excluído do item 19 do Anexo I).

**Choice:** `imposto_seletivo_incidencia_ncm.excecao BOOLEAN` — quando o prefixo mais específico
que casa com o código é uma linha de exceção, a situação é `NAO_SUJEITO` (não
`EXCLUIDA_EXPRESSAMENTE`, porque aqui não há um segundo Anexo disputando o mesmo código; a exceção
simplesmente remove o código da base de incidência, ponto final).

**Rationale:** Reaproveitar o booleano já validado em 5 features anteriores é mais barato e mais
testado do que inventar um mecanismo novo para o mesmo problema.

**Alternatives Rejected:**
1. Um enum `SituacaoImpostoSeletivo.EXCLUIDO_EXPRESSAMENTE`, espelhando `EXCLUIDA_EXPRESSAMENTE`
   do lado NCM — rejeitada: lá a distinção importa porque o cliente quer saber "excluído DESTE
   Anexo, mas incluído por outro" (produto continua tributado, só que por outro dispositivo).
   Aqui não há outro Anexo — "excluído" e "fora da base" são a mesma coisa na prática, então
   `NAO_SUJEITO` já comunica isso sem inventar uma quinta situação.

**Consequences:**
- Uma linha de teste dedicada garante que `8802.60.00` resolve `NAO_SUJEITO` mesmo casando com o
  prefixo `8802` — mesma disciplina de "nunca presumir, sempre testar" já usada para o Capítulo 6
  do Anexo XV.

---

### Decisão 6: `qual bloco da resposta` — novo campo `ItemDetalhado.imposto_seletivo`, paralelo a `reducao`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-31 |

**Context:** O `/define` deixou em aberto (Open Question 3) onde o sinalizador vive na resposta.

**Choice:** Novo campo `ItemDetalhado.imposto_seletivo: ImpostoSeletivoItem | None`, preenchido
nos DOIS ramos do laço por item (mercadoria e serviço) — `None`/`NAO_APLICAVEL` para serviço,
nunca por default do model.

**Rationale:** Mesmo padrão já usado por `reducao` (bloco por item, dentro de `ItemDetalhado`) —
o dado É por item (depende do NCM daquele item específico), diferente do piso do Anexo XVI (que
era por requisição). Reaproveitar a mesma posição estrutural que `reducao` já ocupa reduz a
superfície de decisão nova.

**Alternatives Rejected:**
1. Embutir dentro do próprio bloco `reducao` (já que os dois são "bloco de classificação fiscal
   por item") — rejeitada: `reducao` é especificamente sobre os Anexos de CBS/IBS; o IS é um
   tributo diferente (art. 153, VIII da CF, não art. 156-A/195 do IBS/CBS) — misturar os dois
   blocos obscureceria qual tributo cada situação descreve.

**Consequences:**
- `ItemDetalhado` ganha um segundo bloco de classificação fiscal, ao lado de `reducao` — ambos
  seguem a mesma convenção (`situacao` como string, nunca um booleano solto).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `db/migrations/013_imposto_seletivo_incidencia.sql` | Create | Tabelas `imposto_seletivo_incidencia`/`_ncm`; seed das 6 categorias com código (24 prefixos); prova de não-sobreposição | @database-reviewer | None |
| 2 | `db/repositorio.py` | Modify | `PrefixoIncidenciaIS` (dataclass) + `buscar_incidencia_is_por_prefixo` (append) | @database-reviewer | 1 |
| 3 | `api/imposto_seletivo.py` | Create | `SituacaoImpostoSeletivo`, `ResolucaoImpostoSeletivo`, `ConsultaImpostoSeletivo`, `consultar_com_seguranca`, `resolver_item` (Decisões 1-5) | @python-developer | 2 |
| 4 | `api/schemas_simulate.py` | Modify | `ItemSimulacao.embalagem_primaria_consumidor_final`; novo model `ImpostoSeletivoItem`; `ItemDetalhado.imposto_seletivo` | @python-developer | None |
| 5 | `api/routers/simulate.py` | Modify | 4ª consulta em lote; dispatch por `natureza` (só MERCADORIA); popula o bloco nos dois ramos do laço | @python-developer | 2, 3, 4 |
| 6 | `tests/test_imposto_seletivo.py` | Create | Unit tests de `resolver_item` — AT-001 a AT-008 (função pura, seed lido da migração 013) | @test-generator | 3 |
| 7 | `tests/test_imposto_seletivo_db.py` | Create | Integration tests contra Postgres real (CI) — schema, contagens, não-sobreposição | @test-generator | 1, 2 |
| 8 | `tests/test_api_simulate_imposto_seletivo.py` | Create | E2E via `TestClient` + pool fake — AT-009 (zero regressão), fluxo completo | @test-generator | 4, 5 |
| 9 | `scripts/verificar_imposto_seletivo_producao.py` | Create | Verificação real contra Cloud SQL — mesmo padrão dos scripts anteriores | @database-reviewer | 1, 2 |
| 10 | `.github/workflows/migrar_banco.yml` | Modify | Novo input `verificar_imposto_seletivo` + step | @ci-cd-specialist | 9 |
| 11 | `.github/workflows/deploy.yml` | Modify | Nova chamada de smoke test (veículo sujeito ao IS) | @ci-cd-specialist | 5 |

**Total Files:** 11

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|-----------------|
| @database-reviewer | 1, 2, 9 | Schema PostgreSQL — mesmo agente das 6 migrações anteriores |
| @python-developer | 3, 4, 5 | Python puro / API — mesmo agente de `api/reducao.py`/`api/ipi.py` |
| @test-generator | 6, 7, 8 | Testes pytest, padrão já estabelecido |
| @ci-cd-specialist | 10, 11 | Workflows do GitHub Actions |
| @security-reviewer | (revisão, não arquivo) | Recomendado antes do `/ship` — `embalagem_primaria_consumidor_final` é mais um campo autodeclarado que afeta classificação fiscal, mesma classe de risco já sinalizada para os campos declaratórios anteriores |

---

## Code Patterns

### Pattern 1: `api/imposto_seletivo.py` — situação e resolução

```python
"""Resolve a base de incidência do Imposto Seletivo (LCP 214/2025, art. 409,
§§1º-2º, Anexo XVII) — NUNCA calcula valor de IS; `motor_calculo/
tabela_aliquotas.py` permanece a única fonte de `aliq_is`, intocado por este
módulo (Decisão 1 do DESIGN).

Irmão de `api/reducao.py`, mas mais simples: as 6 categorias com código NCM
(veículos, aeronaves/embarcações, fumígenos, bebidas alcoólicas, bebidas
açucaradas, bens minerais) cobrem faixas disjuntas — sem desempate entre
categorias, só dentro de uma (Decisão 2). A condição de embalagem primária
(fumígenos/bebidas alcoólicas, art. 409 §2º) usa o MESMO mecanismo de gating
e o MESMO nome de situação (`CONDICAO_NAO_SATISFEITA`) que
`api/reducao_nbs.py` já usa para o Anexo X (Decisão 3).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm

logger = logging.getLogger("api.imposto_seletivo")


class SituacaoImpostoSeletivo(StrEnum):
    SUJEITO = "SUJEITO"
    CONDICAO_NAO_SATISFEITA = "CONDICAO_NAO_SATISFEITA"
    NAO_SUJEITO = "NAO_SUJEITO"
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaImpostoSeletivo:
    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResolucaoImpostoSeletivo:
    situacao: SituacaoImpostoSeletivo
    categoria: str | None = None
    dispositivo_legal_ref: str | None = None
    # Não-nulo só nos incisos III/IV — citado SEMPRE que a categoria exige a
    # condição, informada ou não (mesma disciplina de `dispositivo_legal_
    # comprador` do lado NCM).
    condicao_embalagem_primaria_ref: str | None = None
    # Não-nulo só nos incisos I/II — SEMPRE citado quando a categoria casa,
    # porque a exceção de uso NUNCA é verificada (Decisão 4).
    excecao_uso_ref: str | None = None

    @property
    def aplicavel(self) -> bool:
        return self.situacao not in (
            SituacaoImpostoSeletivo.CONSULTA_INDISPONIVEL,
            SituacaoImpostoSeletivo.NCM_NAO_RECONHECIDO,
        )


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaImpostoSeletivo:
    """Nunca levanta — mesma disciplina de `api/reducao.py::consultar_com_seguranca`."""
    if pool is None:
        return ConsultaImpostoSeletivo(disponivel=False)
    if not prefixos:
        return ConsultaImpostoSeletivo(disponivel=True)

    try:
        from db.repositorio import buscar_incidencia_is_por_prefixo

        with pool.connection() as conexao:
            return ConsultaImpostoSeletivo(
                disponivel=True,
                linhas=buscar_incidencia_is_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar a base de incidência do Imposto Seletivo "
            "(Anexo XVII) — a simulação segue sem classificar o item"
        )
        return ConsultaImpostoSeletivo(disponivel=False)


def resolver_item(
    natureza: str,
    ncm: str,
    consulta: ConsultaImpostoSeletivo,
    embalagem_primaria_consumidor_final: bool | None = None,
) -> ResolucaoImpostoSeletivo:
    """Função pura — mesma ordem de guardas de `api/reducao.py::resolver_item`."""
    if natureza != "MERCADORIA":
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.CONSULTA_INDISPONIVEL)

    # Agrupa por INCISO (categoria) — sem desempate entre categorias
    # (Decisão 2): faixas disjuntas, provado pela migração 013.
    por_inciso: dict[int, list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        if codigo.startswith(linha.prefixo):
            por_inciso[linha.inciso].append(linha)

    if not por_inciso:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_SUJEITO)

    # Só uma categoria deveria ter candidatos (faixas disjuntas) — se mais de
    # uma aparecer (dado inesperado), a menor inciso vence, de forma
    # determinística, e o caso vira um teste de regressão, não um silêncio.
    inciso_vencedor = min(por_inciso)
    vencedora = max(por_inciso[inciso_vencedor], key=lambda linha: len(linha.prefixo))

    if vencedora.excecao:
        return ResolucaoImpostoSeletivo(SituacaoImpostoSeletivo.NAO_SUJEITO)

    if vencedora.condicao_embalagem_primaria_ref is not None and not embalagem_primaria_consumidor_final:
        return ResolucaoImpostoSeletivo(
            situacao=SituacaoImpostoSeletivo.CONDICAO_NAO_SATISFEITA,
            categoria=vencedora.categoria,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            condicao_embalagem_primaria_ref=vencedora.condicao_embalagem_primaria_ref,
        )

    return ResolucaoImpostoSeletivo(
        situacao=SituacaoImpostoSeletivo.SUJEITO,
        categoria=vencedora.categoria,
        dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
        condicao_embalagem_primaria_ref=vencedora.condicao_embalagem_primaria_ref,
        excecao_uso_ref=vencedora.excecao_uso_ref,
    )
```

### Pattern 2: Migração — schema e seed

```sql
-- 013_imposto_seletivo_incidencia.sql
-- Base de incidência do Imposto Seletivo (art. 409, §§1º-2º, Anexo XVII).
-- NUNCA uma alíquota — motor_calculo/tabela_aliquotas.py permanece intocado.

CREATE TABLE imposto_seletivo_incidencia (
    inciso                     SMALLINT PRIMARY KEY CHECK (inciso BETWEEN 1 AND 7),
    categoria                  TEXT NOT NULL,
    dispositivo_legal_ref      TEXT NOT NULL,
    -- Não-nulo só nos incisos III (fumígenos) e IV (bebidas alcoólicas).
    condicao_embalagem_primaria_ref TEXT,
    -- Não-nulo só nos incisos I (veículos) e II (aeronaves/embarcações).
    excecao_uso_ref            TEXT
);

CREATE TABLE imposto_seletivo_incidencia_ncm (
    inciso    SMALLINT NOT NULL REFERENCES imposto_seletivo_incidencia (inciso),
    prefixo   VARCHAR(8) NOT NULL CHECK (prefixo ~ '^[0-9]+$' AND length(prefixo) IN (4, 6, 8)),
    excecao   BOOLEAN NOT NULL DEFAULT FALSE,
    texto_ncm TEXT NOT NULL,
    UNIQUE (inciso, prefixo)
);

CREATE INDEX idx_imposto_seletivo_incidencia_ncm_prefixo
    ON imposto_seletivo_incidencia_ncm (prefixo);

INSERT INTO imposto_seletivo_incidencia
       (inciso, categoria, dispositivo_legal_ref, condicao_embalagem_primaria_ref, excecao_uso_ref) VALUES
 (1, 'Veículos', 'LCP 214/2025, art. 409, §1º, I, Anexo XVII', NULL,
  'LCP 214/2025, Anexo XVII — ressalvados veículos de uso operacional das Forças Armadas/Segurança Pública'),
 (2, 'Embarcações e aeronaves', 'LCP 214/2025, art. 409, §1º, II, Anexo XVII', NULL,
  'LCP 214/2025, Anexo XVII — ressalvadas aeronaves/embarcações de uso operacional das Forças Armadas/Segurança Pública'),
 (3, 'Produtos fumígenos', 'LCP 214/2025, art. 409, §1º, III, Anexo XVII',
  'LCP 214/2025, art. 409, §2º — só em embalagem primária destinada ao consumidor final', NULL),
 (4, 'Bebidas alcoólicas', 'LCP 214/2025, art. 409, §1º, IV, Anexo XVII',
  'LCP 214/2025, art. 409, §2º — só em embalagem primária destinada ao consumidor final', NULL),
 (5, 'Bebidas açucaradas', 'LCP 214/2025, art. 409, §1º, V, Anexo XVII', NULL, NULL),
 (6, 'Bens minerais', 'LCP 214/2025, art. 409, §1º, VI, Anexo XVII', NULL, NULL)
ON CONFLICT DO NOTHING;
-- Inciso 7 (concursos de prognósticos e fantasy sport) NUNCA inserido — sem
-- código citável (célula vazia no Anexo XVII), mesma disciplina de todos os
-- itens "sem código" já documentados nas features anteriores.

INSERT INTO imposto_seletivo_incidencia_ncm (inciso, prefixo, excecao, texto_ncm) VALUES
 (1, '8703',     FALSE, '87.03'),
 (1, '870421',   FALSE, '8704.21 (exceto os caminhões)'),
 (1, '870431',   FALSE, '8704.31 (exceto os caminhões)'),
 (1, '87044100', FALSE, '8704.41.00 (exceto os caminhões)'),
 (1, '87045100', FALSE, '8704.51.00 (exceto os caminhões)'),
 (1, '87046000', FALSE, '8704.60.00 (exceto os caminhões)'),
 (1, '87049000', FALSE, '8704.90.00 (exceto os caminhões)'),
 (2, '8802',     FALSE, '8802'),
 (2, '88026000', TRUE,  '8802.60.00 (excluído expressamente)'),
 (2, '8903',     FALSE, '8903 (embarcações com motor)'),
 (3, '2401',     FALSE, '24.01'),
 (3, '2402',     FALSE, '24.02'),
 (3, '2403',     FALSE, '24.03'),
 (3, '2404',     FALSE, '24.04'),
 (4, '2203',     FALSE, '22.03'),
 (4, '2204',     FALSE, '22.04'),
 (4, '2205',     FALSE, '22.05'),
 (4, '2206',     FALSE, '22.06'),
 (4, '2208',     FALSE, '22.08'),
 (5, '22021000', FALSE, '2202.10.00'),
 (6, '2601',     FALSE, '26.01'),
 (6, '27090010', FALSE, '2709.00.10'),
 (6, '27111100', FALSE, '2711.11.00'),
 (6, '27112100', FALSE, '2711.21.00')
ON CONFLICT DO NOTHING;

-- Prova de não-sobreposição (Decisão 2): nenhum prefixo de uma categoria é
-- prefixo (ou é prefixado por) um prefixo de OUTRA categoria — sem isso, a
-- ausência de desempate cross-categoria seria uma afirmação, não um fato.
DO $$
DECLARE conflitos int;
BEGIN
    SELECT count(*) INTO conflitos
    FROM imposto_seletivo_incidencia_ncm a
    JOIN imposto_seletivo_incidencia_ncm b
      ON a.inciso <> b.inciso
     AND (b.prefixo LIKE a.prefixo || '%' OR a.prefixo LIKE b.prefixo || '%');
    IF conflitos > 0 THEN
        RAISE EXCEPTION 'Categorias do Anexo XVII se sobrepõem (% pares) — a Decisão 2 do '
            'DESIGN presumia faixas disjuntas', conflitos;
    END IF;

    IF (SELECT count(*) FROM imposto_seletivo_incidencia) <> 6 THEN
        RAISE EXCEPTION 'esperado 6 categorias com código (I-VI); VII nunca é inserida';
    END IF;
    IF (SELECT count(*) FROM imposto_seletivo_incidencia_ncm) <> 24 THEN
        RAISE EXCEPTION 'esperados 24 prefixos (7+3+4+5+1+4)';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'taxreformai_app') THEN
        EXECUTE 'GRANT SELECT ON imposto_seletivo_incidencia     TO taxreformai_app';
        EXECUTE 'GRANT SELECT ON imposto_seletivo_incidencia_ncm TO taxreformai_app';
    END IF;
END $$;
```

---

## Data Flow

```text
1. Cliente envia ItemSimulacao (natureza=MERCADORIA, ncm="8704.21", ...)
   │
   ▼
2. api/routers/simulate.py agrupa NCMs de itens MERCADORIA, gera prefixos
   candidatos via api/ncm.py (REAPROVEITADO sem mudança)
   │
   ▼
3. 4ª query (buscar_incidencia_is_por_prefixo) — domínio de falha SEPARADO
   das 3 já existentes (IPI, redução NCM, redução NBS)
   │
   ▼
4. Por item: resolver_item() agrupa por inciso, resolve exceção de código,
   avalia condição de embalagem primária
   │
   ├─ SUJEITO (com ou sem excecao_uso_ref) → categoria + dispositivo citados
   ├─ CONDICAO_NAO_SATISFEITA → categoria citada, condição pendente declarada
   ├─ NAO_SUJEITO → nem categoria nem dispositivo (fora da base OU excluído)
   └─ NCM_NAO_RECONHECIDO/CONSULTA_INDISPONIVEL → mesma disciplina de sempre
   │
   ▼
5. ItemDetalhado.imposto_seletivo populado — NUNCA toca total_is/aliq_is
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-------------------|-----------------|
| Cloud SQL (`imposto_seletivo_incidencia`, `imposto_seletivo_incidencia_ncm`) | SQL via `psycopg`, papel `taxreformai_app` (SELECT) | Secret Manager (já configurado) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|-----------------|
| Unit | `resolver_item` (sem banco, seed lido da migração 013) | `tests/test_imposto_seletivo.py` | pytest | AT-001 a AT-008 |
| Integration | Postgres real | `tests/test_imposto_seletivo_db.py` | pytest + Postgres (CI) | Contagens, não-sobreposição, GRANT |
| E2E | `/v1/tax/simulate` | `tests/test_api_simulate_imposto_seletivo.py` | pytest + `TestClient` | AT-009 (zero regressão) |
| Verificação real (produção) | `migrar_banco.yml` + smoke test do `deploy.yml` | `scripts/verificar_imposto_seletivo_producao.py` | psycopg contra Cloud SQL real | Mesmo padrão das 6 features anteriores |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|---------------------|--------|
| Cloud SQL indisponível/GRANT faltando | `consultar_com_seguranca` nunca propaga — `CONSULTA_INDISPONIVEL`, item some do bloco de incidência (nunca afeta CBS/IBS/IPI) | Não |
| NCM malformado | `NCM_NAO_RECONHECIDO` — mesma disciplina do resto do projeto | Não |
| Condição de embalagem primária ausente | `CONDICAO_NAO_SATISFEITA` — não é erro, é resposta de negócio | Não |
| Exceção de uso (militar/segurança) não verificável | Nunca um erro — a resposta declara a limitação via `excecao_uso_ref`, sempre que relevante | Não |

---

## Configuration

Nenhuma — reaproveita `DATABASE_URL`/pool já existentes (`api/db.py`).

---

## Security Considerations

- `embalagem_primaria_consumidor_final` é DECLARATÓRIO, como os campos análogos já existentes — a
  simulação não verifica a embalagem real do produto.
- Nenhum dado pessoal novo.

---

## Observability

| Aspect | Implementation |
|--------|------------------|
| Logging | `logger.exception` em `consultar_com_seguranca`, mesmo padrão do resto do projeto |
| Metrics | Nenhuma |
| Tracing | Nenhum |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|-----------|
| 1.0 | 2026-07-31 | design-agent | Versão inicial. Seis decisões: `motor_calculo/` permanece intocado, sem campo de valor sequer `None` (Decisão 1); desempate simplificado, sem competição entre categorias porque as faixas de NCM são disjuntas — provado por asserção na migração, não afirmado (Decisão 2); condição de embalagem primária reaproveitando o NOME `CONDICAO_NAO_SATISFEITA` já usado em `api/reducao_nbs.py`, para consistência de linguagem entre features de gating (Decisão 3); exceção de uso militar/segurança pública NUNCA verificada mas SEMPRE declarada quando relevante (Decisão 4); exceção de código (8802.60.00) reaproveitando o booleano `excecao` já validado nos 10 Anexos NCM (Decisão 5); bloco novo `ItemDetalhado.imposto_seletivo`, paralelo a `reducao` mas para um tributo diferente (Decisão 6). |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md`
