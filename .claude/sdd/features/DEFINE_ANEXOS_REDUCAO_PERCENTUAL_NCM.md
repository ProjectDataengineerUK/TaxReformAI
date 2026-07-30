# DEFINE: Anexos IV, V, VI, VII, VIII e IX — Redução de 60% de CBS/IBS por NCM

> Estender `/v1/tax/simulate` para os 6 Anexos de 60% da LCP 214/2025 cuja chave de
> correspondência é predominantemente NCM/SH — introduzindo o primeiro mecanismo de cálculo
> **novo** desde o Anexo I (redução PERCENTUAL, não a zero) — e tratar explicitamente o achado
> crítico desta sessão: 3 dos 6 Anexos (IV, V, VI) não são "60% incondicional".
>
> **Posição na sequência:** 13 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Roda depois da posição 12 (`ANEXOS_REDUCAO_ZERO_XII_XIII_XV`, shipada
> 2026-07-29), cujo `/design` já registrou o achado que esta sessão confirma e amplia (ver
> "Achado crítico" abaixo).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NCM |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | Designed — ver [DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NCM.md](./DESIGN_ANEXOS_REDUCAO_PERCENTUAL_NCM.md) (2026-07-29). **Atenção:** o `/design` refutou `A-003` (existem 117 pares de sobreposição entre estes 6 Anexos e os 4 já shipados, não zero) e corrigiu 3 contagens (Anexo V 26→29 itens; item 7 do Anexo IX 28→29 códigos; 13 códigos do Anexo IV não são de 8 dígitos) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Seis Anexos da LCP 214/2025 (IV, V, VI, VII, VIII, IX — 271 itens verificados nesta sessão, não
os ~322 estimados pelo brainstorm) reduzem CBS/IBS a **60%** do valor da fase para dispositivos
médicos, acessibilidade, nutrição enteral/parenteral, alimentos, higiene/limpeza e insumos
agropecuários — mas `/v1/tax/simulate` não tem nenhum conceito de redução **percentual** (só a
redução a zero, já shipada para os Anexos I/XII/XIII/XV). Pior: a verificação desta sessão contra
o texto vigente encontrou que **3 desses 6 Anexos (IV, V e VI) não são "60% incondicional"** — os
arts. 144-II, 145-II e 146 §2 da própria lei reduzem a **zero**, não a 60%, quando o produto é
adquirido por órgão público ou entidade de saúde com CEBAS. Sem tratar essa condição
explicitamente, o simulador continuaria superestimando a carga tributária de todo o grupo (hoje,
por não ter nenhuma redução) e, pior, poderia subestimá-la se um `/design` ingênuo assumisse
"60% sempre" para IV/V/VI sem checar o comprador.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Simula dispositivos médicos, produtos de acessibilidade, nutrição clínica, alimentos, higiene e insumos agropecuários com a alíquota geral da fase, quando a lei já garante 60% de redução — ou, para compras de órgãos públicos/entidades CEBAS, redução a **zero** — para esses produtos especificamente |
| Controller/CFO usando o simulador | Consumidor indireto do produto (via ERP ou frontend) | Não consegue demonstrar o benefício fiscal real de setores sensíveis (saúde, alimentação, higiene, agropecuária) numa simulação que se propõe auditável; pior, se comprador for órgão público, precisa saber que a redução correta é maior (zero) do que a "genérica" de 60% |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo completo dos 6 Anexos (IV: 105 itens, V: 26, VI: 81, VII: 17, VIII: 7, IX: 35 — total **271**, verificado nesta sessão, corrigindo as estimativas aproximadas do brainstorm, que eram ~79/~23/~66/~51/~9/~94) verificado contra fonte primária — ver "Os 6 Anexos, verificados nesta sessão" |
| **MUST** | Nova função de cálculo `aplicar_reducao_percentual` (ou equivalente) implementada em `motor_calculo/reducoes.py`, multiplicando CBS/IBS por `(1 - 0,60)` e mantendo o IS intocado — decisão exata de assinatura/generalização (função nova vs. `aplicar_reducao_a_zero(percentual=1.0)`) fica para o `/design`, mas a MULTIPLICAÇÃO por um percentual arbitrário (não só 0 ou 1) é requisito, porque o achado abaixo introduz um TERCEIRO percentual efetivo (zero) para o mesmo Anexo |
| **MUST** | **Achado crítico desta sessão, que muda a classificação do roadmap: Anexos IV, V e VI NÃO são "60% incondicional".** Arts. 144-II (Anexo IV), 145-II (Anexo V) e 146 §2 (Anexo VI) da LCP 214/2025 reduzem a **ZERO** — não a 60% — quando o produto é adquirido por (a) órgão da administração pública direta, autarquia ou fundação pública, ou (b) entidade de saúde imune ao IBS/CBS com CEBAS comprovando prestação de serviços ao SUS. Isso é uma condição sobre o **comprador**, que o payload atual de `/v1/tax/simulate` não expressa (nenhum campo `comprador_tipo` ou similar existe hoje). O `/design` DEVE decidir explicitamente como tratar essa lacuna — nunca assumir "sempre 60%" nem "sempre zero" silenciosamente. Ver "Achado crítico: redução condicionada ao comprador" |
| **MUST** | Precedência normativa explícita entre os 4 Anexos ZERO já shipados (I, XII, XIII, XV) e estes 6 Anexos de 60%: nenhum NCM que já recebe zero por outro Anexo pode receber 60% por engano. Cobre a remissão textual EXPLÍCITA do Anexo VII — **5 itens** (4, 5, 6, 14 e 15 — não só os itens 4/5 que o brainstorm supunha) remetem ao Anexo I ("ressalvados os produtos relacionados no Anexo I"), e o item 14 remete TAMBÉM ao Anexo XV |
| **MUST** | Confirmado nesta sessão, contra fonte primária, que a LC 227/2026 alterou **só o Anexo VII** entre os 6 (tentativa de nova redação ao item 2, **integralmente VETADA** — sem efeito, o item 2 permanece com o texto original) — nenhum dos outros 5 Anexos (IV, V, VI, VIII, IX) nem os artigos que os regem (131, 132, 136, 137, 138) foram tocados. O art. 146 (medicamentos) foi alterado, mas a cláusula que beneficia o Anexo VI (o então/atual §2) é substancialmente idêntica antes e depois — não é uma alteração introduzida por esta LC, é achado independente desta sessão |
| **MUST** | Itens de chave NBS do Anexo IX (itens 22 a 33 — **12 itens**, "Serviços agronômicos" etc.) documentados como não resolvidos nesta feature — nunca tratados como "NCM não encontrado" silencioso. O item 34 do Anexo IX ("Melhoramento genético de animais e plantas e biotecnologia, inclusive seus royalties") **não cita nenhum código, nem NCM nem NBS** — é uma limitação distinta (nenhuma chave citável), documentada separadamente |
| **MUST** | Itens de mercadoria cujo NCM não bate com nenhum item dos 6 Anexos (nem dos 4 já shipados) continuam recebendo a alíquota geral da fase — zero regressão nos 4 Anexos zero, no IPI e no regime vigente |
| **MUST** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura |
| **SHOULD** | Verificação programática de overlap entre os 6 novos Anexos entre si e com os 4 já shipados — o volume (271 itens, ~4,5× o volume da feature anterior) torna a inspeção manual exaustiva pouco confiável; recomendado ainda mais fortemente que na feature anterior (onde já era `SHOULD`) |
| **SHOULD** | O "diferimento" do art. 138 §2 (Anexo IX — adiamento do recolhimento de IBS/CBS em certas cadeias B2B/produtor rural não contribuinte) documentado como identificado e **fora do mecanismo de redução** — não é uma alíquota menor, é um adiamento de pagamento; nenhuma ação de cálculo é exigida nesta feature, mas a distinção deve ficar registrada para não ser confundida com "redução percentual" num `/design` apressado |
| **SHOULD** | Estrutura "Capítulos X, Y e Z" — um único item do Anexo IX citando **dois ou mais** capítulos de 2 dígitos ao mesmo tempo (itens 10 e 19: "Capítulos 7, 10 e 12" e "Capítulos 10, 11 e 12") — documentada para o `/design` generalizar a geração de linhas de prefixo por item; o mecanismo 1:N já existe, mas nunca precisou emitir múltiplos prefixos do MESMO comprimento curto (2 dígitos) para um único item |
| **COULD** | Confirmar contra a TIPI já ingerida (`aliquotas_ipi_tipi`) se as cláusulas "exceto" não-codificáveis do Anexo IX (6 ocorrências, todas "exceto de animais domésticos"/"exceto as ornamentais" — nenhuma cita código) e as 6 do Anexo IV (todas DESCRITIVAS — o próprio código do item já é distinto do que a cláusula exclui) são de fato inócuas, mesmo tratamento dado ao Anexo XII item 5 |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

