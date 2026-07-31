# DEFINE: Anexo XVI — Piso da Alíquota Própria de Estados e Municípios

> Limite inferior (2029-2077) que Estados/Municípios podem fixar para a fatia própria do IBS,
> como proporção da alíquota de referência — primeira feature do projeto que NÃO é sobre
> produto nem serviço, e a de schema mais simples de toda a leva.
>
> **Posição na sequência:** 15 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Roda depois da posição 14 (`ANEXOS_REDUCAO_PERCENTUAL_NBS`, shipada 2026-07-31,
> os 4 Anexos completos), mas sem NENHUMA dependência técnica dela — Anexo XVI não usa NCM, NBS,
> nem qualquer mecanismo de correspondência por código já construído nas 5 features anteriores
> desta leva.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXO_XVI_PISO_ALIQUOTA_PROPRIA |
| **Date** | 2026-07-31 |
| **Author** | define-agent |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O art. 371 da LCP 214/2025 (Capítulo II, "Do Limite para Redução das Alíquotas do IBS de 2029 a
2077") proíbe Estados, Distrito Federal e Municípios de fixarem a alíquota própria do IBS abaixo
de um piso — um percentual da "alíquota de referência" da respectiva esfera federativa, fixado
ano a ano no Anexo XVI, de 2029 a 2077 (49 anos). Esse dado não está representado em lugar nenhum
do projeto hoje: nenhuma tabela, nenhum consumidor em `/v1/tax/simulate`. Diferente de todas as 5
features anteriores desta leva, não há produto nem serviço envolvido — é uma faculdade normativa
de ente federativo, indexada só por ano.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Controller/CFO usando o simulador | Consumidor do produto (via ERP ou frontend) | Ao simular uma operação em 2029 ou além, não tem como saber, a partir da resposta, qual é o piso legal que o Estado/Município de destino pode ou não respeitar ao fixar sua própria alíquota de IBS — informação relevante para auditoria de compliance fiscal de longo prazo |
| Consultoria tributária | Usuária avançada, análise de cenários multi-ano | Precisa demonstrar a um cliente como o piso evolui ano a ano (ex.: por que 2033 salta para 90,5% e depois cai progressivamente até 6,9% em 2077) sem transcrever a tabela manualmente da lei |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Tabela COMPLETA do Anexo XVI (49 anos, 2029 a 2077) verificada contra fonte primária nesta sessão — substitui os 5 anos (2029-2033) que o brainstorm tinha observado |
| **MUST** | Identificar e citar o dispositivo que rege o Anexo (não identificado pelo brainstorm): **art. 371, §1º** (o percentual do Anexo aplica-se sobre a alíquota de referência da esfera) e **§2º** (se o ente fixar abaixo do piso, prevalece o piso calculado) |
| **MUST** | Confirmado nesta sessão, contra fonte primária, que a LC 227/2026 **não alterou** nem o art. 371 nem o Anexo XVI |
| **MUST** | Decisão de produto: o piso entra em `/v1/tax/simulate` como campo/bloco INFORMATIVO no nível da REQUISIÇÃO (indexado só por `ano_operacao`, nunca por item — este dado não tem NCM, NBS, nem SKU) — resolve a pergunta em aberto do brainstorm a favor da Approach A, com a granularidade (request-level, não item-level) como achado desta sessão |
| **MUST** | Nenhuma alíquota final do IBS subnacional é calculada — o percentual do Anexo XVI só é MULTIPLICADOR de uma "alíquota de referência por esfera federativa" que **não é um valor de tabela**: é uma grandeza CALCULADA (art. 370) a partir de estimativas de receita real (CBS/IBS/impostos antigos, médias de anos-base), nunca fixada como número na lei. Diferente do "achado 12" (bloqueado por lei ainda não promulgada), aqui o bloqueio é ESTRUTURAL — mesmo com a lei promulgada, o valor depende de dado fiscal de execução real que este projeto não ingere e não tem como ingerir (mesma classe de limitação já aceita para ICMS interno/ISS: "não existe agregador federal") |
| **MUST** | Anos fora da janela 2029-2077 (antes de 2029, depois de 2077) são **NÃO SE APLICA**, nunca confundidos com "não encontrado"/"não fixado" — o art. 371 delimita explicitamente o intervalo no caput ("De 2029 a 2077") |
| **SHOULD** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura — mesmo padrão de `regime_atual.py` (tabela pequena, Python puro, sem banco) |
| **COULD** | Investigar se a Resolução CGIBS 6/2026 (já ingerida no Qdrant, 617 artigos, regulamenta o IBS) define a fórmula de cálculo da alíquota de referência com mais detalhe que o art. 370 — fora de escopo desta feature (não muda o piso do Anexo XVI em si), mas registrado como contexto para uma eventual feature futura que tentasse desbloquear o "achado 12"/alíquota de referência |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

Mesma fonte já qualificada nas 5 features anteriores desta leva (`legis.senado.leg.br`), mais uma
SEGUNDA fonte independente usada como conferência cruzada — o PDF "Texto Atualizado" da Câmara dos
Deputados (LegIn), já usado no fechamento do Anexo X de `ANEXOS_REDUCAO_PERCENTUAL_NBS` nesta mesma
sessão, lido via `pdftotext -layout` (contorna o limite de tamanho da ferramenta de leitura web para
o corpo integral da LCP 214/2025).

**O que foi verificado, com URL e conteúdo real, nesta sessão (2026-07-31):**

1. **Anexo XVI completo** (49 linhas, 2029-2077):
   `https://legis.senado.leg.br/norma/40180341/publicacao/40181067` — HTTP 200. Tabela: 81,0%
   (2029-2032) → 90,5% (2033, o único SALTO para cima) → declínio quase monotônico até 6,9% em
   2077. Os 5 anos que o brainstorm tinha capturado (2029-2033) conferem exatamente; os 44 anos
   restantes (2034-2077) são novos nesta sessão.
2. **Confirmação cruzada independente**: o mesmo Anexo XVI, extraído do PDF "Texto Atualizado" da
   Câmara dos Deputados (`www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-
   2025-796905-normaatualizada-pl.pdf`, já baixado nesta sessão para o Anexo X) via `pdftotext
   -layout` — **os 49 valores batem, dígito a dígito**, com a leitura do Senado.
3. **Dispositivo que rege o Anexo** (não identificado pelo brainstorm original): localizado no
   mesmo PDF, `CAPÍTULO II — DO LIMITE PARA REDUÇÃO DAS ALÍQUOTAS DO IBS DE 2029 A 2077`:
   > "Art. 371. De 2029 a 2077 é vedado aos Estados, ao Distrito Federal e aos Municípios fixar
   > alíquotas do IBS inferiores às necessárias para garantir as retenções de que tratam o § 1º do
   > art. 131 e o art. 132, ambos do Ato das Disposições Constitucionais Transitórias da
   > Constituição Federal.
   > § 1º Para fins do disposto no caput deste artigo, as alíquotas do IBS fixadas pelos Estados,
   > pelo Distrito Federal e pelos Municípios não poderão ser inferiores ao valor resultante da
   > aplicação dos percentuais estabelecidos para cada ano no Anexo XVI, sobre a alíquota de
   > referência da respectiva esfera federativa.
   > § 2º Na hipótese de fixação da alíquota pelo ente em nível inferior ao previsto no § 1º,
   > prevalecerá o limite inferior da alíquota, calculado nos termos do § 1º deste artigo."
4. **A "alíquota de referência" citada no §1º é CALCULADA, não tabelada** — confirmado lendo o
   artigo imediatamente anterior no mesmo Capítulo (art. 370, não transcrito por inteiro aqui por
   estar fora de escopo, mas seu caput e §§1º-4º definem um "redutor" calculado a partir de médias
   de estimativa de receita de CBS/IBS/tributos antigos para anos-base históricos, ano a ano —
   nenhum valor fixo, uma fórmula sobre dado fiscal real). Achado que MUDA o entendimento do
   brainstorm: a dependência com o "achado 12" não é só "a lei ainda não existe" (que é o caso da
   CBS de referência 2027-2028) — para a alíquota de referência do IBS por esfera federativa, o
   bloqueio é estrutural mesmo com a lei em vigor, porque o valor nasce de execução fiscal real, não
   de texto legal.
5. **LC 227/2026 não alterou nem o art. 371 nem o Anexo XVI** — confirmado consultando a página de
   detalhe da norma (`https://legis.senado.leg.br/norma/40180341`) e sua lista de "Alterações ou
   remissões por dispositivo": a LC 227/2026 alterou uma lista extensa de artigos e os Anexos 7, 14
   (revogado), 20 e 21 — nenhum deles é o art. 371 ou o Anexo XVI.

Consultado em 2026-07-31.

---

## O Anexo XVI, verificado nesta sessão

**Tabela completa (49 anos, 2029-2077)** — a coluna "Limite Inferior" é a fração da alíquota de
referência da esfera federativa que o ente NÃO pode fixar abaixo dela:

| Período | Padrão observado |
|---------|-------------------|
| 2029-2032 | Constante em 81,0% |
| 2033 | Salto único para 90,5% (o único ano em que o piso SOBE) |
| 2034-2077 | Declínio quase monotônico, de 88,6% (2034) a 6,9% (2077) — um "sunset" de 44 anos que praticamente extingue o piso |

Tabela completa (todos os 49 valores, para a migração do `/build`):

```
2029 81.0%   2042 73.4%   2055 48.7%   2068 24.0%
2030 81.0%   2043 71.5%   2056 46.8%   2069 22.1%
2031 81.0%   2044 69.6%   2057 44.9%   2070 20.2%
2032 81.0%   2045 67.7%   2058 43.0%   2071 18.3%
2033 90.5%   2046 65.8%   2059 41.1%   2072 16.4%
2034 88.6%   2047 63.9%   2060 39.2%   2073 14.5%
2035 86.7%   2048 62.0%   2061 37.3%   2074 12.6%
2036 84.8%   2049 60.1%   2062 35.4%   2075 10.7%
2037 82.9%   2050 58.2%   2063 33.5%   2076  8.8%
2038 81.0%   2051 56.3%   2064 31.6%   2077  6.9%
2039 79.1%   2052 54.4%   2065 29.7%
2040 77.2%   2053 52.5%   2066 27.8%
2041 75.3%   2054 50.6%   2067 25.9%
```

**Condição legal (art. 371, §§1º-2º)**: o percentual multiplica a "alíquota de referência da
respectiva esfera federativa" — um valor que NÃO está neste Anexo nem em nenhuma tabela da lei
(ver Achado 4 da verificação acima). Isso significa que o Anexo XVI, sozinho, produz um
PERCENTUAL DE REFERÊNCIA (ex. "81,0% da alíquota de referência de 2029"), nunca um número absoluto
de alíquota — a mesma disciplina de "nunca estimar" já aplicada ao "achado 12" (2027-2028 CBS
parcial) se aplica aqui, com uma causa raiz diferente e mais permanente (dado de execução fiscal
real, não lei pendente).

**Fonte:** `LCP 214/2025, art. 371, §§1º-2º, Anexo XVI`. Não alterado pela LC 227/2026.

---

## Success Criteria

- [ ] Tabela completa do Anexo XVI (49 anos, 2029-2077) verificada contra DUAS fontes
      independentes (Senado + Câmara), com 100% de correspondência — concluído nesta sessão
- [ ] Dispositivo que rege o Anexo (art. 371, §§1º-2º) identificado e citado — não constava no
      brainstorm original — concluído nesta sessão
- [ ] Confirmado contra fonte primária que a LC 227/2026 não alterou o art. 371 nem o Anexo XVI —
      concluído nesta sessão
- [ ] Decisão de produto tomada: piso exposto como bloco informativo em `/v1/tax/simulate`,
      indexado só por `ano_operacao` (nível de REQUISIÇÃO, não de item) — nunca tentando calcular
      a alíquota final do IBS subnacional
- [ ] Anos fora de 2029-2077 (antes ou depois) tratados como NÃO SE APLICA, nunca confundidos com
      "não encontrado" ou com um piso de 0%/100% presumido
- [ ] `motor_calculo/` não ganha nenhuma dependência de infraestrutura (schema Python puro, mesmo
      padrão de `regime_atual.py`)
- [ ] Zero regressão: os 14 Anexos de redução (10 NCM + 4 NBS), o IPI e o regime vigente continuam
      funcionando exatamente como hoje — este é um campo puramente ADITIVO à resposta

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — início da janela (2029) | `ano_operacao = 2029` | `POST /v1/tax/simulate` | 200; bloco do piso presente, `limite_inferior_percentual = 81.0`, dispositivo citado "LCP 214/2025, art. 371, §1º, Anexo XVI" |
| AT-002 | O único ano de SALTO (2033) | `ano_operacao = 2033` | `POST /v1/tax/simulate` | `limite_inferior_percentual = 90.5` — prova que a tabela não é lida como monotônica por presunção |
| AT-003 | Fim da janela (2077) | `ano_operacao = 2077` | `POST /v1/tax/simulate` | `limite_inferior_percentual = 6.9` |
| AT-004 | Antes da janela (2026, o ano corrente do projeto) | `ano_operacao = 2026` | `POST /v1/tax/simulate` | Bloco do piso ausente/nulo com indicação explícita de "não se aplica" (regime do art. 371 só vale de 2029 a 2077) — nunca omitido em silêncio nem com um valor presumido |
| AT-005 | Depois da janela (2078, hipotético) | `ano_operacao = 2078` | `POST /v1/tax/simulate` | Mesma resposta de AT-004 — fora da janela em qualquer direção é o mesmo "não se aplica", nunca um erro 422 (o motor de cálculo do IVA Dual em si pode ou não suportar 2078, isso é decisão de `fases.py`, ortogonal a esta feature) |
| AT-006 | Nunca calcula alíquota final | Qualquer `ano_operacao` dentro de 2029-2077 | `POST /v1/tax/simulate` | A resposta NUNCA contém um valor de "alíquota mínima de IBS em R$/percentual absoluto" — só o percentual do Anexo XVI e a citação de que ele multiplica uma alíquota de referência não calculável por este projeto |
| AT-007 | Zero regressão | Payload idêntico ao de qualquer teste já existente (Anexos NCM/NBS, IPI, regime vigente) | `POST /v1/tax/simulate` | Resposta idêntica à de antes desta feature, mais o campo aditivo novo |
| AT-008 | Motor determinístico sem infraestrutura | — | Import de `motor_calculo.piso_aliquota_ibs` (ou equivalente) | Nenhuma dependência de `psycopg`/banco — mesmo padrão de `regime_atual.py` |

---

## Out of Scope

- **Cálculo da alíquota de referência por esfera federativa** (o "achado 12", agora com causa raiz
  mais precisa: é uma grandeza CALCULADA a partir de execução fiscal real — art. 370 —, não um
  valor de lei pendente de promulgação). Sem isso, o Anexo XVI nunca produz um número absoluto de
  alíquota, só um percentual multiplicador — aceito como limitação permanente, não temporária.
- **Qualquer tabela por Estado/Município individual** (27 UFs + 5.570 municípios) — o Anexo XVI é
  nacional, uniforme por ano; a "alíquota de referência" (fora de escopo, ver acima) é que
  eventualmente variaria por ente, não o percentual do Anexo.
- **Art. 370** (o "redutor" da CBS/IBS para fins de estimativa de receita, 2027-2033) — dispositivo
  vizinho, mas sobre um mecanismo diferente (cálculo transitório da própria alíquota de
  referência), não sobre o piso em si. Candidato a investigação futura, não a esta feature.
- **Anexo XVII (Imposto Seletivo, posição 16) e Simples Nacional (posições 18-23, posição 17)** —
  features futuras próprias, sem relação de dado com o Anexo XVI.
- Qualquer Anexo de produto/serviço (posições 12-14, já shipadas) — o Anexo XVI não usa NCM nem NBS.
- Endpoint dedicado separado de `/v1/tax/simulate` (Approach B do brainstorm) — decisão desta
  sessão: bloco informativo dentro da resposta existente, indexado por `ano_operacao`, é
  suficiente e mais descobrível; um endpoint próprio pode ser reconsiderado no `/design` se a
  granularidade request-level se provar errada, mas não há indício disso agora.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar sem infraestrutura — tabela pequena (49 linhas), Python puro | Mesmo padrão de `regime_atual.py`/`tabela_aliquotas.py`, nenhuma migração de banco necessária |
| Technical | O dado é indexado SÓ por ano, nunca por item/NCM/NBS — primeira feature de redução da leva sem chave de produto/serviço | `/design` decide se vive em `motor_calculo/` (mais provável, dado o padrão de `regime_atual.py`) ou precisa de schema novo — mas não precisa de tabela relacional, um dicionário Python `{ano: Decimal}` basta |
| Legal | O percentual multiplica uma alíquota de referência NÃO calculável por este projeto (art. 370, dado de execução fiscal real) | Nunca produzir um valor absoluto de alíquota mínima — só o percentual e a citação legal |
| Legal | Janela temporal explícita no caput do art. 371: "De 2029 a 2077" | Anos fora dessa janela são NÃO SE APLICA, nunca "não encontrado" |
| Business | Escopo estritamente limitado ao Anexo XVI — nenhuma tentativa de resolver a alíquota de referência (fora de escopo permanente) | Sucesso desta feature não depende do achado 12/art. 370 nunca serem desbloqueados |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Provavelmente só `motor_calculo/` (tabela Python pura, sem banco) + extensão de `api/schemas_simulate.py` (bloco novo na resposta) + `api/routers/simulate.py` (popular o bloco a partir de `payload.ano_operacao`) — decisão final de "banco vs. Python puro" cabe ao `/design`, mas o padrão de `regime_atual.py` (tabelas pequenas, estáticas, citáveis por artigo, sem I/O) é o precedente mais próximo | Diferente de TODAS as 5 features anteriores desta leva: nenhuma migração SQL é obrigatória — 49 linhas ano→percentual não precisam de tabela relacional para serem citáveis e testáveis |
| **KB Domains** | `python` (clean patterns, já usado em `regime_atual.py`), `testing` (mesmo padrão Protocol real/fake, se aplicável) | Nenhum domínio de banco de dados necessário nesta feature — primeira da leva sem `@database-reviewer` como agente central |
| **IaC Impact** | Nenhum — sem migração, sem GRANT, sem tabela nova no Cloud SQL | Reduz drasticamente a superfície de verificação de infraestrutura real desta feature comparada às 5 anteriores |

**Why This Matters:**

- **Location** → Sem tabela relacional, esta é a primeira feature da leva onde `/design` pode
  legitimamente considerar Python puro em vez de SQL — mas a decisão final (e o porquê) precisa
  ficar explícita no `/design`, não presumida.
- **KB Domains** → Ausência do `database-reviewer` como agente central é um sinal correto da
  simplicidade do dado, não um descuido.
- **IaC Impact** → Sem migração significa sem a classe inteira de riscos que as 5 features
  anteriores desta leva enfrentaram (GRANT faltando, rename de tabela em uso, etc.) — mas também
  sem a garantia de integridade que uma CHECK constraint de banco daria; `/design` deve decidir se
  isso é aceitável para um dado que não muda (é lei promulgada, não seed operacional).

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexo XVI (`legis.senado.leg.br`, mirror do DOU) | Texto legal | 49 linhas (2029-2077) | Estático — LC 227/2026 não o alterou (confirmado nesta sessão) | Legislativo Federal |
| LCP 214/2025, art. 371, §§1º-2º (idem) | Texto legal (dispositivo que rege o Anexo) | 1 artigo + 2 parágrafos | Estático, idem | Legislativo Federal |
| Confirmação cruzada: Câmara dos Deputados (LegIn), "Texto Atualizado" (PDF) | Texto legal, fonte independente | Mesmas 49 linhas | Estático | Legislativo Federal (Câmara) |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Tabela ano → percentual | 49 entradas, 2029-2077, `Decimal` de 1 casa decimal (ex. `81.0`, `90.5`, `6.9`) | Sim |
| Janela temporal explícita | Anos fora de [2029, 2077] devolvem "não se aplica", nunca um valor | Sim |
| Citação legal | "LCP 214/2025, art. 371, §1º, Anexo XVI" (mais §2º quando relevante à explicação da prevalência do piso) | Sim |
| Nunca calcula alíquota absoluta | O bloco da resposta expõe só o percentual do Anexo XVI, nunca multiplicado por nada (a alíquota de referência não existe neste projeto) | Sim |

### Freshness SLAs

Não aplicável — dado estático, sem pipeline de atualização recorrente e sem cláusula de revisão
periódica no corpo do art. 371 (diferente dos Anexos IV/V/VI/IX, que têm revisão a cada 120 dias).

### Completeness Metrics

- 49/49 anos do Anexo XVI verificados contra fonte primária nesta sessão (100%), com confirmação
  cruzada de uma SEGUNDA fonte independente (Câmara dos Deputados) — primeira feature do projeto
  com dupla verificação de fonte primária no mesmo `/define`
- 1/1 dispositivo que rege o Anexo identificado (art. 371, §§1º-2º) — não constava no brainstorm

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto do Anexo XVI e do art. 371 obtidos via `legis.senado.leg.br` é o texto vigente, sem alterações posteriores | A tabela/citação usada no `/design`/`/build` estaria errada | [x] Validado nesta sessão — conferido contra uma SEGUNDA fonte independente (Câmara dos Deputados), 49/49 valores idênticos, e contra a lista de alterações da LC 227/2026 (nenhuma toca o art. 371/Anexo XVI) |
| A-002 | A "alíquota de referência da respectiva esfera federativa" (art. 371, §1º) nunca será calculável por este projeto, mesmo no futuro | Se um dia existir uma fonte pública e citável dessa alíquota (ex. publicada pelo CGIBS), o Anexo XVI passaria a poder produzir um número absoluto — feature futura, não uma correção desta | [ ] Não totalmente validado — o art. 370 (mecanismo de cálculo) foi lido, mas a Resolução CGIBS 6/2026 (já ingerida, 617 artigos) não foi consultada a fundo para confirmar se ela publica esse valor periodicamente. Registrado como COULD, não bloqueia esta feature |
| A-003 | Um bloco informativo no NÍVEL DA REQUISIÇÃO (indexado só por `ano_operacao`) é a granularidade certa, não por item | Se algum caso de uso exigir o piso por Estado/Município específico do item, a granularidade precisaria mudar — mas a "alíquota de referência" em si já não varia por item, só por esfera federativa (Estado vs. Município), e nem isso está calculável (ver A-002) | [x] Validado nesta sessão — o art. 371 não faz nenhuma referência a produto, serviço, NCM ou NBS |

**Note:** Validar A-002 (se a Resolução CGIBS 6/2026 publica a alíquota de referência) é
recomendado como investigação de baixo custo no `/design`, mas não bloqueia o avanço — mesmo que a
resposta seja "sim, publica", isso abriria uma feature FUTURA (calcular a alíquota final), não
mudaria o escopo desta.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, com o dispositivo exato (art. 371) e o dado quantificado (49 anos) — o brainstorm não tinha nem o artigo nem a tabela completa |
| Users | 3 | Dois usuários com pain points específicos e distintos (compliance de operação única vs. análise de cenário multi-ano) |
| Goals | 3 | MoSCoW explícito; o achado mais importante (a alíquota de referência é estruturalmente incalculável, não só "bloqueada por lei pendente") é MUST, não escondido |
| Success | 3 | Critérios testáveis e numéricos (49/49 anos, janela [2029,2077] exata) |
| Scope | 2 | Out of scope explícito e bem fundamentado, mas a forma exata do schema (Python puro vs. tabela SQL) fica deliberadamente aberta para o `/design` — correto por não presumir a resposta, mesma razão de nota reduzida das features anteriores desta leva |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** o brainstorm já tinha identificado
corretamente que esta é a feature de schema mais simples da leva. A verificação desta sessão não
encontrou nenhum fator de esforço oculto — ao contrário das 5 features anteriores (cada uma
encontrou pelo menos um achado que aumentava o escopo real vs. o estimado), aqui a única correção
foi de PRECISÃO (o dispositivo exato, a tabela completa, a natureza estrutural do bloqueio da
alíquota de referência), não de ESCOPO. É a primeira feature da leva onde a verificação de fonte
primária confirma a simplicidade em vez de revelar complexidade escondida.

---

## Open Questions

Nenhum item abaixo bloqueia o avanço para `/design` — são decisões de implementação, não lacunas
de entendimento:

1. **Python puro (`motor_calculo/`) vs. tabela SQL**: o `/design` decide onde a tabela de 49 linhas
   vive. Dado que é lei promulgada e imutável (sem cláusula de revisão periódica), Python puro
   (mesmo padrão de `regime_atual.py`) parece mais barato e igualmente auditável que uma migração —
   mas a decisão final e o porquê ficam para o `/design`.
2. **Nome exato do campo/bloco na resposta** (`piso_aliquota_ibs`, `limite_aliquota_propria`, ou
   outro) — decisão do `/design`, sem impacto na substância desta feature.
3. **Se a Resolução CGIBS 6/2026 publica a alíquota de referência** (Assunção A-002) — investigação
   de baixo custo recomendada no `/design`, não bloqueante.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-31 | define-agent | Versão inicial, extraída de `BRAINSTORM_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md`; verificação de fonte primária realizada nesta sessão com DUPLA fonte independente (Senado + Câmara dos Deputados, 49/49 valores idênticos) — tabela completa 2029-2077 (o brainstorm só tinha 2029-2033), dispositivo que rege o Anexo identificado pela primeira vez (art. 371, §§1º-2º), confirmado que a LC 227/2026 não alterou nem o artigo nem o Anexo, e achado que refina o entendimento do brainstorm: a "alíquota de referência" que o percentual multiplica é uma grandeza CALCULADA de execução fiscal real (art. 370), não um valor de lei pendente — bloqueio estrutural permanente, não temporário como o achado 12 original. Decisão de produto confirmada: bloco informativo em `/v1/tax/simulate`, nível de requisição (por `ano_operacao`), nunca calculando alíquota absoluta. |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ANEXO_XVI_PISO_ALIQUOTA_PROPRIA.md`
