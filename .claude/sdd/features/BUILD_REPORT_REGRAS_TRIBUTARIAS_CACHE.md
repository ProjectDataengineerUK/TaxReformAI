# BUILD REPORT: Cesta Básica Nacional (Anexo I) — redução a zero de CBS/IBS por NCM

> Relatório de implementação do schema novo do Anexo I da LCP 214/2025 (art. 125), do override por
> item em `POST /v1/tax/simulate`, e da remoção de `regras_tributarias_cache` como código morto

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REGRAS_TRIBUTARIAS_CACHE |
| **Date** | 2026-07-28 |
| **DEFINE** | [DEFINE_REGRAS_TRIBUTARIAS_CACHE.md](./DEFINE_REGRAS_TRIBUTARIAS_CACHE.md) |
| **DESIGN** | [DESIGN_REGRAS_TRIBUTARIAS_CACHE.md](./DESIGN_REGRAS_TRIBUTARIAS_CACHE.md) |
| **Posição na sequência** | 2 de 11 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Summary

O achado 2 da auditoria era uma tabela sem consumidor (`regras_tributarias_cache`). O DESIGN
mostrou que a resposta certa não era plugá-la em alguém, e sim **removê-la e construir a forma que
o texto legal exige** — a Cesta Básica Nacional (LCP 214/2025, art. 125 e Anexo I): 26 itens de
alimentos com alíquota **zero** de CBS/IBS, hoje cobrados pela alíquota geral da fase.

O que a feature entrega, em três camadas com a mesma disciplina da feature 1
(`db/repositorio.py` → `api/cesta_basica.py` → `api/routers/simulate.py`):

1. **Um só mecanismo de correspondência.** Toda citação do Anexo I — "posição 09.01" (4 dígitos),
   "subposição 1902.1" (5), "1006.20" (6), "0210.99.1" (7), "código 0405.10.00" (8) — é prefixo do
   código de 8 dígitos da mercadoria. Os 20 itens "exatos" e os 6 não-triviais caem no mesmo
   código, e as 19 exceções dos itens 19/20 (foie gras, salmonídeos, atuns, bacalhau) também.
2. **O prefixo é expandido no Python, não no SQL.** `prefixos_ncm("04051000")` gera os 5
   candidatos e a query continua sendo `WHERE prefixo = ANY(%s)` — mesmo idioma da TIPI, índice
   preservado, e o acoplamento "4 a 8 dígitos" travado dos dois lados (a CHECK
   `prefixo_comprimento_valido` recusa no INSERT o que o gerador jamais enxergaria).
3. **A degradação é conservadora, e essa é a diferença central em relação ao IPI.** Lá, o lookup
   indisponível fazia `total_ipi` virar `null`. Aqui ele faz a **alíquota geral** ser aplicada —
   um tributo maior que o devido, nunca menor, que é literalmente o comportamento de antes desta
   feature. Nenhum código de erro novo, nenhum campo de CBS/IBS anulável.

Seis situações (`SituacaoCestaBasica`) impedem que coisas diferentes virem o mesmo `false`. A mais
valiosa é `EXCLUIDA_EXPRESSAMENTE`: "seu produto está na posição 02.07, mas o Anexo I exclui
expressamente o código 0207.43.00" é informação jurídica que o cliente não obteria de outra forma,
e é o oposto de `FORA_DO_ANEXO` para quem revisa uma classificação fiscal.

**Nenhum teste da feature 1 (ou de qualquer feature anterior) precisou de edição** — as 126
asserções de `test_ipi_resolucao.py`, `test_api_simulate_ipi.py`, `test_api_simulate.py`,
`test_escopo_e_compensacao.py`, `test_engine.py`, `test_tabela_aliquotas.py` e
`test_regime_atual.py` passam intactas. A **única exceção**, prevista e autorizada pela Decisão 12,
é `tests/test_schema_postgres.py`, que perde os 2 testes da tabela removida.

---

## Tasks with Attribution

