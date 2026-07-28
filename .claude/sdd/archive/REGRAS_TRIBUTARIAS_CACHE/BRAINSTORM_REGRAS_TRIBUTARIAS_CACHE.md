# BRAINSTORM: Regras Tributárias Cache — Cesta Básica Nacional (Anexo I)

> Exploratory session to clarify intent and approach before requirements capture
>
> **Esta é a feature 2 de uma sequência de 11 features já roteirizada** a partir de uma
> auditoria profunda de 12 achados (achado 13 descartado, achado 12 registrado à parte como
> item de monitoramento). Ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`
> para a ordem completa e o racional de sequenciamento. Esta sessão cobre só o escopo do
> item 2 (achado original nº 2 do levantamento).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REGRAS_TRIBUTARIAS_CACHE |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 2 de 11 (ver ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md) |

---

## Initial Idea

**Raw Input:** Auditoria profunda encontrou que a tabela `regras_tributarias_cache`
(migração `001_schema_inicial.sql`) e a função `db/repositorio.py::buscar_regra_cache()`
existem desde o SHIPPED de `SCHEMA_POSTGRESQL`, mas não têm nenhum chamador em `api/` ou
`scripts/` — nunca são escritas nem lidas por nenhum código real. Puro código morto,
candidato a "remover" ou "conectar a um uso real", no mesmo espírito da decisão já tomada
para `RegimeIndisponivelError` na feature 1.

**Context Gathered (nesta sessão):**

- `regras_tributarias_cache` é chaveada por `(ncm_code, ano_vigencia, regime_especial)`,
  sem RLS (dado legal público, igual para todo tenant — mesmo padrão de
  `aliquotas_ipi_tipi`).
- Hoje `/v1/tax/simulate` tira CBS/IBS/IS de `TabelaAliquotasSeed`
  (`motor_calculo/tabela_aliquotas.py`), que é indexada **só por fase da transição**
  (2026, 2027-2028...), igual para qualquer NCM — o motor de cálculo da reforma não tem
  hoje nenhum conceito de "alíquota diferente por produto".
- Diferente da TIPI (feature 1), a tabela está **zerada**: nenhuma linha real foi
  ingerida, nenhum script de carga existe. `regime_especial` no blueprint original
  (`contexto.md`, linha 341) é só um `VARCHAR(64) DEFAULT 'GERAL'`, sem nenhuma
  elaboração de quais valores existiriam.
- O payload de `/v1/tax/simulate` (`PayloadSimulacao`/`ItemSimulacao`) não tem nenhum
  campo `regime_especial` hoje.
- **Investigação de conteúdo real da LCP 214/2025** (`planalto.gov.br` inacessível deste
  ambiente; usadas duas fontes secundárias independentes — `modeloinicial.com.br` e
  `simtax.com.br` — cujo conteúdo do Anexo I bate item a item, incluindo os mesmos NCMs
  para os mesmos itens numerados):
  - **Art. 125** cria a Cesta Básica Nacional: alíquota **zero** de IBS e CBS para uma
    lista fechada de alimentos, listada no **Anexo I** (26 itens, dezenas de códigos
    NCM/SH — arroz, leite, feijão, carnes, queijos, farinhas, etc.).
  - O Anexo I é só 1 de **17 Anexos** (I a XVII) que tratam de regimes diferenciados,
    mais um segundo conjunto (XVIII a XXIII) que são versões de "produção de efeitos"
    futura de 5 deles (I-V, VII) — a lista de produtos beneficiados tem dimensão
    temporal própria, análoga ao conceito de "fase" que `TabelaAliquotasSeed` já tem,
    só que por produto, não por ano.
  - Os 17 Anexos **não são todos por NCM**: Anexo II (educação), III (saúde), X
    (produções culturais), XI (segurança/cibersegurança), entre outros, são
    **serviços** — a chave seria `nbs_code`, não `ncm_code`. `regras_tributarias_cache`
    só tem `ncm_code`.
  - As reduções não são um percentual único: **zero** (I, XII, XIII, XIV), **60%**
    (II-XI, exceto I), **100%** (XV — hortícolas/frutas/ovos, redação equivalente a
    zero mas expressa como percentual de redução). Anexo XVI não é sobre produto (piso
    de alíquota própria dos entes federativos). Anexo XVII é a lista de bens/serviços
    do **Imposto Seletivo** — tributo diferente de CBS/IBS.
  - Uma das fontes secundárias marca o **Anexo XIV como REVOGADO** — **não confirmado
    contra o texto oficial do Planalto**, só observado numa fonte secundária. Fica
    registrado como item a verificar no `/define`/`/design`, quando houver acesso à
    fonte primária (ou à própria coleção já ingerida no Qdrant de produção).
  - Pelo menos alguns itens do Anexo I **não são NCM exato**: itens 19 e 20 (carnes,
    peixes) usam posição/subposição inteira **com exceção explícita** ("02.01, 02.02,
    [...] exceto os produtos das subposições X, Y"). Isso não é um
    `WHERE ncm_code = ANY(%s)` de igualdade simples como a TIPI (feature 1) — exige
    correspondência por prefixo/faixa mais exclusão.
- **Conclusão de escopo:** a tabela como existe hoje (`ncm_code` + `ano_vigencia` +
  `regime_especial` livre, uma linha por NCM) não tem forma para os ~16 outros Anexos
  (serviço, percentuais variáveis, IS), nem para exceção por prefixo. **Não é um caso de
  "plugar dado existente"** como a TIPI — o schema precisaria ser redesenhado do zero
  para caber mesmo só o Anexo I.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Schema atual | `regras_tributarias_cache` guarda `aliquota_cbs`/`aliquota_ibs`/`aliquota_is` como números por linha, pensada para "a alíquota final já resolvida" — não para "um percentual de redução aplicado sobre a alíquota de referência da fase" | O Anexo I é o caso mais simples porque a redução é *sempre* 100% (zero) — não precisa resolver a interação "alíquota de referência × percentual de redução" que os Anexos de 60% exigiriam |
| Match por NCM | Maioria dos 26 itens do Anexo I é igualdade exata de NCM/SH (8 dígitos ou faixa curta); dois itens (19, 20) têm exceção por subposição | `/design` precisa decidir se cobre os dois itens com exceção nesta feature ou os trata como "não resolvido, resolução manual" nesta primeira iteração — decisão explícita, não implícita |
| Tabela renomeada/redesenhada | Manter o nome `regras_tributarias_cache` genérico, ou nomear algo específico do Anexo I (ex. `cesta_basica_nacional_ncm`)? A coluna `regime_especial` livre (`VARCHAR(64)`) não tem valor conhecido a preencher ainda — nenhum dos 17 Anexos tem um enum estabelecido no código hoje | `/design` decide entre um schema novo e dedicado ao Anexo I vs. adaptar o existente; ambos são "redesenho", não "reuso" |
| Payload da API | `ItemSimulacao` não tem campo para sinalizar "este item está na cesta básica" — hoje o único dado disponível para lookup é `ncm` | Mesma forma de lookup que a TIPI (por NCM, no meio do laço de `/v1/tax/simulate`), mas aplicado só a CBS/IBS da reforma, não ao regime vigente |
| Relevant KB Domains | python-developer, database-reviewer | Mesmo padrão `Protocol` real/fake já usado em `TabelaAliquotas`/`TabelaPisCofins`, provavelmente reaproveitável para uma "tabela de exceção por NCM" da reforma |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O caso de uso real por trás de `regime_especial` já era conhecido (reduções por NCM da LCP 214/2025), ou a intenção era descobrir junto/remover como código morto? | (a) Sim — o caso de uso real em mente eram as reduções/isenções por NCM previstas na própria LCP 214/2025 (cesta básica, Anexos), separado da lógica "por fase" que `TabelaAliquotasSeed` já cobre | Direção de investigação: checar o texto real da lei antes de desenhar qualquer coisa, em vez de assumir "remover" ou inventar um enum de regimes |
| 2 | Diante do achado de que a base legal real tem 17 Anexos (não NCM puro, percentuais variados, dimensão temporal, exceções por prefixo) — muito maior que um `regime_especial: GERAL` — qual direção: (a) escopar só o Anexo I; (b) investigar mais antes de decidir; (c) remover a tabela agora e abrir uma feature dedicada mais adiante; (d) outra | (a) Escopar SÓ o Anexo I (Cesta Básica Nacional, art. 125, alíquota zero) nesta feature | Define o corte exato desta feature: 1 de 17 Anexos, o subconjunto mais simples (NCM predominantemente exato, alíquota zero é o caso de cálculo mais fácil); os outros 16 ficam para features futuras |
| 3 | Confirmar: schema atual (`ncm_code` + `regime_especial` livre) precisa ser redesenhado do zero, não só populado? | Confirmado pelo usuário — registrar explicitamente para não subestimar o esforço do `/design` | `/design` não deve tratar isso como "escrever um script de carga" (como a TIPI); é desenho de schema novo + decisão sobre exceção por prefixo |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexo I) | Fontes secundárias (`modeloinicial.com.br`, `simtax.com.br`), cruzadas entre si | 26 itens numerados, dezenas de códigos NCM/SH | **Não verificado contra o texto oficial do Planalto** (`planalto.gov.br` inacessível deste ambiente durante o brainstorm) nem contra a coleção já ingerida no Qdrant de produção (`legislacao_tributaria`, que já tem a LCP 214/2025 completa, 3417 chunks) — verificação contra fonte primária é item obrigatório do `/define`/`/design`, não uma suposição aceita aqui |
| Fonte legal | Art. 125 + Anexo I, LCP 214/2025 | 1 artigo + 1 anexo | Citação por item é possível (cada um dos 26 itens do Anexo I é numerado, citável individualmente) |
| Estrutura de exceção | Itens 19 e 20 do Anexo I | 2 de 26 | Únicos itens observados com exceção por subposição em vez de NCM exato; candidatos a ficar "fora de escopo" mesmo dentro do Anexo I, se o `/design` decidir não resolver correspondência por prefixo+exclusão nesta primeira iteração |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design` — provavelmente um subconjunto pequeno e real dos 26 itens (incluindo pelo menos 1 dos itens com exceção, para decidir explicitamente o comportamento) |

