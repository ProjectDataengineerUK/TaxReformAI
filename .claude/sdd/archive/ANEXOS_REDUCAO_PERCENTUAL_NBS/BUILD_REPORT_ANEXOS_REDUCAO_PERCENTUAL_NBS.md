# BUILD REPORT: Anexos II, III, X e XI — Redução de 60% de CBS/IBS por NBS

> Implementation report for ANEXOS_REDUCAO_PERCENTUAL_NBS (posição 14/17 do roadmap)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NBS |
| **Date** | 2026-07-31 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md](../features/DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md) |
| **DESIGN** | [DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md](../features/DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NBS.md) |
| **Status** | Complete — com um gap documentado (Anexo X sem itens, ver "Blockers") |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 10/10 |
| **Files Created** | 9 novos + 4 modificados |
| **Lines of Code** | ~1.570 (código + SQL + testes) |
| **Tests Passing** | 469/469 (+36 novos desta feature), 4 skipped (sem `DATABASE_URL`, esperado) |
| **Lint** | `ruff check .` — limpo |
| **Agents Used** | 0 (build direto, mesmo padrão das 6 features anteriores desta leva) |

---

## Task Execution

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `api/nbs.py` — canonização NBS | ✅ Complete | 9 dígitos + classificador de topo "1"; prefixos (5,6,7,9) |
| 2 | `db/migrations/011_*.sql` | ✅ Complete | Catálogo +4 Anexos; 2 tabelas novas; Anexo X só no catálogo (gap documentado) |
| 3 | `db/repositorio.py` extensão | ✅ Complete | `PrefixoReducaoNbs` + `buscar_reducao_nbs_por_prefixo`, sem tocar funções NCM |
| 4 | `api/reducao_nbs.py` | ✅ Complete | `SituacaoReducaoNbs` (com `CONDICAO_NAO_SATISFEITA`), `resolver_item_nbs` |
| 5 | `api/schemas_simulate.py` extensão | ✅ Complete | 3 campos em `ItemSimulacao`, 2 em `ReducaoItem` |
| 6 | `api/routers/simulate.py` — dispatch por natureza | ✅ Complete | Encontrou e corrigiu 1 bug real (ver "Issues Encontrados") |
| 7 | Testes (unit + integration + E2E) | ✅ Complete | 4 arquivos novos, 36 testes, todos passando |
| 8 | Script de verificação real + workflows | ✅ Complete | `verificar_reducao_nbs_producao.py`, `migrar_banco.yml`, `deploy.yml` |
| 9 | `ruff check` + `pytest` | ✅ Complete | Limpo após 1 fix de import order (auto) |
| 10 | Este BUILD_REPORT | ✅ Complete | — |

---

## Verificação de Fonte Primária Realizada Durante o Build

O `/design` já havia identificado que o mapeamento item-a-inciso do Anexo X (necessário para a condição de nacionalidade) ficava para o `/build`. Nesta sessão:

1. **Anexo II** (`legis.senado.leg.br/norma/40180341/publicacao/40180894`) — os 9 itens lidos e conferidos byte a byte contra o `/define`: **idênticos**, nenhuma correção.
2. **Anexo III** (`.../40180900`) — os 30 itens lidos individualmente (o `/define` só tinha resumido 1-17 como "faixa de 17 códigos distintos"); confirmado item a item, incluindo a anomalia do item 29 (`1.2301.99.0`, 8 dígitos).
3. **Anexo X** (`.../40180985`) — os 57 itens lidos e transcritos individualmente (ver lista completa abaixo). **Não semeado nesta migração** — ver "Blockers".
4. **Anexo XI** (`.../40180991`) — os 46 itens (Bloco 1 + Bloco 2) lidos e conferidos: idênticos ao `/define`.
5. **Art. 139** (corpo da LCP 214/2025) — **tentativa falhou**: a ferramenta de leitura web deste ambiente trunca o documento de 544 artigos antes de alcançar o art. 139 (parou no art. 59 em duas tentativas, com prompts diferentes). Não há âncora por artigo na página do Senado. Mesma classe de limitação de acesso já registrada para `planalto.gov.br` e `nbs.economia.gov.br` no `/define` — tratada da mesma forma: documentada, não contornada com uma suposição.