| # | Arquivo | Ação | Agente | Status |
|---|---------|------|--------|--------|
| 1 | `db/migrations/005_cesta_basica_anexo_i.sql` | Create | @database-reviewer (padrões) | ✅ 2 tabelas, 2 CHECKs, seed de 26 itens/95 prefixos, `GRANT SELECT` |
| 2 | `db/migrations/006_remover_regras_tributarias_cache.sql` | Create | @database-reviewer | ✅ `DROP` guardado por checagem de "está vazia?" |
| 3 | `db/repositorio.py` | Modify | @database-reviewer | ✅ +`PrefixoCestaBasica`/`buscar_cesta_basica_por_prefixo`; −`RegraTributariaCache`/`buscar_regra_cache` |
| 4 | `api/ncm.py` | Create | @python-developer | ✅ 49 linhas, sem conhecer IPI nem cesta básica |
| 5 | `api/ipi.py` | Modify | @python-developer | ✅ `normalizar_ncm` delega a `digitos_ncm`; assinatura e comportamento idênticos |
| 6 | `api/cesta_basica.py` | Create | @python-developer | ✅ 181 linhas, 6 situações, nunca levanta |
| 7 | `motor_calculo/reducoes.py` | Create | @python-developer | ✅ 50 linhas, importa só `dataclasses`/`decimal`/`ResultadoCalculo` |
| 8 | `motor_calculo/regras_fiscais.py` | Modify | @python-developer | ✅ `fonte_legal_reducoes: str \| None = None` |
| 9 | `motor_calculo/tabela_aliquotas.py` | Modify | @python-developer | ✅ seed de 2026 (art. 348, III, "a") e 2027-2028 (arts. 344 §ú, I / 347, § 1º, I) |
| 10 | `api/schemas_simulate.py` | Modify | @python-developer | ✅ `CestaBasicaItem`, `CestaBasicaResumo`, `ItemNaoAvaliado` |
| 11 | `api/routers/simulate.py` | Modify | @python-developer | ✅ 1 lookup antes do laço, override por item, agregação, advertência, audit log |
| 12 | `tests/test_cesta_basica_resolucao.py` | Create | @test-generator (padrões) | ✅ 58 testes puros |
| 13 | `tests/test_api_simulate_cesta_basica.py` | Create | @test-generator | ✅ 29 testes, AT-001..AT-005 |
| 14 | `tests/test_cesta_basica_db.py` | Create | @database-reviewer | ✅ 19 testes contra Postgres real (pulam local, rodam no CI) |
| 15 | `tests/test_schema_postgres.py` | Modify | @database-reviewer | ✅ −2 testes da tabela removida, −a tabela do `TRUNCATE` |
| 16 | `scripts/verificar_cesta_basica_producao.py` | Create | @gcp-data-architect | ✅ escrito, **não executado** (roda só por workflow) |
| 17 | `.github/workflows/migrar_banco.yml` | Modify | @gcp-data-architect | ✅ input `verificar_cesta_basica` + passo com o papel `taxreformai_app` |
| 18 | `.github/workflows/deploy.yml` | Modify | @gcp-data-architect | ✅ 2ª chamada de smoke test, payload próprio |
| 19 | `CLAUDE.md` | Modify | @python-developer | ✅ tabela de features, estrutura, arquivos-chave, banco, SPED/IBPT, rodapé |

**19/19 arquivos do manifesto.** O cabeçalho do manifesto diz "8 novos + 11 modificados", mas as
`Action` linha a linha somam **9 novos + 10 modificados** (o item 14, `tests/test_cesta_basica_db.py`,
é `Create`) — seguimos as linhas, não o cabeçalho. `git status` confirma exatamente esses 19.

Nenhum arquivo fora do manifesto foi tocado: `frontend/` (campos novos são aditivos e opcionais),
`contexto.md` (blueprint é registro de intenção) e as migrações 001-004 (histórico aplicado, não se
edita) ficaram intactos, como o DESIGN determina.

Delegação: os agentes especialistas do manifesto não foram invocados como subagentes, mesma decisão
da feature 1 — os `Code Patterns` do DESIGN já estavam no nível de implementação, e a execução
direta evitou re-derivar contexto que já estava no documento. O que **não** estava no DESIGN e
precisou de julgamento está em "Desvios", não escondido.