**Como os dados serão usados (se aprovado no /define):** o payload de `/v1/tax/simulate`
já traz `ncm` por item de mercadoria; um lookup buscaria se o NCM está na lista do Anexo I
e, se estiver, aplicaria alíquota zero de CBS/IBS àquele item (em vez da alíquota geral da
fase), citando "LCP 214/2025, art. 125, Anexo I, item N" como fonte legal — mesmo padrão de
transparência já usado para IPI/ICMS/ISS/PIS-COFINS.

---

## Approaches Explored

### Approach A: Escopar só o Anexo I nesta feature, schema redesenhado do zero ⭐ Recomendada (escolhida)

**What:** Uma tabela nova (nome a definir no `/design` — provavelmente não reaproveitando
`regras_tributarias_cache` como está, dado que seu schema atual não cabe nem no Anexo I sem
mudança) que guarda os itens do Anexo I por NCM/SH, com `dispositivo_legal_ref` citando o
item exato do Anexo I. `/v1/tax/simulate` consulta essa tabela para itens de mercadoria e,
quando o NCM bate, aplica alíquota zero de CBS/IBS àquele item específico, citando a fonte.
Os outros 16 Anexos, o Imposto Seletivo (Anexo XVII) e a dimensão de "produção de efeitos
futura" (Anexos XVIII-XXIII) ficam **explicitamente fora**, para features futuras da
sequência (fora até das 11 já roteiradas — seria uma feature nova, a inserir no roadmap).

