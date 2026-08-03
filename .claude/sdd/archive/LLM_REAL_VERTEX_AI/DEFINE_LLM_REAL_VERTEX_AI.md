# DEFINE: LLM Real via Vertex AI + Nós Reais da Orquestração

> Conectar Claude via Vertex AI de verdade e reescrever os 4 nós fake da orquestração
> multi-agente (`classificador`, `pesquisador_legal`, `extrator_regras`, `sintetizador`) para
> usar essa conexão — fundindo as posições 4 e 5 do roadmap por instrução explícita do usuário.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_REAL_VERTEX_AI |
| **Date** | 2026-08-03 |
| **Author** | define-agent |
| **Status** | ✅ Shipped 2026-08-03 |
| **Clarity Score** | 14/15 |

---

## Problem Statement

4 dos 5 nós de `orquestracao/nos/` (`classificador`, `pesquisador_legal`, `extrator_regras`,
`sintetizador`) são fake — não chamam nenhum LLM real nem fazem busca híbrida real no Qdrant,
apesar da infraestrutura de busca já existir e estar verificada em produção (6866 pontos,
`scripts/verificar_busca_hibrida.py` APROVADA). Isso impede que `POST /v1/tax/query` (o
endpoint conversacional já shipado em `API_HTTP_SIMULACAO`) entregue respostas reais
fundamentadas em legislação — hoje ele monta uma resposta Markdown hardcoded e registra
`"[FAKE]"` no histórico auditável, o que é inaceitável para uma plataforma que promete
"simulações 100% auditáveis com citação de fontes oficiais".

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Fiscal/controller/CFO (usuário final do simulador) | Consome `/v1/tax/query` via frontend `/consulta` | Recebe hoje uma resposta sintética que não reflete nenhuma pergunta real feita, nem cita legislação de verdade — a "conversa" é decorativa |
| Equipe de engenharia do projeto | Mantém `orquestracao/` e a suíte de testes | Precisa que os nós sejam testáveis sem gerar custo real por token em cada rodada de teste local/CI |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Conectar Claude via Vertex AI de verdade (SDK `anthropic[vertex]`, client `AnthropicVertex`), habilitando `aiplatform.googleapis.com` e concedendo `roles/aiplatform.user` à SA `taxreformai-runtime` |
| **MUST** | Reescrever `classificador.py` para classificar intenção real via Claude Haiku, preservando o mascaramento de PII real (CPF/CNPJ) que já roda ANTES de qualquer chamada de LLM |
| **MUST** | Reescrever `pesquisador_legal.py` para chamar `QdrantIndexer.search_hybrid` de verdade (reuso, sem reingestão) |
| **MUST** | Reescrever `extrator_regras.py` para extração estruturada real via Claude Sonnet |
| **MUST** | Reescrever `sintetizador.py` para síntese real via Claude Sonnet, citando as fontes recuperadas — remover o marcador `"[FAKE]"` do histórico auditável |
| **MUST** | Nenhuma chamada real ao Vertex AI em teste local/CI — só via `workflow_dispatch` gated, mesmo padrão de `ingestao.yml`/`migrar_banco.yml`/`deploy.yml` |
| **SHOULD** | Revisão de segurança dedicada (prompt injection via conteúdo recuperado do Qdrant e via consulta do usuário) antes do `/ship` |
| **COULD** | Endpoint regional dedicado ou cache de respostas — nenhum requisito de performance/custo levantou essa necessidade ainda |

---

## Success Criteria