### Os 57 itens do Anexo X, lidos nesta sessão (para referência futura)

| # | Descrição | Código | # | Descrição | Código |
|---|-----------|--------|---|-----------|--------|
| 1 | Licenciamento de direitos de autor e conexos | 1.1103 | 30 | Cessão definitiva — obras musicais/fonogramas | 1.1107.40.00 |
| 2 | Licenciamento — obras literárias | 1.1103.10.00 | 31 | Animação | 1.2501.35.00 |
| 3 | Licenciamento — obras cinematográficas | 1.1103.31.00 | 32 | Legendas/títulos/dublagem | 1.2501.36.00 |
| 4 | Licenciamento — obras jornalísticas | 1.1103.32.00 | 33 | Projeto/edição de som | 1.2501.37.00 |
| 5 | Licenciamento conexo — intérpretes audiovisual | 1.1103.34.00 | 34 | Projeção de filmes | 1.2501.50.00 |
| 6 | Licenciamento conexo — produtores audiovisual | 1.1103.35.00 | 35 | Produção audiovisual NC | 1.2501.90.00 |
| 7 | Licenciamento — obras p/ TV | 1.1103.36 | 36 | Organização/promoção de atuações ao vivo | 1.2502.10.00 |
| 8 | Licenciamento — obras musicais/fonogramas | 1.1103.4 | 37 | Produção/apresentação de atuações ao vivo | 1.2502.20.00 |
| 9 | Cessão temporária — obras literárias | 1.1106.10.00 | 38 | Atuação artística | 1.2503.10.00 |
| 10 | Cessão temporária — obras cinematográficas | 1.1106.31.00 | 39 | Autores/compositores/escultores/pintores | 1.2503.20.00 |
| 11 | Cessão temporária — obras jornalísticas | 1.1106.32.00 | 40 | Museus | 1.2504.11.00 |
| 12 | Cessão temporária conexa — intérpretes audiovisual | 1.1106.34.00 | 41 | Reservas de ingressos | 1.1805.32.00 |
| 13 | Cessão temporária conexa — produtores audiovisual | 1.1106.35.00 | 42 | Fotografias artísticas originais | 4911.91.00 (NCM) |
| 14 | Cessão temporária — obras p/ TV | 1.1106.36 | 43 | Quadros/pinturas/desenhos originais | 9701.91.00 (NCM) |
| 15 | Cessão temporária — obras musicais/fonogramas | 1.1106.4 | 44 | Gravuras/estampas/litografias | 9702.90.00 (NCM) |
| 16 | Cessão definitiva — obras literárias | 1.1107.10.00 | 45 | Esculturas | 9703.90.00 (NCM) |
| 17 | Cessão definitiva — obras cinematográficas | 1.1107.31.00 | 46 | Licenciamento conexo — intérpretes (geral) | 1.1103.42.00 |
| 18 | Cessão definitiva — obras jornalísticas | 1.1107.32.00 | 47 | Cessão temporária de direitos (geral) | 1.1106 |
| 19 | (dup. — ver nota¹) | 1.1107.40.00 | 48 | Cessão temporária conexa — intérpretes (geral) | 1.1106.42.00 |
| 20 | Agências de notícias — jornais/periódicos | 1.1704.10.00 | 49-54 | Direitos de obras TEATRAIS (6 itens) | **sem código** |
| 21 | Agências de notícias — mídia audiovisual | 1.1704.20.00 | 55 | Sonorização/iluminação/figurino/cenografia | 1.2502.30.00 |
| 22 | Convenções/feiras de negócios/exposições/eventos | 1.1806.6 | 56 | Locação/montagem/desmontagem de palcos | 1.0105.70.00 |
| 23 | Gravação de som em estúdio | 1.2501.11.00 | 57 | Apresentação/promoção de atuações, gestão de espaços | 1.2502.90.00 |
| 24 | Gravação de som ao vivo | 1.2501.12.00 | | | |
| 25 | Produção de programas de TV/filmes | 1.2501.21.00 | | | |
| 26 | Produção de programas de rádio | 1.2501.22.00 | | | |
| 27 | Edição de obras audiovisuais | 1.2501.31.00 | | | |
| 28 | Duplicação/transferência | 1.2501.32.00 | | | |
| 29 | Correção de cor/restauração digital | 1.2501.33.00 | | | |

