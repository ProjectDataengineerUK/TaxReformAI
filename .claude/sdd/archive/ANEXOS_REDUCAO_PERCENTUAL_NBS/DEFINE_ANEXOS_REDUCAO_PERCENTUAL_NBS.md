# DEFINE: Anexos II, III, X e XI — Redução de 60% de CBS/IBS por NBS

> Estender `/v1/tax/simulate` para os 4 Anexos de 60% da LCP 214/2025 cuja chave de
> correspondência é predominantemente NBS (Nomenclatura Brasileira de Serviços) —
> introduzindo o primeiro vocabulário de correspondência por SERVIÇO de todo o projeto — e
> tratar explicitamente três achados críticos desta sessão que mudam a leitura do brainstorm:
> (1) a estrutura do código NBS tem 4 níveis hierárquicos, não 3 nem "NCM com pontuação
> diferente"; (2) diferente de Educação/Saúde, os Anexos X e XI carregam condições legais
> adicionais — nacionalidade de conteúdo (X) e tipo de comprador/vendedor (XI) — que impedem
> tratar "60%" como incondicional; (3) várias contagens do brainstorm estavam distantes da
> realidade (Anexo XI: ~33 → 46 itens, dos quais só 5 são efetivamente resolvíveis nesta
> feature).
>
> **Posição na sequência:** 14 de 17 (`.claude/sdd/features/ROADMAP_SEQUENCIA_AUDITORIA_2026-07.md`,
> "Segunda leva"). Roda depois da posição 13 (`ANEXOS_REDUCAO_PERCENTUAL_NCM`, shipada
> 2026-07-30), cujo mecanismo de redução percentual (`aplicar_reducao_percentual`) e cujo
> padrão de campo declaratório (`comprador_tipo`) esta feature reaproveita como precedente,
> mas para um vocabulário de chave inteiramente novo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | ANEXOS_REDUCAO_PERCENTUAL_NBS |
| **Date** | 2026-07-30 |
| **Author** | define-agent |
| **Status** | ✅ Shipado 2026-07-31 (ver `SHIPPED_2026-07-31.md`) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Quatro Anexos da LCP 214/2025 (II, III, X, XI — 142 itens verificados nesta sessão, não os
~113 estimados pelo brainstorm) reduzem CBS/IBS a 60% para serviços de educação, saúde,
produções artísticas/culturais/audiovisuais e bens/serviços de soberania e segurança
cibernética — mas o projeto não tem hoje nenhum conceito de correspondência por serviço
(NBS): `ItemSimulacao` só identifica mercadorias por NCM. Pior, a verificação desta sessão
contra o texto vigente encontrou que **apenas 2 dos 4 Anexos (II e III) são efetivamente "60%
por código", sem condição adicional** — os outros 2 carregam condições que um `/design`
ingênuo poderia ignorar silenciosamente: o Anexo X (art. 139, §§1º-3º) exige conteúdo
majoritariamente brasileiro para boa parte das produções listadas, e o Anexo XI (art. 142)
não tem NENHUM "60% incondicional" — a redução só existe quando o comprador é órgão público
ou (para um subconjunto de serviços) o vendedor é sociedade com sócio brasileiro
qualificado. Sem tratar essas duas condições explicitamente, o simulador aplicaria 60% a
produções estrangeiras que a lei não beneficia (Anexo X) ou, pior, aplicaria 60% a bens e
serviços de segurança nacional que a lei só reduz para um comprador ou vendedor específico
(Anexo XI) — o mesmo tipo de erro que a feature anterior já identificou e resolveu para os
Anexos IV/V/VI, agora numa forma estruturalmente diferente (nacionalidade de conteúdo;
condição de vendedor, não só de comprador).

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Cliente ERP consumindo `/v1/tax/simulate` | Sistema externo consumidor (integração B2B) | Simula serviços de educação, saúde, produções culturais e bens/serviços de segurança com a alíquota geral da fase, quando a lei já garante 60% de redução para esses serviços — ou, no caso de produções culturais estrangeiras ou fornecimentos a compradores/vendedores não qualificados, corre o risco oposto: um `/design` apressado poderia conceder 60% onde a lei não concede nada |
| Controller/CFO usando o simulador | Consumidor indireto do produto (via ERP ou frontend) | Não consegue demonstrar o benefício fiscal real de escolas, clínicas, produtoras culturais e empresas de segurança da informação numa simulação que se propõe auditável; para produções culturais e para bens/serviços de segurança nacional, precisa entender que o benefício depende de fatos que o payload de hoje não captura (nacionalidade do conteúdo; natureza do comprador/vendedor) |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conteúdo completo dos 4 Anexos (II: 9 itens, III: 30, X: 57, XI: 46 — total **142**, verificado nesta sessão, corrigindo as estimativas aproximadas do brainstorm, que eram ~7/~22/~51/~33) verificado contra fonte primária — ver "Os 4 Anexos, verificados nesta sessão" |
| **MUST** | **Estrutura do código NBS investigada e documentada nesta sessão** (achado crítico 1): 4 níveis hierárquicos — capítulo/seção (1 dígito, sempre "1" em todos os 90 códigos NBS resolvíveis observados), posição (4 dígitos), subposição (2 dígitos) e item (2 dígitos), formato `C.PPPP.SS.II` (9 dígitos completos, ex. `1.2301.11.00`), com prefixos aceitos em QUALQUER fronteira, inclusive truncamento parcial de 1 dígito dentro da subposição (ex. `1.2201.1` = subposição 10-19). O mecanismo de correspondência por prefixo já generalizado em `api/ncm.py`/`api/reducao.py` (comparação de string após remover pontuação) é estruturalmente reaproveitável, mas exige uma função de canonização NOVA (`digitos_nbs` ou equivalente) com regras de validação próprias (9 dígitos completos, não 8) |
| **MUST** | Nova função `api/nbs.py` (irmã de `api/ncm.py`), decisão do `/design` se o lookup de NBS entra na mesma consulta/tabela do NCM (com discriminador de vocabulário) ou em tabela(s)/consulta(s) totalmente separada(s) — **nunca comingladas sem discriminador**, porque um prefixo NBS truncado (ex. `12203`, 5 dígitos) e um prefixo NCM de mesmo comprimento não são distinguíveis pelo dígito puro (ver "Achado crítico 4: por que NBS e NCM não podem compartilhar coluna sem discriminador") |
| **MUST** | `ItemSimulacao` ganha um campo novo (`nbs` ou equivalente, decisão de nome do `/design`) — mudança de contrato de API confirmada pelo brainstorm, não uma extensão do campo `ncm` existente |
| **MUST** | **Achado crítico 2 desta sessão: Anexos II e III não têm nenhuma condição além do próprio código; Anexo X tem condição de NACIONALIDADE DE CONTEÚDO (art. 139, §§1º-3º); Anexo XI não tem NENHUM "60% incondicional"** — toda a redução do Anexo XI depende de o comprador ser órgão público (art. 142, I) ou, só para um subconjunto de serviços de segurança da informação/cibernética, de o vendedor ser sociedade com sócio brasileiro ≥20% do capital (art. 142, II). Ver "Achado crítico 2" — o `/design` DEVE decidir explicitamente como tratar essas duas lacunas de payload, nunca assumir "60% sempre" nem "alíquota geral sempre" silenciosamente |
| **MUST** | Itens de chave NCM minoritária nos Anexos X (itens 42-45, 4 itens: fotografias/quadros/gravuras/esculturas artísticas) e XI (itens 2.1-2.30, 30 itens: viaturas, blindados, armamento, aeronaves militares etc.) documentados como não resolvidos nesta feature — nunca tratados como "NBS não encontrado" silencioso |
| **MUST** | Itens sem NENHUM código citável documentados como limitação distinta, nunca confundidos com "NBS não reconhecido": Anexo II item 9 (educação especial, célula vazia), Anexo X itens 49-54 (6 itens de "obras teatrais", célula vazia) e Anexo XI itens 1.6/1.7/1.10/1.11/1.12 (5 itens, célula literalmente "pendente de classificação" — descrição válida, mas a nomenclatura ainda não atribuiu um código) |
| **MUST** | Itens vetados do Anexo XI (1.4, 1.5, 1.8 e 1.9 — 4 itens) tratados como se NUNCA tivessem existido no Anexo, nunca como "excluído expressamente" (que é uma categoria legal diferente, já usada pelos Anexos NCM) — o veto (Mensagem de Veto Parcial nº 88/2025) é da sanção ORIGINAL da LCP 214/2025, não da LC 227/2026 |
| **MUST** | Confirmado nesta sessão, contra fonte primária, que a LC 227/2026 **não alterou nenhum dos Anexos II, III, X ou XI em si**, mas alterou o **art. 142, inciso II** (que rege o Anexo XI) — mudança de redação que remove a citação equivocada de "NCM/SH" do inciso (que trata só de serviços) e substitui "operações e prestações de" por "fornecimento"; a condição substantiva (sócio brasileiro ≥20%) não muda. Nenhuma alteração ou veto adicional aos arts. 129 (Anexo II) e 130 (Anexo III); o art. 139 (Anexo X) também não foi tocado |
| **MUST** | **Achado crítico 3: itens DIFERENTES do MESMO Anexo compartilhando o MESMO código NBS** — 10 itens do Anexo III (18, 19, 20, 21, 22, 23, 24, 25, 26, 28) citam literalmente o mesmo código `1.2301.99.00`; 2 itens do Anexo II (7 e 8) citam o mesmo código `1.2205.13.00`. Isso é estruturalmente diferente da precedência entre Anexos distintos (já resolvida na feature anterior): aqui não há "vencedor" por especificidade ou percentual — são o MESMO Anexo, o MESMO percentual, itens apenas descritivamente diferentes. O mecanismo de desempate já existente (`itens_correspondentes` lista todos, um item "vencedor" é escolhido para a citação principal) parece compatível por construção, mas nunca foi exercitado neste cenário e precisa de um Acceptance Test dedicado |
| **MUST** | `motor_calculo/` não ganha nenhuma dependência de infraestrutura |
| **SHOULD** | Investigação da fonte oficial da estrutura do NBS (Receita Federal/antigo `nbs.economia.gov.br`) documentada como **inacessível deste ambiente** (`NXDOMAIN`, mesma classe de restrição já registrada para `planalto.gov.br`) — a estrutura desta sessão foi inferida empiricamente dos 90 códigos observados nos 4 Anexos, não de uma especificação oficial; recomendado ao `/design` tratar isso como uma assunção a validar, não um fato fechado |
| **SHOULD** | Overlap entre os códigos NBS destes 4 Anexos e os 10 Anexos NCM já shipados — estruturalmente impossível de colidir OPERACIONALMENTE se `nbs` viver num campo/coluna separado do `ncm` (decisão MUST acima), mas o `/design` deve confirmar essa separação explicitamente, não assumi-la |
| **COULD** | Confirmar se os itens "pendente de classificação" do Anexo XI (5 itens) já receberam código NBS numa revisão posterior da nomenclatura, fora do escopo desta sessão (que verificou só o texto legal, não a nomenclatura em si, inacessível) |