---

## Verification Results

```text
ruff check .   → All checks passed
pytest         → 331 passed, 3 skipped (era 244 passed, 2 skipped antes da feature)
YAML           → migrar_banco.yml e deploy.yml parseiam
SQL            → aspas e parênteses balanceados fora de string literal; as 7 sobras
                 de ')' são os marcadores de alínea "a)".."d)" dentro do texto do DOU
```

| Suíte | Resultado |
|-------|-----------|
| `tests/test_cesta_basica_resolucao.py` (novo) | 58 passed — lógica pura, sem banco e sem HTTP |
| `tests/test_api_simulate_cesta_basica.py` (novo) | 29 passed — AT-001..AT-005 via `TestClient` + pool espião |
| `tests/test_cesta_basica_db.py` (novo) | 19 testes, skipped local (sem `DATABASE_URL`), rodam no CI contra `postgres:16` |
| `tests/test_ipi_resolucao.py` + `test_api_simulate_ipi.py` | passed **sem edição** — nada da feature 1 regrediu |
| `test_api_simulate.py`, `test_escopo_e_compensacao.py`, `test_engine.py`, `test_tabela_aliquotas.py`, `test_regime_atual.py` | passed **sem edição** (126 asserções no total com as de IPI) |
| `tests/test_schema_postgres.py` | −2 testes por decisão explícita (Decisão 12) |

### O seed é lido da migração, não redigitado no teste

Escolha deliberada de implementação: `tests/test_cesta_basica_resolucao.py` **parseia
`db/migrations/005_cesta_basica_anexo_i.sql`** e monta os 95 `PrefixoCestaBasica` a partir dele.

Uma segunda cópia dos 26 itens em Python seria uma segunda fonte de verdade para dado legal
transcrito à mão do DOU — exatamente o risco que a CHECK `prefixo_bate_com_texto` existe para
eliminar dentro do banco. O efeito colateral é grande: as contagens de fechamento do DESIGN
(26 itens · 95 linhas · 76 inclusões · 19 exceções · comprimentos {4,5,6,7,8} · nenhuma duplicata ·
`21069090` como único prefixo compartilhado · toda exceção descendendo de uma inclusão do mesmo
item) passam a ser verificadas **localmente, sem Postgres**, e não só no CI. As mesmas asserções
existem também em SQL, contra o banco real, em `test_cesta_basica_db.py`.

Isso permitiu dois testes exaustivos que de outra forma seriam inviáveis:

- **as 76 inclusões**, cada uma completada com zeros até 8 dígitos, resolvem `APLICADA` no
  próprio item — cobre os 26 itens de uma vez, inclusive os 6 não-triviais;
- **as 19 exceções**, idem, resolvem `EXCLUIDA_EXPRESSAMENTE` — nenhuma delas recebe zero.

### Mapa Acceptance Test → teste

| AT | Cenário | Onde | Asserção-chave | Status |
|----|---------|------|----------------|--------|
| AT-001 | Manteiga `0405.10.00` (item 5, EXATO) | `test_at001_manteiga_zera_cbs_e_ibs_citando_o_item_5` | `total_cbs`/`total_ibs` = 0,00; `dispositivo_legal_ref == "LCP 214/2025, art. 125, Anexo I, item 5"`; `cbs_percentual == 0`; `valor_liquido == valor_base` | ✅ |
| AT-002 | Cerveja `22030000` (o NCM do smoke test atual) | `test_at002_cerveja_segue_com_a_aliquota_geral_da_fase` | `FORA_DO_ANEXO`; CBS 0,9% e IBS 0,1% idênticos ao de antes; `item is None` | ✅ |
| AT-003 | Café `09012100` (item 8), mate `09032000` (item 23), arroz `10062010` (item 1) | `test_at003_cafe_mate_e_arroz_resolvem_por_prefixo` | `APLICADA`, `tipo_correspondencia == "PREFIXO"`, `ncm_correspondido == "09.01"`, CBS/IBS = 0 | ✅ |
| AT-004 | Foie gras `02074300` (item 19), salmão `03021100` (item 20) | `test_at004_foie_gras_e_salmao_nunca_recebem_zero` | `EXCLUIDA_EXPRESSAMENTE`; alíquota **geral**, nunca zero; `ncm_correspondido == "0207.43.00"`/`"0302.1"` | ✅ |
| AT-005 | Arroz com casca `10061010`, mais 5 vizinhos de prefixo | `test_at005_vizinho_de_prefixo_nao_recebe_reducao` (parametrizado) | `FORA_DO_ANEXO` — o match respeita o limite da subposição, não é "contém a substring" | ✅ |

