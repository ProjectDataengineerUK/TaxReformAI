# BUILD REPORT: Anexos IV, V, VI, VII, VIII e IX (redução de 60%) — generalização para 10 Anexos

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NCM |
| **Posição no roadmap** | 13 (segunda da "segunda leva", executada logo após a posição 12) |
| **Date** | 2026-07-30 |
| **Author** | build-agent (duas sessões interrompidas por limite de sessão da API — a primeira antes de qualquer código, a segunda no meio da escrita de `api/`/`motor_calculo/`, com as migrações 009/010 já completas; este relatório e a continuação foram feitos por Claude, na conversa principal, inspecionando o estado final do código e completando os arquivos que ainda faltavam) |
| **DEFINE** | `.claude/sdd/features/DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NCM.md` (Clarity 14/15) |
| **DESIGN** | `.claude/sdd/features/DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NCM.md` (13 decisões, 17 arquivos no manifesto) |

## Summary

Generaliza o mecanismo de redução (shipado nas posições 2 e 12 só para redução A ZERO) para cobrir
também redução PERCENTUAL de 60% — Anexos IV (art. 131, 105 itens), V (art. 132, 29), VI (art. 133
§1º, 81), VII (art. 135, 17), VIII (art. 136, 7) e IX (art. 138, 22 dos 35 itens — os 12 restantes
são NBS, fora de escopo) da LCP 214/2025.

**Achado do `/design` que mudou o desenho inteiro**: os 6 Anexos novos e os 4 já shipados (zero)
NÃO são independentes — 117 pares de prefixo se sobrepõem, 35 deles no MESMO código de 8 dígitos
(ex. `9018.90.99` é XII/9 a zero e 9 itens do Anexo IV a 60%). Resolver em tabelas separadas
aplicaria 60% onde a lei dá zero. A migração 009 unifica tudo numa tabela só + um catálogo de 10
linhas (`anexos_reducao_catalogo`: percentual, ordinal, artigo, condição de comprador por Anexo), e
o desempate de especificidade (antes 4 componentes, só do Anexo I) virou 6 componentes.

Mudanças estruturais principais:
- `db/migrations/009`: cria `anexos_reducao_catalogo`; renomeia `anexos_reducao_zero*` →
  `anexos_reducao*` (segundo rename da mesma tabela em duas features); prova que os 60 itens/151
  prefixos dos 4 Anexos zero sobreviveram ao rename.
- `db/migrations/010`: transcreve os 6 Anexos novos (261 itens, 389 prefixos: 381 inclusões + 8
  exceções), com 7 asserções — inclusive uma prova SQL de que o desempate por especificidade honra
  a remissão que o próprio Anexo VII escreve para os Anexos I e XV (itens 4, 5, 6, 14, 15).
- `motor_calculo/engine.py`: extrai `valor_do_tributo(base, aliquota)` — sem mudança de
  comportamento, só isolando a fórmula que a redução percentual precisa reaplicar.
- `motor_calculo/reducoes.py`: `aplicar_reducao_percentual` (nova) — reduz a ALÍQUOTA antes de
  recalcular CBS/IBS, não o valor já arredondado (evita divergência de 1 centavo). `aplicar_reducao_a_zero`
  mantém assinatura e comportamento.
- `api/reducao_zero.py` → `api/reducao.py` (rename): desempate de 6 componentes; `resolver_item`
  ganha o parâmetro `comprador_tipo`; `_tipo_correspondencia` distingue `CAPITULO` de `PREFIXO`.
- `api/schemas_simulate.py`: `CompradorTipo` (enum); `PayloadSimulacao.comprador_tipo` (novo campo
  de payload, opcional); bloco da resposta `reducao_zero` → `reducao`, **sem alias** — terceiro
  rename do mesmo bloco em três features consecutivas (`cesta_basica` → `reducao_zero` → `reducao`).
- `motor_calculo/regras_fiscais.py`: só comentário — `fonte_legal_reducoes` já era genérico o
  bastante para os 10 Anexos, zero mudança de valor.

## Verificação feita nesta sessão (continuação após a 2ª interrupção)

- `ruff check .` → **All checks passed**
- `python3 -m pytest tests/ -v` → **433 passed, 3 skipped** (era 331 antes desta feature — a
  feature 12, shipada entre a 331 e esta, já tinha subido para 368; esta feature soma +65 líquidos)
- Smoke test manual via `uvicorn` real (`api.main:app`), sem Postgres disponível (sandbox local):
  payload com 3 itens (60%, precedência de Anexo, `comprador_tipo=ORGAO_PUBLICO`) → `200 OK`, bloco
  `reducao` presente com `situacao: "CONSULTA_INDISPONIVEL"` para os três (degradação correta), com
  os campos novos (`percentual_reducao`, `dispositivo_legal_comprador`,
  `zero_por_comprador_disponivel`, `itens_por_capitulo`) presentes no schema

## Estado em que a continuação encontrou o build (2ª interrupção)

As migrações 009 e 010 já estavam completas e bem formadas (verificado por inspeção estrutural:
contagens de linhas batendo com o cabeçalho, blocos `INSERT`/`DO $$` fechando corretamente) — não
foram reescritas. O restante do código Python (`api/`, `motor_calculo/`, testes) já tinha sido
escrito quase por inteiro, mas com referências remanescentes ao nome antigo
(`buscar_reducao_zero_por_prefixo`, `api.reducao_zero`, `ConsultaReducaoZero`/`SituacaoReducaoZero`)
em 2 arquivos que o rename mecânico não tinha alcançado (`tests/test_reducao_db.py`,
`scripts/verificar_reducao_producao.py`), e 3 arquivos do manifesto inteiramente não tocados:
`.github/workflows/migrar_banco.yml`, `.github/workflows/deploy.yml`, `CLAUDE.md`.

