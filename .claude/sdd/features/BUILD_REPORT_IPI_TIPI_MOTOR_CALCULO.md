# BUILD REPORT: IPI/TIPI no Motor de Cálculo

> Relatório de implementação do consumidor de `aliquotas_ipi_tipi` (9231 NCMs já ingeridos e
> verificados no Cloud SQL) em `POST /v1/tax/simulate`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | IPI_TIPI_MOTOR_CALCULO |
| **Date** | 2026-07-27 |
| **DEFINE** | [DEFINE_IPI_TIPI_MOTOR_CALCULO.md](./DEFINE_IPI_TIPI_MOTOR_CALCULO.md) |
| **DESIGN** | [DESIGN_IPI_TIPI_MOTOR_CALCULO.md](./DESIGN_IPI_TIPI_MOTOR_CALCULO.md) |
| **Posição na sequência** | 1 de 11 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Summary

O dado já existia, estava verificado e pago, e não tinha nenhum consumidor: `aliquotas_ipi_tipi`
(migração 004) guardava 9231 códigos NCM → alíquota de IPI enquanto `regime_atual.py` declarava
`TRIBUTOS_INDISPONIVEIS = ("IPI",)` e o `/v1/tax/simulate` nunca consultava a tabela. Esta feature
fecha a lacuna com três camadas de responsabilidade estrita:

1. **`db/repositorio.buscar_ipi_por_ncm`** — SQL puro, uma query por request (`= ANY(%s)`),
   propaga exceção de propósito.
2. **`api/ipi.py`** — a fronteira de política. Normaliza o NCM, captura qualquer falha e mapeia
   tudo para um enum de 5 situações. Nunca levanta.
3. **`api/routers/simulate.py`** — chama uma vez antes do laço, aplica por item, agrega.

O que a feature entrega de fato não é "somar mais um tributo": é **nunca confundir quatro coisas
diferentes**. NT (não tributado na TIPI), NCM ausente, consulta indisponível e item de serviço
colapsariam todos num único `ipi_percentual: null` — e o mais perigoso deles, silenciosamente, em
"alíquota zero". `ipi_situacao` torna a diferença inspecionável por máquina, não por leitura
humana de uma advertência em português.

**Nenhum teste existente precisou de edição.** `tests/test_escopo_e_compensacao.py` (que exige
`"IPI"` em `tributos_nao_incluidos`) e `tests/test_api_simulate.py` passam intactos: sem
`DB_INSTANCE_CONNECTION_NAME`, `get_db_pool()` devolve `None`, a situação é
`CONSULTA_INDISPONIVEL` e o IPI segue não incluído. Era a prova, exigida pelo DESIGN (Decisão 8),
de que a feature é aditiva.

---

## Tasks with Attribution

| # | Arquivo | Ação | Agente | Status |
|---|---------|------|--------|--------|
| 1 | `db/repositorio.py` | Modify | @database-reviewer (padrões) | ✅ `AliquotaIpi` + `buscar_ipi_por_ncm` |
| 2 | `api/ipi.py` | Create | @python-developer (padrões) | ✅ 149 linhas, zero dependência de `psycopg` no import |
| 3 | `api/schemas_simulate.py` | Modify | @python-developer | ✅ 3 campos por item + `total_ipi`/`ipi_nao_resolvido` + `IpiNaoResolvido` |
| 4 | `api/routers/simulate.py` | Modify | @python-developer | ✅ lookup único, aplicação por item, escopo/advertência dinâmicos |
| 5 | `motor_calculo/regime_atual.py` | Modify | @python-developer | ✅ `TRIBUTOS_INDISPONIVEIS = ()`, `RegimeIndisponivelError` removido, 3 comentários reescritos |
| 6 | `tests/test_ipi_resolucao.py` | Create | @test-generator (padrões) | ✅ 29 testes puros |
| 7 | `tests/test_api_simulate_ipi.py` | Create | @test-generator | ✅ 16 testes, AT-001..AT-005 |
| 8 | `tests/test_tipi_db.py` | Modify | @database-reviewer | ✅ +6 testes contra PostgreSQL real |
| 9 | `scripts/verificar_ipi_producao.py` | Create | @gcp-data-architect | ✅ escrito, **não executado** (roda só por workflow) |
| 10 | `.github/workflows/migrar_banco.yml` | Modify | @gcp-data-architect | ✅ input `verificar_ipi` + passo com o papel `taxreformai_app` |
| 11 | `.github/workflows/deploy.yml` | Modify | @gcp-data-architect | ✅ smoke test exige `total_ipi` não-nulo |
| 12 | `CLAUDE.md` | Modify | @python-developer | ✅ tabela de features, regime vigente, estrutura, banco |