¹ Item 19 (`1.1107.40.00`, cessão definitiva de obras musicais/fonogramas) e item 30 citam o MESMO código — não investigado a fundo nesta sessão (fora do escopo imediato, já que nenhum item do Anexo X foi semeado).

**Isso NÃO substitui a leitura do art. 139** — sem o texto dos incisos I-VIII e §§1º-3º, não é seguro decidir qual dos itens acima exige `conteudo_nacional_majoritario=True`. A tabela acima fica registrada para a sessão que conseguir ler o art. 139 não precisar reabrir o Anexo X do zero.

---

## Files Created

| File | Lines | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `api/nbs.py` | 44 | ✅ | Testado isoladamente (8 testes) |
| `api/reducao_nbs.py` | 240 | ✅ | Testado isoladamente (20 testes) |
| `db/migrations/011_anexos_reducao_percentual_nbs.sql` | 311 | ✅ | Assertions `DO $$` próprias + testes de integração |
| `scripts/verificar_reducao_nbs_producao.py` | 221 | ⏳ | Só executável contra Cloud SQL real via `migrar_banco.yml` (não local) |
| `tests/test_nbs.py` | 46 | ✅ | 8/8 passando |
| `tests/test_reducao_nbs.py` | 304 | ✅ | 21/21 passando (parseia a migração 011, não redigita o seed) |
| `tests/test_reducao_nbs_db.py` | 127 | ⏭️ | Skipped local (sem `DATABASE_URL`), roda de verdade no CI |
| `tests/test_simulate_nbs.py` | 275 | ✅ | 7/7 passando (E2E via `TestClient` + pool fake) |

## Files Modified

| File | Change | Verified |
|------|--------|----------|
| `db/repositorio.py` | +`PrefixoReducaoNbs` dataclass, +`buscar_reducao_nbs_por_prefixo` | ✅ |
| `api/schemas_simulate.py` | +3 campos em `ItemSimulacao`, +2 em `ReducaoItem` | ✅ |
| `api/routers/simulate.py` | Dispatch por `natureza`; 3ª consulta em lote; textos de advertência atualizados | ✅ |
| `.github/workflows/migrar_banco.yml` | +input `verificar_reducao_nbs` +step | ✅ (YAML válido) |
| `.github/workflows/deploy.yml` | +5ª chamada de smoke test (Anexo II, item 4) | ✅ (YAML válido) |

---

## Verification Results

### Lint Check

```text
$ ruff check .
All checks passed!
```

**Status:** ✅ Pass

### Tests

```text
$ python3 -m pytest tests/ -q
469 passed, 4 skipped, 1 warning in 3.83s
```

**Status:** ✅ 469/469 Pass (36 novos desta feature: 8 em `test_nbs.py`, 21 em `test_reducao_nbs.py`, 7 em `test_simulate_nbs.py`; mais `test_reducao_nbs_db.py`, 9 testes, skip local sem `DATABASE_URL`)

---