## Issues encontrados e corrigidos nesta continuação

### 1. Referências ao módulo/tabela antigos quebravam a coleção de testes

`tests/test_reducao_db.py` importava `buscar_reducao_zero_por_prefixo` de `db.repositorio` — função
que não existe mais (renomeada para `buscar_reducao_por_prefixo` pela migração 009/refactor do
repositório). `scripts/verificar_reducao_producao.py` tinha o mesmo problema, mais `ITENS_ESPERADOS
= 60` (contagem só dos 4 Anexos zero, desatualizada). Corrigido: imports/nomes atualizados, e as
constantes do script recalculadas para os totais reais (321 itens, 508 inclusões, 32 exceções,
somando os 4 Anexos zero + os 6 novos).

### 2. Dois testes tinham premissas que os 6 Anexos novos invalidaram de verdade (não bugs de código)

`test_at010_vizinho_de_prefixo_nao_entra_pela_vizinhanca` testava que códigos "vizinhos" de um
prefixo não entravam por acidente — dois dos três NCMs de exemplo (`10061010`, capítulo 10; e um
terceiro trocado, `85171200`, que por coincidência é um telefone adaptado do Anexo V) passaram a
resolver `APLICADA` de verdade, porque os Anexos VII/15 e IX/10 cobrem os capítulos 10 e 07/10 por
inteiro — cobertura real da lei que não existia antes desta feature, não uma falha de matching.
Substituídos por três NCMs (automóvel, aço, notebook) confirmados fora dos 10 Anexos.

`test_at006_protese_dentaria_e_trufa_nunca_recebem_zero` testava dois casos de exceção operante; um
deles (`07108000`, trufa) na verdade resolve `APLICADA` via Anexo VII/14 a 60% — a exclusão do
Anexo XV/2 ("exceto cogumelos e trufas") não bloqueia o Anexo VII, porque a remissão do VII/14 só
cede ao XV quando o XV realmente cobre o código, e aqui não cobre (está no "exceto"). É o MESMO
mecanismo já sancionado pelo design para o cogumelo (`0709.51.00`). Separado num teste próprio,
`test_trufa_excluida_do_zero_recebe_60_por_cento_via_anexo_vii`, com a explicação no docstring.

### 3. Dois ajustes esperados e já autorizados pelo design

`tipo_correspondencia` de `06031100` mudou de `"PREFIXO"` para `"CAPITULO"` (Decisão do design —
2 dígitos ganhou seu próprio rótulo, distinto de prefixo genérico de 4-8). A mensagem de log da
falha de conexão mudou de "Falha ao consultar os Anexos de redução a zero" para "Falha ao consultar
os Anexos de redução" (lista os 10 nomes). Ambos eram mudanças de VALOR pré-autorizadas pelo design
e pelas instruções desta sessão — só os testes foram atualizados, nenhum código de produção mudou
por causa disso.

### 4. Arquivos do manifesto inteiramente pendentes

`migrar_banco.yml`: input renomeado `verificar_reducao_zero` → `verificar_reducao`, descrição e
comentários atualizados para os 10 Anexos, script apontado para `verificar_reducao_producao.py`.

`deploy.yml`: os dois `jq` existentes apontados para `.reducao` (era `.reducao_zero`); adicionada
uma **quarta** chamada de smoke test, payload próprio (`34011190`, sabão de toucador, Anexo VIII/1),
exigindo `cbs_percentual == 0.36` — prova E2E de que a redução percentual funciona em produção sem
acoplar a nenhum outro tributo/Anexo já verificado.

`CLAUDE.md`: linha da feature na tabela de status (nova, 🔄 Construída); diagrama de estrutura
(migrações 009/010, `api/reducao.py`, `buscar_reducao_por_prefixo`); seção "Banco de dados"
reescrita para os 10 Anexos + catálogo; rodapé com a entrada desta sessão. **Achado à parte,
corrigido nesta continuação**: o `/ship` da feature anterior (posição 12) nunca tinha de fato
commitado a atualização do `CLAUDE.md` (só `.claude/sdd/` foi staged naquele commit) — a linha da
posição 12 ainda dizia "🔄 Construída, falta o deploy" mesmo já shipada. Corrigido de passagem.

## Ainda NÃO verificado (por política, não por omissão)

Nenhum comando executado contra infraestrutura real nesta sessão — política do projeto, nunca
local. Antes do `/ship`:

1. `migrar_banco.yml` com `verificar_reducao=sim` — prova que as migrações 009+010 aplicam sem erro
   contra o Cloud SQL real, e que o papel de runtime lê os 10 Anexos combinados (14 casos no script:
   os 7 herdados da feature anterior + a precedência normativa, o multi-capítulo do Anexo IX e a
   condição de comprador dos Anexos IV/V/VI).
2. `deploy.yml` (`target=api`) — smoke test em produção real, incluindo a quarta chamada nova
   (redução percentual).

**Atenção à ordem**: a migração 009 renomeia tabelas em uso pela feature anterior
(`anexos_reducao_zero*` → `anexos_reducao*`). A ordem correta é `migrar_banco.yml` primeiro,
`deploy.yml` depois — mesma disciplina já estabelecida.

## Final Status

### Overall: ✅ BUILD COMPLETO — ⏳ pendente das verificações contra infraestrutura real

- Todos os 17 arquivos do manifesto do DESIGN presentes e coerentes
- 433/436 testes passando (3 skips pré-existentes, sem Postgres local)
- Lint limpo
- Smoke test manual confirma degradação graciosa correta sem infraestrutura real
- 2 defeitos reais de teste (premissas invalidadas por dado real novo) encontrados e corrigidos
  durante esta continuação — nenhum bug de produção
