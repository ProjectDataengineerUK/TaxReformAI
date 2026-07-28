# INVESTIGAÇÃO RESOLVIDA: LC 227/2026 — Atualização Legal da LCP 214/2025

> Este NÃO é um documento SHIPPED de feature. `LC_227_2026_ATUALIZACAO_LEGAL` nunca teve
> `/brainstorm`, nunca passou por `/design` nem `/build` — foi uma investigação factual aberta
> por uma Open Question do `/define` de `REGRAS_TRIBUTARIAS_CACHE`
> (`../REGRAS_TRIBUTARIAS_CACHE/DEFINE_REGRAS_TRIBUTARIAS_CACHE.md`, Open Questions #2) e
> resolvida sem nunca precisar avançar no workflow SDD. Arquivada aqui, separada das features
> shipadas, para não confundir "investigação fechada" com "feature entregue" — mas preservando a
> trilha de auditoria completa.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Origem** | Open Question levantada durante `/define` de `REGRAS_TRIBUTARIAS_CACHE` (2ª feature de 11, `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |
| **Tipo** | Investigação factual (não é uma feature) |
| **Status final** | ✅ Resolvida — nenhuma ação corretiva necessária |
| **Data de resolução** | 2026-07-28 |
| **Documento original** | [`DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md`](./DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md) |

---

## O que motivou a investigação

Durante a verificação de fonte primária do Anexo I (Cesta Básica Nacional), ficou claro que a
**Lei Complementar nº 227, de 13 de janeiro de 2026** altera extensivamente a LCP 214/2025 — a lei
em que todo `motor_calculo/` e a ingestão em `ingestion/`/Qdrant se baseiam. Isso levantou duas
perguntas que o `/define` de `REGRAS_TRIBUTARIAS_CACHE` não podia responder sozinho (fora de seu
escopo, que era só o Anexo I):

1. Alguma alíquota/regra já codificada no projeto ficou numericamente errada por causa da LC
   227/2026?
2. O corpus legal já ingerido no Qdrant (580 artigos da LCP 214/2025, ingeridos em 2026-07-25)
   reflete o texto pós-LC-227, ou está desatualizado?

## Diagnóstico executado

Uma sessão de `/define` dedicada (`DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md`) catalogou, contra
fonte primária (`legis.senado.leg.br`, mirror oficial do DOU), **255 dispositivos alterados** pela
LC 227/2026 na LCP 214/2025 (244 efetivamente em vigor, 11 vetados pela Presidência). Análise
focada nos únicos artigos citados por número no código real (343, 344, 346, 347, 348) concluiu:
**nenhuma alíquota ou regra já codificada neste projeto ficou numericamente errada** — os
dispositivos novos (art. 344, § único, IV; art. 348, §§ 3º/4º) ampliam o alcance jurídico de
artigos já citados, sem contradizer nenhum número já calculado.

A segunda pergunta (corpus desatualizado?) não pôde ser fechada só por análise textual — exigia
uma consulta real contra o Qdrant de produção. Essa consulta foi rodada **depois** do `/define`,
como um diagnóstico de leitura isolado (sem reingestão):

```
scripts/verificar_lc227_ingerida.py (novo)
ingestao.yml, verificar_lc227=sim, fonte=nenhuma (só leitura)
Run: https://github.com/ProjectDataengineerUK/TaxReformAI/actions/runs/30368697093 (2026-07-28)

Documento 'LCP_214_2025': 3375 chunks indexados
ACHOU artigo novo: dispositivo='Art. 341-A'
ACHOU inciso IV: dispositivo='Art. 344, Parágrafo único, Inciso IV'
VEREDITO: corpus JÁ REFLETE a LC 227/2026. Nenhuma reingestão necessária.
```

Os dois marcadores buscados (art. 341-A — artigo inteiramente novo, exclusivo da LC 227/2026; e o
texto literal do Inciso IV do art. 344, acréscimo da mesma lei) já estavam indexados. Isso
confirma a hipótese levantada no `/define`: a ingestão de 2026-07-25 usou a URL de "texto
compilado" do Planalto (`ccivil_03`), que o próprio site mantém atualizado com as alterações mais
recentes — ao contrário da "Publicação Original" do DOU, que seria um instantâneo imutável do
texto de 2025.

## Por que isto não vira uma feature

- Não há regressão para corrigir (nenhum número codificado está errado).
- Não há reingestão necessária (o corpus já reflete a lei vigente).
- As duas perguntas de estratégia mais amplas que o `/define` original havia deixado em aberto
  ("vale modelar os regimes de referência do art. 344, IV?", "vale ingerir a LC 227/2026 como
  fonte própria, separada da LCP 214/2025?") deixaram de ser urgentes assim que a pergunta
  bloqueante (corpus desatualizado?) foi respondida negativamente — ficam como possibilidades
  futuras, não como pendências, e não foram adicionadas ao
  `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md` (que continua com as mesmas 11 features).

## Rastro de verificação

| Verificação | Onde | Resultado |
|-------------|------|-----------|
| Catálogo dos 255 dispositivos alterados/vetados | `DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md` | Fonte primária (`legis.senado.leg.br`), URLs e datas registradas |
| Análise focada nos artigos citados no código (343/344/346/347/348) | `DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md` | Nenhum número codificado ficou errado |
| Diagnóstico contra o Qdrant real | `scripts/verificar_lc227_ingerida.py`, `ingestao.yml` run `30368697093` | Corpus já reflete a LC 227/2026 — nenhuma reingestão necessária |

---

## Status: ✅ RESOLVIDA (não é uma feature shipada)

*Arquivada em 2026-07-28 por ship-agent, junto com o `/ship` de `REGRAS_TRIBUTARIAS_CACHE` — ver
`../REGRAS_TRIBUTARIAS_CACHE/SHIPPED_2026-07-28.md`.*