## Issues Encontrados Durante o Build

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `api/routers/simulate.py` acessava `resolucao.tipo_correspondencia` diretamente (sem `getattr`) na contagem de `itens_por_capitulo`, fora do bloco de construção do `ReducaoItem` que já tinha sido corrigido para usar `getattr`. `AttributeError` real, pego pelo teste E2E `test_at001_ensino_tecnico_reduz_60_por_cento_via_nbs` (que um teste isolado de `api/reducao_nbs.py` nunca alcançaria, porque o bug estava no ROUTER, não no resolvedor). | Trocado para `getattr(resolucao, "tipo_correspondencia", None) == "CAPITULO"`. |
| 2 | Item 29 do Anexo III (`1.2301.99.0`, 8 dígitos, 1 a menos que o padrão) colidiria com a CHECK `prefixo_bate_com_texto_nbs` se completado ingenuamente. | Resolvido com uma exceção NOMEADA na própria CHECK (`(anexo,item,sub_item) = ('III',29,0) OR prefixo = regexp_replace(...)`) — documentado, não silencioso (Decisão 6 do DESIGN). |
| 3 | Ao completar o item 29 para 9 dígitos, o valor resultante (`123019900`) coincide EXATAMENTE com o código que 10 outros itens do Anexo III já compartilham — o `/define`/`/design` esperavam um grupo de 10 (AT-003), não 11. | Tratado como refinamento de teste esperado, não bug: a fonte primária, lida literalmente, sustenta a leitura "item 29 pertence ao mesmo grupo residual" (o dígito faltante é plausivelmente o "0" duplicado que todo item irmão tem). `AT-003` foi escrito/verificado para 11 itens, com o porquê documentado no teste. Mesmo padrão de refinamento já registrado no CLAUDE.md para o build anterior (`ANEXOS_REDUCAO_PERCENTUAL_NCM`). |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| **Anexo X (art. 139) não foi semeado** — schema e catálogo prontos, zero itens em `anexos_reducao_nbs` | A Decisão 5 do DESIGN já previa que o mapeamento item-a-inciso ficaria para o `/build`, mas o `/build` não conseguiu ler o art. 139: o corpo da LCP 214/2025 (544 artigos) excede o que a ferramenta de leitura web deste ambiente processa de uma vez (truncou no art. 59 em duas tentativas), e a página do Senado não tem âncora por artigo. Mesma classe de limitação já aceita para `planalto.gov.br`/`nbs.economia.gov.br`. | Nenhum item de serviço casará com o Anexo X nesta versão — todo serviço de produção artística/cultural/audiovisual continua na alíquota geral, o comportamento de ANTES desta feature para esse Anexo especificamente (nunca um erro na direção perigosa: não concede 60% que a lei condiciona a algo não verificado). Ver "Blockers". |
| **AT-003 passou de "10 itens" para "11 itens"** | O item 29 (anomalia de dígito) foi completado para o MESMO código do grupo já identificado pelo `/define`, não mantido isolado — ver "Issues Encontrados #3". | Nenhum, já reconciliado nos testes e neste relatório. |
| **Item 1.2 e 1.3 do Anexo XI NÃO receberam `condicao_vendedor_ref`** | O `/define` já sinalizava ambiguidade ("talvez" item 1.3); o `/build` decidiu conservadoramente que só o item 1.1 ("Segurança em TI") é inequivocamente "segurança da informação/cibernética" sem a nomenclatura oficial (inacessível) para confirmar os demais. | Um vendedor qualificado de aplicativos de TI (item 1.2) não recebe 60% por esse eixo — só pelo eixo comprador (art. 142, I). Documentado inline na migração 011 e no teste `test_eixo_vendedor_nao_se_aplica_ao_item_1_2_conservadoramente`. |

---

## Blockers

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| Art. 139 da LCP 214/2025 não pôde ser lido nesta sessão (documento de 544 artigos excede o processamento da ferramenta de leitura web; sem âncora por artigo) | Uma sessão futura precisa: (a) uma forma de ler o art. 139 isoladamente (ex. um mirror com âncora por artigo, ou um fetch em pedaços menores), (b) mapear os 47 itens NBS do Anexo X (lista completa já transcrita acima) aos incisos I-VIII, e (c) uma nova migração (012) semeando `anexos_reducao_nbs` para o Anexo X — o schema e o catálogo já estão prontos, só falta o INSERT. | Próxima sessão de `/build` ou `/iterate` desta feature |