**Pros:**
- Escopo pequeno e citável (26 itens, 1 artigo, 1 anexo) — mesma disciplina de "uma fonte
  de cada vez" já usada em Planalto → TCU → CGIBS → RFB → TIPI
- Alíquota zero é o caso de cálculo mais simples (não exige resolver "percentual de
  redução sobre alíquota de referência", que os Anexos de 60% exigiriam)
- Aproveita o padrão já validado de citação de fonte por item (`fonte_legal`,
  `dispositivo_legal_ref`) em vez de inventar um novo
- Não força a tabela existente a caber uma forma que ela não tem — honesto sobre o
  esforço real de redesenho

**Cons:**
- Deixa `regras_tributarias_cache`/`buscar_regra_cache()` original ainda como código morto
  até essa decisão de nome/schema ser tomada no `/design` (pode ser substituída, não
  necessariamente removida nesta feature se o `/design` decidir generalizar a forma)
- Os itens 19/20 (exceção por subposição) exigem uma decisão explícita: resolver
  correspondência por prefixo+exclusão nesta feature, ou marcar esses 2 itens como
  "não resolvido nesta iteração" (mesmo padrão de "NCM não encontrado ⇒ nunca 0% silencioso"
  já usado no IPI)
- Conteúdo do Anexo I usado neste brainstorm vem de fonte secundária, não da fonte
  primária nem da coleção Qdrant já ingerida — precisa ser conferido antes do `/build`

**Why Recommended:** É a única abordagem que respeita tanto o tamanho real do achado
(17 Anexos, não 1 tabela simples) quanto a disciplina do projeto de atacar um subconjunto
citável de cada vez — mesmo padrão que já funcionou para a TIPI (decreto único) e para as
4 fontes de ingestão legal (uma por vez).

---

### Approach B: Generalizar `regime_especial` para cobrir os 17 Anexos de uma vez

**What:** Desenhar desde já um schema (ou enum) que representasse os 17 Anexos completos —
zero, 60%, 100%, serviço vs. mercadoria, Imposto Seletivo — antes de popular qualquer dado.

**Pros:**
- Evitaria um segundo redesenho de schema quando a próxima feature quisesse cobrir outro
  Anexo

**Cons:**
- Schema genérico para 17 Anexos heterogêneos (alguns por NCM, alguns por NBS, percentuais
  variáveis, um deles nem é produto) tende a general-purpose demais para o primeiro caso
  real — risco real de super-engenharia sem nenhum dado ainda ingerido para validar a forma
- Contradiz a disciplina "uma fonte/decisão de cada vez" que susteve a sequência de 11
  features sem reabertura até aqui (ver Lição de Processo do SHIPPED da feature 1)
- Sem verificação contra o texto oficial (Planalto inacessível neste brainstorm), desenhar
  um schema definitivo para todos os 17 Anexos de uma vez seria comprometer-se com uma
  forma antes de examinar o texto real de cada um

---

### Approach C: Remover `regras_tributarias_cache` agora, tratar Anexo I como feature nova e separada mais adiante

**What:** Remover a tabela/função como código morto nesta feature (fechando o achado 2 da
auditoria como "removido"), e abrir uma feature nova e dedicada ao Anexo I mais adiante na
sequência de 11 (nome próprio, ex. `CESTA_BASICA_ANEXO_I_MOTOR_CALCULO`).

**Pros:**
- Fecha o achado original (código morto) de forma mais rápida e simples

**Cons:**
- Rejeitado pelo usuário: a Approach A já entrega o caso de uso real descoberto nesta
  mesma sessão, sem precisar de uma segunda rodada de brainstorm/define/design só para
  reabrir o mesmo achado
- Descartaria o trabalho de investigação já feito nesta sessão (Anexo I, art. 125, os 26
  itens) sem necessidade

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — escopar só o Anexo I (Cesta Básica Nacional, art. 125), schema redesenhado do zero, sem reaproveitar `regras_tributarias_cache` como está |
| **User Confirmation** | ✅ Confirmado explicitamente pelo usuário nesta sessão |
| **Reasoning** | Único approach que reconhece o tamanho real do achado (17 Anexos, não um flag simples) e ainda assim entrega algo citável e verificável nesta feature, seguindo a mesma disciplina incremental já usada nas 8 features anteriores do projeto |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo desta feature é **só o Anexo I** (Cesta Básica Nacional, art. 125, alíquota zero, 26 itens) | É o subconjunto mais simples de calcular (zero, não um percentual de redução sobre a alíquota de referência) e o mais fácil de verificar (predominantemente NCM exato) | Cobrir os 17 Anexos de uma vez (Approach B) — rejeitado por super-engenharia sem dado ainda validado |
| 2 | Os outros 16 Anexos (II-XVII, incluindo Imposto Seletivo no XVII e a dimensão "produção de efeitos futura" dos Anexos XVIII-XXIII) ficam **explicitamente fora de escopo** desta feature | Cada um tem uma forma de dado diferente (serviço/NBS, percentual de 60%, tributo diferente) que merece sua própria sessão de brainstorm, não uma decisão apressada aqui | Incluir "pelo menos os Anexos de zero" (I, XII, XIII, XIV) de uma vez — rejeitado; XII/XIII/XIV ainda não foram investigados com o mesmo rigor que o Anexo I nesta sessão |
| 3 | O achado do Anexo XIV possivelmente **REVOGADO** fica registrado como pendência de verificação contra o texto oficial do Planalto | Observado só numa fonte secundária durante este brainstorm (Planalto inacessível neste ambiente); nenhuma afirmação sobre Anexo XIV deve ser tratada como fato até conferência contra fonte primária — mesmo princípio de "nunca citar de memória" já praticado no resto do projeto | Ignorar o achado — rejeitado, seria descartar um sinal real sem registro |
| 4 | O schema atual de `regras_tributarias_cache` (`ncm_code` + `ano_vigencia` + `regime_especial` livre, uma linha por NCM) **precisa ser redesenhado do zero** para caber o Anexo I, não populado como está | O schema não tem coluna para `nbs_code` (Anexos de serviço, fora de escopo aqui, mas mostra que o desenho original não previu isso), não distingue "alíquota zero por regime especial" de "alíquota resolvida por fase", e não tem forma para exceção por prefixo/subposição (itens 19/20) | Tratar como "plugar dado existente", no mesmo molde da TIPI (feature 1) — rejeitado explicitamente; o esforço real do `/design` é maior que um script de carga |
| 5 | Itens 19 e 20 do Anexo I (exceção por subposição, não NCM exato) são uma decisão técnica explícita a resolver no `/design`, não implícita | Correspondência por prefixo + exclusão é uma lógica de matching diferente da igualdade exata usada em toda a TIPI/regime vigente; decidir "resolver agora" vs. "marcar como não resolvido nesta iteração" muda o desenho do lookup | Assumir que todo item do Anexo I é NCM exato — rejeitado, seria uma afirmação falsa sobre 2 dos 26 itens |
| 6 | Conteúdo do Anexo I usado nesta sessão vem de **fontes secundárias** (`planalto.gov.br` inacessível neste ambiente), cruzadas entre si mas não contra a fonte primária nem contra a coleção Qdrant de produção | Mesmo princípio de rigor do resto do projeto: nenhuma alíquota/NCM deve ser tratada como definitiva sem conferência contra a fonte oficial | Aceitar as fontes secundárias como definitivas para o `/build` — rejeitado; é um item de verificação obrigatório do `/define`/`/design`, análogo à disciplina já usada com TIPI/CGIBS/RFB |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Cobrir os 17 Anexos nesta feature (Approach B) | Schema genérico demais sem dado real ainda validado; contradiz a disciplina "um subconjunto citável de cada vez" já estabelecida | Sim — cada Anexo (ou grupo coerente de Anexos, ex. os de 60% por serviço) é candidato a virar uma feature própria, a inserir no roadmap |
| Resolver Anexo XVII (Imposto Seletivo) junto, aproveitando que `motor_calculo` já calcula IS | Achado 2 da auditoria é especificamente sobre `regras_tributarias_cache`/CBS-IBS; IS por Anexo XVII é um tributo e uma lista diferentes, merece investigação própria (o `motor_calculo/tabela_aliquotas.py` já trata IS como "fixado por lei ordinária, variável por produto" — o Anexo XVII pode ser justamente essa lei, mas isso não foi verificado nesta sessão) | Sim, como feature futura dedicada |
| Resolver a dimensão "produção de efeitos futura" (Anexos XVIII-XXIII) | Fora do escopo desta sessão; precisaria entender exatamente quando cada versão futura passa a valer, o que não foi investigado aqui | Sim, quando/se o Anexo I específico for revisitado com essa dimensão temporal |
| Corresponder por prefixo+exclusão os itens 19/20 do Anexo I nesta mesma decisão de brainstorm | É uma decisão de design técnico (schema de matching), não de escopo de produto — melhor deixada para o `/design`, com a opção explícita de "não resolvido nesta iteração" sobre a mesa | Sim — decisão adiada para o `/design`, não descartada |
| Remover a tabela como código morto sem investigar (Approach C original da auditoria) | Rejeitada pelo usuário: a investigação desta sessão já validou um caso de uso real e citável (Anexo I) | Não aplicável — decisão já tomada |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Se o achado 2 já tinha um caso de uso real em mente vs. descobrir/remover | ✅ | (a) Sim — reduções por NCM da LCP 214/2025 | Direcionou a investigação para o texto real da lei |
| Achado de que a base legal real são 17 Anexos heterogêneos, muito além de `regime_especial: GERAL` — qual direção tomar | ✅ | (a) Escopar só o Anexo I | Fechou o corte exato da feature |
| Confirmação de que o schema precisa ser redesenhado do zero (não só populado) | ✅ | Confirmado, com pedido explícito de registrar isso para não subestimar o `/design` | Registrado na Key Decision 4 |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
`regras_tributarias_cache` existe desde `SCHEMA_POSTGRESQL` sem nenhum consumidor real, e
seu schema (`ncm_code` + `ano_vigencia` + `regime_especial` livre) não corresponde à forma
real de nenhum regime diferenciado da LCP 214/2025. A Cesta Básica Nacional (art. 125,
Anexo I) é o subconjunto mais simples e citável de um achado bem maior (17 Anexos de
regimes diferenciados) — 26 itens de alimentos com alíquota zero de CBS/IBS. Esta feature
desenha um schema novo (ou substitui o existente) para representar o Anexo I e conecta
`/v1/tax/simulate` a ele, aplicando alíquota zero de CBS/IBS aos itens de mercadoria cujo
NCM estiver na lista, com a fonte legal citada por item.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Simula CBS/IBS para alimentos da cesta básica com a alíquota geral da fase, quando a lei já garante alíquota zero para esses produtos especificamente — superestimando a carga tributária projetada |
| Controller/CFO usando o simulador | Não consegue demonstrar o benefício real da Cesta Básica Nacional (uma mudança relevante de política pública da reforma) numa simulação que se propõe auditável |

### Success Criteria (Draft — a refinar no /define)
- [ ] Conteúdo do Anexo I (26 itens, NCMs) verificado contra a fonte oficial (Planalto)
      ou contra a coleção Qdrant de produção já ingerida (`legislacao_tributaria`) —
      não aceito de fontes secundárias sem essa conferência
- [ ] Schema novo (nome e forma a definir no `/design`) representa os itens do Anexo I
      com `dispositivo_legal_ref` citando "LCP 214/2025, art. 125, Anexo I, item N"
- [ ] `/v1/tax/simulate` aplica alíquota zero de CBS/IBS a itens de mercadoria cujo NCM
      esteja na lista do Anexo I, em vez da alíquota geral da fase
- [ ] Decisão explícita e documentada sobre os itens 19/20 (exceção por subposição):
      resolvidos nesta feature ou marcados como "não resolvido" sem promessa de zero
      silencioso
- [ ] Achado do Anexo XIV possivelmente revogado, resolvido (confirmado ou descartado)
      contra fonte oficial antes do `/build`
- [ ] `motor_calculo/` não ganha dependência de infraestrutura — mesmo padrão da feature 1
      (lookup em `api/`/`db/repositorio.py`)
- [ ] `regras_tributarias_cache`/`buscar_regra_cache()` original: decisão explícita no
      `/design` sobre se são substituídas por schema novo, adaptadas, ou removidas

### Constraints Identified
- `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura — mesmo princípio já
  estabelecido na feature 1 (IPI/TIPI)
- Sem RLS na nova tabela (dado legal público, igual para todos os tenants), mesmo padrão
  de `aliquotas_ipi_tipi`/`regras_tributarias_cache`
- Nenhuma alíquota/NCM deve ser tratada como definitiva sem verificação contra fonte
  primária (Planalto) ou a coleção Qdrant já ingerida — disciplina "nunca de memória" já
  praticada no resto do projeto
- Escopo estritamente limitado ao Anexo I — nenhum dos outros 16 Anexos, nem o Imposto
  Seletivo (Anexo XVII), entram nesta feature

### Out of Scope (Confirmed)
- Anexos II a XVII (educação, saúde, dispositivos médicos, acessibilidade, nutrição
  enteral/parenteral, alimentos com redução de 60%, higiene, insumos agropecuários,
  produções culturais, segurança nacional/cibersegurança, dispositivos médicos e
  medicamentos com redução a zero, hortícolas/frutas/ovos, piso de alíquota própria,
  Imposto Seletivo) — candidatos a features futuras próprias, fora da sequência de 11 já
  roteirizada
- Anexos XVIII a XXIII (dimensão "produção de efeitos futura")
- API de `empresa_skus` (achado 3, próxima posição da sequência)
- Qualquer trabalho de LLM/orquestração (achados 4, 5, 6)
- Cloud Composer, verificação de frontend, diagnóstico de busca híbrida, BigQuery, fila
  assíncrona (achados 7-11)
- Linha do tempo 2029-2033 (achado 12) — item de monitoramento, não uma feature

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 3 de 2 |
| Duration | 1 sessão de diálogo, incluindo leitura de código real (`db/repositorio.py`, migração 001, `motor_calculo/tabela_aliquotas.py`/`regras_fiscais.py`, `api/routers/simulate.py`) e investigação do texto da LCP 214/2025 via fontes secundárias (Planalto inacessível deste ambiente) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_REGRAS_TRIBUTARIAS_CACHE.md`

**Antes do /define avançar**, vale reconfirmar com o usuário se a verificação do conteúdo
do Anexo I contra fonte oficial (Planalto ou Qdrant de produção) acontece como parte do
`/define`/`/design`, ou se é um passo manual prévio — esta sessão de brainstorm não teve
acesso à fonte primária.

**Depois desta feature ser shipada**, a próxima da sequência é a posição 3:
`API_EMPRESA_SKUS` (ver `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`).