**12/12 arquivos do manifesto** (4 novos + 8 modificados). Nenhum arquivo fora do manifesto foi
tocado — em particular, `frontend/` ficou de fora, como o DESIGN determina (todos os campos novos
são aditivos e opcionais; o frontend sequer tipa `regime_vigente` hoje).

Delegação: os agentes especialistas do manifesto não foram invocados como subagentes. Os padrões
de código do DESIGN já estavam completos ao nível de implementação (Patterns 1-5), e a execução
direta evitou o custo de re-derivar contexto que já estava no documento. As decisões que **não**
estavam no DESIGN e precisaram de julgamento estão registradas em "Desvios", não escondidas.

---

## Verification Results

```text
ruff check .   → All checks passed
pytest         → 244 passed, 2 skipped (era 199 passed, 2 skipped antes da feature)
YAML           → migrar_banco.yml e deploy.yml parseiam
```

| Suíte | Resultado |
|-------|-----------|
| `tests/test_ipi_resolucao.py` (novo) | 29 passed — lógica pura, sem banco e sem HTTP |
| `tests/test_api_simulate_ipi.py` (novo) | 16 passed — AT-001..AT-005 via `TestClient` + pool espião |
| `tests/test_tipi_db.py` (+6) | skipped local (sem `DATABASE_URL`), roda no CI contra `postgres:16` |
| `tests/test_escopo_e_compensacao.py` | passed **sem edição** |
| `tests/test_api_simulate.py` | passed **sem edição** |

### Mapa Acceptance Test → teste

| AT | Onde | Asserção-chave | Status |
|----|------|----------------|--------|
| AT-001 | `test_at001_ncm_com_aliquota_soma_total_e_sai_de_tributos_nao_incluidos` | `total_ipi == 32.50` (3,25% de 1000), `fonte_legal_ipi == dispositivo_legal_ref`, `"IPI"` fora de `tributos_nao_incluidos` | ✅ |
| AT-002 | `test_at002_nao_tributado_e_declarado_e_nao_bloqueia_o_total` | `ipi_situacao == "NAO_TRIBUTADO"`, `ipi_percentual is None`, total não cresce, `ipi_nao_resolvido` vazio | ✅ |
| AT-003 | `test_at003_ncm_ausente_falha_so_o_item_e_a_resposta_segue_200` | status **200**, item em `ipi_nao_resolvido`, `total_ipi is None` | ✅ |
| AT-004 | `test_at004_n_ncms_distintos_resolvem_em_exatamente_uma_query` | `len(queries_ipi) == 1`; argumento contém os 3 NCMs distintos normalizados e ordenados | ✅ |
| AT-005 | `test_at005_payload_so_de_servico_nao_abre_conexao` | nenhuma query à TIPI; `ipi_situacao == "NAO_APLICAVEL"` | ✅ |

Mais os dois cenários que o DESIGN pediu por causa das decisões novas: pool `None` → todos os
itens `CONSULTA_INDISPONIVEL` com 200 (`test_sem_pool_nenhum_a_feature_e_aditiva_e_nada_muda`),
e pool que levanta `ConnectionError` → 200, não 5xx, com o resto da simulação intacto
(`test_falha_de_conexao_degrada_para_200_nunca_5xx`).

### Ainda NÃO verificado (por política, não por omissão)