Mesma fonte já qualificada nas duas features anteriores (Anexo I e Anexos XII/XIII/XV): o portal
oficial do Senado Federal (`legis.senado.leg.br`), espelho da "Publicação Original" do DOU.
`planalto.gov.br` continua inacessível deste ambiente. O acesso só respondeu 200 com um header de
`User-Agent` de navegador — sem ele, 403 (aviso herdado, confirmado novamente nesta sessão).

**O que foi verificado, com URL e conteúdo real, nesta sessão (2026-07-29):**

1. **Texto integral dos 6 Anexos**, cada um sua própria "Publicação de Anexo" (DOU Edição Extra
   nº 11-B de 16/01/2025):
   - Anexo IV: `https://legis.senado.leg.br/norma/40180341/publicacao/40180906` (p. 48, col. 1) — HTTP 200
   - Anexo V: `https://legis.senado.leg.br/norma/40180341/publicacao/40180912` (p. 50, col. 1) — HTTP 200
   - Anexo VI: `https://legis.senado.leg.br/norma/40180341/publicacao/40180918` (p. 50, col. 1) — HTTP 200
   - Anexo VII: `https://legis.senado.leg.br/norma/40180341/publicacao/40180967` (p. 51, col. 1) — HTTP 200
   - Anexo VIII: `https://legis.senado.leg.br/norma/40180341/publicacao/40180973` (p. 51, col. 1) — HTTP 200
   - Anexo IX: `https://legis.senado.leg.br/norma/40180341/publicacao/40180979` (p. 51-52, col. 1) — HTTP 200
2. **Corpo da LCP 214/2025** (arts. 1º a 544), mesma URL já usada nas duas features anteriores:
   `https://legis.senado.leg.br/norma/40180341/publicacao/40181429` — HTTP 200. Lidos os arts.
   129-142 (Capítulo III, "Da Redução de 60%") e 143-148 (Capítulo IV, "Da Redução a Zero") na
   íntegra, não só os artigos já citados por features anteriores.
3. **Página de detalhe da norma** (`https://legis.senado.leg.br/norma/40180341`) — lista completa
   de "Normas posteriores": a LC 227/2026 alterou, entre Anexos, **só** "Anexo 7 — Alteração
   Vetada", "Anexo 14 — Revogação", "Anexo 20 — Alteração" e "Anexo 21 — Alteração". Entre
   artigos do intervalo relevante a esta feature, só **"Art. 146 — Alteração"** (nenhum dos arts.
   129-142, 144, 145, 147, 148).
4. **Mensagem de Veto Parcial nº 36/2026** (`https://legis.senado.leg.br/norma/42042155`) e o texto
   publicado da própria **LC 227/2026** (`https://legis.senado.leg.br/norma/42042119/publicacao/42042119`… texto em
   `.../publicacao/42256084`) — lidos para confirmar o CONTEÚDO da alteração/veto ao Anexo VII e ao
   art. 146, não só a existência do rótulo "Alteração"/"Veto" na lista.

Consultados em 2026-07-29.

**Cinco achados de fonte primária que o brainstorm não tinha:**

1. **As contagens do brainstorm estavam sistematicamente erradas**, em ambas as direções — ver
   tabela na próxima seção. Os maiores desvios: Anexo VII (~51 estimado → **17** reais, o Anexo
   é o mais textual/menos tabular dos 6, sem coluna de NCM separada) e Anexo IX (~94 estimado →
   **35** reais, mas com o item mais denso de código de qualquer Anexo já visto no projeto: o
   item 7 sozinho cita **28** códigos/prefixos). Anexo IV (~79 → **105**) e Anexo VI (~66 → **81**)
   foram subestimados.
2. **Anexos IV, V e VI têm uma condição de redução a ZERO amarrada ao comprador**, nos arts.
   144-II, 145-II e 146 §2 — ver seção dedicada abaixo. O `/design` de `ANEXOS_REDUCAO_ZERO_
   XII_XIII_XV` já tinha achado isso para IV e V (por causa do art. 144/145 caput, que ele
   precisava ler de qualquer forma para os Anexos XII/XIII); esta sessão **confirma esse achado
   de forma independente** e **encontra um terceiro caso** (Anexo VI, art. 146 §2) que a sessão
   anterior não tinha motivo para investigar (o art. 146 rege o Anexo XIV, fora do escopo dela).