### Testes além dos AT, exigidos pelas decisões novas

| Cenário | Onde | Resultado |
|---------|------|-----------|
| Sobreposição 15/25 (`19021900`) | unit + API | cita o item **25**, `itens_correspondentes == [15, 25]` ✅ |
| Sobreposição 4/26 (`21069090`) | unit + API | cita o item **4** (empate em 8 dígitos → menor item), `[4, 26]` ✅ |
| Desempate independe da ordem do banco | `test_desempate_independe_da_ordem_das_linhas_do_banco` | lista invertida dá o mesmo resultado ✅ |
| Prefixo de 7 dígitos (`02109911` → `0210.99.1`) | unit | `APLICADA` no item 19 ✅ |
| Invariante do líquido após a redução | `test_invariante_do_liquido_sobrevive_a_reducao` | `valor_liquido == valor_base - total_tributos`, `total_tributos == valor_is` ✅ |
| Ramo `split_payment_active=False` | `test_sem_split_payment_o_liquido_e_o_bruto` | líquido = bruto ✅ |
| IS intacto (art. 125 só reduz IBS e CBS) | `test_reducao_zera_cbs_e_ibs_e_preserva_o_imposto_seletivo` | `valor_is` preservado ✅ |
| Pool `None` | `test_sem_pool_nenhum_a_feature_e_aditiva_e_nada_muda` | 200, `CONSULTA_INDISPONIVEL`, CBS na alíquota geral, totais `None` ✅ |
| Pool que levanta `ConnectionError` | `test_falha_de_conexao_degrada_para_200_com_a_aliquota_geral` | 200 (nunca 5xx), `logger.exception`, resto da simulação intacto ✅ |
| Exceção de um item não afeta outro | `test_excecao_de_um_item_nao_afeta_a_inclusao_de_outro` | inclusão do 19 vence exceção do 20 ✅ |
| Os dois lookups são independentes | `test_os_dois_lookups_sao_independentes` | 1 query à TIPI + 1 ao Anexo I, domínios de falha separados ✅ |
| 50 itens do mesmo NCM | `test_ncms_repetidos_viram_um_unico_conjunto_de_prefixos` | 5 prefixos na query, `total_cbs_dispensado == 450,00` ✅ |
| Serviço | `test_payload_so_de_servico_nao_consulta_o_anexo` | `NAO_APLICAVEL`, nenhuma query ao Anexo I ✅ |
| Fase 2027 | `test_fase_recusada_nem_chega_a_avaliar_a_cesta` | 422 antes do laço, nenhuma query ✅ |
| CHECKs recusando transcrição inválida | `test_cesta_basica_db.py` (CI) | `('0210.99.1','02109910')` e `'020'` viram `CheckViolation` ✅ |
| `regras_tributarias_cache` removida | `test_regras_tributarias_cache_nao_existe_mais` (CI) | `to_regclass(...) IS NULL` ✅ |

### Ainda NÃO verificado (por política, não por omissão)

| Verificação | Como rodar | Por que não rodou aqui |
|-------------|------------|------------------------|
| Migrações 005/006 aplicadas de verdade + `GRANT SELECT` ao papel `taxreformai_app` | `migrar_banco.yml` (`MIGRAR`, `verificar_cesta_basica=sim`) | Infraestrutura real nunca roda local (política do projeto) |
| Redução aplicada contra a API pública | `deploy.yml` (`DEPLOY`, `target=api`), 2ª chamada do smoke test | Idem |
| Os 19 testes de `test_cesta_basica_db.py` | CI (`ci.yml`, container `postgres:16`) | Sem Postgres, sem `psycopg` e sem Docker neste sandbox |