**Priority Guide:**
- **MUST** = a feature falha seu propósito sem isto
- **SHOULD** = importante, mas existe contorno se o prazo apertar
- **COULD** = bônus, primeiro a cortar se necessário

---

## Verificação de Fonte Primária (obrigatória antes deste /define)

Mesma fonte já qualificada nas três features anteriores desta leva: o portal oficial do
Senado Federal (`legis.senado.leg.br`), espelho da "Publicação Original" do DOU.
`planalto.gov.br` continua inacessível deste ambiente. O acesso só respondeu 200 com um header
de `User-Agent` de navegador — sem ele, 403 (aviso herdado, confirmado novamente nesta sessão).

**O que foi verificado, com URL e conteúdo real, nesta sessão (2026-07-30):**

1. **Texto integral dos 4 Anexos**, cada um sua própria "Publicação de Anexo" (DOU Edição
   Extra nº 11-B de 16/01/2025):
   - Anexo II: `https://legis.senado.leg.br/norma/40180341/publicacao/40180894` (p. 48, col.
     1) — HTTP 200
   - Anexo III: `https://legis.senado.leg.br/norma/40180341/publicacao/40180900` (p. 48, col.
     1) — HTTP 200
   - Anexo X: `https://legis.senado.leg.br/norma/40180341/publicacao/40180985` (p. 52, col. 1)
     — HTTP 200
   - Anexo XI: `https://legis.senado.leg.br/norma/40180341/publicacao/40180991` (p. 53, col.
     1) — HTTP 200
2. **Corpo da LCP 214/2025** (arts. 1º a 544), mesma URL já usada nas três features
   anteriores: `https://legis.senado.leg.br/norma/40180341/publicacao/40181429` — HTTP 200.
   Lidos os arts. 129-142 (Seções II a XIV do Capítulo III, "Da Redução de 60%") na íntegra —
   inclusive arts. 137, 140 e 141, que regem reduções de 60% SEM Anexo (fora de escopo, ver
   "Out of Scope").
3. **Página de detalhe da norma** (`https://legis.senado.leg.br/norma/40180341`) — lista
   completa de "Normas posteriores": confirmado que (a) a **Mensagem de Veto Parcial nº
   88/2025** (da sanção ORIGINAL da LCP 214/2025, não da LC 227/2026) vetou os itens 1.4, 1.5,
   1.8 e 1.9 do Anexo XI; (b) a **LC 227/2026** alterou, entre Anexos, só "Anexo 7", "Anexo
   14", "Anexo 20" e "Anexo 21" — nenhum dos Anexos II, III, X ou XI; (c) entre artigos no
   intervalo 125-149, a LC 227/2026 alterou só o art. 126 §6 (Anexo I, fora de escopo), o
   **art. 142, caput, inciso II** (Anexo XI), o art. 146 (já coberto pela feature anterior) e
   o art. 149 (zero-rate de automóveis, sem relação com estes 4 Anexos).
4. **Texto publicado da LC 227/2026**
   (`https://legis.senado.leg.br/norma/42042119/publicacao/42256084`) — lido para confirmar o
   CONTEÚDO exato da alteração ao art. 142, II (ver "Achado crítico 2").
