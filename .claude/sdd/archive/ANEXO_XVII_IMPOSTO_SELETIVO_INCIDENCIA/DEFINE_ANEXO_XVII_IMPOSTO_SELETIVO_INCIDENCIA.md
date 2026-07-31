# DEFINE: Anexo XVII — Base de Incidência do Imposto Seletivo

> Identifica se um item de `/v1/tax/simulate` está na base de incidência do Imposto Seletivo
> (IS) — nunca calcula o valor do IS, que continua indisponível (alíquota fixada por lei
> ordinária, ainda inexistente). Primeiro tributo do projeto que não é CBS nem IBS.
>
> **Posição na sequência:** 16 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Roda depois da posição 15 (`ANEXO_XVI_PISO_ALIQUOTA_PROPRIA`, shipada
> 2026-07-31), sem nenhuma dependência técnica dela — o Anexo XVII usa NCM (como as 10 features
> de redução), não o padrão "ano → percentual" do Anexo XVI.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA |
| **Date** | 2026-07-31 |
| **Author** | define-agent |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |
| **Clarity Score** | 13/15 |

---

## Problem Statement

O art. 409 da LCP 214/2025 institui o Imposto Seletivo (IS) sobre bens/serviços "prejudiciais à
saúde ou ao meio ambiente" e delimita sua base de incidência em 7 categorias (§1º, incisos I-VII),
detalhadas por código NCM/SH no Anexo XVII — mas `/v1/tax/simulate` não identifica hoje se um item
específico está nessa base. O motor já recusa corretamente CALCULAR o valor do IS (a alíquota é
fixada por lei ordinária, ainda inexistente para a maioria das categorias) — mas não diz ao
usuário SE aquele item, mesmo sem alíquota, é ou não um bem/serviço sujeito ao IS. Essa é
informação pública, citável e útil hoje, independente de quando a lei ordinária existir.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Controller/CFO usando o simulador | Consumidor do produto | Não sabe, a partir da resposta, se um veículo, embarcação, produto fumígeno, bebida ou bem mineral que está simulando cairá no IS quando a lei ordinária existir — precisa hoje decidir isso manualmente lendo a lei |
| Consultoria tributária | Análise de portfólio de produtos de um cliente | Precisa mapear, para um catálogo inteiro de SKUs, quais produtos entram na base do IS (para planejamento tributário futuro), sem ferramenta que faça essa triagem hoje |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo COMPLETO do Anexo XVII (7 categorias, todos os códigos NCM e todas as ressalvas) verificado contra fonte primária nesta sessão — substitui a lista aproximada do brainstorm |
| **MUST** | Identificar e citar o dispositivo que institui a base de incidência (não estava claro no brainstorm): **art. 409, caput e §1º** (7 incisos, um por categoria) e **§2º** (condição de embalagem primária para fumígenos/bebidas alcoólicas — achado desta sessão, ausente do brainstorm) |
| **MUST** | Confirmado nesta sessão, contra fonte primária, que a LC 227/2026 **não alterou** nem o art. 409 nem o Anexo XVII (alterou artigos vizinhos — 414, 422 — sobre base de cálculo/alíquotas, não sobre a base de incidência em si) |
| **MUST** | `/v1/tax/simulate` sinaliza, por ITEM, se o NCM está na base de incidência do IS — citando a categoria (inciso I-VI) e o dispositivo — SEM produzir nenhum valor monetário de IS: a alíquota continua `None`/indisponível, mesma disciplina de `AliquotaNaoDisponivelError` |
| **MUST** | Categoria VII ("concursos de prognósticos e fantasy sport", art. 409, §1º, VII) não tem NENHUM código NCM ou NBS no Anexo XVII — documentada como não resolvida nesta feature, nunca confundida com as categorias I-VI (que têm código) |
| **MUST** | Condição de embalagem primária (art. 409, §2º — produtos fumígenos e bebidas alcoólicas só entram na base do IS "quando acondicionados em embalagem primária... destinada ao consumidor final") declarada explicitamente — o payload de `/v1/tax/simulate` não tem hoje nenhum campo para expressar isso; o `/design` decide se resolve com campo novo ou documenta como limitação, mas NUNCA presume que todo fumígeno/bebida alcoólica está automaticamente na base (nem o oposto) |
| **MUST** | Exceção por FINALIDADE DE USO (veículos/aeronaves/embarcações para uso operacional das Forças Armadas ou Segurança Pública, mesmo art. 409 combinado com o texto do Anexo XVII) documentada como limitação estrutural — `ItemSimulacao` não tem campo para capturar isso, e esta feature NÃO o adiciona (mesma decisão do brainstorm, YAGNI) |
| **MUST** | `motor_calculo/tabela_aliquotas.py` não é alterado — a alíquota do IS continua `None`/pendente para todas as fases; esta feature é ORTOGONAL ao valor, nunca uma tentativa de calculá-lo |
| **SHOULD** | Mencionar, como contexto informativo (não cálculo), os dois tetos/condições REAIS já fixados por lei que o brainstorm não tinha notado: (a) **art. 420** — alíquota ZERO para veículos adquiridos por beneficiários do regime diferenciado do art. 149 (uma condição de comprador, estruturalmente parecida com `comprador_tipo` já existente para CBS/IBS, mas para um regime NÃO modelado neste projeto); (b) **art. 422, §2º** — teto de 0,25% para bens minerais extraídos. Nenhum dos dois é calculado por esta feature (fora de escopo — ver Out of Scope), mas merecem nota no `/design` para não serem redescobertos do zero numa feature futura |
| **COULD** | Investigar se "concursos de prognósticos e fantasy sport" tem código NBS numa revisão da nomenclatura não capturada pelo texto legal (mesma classe de limitação já aceita para itens NBS "pendentes de classificação" de `ANEXOS_REDUCAO_PERCENTUAL_NBS`) |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

