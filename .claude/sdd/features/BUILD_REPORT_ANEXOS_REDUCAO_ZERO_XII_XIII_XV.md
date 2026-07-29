# BUILD REPORT: Anexos XII, XIII e XV (redução a zero) — generalização do mecanismo do Anexo I

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_ZERO_XII_XIII_XV |
| **Posição no roadmap** | 12 (primeira da "segunda leva", executada antes das posições 3-11 por decisão do usuário) |
| **Date** | 2026-07-28 |
| **Author** | build-agent (implementação interrompida por limite de sessão da API; este relatório foi completado por inspeção direta do estado final do código, não é uma narrativa ao vivo do processo de build) |
| **DEFINE** | `.claude/sdd/features/DEFINE_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md` (Status: Designed) |
| **DESIGN** | `.claude/sdd/features/DESIGN_ANEXOS_REDUCAO_ZERO_XII_XIII_XV.md` (13 decisões, 15 arquivos no manifesto) |

## Summary

Generaliza o mecanismo de redução a zero já shipado para o Anexo I (`REGRAS_TRIBUTARIAS_CACHE`)
para cobrir mais 3 Anexos da LCP 214/2025 — XII (art. 144, dispositivos médicos, 20 itens),
XIII (art. 145, dispositivos de acessibilidade, 8 itens) e XV (art. 148, hortícolas/frutas/ovos,
6 itens), verificados contra fonte primária (`legis.senado.leg.br`). Nenhuma linha de
`motor_calculo/` mudou — o art. 148 escreve "reduzidas a ZERO" ainda que o cabeçalho do Anexo
diga "100%", então `aplicar_reducao_a_zero` continua sendo a função certa por texto de lei, não
por analogia aritmética.

Mudanças estruturais principais:
- `db/migrations/007`: generaliza o schema do Anexo I via `ALTER` — chave primária vira
  `(anexo, item, sub_item)` (antes só `item`), `api/ncm.py::_COMPRIMENTOS_PREFIXO` passa a aceitar
  `{2,4,5,6,7,8}` (antes `4..8`) para o prefixo de 2 dígitos ("Capítulo 6") do Anexo XV.
- `db/migrations/008`: transcreve os 3 Anexos novos — 34 itens, 56 linhas de prefixo (51
  inclusões + 5 exceções), com 5 `RAISE EXCEPTION` de integridade (contagem por Anexo,
  inclusões/exceções no total, exceção órfã, item sem prefixo nem sub-item, comprimento de
  prefixo fora do conjunto permitido).
- `api/cesta_basica.py` → `api/reducao_zero.py` (renomeado): desempate de sobreposição
  generalizado de 2 para N itens via chave `(len(prefixo), -anexo_ordem, -item, -sub_item)`.
- Bloco da resposta da API: `cesta_basica` → `reducao_zero` **sem alias** (Decisão 8 do design,
  confirmada diretamente com o usuário via pergunta explícita antes do build) — `item` passa de
  `int` para `string` (grafia canônica, ex. `"1.2"`).
- `regras_tributarias_cache`/scripts/testes correspondentes renomeados de `cesta_basica_*` para
  `reducao_zero_*` em todo o projeto (scripts, workflows, testes).

## Verification Results (feitas nesta sessão, diretamente)

- `ruff check .` → **All checks passed**
- `python3 -m pytest tests/ -v` → **368 passed, 3 skipped** (era 331 passed, 3 skipped antes desta
  feature — +37 testes líquidos, considerando que os testes do Anexo I foram ajustados para o
  novo nome de bloco/tipo de `item`, não substituídos)
- Smoke test manual via `uvicorn` real (`api.main:app`), sem Postgres disponível (sandbox local):
  - `POST /v1/tax/simulate` com 2 itens de mercadoria (NCM real do Anexo I e do Anexo XII)
  - Resposta: `200 OK`, bloco `reducao_zero` presente com `situacao: "CONSULTA_INDISPONIVEL"`
    para os dois itens (degradação correta — nunca zera indevidamente sem consulta disponível)
  - `escopo.advertencia` nomeia explicitamente os 4 Anexos (I/125, XII/144, XIII/145, XV/148) e
    avisa que os itens não avaliados podem estar **superestimados** (CBS/IBS na alíquota geral) —
    a direção "perigosa" de degradação que o design registrou como única exceção à regra geral
    "errar para cima é seguro"
  - `regime_vigente.reducao_zero.fonte_legal` cita os 4 artigos/Anexos corretamente