3. **A LC 227/2026 tentou alterar o item 2 do Anexo VII, e a alteração foi INTEGRALMENTE
   VETADA** — o texto publicado da LC 227/2026 mostra literalmente `"ANEXO VII ... 2(VETADO) ...
   ” (NR)"`, ou seja, a nova redação proposta para o item 2 nunca entrou em vigor. O item 2 vigente
   é o texto ORIGINAL (já transcrito nesta sessão): "Leite fermentado, bebidas e compostos
   lácteos [...] classificados nos códigos 0403.20.00, 0403.90.00 e 2202.99.00". Nenhuma "Norma
   posterior" à própria LC 227/2026 registra derrubada de veto — o veto foi publicado no mesmo
   dia da sanção (14/01/2026) e permanece o estado vigente.
4. **O art. 146 foi de fato alterado pela LC 227/2026 — mas não na cláusula que interessa a esta
   feature.** A mudança substitui o mecanismo de zero-rate de medicamentos "por lista" (Anexo XIV,
   agora revogado) por um mecanismo "por categoria terapêutica" (doenças raras, negligenciadas,
   oncologia, diabetes, HIV/aids, cardiovasculares, Farmácia Popular). O §2 do artigo — que
   estende a redução a zero às composições do **Anexo VI** quando adquiridas por órgão
   público/CEBAS — está presente e é **substancialmente idêntico** nas versões antes e depois da
   LC 227/2026 (mesmos dois incisos de comprador, mesma remissão ao Anexo VI). Ou seja: o achado
   do item 2 acima é o único efeito real da LC 227/2026 sobre o conteúdo dos 6 Anexos desta
   feature.
5. **O art. 137 não pertence a este grupo.** Existe uma redução de 60% a produtos "agropecuários,
   aquícolas, pesqueiros, florestais e extrativistas vegetais **in natura**" (art. 137) que **não
   cita nenhum Anexo** — é definida por categoria ("in natura", com §§ 1-3 definindo o conceito),
   não por lista de NCM. Isso é estruturalmente diferente dos 6 Anexos desta feature (todos
   remetem a uma lista fechada) e **fica fora de escopo aqui** — é candidato a uma feature própria
   futura (mecanismo de correspondência por "natureza do produto", não por código), registrado
   para o roadmap.

---

## Os 6 Anexos, verificados nesta sessão

**Contagens exatas (substituindo as estimativas aproximadas do brainstorm):**

| Anexo | Assunto | Artigo que rege (60%) | Itens (brainstorm → real) | Estrutura |
|-------|---------|------------------------|------------------------------|-----------|
| IV | Dispositivos médicos | art. 131 | ~79 → **105** | Flat (sem sub-item), tabela ITEM/DESCRIÇÃO/NCM-SH, todos EXATO (8 dígitos), 6 cláusulas "exceto" — todas DESCRITIVAS |
| V | Acessibilidade | art. 132 | ~23 → **26** | 3 itens-cabeçalho (1, 2, 3) sem NCM próprio + sub-itens decimais (1.1-1.13, 2.1-2.10, 3.1-3.3) — mesmo padrão do Anexo XIII já shipado (Decisão 7 do `/design` anterior) |
| VI | Nutrição enteral/parenteral | art. 133 §1º | ~66 → **81** | Flat, todos EXATO, **nenhuma** cláusula "exceto"/"ressalvado" — o mais simples dos 6 em termos de exceção |
| VII | Alimentos | art. 135 | ~51 → **17** | Tabela de **2 colunas** (sem NCM separado, como o Anexo XV já shipado), a maior densidade de texto/exceção dos 6 — ver seção dedicada |
| VIII | Higiene/limpeza | art. 136 | ~9 → **7** | Flat, todos EXATO, nenhuma exceção — o mais simples dos 6 em volume |
| IX | Insumos agropecuários/aquícolas | art. 138 | ~94 → **35** | **Misto** (NCM dominante + NBS + 1 item sem código) — ver seção dedicada; densidade de código por item muito maior que qualquer Anexo anterior (item 7 sozinho cita 28 códigos/prefixos) |

**Total: 271 itens** (não os ~322 do brainstorm). Nenhum código foi aceito de memória — todos os 6
Anexos foram lidos integralmente nesta sessão.

### Anexo IV — Dispositivos médicos (105 itens, todos EXATO)

Tabela de 3 colunas (ITEM/DESCRIÇÃO/NCM-SH), numeração flat de 1 a 105, sem sub-item decimal.
Alguns itens citam **mais de um código** de 8 dígitos na mesma célula (ex.: item 12 —
"Conjunto para hidrocefalia standard" — cita `9021.90.19` e `9021.90.80`; itens 37, 42, 48, 68 e
102 também citam 2 códigos cada). 6 cláusulas "exceto"/"excluídas" (itens 48, 49, 51, 54, 61, 68) —
**todas DESCRITIVAS**: em cada uma, o próprio código do item já é de 8 dígitos e distinto de tudo
que a cláusula exclui (ex.: item 51 "Produtos para obturação dentária, exceto cimentos" tem código
`3006.40.12`, e "cimentos" já é o item 4, código `3006.40.20` — são siblings sob o mesmo prefixo
de 6 dígitos, nunca colidem). Nenhuma linha de exclusão é necessária, mesmo padrão do Anexo XII
(itens 1.3/11) já shipado.

**Fonte:** `LCP 214/2025, art. 131, Anexo IV`.

### Anexo V — Acessibilidade (26 itens: 3 cabeçalhos + 23 sub-itens, todos EXATO)