5. **Tentativa de acesso à fonte oficial da estrutura do NBS**
   (`nbs.economia.gov.br`, referenciado por um hyperlink dentro da própria "Publicação de
   Anexo" do Anexo X, item 21: `http://nbs.economia.gov.br/pt/concepts/servicos-de-agencias-
   de-noticias-para-midia-audiovisual/glance.html`) — **domínio não resolve (`NXDOMAIN`)**
   deste ambiente. Tentativas adicionais de domínios sucessores prováveis
   (`nbs.mdic.gov.br`, `www.gov.br/mdic/...`, `www.gov.br/produtividade-e-comercio-exterior/
   ...`, `siscoserv.mdic.gov.br`, `portalunico.siscomex.gov.br/nbs`) e do Wayback Machine
   (`web.archive.org`) também falharam (404/NXDOMAIN/sem snapshot no caminho tentado). A
   estrutura documentada nesta sessão (ver "Achado crítico 1") é **inferida empiricamente**
   dos 90 códigos NBS observados nos 4 Anexos, não confirmada contra uma especificação
   oficial — mesma classe de limitação já aceita pelo projeto para `planalto.gov.br`.

Consultados em 2026-07-30.

---

## Os 4 Anexos, verificados nesta sessão

**Contagens exatas (substituindo as estimativas aproximadas do brainstorm):**

| Anexo | Assunto | Artigo que rege | Itens (brainstorm → real) | NBS resolvível nesta feature | Fora de escopo (NCM minoritário) | Sem código citável | Vetado |
|-------|---------|-------------------|-------------------------------|------------------------------|-------------------------------------|-------------------------|--------|
| II | Educação | art. 129 | ~7 → **9** | 8 | 0 | 1 | 0 |
| III | Saúde | art. 130 | ~22 → **30** | 30 | 0 | 0 | 0 |
| X | Produções artísticas/culturais/eventos/jornalísticas/audiovisuais | art. 139 | ~51 → **57** | 47 | 4 | 6 | 0 |
| XI | Soberania/segurança nacional/informação/cibernética | art. 142 | ~33 → **46** | 5 | 30 | 5 | 4 |
| **Total** | | | **~113 → 142** | **90** | **34** | **12** | **4** |

Nenhum código foi aceito de memória — os 4 Anexos foram lidos integralmente nesta sessão, e a
página de detalhe da norma foi lida para confirmar (não presumir) o histórico de veto/alteração.

### Anexo II — Educação (9 itens: 8 NBS + 1 sem código)

| Item | Descrição (resumida) | Código NBS | Achado |
|------|------------------------|-----------------|--------|
| 1 | Ensino Infantil, inclusive creche e pré-escola | `1.2201.1` | PREFIXO parcial (1 dígito da subposição — cobre 10-19) |
| 2 | Ensino Fundamental | `1.2201.20.00` | EXATO |
| 3 | Ensino Médio | `1.2201.30.00` | EXATO |
| 4 | Ensino Técnico de Nível Médio | `1.2202.00.00` | EXATO |
| 5 | Ensino para jovens e adultos (EJA) | `1.2203` | PREFIXO (posição, 4 dígitos) |
| 6 | Ensino Superior (graduação, pós, extensão, sequenciais) | `1.2204` | PREFIXO (posição, 4 dígitos) |
| 7 | Ensino de sistemas linguísticos visomotores/escrita tátil | `1.2205.13.00` | EXATO — **mesmo código do item 8** |
| 8 | Ensino de línguas nativas de povos originários | `1.2205.13.00` | EXATO — **mesmo código do item 7** |
| 9 | Educação especial (PCD, TGD, altas habilidades) | *(célula vazia na fonte)* | **SEM CÓDIGO** — nem NBS nem NCM, mesma classe do item 34 do Anexo IX (feature anterior) |

**Condição legal (art. 129, parágrafo único)**: a redução (I) só se aplica ao valor da
contraprestação dos serviços listados, e (II) não se estende a outras operações eventuais no
âmbito das escolas/instituições — restrições de **base de cálculo**, não de comprador/
vendedor/nacionalidade; não exigem campo novo no payload (o item já representa um valor
unitário do serviço qualificado).

**Fonte:** `LCP 214/2025, art. 129, Anexo II`. Não alterado pela LC 227/2026.

### Anexo III — Saúde (30 itens, todos NBS)

| Item | Descrição (resumida) | Código NBS |
|------|------------------------|-----------------|
| 1-17 | Cirúrgicos, ginecológicos/obstétricos, psiquiátricos, UTI, urgência, hospitalares gerais, clínica médica, médicos especializados, odontológicos, enfermagem, fisioterapia, laboratoriais, diagnóstico por imagem, bancos de material biológico, ambulância, parto/pós-parto, psicologia | `1.2301.11.00` a `1.2301.98.00` (17 códigos distintos) |
| 18, 19, 20, 21, 22, 23, 24, 25, 26, 28 | Vigilância sanitária, epidemiologia, vacinação, fonoaudiologia, nutrição, optometria, instrumentação cirúrgica, biomedicina, farmacêuticos, domiciliares de apoio | **`1.2301.99.00` — MESMO código nos 10 itens** |
| 27 | Cuidado/assistência a idosos e PCD em unidades de acolhimento | `1.2302` |
| 29 | Esterilização | `1.2301.99.0` — **1 dígito a menos que o padrão** (anomalia literal da fonte, ver nota) |
| 30 | Funerários, cremação, embalsamamento | `1.2603.00.00` |

**Nota sobre o item 29**: o texto oficial publica `1.2301.99.0` (8 dígitos após o "1.", não 9)
— um dígito a menos do que todo item de nível "item" (2 dígitos finais) neste e nos outros 3
Anexos. Transcrito literalmente como publicado; é uma anomalia da fonte, não um erro de
transcrição desta sessão (confirmado no HTML bruto). O `/design`/`/build` decide como
armazenar — como publicado (literal) ou com nota de correção documentada — mas nunca
silenciosamente "corrigido" sem registro.

**Condição legal (art. 130, parágrafo único)**: exclui da base de cálculo valores glosados
pela auditoria médica de planos de saúde e não pagos — ajuste de base de cálculo que este
motor não modela (mesma classe de limitação estrutural já aceita para ICMS/ISS por item
específico); não é uma condição de comprador/vendedor/nacionalidade.

**Fonte:** `LCP 214/2025, art. 130, Anexo III`. Não alterado pela LC 227/2026. Nenhuma
cláusula "revisão a cada 120 dias" (diferente de IV/V/VI/IX) — confirmado por leitura direta
do art. 130, que não tem parágrafo equivalente.

### Anexo X — Produções artísticas, culturais, eventos, jornalísticas e audiovisuais (57 itens: 47 NBS + 4 NCM + 6 sem código)

Cabeçalho oficial "NBS/NCM" confirmado — mas a imensa maioria (47/57 = 82%) é NBS.

- **Itens 1-41, 46-48, 55-57 (47 itens): chave NBS**, em escopo desta feature. Cobre
  licenciamento/cessão de direitos autorais e conexos (obras literárias, cinematográficas,
  jornalísticas, audiovisuais, musicais), agências de notícias, gravação/produção/edição/
  efeitos visuais/animação/legendas de obras audiovisuais, museus, atuação artística,
  organização de eventos culturais, sonorização/iluminação/montagem de palcos.
- **Itens 42-45 (4 itens): chave NCM** — fotografias artísticas originais (`4911.91.00`),
  quadros/pinturas/desenhos artísticos originais (`9701.91.00`), gravuras/estampas/litografias
  (`9702.90.00`), esculturas (`9703.90.00`) — **fora de escopo desta feature**, documentados
  como não resolvidos, mesmo tratamento do Anexo IX (feature anterior).
- **Itens 49-54 (6 itens): SEM CÓDIGO** — licenciamento/cessão de direitos de autor e conexos
  de obras TEATRAIS (autor, produtores, intérpretes/executantes, temporária e — pelo padrão
  dos itens irmãos — presumivelmente também definitiva, mas o texto só lista os 6 acima),
  célula vazia na fonte (confirmado no HTML bruto) — mesma classe do item 9 do Anexo II e do
  item 34 do Anexo IX.

**Condição legal — achado crítico (art. 139, §§1º-3º)**: o caput do art. 139 exige que cada
item do Anexo X se relacione a UMA das 8 categorias listadas (incisos I-VIII: espetáculos
teatrais/circenses/dança; shows musicais; desfiles carnavalescos/folclóricos; eventos
acadêmicos/científicos; feiras de negócios; exposições/feiras/galerias/mostras culturais;
programas de auditório/jornalísticos/filmes/documentários/séries/novelas/entrevistas/clipes
musicais; obras de arte). Adicionalmente:

- **§1º**: os incisos I, II, III e VII (teatro/circo/dança, shows musicais, desfiles, e
  programas de TV/rádio/filmes/documentários/séries/novelas/entrevistas/clipes) **só se
  aplicam a produções realizadas no País com conteúdo majoritariamente brasileiro** (obras/
  autores/intérpretes brasileiros).
- **§2º**: obras cinematográficas/videofonográficas do inciso VII exigem adicionalmente
  atender aos requisitos de "obra audiovisual nacional" da legislação específica.
- **§3º**: obras de arte do inciso VIII (itens 42-45, os de chave NCM) só se aplicam a
  produzidas por artistas brasileiros.
- Os incisos IV, V e VI (eventos acadêmicos, feiras de negócios, exposições/galerias/mostras)
  **não têm exigência de nacionalidade**.

Isso significa que **o Anexo X não é "60% por código, sem mais nada"**: para boa parte dos 47
itens NBS em escopo, a redução depende de um fato sobre a PRODUÇÃO (nacionalidade de
conteúdo/autoria) que o payload de `/v1/tax/simulate` não tem hoje nenhum campo para
expressar. Mapear cada um dos 47 itens ao inciso exato (I-VIII) do art. 139 que o rege é
trabalho de granularidade de `/design`/`/build`; o que este `/define` fixa como MUST é que a
condição existe, afeta a maioria dos itens do Anexo, e não pode ser tratada como se não
existisse.

**Fonte:** `LCP 214/2025, art. 139, Anexo X`. Não alterado pela LC 227/2026.

### Anexo XI — Soberania, segurança nacional, segurança da informação e cibernética (46 itens: 5 NBS + 30 NCM + 5 sem código + 4 vetados + 2 cabeçalhos)

Cabeçalho oficial "NBS / NCM/SH" confirmado — estrutura em 2 blocos com cabeçalho próprio (sem
código): item **1** ("SERVIÇOS...") com sub-itens 1.1-1.14, e item **2** ("BENS...") com
sub-itens 2.1-2.30 — mesmo padrão de cabeçalho-sem-código do Anexo V (feature anterior), mas
aqui os DOIS blocos são grandes (14 e 30 sub-itens), não só 3 cabeçalhos pequenos.

**Bloco 1 — Serviços (14 sub-itens, chave NBS quando presente):**

| Sub-item | Descrição (resumida) | Código | Situação |
|----------|------------------------|-------------|----------|
| 1.1 | Segurança em Tecnologia da Informação (TI) | `1.1501.20.00` | Resolvível |
| 1.2 | Projeto/desenvolvimento de aplicativos e programas de TI | `1.1502.90.00` | Resolvível |
| 1.3 | Serviços de TI não classificados em subposições anteriores | `1.1510.00.00` | Resolvível |
| 1.4 | *(VETADO)* | `1.1802.90.00` | **Vetado na sanção original — nunca em vigor** |
| 1.5 | *(VETADO)* | `1.1802.30.00` | **Vetado na sanção original — nunca em vigor** |
| 1.6 | Localização de dispositivo perdido/furtado (proteção de dados pessoais) | `pendente de classificação` | **Sem código atribuído** — descrição válida, não vetado |
| 1.7 | Bloqueio de dispositivo perdido/furtado | `pendente de classificação` | **Sem código atribuído** |
| 1.8 | *(VETADO)* | `pendente de classificação` | **Vetado na sanção original** |
| 1.9 | *(VETADO)* | `pendente de classificação` | **Vetado na sanção original** |
| 1.10 | Monitoramento de uso de dados em redes tipo onion | `pendente de classificação` | **Sem código atribuído** |
| 1.11 | Conexão protegida e criptografada para dispositivos | `pendente de classificação` | **Sem código atribuído** |
| 1.12 | Identificação/alerta de arquivos maliciosos | `pendente de classificação` | **Sem código atribuído** |
| 1.13 | Manutenção e reparação de veículos militares | `1.2001.35.00` | Resolvível |
| 1.14 | Manutenção e reparação de equipamentos militares | `1.2001.83.00` | Resolvível |

Resultado do Bloco 1: **5 resolvíveis nesta feature** (1.1, 1.2, 1.3, 1.13, 1.14), **4 vetados**
(1.4, 1.5, 1.8, 1.9) e **5 sem código atribuído** (1.6, 1.7, 1.10, 1.11, 1.12) — uma situação
NORMATIVA VÁLIDA, distinta de "célula vazia" (Anexo II/9, Anexo X/49-54): a lei descreve o
serviço, mas a nomenclatura (NBS) ainda não lhe atribuiu um código formal, então não há string
para casar contra nenhuma tabela de prefixo. Documentado como limitação distinta, nunca
confundido com "NBS não reconhecido" (erro de payload) nem com "excluído expressamente" (o
item existe e é elegível, só não é operacionalizável).

**Bloco 2 — Bens (30 sub-itens, chave NCM — 2.1 a 2.30, todos com código, nenhum vetado nem
pendente)**: viaturas/blindados/carros de combate militares, simuladores, tratores militares,
radares, foguetes, explosivos, munição, aeronaves/VANTs, veículos espaciais, paraquedas,
embarcações militares, e dispositivos de segurança da informação/cibernética (IPS/IDS,
autenticação, criptografia, firewalls, switches/roteadores seguros, armazenamento seguro).
**Fora de escopo desta feature** (chave NCM minoritária) — documentado como não resolvido,
mesmo tratamento do Anexo IX (feature anterior) e dos itens 42-45 do Anexo X.

**Condição legal — achado crítico (art. 142)**: diferente de todos os Anexos já vistos no
projeto (incluindo IV/V/VI, onde 60% é o PADRÃO e zero é a exceção condicionada), o **Anexo XI
não tem NENHUM "60% incondicional"**. O caput do art. 142 fixa 60% APENAS em duas hipóteses:

- **Inciso I**: fornecimento à administração pública direta, autarquias e fundações públicas
  — aplica-se a QUALQUER item do Anexo XI (bens e serviços). Mesma definição de comprador já
  usada para `CompradorTipo.ORGAO_PUBLICO` nos arts. 144-II/145-II/146-§1º-I (redação
  equivalente: "administração pública direta, autarquia[s] [e/ou] fundação[ões] pública[s]").
- **Inciso II**: fornecimento de serviços de segurança da informação e segurança cibernética
  por sociedade com sócio brasileiro ≥20% do capital social — aplica-se SÓ a serviços dessa
  natureza específica (plausivelmente item 1.1 e talvez 1.3; itens 1.2, 1.13 e 1.14 não
  parecem ser "segurança da informação/cibernética" propriamente ditos — decisão de
  classificação item a item cabe ao `/design`). **Não existe hoje nenhum campo no payload que
  descreva a composição societária do vendedor** — dimensão nunca modelada pelo projeto (todas
  as condições anteriores, `bem_importado`, `regime_apuracao`, `comprador_tipo`, são sobre a
  operação ou o comprador, nunca sobre o vendedor).

**Achado textual da LC 227/2026 (inciso II)**: redação ORIGINAL (LCP 214/2025) — "II –
**operações e prestações de** serviços de segurança da informação e segurança cibernética
desenvolvidos por sociedade que tenha sócio brasileiro com o mínimo de 20% (vinte por cento)
do seu capital social, relacionados no Anexo XI [...], com a especificação das respectivas
classificações da **NBS e da NCM/SH**." Nova redação (LC 227/2026, em vigor): "II –
**fornecimento de** serviços de segurança da informação e segurança cibernética desenvolvidos
por sociedade que tenha sócio brasileiro com o mínimo de 20% (vinte por cento) do seu capital
social, relacionados no Anexo XI [...], com a especificação das respectivas classificações da
**NBS**." — a mudança substantiva é a REMOÇÃO da referência a "NCM/SH": o legislador corrigiu
um erro do texto original (o inciso II sempre foi sobre SERVIÇOS, nunca deveria citar NCM/SH).
A condição de 20% de capital brasileiro não muda.

**Fonte:** `LCP 214/2025, art. 142, Anexo XI` (bens e serviços); veto original dos itens 1.4,
1.5, 1.8, 1.9 — Mensagem de Veto Parcial nº 88/2025; alteração do inciso II do art. 142 — LC
227/2026, texto publicado em `legis.senado.leg.br/norma/42042119/publicacao/42256084`.

---

## Achado crítico 1: estrutura do código NBS (empírica, fonte oficial inacessível)

Os 90 códigos NBS resolvíveis observados nos 4 Anexos seguem, sem exceção, o formato:

```
C.PPPP.SS.II
```

- **C** — 1 dígito, classificador de topo (capítulo/seção). **Em 100% dos 90 códigos
  observados, C = "1"** — não há evidência, dentro desta feature, de nenhum outro valor. Isso
  pode significar que a "Seção 1" da NBS cobre genericamente todos os serviços (hipótese mais
  provável, dado que os 4 Anexos cobrem domínios tão diferentes quanto educação, saúde, cultura
  e segurança cibernética, todos com C="1"), ou pode ser uma coincidência restrita a estes 4
  Anexos — **não confirmável sem a fonte oficial** (inacessível, ver acima). Tratado como
  assunção a validar pelo `/design`, não como fato fechado.
- **PPPP** — 4 dígitos, "posição".
- **SS** — 2 dígitos, "subposição". Aceita truncamento parcial de 1 dígito (ex. `1.2201.1`,
  `1.1103.4`, `1.1806.6`) — o dígito presente é o primeiro da dezena (`1` = subposições 10-19).
- **II** — 2 dígitos, "item".

Código completo = 9 dígitos (sem os pontos), contra os 8 dígitos do NCM — confirma o achado
estrutural do brainstorm ("prefixo adicional antes do primeiro ponto") e o formaliza. Prefixos
podem ser truncados em QUALQUER fronteira observada: só posição (5 dígitos com o "1", ex.
`1.2203`), posição + 1 dígito de subposição (6 dígitos, ex. `1.2201.1`), posição + subposição
completa sem item (7 dígitos, ex. `1.1103.36`), ou código completo (9 dígitos). Isso é
estruturalmente equivalente ao mecanismo de prefixo por comprimento variável já generalizado em
`api/reducao.py`/`api/ncm.py` (`_COMPRIMENTOS_PREFIXO`), só que sobre uma string de 9 dígitos em
vez de 8 — o `/design` decide se estende a mesma tupla de comprimentos aceitos ou define uma
nova, específica para NBS.

**Duas anomalias literais da fonte** (não erro de transcrição desta sessão, confirmadas no
HTML bruto): o item 29 do Anexo III (`1.2301.99.0`, faltando 1 dígito) e a divisão do código do
item 21 do Anexo X entre duas células de tabela por causa de um hyperlink (`1.` + `1704.20.00`
— reconstituído corretamente para `1.1704.20.00`, confirmado contra o HTML bruto, que também
revelou o link `nbs.economia.gov.br` usado na tentativa de achar a fonte oficial).

---

## Achado crítico 2: condições legais além do código (Anexos X e XI)

| Anexo | Condição adicional | Dimensão | Campo de payload equivalente hoje | Precedente no projeto |
|-------|----------------------|----------|--------------------------------------|--------------------------|
| II | Nenhuma (só base de cálculo, art. 129, parágrafo único) | — | — | — |
| III | Nenhuma (só base de cálculo, art. 130, parágrafo único — glosas médicas) | — | — | — |
| X | Nacionalidade do CONTEÚDO/autoria (art. 139, §§1º-3º) — afeta a maioria dos 47 itens NBS | Produção/obra | Nenhum | Nenhum — primeira condição de "nacionalidade de conteúdo" do projeto |
| XI | Tipo de COMPRADOR (art. 142, I — órgão público) OU tipo de VENDEDOR (art. 142, II — sócio brasileiro ≥20%, só para segurança da informação/cibernética) | Comprador **e** vendedor (dois eixos, não um) | `comprador_tipo` (`ORGAO_PUBLICO`) já cobre o eixo do comprador com a MESMA definição textual; nenhum campo cobre o eixo do vendedor | `comprador_tipo` (feature anterior) para o eixo comprador; eixo vendedor é inédito |

**Diferença estrutural do achado da feature anterior**: em IV/V/VI, 60% é o PADRÃO e a condição
de comprador cria uma exceção (zero). Aqui, para o Anexo XI, **não existe padrão nenhum** — a
alíquota geral da fase é o que se aplica por default, e 60% só nasce com uma das duas condições
provada. Isso inverte a direção do "silêncio seguro": aplicar 60% sem informação sobre o
comprador/vendedor SUPERESTIMARIA o benefício (o oposto do erro "seguro" aceito em outros
pontos do projeto); a única resposta compatível com "nunca estimar" é aplicar a alíquota geral
por padrão e declarar, no próprio item, que 60% seria aplicável se `comprador_tipo=ORGAO_
PUBLICO` (ou um campo de vendedor equivalente) tivesse sido informado — mesma disciplina do
`zero_por_comprador_disponivel` já usado para IV/V/VI, mas com os papéis de "padrão" e
"condicionado" trocados.

**Recomendação explícita para o `/design`** (decisão não tomada aqui, mas as duas lacunas não
podem ficar sem tratamento):

1. **Eixo comprador (Anexo XI, inciso I)**: reaproveitar `comprador_tipo=ORGAO_PUBLICO` já
   existente — mesma definição textual de "administração pública direta, autarquia(s),
   fundação(ões) pública(s)". `ENTIDADE_CEBAS_SUS` NÃO se aplica ao Anexo XI (nenhuma base
   legal) — o `/design` deve garantir que esse valor não dispare 60% para itens do Anexo XI.
2. **Eixo vendedor (Anexo XI, inciso II)**: campo novo (ex. `vendedor_capital_brasileiro_
   qualificado: bool | None`, nome exato a decidir), declaratório como os demais (a simulação
   não valida o capital social real), aplicável só ao subconjunto de itens de "segurança da
   informação/cibernética" do Bloco 1 — ou documentar como limitação conhecida, se o `/design`
   decidir não estender o payload nesta feature.
3. **Nacionalidade de conteúdo (Anexo X)**: campo novo (ex. `conteudo_nacional_majoritario: bool
   | None`) ou limitação documentada — aplicável aos itens do Anexo X que a análise de
   `/design`/`/build` mapear aos incisos I, II, III, VII e VIII do art. 139. O que NÃO é
   aceitável, para nenhum dos três casos, é o silêncio: nem a implementação nem a documentação
   podem tratar X ou XI como "60% incondicional" sem a ressalva.

---

## Achado crítico 3: itens diferentes do mesmo Anexo compartilhando o mesmo código NBS

Diferente da precedência ENTRE Anexos (já resolvida pela feature anterior com 6 componentes de
desempate), aqui o cenário é: **múltiplos itens do MESMO Anexo, MESMO percentual, código NBS
idêntico**:

- Anexo III: 10 itens (18, 19, 20, 21, 22, 23, 24, 25, 26, 28) compartilham `1.2301.99.00`.
- Anexo II: 2 itens (7, 8) compartilham `1.2205.13.00`.

O mecanismo de agrupamento já existente em `api/reducao.py::resolver_item` (`por_item` chaveado
por `(anexo, item, sub_item)`, com `itens_correspondentes` listando todos os itens casados e um
"vencedor" escolhido por especificidade) parece compatível por construção — a chave de
desempate já usada (`-item` como componente de desempate final, favorecendo o menor número de
item) resolveria este cenário elegendo o item de menor número como citação principal e listando
os demais em `itens_correspondentes`, sem exigir mudança de mecanismo. **Isso nunca foi
exercitado** (nas 10 Anexos NCM já shipados, nenhum código tem essa característica dentro do
MESMO Anexo) e precisa de um Acceptance Test dedicado (AT-003) para confirmar, não presumir,
que o comportamento é o desejado — o "vencedor" arbitrário entre 10 descrições de serviços
igualmente válidas é uma decisão de produto (qual descrição aparece como principal), não só
uma consequência técnica do desempate.

---

## Achado crítico 4: por que NBS e NCM não podem compartilhar coluna sem discriminador

Diferente da feature anterior — onde os 6 Anexos percentuais e os 4 Anexos zero competiam pelo
MESMO vocabulário (NCM) e por isso precisaram de uma tabela unificada com desempate de 6
componentes — aqui o vocabulário é estruturalmente diferente (9 dígitos com o "1" inicial vs. 8
dígitos do NCM puro). Ainda assim, um prefixo NBS truncado na fronteira "posição apenas" (ex.
`1.2203` → dígitos `12203`, 5 caracteres) tem o MESMO comprimento que um prefixo NCM válido de 5
dígitos (`_COMPRIMENTOS_PREFIXO` já aceita 5) — a string pura `"12203"` não diz, por si só, de
qual vocabulário ela veio. **Isso não é um problema OPERACIONAL enquanto `nbs` e `ncm` viverem
em campos/colunas separados** (decisão MUST já tomada pelo brainstorm) — mas se um `/design`
ingênuo decidisse reaproveitar a MESMA tabela/coluna de prefixo para os dois vocabulários "para
economizar uma tabela", uma consulta por `codigo.startswith(prefixo)` teria colisão real e
silenciosa. Este `/define` fixa como MUST que a separação de campo é também uma separação de
consulta/tabela, nunca apenas uma convenção de nomenclatura de coluna.

---

## Success Criteria

- [ ] Conteúdo dos 4 Anexos (142 itens) verificado contra fonte primária, com URLs e data de
      acesso registrados neste documento — concluído nesta sessão
- [ ] Estrutura do código NBS (4 níveis, 9 dígitos completos, truncamento parcial de 1 dígito
      dentro da subposição) documentada, com a limitação explícita de que a fonte oficial
      (`nbs.economia.gov.br`) está inacessível deste ambiente — concluído nesta sessão
- [ ] Confirmado contra fonte primária que a LC 227/2026 não alterou os Anexos II, III, X ou
      XI, mas alterou o art. 142, inciso II (Anexo XI) — concluído nesta sessão
- [ ] `api/nbs.py` implementado com canonização e correspondência por prefixo, análogo a
      `api/ncm.py`, sem comingle de coluna/consulta com NCM (Achado crítico 4)
- [ ] `ItemSimulacao` ganha campo novo para identificar serviço por NBS
- [ ] `/v1/tax/simulate` aplica 60% aos itens de serviço cujo NBS bate com um item resolvido de
      II, III, X ou XI, citando o Anexo e item exatos
- [ ] Decisão explícita e documentada (no `/design`) sobre o tratamento das condições de
      nacionalidade de conteúdo (Anexo X) e de comprador/vendedor (Anexo XI) — nunca "60%
      incondicional" tratado como fato assumido para nenhum dos dois Anexos
- [ ] Cenário de múltiplos itens do MESMO Anexo compartilhando o MESMO código NBS (achado
      crítico 3) coberto por teste dedicado, não presumido resolvido pelo mecanismo herdado
- [ ] Itens de chave NCM minoritária do Anexo X (4 itens) e do Anexo XI (30 itens) documentados
      como não resolvidos nesta feature
- [ ] Itens sem nenhum código citável (Anexo II item 9, Anexo X itens 49-54, Anexo XI itens
      1.6/1.7/1.10/1.11/1.12) documentados como limitação distinta de "NBS não reconhecido"
- [ ] Itens vetados do Anexo XI (1.4, 1.5, 1.8, 1.9) nunca resolvidos, tratados como se não
      existissem no Anexo
- [ ] Zero regressão: os 10 Anexos NCM já shipados, o IPI e o regime vigente continuam
      funcionando exatamente como hoje
- [ ] `motor_calculo/` não ganha nenhuma dependência de infraestrutura

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path — NBS exato (Anexo II) | `nbs = "1.2202.00.00"` (Ensino Técnico, item 4) | `POST /v1/tax/simulate` | 200; CBS/IBS reduzidos a 60% do valor da fase; fonte citada "LCP 214/2025, Anexo II, item 4" |
| AT-002 | Prefixo parcial de subposição (Anexo II) | `nbs` correspondente a `1.2201.1x` (dentro do prefixo `1.2201.1`) | `POST /v1/tax/simulate` | 60%, citando "Anexo II, item 1" — prova que o truncamento de 1 dígito dentro da subposição funciona |
| AT-003 | Múltiplos itens do MESMO Anexo, MESMO código (Anexo III) | `nbs = "1.2301.99.00"` | `POST /v1/tax/simulate` | 60%, citando o item de MENOR número (18, "vigilância sanitária") como principal; `itens_correspondentes` lista os 10 itens (18, 19, 20, 21, 22, 23, 24, 25, 26, 28) |
| AT-004 | Item sem código (Anexo II) | `nbs` fantasiado tentando casar com o item 9 ("Educação especial") — sem código real na fonte | `POST /v1/tax/simulate` | Nunca "resolvido" por acidente; documentação/resposta deixa explícito que o item 9 não tem código citável, distinto de "NBS não reconhecido" |
| AT-005 | Minoria NCM do Anexo X não resolvida | `ncm` correspondente a um dos itens 42-45 (ex. `9701.91.00`, quadros artísticos) | `POST /v1/tax/simulate` | Nunca recebe 60% pelo Anexo X "por acidente" (chave é NCM aqui, fora de escopo desta feature); documentação declara isso |
| AT-006 | Itens sem código do Anexo X (obras teatrais) | Requisição referente a um dos itens 49-54 | `POST /v1/tax/simulate` | Nunca "resolvido"; documentado como limitação (célula vazia na fonte) |
| AT-007 | Condição de nacionalidade não informada (Anexo X) | `nbs` de um item plausivelmente coberto pelos incisos I/II/III/VII do art. 139 (conteúdo nacional exigido), sem nenhum campo de nacionalidade no payload | `POST /v1/tax/simulate` | Comportamento declarado explicitamente pelo `/design` (aplicar 60% com aviso, ou não aplicar com aviso) — nunca silêncio sobre a condição |
| AT-008 | Anexo XI, item vetado | `nbs` correspondente a `1.1802.90.00` ou `1.1802.30.00` (itens 1.4/1.5, vetados) | `POST /v1/tax/simulate` | Nunca resolvido — tratado como se o item não existisse no Anexo, não como "excluído expressamente" |
| AT-009 | Anexo XI, item "pendente de classificação" | Requisição referente a um dos itens 1.6/1.7/1.10/1.11/1.12 | `POST /v1/tax/simulate` | Nunca "resolvido" por não haver código; documentado como limitação distinta ("código ainda não atribuído pela nomenclatura", não "célula vazia") |
| AT-010 | Anexo XI, condição de comprador não informada | `nbs = "1.1501.20.00"` (item 1.1, Segurança em TI), sem `comprador_tipo` no payload | `POST /v1/tax/simulate` | Alíquota geral da fase (não 60%) — resposta declara explicitamente que 60% se aplicaria com `comprador_tipo=ORGAO_PUBLICO` |
| AT-011 | Anexo XI, condição de comprador informada | Mesmo item, `comprador_tipo=ORGAO_PUBLICO` no payload | `POST /v1/tax/simulate` | 60%, citando "Anexo XI, item 1.1, art. 142, I" |
| AT-012 | Anexo XI, `ENTIDADE_CEBAS_SUS` não se aplica | Mesmo item, `comprador_tipo=ENTIDADE_CEBAS_SUS` no payload | `POST /v1/tax/simulate` | Alíquota geral da fase — `ENTIDADE_CEBAS_SUS` não tem base legal no art. 142, nunca dispara 60% para itens do Anexo XI |
| AT-013 | Anexo XI, minoria NCM (bens) não resolvida | `ncm` correspondente a um item do Bloco 2 (ex. `8710.00.00`, carro blindado) | `POST /v1/tax/simulate` | Nunca recebe 60% pelo Anexo XI "por acidente" (chave é NCM aqui, fora de escopo); documentado |
| AT-014 | Regressão — os 10 Anexos NCM já shipados intactos | `ncm` de um item já shipado de qualquer um dos 10 Anexos NCM | `POST /v1/tax/simulate` | Comportamento idêntico ao já shipado, sem nenhuma interferência do campo `nbs` novo |
| AT-015 | Item de mercadoria sem `nbs` preenchido | Payload sem o campo `nbs` (ou `null`) | `POST /v1/tax/simulate` | Comportamento idêntico ao já shipado antes desta feature — o campo novo é opcional, sem efeito quando ausente |

---

## Out of Scope

- Anexos IV, V, VI, VII, VIII, IX (redução de 60% por NCM, posição 13, já shipada) — mecanismo
  de chave diferente, decisão de agrupamento já tomada
- Anexo XVI (piso de alíquota própria, posição 15), Anexo XVII (Imposto Seletivo, posição 16),
  Anexos XVIII-XXIII (Simples Nacional, posição 17) — features futuras próprias
- Itens de chave NCM minoritária dos próprios Anexos X (4 itens: 42-45) e XI (30 itens: bloco
  de bens 2.1-2.30) — documentados como não resolvidos, não implementados
- Itens sem nenhum código citável (Anexo II item 9; Anexo X itens 49-54; Anexo XI itens
  1.6/1.7/1.10/1.11/1.12) — documentados como limitação, não resolvidos
- Itens vetados do Anexo XI (1.4, 1.5, 1.8, 1.9) — nunca implementados, tratados como
  inexistentes no Anexo
- **A implementação de fato dos campos de nacionalidade de conteúdo (Anexo X) e de vendedor
  qualificado (Anexo XI, inciso II) no payload — decisão do `/design` se entram nesta feature
  ou ficam documentados como limitação conhecida; o que NÃO é opcional é que as lacunas sejam
  tratadas explicitamente, não silenciadas**
- Art. 137 (redução de 60% a produtos agropecuários "in natura", sem Anexo — já identificado
  como fora de escopo pela feature anterior), art. 140 (comunicação institucional à
  administração pública, 60%, sem Anexo, lista os serviços diretamente no artigo) e art. 141
  (atividades desportivas, 60%, sem Anexo — inciso I cita um código NBS diretamente no texto
  do artigo, `1.2205.12.00`, sem tabela) — três mecanismos de 60% que NÃO usam nenhum Anexo,
  estruturalmente diferentes desta feature (que trata só de Anexos-tabela); candidatos a
  feature própria futura, registrados para o roadmap
- Ajuste de base de cálculo por glosas médicas (Anexo III, art. 130, parágrafo único) — este
  motor não modela glosas
- Confirmação de que os itens "pendente de classificação" do Anexo XI já receberam código NBS
  numa revisão posterior da nomenclatura (fonte oficial inacessível)
- Mapeamento item a item dos 47 itens do Anexo X aos 8 incisos do art. 139 — a existência da
  condição é MUST desta feature; o mapeamento exaustivo item-a-inciso é trabalho de
  `/design`/`/build`
- Verificação programática automatizada de overlap entre os códigos NBS e os 10 Anexos NCM já
  shipados — estruturalmente desnecessária se `nbs` e `ncm` viverem em campos/tabelas
  separados (Achado crítico 4); o `/design` deve confirmar essa separação, não uma checagem de
  colisão de dado
- Sincronização de eventuais alterações futuras aos 4 Anexos (nova lei complementar) ou de
  atualizações da nomenclatura NBS em si (fora do controle deste projeto)
- Fuzzy match ou heurística além do que o texto de cada Anexo define literalmente

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `motor_calculo/` deve continuar rodando sem nenhuma infraestrutura | A correspondência por NBS é pura, sem I/O — a novidade de dado vive em `db/`/`api/` |
| Technical | Código NBS tem 9 dígitos completos (vs. 8 do NCM) — `api/nbs.py` precisa de canonização e comprimentos de prefixo PRÓPRIOS, não reaproveitados cegamente de `_COMPRIMENTOS_PREFIXO` do NCM | O `/design` decide a tupla de comprimentos aceitos para NBS, informada pelos 90 códigos observados nesta sessão |
| Technical | NBS e NCM não podem compartilhar coluna/consulta sem discriminador de vocabulário (Achado crítico 4) | Risco de colisão silenciosa se um `/design` tentar "economizar" uma tabela |
| Technical | Múltiplos itens do MESMO Anexo podem compartilhar o MESMO código NBS (Achado crítico 3) — nunca visto nos 10 Anexos NCM | O mecanismo de desempate herdado parece compatível, mas precisa de teste dedicado, não presunção |
| Technical | O payload de `/v1/tax/simulate` não tem campo de nacionalidade de conteúdo (Anexo X) nem de composição societária do vendedor (Anexo XI, inciso II) | Bloqueia a implementação COMPLETA de duas condições legais; o `/design` decide se resolve com campo(s) novo(s) ou documenta como limitação explícita — nenhuma das opções pode ficar implícita |
| Technical | A fonte oficial da estrutura do NBS (`nbs.economia.gov.br`) está inacessível deste ambiente (`NXDOMAIN`) | A estrutura documentada é inferida empiricamente dos 90 códigos observados, não confirmada contra especificação oficial — assunção a validar pelo `/design`, não fato fechado |
| Business | Escopo estritamente limitado aos Anexos II, III, X e XI — nenhum outro Anexo, nenhuma alteração aos dados já shipados dos 10 Anexos NCM | Zero regressão (AT-014) |
| Legal | Nenhum código NBS/NCM tratado como definitivo sem verificação contra fonte primária | Concluído nesta sessão para os 142 itens |
| Legal | A LC 227/2026 alterou só o art. 142, inciso II (Anexo XI) entre os dispositivos relevantes a esta feature — nenhuma outra alteração aos Anexos II, III, X, XI ou aos artigos 129, 130, 139 | O `/build` deve usar o texto vigente (pós-LC 227/2026) do art. 142, II, que remove a citação a "NCM/SH" desse inciso |
| Legal | Os itens 1.4, 1.5, 1.8 e 1.9 do Anexo XI foram vetados na sanção ORIGINAL da LCP 214/2025 (Mensagem de Veto Parcial nº 88/2025), não pela LC 227/2026 — nunca estiveram em vigor | O `/build` nunca deve transcrever esses 4 itens como resolvíveis |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Migração nova em `db/migrations/` (próxima numeração livre: `011_*.sql`) + `api/nbs.py` (novo, irmão de `api/ncm.py`) + política de resolução (novo módulo ou extensão de `api/reducao.py`, decisão do `/design`) + extensão de `api/schemas_simulate.py` (campo `nbs` em `ItemSimulacao`, possíveis campos novos de nacionalidade/vendedor) + consumo em `api/routers/simulate.py` | Mesma estrutura de 3 camadas já validada 4 vezes (SQL puro → política → consumo), mas para um vocabulário novo |
| **KB Domains** | `data-modeling` (schema-migration — vocabulário de correspondência inteiramente novo, 9 dígitos, com truncamento parcial de subposição; e duas condições legais de dimensões nunca modeladas — nacionalidade de conteúdo, composição societária do vendedor), `data-quality` (data-contract-authoring — 142 itens, 3 classes distintas de "sem código citável" e uma anomalia literal de dígito faltante), `python` (clean-architecture), `testing` (padrão `Protocol` real/fake já usado 5 vezes) | Nenhum domínio de KB específico para NBS foi encontrado no `_index.yaml` — tratado como desenho genuinamente novo, mesmo aviso já registrado pelo brainstorm |
| **IaC Impact** | Nova migração Postgres a aplicar via `migrar_banco.yml` (mesmo fluxo já usado 5 vezes); `GRANT SELECT` para `taxreformai_app` | Nenhuma mudança de Terraform |

**Why This Matters:**

- **Location** → Reaproveita a estrutura de 3 camadas já validada; a decisão nova é só a forma
  do vocabulário (NBS, não NCM) e os campos de condição legal
- **KB Domains** → `data-modeling` precisa de peso maior aqui: é a primeira vez que o projeto
  modela uma condição sobre o VENDEDOR (não só sobre o comprador ou a operação) e uma condição
  sobre a NACIONALIDADE de um conteúdo/produção
- **IaC Impact** → Mesmo fluxo de migração de sempre

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| LCP 214/2025, Anexo II (`legis.senado.leg.br`, mirror do DOU) | Texto legal | 9 itens (8 NBS + 1 sem código) | Estático — LC 227/2026 não o alterou (confirmado nesta sessão) | Legislativo Federal |
| LCP 214/2025, Anexo III (idem) | Texto legal | 30 itens, todos NBS (10 compartilham 1 código + 1 anomalia de dígito) | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo X (idem) | Texto legal | 57 itens (47 NBS + 4 NCM + 6 sem código) | Estático — idem | Legislativo Federal |
| LCP 214/2025, Anexo XI (idem) | Texto legal | 46 itens (5 NBS resolvíveis + 30 NCM + 5 sem código + 4 vetados + 2 cabeçalhos) | Estático — Anexo em si não alterado; art. 142 (inciso II) alterado pela LC 227/2026 | Legislativo Federal |
| LCP 214/2025, arts. 129, 130, 139, 142 (idem) | Texto legal (artigos que regem os 4 Anexos + condições) | 4 artigos + §§ | Estático, exceto art. 142, II (LC 227/2026, em vigor) | Legislativo Federal |
| Mensagem de Veto Parcial nº 88/2025 (idem) | Texto legal (veto original) | 4 itens vetados do Anexo XI | Estático — veto da sanção original, não da LC 227/2026 | Presidência da República |
| Nomenclatura Brasileira de Serviços (NBS) — estrutura oficial | Especificação de nomenclatura | Desconhecido | **Fonte inacessível deste ambiente** (`nbs.economia.gov.br`, `NXDOMAIN`) | RFB/MDIC (sucessor do antigo Ministério da Economia) |

### Schema Contract (requisitos — forma final a definir no `/design`)

| Requisito | Descrição | Obrigatório? |
|-----------|-----------|--------------|
| Identificação do Anexo | Distinguir II/III/X/XI — mesmo padrão `(anexo, item, sub_item)` já generalizado nas features anteriores | Sim |
| Vocabulário discriminado | Coluna/tabela de prefixo NBS separada (ou com discriminador explícito) da de prefixo NCM — nunca comingladas sem tipo (Achado crítico 4) | Sim |
| Percentual de redução | 60% uniforme nos 4 Anexos — mesma decisão de reaproveitar o catálogo já existente (`anexos_reducao_catalogo`) ou criar entradas próprias, decisão do `/design` | Sim |
| Prefixo de dígitos NBS, comprimento variável (até 9), com truncamento PARCIAL de 1 dígito dentro de um nível de 2 dígitos | Observado nos itens de subposição truncada (`1.2201.1`, `1.1103.4`, `1.1806.6`) — nunca visto nos Anexos NCM, onde os comprimentos aceitos sempre alinham a fronteiras de nível completo | Sim |
| Múltiplos itens do MESMO Anexo com o MESMO prefixo | Cobre o Anexo III (10 itens) e o Anexo II (2 itens) — requer decisão de qual item é "vencedor" para citação principal, com todos preservados em `itens_correspondentes` | Sim |
| Situação "sem código atribuído pela nomenclatura" (distinta de "célula vazia") | Cobre os 5 itens "pendente de classificação" do Anexo XI — semanticamente diferente de "célula vazia sem nenhuma chave" (Anexo II/9, Anexo X/49-54) | Sim |
| Situação "vetado" | Cobre os 4 itens do Anexo XI vetados na sanção original — nunca tratados como "excluído expressamente" nem "resolvido" | Sim |
| Condição de comprador (Anexo XI, inciso I) | Reaproveitar `CompradorTipo.ORGAO_PUBLICO` — decisão do `/design` confirmar que `ENTIDADE_CEBAS_SUS` NUNCA dispara 60% para itens do Anexo XI | Sim |
| Condição de vendedor (Anexo XI, inciso II) | Campo novo ou limitação documentada — decisão do `/design` | Sim, uma das duas |
| Condição de nacionalidade de conteúdo (Anexo X) | Campo novo ou limitação documentada — decisão do `/design`; mapeamento item-a-inciso do art. 139 é trabalho de `/design`/`/build` | Sim, uma das duas |
| `dispositivo_legal_ref` | Formato análogo ao já usado: "LCP 214/2025, Anexo {Anexo}, item {N}" — os artigos que regem cada Anexo (129, 130, 139, 142) e as condições (139 §§1º-3º; 142, I/II) precisam ser citados corretamente | Sim |
| Descrição do serviço | Texto literal do item, para auditoria | Sim |

### Freshness SLAs

Não aplicável — dado estático, sem pipeline de atualização recorrente. Nota: diferente dos
Anexos IV/V/VI/IX (revisão a cada 120 dias por ato conjunto), nenhum dos 4 Anexos desta feature
tem cláusula de revisão periódica no corpo da lei — confirmado por leitura direta dos arts.
129, 130, 139 e 142.

### Completeness Metrics

- 142/142 itens dos Anexos II, III, X e XI verificados contra fonte primária nesta sessão
  (100%)
- 90/142 itens (63%) são NBS resolvíveis nesta feature; 34/142 (24%) são NCM minoritário (fora
  de escopo); 12/142 (8%) não têm nenhum código citável (2 subclasses: célula vazia vs.
  "pendente de classificação"); 4/142 (3%) foram vetados na sanção original
- 2/4 Anexos (II, III) não têm nenhuma condição além do código; 1/4 (X) tem condição de
  nacionalidade de conteúdo afetando a maioria dos itens NBS; 1/4 (XI) não tem NENHUM "60%
  incondicional" — toda a redução depende de comprador ou vendedor qualificado
- 12/90 itens NBS resolvíveis (13%, os 10 do Anexo III + 2 do Anexo II) compartilham código com
  outro item do MESMO Anexo — cenário nunca visto nos 10 Anexos NCM já shipados

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O texto dos 4 Anexos obtido via `legis.senado.leg.br` é o texto vigente, sem alterações posteriores além da alteração ao art. 142, II | Os itens/códigos usados no `/design`/`/build` estariam errados | [x] Validado nesta sessão — lista de "Normas posteriores" da LCP 214/2025 e conteúdo integral da LC 227/2026 e da Mensagem de Veto nº 88/2025 lidos diretamente |
| A-002 | O classificador de topo "1" (antes do primeiro ponto) é uma "Seção" genérica de serviços da NBS, não uma coincidência restrita a estes 4 Anexos | Se houver códigos NBS com outro classificador de topo em Anexos futuros, a estrutura de canonização precisaria ser revista | [ ] NÃO validado — fonte oficial (`nbs.economia.gov.br`) inacessível deste ambiente; inferido empiricamente de 90 códigos, todos com "1" |
| A-003 | O mecanismo de desempate herdado (`itens_correspondentes` + `-item` como critério final) resolve corretamente o cenário de múltiplos itens do MESMO Anexo com o MESMO código (Achado crítico 3), sem exigir um mecanismo novo | Se a citação "vencedora" escolhida não fizer sentido de produto (ex. citar sempre o item de menor número quando um item mais descritivo seria mais útil ao auditor), o `/design` precisaria de uma regra dedicada | [ ] A confirmar no `/design`, com teste dedicado (AT-003) |
| A-004 | `CompradorTipo.ORGAO_PUBLICO` (já existente) é reaproveitável, sem alteração de enum, para a condição do art. 142, I (Anexo XI) | Se a definição legal divergir em algum detalhe não capturado nesta sessão, a reutilização citaria o dispositivo errado | [x] Validado nesta sessão — texto do art. 142, I ("administração pública direta, autarquias e fundações públicas") e dos arts. 144-II-a/145-II-a/146-§1º-I (base do enum existente) comparados; mesma definição substantiva |
| A-005 | O `/design` decide como tratar as lacunas de "nacionalidade de conteúdo" (Anexo X) e "vendedor qualificado" (Anexo XI, inciso II) — nem "60% incondicional" nem "nunca 60%" são aceitáveis como default silencioso | Se o `/design` (ou `/build`) assumir um dos dois extremos sem declarar, a simulação erra sistematicamente para uma classe real de clientes (produções culturais estrangeiras; fornecedores de segurança cibernética) | [ ] Não resolvido nesta sessão — decisão explícita fica para o `/design`, ver "Achado crítico 2" |
| A-006 | Os 5 itens "pendente de classificação" do Anexo XI continuam sem código também na nomenclatura NBS atual (não só no texto legal de 2025) | Se a nomenclatura já tiver atribuído códigos a esses serviços numa revisão posterior, a feature estaria deixando de resolver itens resolvíveis | [ ] NÃO validado — fonte da nomenclatura em si inacessível; só o texto legal (que reflete o estado de 2025) foi verificado |

**Note:** Validar A-002, A-003 e A-005 explicitamente no `/design` antes do `/build` — todas têm
potencial de gerar erro de cálculo real (não cosmético) ou uma decisão de produto pouco visível
se ignoradas.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase clara, quantificada (142 itens, 4 Anexos, 3 achados críticos), causa raiz nova (vocabulário de correspondência por serviço, inexistente no projeto) |
| Users | 3 | Mesmos dois usuários já validados nas features anteriores, com pain point específico (superestimação de X e Y, e o risco oposto para produções estrangeiras/fornecedores não qualificados) |
| Goals | 3 | MoSCoW explícito; os 3 achados críticos (estrutura NBS, condições legais de X/XI, itens duplicados dentro do mesmo Anexo) são MUST, não escondidos nem deferidos silenciosamente |
| Success | 3 | Critérios testáveis e numéricos (142/142 itens, 90/142 NBS resolvíveis, 12/90 com código compartilhado) |
| Scope | 2 | Out of scope explícito, mas três decisões de fronteira ficam deliberadamente abertas para o `/design` (campos de nacionalidade/vendedor no payload; forma exata do schema NBS; comprimentos de prefixo aceitos) — correto por não presumir a resposta, mas reduz a nota porque a fronteira exata da implementação não está 100% fechada, mesma razão da feature anterior |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

**Nota sobre esforço (não é parte da nota de clareza):** o brainstorm estimou este grupo como
"replica o padrão NCM, só muda a chave". A verificação desta sessão confirma que o MECANISMO de
cálculo (redução percentual de 60%) é totalmente reaproveitável da feature anterior, mas
encontra 3 fatores de esforço que o brainstorm não previu: (1) a estrutura do código NBS tem 4
níveis e permite truncamento parcial de subposição, exigindo uma função de canonização nova,
não uma cópia de `digitos_ncm`; (2) 2 dos 4 Anexos (X e XI) carregam condições legais que o
brainstorm não tinha detectado — nacionalidade de conteúdo e (inédito no projeto) composição
societária do vendedor; (3) o Anexo XI, que o brainstorm tratava como "mais um Anexo de 60%",
na prática não tem NENHUM "60% incondicional" — é estruturalmente mais parecido com uma
exceção condicionada (como IV/V/VI) do que com um Anexo "simples" (como II/III). Isso não muda
a resposta de "qual é o problema" (nota de clareza), mas muda substancialmente "quanto
trabalho" — mesmo padrão de correção já visto nas três features anteriores desta leva.

---

## Open Questions

Nenhum item abaixo bloqueia o avanço para `/design` — são decisões de implementação, não
lacunas de entendimento:

1. **Como tratar a condição de nacionalidade de conteúdo (Anexo X)**: campo novo no payload
   (`conteudo_nacional_majoritario` ou equivalente) vs. limitação documentada explicitamente
   sem mudança de payload — decisão do `/design`, com a restrição de que nenhuma das duas pode
   ficar implícita (ver "Achado crítico 2").
2. **Como tratar a condição de vendedor qualificado (Anexo XI, inciso II)**: campo novo vs.
   limitação documentada — mesma restrição.
3. **Mapeamento item-a-inciso do art. 139** (quais dos 47 itens NBS do Anexo X se relacionam a
   qual dos 8 incisos, e portanto quais têm exigência de nacionalidade) — trabalho de
   granularidade de `/design`/`/build`, não resolvido exaustivamente neste `/define`.
4. **Forma exata do schema NBS**: nova tabela dedicada (`anexos_reducao_nbs` ou equivalente)
   vs. extensão do catálogo/tabela já existente com um discriminador de vocabulário — decisão
   do `/design`, análoga à Decisão 1 das duas features anteriores, mas com a restrição adicional
   do Achado crítico 4 (nunca comingle sem discriminador).
5. **Comprimentos de prefixo NBS aceitos**: os 90 códigos observados sugerem 5 (posição), 6
   (posição + 1 dígito de subposição), 7 (posição + subposição completa) e 9 (completo) dígitos
   — decisão do `/design` se replica exatamente esses 4 comprimentos ou generaliza mais
   amplamente (ex. aceitar qualquer comprimento entre 5 e 9, análogo ao NCM).
6. **Citação "vencedora" quando múltiplos itens do mesmo Anexo compartilham código** (Achado
   crítico 3) — o mecanismo herdado parece compatível, mas a escolha de qual descrição vira a
   citação principal é uma decisão de produto, não só técnica.
7. **Nome exato do campo novo em `ItemSimulacao`** (`nbs`, `codigo_nbs`, ou outro) — decisão do
   `/design`, sem impacto na substância desta feature.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-30 | define-agent | Versão inicial, extraída de `BRAINSTORM_ANEXOS_REDUCAO_PERCENTUAL_NBS.md`; verificação de fonte primária realizada nesta sessão (4 Anexos via `legis.senado.leg.br`, corpo da LCP 214/2025 arts. 129-142/137/140/141, texto da LC 227/2026 e da Mensagem de Veto Parcial nº 88/2025); contagens corrigidas (142 itens reais vs. ~113 estimados, com desvios grandes por Anexo); estrutura do código NBS investigada empiricamente (4 níveis, 9 dígitos, truncamento parcial de subposição) — fonte oficial (`nbs.economia.gov.br`) confirmada inacessível deste ambiente (`NXDOMAIN`); três achados críticos novos — condição de nacionalidade de conteúdo (Anexo X, art. 139 §§1º-3º), ausência de "60% incondicional" no Anexo XI (art. 142, condicionado a comprador OU vendedor) e itens do MESMO Anexo compartilhando o MESMO código NBS (Anexo III: 10 itens; Anexo II: 2 itens); confirmado que a LC 227/2026 não alterou os 4 Anexos em si, mas alterou o art. 142, II (Anexo XI), removendo uma citação equivocada a "NCM/SH" de um inciso que trata só de serviços |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_ANEXOS_REDUCAO_PERCENTUAL_NBS.md`