**Pela Decisão 13, a feature não está pronta sem as duas primeiras.** E aqui o argumento é mais
forte que na feature 1: lá, um `GRANT` faltando produzia `total_ipi: null`, um sintoma visível na
resposta. Aqui produz a **alíquota geral da fase** — que é exatamente a resposta correta de antes
desta feature. Uma migração não aplicada deixa tudo verde: 200, smoke test do IPI passando, testes
passando, e **zero redução aplicada**. Os dois passos de workflow são os únicos lugares do sistema
onde esse modo de falha vira ruído.

---

## Issues Encontrados

### 1. A invariante da Decisão 9 se contradizia num payload sem mercadoria

O `Pattern 7` define `avaliacao_completa = consulta_cesta.disponivel and not itens_nao_avaliados`,
enquanto a Decisão 9 enuncia a invariante `¬avaliacao_completa → totais = null ∧
itens_nao_avaliados[] não vazio`. As duas coisas não podem valer juntas:

| Payload | Pool | `Pattern 7` | Invariante da Decisão 9 |
|---------|------|-------------|--------------------------|
| ≥1 mercadoria, consulta caiu | `None`/quebrado | `null` + lista cheia | ✅ (todos os itens entram na lista) |
| **só serviços** | `None` | **`null` + lista VAZIA** | ❌ "não sei o total" sem dizer por causa de qual item — resposta: nenhum |
| **só serviços** | quebrado | `0.00` | — e note que é o **mesmo payload** da linha acima, com resposta diferente |

A última linha é o diagnóstico: sem item de mercadoria não há prefixo a consultar, então
`consultar_com_seguranca` nem tenta abrir conexão e devolve `disponivel=True` — um pool quebrado dá
`0.00` e um pool ausente dá `null`, para uma pergunta cuja resposta não depende do banco.

**Correção:** o predicado passou a ser `avaliacao_completa = not itens_nao_avaliados`. Os dois são
**equivalentes sempre que existe ao menos um item de mercadoria** (se a consulta caiu, todos eles
caem em `CONSULTA_INDISPONIVEL` e entram na lista), e divergem só no caso sem mercadoria, onde
"nada a avaliar" passa a ser tratado como avaliação completa — `0.00` dispensado é fato, não
estimativa. `consulta_disponivel` continua no resumo, separado, para quem quiser o outro fato.

É o mesmo tipo de contradição que a feature 1 encontrou entre seu `Pattern 2` e sua Decisão 4
("não ter nada a perguntar ≠ não conseguir perguntar"), e a correção segue a mesma direção.
Coberto por `test_payload_so_de_servico_tem_total_dispensado_zero_e_lista_vazia` e
`test_totais_nulos_sempre_vem_com_ao_menos_um_item_nomeado`.

### 2. `tipo_correspondencia` da Decisão 4 não podia ser derivado como no ramo de inclusão

Menor, mas vale registrar: o `Pattern 4` deriva `"EXATO" if len(prefixo) == 8 else "PREFIXO"` no
ramo de inclusão e fixa `"EXCECAO"` no ramo de exclusão. Mantido como está — mas isso significa que
uma exceção de 8 dígitos (`0207.43.00`) e uma de 5 (`0302.1`) reportam o mesmo tipo, perdendo a
distinção que o ramo de inclusão faz. Não foi "corrigido" porque o campo responde *como* o Anexo
alcançou o produto, e para uma exclusão o fato relevante é **que** foi excluído; a grafia literal
(`ncm_correspondido`) já diz o nível. Registrado aqui para não ser redescoberto como bug.

### 3. Contagem do cabeçalho do manifesto divergia das linhas

"8 novos + 11 modificados" no texto, 9 `Create` + 10 `Modify` nas linhas. Seguimos as linhas.
Sem impacto além deste registro.