Mesma fonte já qualificada nas features anteriores (`legis.senado.leg.br`), com conferência
cruzada via o PDF "Texto Atualizado" da Câmara dos Deputados (LegIn) já baixado nesta sessão
(`www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-2025-796905-
normaatualizada-pl.pdf`, lido via `pdftotext -layout`).

**O que foi verificado, com URL/trecho e conteúdo real, nesta sessão (2026-07-31):**

1. **Anexo XVII completo** (`legis.senado.leg.br/norma/40180341/publicacao/40181073` — HTTP 200,
   e conferido dígito a dígito contra o PDF da Câmara): 7 categorias, todas as transcritas abaixo
   em "O Anexo XVII, verificado nesta sessão".
2. **Art. 409** (LIVRO II, TÍTULO I, "Disposições Preliminares" — não constava no brainstorm, que
   só citava "o Anexo XVII" sem o artigo que o institui):
   > "Art. 409. Fica instituído o Imposto Seletivo, de que trata o inciso VIII do art. 153 da
   > Constituição Federal, incidente sobre a produção, extração, comercialização ou importação de
   > bens e serviços prejudiciais à saúde ou ao meio ambiente.
   > § 1º Para fins de incidência do Imposto Seletivo, consideram-se prejudiciais à saúde ou ao
   > meio ambiente os bens classificados nos códigos da NCM/SH e o carvão mineral, e os serviços
   > listados no Anexo XVII, referentes a: I - veículos; II - embarcações e aeronaves; III -
   > produtos fumígenos; IV - bebidas alcoólicas; V - bebidas açucaradas; VI - bens minerais; VII
   > - concursos de prognósticos e fantasy sport.
   > § 2º Os bens a que se referem os incisos III e IV do § 1º estão sujeitos ao Imposto Seletivo
   > quando acondicionados em embalagem primária, assim entendida aquela em contato direto com o
   > produto e destinada ao consumidor final."
