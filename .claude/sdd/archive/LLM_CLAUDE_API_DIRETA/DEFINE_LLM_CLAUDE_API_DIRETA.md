# DEFINE: LLM_CLAUDE_API_DIRETA

> Contorno do bloqueio real de quota do Vertex AI — cliente LLM alternativo via API Claude direta, selecionável por env var

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LLM_CLAUDE_API_DIRETA |
| **Date** | 2026-08-04 |
| **Author** | (sessão direta, sem subagentes) |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## Problem Statement

O projeto `taxreformai-dev` tem quota zero/mínima do Vertex AI para modelos Claude
(`429 RESOURCE_EXHAUSTED`, documentado em `LLM_REAL_VERTEX_AI/SHIPPED_2026-08-03.md`), bloqueando
por completo o caminho `200` de `POST /v1/tax/query` — bloqueio externo, resolvível só pelo
usuário no Console do GCP, sem prazo definido. É preciso um caminho alternativo real via API
Claude direta (Anthropic) para destravar o produto sem depender da liberação da quota.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Usuário final do endpoint conversacional | Consome `POST /v1/tax/query` | Hoje recebe 503 sempre que o LLM é chamado, mesmo com todo o resto da orquestração (RAG híbrido, motor determinístico) funcionando |
| Time de operação/deploy | Configura o serviço `taxreformai-api` | Precisa de uma forma simples e reversível de trocar de provider sem reescrever código, para quando a quota do Vertex for liberada |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `ClienteAnthropicDireto` novo, implementando o mesmo `Protocol` `ClienteLLM` já existente |
| **MUST** | Seleção de provider via `LLM_PROVIDER` (`"direto"` default, `"vertex"` opt-in) |
| **MUST** | Zero mudança em qualquer nó de `orquestracao/nos/` |
| **MUST** | Zero dependência Python nova |
| **SHOULD** | `POST /v1/tax/query` verificado contra a API Claude direta real (200 de verdade), mesma disciplina de `LLM_REAL_VERTEX_AI` |
| **COULD** | Mensagem de erro clara quando `ANTHROPIC_API_KEY` estiver ausente com `LLM_PROVIDER=direto` |

---

## Success Criteria

- [ ] `LLM_PROVIDER=direto` (ou variável ausente) instancia `ClienteAnthropicDireto`
- [ ] `LLM_PROVIDER=vertex` continua instanciando `ClienteVertexAI`, sem nenhuma regressão nos testes existentes de `LLM_REAL_VERTEX_AI`
- [ ] `git diff` confirma zero linha alterada em `orquestracao/nos/`
- [ ] `POST /v1/tax/query` responde `200` com `parecer_final` real, chamando a API Claude direta em produção
- [ ] `requirements-api.txt` sem nenhuma linha nova

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Provider direto é o default | `LLM_PROVIDER` não definida | `criar_dependencias_reais(settings)` é chamado | `cliente_llm` é instância de `ClienteAnthropicDireto` |
| AT-002 | Provider Vertex continua funcionando | `LLM_PROVIDER=vertex` | `criar_dependencias_reais(settings)` é chamado | `cliente_llm` é instância de `ClienteVertexAI` (sem regressão) |
| AT-003 | Chamada real via API direta | `LLM_PROVIDER=direto`, `ANTHROPIC_API_KEY` real configurada | `ClienteAnthropicDireto.gerar(...)` é chamado | Retorna texto real da API Claude, sem lançar `LLMIndisponivelError` |
| AT-004 | Erro da API direta vira `LLMIndisponivelError` | API Claude direta indisponível/erro de rede | `ClienteAnthropicDireto.gerar(...)` é chamado | Levanta `LLMIndisponivelError`, mesma disciplina de `ClienteVertexAI` |
| AT-005 | `POST /v1/tax/query` em produção | Serviço deployado com `LLM_PROVIDER=direto` e `ANTHROPIC_API_KEY` reais | Requisição real ao endpoint | Resposta `200` com parecer real, guardrail do sintetizador satisfeito |
| AT-006 | Nenhum nó muda | Estado do repositório após o build | `git diff -- orquestracao/nos/` | Diff vazio |

---

## Out of Scope

- Failover automático entre providers (Vertex → direto ou vice-versa)
- Revisão do mapeamento de modelo por nó (Haiku no classificador, Sonnet nos outros 3 continuam)
- Remoção de `ClienteVertexAI`/suporte ao Vertex AI
- Qualquer mudança em `orquestracao/nos/`, `api/`, ou schema do banco

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Zero dependência Python nova | `anthropic[vertex]` já inclui a classe `Anthropic` da API direta |
| Technical | `ClienteLLM` Protocol não muda de assinatura | `ClienteAnthropicDireto` precisa se encaixar no contrato existente |
| Process | `ANTHROPIC_API_KEY` é criada manualmente pelo usuário no Console da Anthropic | Mesma disciplina de credenciais já estabelecida — nunca gerada pelo agente |
| Design | IDs de modelo diferem entre Vertex (`claude-haiku-4-5@20251001`) e API direta (`claude-haiku-4-5-20251001`) | Precisa de mapeamento explícito por provider, não pode reusar as constantes atuais como estão |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `orquestracao/llm/cliente.py`, `orquestracao/config.py`, `orquestracao/dependencias.py` | Nenhum arquivo fora de `orquestracao/` |
| **KB Domains** | N/A | Troca de transporte, não de lógica de orquestração |
| **IaC Impact** | Nenhum recurso Terraform novo — só um GitHub Secret novo (`ANTHROPIC_API_KEY`) e uma env var nova (`LLM_PROVIDER`) no Cloud Run já existente de `taxreformai-api` | Requer atualizar `deploy.yml` para passar as novas env vars |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `anthropic.Anthropic` (classe da API direta) já está disponível em `anthropic[vertex]` instalado, sem `pip install` adicional | Precisaria adicionar dependência nova em `requirements-api.txt` | [ ] |
| A-002 | O usuário cria manualmente a `ANTHROPIC_API_KEY` no Console da Anthropic e cadastra como GitHub Secret antes do deploy real | Login/chamadas reais falham até a credencial existir | [ ] |
| A-003 | Os IDs de modelo da API direta (`claude-haiku-4-5-20251001`, `claude-sonnet-5`) são os oficiais e correspondem aos mesmos modelos hoje usados via Vertex | Parecer poderia usar um modelo diferente do esperado por nó | [ ] |

**Note:** A-001 deve ser validada no `/design`/`/build` com um `import anthropic; anthropic.Anthropic` real antes de comprometer a arquitetura.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Bloqueio real já documentado em feature anterior, com causa raiz e impacto claros |
| Users | 3 | 2 personas identificadas, cada uma com dor específica |
| Goals | 3 | Priorizados MUST/SHOULD/COULD, todos testáveis |
| Success | 3 | Critérios verificáveis, incluindo "zero linha em `orquestracao/nos/`" como critério negativo checável |
| Scope | 3 | Out of Scope explícito, herdado diretamente das decisões já validadas no `/brainstorm` |
| **Total** | **15/15** | |

**Minimum to proceed: 12/15** — atendido.

---

## Open Questions

None - ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-04 | (sessão direta) | Versão inicial, extraída do BRAINSTORM já validado |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_LLM_CLAUDE_API_DIRETA.md`