- [ ] `anthropic[vertex]` adicionado a `requirements.txt`/`requirements-api.txt`, importável no sandbox
- [ ] Terraform (`infra/terraform/`) habilita `aiplatform.googleapis.com` e concede `roles/aiplatform.user` a `taxreformai-runtime@taxreformai-dev.iam.gserviceaccount.com`
- [ ] Client `Protocol` real/fake criado (nome a definir no `/design`), seguindo o padrão já usado em `RawStorage`/`LegalSource`/`Embedder`
- [ ] Os 4 nós fake passam a usar o client real, cada um no modelo correto da matriz do `contexto.md` seção 3.1 (Haiku para Classificador; Sonnet para Pesquisador Legal, Extrator de Regras e Sintetizador)
- [ ] `deterministico.py` permanece inalterado (já real, Python puro, sem LLM por desenho)
- [ ] 0 chamadas reais ao Vertex AI na suíte de testes local/CI (100% via fake do `Protocol`)
- [ ] Pelo menos 1 verificação end-to-end real por nó (chamada de verdade, não fake), disparada via `workflow_dispatch`, com evidência de resposta (não só "200 OK")
- [ ] `sintetizador.py` não grava mais `"[FAKE]"` em nenhum campo do histórico auditável
- [ ] Revisão de segurança concluída, sem achado crítico não resolvido, cobrindo especificamente: (a) conteúdo do Qdrant tratado como dado, nunca como instrução, dentro do prompt; (b) mascaramento de PII confirmado antes de qualquer envio ao Vertex AI

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Classificação real de intenção | Uma consulta conversacional de exemplo ("Quanto de CBS incide sobre uma venda de R$ 10.000 em 2026?") chega a `classificador.py`, client Vertex AI real configurado | O nó processa a mensagem | O CPF/CNPJ (se presente) é mascarado ANTES da chamada ao Vertex AI, e a intenção retornada reflete o conteúdo real da mensagem (não mais o hardcode `"SIMULACAO_TRIBUTARIA"` fixo) |
| AT-002 | Busca híbrida real no Pesquisador Legal | `pesquisador_legal.py` recebe uma consulta sobre CBS/IBS, Qdrant real acessível | O nó chama `search_hybrid` | Retorna ao menos 1 `Chunk` real da coleção `legislacao_tributaria` (não mais o `Chunk` sintético fixo), com o texto e a referência de origem preenchidos |
| AT-003 | Extração estruturada real | Texto de consulta + chunks recuperados chegam a `extrator_regras.py` | O nó chama o client real (Sonnet) | `payload_extraido` é montado a partir da extração do LLM, não mais copiado diretamente de `state` sem processamento |
| AT-004 | Síntese real com citação de fonte | `state.resultado_calculo` e os chunks recuperados chegam a `sintetizador.py` | O nó chama o client real (Sonnet) | A resposta Markdown final cita ao menos uma fonte real recuperada pelo Pesquisador Legal, e nenhum campo do histórico auditável contém a string `"[FAKE]"` |
| AT-005 | Vertex AI indisponível/erro de rede | Client real configurado, mas a chamada falha (timeout, erro 5xx, credencial inválida) | Qualquer um dos 4 nós tenta chamar o LLM | O erro é nomeado explicitamente no retorno/estado (nunca um 200 silencioso com conteúdo fabricado), consistente com a disciplina do projeto de nunca omitir falha de infraestrutura como sucesso |
| AT-006 | Zero custo em teste local/CI | Suíte `pytest tests/` completa rodando sem `DATABASE_URL`/credenciais de Vertex AI | `pytest tests/` é executado | Nenhum teste faz uma chamada de rede real ao Vertex AI — todos usam o fake do `Protocol`; suíte passa sem qualquer variável de ambiente de credencial do Vertex AI |
| AT-007 | PII mascarado antes do envio (segurança) | Mensagem de consulta contém um CPF/CNPJ real de exemplo | `classificador.py` processa a mensagem antes de chamar o Vertex AI | O payload efetivamente enviado ao client Vertex AI (real ou fake, verificável via teste) NUNCA contém o CPF/CNPJ em texto plano — só a versão mascarada já produzida pela regex existente |
| AT-008 | Verificação real end-to-end via workflow | Feature buildada, Terraform aplicado (API habilitada + IAM concedido) | Um workflow dedicado (novo ou estendido) é disparado via `workflow_dispatch` contra a infraestrutura real | Cada um dos 4 nós recebe ao menos uma chamada real ao Vertex AI, com evidência de resposta não-fake registrada no log do workflow |

---

## Out of Scope