| Verificação | Como rodar | Por que não rodou aqui |
|-------------|------------|------------------------|
| `GRANT SELECT` ao papel `taxreformai_app` | `migrar_banco.yml`, `verificar_ipi=sim` | Infraestrutura real nunca roda local (política do projeto) |
| `total_ipi` não-nulo contra a API pública | `deploy.yml`, smoke test | Idem |
| `buscar_ipi_por_ncm` contra Postgres de verdade | CI (`ci.yml`, container `postgres:16`) | Sem Docker/Postgres neste sandbox — os 6 testes pulam local e rodam no CI |

Pela Decisão 9 do DESIGN, **a feature não está pronta sem as duas primeiras**. Elas são a razão
de existirem: o único modo de falha desta feature é silencioso.

---

## Issues Encontrados

Dois defeitos reais no padrão de código do DESIGN, ambos encontrados pelos testes novos — não por
revisão.

### 1. Payload com todos os NCMs irreconhecíveis acusava o banco de um problema do payload

O `Pattern 2` do DESIGN faz `consultar_ipi_com_seguranca` devolver `disponivel=False` quando a
lista de NCMs está vazia, e `resolver_item` checa `disponivel` **antes** de normalizar. A
combinação produz um resultado errado e, pior, **inconsistente**:

| Payload | Situação do item `ncm="2203"` | Correto? |
|---------|-------------------------------|----------|
| só `"2203"` | `CONSULTA_INDISPONIVEL` | ❌ o banco está ótimo; o código é que não é um NCM |
| `"2203"` + `"22030000"` | `NCM_NAO_ENCONTRADO` | ✅ |

O mesmo item recebia respostas diferentes dependendo de quem estava ao lado dele no payload. E
`CONSULTA_INDISPONIVEL` é acionável ("reprocesse"), então o cliente reprocessaria para sempre um
código que nenhuma TIPI conteria — `2203` é posição, cabeçalho de categoria, não um NCM completo.

**Correção**, em duas partes, implementando a intenção que o próprio DESIGN já declara (Decisão 4
e a linha "NCM em formato não reconhecível → mesmo tratamento, sem consultar o banco" da tabela de
Error Handling):

- `consultar_ipi_com_seguranca` com pool presente e lista vazia devolve `disponivel=True`. Não
  ter **nada** a perguntar é diferente de não **conseguir** perguntar. Nenhuma conexão é aberta
  nos dois casos, então AT-005 e a Decisão 7 continuam satisfeitos.
- Em `resolver_item`, a guarda de formato passa a vir **antes** da de disponibilidade. Um NCM que
  não canoniza para 8 dígitos é `NCM_NAO_ENCONTRADO` mesmo com o banco fora do ar: é propriedade
  do código informado, não do banco.

Coberto por `test_ncm_irreconhecivel_nao_encontra_ate_com_o_banco_fora_do_ar` (parametrizado nas
duas consultas) e `test_ncm_parcial_nao_vira_busca_por_prefixo`.

### 2. Total de um payload inteiramente NT serializava como `"0"`, não `"0.00"`

A Decisão 5 diz textualmente que `Decimal("0.00")` é um total legítimo (payload todo NT), mas o
acumulador começa em `Decimal(0)` e NT contribui `Decimal(0)` — sem nenhuma quantização no
caminho, a resposta saía `"total_ipi": "0"`. Num campo financeiro, `"0"` tem cara de campo não
preenchido; `"0.00"` tem cara do total que de fato é. Corrigido quantizando o total em centavos
(`ROUND_HALF_UP`, a mesma disciplina do engine) no ramo em que ele é um total de verdade.

### 3. `CLAUDE.md` afirmava que ICMS interno e ISS não estavam plugados no endpoint

Achado colateral, fora do escopo da feature mas dentro do arquivo 12 do manifesto. A seção
"Regime tributário vigente" dizia *"**Ainda não plugados em `/v1/tax/simulate`**: o endpoint segue
declarando os dois em `tributos_nao_incluidos`"*. Falso desde `SCHEMA_POSTGRESQL`: o router já
escolhe interno x interestadual por `uf_origem == uf_destino` e ICMS x ISS por `natureza`, e
`tests/test_escopo_e_compensacao.py` prova os dois caminhos. Corrigido junto.

---

## Deviations from Design