## Manifesto (15 arquivos do DESIGN, conforme `git status`)

Modificados: `api/ncm.py`, `api/routers/simulate.py`, `api/schemas_simulate.py`,
`db/repositorio.py`, `motor_calculo/regras_fiscais.py` (só comentário, sem mudança de lógica),
`.github/workflows/deploy.yml`, `.github/workflows/migrar_banco.yml`, `CLAUDE.md`,
`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.

Renomeados (`git mv` semântico, refletido como rename no `git status`): `api/cesta_basica.py` →
`api/reducao_zero.py`; `scripts/verificar_cesta_basica_producao.py` →
`scripts/verificar_reducao_zero_producao.py`; `tests/test_api_simulate_cesta_basica.py` →
`tests/test_api_simulate_reducao_zero.py`; `tests/test_cesta_basica_db.py` →
`tests/test_reducao_zero_db.py`; `tests/test_cesta_basica_resolucao.py` →
`tests/test_reducao_zero_resolucao.py`.

Novos: `db/migrations/007_generalizar_anexos_reducao_zero.sql`,
`db/migrations/008_anexos_reducao_zero_xii_xiii_xv.sql`.

## Achado fora de escopo, registrado para o `/ship` (não implementado aqui)

O `/design` encontrou que os arts. 144-II e 145-II reduzem a **zero** os Anexos IV e V quando o
comprador é órgão público ou entidade CEBAS — a classificação da posição 13 do roadmap
(`ANEXOS_REDUCAO_PERCENTUAL_NCM`, hoje "60%") está incompleta: para esse comprador específico, a
alíquota é zero, não 60% de redução. Isso não foi implementado nesta feature (fora de escopo,
Anexos IV/V pertencem à posição 13) — fica registrado aqui para o roadmap ser atualizado no
`/ship` desta feature, e para o `/define` da posição 13 tratar explicitamente.

## Ainda NÃO verificado (por política, não por omissão)

Nenhum comando foi executado contra infraestrutura real (Cloud SQL, Qdrant) nesta sessão — política
do projeto, nunca local. Antes do `/ship`:

1. `migrar_banco.yml` com `verificar_reducao_zero=sim` — prova que a migração 007
   (rename) + 008 (dado) aplicam sem erro contra o Cloud SQL real, e que o papel de runtime lê os
   4 Anexos combinados (`scripts/verificar_reducao_zero_producao.py`).
2. `deploy.yml` (`target=api`) — smoke test em produção real precisa confirmar que o rename do
   bloco (`cesta_basica` → `reducao_zero`) não quebra nada que dependa do nome antigo, e que os 3
   Anexos novos resolvem corretamente contra o Cloud SQL real (ex.: um NCM do Anexo XII/XIII/XV
   real recebendo `situacao: "APLICADA"`).

**Atenção à ordem**: a migração 007 renomeia tabelas em uso (`cesta_basica_anexo_i*` →
`anexos_reducao_zero*`). A ordem correta é `migrar_banco.yml` primeiro, `deploy.yml` depois — a
janela entre os dois é aceita (a API antiga cai no `except` de degradação e responde 200 com a
alíquota geral, nunca 5xx), mas não deve ser invertida.

## Final Status

### Overall: ✅ BUILD COMPLETO (verificado por inspeção direta) — ⏳ pendente das 2 verificações
contra infraestrutura real antes do `/ship`

- Todos os 15 arquivos do manifesto do DESIGN presentes e coerentes
- 368/371 testes passando (3 skips pré-existentes, sem Postgres local)
- Lint limpo
- Smoke test manual confirma degradação graciosa correta sem infraestrutura real
