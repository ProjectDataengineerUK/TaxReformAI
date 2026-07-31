# BRAINSTORM: Anexos II, III, X e XI — Redução de 60% de CBS/IBS por NBS

> Exploratory session to clarify intent and approach before requirements capture
>
> **Posição 14 de 17** na sequência pós-auditoria (ver
> `.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`, seção "Segunda leva"). A
> mais nova estruturalmente das 3 features de "produto/serviço": nenhuma parte do projeto
> hoje tem lookup por NBS (Nomenclatura Brasileira de Serviços) — `api/ncm.py` e o schema do
> Anexo I são inteiramente sobre NCM.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NBS |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | Pronto para `/define` |
| **Posição na sequência** | 14 de 17 (`ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`) |

---

## Initial Idea

**Raw Input:** Dos 16 Anexos restantes, quatro (II, III, X, XI) aplicam redução de 60% cuja
chave é predominantemente NBS (serviços), não NCM. Isso exige infraestrutura nova — nenhum
lookup por serviço existe hoje neste projeto.

**Context Gathered (nesta sessão, verificado contra fonte primária):**

- Fonte: `legis.senado.leg.br/norma/40180341/publicacao/{id}` — II=`40180894`, III=`40180900`,
  X=`40180985`, XI=`40180991`.
- **Anexo II**: "SERVIÇOS DE EDUCAÇÃO SUBMETIDOS À REDUÇÃO DE 60%". NBS puro (ex. "Ensino
  Infantil, inclusive creche e pré-escola", código `1.2201.1`). ~7 códigos observados — o
  menor do grupo.
- **Anexo III**: "SERVIÇOS DE SAÚDE SUBMETIDOS À REDUÇÃO DE 60%". NBS puro (ex. "Serviços
  cirúrgicos", `1.2301.11.00`). ~22 códigos.
- **Anexo X**: "PRODUÇÕES NACIONAIS ARTÍSTICAS, CULTURAIS, DE EVENTOS, JORNALÍSTICAS E
  AUDIOVISUAIS SUBMETIDAS À REDUÇÃO DE 60%". Cabeçalho **"NBS/NCM"** — misto, mas os itens
  observados (licenciamento de direitos autorais, `1.1103`/`1.1103.10.00`/`1.1103.31.00`) são
  predominantemente NBS. ~51 códigos.
- **Anexo XI**: "BENS E SERVIÇOS RELACIONADOS À SOBERANIA E À SEGURANÇA NACIONAL, [...]
  SEGURANÇA CIBERNÉTICA SUBMETIDOS À REDUÇÃO DE 60%". Cabeçalho **"NBS / NCM/SH"** —
  explicitamente "bens e serviços" no próprio título, mas os itens observados são
  majoritariamente serviços de TI (ex. "Segurança em Tecnologia da Informação (TI)",
  `1.1501.20.00`). ~33 códigos.
- **Formato do código NBS observado**: diferente do NCM (numérico com pontos, ex.
  `8708.99.10`), o NBS tem um prefixo adicional antes do primeiro ponto (ex. `1.2201.1`,
  `1.1103.31.00`) — não é uma simples troca de vocabulário, é uma estrutura de código
  diferente. `/design` não pode reaproveitar `digitos_ncm`/`prefixos_ncm` de `api/ncm.py` sem
  adaptação; precisa investigar a estrutura completa do NBS (quantos dígitos por nível
  hierárquico) antes de desenhar o schema.
- **Nenhum precedente no projeto**: `db/`, `motor_calculo/`, `api/` não têm nenhuma menção a
  NBS hoje. Esta é a primeira feature de toda a leva (e do projeto) que precisa desenhar do
  zero um vocabulário de correspondência por serviço.
- **Risco herdado**: LC 227/2026 nunca foi checada contra estes 4 Anexos.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|--------------|
| Estrutura do código NBS | Prefixo antes do primeiro ponto (`1.2201.1`), diferente do NCM puro | `/design` precisa investigar a hierarquia oficial do NBS (Nomenclatura Brasileira de Serviços, mantida pela RFB) antes de decidir a forma da tabela de prefixo — não é um `s/ncm/nbs/` no schema existente |
| Anexos mistos (X, XI) | Cabeçalho cita NBS *e* NCM/SH | Itens de chave NCM dentro de X e XI ficam documentados como não resolvidos nesta feature, por decisão do usuário — mesmo tratamento que o Anexo IX recebeu na posição 13, mas invertido (aqui o NCM é a minoria) |
| Serviço "puro" nos itens observados | Educação (II) e Saúde (III) não têm nenhum código NCM — são o caso mais simples desta feature | `/design` pode escolher começar a implementação/teste por esses dois antes de X/XI, que exigem decidir o que fazer com os itens NCM residuais |
| Volume | Menor volume total do grupo (~7+22+51+33 ≈ 113 códigos observados) comparado à posição 13 (~322) | Não reduz o esforço de design (infraestrutura nova), mas indica menor volume de transcrição |
| Relevant KB Domains | python-developer, database-reviewer — nenhum domínio de KB específico para NBS foi encontrado no `_index.yaml` | Primeira feature da leva sem nenhum precedente de KB ou de código a reaproveitar; tratar como desenho genuinamente novo |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como agrupar os 16 Anexos restantes em features? | Híbrido: mecanismo + chave | Definiu esta feature como "percentual + NBS dominante" |
| 2 | Anexos mistos (IX, X, XI) — como tratar? | Dominante + pendência explícita | X e XI entram aqui; seus itens NCM ficam pendentes |
| 3 | Onde esta leva entra na sequência? | Depois das 9 posições já roteirizadas | Posição 14 |

**Minimum Questions:** 3 ✅

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Ground truth (Anexos II, III, X, XI) | `legis.senado.leg.br` | ~7+22+51+33 ≈ 113 códigos observados (aproximado) | Transcrição exata é trabalho do `/define` |
| Estrutura do NBS | Observada nos códigos, não documentada formalmente nesta sessão | N/A | `/define` precisa localizar a fonte oficial da estrutura hierárquica do NBS (RFB) antes do `/design` desenhar o schema |
| Anexos mistos | X e XI (cabeçalho "NBS/NCM") | A quantificar no `/define` | Itens NCM ficam fora de escopo desta feature |
| Fixture de teste | Nenhuma ainda | 0 | A definir no `/design` |

**Como os dados serão usados (se aprovado no /define):** o payload de `/v1/tax/simulate`
precisaria de um campo novo para identificar serviços por código NBS — hoje `ItemSimulacao`
só tem `ncm`. Essa é uma mudança de contrato da API, não só de schema de banco, diferente das
posições 12/13.

---

## Approaches Explored

### Approach A: Schema e vocabulário NBS espelhando o padrão NCM, mas com investigação própria da hierarquia do código ⭐ Recomendada

**What:** Criar `api/nbs.py` (irmão de `api/ncm.py`) com as funções equivalentes de
normalização/expansão de prefixo, uma vez que a estrutura hierárquica real do NBS seja
confirmada no `/define`. Payload da API ganha um campo `nbs` opcional em `ItemSimulacao`
(análogo a `ncm`), e o override de cálculo reaproveita `aplicar_reducao_percentual` (se já
existir da posição 13) ou é implementado aqui, o que vier primeiro na ordem real de entrega.

**Pros:**
- Replica o padrão já validado (vocabulário compartilhado, prefixo, override puro) em vez de
  inventar uma abordagem nova
- Isola a única parte genuinamente nova (a estrutura do código NBS) da parte já resolvida
  (mecanismo de redução percentual)

**Cons:**
- Depende de investigação de fonte primária adicional (estrutura oficial do NBS), que não é
  garantida ter a mesma forma do NCM (dígitos por nível)
- Muda o contrato de `ItemSimulacao` (campo novo), o que nenhuma das features anteriores desta
  leva precisou fazer — usuários de API (clientes ERP) precisam ser informados

**Why Recommended:** Minimiza o risco tratando o "novo" (NBS) como uma extensão do padrão
"velho" (NCM) em vez de um desenho paralelo inteiro.

### Approach B: Adiar esta feature até a estrutura do NBS ser mapeada numa investigação separada

**What:** Antes de comprometer a posição 14 no roadmap, rodar uma investigação dedicada
(fora do ciclo `/brainstorm`→`/define`→...) só para mapear a fonte oficial e a estrutura do
NBS, no mesmo espírito da investigação `LC_227_2026_ATUALIZACAO_LEGAL`.

**Pros:**
- Reduz o risco de o `/design` descobrir tarde demais que o NBS tem uma estrutura muito
  diferente do NCM

**Cons:**
- Adiciona uma etapa extra à sequência sem necessidade clara — o `/define` já é o lugar onde
  esse tipo de descoberta acontece (foi assim para os itens 19/20 do Anexo I)
- Contradiz o padrão já estabelecido de resolver descobertas de fonte primária dentro do
  próprio ciclo da feature, não como pré-requisito bloqueante

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — replicar o padrão NCM para NBS, com investigação da estrutura do código feita dentro do `/define` desta própria feature |
| **User Confirmation** | Decisão de agrupamento e tratamento de Anexos mistos confirmadas nesta sessão |
| **Reasoning** | Consistente com o padrão de todas as features anteriores: investigação de fonte primária acontece no `/define`/`/design`, não como pré-requisito separado |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo é II, III, X e XI — os 4 Anexos de 60% com chave NBS dominante | Mesmo mecanismo (percentual), chave nova (NBS) | Anexo IX (NCM dominante) vai para a posição 13 |
| 2 | Itens de chave NCM dentro de X e XI ficam documentados como não resolvidos nesta feature | Decisão do usuário sobre Anexos mistos | Resolver os dois tipos de chave na mesma feature — rejeitado, dobraria o escopo técnico novo |
| 3 | `ItemSimulacao` precisa de um campo novo (`nbs`) — mudança de contrato de API, não só de schema | Diferente das posições 12/13, que só tocam `ncm` já existente | Reaproveitar o campo `ncm` para carregar códigos NBS — rejeitado, seria confundir dois vocabulários diferentes no mesmo campo |
| 4 | Verificar se a LC 227/2026 alterou algum dos 4 Anexos | Mesma disciplina das outras 5 features desta leva | Assumir que não — rejeitado |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|--------------------|------------------|------------------|
| Resolver os itens NCM residuais de X e XI nesta feature | Decisão do usuário: dominante + pendência explícita | Sim, como extensão futura ou dentro da posição 13 se fizer mais sentido técnico na hora |
| Investigação separada da estrutura do NBS antes desta feature (Approach B) | Contradiz o padrão já estabelecido de resolver no próprio `/define` | Não necessário — mesma disciplina das features anteriores |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|-----------------|-----------|
| Agrupamento híbrido | ✅ | Confirmado | Definiu esta feature como "percentual + NBS" |
| Anexos mistos (X, XI) | ✅ | Dominante + pendência explícita | Incluídos com ressalva |
| Sequência (posição 14) | ✅ | Depois das 9 restantes | Registrado no roadmap |

**Minimum Validations:** 3 de 2 ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Quatro Anexos da LCP 214/2025 (II, III, X, XI) aplicam redução de 60% de CBS/IBS a serviços
de educação, saúde, produções culturais e segurança/cibersegurança — mas o projeto não tem
hoje nenhum conceito de correspondência por serviço (NBS); `ItemSimulacao` só identifica
mercadorias por NCM. Clientes que consomem serviços cobertos por esses Anexos não têm como
simular o benefício.

### Success Criteria (Draft)
- [ ] Estrutura oficial do código NBS investigada e documentada (fonte: RFB ou a própria
      transcrição dos Anexos)
- [ ] Conteúdo completo dos 4 Anexos verificado contra fonte primária
- [ ] `ItemSimulacao` ganha campo novo para identificar serviço por NBS
- [ ] `/v1/tax/simulate` aplica redução de 60% a itens de serviço cujo NBS esteja nos 4
      Anexos, citando a fonte
- [ ] Itens de chave NCM residuais em X e XI documentados como não resolvidos, nunca
      silenciosamente ignorados
- [ ] Confirmado se a LC 227/2026 alterou algum dos 4 Anexos
- [ ] `motor_calculo/` continua sem dependência de infraestrutura

### Constraints Identified
- Mudança de contrato de API (campo novo) — comunicar a clientes ERP consumidores
- Sem RLS na(s) tabela(s) nova(s)
- Reaproveitar `aplicar_reducao_percentual` se a posição 13 já a tiver implementado

### Out of Scope (Confirmed)
- Anexos de chave NCM dominante (posição 13)
- Anexo XVI, XVII, Simples Nacional (posições 15-17)
- Itens NCM residuais dos próprios Anexos X e XI

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 (nível de leva) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 3 de 2 |
| Duration | Parte da sessão única desta leva, incluindo verificação real dos 4 Anexos contra `legis.senado.leg.br` |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NBS.md`

**Posição na sequência:** 14 de 17 — depende de prioridade das posições 3-11 e das posições
12-13 conforme `ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`.