| Desvio | Razão |
|--------|-------|
| `consultar_ipi_com_seguranca` devolve `disponivel=True` para lista vazia (o `Pattern 2` devolve `False`) | Issue 1 — o comportamento do padrão contradizia a Decisão 4 e a tabela de Error Handling do próprio DESIGN |
| Ordem das guardas em `resolver_item`: formato antes de disponibilidade | Issue 1 — mesma razão |
| `total_ipi` quantizado em centavos quando é um total completo | Issue 2 — implementa literalmente o `Decimal("0.00")` da Decisão 5 |
| AT-004/AT-005 asseveram "nenhuma query **à TIPI**", não "`pool.connection` nunca chamado" | O audit log usa o **mesmo pool no mesmo request**, então contar `connection()` cru mediria as duas coisas juntas. Que `consultar_ipi_com_seguranca` não abre conexão com lista vazia é provado à parte, em `test_ipi_resolucao.py` |
| `scripts/verificar_ipi_producao.py` escolhe os NCMs por consulta, em vez de fixá-los no código | A TIPI é reeditada por ADE da RFB; um código fixo poderia sumir numa reedição e reprovar o job pelo motivo errado |
| Agentes especialistas não invocados como subagentes | Os `Code Patterns` do DESIGN já estavam no nível de implementação; execução direta evitou re-derivar contexto |

Nenhuma decisão de arquitetura do DESIGN foi reaberta: lookup em lote em `db/repositorio.py`
consumido por `api/routers/simulate.py`, `motor_calculo/` sem infraestrutura, NCM ausente falhando
só o item com 200, falha do Postgres degradando sem 5xx, enum de 5 estados, `normalizar_ncm`, e
`RegimeIndisponivelError` removido — todas implementadas como especificadas.

---

## Segurança

- **Sem SQL dinâmico.** `= ANY(%s)` recebe a lista como parâmetro vinculado. A string que chega ao
  banco passou por `normalizar_ncm` e é sempre `[0-9]{4}\.[0-9]{2}\.[0-9]{2}` — jamais o texto
  bruto do cliente. Um NCM malformado nem chega ao SQL.
- **Sem RLS, deliberadamente.** `aliquotas_ipi_tipi` é dado legal público (decreto), idêntico para
  todo tenant — a mesma decisão já tomada em `regras_tributarias_cache` e registrada na migração
  004.
- **Privilégio mínimo preservado.** Só `SELECT`; nenhum grant novo foi pedido. A escrita continua
  exclusiva do papel admin via `scripts/ingerir_tipi.py`.
- **Sem PII.** NCM e alíquota são dados de produto e de norma pública.

---

## Final Status

### Overall: ✅ BUILD COMPLETO — ⏳ pendente de verificação contra infraestrutura real

- [x] 12/12 arquivos do manifesto
- [x] `ruff check .` limpo
- [x] 244 passed, 2 skipped (+45 testes)
- [x] AT-001..AT-005 cobertos, mais os 2 cenários extras das Decisões 1 e 2
- [x] `test_escopo_e_compensacao.py` e `test_api_simulate.py` passam **sem edição**
- [x] `RegimeIndisponivelError` removido (dead code confirmado por `grep`)
- [ ] `migrar_banco.yml` com `verificar_ipi=sim` — prova o `GRANT` ao papel de runtime
- [ ] `deploy.yml` — smoke test exigindo `total_ipi` não-nulo contra a API pública

## Recomendação

**Rodar as duas verificações pendentes antes de `/ship`.** Não é formalidade: pela Decisão 2, um
`GRANT` faltando ou uma migração não aplicada **não** produz erro em runtime — produz
`CONSULTA_INDISPONIVEL` silencioso, 200, verde, e sem IPI. Os dois passos de workflow são os
únicos lugares do sistema em que esse modo de falha vira ruído. A lição 3 do SHIPPED de
`SCHEMA_POSTGRESQL` (nenhum papel do Cloud SQL é superusuário, ao contrário de Postgres
autogerido) é exatamente sobre config de papel que parecia certa e não era.

Ordem sugerida: `migrar_banco.yml` (`MIGRAR`, `verificar_ipi=sim`, `ingerir_tipi=nao` — já
ingerida) e depois `deploy.yml` (`DEPLOY`, `target=api`).