- Suporte a múltiplos provedores de LLM (Bedrock, Anthropic API direta, etc.) — `contexto.md` já fixa Vertex AI
- Endpoint regional dedicado (`us-east5`/`europe-west1`) — endpoint `global` é a recomendação oficial da Anthropic, sem premium de preço, e resolve o único trade-off de região identificado
- Cache de respostas de LLM
- Service account dedicada só para LLM, separada de `taxreformai-runtime`
- Qualquer mudança em `motor_calculo/` ou `orquestracao/nos/deterministico.py` (já real, sem LLM, por desenho)
- Reingestão da coleção Qdrant (dados já existentes e verificados em `PIPELINE_INGESTAO_LEGAL`)
- Resolver o campo `finalidade_uso`/exceções que outras features já documentaram como limitação estrutural (não relacionado a este escopo)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Custo | Cada chamada real de verificação/build/deploy gera cobrança real por token no Vertex AI | Usuário já confirmou ciência; `/design` deve minimizar o número de chamadas reais de verificação (1 por nó é suficiente, não uma suíte inteira) |
| Política do projeto | Infraestrutura real nunca roda local (memória `feedback_cloud_only_execution.md`) | Toda chamada real só via `workflow_dispatch`, mesmo padrão de `ingestao.yml`/`migrar_banco.yml`/`deploy.yml` |
| IAM | `taxreformai-runtime` é deliberadamente sem role de projeto desde `SCHEMA_POSTGRESQL` | Esta feature concede a primeira role de projeto a essa SA (`roles/aiplatform.user`) — desvio documentado, não acidental |
| Técnico | Nenhum dos pacotes (`anthropic`, `google-cloud-aiplatform`) está instalado no sandbox de build hoje | Mesma situação já enfrentada com `qdrant-client`/`apache-airflow` — build valida por revisão de código onde a instalação real não for possível, e testa via fake onde for |
| Segurança | Primeira feature do projeto onde texto de usuário E conteúdo de terceiros (chunks de legislação) entram dentro de um prompt de LLM real | Superfície de prompt injection nova — revisão de segurança dedicada antes do `/ship` |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `orquestracao/nos/*.py` (modificados) + novo módulo de client em `orquestracao/llm/` (a nomear no `/design`) | Mantém a estrutura já existente de `orquestracao/` |
| **KB Domains** | genai-architect, python-developer, security-reviewer | genai-architect para o desenho de prompts/roteamento de modelo; security-reviewer para a superfície de prompt injection nova |
| **IaC Impact** | Novos recursos: `google_project_service` (habilitar `aiplatform.googleapis.com`) + `google_project_iam_member` (`roles/aiplatform.user` para `taxreformai-runtime`) em `infra/terraform/` | Primeira vez que Terraform toca permissões de LLM; segue o padrão já existente de outros `google_project_iam_member` do projeto |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O endpoint `global` do `AnthropicVertex` (`region="global"`) está disponível para os modelos `claude-sonnet-5`/`claude-haiku-4-5` no projeto `taxreformai-dev` | Precisaria cair para endpoint regional (`us-east5`/`europe-west1`), reintroduzindo a questão de região que o `global` resolvia | [x] Confirmado via documentação oficial (`platform.claude.com`) nesta sessão |
| A-002 | `anthropic[vertex]` funciona com autenticação padrão do Google Cloud (Application Default Credentials) já usada por outros clients GCP do projeto (GCS, Cloud SQL) | Precisaria de mecanismo de autenticação adicional/diferente | [ ] A validar no `/build`, contra o Cloud Run real |
| A-003 | `QdrantIndexer.search_hybrid` pode ser chamado diretamente de dentro de um nó de orquestração sem mudança de assinatura | Precisaria adaptar a interface existente | [ ] A validar no `/design`, lendo a assinatura completa do método |
| A-004 | O custo de 1 chamada real por nó (4 chamadas) por verificação é aceitável e não requer aprovação adicional além da já dada pelo usuário | Precisaria negociar um orçamento explícito de verificação | [x] Usuário já confirmou ciência do custo por token antes do brainstorm |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Claro e específico: 4 nós nomeados, infraestrutura de busca já existente subutilizada, impacto direto no endpoint `/v1/tax/query` |
| Users | 2 | Usuário final (fiscal/CFO) é inferido do blueprint (`contexto.md`), não entrevistado diretamente nesta sessão; equipe de engenharia é auto-evidente |
| Goals | 3 | Priorizados (MUST/SHOULD/COULD), cada um mapeado a um arquivo/decisão concreta |
| Success | 3 | Critérios testáveis e numéricos onde aplicável (0 chamadas reais em CI, 1+ verificação real por nó) |
| Scope | 3 | Out of Scope explícito e extenso, com justificativa de cada corte (YAGNI já aplicado no brainstorm) |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** ✅

---

## Open Questions

Nenhuma bloqueante para `/design`. Duas assunções técnicas (A-002, A-003) ficam para validação
durante `/design`/`/build`, não são bloqueantes de requisitos.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-03 | define-agent | Initial version, extraído de BRAINSTORM_LLM_REAL_VERTEX_AI.md |
| 1.1 | 2026-08-03 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_LLM_REAL_VERTEX_AI.md`