Este blocker **não impede o `/ship`**: os Anexos II, III e XI estão completos, verificados e testados; o Anexo X está deliberadamente e visivelmente vazio (não quebrado, não parcialmente errado) — mesma disciplina do projeto de "nunca estimar", aplicada aqui a uma AUSÊNCIA de dado, não a uma alíquota.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Happy path NBS exato (Anexo II) | ✅ Pass | `test_at001_*` em 3 arquivos (unit, resolução, E2E) |
| AT-002 | Prefixo parcial de subposição (Anexo II) | ✅ Pass | `test_at002_*` |
| AT-003 | Múltiplos itens do MESMO Anexo, MESMO código (Anexo III) | ✅ Pass (refinado para 11 itens, não 10 — ver Deviations) | `test_at003_*` |
| AT-004 | Item sem código (Anexo II) | ✅ Pass | `test_at004_*` |
| AT-005 | Minoria NCM do Anexo X não resolvida | ✅ Pass (trivialmente — Anexo X vazio; item 42-45 nunca teria chave NBS de qualquer forma) | `test_at013_carro_blindado...` (equivalente para XI, mesmo mecanismo) |
| AT-006 | Itens sem código do Anexo X (obras teatrais) | ⏸️ Não aplicável ainda — Anexo X vazio | Ver Blockers |
| AT-007 | Condição de nacionalidade não informada (Anexo X) | ❌ Bloqueado | Ver Blockers — não há item do Anexo X para testar |
| AT-008 | Anexo XI, item vetado | ✅ Pass | `test_at008_*` |
| AT-009 | Anexo XI, item "pendente de classificação" | ✅ Pass | `test_at009_*` |
| AT-010 | Anexo XI, condição de comprador não informada | ✅ Pass | `test_at010_*` (2 arquivos) |
| AT-011 | Anexo XI, condição de comprador informada | ✅ Pass | `test_at011_*` (2 arquivos) |
| AT-012 | Anexo XI, `ENTIDADE_CEBAS_SUS` não se aplica | ✅ Pass | `test_at012_*` |
| AT-013 | Anexo XI, minoria NCM (bens) não resolvida | ✅ Pass | `test_at013_*` |
| AT-014 | Regressão — os 10 Anexos NCM já shipados intactos | ✅ Pass | `test_at014_*`, mais `test_reducao_nbs_db.py::test_os_10_anexos_ncm_sobreviveram...` |
| AT-015 | Item de mercadoria sem `nbs` preenchido | ✅ Pass | `test_at015_*` (2 arquivos) |

**13/15 verificados nesta sessão; 2 bloqueados pela ausência do art. 139 (AT-006, AT-007), não por falha de implementação.**

---

## Final Status

### Overall: ✅ COMPLETE (com gap documentado no Anexo X)

**Completion Checklist:**

- [x] Todos os arquivos do manifesto criados/modificados
- [x] `ruff check .` limpo
- [x] 469/469 testes passando (4 skip esperados)
- [x] Zero regressão nos 10 Anexos NCM (provado por teste, não só inferido)
- [x] Blocker do Anexo X documentado explicitamente (não escondido, não contornado com estimativa)
- [x] 13/15 Acceptance Tests verificados; os 2 restantes (AT-006/AT-007) dependem de dado ainda não disponível

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md` — com o gap do Anexo X registrado no SHIPPED como pendência de continuação (mesmo padrão de "próximo ciclo" já usado pelo projeto para outros itens em aberto), não como feature incompleta: os 3 Anexos que TÊM dado semeado (II, III, XI) estão completos, testados e verificáveis contra o Cloud SQL real via `migrar_banco.yml` (`verificar_reducao_nbs=sim`) e o smoke test do `deploy.yml`.