Estrutura idêntica em espírito à do Anexo XIII já shipado: os itens **1** ("Acessórios e
adaptações especiais para veículos..."), **2** ("Produtos destinados a uso de pessoa com
deficiência visual") e **3** ("Produtos destinados ao uso de pessoas com deficiência auditiva")
são **cabeçalhos sem NCM próprio** — o código mora exclusivamente nos sub-itens (1.1-1.13, 10 e 13
respectivamente; 2.1-2.10; 3.1-3.3). Alguns sub-itens citam múltiplos códigos (ex.: 2.2 "Relógio
em braille..." cita 3 códigos: `9102.11.10`, `9102.11.90`, `9102.91.00`). Nenhuma exceção.

**Fonte:** `LCP 214/2025, art. 132, Anexo V`.

### Anexo VI — Nutrição enteral/parenteral (81 itens, todos EXATO, sem exceção)

Lista flat de substâncias/compostos químicos e fórmulas nutricionais (ex.: item 1 "Acetato de
dextroalfatocoferol", `2936.28.12`). Vários itens citam 2 códigos (ex.: item 26 "Cloreto de
cálcio" — `2827.20.10` e `2827.20.90`). **Nenhuma cláusula "exceto"/"ressalvado" em todo o
Anexo** — o mais simples dos 6 nessa dimensão, mesmo sendo o segundo maior em volume.

**Fonte:** `LCP 214/2025, art. 133 §1º, Anexo VI` — **e art. 146 §2** para a condição de zero-rate
por comprador (ver "Achado crítico" abaixo).

### Anexo VII — Alimentos (17 itens — não ~51 — a maior complexidade textual dos 6)

Tabela de **2 colunas** (ITEM/DESCRIÇÃO DO PRODUTO), sem coluna de NCM separada — mesmo padrão do
Anexo XV já shipado. Os 17 itens, com tipo e achados:

| Item | Descrição (resumida) | Código(s)/prefixo(s) | Achado |
|------|------------------------|--------------------------|--------|
| 1 | Crustáceos/moluscos, `0306.1`/`0306.3` (exceto subposição `0306.11` e 4 códigos) e `0307.31/32/42/43/51/52/91/92` | PREFIXO + EXCEÇÃO operante | Exceção real (os códigos excluídos são descendentes do prefixo incluído) |
| 2 | Leite fermentado/bebidas/compostos lácteos, `0403.20.00`/`0403.90.00`/`2202.99.00` | EXATO (3 códigos) | **Alvo do veto da LC 227/2026** — texto vigente é o ORIGINAL, não alterado |
| 3 | Mel natural, `0409.00.00` | EXATO | — |
| 4 | Farinha, `1101.00`/`11.02`/`11.05`/`11.06`/`12.08` | PREFIXO | **Ressalvados os produtos do Anexo I** |
| 5 | Grumos e sêmolas, `1103.11.00`/`1103.19.00` | EXATO (2) | **Ressalvados os produtos do Anexo I** |
| 6 | Grãos de cereais, `1104.1`/`1104.2` | PREFIXO | **Ressalvados os produtos do Anexo I** |
| 7 | Amido de milho, `1108.12.00` | EXATO | — |
| 8 | Óleos vegetais, `1507.90`/`15.08`/`15.11`-`15.15` | PREFIXO | — |
| 9 | Massas alimentícias, `1902.20.00`/`1902.30.00` | EXATO (2) | — |
| 10 | Sucos naturais, `20.09` | PREFIXO | — |
| 11 | Polpas de fruta, `20.08` | PREFIXO | — |
| 12 | Pão de forma, `1905.90.10` | EXATO | — |
| 13 | Extrato de tomate, `2002.90.00` | EXATO | — |
| 14 | Frutas/hortícolas/vegetais, capítulos **7 e 8**, exceto posições `07.11`/`08.12`/`0814.00.00` | PREFIXO (2 dígitos ×2) + EXCEÇÃO operante | **Ressalvados os produtos dos Anexos I E XV** — o único item do grupo que remete a 2 Anexos zero |
| 15 | Cereais (capítulo 10) e oleaginosas (capítulo 12) | PREFIXO (2 dígitos ×2) | **Ressalvados os produtos do Anexo I** |
| 16 | Hortícolas pré-cozidos, `20.04`/`20.05`/`2002.10.00` | PREFIXO | — |
| 17 | Fruta de casca rija regional/amendoins torrados, `2008.1` | PREFIXO | — |

**Achado**: **5 itens** (4, 5, 6, 14, 15) — não os 2 que o brainstorm supunha — remetem
explicitamente ao Anexo I ("ressalvados os produtos relacionados no Anexo I"), e o item 14 remete
adicionalmente ao Anexo XV. Isso é uma hierarquia normativa **escrita na lei**, não um desempate
técnico: para qualquer NCM que caia num desses 5 itens E no Anexo I (ou, no caso do item 14,
também no XV), o zero do Anexo I/XV vence — nunca o 60% do Anexo VII.

**Fonte:** `LCP 214/2025, art. 135, Anexo VII`. LC 227/2026 tentou alterar o item 2; vetada.

### Anexo VIII — Higiene/limpeza (7 itens — não ~9 — todos EXATO, sem exceção)

O menor e mais simples dos 6: sabão de toucador (`3401.11.90`), dentifrício (`3306.10.00`),
escova de dente (`9603.21.00`), papel higiênico (`4818.10.00`), água sanitária (`3808.94.19`),
sabão em barra (`3401.19.00`), fraldas/artigos higiênicos (`9619.00.00`). Nenhuma exceção, nenhum
prefixo — todos correspondência exata de 8 dígitos.

**Fonte:** `LCP 214/2025, art. 136, Anexo VIII`.

### Anexo IX — Insumos agropecuários/aquícolas (35 itens — não ~94 — MISTO, o mais complexo dos 6)

Cabeçalho oficial "NBS / NCM/SH" confirmado. Estrutura real, verificada item a item nesta sessão:

- **Itens 1-21 e 35 (22 itens): chave NCM**, em escopo desta feature. Densidade de código muito
  maior que qualquer Anexo já visto: o item 7 sozinho cita **28** códigos/prefixos distintos
  (comprimentos 2, 4 e 8 dígitos misturados na mesma célula); os itens 10 e 19 citam **múltiplos
  capítulos de 2 dígitos no mesmo item** ("Capítulos 7, 10 e 12"; "Capítulos 10, 11 e 12") — um
  padrão nunca visto nos Anexos já shipados (lá, um item tinha no máximo 1 prefixo curto).
- **Itens 22-33 (12 itens): chave NBS** ("Serviços agronômicos", "Serviços de técnico agrícola",
  "Serviços veterinários para produção animal", "Serviços de zootecnistas", "Serviços de
  inseminação e fertilização de animais de criação", "Serviços de engenharia florestal",
  "Serviços de pulverização e controle de pragas", "Serviços de semeadura, adubação...",
  "Serviços de projetos para irrigação e fertirrigação", "Serviços de análise laboratorial...",
  "Licenciamento de direitos sobre cultivares", "Cessão definitiva de direitos sobre cultivares")
  — **fora de escopo desta feature**, documentados como não resolvidos, mesmo padrão dos itens
  19/20 do Anexo I.
- **Item 34 ("Melhoramento genético de animais e plantas e biotecnologia, inclusive seus
  royalties"): NENHUM código citado** — nem NCM nem NBS, célula vazia na fonte primária. É uma
  limitação DIFERENTE das duas acima (não é "chave errada", é "sem chave nenhuma") — documentada
  separadamente, nunca tratada como um erro de transcrição.
- **6 cláusulas "exceto"** (itens 12, 13, 18, 19, 20, 21) — todas do tipo NÃO CODIFICÁVEL
  ("exceto de animais domésticos", "exceto as ornamentais"): nenhuma nomeia um código NCM,
  mesma classe já estabelecida pela Decisão 6 do `/design` da feature anterior para "exceto os
  dentários" do Anexo XII.
- **Art. 138 §2º** (não no Anexo, no corpo do artigo): um **diferimento** do recolhimento de
  IBS/CBS em certas cadeias de fornecimento com produtor rural não contribuinte — **não é uma
  redução de alíquota**, é adiamento de pagamento. Fica fora do mecanismo desta feature, registrado
  para não ser confundido com "percentual" num `/design` apressado.

**Fonte:** `LCP 214/2025, art. 138, Anexo IX`.

---

## Achado crítico: redução condicionada ao comprador (Anexos IV, V e VI)

A leitura integral dos arts. 129-148 nesta sessão confirma e amplia o achado já registrado pelo
`/design` da feature anterior (que via de relance os arts. 144/145 ao verificar os Anexos XII/XIII):

| Anexo | Artigo do "60% padrão" | Artigo/inciso do "zero condicionado" | Condição do comprador |
|-------|--------------------------|------------------------------------------|--------------------------|
| IV | art. 131 | **art. 144, II** | a) órgão da administração pública direta, autarquia, fundação pública; ou b) entidade de saúde imune ao IBS/CBS com CEBAS (comprovando serviço ao SUS, LC 187/2021 arts. 9º-11) |
| V | art. 132 | **art. 145, II** | idem |
| VI | art. 133 §1º | **art. 146 §2º** | idem (remete aos mesmos incisos I/II do §1º do art. 146) |

Nos três casos, a estrutura é a MESMA: o artigo "genérico" (131/132/133) fixa 60% como regra geral
para todo mundo; um artigo do Capítulo IV ("Da Redução a Zero") cria uma exceção que zera a
alíquota especificamente quando o adquirente é um dos dois tipos de comprador acima — para o
MESMO Anexo (IV, V ou VI), não um Anexo separado.

**Por que isso é um problema de payload, não só de dado**: `POST /v1/tax/simulate` hoje não tem
nenhum campo que identifique o tipo de comprador (nem "pessoa física/jurídica", nem "órgão
público", nem "CEBAS"). Sem esse campo:

- Aplicar 60% incondicionalmente a IV/V/VI **superestima** a tributação de qualquer compra feita
  por um órgão público ou entidade CEBAS (que deveria ser zero) — o mesmo tipo de erro "para cima"
  que o projeto já aceita como direção seguro de degradação em outros pontos.
- Mas **assumir zero por padrão seria pior**: subestimaria a tributação de qualquer compra privada
  comum (a grande maioria), o que a disciplina do projeto ("nunca estimar/presumir") proíbe
  taxativamente.

**Recomendação explícita para o `/design`** (decisão não tomada aqui, mas o problema não pode
ficar sem tratamento): a opção mais alinhada ao padrão já usado em `regime_apuracao` (`None`
= "não informado", nunca um default silencioso) é acrescentar um campo opcional ao payload (ex.
`comprador_tipo: "PUBLICO" | "CEBAS" | None`), usado **só** para decidir entre 60% (padrão, sem
informação) e zero (quando o campo indicar explicitamente um comprador qualificado). A alternativa
— não tratar nesta feature e documentar como limitação conhecida (like o Capítulo 6 do Anexo XV) —
é aceitável **apenas se** a resposta deixar explícito, por produto, que a redução aplicada
(60%) pode ser maior (zero) dependendo do comprador, e que o payload atual não permite verificar
essa condição. **O que não é aceitável** é o silêncio: nem a implementação nem a documentação
podem tratar IV/V/VI como "60% sempre" sem essa ressalva.

---

## Success Criteria

- [ ] Conteúdo dos 6 Anexos (271 itens) verificado contra fonte primária, com URLs e data de
      acesso registrados neste documento — concluído nesta sessão
- [ ] Confirmado contra fonte primária que a LC 227/2026 alterou só o Anexo VII (item 2, vetado)
      entre os 6 — concluído nesta sessão
- [ ] `aplicar_reducao_percentual` (ou equivalente) implementada em `motor_calculo/reducoes.py`,
      sem alterar `aplicar_reducao_a_zero`
- [ ] `/v1/tax/simulate` aplica 60% aos itens de mercadoria cujo NCM bate com um item resolvido de
      IV/V/VI/VII/VIII/IX, citando o Anexo e item exatos
- [ ] Precedência normativa explícita: nenhum NCM que já recebe zero por I/XII/XIII/XV recebe 60%
      por um destes 6 Anexos — cobrindo em particular os 5 itens do Anexo VII com remissão ao
      Anexo I (e o item 14, também ao Anexo XV)
- [ ] Decisão explícita e documentada (no `/design`) sobre o tratamento da condição de comprador
      para Anexos IV/V/VI — nunca "60% incondicional" tratado como fato assumido
- [ ] Itens de chave NBS do Anexo IX (12 itens) documentados como não resolvidos; item 34 (sem
      nenhuma chave) documentado como limitação distinta
- [ ] Zero regressão: os 4 Anexos zero, o IPI e o regime vigente continuam funcionando exatamente
      como hoje
- [ ] `motor_calculo/` não ganha dependência de infraestrutura

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — 60% simples (Anexo VIII) | `ncm = "3401.11.90"` (sabão de toucador, item 1) | `POST /v1/tax/simulate` | 200; CBS/IBS reduzidos a 60% do valor da fase; fonte citada "LCP 214/2025, Anexo VIII, item 1" |
| AT-002 | Precedência — Anexo I vence sobre Anexo VII | `ncm` de um item do Anexo VII que também está listado no Anexo I (ex.: um código de farinha do item 4 do Anexo VII que coincide com item do Anexo I) | `POST /v1/tax/simulate` | CBS/IBS **zero**, citando "Anexo I", NUNCA 60% citando "Anexo VII" |
| AT-003 | Remissão dupla (Anexo VII item 14 → Anexo I e XV) | `ncm` de fruta/hortícola do capítulo 7 ou 8 que também está no Anexo XV | `POST /v1/tax/simulate` | Zero, citando o Anexo (I ou XV) que efetivamente contém o código — nunca 60% |
| AT-004 | Exceção operante (Anexo VII, item 1) | `ncm` correspondente a `0306.11` (dentro do prefixo `0306.1`, mas expressamente excluído) | `POST /v1/tax/simulate` | Nunca recebe 60% por este item |
| AT-005 | Exceção operante (Anexo VII, item 14) | `ncm` correspondente a `07.11` (dentro do capítulo 7, mas expressamente excluído) | `POST /v1/tax/simulate` | Nunca recebe 60% por este item |
| AT-006 | Sub-item decimal com cabeçalho (Anexo V) | `ncm = "8708.99.10"` (comando de embreagem manual, item 1.1, sob o cabeçalho "item 1") | `POST /v1/tax/simulate` | 60%, citando "Anexo V, item 1.1", com `descricao_contexto` do item-pai (item 1) presente |
| AT-007 | Prefixo de capítulo múltiplo (Anexo IX, item 19) | `ncm` de 8 dígitos iniciado por `10`, `11` ou `12` (capítulos citados pelo item 19) | `POST /v1/tax/simulate` | 60%, citando "Anexo IX, item 19" — prova que o mecanismo aceita múltiplos prefixos de 2 dígitos no mesmo item |
| AT-008 | Item NBS do Anexo IX não resolvido | Requisição relativa a um dos serviços dos itens 22-33 (ex.: "Serviços veterinários para produção animal") — fora do payload atual (`ncm`), ou um `ncm` fantasiado que um cliente tentasse mapear a esse item | `POST /v1/tax/simulate` | Nunca recebe 60% "por acidente"; documentação/resposta deixa explícito que os itens NBS do Anexo IX não são resolvidos nesta feature |
| AT-009 | Item sem nenhuma chave (Anexo IX, item 34) | — | — | Documentado como limitação — nenhum teste automatizado pode "resolver" o item 34, porque não há código para casar |
| AT-010 | Comprador condicionado (Anexo IV/V/VI) | `ncm` de um item do Anexo IV, sem nenhuma informação de comprador no payload atual | `POST /v1/tax/simulate` | Aplica 60% (não zero) — mas a resposta/documentação declara explicitamente que, se o comprador for órgão público ou entidade CEBAS, a alíquota real seria zero, e que o payload atual não permite verificar essa condição |
| AT-011 | Regressão — Anexo VII item 2 não foi alterado pelo veto | `ncm` correspondente a um dos 3 códigos do item 2 (`0403.20.00`, `0403.90.00`, `2202.99.00`) | `POST /v1/tax/simulate` | 60%, citando "Anexo VII, item 2" com o texto ORIGINAL (não a redação vetada) |
| AT-012 | Regressão — Anexos zero e IPI intactos | `ncm` de um item já shipado do Anexo I, XII, XIII, XV ou da TIPI | `POST /v1/tax/simulate` | Comportamento idêntico ao já shipado, sem nenhuma interferência dos 6 Anexos novos |
| AT-013 | Item fora de todos os 10 Anexos conhecidos | `ncm` que não corresponde a nenhum item de I, IV, V, VI, VII, VIII, IX, XII, XIII ou XV | `POST /v1/tax/simulate` | 200; alíquota geral da fase, sem nenhuma referência a Anexo |

---

## Out of Scope

- Anexos II, III, X, XI (redução de 60% por NBS, posição 14) — mecanismo de chave diferente,
  decisão de agrupamento já tomada
- Anexo XVI (piso de alíquota própria, posição 15), Anexo XVII (Imposto Seletivo, posição 16),
  Anexos XVIII-XXIII (Simples Nacional, posição 17) — features futuras próprias
- Anexo XIV — já revogado pela LC 227/2026 (achado da feature anterior, `ANEXOS_REDUCAO_ZERO_
  XII_XIII_XV`)
- Itens de chave NBS do próprio Anexo IX (12 itens, 22-33) — documentados como não resolvidos,
  não implementados
- O item 34 do Anexo IX (sem nenhuma chave citável) — documentado como limitação, não resolvido
- **A implementação de fato do campo de comprador (`comprador_tipo` ou equivalente) no payload —
  decisão do `/design` se entra nesta feature ou fica documentada como limitação conhecida; o que
  NÃO é opcional é que a lacuna seja tratada explicitamente, não silenciada**
- Art. 137 (redução de 60% a produtos "in natura", sem Anexo) — mecanismo de correspondência por
  categoria de produto, não por lista de NCM; estruturalmente diferente dos 6 Anexos desta
  feature, candidato a feature própria futura
- O "diferimento" do art. 138 §2 (Anexo IX) — não é uma redução de alíquota, fica só documentado
- Verificação programática automatizada de overlap entre os 6 Anexos novos, os 4 já shipados e
  entre si — feita manualmente onde a remissão é textual explícita (Anexo VII); recomendada como
  `SHOULD` ao `/design`, não bloqueante
- Sincronização de eventuais alterações futuras aos 6 Anexos (nova lei complementar)
- Fuzzy match ou heurística além do que o texto de cada Anexo define literalmente

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura | A nova função de redução percentual é pura, sem I/O — a novidade de dado vive em `db/`/`api/` |
| Technical | `_COMPRIMENTOS_PREFIXO = (2,4,5,6,7,8)` (já alargado pela feature anterior) precisa suportar MÚLTIPLOS prefixos de 2 dígitos por item (Anexo IX, itens 10/19) — nunca testado antes | O `/design` decide como representar N prefixos curtos por item na tabela (mesmo mecanismo 1:N já existe; só o volume de linhas por item cresce) |
| Technical | O payload de `/v1/tax/simulate` não tem campo de tipo de comprador | Bloqueia a implementação COMPLETA da regra de zero-rate condicionado (IV/V/VI); o `/design` decide se resolve com um campo novo ou documenta como limitação explícita — nenhuma das duas opções pode ficar implícita |
| Business | Escopo estritamente limitado aos Anexos IV, V, VI, VII, VIII e IX — nenhum outro Anexo, nenhuma alteração aos dados já shipados dos 4 Anexos zero | Zero regressão nos 4 Anexos zero, no IPI e no regime vigente (AT-012) |
| Legal | Nenhum NCM/prefixo tratado como definitivo sem verificação contra fonte primária | Concluído nesta sessão para os 271 itens |
| Legal | A LC 227/2026 alterou o Anexo VII (item 2, vetado) e o art. 146 (categoria de medicamentos + revogação do Anexo XIV) — nenhuma outra alteração aos 6 Anexos ou aos artigos 131-138/144-146 | O `/build` deve usar o texto ORIGINAL do item 2 do Anexo VII (a alteração nunca entrou em vigor) |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Migração nova em `db/migrations/` (próxima numeração livre: `009_*.sql` em diante — 008 já foi usada pela feature anterior) + extensão de `api/reducao_zero.py` (ou um módulo irmão `api/reducao_percentual.py` — decisão do `/design`) + consumo em `api/routers/simulate.py` | Mesma estrutura já validada 3 vezes (Anexo I, XII/XIII/XV) |
| **KB Domains** | `data-modeling` (schema-migration — nova tabela ou extensão da existente, com um percentual que não é sempre 0 nem sempre 1; e a condição de comprador para IV/V/VI, se implementada, é uma decisão de modelagem nova), `data-quality` (data-contract-authoring — 271 itens, a maior transcrição do projeto até aqui, com 3 classes de "exceto" já mapeadas), `python` (clean-architecture), `testing` (padrão `Protocol` real/fake já usado 4 vezes) | Ênfase maior em `data-quality` que nas features anteriores, pelo volume e pela condição de comprador |
| **IaC Impact** | Nova migração Postgres a aplicar via `migrar_banco.yml` (mesmo fluxo já usado 4 vezes); `GRANT SELECT` para `taxreformai_app` | Nenhuma mudança de Terraform |

**Why This Matters:**

- **Location** → Reaproveita a estrutura já validada; nenhuma decisão arquitetural nova de onde as coisas vivem
- **KB Domains** → `data-quality` precisa de peso maior aqui: volume 4,5× maior que a feature anterior, e uma condição de negócio (comprador) que nenhuma feature anterior teve
- **IaC Impact** → Mesmo fluxo de migração de sempre

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexo IV (`legis.senado.leg.br`, mirror do DOU) | Texto legal | 105 itens, todos EXATO | Estático — LC 227/2026 não o alterou (confirmado nesta sessão) | Legislativo Federal |
| LCP 214/2025, Anexo V (idem) | Texto legal | 26 itens (3 cabeçalho + 23 sub-item) | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo VI (idem) | Texto legal | 81 itens, todos EXATO, sem exceção | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo VII (idem) | Texto legal | 17 itens (5 com remissão ao Anexo I) | Estático — item 2 sofreu tentativa de alteração VETADA (sem efeito) | Legislativo Federal |
| LCP 214/2025, Anexo VIII (idem) | Texto legal | 7 itens, todos EXATO, sem exceção | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo IX (idem) | Texto legal | 35 itens (22 NCM + 12 NBS + 1 sem código) | Estático — idem | Legislativo Federal |
| LCP 214/2025, arts. 144-II/145-II/146 §2 (idem) | Texto legal (condição de comprador) | 3 incisos/parágrafos | Estático — substancialmente inalterado pela LC 227/2026 | Legislativo Federal |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Identificação do Anexo | Distinguir IV/V/VI/VII/VIII/IX — mesmo padrão `(anexo, item, sub_item)` já generalizado pela feature anterior | Sim |
| Percentual de redução | Coluna que representa "60%" — decisão do `/design` se é um valor fixo (`DECIMAL`) ou uma constante de código, dado que os 6 Anexos desta feature são uniformemente 60% (diferente dos Anexos zero, que eram sempre 100%) | Sim |
| Prefixo de dígitos, comprimento 2-8, **N por item** | O Anexo IX exige até 2+ prefixos curtos (2 dígitos) no MESMO item — o schema 1:N já suporta isso estruturalmente, mas nunca foi exercitado com múltiplos prefixos do mesmo comprimento curto num único item | Sim |
| Exceção (booleano `excecao`, escopada ao item) | Cobre a exceção operante do Anexo VII (itens 1 e 14) | Sim |
| Remissão a Anexo(s) zero | Os 5 itens do Anexo VII (4, 5, 6, 14, 15) precisam de uma forma de declarar "cede a I" (e, no item 14, também "a XV") — decisão do `/design`: coluna dedicada vs. lógica de precedência centralizada no lookup | Sim |
| Condição de comprador (Anexos IV/V/VI) | Decisão do `/design`: coluna(s) que representem "zero se comprador ∈ {público, CEBAS}" — ou documentação explícita da limitação, se o payload não for estendido nesta feature | Sim, uma das duas |
| `dispositivo_legal_ref` | Formato análogo ao já usado: "LCP 214/2025, Anexo {Anexo}, item {N}" — os artigos que regem cada Anexo (131-138) e os que condicionam o comprador (144-II/145-II/146§2) precisam ser citados corretamente | Sim |
| Descrição do produto | Texto literal do item, para auditoria | Sim |

### Freshness SLAs

Não aplicável — dado estático, sem pipeline de atualização recorrente.

### Completeness Metrics

- 271/271 itens dos Anexos IV, V, VI, VII, VIII e IX verificados contra fonte primária nesta
  sessão (100%)
- 22/35 itens do Anexo IX (63%) são NCM (em escopo); 12/35 (34%) são NBS (fora de escopo,
  documentados); 1/35 (3%) não tem nenhuma chave citável (documentado como limitação distinta)
- 5/17 itens do Anexo VII (29%) têm remissão normativa explícita a Anexo(s) zero — nenhum tratado
  como resolvido sem a checagem de precedência
- 3/6 Anexos (IV, V, VI — 50% do grupo, 212/271 itens = 78% do volume) têm condição de zero-rate
  amarrada ao comprador — não "60% incondicional" como o roadmap havia classificado inicialmente

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto dos 6 Anexos obtido via `legis.senado.leg.br` é o texto vigente, sem alterações posteriores além do veto ao item 2 do Anexo VII | Os itens/códigos usados no `/design`/`/build` estariam errados | [x] Validado nesta sessão — lista de "Normas posteriores" da LCP 214/2025 e conteúdo integral da LC 227/2026 e da Mensagem de Veto nº 36/2026 lidos diretamente |
| A-002 | O §2 do art. 146 (zero-rate do Anexo VI condicionado ao comprador) é substancialmente idêntico antes e depois da LC 227/2026 | Se houvesse diferença material, a condição de comprador para o Anexo VI poderia estar incorreta | [x] Validado nesta sessão — texto do art. 146 lido tanto na "Publicação Original" da LCP 214/2025 quanto na "(NR)" da LC 227/2026; a cláusula do §2 é a mesma nos dois |
| A-003 | Não há overlap de NCM entre os 6 Anexos desta feature e os 4 Anexos zero, ALÉM da remissão textual explícita já encontrada no Anexo VII | Se houvesse overlap não declarado, a citação da fonte poderia apontar para o Anexo errado, ou pior, aplicar 60% a algo que já é zero | [ ] NÃO verificado exaustivamente nesta sessão — o volume (271 itens novos + 60 já shipados) tornou inviável a checagem manual completa feita na feature anterior (que cobria só 56+95 linhas); fica como `SHOULD` explícito ao `/design`, com risco maior que o registrado na feature anterior |
| A-004 | A abordagem técnica é generalizar ainda mais o schema já existente (`anexos_reducao_zero`/`anexos_reducao_zero_ncm`, ou uma tabela irmã de mesma forma com uma coluna de percentual), análoga à Decisão 1 do `/design` da feature anterior | Se o `/design` concluir que misturar "zero" e "percentual" na mesma tabela é arriscado (ex.: por causa da condição de comprador, que não existe nos Anexos zero), pode preferir uma tabela nova e paralela | [ ] A confirmar no `/design` — nenhuma das duas opções foi decidida aqui, mas ambas resolvem sem alterar `motor_calculo/` |
| A-005 | O `/design` decide como tratar a lacuna de "tipo de comprador" no payload — nem "sempre 60%" nem "sempre zero" são aceitáveis como default silencioso | Se o `/design` (ou `/build`) assumir um dos dois extremos sem declarar, a simulação erra sistematicamente para uma classe real de clientes (compras de órgãos públicos/CEBAS) | [ ] Não resolvido nesta sessão — decisão explícita fica para o `/design`, ver "Achado crítico" |

**Note:** Validar A-003 e A-005 explicitamente no `/design` antes do `/build` — ambas têm potencial
de gerar erro de cálculo real (não cosmético) se ignoradas.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, quantificada (271 itens, 6 Anexos, 3 com condição de comprador), causa raiz nova (mecanismo de cálculo percentual, não zero) |
| Users | 3 | Mesmos dois usuários já validados nas duas features anteriores, com pain point específico (superestimação Y subestimação de risco oposto) a este escopo |
| Goals | 3 | MoSCoW explícito; o achado crítico do comprador é MUST, não escondido nem deferido silenciosamente |
| Success | 3 | Critérios testáveis e numéricos (271/271 itens, 22/35 NCM do Anexo IX, 5/17 itens com remissão) |
| Scope | 2 | Out of scope explícito, mas duas decisões de fronteira ficam deliberadamente abertas para o `/design` (campo de comprador no payload; forma exata do schema) — correto por não presumir a resposta, mas reduz a nota porque a fronteira exata da implementação (o que entra nesta feature vs. fica só documentado) não está 100% fechada |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** o brainstorm estimou este grupo como
"reaproveita 100% do vocabulário NCM, só a função de cálculo é nova". A verificação desta sessão
confirma a premissa central (nenhuma mudança de mecanismo de correspondência é necessária além do
já generalizado pela feature anterior), mas encontra 2 fatores de esforço que o brainstorm não
previu: (1) o volume é 4,5× maior (271 vs. 56 itens) com um item isolado (Anexo IX, item 7) citando
sozinho mais códigos que Anexos inteiros já shipados; (2) 3 dos 6 Anexos (78% do volume) carregam
uma condição de comprador que exige uma decisão de payload, não só de dado. Isso não muda a
resposta de "qual é o problema" (nota de clareza), mas muda substancialmente "quanto trabalho" —
mesmo padrão de correção já visto nas duas features anteriores.

---

## Open Questions

Nenhum item abaixo bloqueia o avanço para `/design` — são decisões de implementação, não lacunas
de entendimento:

1. **Como tratar a condição de comprador (Anexos IV/V/VI)**: campo novo no payload (`comprador_
   tipo` ou equivalente) vs. limitação documentada explicitamente sem mudança de payload — decisão
   do `/design`, com a restrição de que nenhuma das duas pode ficar implícita (ver "Achado
   crítico").
2. **Forma exata do schema**: estender ainda mais `anexos_reducao_zero`/`_ncm` (com uma coluna de
   percentual e, possivelmente, de condição de comprador) vs. uma tabela irmã nova
   (`anexos_reducao_percentual`/`_ncm`) — decisão do `/design`, análoga à Decisão 1 da feature
   anterior, mas agora com a complicação de que "zero" e "percentual condicionado a zero" convivem
   nos mesmos 3 Anexos (IV/V/VI).
3. **Assinatura de `aplicar_reducao_percentual`**: função nova e dedicada vs. generalização de
   `aplicar_reducao_a_zero` com um parâmetro `percentual` (em que 1.0 é o caso hoje já shipado) —
   decisão do `/design`, ambas preservam a regra "IS nunca é tocado".
4. **Verificação automatizada de overlap** entre os 6 Anexos novos, entre si e com os 4 já
   shipados — recomendada como `SHOULD`, não bloqueante, mas com risco maior que na feature
   anterior dado o volume.
5. **Como representar múltiplos prefixos curtos por item** (Anexo IX, itens 10 e 19 — "Capítulos
   X, Y e Z") — o mecanismo 1:N já existe; a única decisão é se há algum limite prático de linhas
   por item a impor no `/design` (nenhum indício disso nos dados verificados, mas vale registrar).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Versão inicial, extraída de `BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NCM.md`; verificação de fonte primária realizada nesta sessão (6 Anexos via `legis.senado.leg.br`, mais o corpo da LCP 214/2025 arts. 129-148 e o texto da LC 227/2026/Mensagem de Veto nº 36/2026); contagens corrigidas (271 itens reais vs. ~322 estimados, com desvios grandes em ambas as direções por Anexo); achado crítico confirmado e ampliado — Anexos IV, V e VI têm condição de zero-rate amarrada ao comprador (arts. 144-II, 145-II, 146 §2), não "60% incondicional"; confirmado que a LC 227/2026 só tocou o Anexo VII (item 2, integralmente vetado) entre os 6; estrutura mista do Anexo IX detalhada item a item (22 NCM + 12 NBS + 1 sem nenhuma chave) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NCM.md`