---

## Deviations from Design

| Desvio | Razão |
|--------|-------|
| `avaliacao_completa = not itens_nao_avaliados` (o `Pattern 7` conjuga com `consulta_cesta.disponivel`) | Issue 1 — o padrão contradizia a invariante que a própria Decisão 9 enuncia, e dava respostas diferentes ao mesmo payload conforme o pool fosse ausente ou quebrado |
| A advertência de degradação sempre nomeia as situações, sem ramo de "consulta indisponível" genérico | Consequência do desvio acima: pela invariante corrigida, `¬avaliacao_completa` implica lista não vazia, então o ramo genérico seria código morto no nascimento |
| `CestaBasicaItem` e `CestaBasicaResumo` são `X \| None` no schema, preenchidos sempre pelo router | Mesma escolha do `ipi_situacao` da feature 1: o default do modelo nunca decide nada, mas o campo opcional mantém o contrato aditivo para qualquer cliente que ainda não conheça o bloco |
| Os testes leem o seed da migração 005 em vez de redigitar os 26 itens | Dado legal transcrito à mão não pode ter duas fontes de verdade; de quebra, as contagens de fechamento passam a rodar localmente e as 76 inclusões/19 exceções ficam todas cobertas |
| AT/serviço asseveram "nenhuma query **ao Anexo I**", não "`pool.connection` nunca chamado" | O audit log e a TIPI usam o mesmo pool no mesmo request — contar `connection()` cru mediria três coisas juntas. Que `consultar_com_seguranca` não abre conexão com lista vazia é provado à parte, em `test_cesta_basica_resolucao.py` (mesmo desvio, pela mesma razão, da feature 1) |
| `scripts/verificar_cesta_basica_producao.py` verifica também o café (`09012100`, prefixo de 4) | O DESIGN pede manteiga e foie gras; o café acrescenta o único comprimento que só existe por causa dos 6 itens não-triviais, sem custo |
| Agentes especialistas não invocados como subagentes | Os `Code Patterns` do DESIGN já estavam no nível de implementação; execução direta evitou re-derivar contexto |

Nenhuma decisão de arquitetura foi reaberta. Prefixo de dígitos como mecanismo único (Decisão 1),
expansão do lado da consulta (2), duas tabelas com exceção escopada ao item (3), desempate por
prefixo mais longo e menor item (4), redução válida em 2026 pelo art. 348, III, "a" (5), override
puro em `motor_calculo/reducoes.py` sem tocar `engine.py` (6), 6 situações (7), degradação para a
alíquota geral (8), totais `None` em avaliação parcial (9), `api/ncm.py` compartilhado (10), seed
dentro da migração com as 2 CHECKs (11) e remoção de `regras_tributarias_cache` (12) — todas
implementadas como especificadas.

---

## Conformidade com as constraints do DEFINE

| Constraint | Como foi respeitada |
|------------|---------------------|
| `motor_calculo/` sem dependência de infraestrutura | `motor_calculo/reducoes.py` importa apenas `dataclasses`, `decimal` e `ResultadoCalculo`. O lookup vive inteiramente em `api/`/`db/repositorio.py`, e `engine.py` não foi tocado |
| Sem RLS na tabela nova | Nenhum `ENABLE ROW LEVEL SECURITY` na migração 005 — dado legal público, mesmo padrão de `aliquotas_ipi_tipi` |
| Override por item aplicado **depois** de `engine.calcular()` | `aplicar_reducao_a_zero(resultado)` recebe o `ResultadoCalculo` pronto e devolve outro |
| Nenhuma inferência além do que a lei escreve | Os 95 prefixos são transcrição literal; nenhum código de 8 dígitos foi materializado a partir de uma posição, e nenhuma alíquota foi estimada |
| Escopo estrito ao Anexo I | Nenhum dos outros 16 Anexos entrou; o IS ficou intacto na redução, porque o art. 125 só alcança IBS e CBS |

---

## Segurança