3. **Achado crítico — art. 409, §2º**: a condição de "embalagem primária" para produtos fumígenos
   (III) e bebidas alcoólicas (IV) **não constava em nenhum lugar do brainstorm**. Sem essa
   verificação, um `/design` ingênuo trataria qualquer NCM de fumígeno/bebida alcoólica como
   automaticamente sujeito ao IS — o que a lei não afirma: a sujeição depende de uma característica
   da embalagem que nenhum campo de `ItemSimulacao` hoje descreve.
4. **Achado adicional — arts. 420 e 422, §2º**: ao ler o Capítulo IV ("Das Alíquotas") para
   confirmar que nenhuma alíquota geral está fixada, dois FATOS REAIS (não pendências) apareceram:
   art. 420 fixa alíquota **ZERO** para veículos comprados por beneficiários do regime diferenciado
   do art. 149 (condição de comprador, mecanismo nunca modelado neste projeto — o "regime
   diferenciado" é uma estrutura própria, distinta de `comprador_tipo`); art. 422, §2º fixa um
   **TETO de 0,25%** para bens minerais extraídos (não um valor exato, mas um limite superior real,
   citável). Nenhum dos dois é MUST desta feature (ver Out of Scope), mas ambos são fatos
   verificados, não estimativas — registrados para não serem perdidos.
5. **LC 227/2026 não alterou o art. 409 nem o Anexo XVII** — confirmado consultando a página de
   detalhe da norma (`https://legis.senado.leg.br/norma/40180341`) e sua lista de "Alterações ou
   remissões por dispositivo" (já consultada nesta sessão para a feature anterior): a LC 227/2026
   alterou os arts. 408, 414, 422-434 (mecânica de base de cálculo/alíquotas, INCLUINDO uma
   alteração ao próprio art. 422, §2º — o teto de bens minerais foi REDIGIDO pela LC 227/2026, mas
   o VALOR do teto, 0,25%, é o mesmo texto atualizado já lido) — mas não o art. 409 nem o Anexo
   XVII, que ficam FORA da faixa 408-434 e da lista de Anexos alterados (7, 14, 20, 21).

Consultado em 2026-07-31.

---

## O Anexo XVII, verificado nesta sessão (art. 409, §1º, incisos I-VII)

| Inciso | Categoria | Código(s) NCM/SH | Ressalva |
|--------|-----------|--------------------|----------|
| I | Veículos | `87.03`; `8704.21`; `8704.31`; `8704.41.00`; `8704.51.00`; `8704.60.00`; `8704.90.00` (todos "exceto os caminhões" nas posições 8704.x) | Excluídos veículos com características técnicas específicas para uso operacional das Forças Armadas ou órgãos de Segurança Pública — exceção por FINALIDADE DE USO, não por código |
| II | Embarcações e aeronaves | `8802`, exceto `8802.60.00`; embarcações com motor na posição `8903` | Mesma ressalva de uso militar/segurança pública que o inciso I |
| III | Produtos fumígenos | `2401`; `2402`; `2403`; `2404` | Só sujeitos ao IS se em embalagem primária destinada ao consumidor final (art. 409, §2º) |
| IV | Bebidas alcoólicas | `2203`; `2204`; `2205`; `2206`; `2208` | Mesma condição de embalagem primária do inciso III |
| V | Bebidas açucaradas | `2202.10.00` | Nenhuma |
| VI | Bens minerais | `2601`; `2709.00.10`; `2711.11.00`; `2711.21.00` | Nenhuma (mas sujeitos ao teto de 0,25% do art. 422, §2º, fora de escopo desta feature) |
| VII | Concursos de prognósticos e fantasy sport | **Nenhum código** (célula vazia no Anexo XVII) | Sem código citável — nunca confundido com as categorias I-VI |

**Fonte:** `LCP 214/2025, art. 409, §§1º-2º, Anexo XVII`. Não alterado pela LC 227/2026.

---

## Success Criteria

- [ ] As 7 categorias do Anexo XVII (art. 409, §1º) verificadas contra DUAS fontes independentes
      (Senado + Câmara dos Deputados), com correspondência dígito a dígito — concluído nesta sessão
- [ ] Dispositivo identificado (art. 409, caput, §§1º-2º) — não constava no brainstorm
- [ ] Condição de embalagem primária (§2º, fumígenos/bebidas alcoólicas) documentada explicitamente
      — achado crítico desta sessão, ausente do brainstorm
- [ ] Confirmado contra fonte primária que a LC 227/2026 não alterou o art. 409 nem o Anexo XVII
- [ ] `/v1/tax/simulate` sinaliza, por item, se o NCM está na base de incidência do IS, citando
      categoria e dispositivo — SEM produzir valor monetário
- [ ] Categoria VII (sem código) documentada como não resolvida, nunca como "fora da base"
- [ ] Exceção por finalidade de uso (militar/segurança pública) documentada como limitação
      estrutural, não modelada nesta feature
- [ ] `motor_calculo/tabela_aliquotas.py` intocado — alíquota do IS continua `None`
- [ ] Zero regressão: os 14 Anexos de redução (10 NCM + 4 NBS), IPI, regime vigente e o piso do
      Anexo XVI continuam funcionando exatamente como hoje

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — veículo na base de incidência | `ncm` correspondente a `8704.21` (exceto caminhão) | `POST /v1/tax/simulate` | 200; item sinalizado como sujeito ao IS, categoria "Veículos", citando "LCP 214/2025, art. 409, §1º, I, Anexo XVII" |
| AT-002 | Bem mineral | `ncm` correspondente a `2601` | `POST /v1/tax/simulate` | Sujeito ao IS, categoria "Bens minerais" |
| AT-003 | Fumígeno — condição de embalagem primária não informada | `ncm` correspondente a `2402` (posição de cigarros) | `POST /v1/tax/simulate` | Resposta declara explicitamente a condição do art. 409, §2º — nunca afirma incondicionalmente que o item está sujeito ao IS nem que não está |
| AT-004 | Bebida açucarada, sem condição adicional | `ncm` correspondente a `2202.10.00` | `POST /v1/tax/simulate` | Sujeito ao IS, sem nenhuma condição a declarar (categoria V não tem ressalva) |
| AT-005 | NCM fora das 7 categorias | `ncm` de um item qualquer não coberto (ex. já usado em outros testes, `04051000`) | `POST /v1/tax/simulate` | Não sujeito ao IS — situação distinta de "não resolvido" |
| AT-006 | Categoria VII sem código nunca "resolve por acidente" | Qualquer `ncm`/`nbs` fantasiado tentando casar com "concursos de prognósticos" | `POST /v1/tax/simulate` | Nunca marcado como sujeito ao IS por essa categoria — documentado como não resolvido, distinto de "fora da base" |
| AT-007 | Exceção por uso militar/segurança pública nunca verificada silenciosamente | `ncm` de veículo sujeito ao IS, sem nenhum campo indicando uso militar | `POST /v1/tax/simulate` | Resposta trata o item como sujeito ao IS (não verifica a exceção de uso, que não é modelada) — mas a documentação/resposta deixa claro que essa exceção existe e não é verificada, nunca finge tê-la resolvido |
| AT-008 | Nenhum valor monetário de IS é produzido | Qualquer item sujeito ao IS, qualquer `ano_operacao` | `POST /v1/tax/simulate` | A resposta nunca contém um valor de "IS calculado" para esse item — `total_is`/`aliquotas_aplicadas.is_percentual` continuam exatamente como hoje (0 ou indisponível, conforme a fase) |
| AT-009 | Zero regressão | Payload idêntico a qualquer teste já existente | `POST /v1/tax/simulate` | Resposta idêntica à de antes desta feature, mais o campo aditivo novo |

---

## Out of Scope

- **Cálculo de qualquer valor de IS** — a alíquota geral continua indisponível (lei ordinária
  inexistente para a maioria das categorias); esta feature é só sobre a BASE DE INCIDÊNCIA.
- **Art. 420 (alíquota zero para veículos do regime diferenciado, art. 149)** — depende de um
  regime inteiro (elegibilidade de comprador via art. 149/153) que este projeto não modela hoje;
  registrado como achado para uma feature futura, não implementado aqui.
- **Art. 422, §2º (teto de 0,25% para bens minerais)** — é um TETO, não um valor fixo; calculá-lo
  como se fosse a alíquota efetiva seria uma estimativa não autorizada. Fora de escopo, mas citável
  como contexto informativo se o `/design` decidir.
- **Condição de embalagem primária (fumígenos/bebidas alcoólicas)**: a IMPLEMENTAÇÃO de um campo
  novo no payload para capturar isso é decisão do `/design` — o que não é opcional é que a
  condição seja declarada explicitamente, nunca presumida silenciosamente em qualquer direção.
- **Exceção por finalidade de uso (Forças Armadas/Segurança Pública)** — `ItemSimulacao` não ganha
  campo para isso nesta feature (mesma decisão YAGNI do brainstorm); documentada como limitação
  estrutural declarada.
- **Categoria VII (concursos de prognósticos e fantasy sport)** — sem código citável, documentada
  como não resolvida, nunca implementada por aproximação.
- Qualquer Anexo de CBS/IBS (posições 12-14) ou o Anexo XVI (posição 15) — tributos/mecanismos
  diferentes, já shipados.
- Simples Nacional (posição 17) — regime tributário à parte, próxima feature do roadmap.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/tabela_aliquotas.py` não pode ganhar nenhum valor de IS além do já existente (`None`/pendente) | Esta feature vive inteiramente em cima de uma nova classificação de NCM, ortogonal ao cálculo |
| Technical | O mecanismo de correspondência por NCM (prefixo, exceção por código) já está generalizado em `api/ncm.py`/`api/reducao.py` — reaproveitável para a base de incidência, mas é uma tabela/consulta PRÓPRIA (mesma disciplina de nunca comingle entre features de dado diferente, ver Achado crítico 4 de `ANEXOS_REDUCAO_PERCENTUAL_NBS`) | `/design` decide se cria tabelas novas (`imposto_seletivo_*`) ou reaproveita as existentes com discriminador — a recomendação é tabelas novas, pelo mesmo motivo da feature anterior |
| Legal | Categoria VII sem código citável — nunca implementada por analogia | Documentada, não resolvida |
| Legal | Condição de embalagem primária (§2º) e exceção de uso (Forças Armadas/Segurança Pública) não são verificáveis a partir do NCM sozinho | Ambas precisam de decisão explícita do `/design`, nunca silêncio |
| Legal | LC 227/2026 não alterou o art. 409 nem o Anexo XVII (alterou os arts. 414/422, mecânica de cálculo) | `/build` usa o texto vigente já lido nesta sessão |
| Business | Escopo estritamente limitado à identificação da base de incidência — nenhuma tentativa de resolver o valor do IS | Sucesso desta feature não depende de nenhuma lei ordinária futura |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Reaproveita o padrão de 3 camadas já validado 5 vezes (SQL puro → política pura → consumo em `api/routers/simulate.py`) — tabelas NOVAS (`imposto_seletivo_incidencia`/`imposto_seletivo_incidencia_ncm` ou nomes equivalentes a decidir no `/design`), migração nova (próxima numeração livre: `013_*.sql`), módulo novo (`api/imposto_seletivo.py` ou equivalente) | Estruturalmente mais parecido com os 10 Anexos NCM (mecanismo de correspondência) do que com o Anexo XVI (Python puro) — a diferença central é que aqui NÃO há percentual nenhum a devolver, só um booleano + citação |
| **KB Domains** | `database-reviewer` (schema simples: 7 categorias, ~14 códigos/faixas NCM, sem percentual), `python` (reaproveita `api/ncm.py`), `testing` (padrão Protocol real/fake já usado 6 vezes) | Volta a ter `database-reviewer` como agente central, diferente da feature anterior (Anexo XVI, sem infraestrutura) |
| **IaC Impact** | Nova migração Postgres a aplicar via `migrar_banco.yml` (mesmo fluxo já usado 6 vezes); `GRANT SELECT` para `taxreformai_app` | Nenhuma mudança de Terraform |

**Why This Matters:**

- **Location** → O mecanismo (prefixo NCM, exceção por código) já é genérico o bastante em
  `api/ncm.py` para ser reaproveitado sem mudança — a novidade é o SIGNIFICADO do resultado
  (booleano de incidência, não percentual de redução).
- **KB Domains** → Volta a precisar de schema real (diferente do Anexo XVI), mas o schema é o mais
  simples entre as 6 features que já tocaram Cloud SQL (sem catálogo de percentuais, sem condição
  declaratória de comprador/vendedor).
- **IaC Impact** → Mesmo fluxo de migração de sempre; o `script de verificação de produção` desta
  feature é mais simples que os anteriores (não há percentual nem desempate a provar, só presença/
  ausência na base).

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexo XVII (`legis.senado.leg.br`, mirror do DOU) | Texto legal | 7 categorias, ~14 códigos/faixas NCM | Estático — LC 227/2026 não o alterou (confirmado nesta sessão) | Legislativo Federal |
| LCP 214/2025, art. 409, §§1º-2º (idem) | Texto legal (dispositivo que institui a base) | 1 artigo + 2 parágrafos | Estático, idem | Legislativo Federal |
| Confirmação cruzada: Câmara dos Deputados (LegIn), "Texto Atualizado" (PDF) | Texto legal, fonte independente | Mesmas 7 categorias | Estático | Legislativo Federal (Câmara) |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| 7 categorias, NCM/prefixo por categoria | Reaproveita o mecanismo de prefixo já generalizado (`api/ncm.py`), tabelas PRÓPRIAS (nunca comingladas com `anexos_reducao*`) | Sim |
| Exceção por código dentro de uma categoria | Nenhuma observada nesta sessão (as "exceções" do Anexo XVII são por FINALIDADE DE USO, não por código — diferente do mecanismo `excecao` já existente para os 10 Anexos NCM) | Não aplicável a esta feature (ver Constraints) |
| Sinalizador de "sujeito ao IS" | Booleano + categoria + dispositivo — NUNCA um percentual ou valor | Sim |
| Categoria sem código (VII) | Documentada, nunca inserida na tabela de correspondência | Sim |
| Condição de embalagem primária (III, IV) | Coluna/flag indicando que a categoria tem essa condição — decisão do `/design` se o payload ganha campo novo ou se fica só documentado | Sim, uma das duas |

### Freshness SLAs

Não aplicável — dado estático, sem cláusula de revisão periódica no art. 409 nem no Anexo XVII.

### Completeness Metrics

- 7/7 categorias do Anexo XVII verificadas contra fonte primária nesta sessão (100%), com
  confirmação cruzada de uma SEGUNDA fonte independente
- 6/7 categorias têm código NCM citável; 1/7 (concursos de prognósticos) não tem nenhum código
- 2/7 categorias (fumígenos, bebidas alcoólicas) têm condição adicional (embalagem primária)
- 2/7 categorias (veículos, aeronaves/embarcações) têm exceção por finalidade de uso, não modelada

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto do Anexo XVII e do art. 409 obtidos via `legis.senado.leg.br` é o texto vigente | A base de incidência usada no `/design`/`/build` estaria errada | [x] Validado nesta sessão — conferido contra fonte independente (Câmara dos Deputados) e contra a lista de alterações da LC 227/2026 |
| A-002 | "Concursos de prognósticos e fantasy sport" nunca receberá código NBS que este projeto já teria capturado | Se a nomenclatura NBS já cobrir isso (fora do texto legal, que é tudo que foi verificado), a categoria VII poderia ser parcialmente resolvida numa feature futura | [ ] Não validado — mesma limitação de acesso à nomenclatura oficial já registrada em `ANEXOS_REDUCAO_PERCENTUAL_NBS` |
| A-003 | A condição de embalagem primária (art. 409, §2º) e a exceção de uso militar/segurança pública podem ficar como limitação DECLARADA nesta feature, sem novo campo de payload | Se o produto exigir resolver isso de fato, seria uma feature de extensão do payload — mesma disciplina já usada para `comprador_tipo`/`conteudo_nacional_majoritario` | [x] Confirmado como aceitável nesta sessão — mesma razão do YAGNI do brainstorm original |

**Note:** Validar A-002 é de baixo custo e não bloqueia o avanço. A-003 já está resolvida pela
decisão de escopo desta sessão, mas o `/design` deve decidir explicitamente a FORMA da declaração
(campo novo vs. nota fixa na resposta).

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Frase clara, dispositivo exato (art. 409) que o brainstorm não tinha, quantificado (7 categorias) |
| Users | 3 | Dois usuários com pain points específicos |
| Goals | 3 | MoSCoW explícito; achados críticos (§2º embalagem primária; arts. 420/422 §2º) são MUST/SHOULD, não escondidos |
| Success | 3 | Critérios testáveis e numéricos (7/7 categorias, 6/7 com código) |
| Scope | 1 | Duas decisões de fronteira ficam deliberadamente abertas para o `/design` (campo novo para embalagem primária; nome exato das tabelas) — correto por não presumir a resposta, mas a fronteira exata (schema, se há tabela de exceção por uso) ainda não está fechada, reduzindo a nota mais do que nas 2 features imediatamente anteriores |
| **Total** | **13/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** o brainstorm estimou esta feature como
simples ("sinalizador informativo"). A verificação desta sessão confirma a simplicidade RELATIVA
(schema mais simples que os 10 Anexos NCM, porque não há percentual nem catálogo), mas encontrou
DUAS condições que o brainstorm não tinha visto (embalagem primária, art. 409 §2º) e DOIS fatos
reais adicionais (alíquota zero condicionada do art. 420; teto do art. 422 §2º) que, mesmo fora de
escopo, aumentam a superfície de decisão do `/design` em relação ao que o brainstorm previa.

---

## Open Questions

Nenhum item abaixo bloqueia o avanço para `/design`:

1. **Nome exato das tabelas/módulo** (`imposto_seletivo_incidencia` vs. outro nome) — decisão do
   `/design`.
2. **Campo novo de payload para embalagem primária** (ex. `embalagem_primaria_consumidor_final:
   bool | None`) vs. documentar como limitação sem mudar o payload — decisão do `/design`, com a
   restrição de que a condição nunca pode ficar implícita.
3. **Onde vive o sinalizador na resposta** (novo bloco em `ItemDetalhado`, análogo a `reducao`,
   vs. outra forma) — decisão do `/design`.
4. **Se o teto do art. 422, §2º (bens minerais, 0,25%) e a condição do art. 420 (veículos, regime
   diferenciado) merecem nota informativa nesta feature ou ficam só registrados para o futuro** —
   decisão do `/design`, sem bloquear o MUST desta feature.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-31 | define-agent | Versão inicial, extraída de `BRAINSTORM_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md`; verificação de fonte primária realizada nesta sessão com dupla fonte independente (Senado + Câmara dos Deputados, 7/7 categorias idênticas). Identificado pela primeira vez o dispositivo que institui a base de incidência (art. 409, §§1º-2º) — o brainstorm só citava "o Anexo XVII". Achado crítico: a condição de embalagem primária (§2º, fumígenos/bebidas alcoólicas) não constava no brainstorm. Achados adicionais fora de escopo, mas registrados: alíquota zero condicionada do art. 420 (veículos, regime diferenciado do art. 149) e teto de 0,25% do art. 422, §2º (bens minerais) — dois fatos REAIS, não estimativas, que uma feature futura pode reaproveitar. Confirmado que a LC 227/2026 não alterou o art. 409 nem o Anexo XVII. |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md`
