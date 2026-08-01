# DEFINE: Integração de CBS/IBS à Partilha do Simples Nacional (Anexos XVIII-XXIII)

> Regime tributário inteiro, substitutivo (não uma redução sobre `engine.py`): dado a receita
> bruta acumulada em 12 meses, a atividade (Comércio/Indústria/3 tipos de Serviço/MEI) e o ano,
> calcula a alíquota efetiva do Simples Nacional e a partilha entre IRPJ/CSLL/CBS/CPP/ICMS-ou-
> ISS/IBS — incluindo, pela primeira vez neste projeto, um cálculo real de CBS/IBS para 2027-2033
> sem nenhuma restrição de "alíquota indisponível".
>
> **Posição na sequência:** 17 de 17 (última, `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Sem dependência técnica das posições 12-16 (Anexos de redução/Anexo XVI/Anexo
> XVII) — confirmado nesta sessão que os Anexos XVIII-XXIII não citam nenhum deles.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMPLES_NACIONAL_CBS_IBS_TRANSICAO |
| **Date** | 2026-07-31 |
| **Author** | define-agent |
| **Status** | ✅ Shipado 2026-08-01 (ver `SHIPPED_2026-08-01.md`) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

A LCP 214/2025 (Anexos XVIII-XXIII) integra CBS e IBS à partilha do Simples Nacional — o regime
tributário unificado da LC 123/2006 usado por micro e pequenas empresas —, com tabelas de faixa
de receita e partilha percentual entre 6 tributos já fixadas ano a ano de 2027 até 2033 (quando o
regime se torna permanente). Mas `motor_calculo/` não modela o Simples Nacional de nenhuma forma
hoje — só o regime geral (IVA Dual via `engine.py`) e o regime vigente não-Simples
(`regime_atual.py`, PIS/COFINS/ICMS/ISS) —, e `/v1/tax/simulate` não tem como identificar uma
empresa optante desse regime nem sua receita bruta acumulada. Diferente de toda feature anterior
do motor de cálculo pós-2026 (bloqueadas por "alíquota indisponível"), os dados do Simples
Nacional **já estão integralmente fixados por lei** — esta é a primeira oportunidade do projeto de
entregar um cálculo real e completo de CBS/IBS para os anos 2027-2033, sem nenhuma exceção.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Controller/contador de micro/pequena empresa optante do Simples Nacional | Consumidor direto do produto | Precisa saber, ano a ano até 2033, como a fatia de CBS/IBS na partilha do DAS evolui — hoje só existe a tabela legal bruta, sem ferramenta que calcule o valor efetivo por tributo a partir da receita bruta real da empresa |
| Consultoria tributária | Planejamento tributário de carteira de clientes Simples Nacional | Precisa simular, para múltiplos clientes/atividades/faixas, o impacto da transição CBS/IBS no DAS mês a mês — sem replicar manualmente 6 tabelas × 6 faixas × 7 anos em planilha |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo COMPLETO dos 6 Anexos (XVIII-XXIII) — todas as faixas, todos os anos até 2033 (regime permanente), a tabela de valores fixos do MEI — verificado contra fonte primária nesta sessão, com cross-check de duas fontes independentes |
| **MUST** | Identificar e citar o dispositivo que define a fórmula de cálculo em si: **LC 123/2006, art. 18, §§1º, 1º-A e 1º-B** (redação da LC 155/2016) — a "alíquota efetiva" e a "partilha por tributo" NÃO estão nos Anexos da LCP 214/2025 (que só trazem alíquota nominal, valor a deduzir, e percentual de repartição); a fórmula que os combina está na LC 123/2006, achado desta sessão ausente do brainstorm |
| **MUST** | Confirmado nesta sessão, contra fonte primária, quais dos 6 Anexos a LC 227/2026 alterou: **XX e XXI** (Anexos III e IV da LC 123/2006) foram alterados — os outros 4 (XVIII, XIX, XXII, XXIII) não. Confirmado também que o art. 18 da LC 123/2006 (a fórmula em si) não foi alterado pela LC 227/2026 — a redação vigente é da LC 155/2016 |
| **MUST** | Módulo novo de cálculo (`motor_calculo/simples_nacional.py` ou equivalente), Python puro, sem infraestrutura — mesmo padrão de `regime_atual.py`/`piso_aliquota_ibs.py`: implementa (a) `alíquota_efetiva = (RBT12 × Aliq − PD) / RBT12` (art. 18, §1º-A); (b) percentual efetivo de cada tributo = alíquota_efetiva × percentual de repartição da tabela do Anexo correspondente (art. 18, §1º-B) |
| **MUST** | `Payload`/`ItemSimulacao` de `/v1/tax/simulate` ganham campos novos para: opção pelo Simples Nacional, receita bruta acumulada em 12 meses (RBT12), e atividade (mapeando para um dos 6 Anexos: Comércio/Indústria/Serviço-Anexo-III/Serviço-Anexo-IV/Serviço-Anexo-V/MEI) — maior mudança de contrato de API de toda a leva, no nível do PAYLOAD, não por item |
| **MUST** | Resultado cita o Anexo exato (XVIII-XXIII), a faixa (1ª-6ª, ou "MEI" sem faixa), e o ano usado para a tabela de partilha — mesma disciplina de citação por dispositivo já usada em toda feature anterior |
| **MUST** | O Anexo XXI (Serviços do §5º-C) **não tem coluna CPP** (a Contribuição Previdenciária é recolhida à parte, fora do DAS, para esse grupo) — o módulo NUNCA inventa um percentual de CPP para esse Anexo; o campo correspondente fica ausente/`None`, nunca zero |
| **MUST** | A cláusula de teto/redistribuição do ISS (Anexos XX e XXI, 5ª Faixa: "o percentual efetivo máximo devido ao ISS será de X%, transferindo-se a diferença, de forma proporcional, aos tributos federais") é implementada com as fórmulas exatas verificadas nesta sessão — nunca aproximada nem ignorada quando a alíquota efetiva ultrapassa o teto daquele ano |
| **MUST** | Anexo XXIII (MEI): tabela de valores FIXOS em R$ (não percentual, não depende de receita bruta/faixa) — módulo trata como caminho de cálculo estruturalmente diferente dos outros 5 Anexos, nunca forçado no mesmo formato de "alíquota efetiva" |
| **MUST** | `motor_calculo/engine.py`/`tabela_aliquotas.py` (regime geral) permanecem INTOCADOS — o Simples Nacional é um regime SUBSTITUTIVO, nunca uma redução aplicada sobre o resultado do regime geral |
| **SHOULD** | Documentar a última tabela de partilha (2033 em diante, "regime permanente") de forma que anos ≥2033 reusem a mesma tabela sem exigir uma linha por ano indefinidamente |
| **COULD** | Investigar se a 6ª Faixa (que não tem ICMS/ISS/IBS declarados nas tabelas 2027-2032, só nos 5 tributos citados) tem tratamento tributário diferente documentado em outro dispositivo — fora de escopo desta feature, mas registrar se encontrado |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

**Método:** `legis.senado.leg.br` (as 6 URLs de publicação de cada Anexo) tentado primeiro;
resultado desigual — Anexo XX foi **recusado integralmente** pelo resumidor do WebFetch (limite
de citação interno, não do documento); Anexo XIX e Anexo XXIII foram **truncados** (WebFetch
reportou incorretamente que a tabela do MEI "termina em 2031" — na verdade tem mais duas linhas,
2032 e 2033). Aplicada a técnica já estabelecida no projeto (Anexo X, `ANEXOS_REDUCAO_PERCENTUAL_NBS`):
baixado o PDF "Texto Atualizado" da Câmara dos Deputados (298 páginas,
`leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.pdf`), extraído via
`pdftotext -layout`, localizadas as seções ANEXO XVIII a ANEXO XXIII (fim do documento). A
transcrição definitiva vem do PDF (completa, verbatim); onde o WebFetch produziu dados, eles
bateram exatamente com o PDF nos pontos comparados — única exceção sendo os anos 2032-2033 do MEI
e as fórmulas de teto de ISS, que só o PDF capturou.

**Correção a uma premissa do brainstorm**: a Tabela 1 (alíquota nominal/valor a deduzir) NÃO
muda a cada ano — há só DUAS versões: 2027-2028 e "a partir de 2029" (idênticas exceto a 6ª
Faixa, que sobe ~0,10 p.p. e permanece assim até o fim). É a Tabela 2 (partilha) que muda ano a
ano, de 2027 até 2033, quando se torna permanente.

**Achado crítico ausente do brainstorm**: a fórmula que transforma "alíquota nominal + valor a
deduzir + percentual de repartição" em "quanto a empresa paga de cada tributo" NÃO está nos
Anexos XVIII-XXIII — está no **art. 18, §§1º, 1º-A e 1º-B da LC 123/2006** (redação dada pela LC
155/2016, verificada nesta sessão contra `planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm`):

> "Art. 18. O valor devido mensalmente [...] será determinado mediante aplicação das alíquotas
> efetivas, calculadas a partir das alíquotas nominais constantes das tabelas dos Anexos I a V
> desta Lei Complementar, sobre a base de cálculo de que trata o §3º deste artigo [...]
> § 1º Para efeito de determinação da alíquota nominal, o sujeito passivo utilizará a receita
> bruta acumulada nos doze meses anteriores ao do período de apuração.
> § 1º-A. A alíquota efetiva é o resultado de: RBT12 × Aliq − PD, em que:
> I - RBT12: receita bruta acumulada nos doze meses anteriores ao período de apuração;
> II - Aliq: alíquota nominal constante dos Anexos I a V desta Lei Complementar;
> III - PD: parcela a deduzir constante dos Anexos I a V desta Lei Complementar.
> § 1º-B. Os percentuais efetivos de cada tributo serão calculados a partir da alíquota efetiva,
> multiplicada pelo percentual de repartição constante dos Anexos I a V desta Lei Complementar
> [...]"

(Nota, RESOLVIDA nesta sessão: a extração de texto plano inicial mostrou "RBT12 × Aliq − PD" sem
divisão explícita. Inspecionando o HTML BRUTO de `planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm`
diretamente (não a extração de texto), confirma-se que "RBT12xAliq-PD" está marcado com `<u>`
(sublinhado) — a formatação visual padrão de fração em texto legal, onde o sublinhado funciona
como barra de fração — e é seguido, na mesma célula de tabela, por um segundo "RBT12" isolado,
antes do início da lista "em que: I - RBT12... II - Aliq... III - PD...". Isso confirma uma
fração empilhada: numerador `RBT12×Aliq−PD`, denominador `RBT12` — exatamente a fórmula usual e
publicamente documentada do Simples Nacional: **alíquota efetiva = (RBT12 × Aliq − PD) / RBT12**.
Não há mais pendência sobre esta fórmula.)

**Confirmado**: LC 227/2026 NÃO alterou o art. 18 da LC 123/2006 (a redação vigente é da LC
155/2016; as alterações da LC 227/2026 na LC 123/2006 concentram-se nos arts. 1º-3º, 12, 13, 17,
22, 25-26, 38-39 — a região do art. 18 não aparece na busca por "Lei Complementar nº 227" no
texto compilado do Planalto).

---

## Os 6 Anexos, verificados nesta sessão (LCP 214/2025, Anexos XVIII-XXIII)

### Tabela 1 — Faixas de receita bruta (comum a cada Anexo, 2 versões: 2027-2028 e 2029+)

**Anexo XVIII → LC 123/2006 Anexo I (Comércio)**

| Faixa | Receita Bruta em 12 Meses | Alíquota (27-28) | Alíquota (29+) | Valor a Deduzir |
|---|---|---|---|---|
| 1ª | Até 180.000,00 | 4,00% | 4,00% | – |
| 2ª | 180.000,01–360.000,00 | 7,30% | 7,30% | 5.940,00 |
| 3ª | 360.000,01–720.000,00 | 9,50% | 9,50% | 13.860,00 |
| 4ª | 720.000,01–1.800.000,00 | 10,70% | 10,70% | 22.500,00 |
| 5ª | 1.800.000,01–3.600.000,00 | 14,30% | 14,30% | 87.300,00 |
| 6ª | 3.600.000,01–4.800.000,00 | 18,90% | 19,00% | 378.000,00 |

**Anexo XIX → LC 123/2006 Anexo II (Indústria)**

| Faixa | Receita Bruta em 12 Meses | Alíquota (27-28) | Alíquota (29+) | Valor a Deduzir |
|---|---|---|---|---|
| 1ª | Até 180.000,00 | 4,50% | 4,50% | – |
| 2ª | 180.000,01–360.000,00 | 7,80% | 7,80% | 5.940,00 |
| 3ª | 360.000,01–720.000,00 | 10,00% | 10,00% | 13.860,00 |
| 4ª | 720.000,01–1.800.000,00 | 11,20% | 11,20% | 22.500,00 |
| 5ª | 1.800.000,01–3.600.000,00 | 14,70% | 14,70% | 85.500,00 |
| 6ª | 3.600.000,01–4.800.000,00 | 29,90% | 30,00% | 720.000,00 |

**Anexo XX → LC 123/2006 Anexo III (locação de bens móveis / serviços não listados no §5º-C) — redação dada pela LC 227/2026**

| Faixa | Receita Bruta em 12 Meses | Alíquota (27-28) | Alíquota (29+) | Valor a Deduzir |
|---|---|---|---|---|
| 1ª | Até 180.000,00 | 6,00% | 6,00% | – |
| 2ª | 180.000,01–360.000,00 | 11,20% | 11,20% | 9.360,00 |
| 3ª | 360.000,01–720.000,00 | 13,50% | 13,50% | 17.640,00 |
| 4ª | 720.000,01–1.800.000,00 | 16,00% | 16,00% | 35.640,00 |
| 5ª | 1.800.000,01–3.600.000,00 | 21,00% | 21,00% | 125.640,00 |
| 6ª | 3.600.000,01–4.800.000,00 | 32,90% | 33,00% | 648.000,00 |

**Anexo XXI → LC 123/2006 Anexo IV (serviços do §5º-C, sem CPP) — redação dada pela LC 227/2026**

| Faixa | Receita Bruta em 12 Meses | Alíquota (27-28) | Alíquota (29+) | Valor a Deduzir |
|---|---|---|---|---|
| 1ª | Até 180.000,00 | 4,50% | 4,50% | – |
| 2ª | 180.000,01–360.000,00 | 9,00% | 9,00% | 8.100,00 |
| 3ª | 360.000,01–720.000,00 | 10,20% | 10,20% | 12.420,00 |
| 4ª | 720.000,01–1.800.000,00 | 14,00% | 14,00% | 39.780,00 |
| 5ª | 1.800.000,01–3.600.000,00 | 22,00% | 22,00% | 183.780,00 |
| 6ª | 3.600.000,01–4.800.000,00 | 32,90% | 33,00% | 828.000,00 |

**Anexo XXII → LC 123/2006 Anexo V (serviços do §5º-I)**

| Faixa | Receita Bruta em 12 Meses | Alíquota (27-28) | Alíquota (29+) | Valor a Deduzir |
|---|---|---|---|---|
| 1ª | Até 180.000,00 | 15,50% | 15,50% | – |
| 2ª | 180.000,01–360.000,00 | 18,00% | 18,00% | 4.500,00 |
| 3ª | 360.000,01–720.000,00 | 19,50% | 19,50% | 9.900,00 |
| 4ª | 720.000,01–1.800.000,00 | 20,50% | 20,50% | 17.100,00 |
| 5ª | 1.800.000,01–3.600.000,00 | 23,00% | 23,00% | 62.100,00 |
| 6ª | 3.600.000,01–4.800.000,00 | 30,40% | 30,50% | 540.000,00 |

### Tabela 2 — Partilha percentual por tributo, por Anexo, por faixa, por ano (2027→2033 permanente)

Volume completo (6 Anexos × até 6 faixas × 7 pontos no tempo × até 6 tributos) transcrito
integralmente nesta sessão a partir do PDF oficial (ver arquivo de trabalho no scratchpad da
sessão, não versionado no repositório — a transcrição definitiva vai para a migração/tabela do
`/design`, não para este documento, por volume). Estrutura confirmada e amostras representativas:

- **Anexo XVIII (Comércio), 2027-2028, 1ª Faixa**: IRPJ 5,50% / CSLL 3,50% / CBS 15,33% / CPP
  41,50% / ICMS 34,00% / IBS 0,17%. **2033+ (permanente), 1ª/2ª Faixa**: IRPJ 5,50% / CSLL 3,50% /
  CBS 15,50% / CPP 41,50% / IBS 34,00% (ICMS zerado, absorvido integralmente pelo IBS).
- **Anexo XIX (Indústria)** tem coluna **IPI** adicional (7 tributos, não 6) — 2027-2028: CBS
  13,85% / IPI 7,50% / ICMS 32,00% / IBS 0,15% (1ª-5ª Faixa). 2033+: IBS assume os 32,00% do ICMS
  integralmente, IPI permanece 7,50%.
- **Anexo XX (locação/serviços gerais)**: única tabela (com o Anexo XXI) com **cláusula de teto
  de ISS** na 5ª Faixa — "o percentual efetivo máximo devido ao ISS será de X%, transferindo-se a
  diferença, de forma proporcional, aos tributos federais [e ao IBS, a partir de 2029] da mesma
  faixa". **Achado desta revisão (originalmente ausente da primeira passada do `/define`): os
  COEFICIENTES de redistribuição MUDAM todo ano** (não são fixos) — tabela completa, verificada
  linha a linha contra o PDF:

  | Ano | Teto ISS | IRPJ | CSLL | CBS | CPP | IBS |
  |---|---|---|---|---|---|---|
  | 2027-2028 | 5,00% | ×6,02% | ×5,26% | ×23,20% | ×65,26% | ×0,26% |
  | 2029 | 4,50% | ×5,73% | ×5,01% | ×22,33% | ×62,13% | ×4,80% |
  | 2030 | 4,00% | ×5,46% | ×4,78% | ×21,31% | ×59,29% | ×9,15% |
  | 2031 | 3,50% | ×5,23% | ×4,57% | ×20,38% | ×56,69% | ×13,13% |
  | 2032 | 3,00% | ×5,01% | ×4,38% | ×19,52% | ×54,32% | ×16,77% |

  Cada coeficiente multiplica `(alíquota efetiva − teto do ano)`; ISS fica fixo no teto do ano;
  gatilho é `alíquota efetiva > 14,92537%` (constante, não muda por ano) — 2033+ não tem mais
  cláusula de teto (tabela permanente já não inclui ISS).
- **Anexo XXI (serviços §5º-C)**: **sem coluna CPP** — só IRPJ/CSLL/CBS/ISS/IBS. Mesma cláusula
  de teto de ISS que o Anexo XX, na 5ª Faixa, com coeficientes PRÓPRIOS (diferentes do Anexo XX)
  que também mudam ano a ano — verificados linha a linha contra o PDF:

  | Ano | Teto ISS | IRPJ | CSLL | CBS | IBS |
  |---|---|---|---|---|---|
  | 2027-2028 | 5,00% | ×31,33% | ×32,00% | ×36,27% | ×0,40% |
  | 2029 | 4,50% | ×29,38% | ×30,00% | ×34,38% | ×6,25% |
  | 2030 | 4,00% | ×27,65% | ×28,24% | ×32,35% | ×11,76% |
  | 2031 | 3,50% | ×26,11% | ×26,67% | ×30,56% | ×16,67% |
  | 2032 | 3,00% | ×24,74% | ×25,26% | ×28,95% | ×21,05% |

  Gatilho `alíquota efetiva > 12,5%` (diferente do Anexo XX, e constante ano a ano). A célula de
  2029 (IRPJ/CSLL) inicialmente ficou ambígua na extração `-layout` do PDF (colunas coladas
  visualmente) — resolvida re-extraindo a mesma página com `pdftotext -raw` (que preserva a ordem
  de leitura em vez de tentar reconstruir colunas), confirmando a separação exata acima.
- **Anexo XXII (serviços §5º-I)**: sem cláusula de teto de ISS impressa no Anexo — 6 tributos
  plenos (IRPJ/CSLL/CBS/CPP/ISS/IBS) em todas as faixas.
- **6ª Faixa, todos os 5 Anexos "percentuais"**: só 4-5 tributos (IRPJ/CSLL/CBS/CPP, mais
  IPI só no Anexo XIX) — ICMS/ISS/IBS não aparecem na 6ª Faixa em nenhum dos anos capturados
  (achado a confirmar no `/design`, ver Open Questions — pode ser recolhimento à parte, fora do
  DAS, para a faixa mais alta).

**Anexo XXIII → LC 123/2006 Anexo VII (MEI) — valores fixos em R$, não percentuais**

| Vigência | ICMS | ISS | CBS | IBS | TOTAL |
|---|---|---|---|---|---|
| 2027–2028 | 1,00 | 5,00 | 0,994 | 0,006 | 7,00 |
| 2029 | 0,90 | 4,50 | 1,00 | 0,20 | 6,60 |
| 2030 | 0,80 | 4,00 | 1,00 | 0,40 | 6,20 |
| 2031 | 0,70 | 3,50 | 1,00 | 0,60 | 5,80 |
| 2032 | 0,60 | 3,00 | 1,00 | 0,80 | 5,40 |
| 2033 em diante | — | — | 1,00 | 2,00 | 3,00 |

Nota de republicação (DOU 23/1/2025), não alteração pela LC 227/2026. A 2033+ não tem
ICMS/ISS — só CBS+IBS somando R$3,00 (fim literal do documento, 298 páginas).

**Fonte:** LCP 214/2025, Anexos XVIII-XXIII, e LC 123/2006, art. 18, §§1º-1º-B (redação LC
155/2016). Anexos XX e XXI alterados pela LC 227/2026 (texto acima já é o vigente,
pós-alteração); os outros 4 não. Consultado em 2026-07-31.

---

## Success Criteria

- [ ] Conteúdo completo dos 6 Anexos (todas as faixas, todos os anos 2027-2033+, tabela do MEI)
      verificado contra fonte primária — concluído nesta sessão, cross-check de 2 fontes
- [ ] Fórmula de cálculo (alíquota efetiva, percentual efetivo por tributo) identificada e citada
      — LC 123/2006, art. 18, §§1º-A/1º-B — achado ausente do brainstorm
- [ ] Confirmado quais dos 6 Anexos a LC 227/2026 alterou (XX, XXI) e quais não (XVIII, XIX,
      XXII, XXIII), e que o art. 18 da LC 123/2006 não foi alterado
- [ ] Módulo novo de cálculo, Python puro, sem infraestrutura, implementando as 3 fórmulas
      verificadas (alíquota efetiva, partilha por tributo, teto de ISS onde aplicável)
- [ ] `/v1/tax/simulate` ganha campos de payload para opção pelo Simples Nacional, RBT12 e
      atividade — resultado cita Anexo/faixa/ano exatos
- [ ] Anexo XXI sem CPP nunca produz um percentual de CPP inventado
- [ ] Cláusula de teto de ISS (Anexos XX/XXI, 5ª Faixa) implementada com a fórmula exata
- [ ] Anexo XXIII (MEI) tratado como caminho de cálculo distinto (valor fixo, não percentual)
- [ ] `motor_calculo/engine.py`/`tabela_aliquotas.py` intocados
- [ ] Zero regressão: todas as features anteriores (IPI, 14 Anexos de redução, Imposto Seletivo,
      piso do Anexo XVI, regime vigente) continuam funcionando exatamente como hoje

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — Comércio, 1ª Faixa, 2027 | Empresa optante do Simples, atividade Comércio, RBT12 = R$150.000, `ano_operacao` 2027 | `POST /v1/tax/simulate` | 200; alíquota efetiva calculada a partir da fórmula do art. 18, §1º-A; partilha cita CBS=15,33%/IBS=0,17% da alíquota efetiva, dispositivo "LCP 214/2025, Anexo XVIII, 1ª Faixa; LC 123/2006, art. 18" |
| AT-002 | Indústria com IPI, 2033+ (regime permanente) | Atividade Indústria, RBT12 na 3ª Faixa, `ano_operacao` 2033 | `POST /v1/tax/simulate` | Partilha usa a tabela permanente (sem coluna ICMS, IBS absorve o percentual antigo do ICMS); IPI presente |
| AT-003 | Serviço Anexo IV (XXI) sem CPP | Atividade "serviço §5º-C", qualquer faixa | `POST /v1/tax/simulate` | Resposta não contém percentual de CPP para este Anexo — campo ausente/`None`, nunca zero |
| AT-004 | Teto de ISS acionado (Anexo XX, 5ª Faixa, alíquota efetiva alta) | Atividade "locação/serviços gerais", RBT12 na 5ª Faixa, receita que gera alíquota efetiva > 14,92537% (2027-2028) | `POST /v1/tax/simulate` | ISS fixado no teto do ano (5% em 2027-2028); diferença redistribuída a IRPJ/CSLL/CBS/CPP/IBS pelas proporções exatas verificadas nesta sessão |
| AT-005 | Teto de ISS NÃO acionado (mesma 5ª Faixa, alíquota efetiva abaixo do teto) | Mesmo Anexo/Faixa de AT-004, mas RBT12 menor | `POST /v1/tax/simulate` | Partilha usa os percentuais base da tabela, sem redistribuição |
| AT-006 | MEI — valor fixo, não percentual | Atividade "MEI", `ano_operacao` 2029 | `POST /v1/tax/simulate` | Resposta usa a tabela de valores fixos (CBS=R$1,00, IBS=R$0,20 para 2029) — nunca calculada como percentual de receita |
| AT-007 | MEI 2033+ sem ICMS/ISS | Atividade "MEI", `ano_operacao` 2033 | `POST /v1/tax/simulate` | Só CBS (R$1,00) e IBS (R$2,00) — sem campos de ICMS/ISS |
| AT-008 | 6ª Faixa sem ICMS/ISS/IBS (achado a confirmar no /design) | Qualquer atividade percentual, RBT12 na 6ª Faixa | `POST /v1/tax/simulate` | Resposta reflete literalmente a ausência desses tributos na 6ª Faixa (não inventa um percentual residual) — comportamento exato a decidir no `/design`, ver Open Questions |
| AT-009 | Payload sem opção pelo Simples Nacional | Payload padrão, sem os novos campos | `POST /v1/tax/simulate` | Comportamento idêntico ao de hoje (regime geral via `engine.py`) — os novos campos são aditivos e opcionais |
| AT-010 | RBT12 ausente mas opção pelo Simples marcada | Payload com opção pelo Simples, sem RBT12 | `POST /v1/tax/simulate` | 422 — não presume nenhuma faixa por omissão |
| AT-011 | Ano fora do intervalo coberto (< 2027) | Payload Simples Nacional, `ano_operacao` 2026 | `POST /v1/tax/simulate` | Resposta explícita de que a tabela do Simples com CBS/IBS só vale a partir de 2027 — nunca aplica a tabela errada |
| AT-012 | Zero regressão | Payload idêntico a qualquer teste já existente (14 Anexos de redução, IPI, Imposto Seletivo, piso do Anexo XVI) | `POST /v1/tax/simulate` | Resposta idêntica à de antes desta feature |

---

## Out of Scope

- **Cálculo do regime geral (IVA Dual) para empresas Simples Nacional** — são regimes mutuamente
  exclusivos; esta feature nunca combina os dois.
- **Verificação de elegibilidade ao Simples Nacional** (atividade permitida, sublimites
  estaduais, impedimentos do art. 3º/17 da LC 123/2006) — o payload é DECLARATÓRIO: a empresa
  informa que optou, a feature não valida se ela poderia.
- **Sublimites estaduais de ICMS/ISS** (art. 19/20 da LC 123/2006, faculdade dos Estados/DF de
  adotar sublimite de R$3,6 milhões) — fora de escopo, mesma disciplina de "não modelar exceção
  sem fonte única citável" já aplicada a `icms_interno`/`iss_faixa`.
- **Achado da 6ª Faixa sem ICMS/ISS/IBS declarado** — se o `/design` não conseguir confirmar
  contra fonte primária adicional (ex. §1º-B combinado com outro dispositivo) qual é o tratamento
  correto, a feature documenta como limitação explícita, nunca presume um percentual.
- **Recálculo retroativo/ajuste do art. 21, §1º da LC 123/2006** (mecanismo de ajuste do PGDAS
  quando a receita bruta real diverge da projetada) — fora de escopo, é mecânica de apuração
  posterior, não de simulação prospectiva.
- Qualquer Anexo de CBS/IBS por produto/serviço (posições 12-14), Anexo XVI (posição 15), Anexo
  XVII/Imposto Seletivo (posição 16) — tributos/mecanismos diferentes, já shipados.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/engine.py`/`tabela_aliquotas.py` não podem ser alterados — Simples Nacional é regime SUBSTITUTIVO, nunca uma redução | Módulo novo, isolado, análogo a `TabelaPisCofins`/`icms_interestadual` de `regime_atual.py` |
| Technical | A 6ª Faixa não declara ICMS/ISS/IBS em nenhum dos 5 Anexos percentuais, em nenhum ano capturado (achado não investigado a fundo nesta sessão) | `/design` decide se resolve com pesquisa adicional (ver Open Questions) ou documenta como limitação explícita |
| Technical | 3 caminhos de cálculo distintos: (a) 5 Anexos "percentuais" sem teto de ISS (XVIII, XIX, XXII); (b) 2 Anexos com teto de ISS (XX, XXI); (c) 1 Anexo de valor fixo (XXIII, MEI) | `/design` decide a forma exata do módulo — provavelmente 3 funções/caminhos, não uma função universal |
| Legal | Anexo XXI não tem coluna CPP | Nunca inventar um valor — campo ausente é o comportamento correto |
| Legal | Anexos XX e XXI alterados pela LC 227/2026; os outros 4 não | `/build` usa o texto já pós-alteração, capturado nesta sessão |
| Legal | 6ª Faixa sem ICMS/ISS/IBS declarado em nenhum dos Anexos "percentuais" | Achado a resolver no `/design` — ver Open Questions |
| Business | Maior mudança de contrato de API de toda a leva — campos novos no payload, não por item | Precisa de decisão explícita do `/design` sobre nomes/tipos de campo, mantendo compatibilidade retroativa (campos opcionais, comportamento idêntico ao de hoje quando ausentes) |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Módulo novo, Python puro, sem infraestrutura (`motor_calculo/simples_nacional.py` ou equivalente) — mesmo padrão de `regime_atual.py`/`piso_aliquota_ibs.py`, NÃO o padrão de tabela+migração Postgres usado pelos Anexos de redução | Estruturalmente mais próximo do Anexo XVI (Python puro) do que de qualquer Anexo NCM/NBS — os dados (6 Anexos × faixas × anos) cabem em estruturas Python, sem necessidade de banco |
| **KB Domains** | `python-developer` (módulo de tabela + função pura, mesmo padrão já validado 2 vezes), nenhum domínio de KB específico para Simples Nacional | Volume de dado grande, mas mecanismo (lookup determinístico) já validado |
| **IaC Impact** | Nenhuma — sem migração, sem Cloud SQL, sem `GRANT`, sem workflow modificado | Mesma propriedade do Anexo XVI: verificação só via `pytest`/`ruff`, já 100% local |

**Why This Matters:**

- **Location** → Diferente de toda feature NCM/NBS desta leva, o Simples Nacional não é um
  lookup por código de produto — é uma função de faixa + ano + fórmula, exatamente o padrão que
  `regime_atual.py` já usa para PIS/COFINS/ICMS.
- **IaC Impact** → Segunda feature do projeto inteiro (depois do Anexo XVI) sem nenhuma
  superfície de infraestrutura — nada para `migrar_banco.yml` verificar.

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexos XVIII-XXIII (`legis.senado.leg.br`, cross-check via PDF Câmara) | Texto legal | 6 Anexos, até 6 faixas × 7 pontos no tempo × até 7 tributos | Estático — tabela final "2033 em diante" é permanente | Legislativo Federal |
| LC 123/2006, art. 18, §§1º-1º-B (`planalto.gov.br`) | Texto legal (fórmula de cálculo) | 1 artigo + 3 parágrafos | Estático — redação da LC 155/2016, não alterada pela LC 227/2026 | Legislativo Federal |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Tabela de faixas por Anexo (2 versões: 2027-2028, 2029+) | 5 Anexos percentuais × 6 faixas | Sim |
| Tabela de partilha por Anexo × faixa × ano (2027→2033 permanente) | Volume maior de toda a leva | Sim |
| Tabela de valores fixos do MEI por ano | Estrutura própria, não percentual | Sim |
| Fórmula de alíquota efetiva e percentual por tributo | Implementação de função, não dado tabular | Sim |
| Fórmula de teto de ISS (Anexos XX/XXI, 5ª Faixa) | Implementação de função condicional | Sim |
| Ausência de CPP no Anexo XXI | Campo estruturalmente ausente | Sim |

### Freshness SLAs

Não aplicável — dado estático até 2033 (regime permanente depois disso), sem cláusula de revisão
periódica identificada nos Anexos nem no art. 18.

### Completeness Metrics

- 6/6 Anexos verificados contra fonte primária nesta sessão (100%), 5/6 com cross-check de duas
  fontes independentes (Anexo XX só tem uma fonte — WebFetch falhou integralmente nele)
- Fórmula de cálculo (art. 18, LC 123/2006) identificada e verificada por completo, inclusive a
  divisão por RBT12 (confirmada via inspeção do HTML bruto) — achado desta sessão, ausente do
  brainstorm original
- 1 item pendente de investigação antes do `/build`: por que a 6ª Faixa não declara ICMS/ISS/IBS
  (ver Open Questions)

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto dos 6 Anexos obtido via PDF da Câmara é o texto vigente | Toda a tabela de partilha estaria errada | [x] Validado nesta sessão — cross-check com legis.senado.leg.br em 5 dos 6 Anexos, e com a lista de alterações da LC 227/2026 |
| A-002 | A fórmula "RBT12 × Aliq − PD" do art. 18, §1º-A inclui uma divisão final por RBT12 | Se a divisão não existisse no texto oficial, a "alíquota efetiva" seria uma grandeza monetária, não uma alíquota — contradiria a própria nomenclatura do dispositivo | [x] Validado nesta sessão — HTML bruto de `planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm` confirma formatação de fração (numerador sublinhado + denominador "RBT12" na mesma célula): `(RBT12 × Aliq − PD) / RBT12` |
| A-003 | A 6ª Faixa (todos os Anexos percentuais) realmente não tem ICMS/ISS/IBS na partilha, não é um erro de transcrição | Se for erro, a partilha da 6ª Faixa estaria incompleta | [x] Validado no `/design` — LC 123/2006, art. 19, §4º: acima do "sublimite" de R$3.600.000,00 (exatamente o piso da 6ª Faixa), ICMS e ISS são recolhidos SEPARADAMENTE, fora do DAS, pelo regime geral — e por extensão o IBS (substituto de ICMS/ISS na reforma) segue a mesma exclusão. Não é lacuna de transcrição |
| A-004 | MEI não tem faixa de receita (limite único ~R$81.000/ano do MEI, diferente do limite geral do Simples) — a tabela do Anexo XXIII não referencia faixas | Se o MEI tiver sub-faixas não capturadas, a tabela estaria incompleta | [x] Confirmado nesta sessão — a tabela do Anexo XXIII é só por ano, sem coluna de faixa |

**Note:** A-002 e A-003, inicialmente bloqueantes do `/build`, foram ambas resolvidas ainda nesta
sessão (A-002 durante o `/define`, A-003 durante o `/design`) — nenhuma pendência bloqueante
remanescente.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Frase clara, quantifica os 6 Anexos e o achado central (dado já fixado, sem restrição de "alíquota indisponível") |
| Users | 3 | Dois usuários com pain points específicos e diferenciados |
| Goals | 3 | MoSCoW explícito; achados críticos (fórmula do art. 18, ausência de CPP no Anexo XXI, teto de ISS) são MUST, não escondidos |
| Success | 3 | Critérios testáveis e numéricos (6/6 Anexos, cross-check de 2 fontes em 5/6) |
| Scope | 2 | Uma questão (A-003, ausência de tributos na 6ª Faixa) fica deliberadamente aberta para o `/design`/`/build` — correta por não presumir a resposta, mas reduz a nota porque bloqueia parte do `/build` até ser fechada; a fórmula de alíquota efetiva (A-002), inicialmente aberta, foi resolvida nesta própria sessão |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** esta é, por volume de dado legal
verificado, a maior feature de toda a "segunda leva" — 6 Anexos × até 6 faixas × 7 pontos no
tempo, mais uma fórmula de cálculo (art. 18) que nenhum Anexo de redução anterior precisou (todos
eram lookup puro, sem fórmula). O WebFetch falhou de formas diferentes em 3 dos 6 Anexos
(recusa total, truncamento silencioso "termina em 2031" quando não terminava, omissão de
fórmulas), reforçando que o cross-check via PDF não é opcional para features deste porte.

---

## Open Questions

Uma bloqueia o `/build` (não o `/design`):

1. **Por que a 6ª Faixa não tem ICMS/ISS/IBS na partilha** — não investigado nesta sessão além de
   confirmar que a ausência é consistente nos 5 Anexos percentuais, em todos os anos capturados.
   Hipótese não verificada: pode ser recolhimento à parte, fora do DAS, para a faixa mais alta
   (análogo ao CPP do Anexo XXI) — `/design` decide se resolve com pesquisa adicional ou documenta
   como limitação.

Não bloqueiam o avanço para `/design`:

2. **Nome exato do módulo/campos de payload** (`simples_nacional.py`, nomes de
   `regime_tributario`/`receita_bruta_acumulada_12_meses`/`atividade`) — decisão do `/design`.
3. **Se os 6 Anexos entram como 1 função com muitos parâmetros ou 3 caminhos de cálculo
   distintos** (percentual simples / percentual com teto de ISS / valor fixo MEI) — decisão do
   `/design`, mas a recomendação desta sessão é 3 caminhos, dada a diferença estrutural real.
4. **Forma de armazenar os dados de 2033+ ("regime permanente")** — se as tabelas de anos ≥2033
   reusam literalmente a mesma estrutura de dados sem duplicar linha por ano indefinidamente.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-31 | define-agent | Versão inicial, extraída de `BRAINSTORM_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`. Verificação completa dos 6 Anexos (XVIII-XXIII) realizada nesta sessão via pesquisa dedicada, com cross-check de duas fontes independentes (legis.senado.leg.br + PDF da Câmara dos Deputados) em 5 dos 6 Anexos — WebFetch falhou de formas diferentes em 3 Anexos (recusa total no XX, truncamento silencioso no XIX e XXIII). Achado crítico ausente do brainstorm: a fórmula de cálculo (alíquota efetiva, percentual por tributo) não está nos Anexos da LCP 214/2025 — está no art. 18, §§1º-1º-B da LC 123/2006, verificado nesta sessão contra o texto compilado do Planalto, inclusive a divisão por RBT12 (confirmada por inspeção do HTML bruto, que a extração de texto plano tinha comido). Confirmado que a LC 227/2026 alterou só os Anexos XX e XXI (não os outros 4) e não alterou o art. 18. Uma questão aberta (ausência de ICMS/ISS/IBS na 6ª Faixa) documentada como bloqueante do `/build`, não do `/design`. |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_SIMPLES_NACIONAL_CBS_IBS_TRANSICAO.md`