- **Sem SQL dinâmico.** `= ANY(%s)` recebe a lista como parâmetro vinculado, e todo prefixo passou
  antes por `digitos_ncm`/`prefixos_ncm`, que só deixam sair `[0-9]{4,8}` — a string que chega ao
  banco nunca é o texto bruto do cliente. Um NCM malformado nem chega ao SQL.
- **Sem RLS, deliberadamente.** O Anexo I é lei federal, idêntico para todo tenant. Tenant scoping
  aqui não protegeria nada e quebraria o padrão já registrado na migração 004.
- **Privilégio mínimo preservado.** Só `SELECT` para o papel de runtime, nas duas tabelas novas; a
  escrita é exclusiva da migração, rodada pelo papel admin.
- **`DROP TABLE` guardado.** A migração 006 recusa derrubar uma tabela com linhas — a afirmação "ela
  nunca teve dados" virou verificação, não crença, e o migrador roda cada migração na própria
  transação, então o `RAISE EXCEPTION` aborta tudo sem perda.
- **Sem PII.** NCM, descrição de produto e dispositivo legal são dados públicos.
- **Enumeração não é vazamento.** O Anexo I foi publicado no DOU; responder "este NCM não está na
  cesta básica" não revela nada que o cliente não possa ler no Diário Oficial.

---

## Final Status

### Overall: ✅ BUILD COMPLETO — ⏳ pendente das 2 verificações reais da Decisão 13

- [x] 19/19 arquivos do manifesto
- [x] `ruff check .` limpo
- [x] 331 passed, 3 skipped (+87 testes locais, +19 que rodam no CI)
- [x] AT-001..AT-005 cobertos, mais os 14 cenários extras das Decisões 4, 6, 8 e 9
- [x] Nada da feature 1 regrediu — 126 asserções passam **sem edição**
- [x] Contagens de fechamento verificadas: 26 itens · 95 linhas · 76 inclusões · 19 exceções ·
      comprimentos {4,5,6,7,8} · `21069090` como único prefixo compartilhado · nenhuma exceção órfã
- [x] `regras_tributarias_cache`/`buscar_regra_cache` removidos (confirmado por `grep`: só restam
      as migrações históricas, que não se editam)
- [ ] **`migrar_banco.yml` com `verificar_cesta_basica=sim`**
- [ ] **`deploy.yml` — 2ª chamada do smoke test**

## Recomendação antes do `/ship`

Rodar, nesta ordem — **não é formalidade**. Pela Decisão 8, uma migração não aplicada ou um `GRANT`
faltando não produzem erro nenhum: produzem a alíquota geral da fase, que é a resposta correta de
antes desta feature. Esta é a única feature do projeto cujo modo de falha é **indistinguível do
sucesso** olhando só para o CI e para o status HTTP.

1. **`migrar_banco.yml`** (`confirm=MIGRAR`, `verificar_cesta_basica=sim`, `ingerir_tipi=nao` — já
   ingerida, `verificar_rls`/`verificar_ipi` a gosto). Aplica 005 e 006 e prova que o papel
   `taxreformai_app` lê o Anexo I: 26/76/19, manteiga `APLICADA` no item 5, café `APLICADA` no item
   8 pela posição 09.01, e foie gras `EXCLUIDA_EXPRESSAMENTE`. Falha ruidosa em qualquer divergência.
2. **`deploy.yml`** (`confirm=DEPLOY`, `target=api`). O smoke test faz agora duas chamadas: a do IPI
   (`22030000`, inalterada) e a nova (`04051000`), que exige `cesta_basica.total_cbs_dispensado`
   não-nulo e `cbs_percentual == 0`. Os payloads são separados de propósito — juntar os dois itens
   faria `total_ipi` depender de `0405.10.00` estar na TIPI ingerida, e um item de mercadoria não
   resolvido zera `total_ipi` para `null`, reprovando o job por um motivo que nada tem a ver com
   esta feature (Decisão 13).

Registrar o número de cada run no `SHIPPED`, como nas duas features anteriores — é o que torna a
alegação auditável por qualquer pessoa com acesso ao repositório, e é coerente com a proposta de
valor do próprio produto.
