# ROADMAP: Sequência Pós-Auditoria (Julho/2026)

> Registro de planejamento — não é um documento SDD por si só (não passa por /define,
> /design, /build, /ship). Serve de mapa para as ~11 sessões de brainstorm/define/design/
> build/ship que virão a seguir, uma feature de cada vez, na ordem definida aqui.
> Atualize a coluna **Status** conforme cada feature for shipada.

## Origem

Duas rodadas de auditoria profunda (SHIPPED_*.md + CLAUDE.md vs. código/CI reais; depois
`contexto.md` — blueprint original de 9 seções — vs. o que existe) levantaram 13 achados.
O achado 13 foi descartado por baixa prioridade/fora de escopo. Dos 12 restantes, o
usuário (Jonatas) decidiu em 2026-07-27:

1. **Não escolher um único achado/candidato** — atacar os 12 (menos o 13) um de cada vez,
   em sequência, não em paralelo nem agrupados livremente.
2. **Achado 12** (linha do tempo da reforma 2029-2033) fica de fora da sequência ATIVA.
   Está estruturalmente bloqueado: a lei que fixaria CBS/IS nesse período ainda não existe
   no mundo real. Vira item de **monitoramento**, não uma feature no pipeline, até (e se)
   a norma for promulgada.
3. **Ordem**: respeitar dependência técnica onde existir; usar a numeração original do
   levantamento (1-11) como desempate nos casos sem dependência entre si. Isso move o
   achado 5 (LLM real) para antes do achado 4 (nós reais da orquestração), que por sua vez
   resolve o achado 6 (vazamento `"[FAKE]"`) como efeito colateral — sem essas trocas, a
   ordem segue a numeração original do levantamento.

## Sequência ativa (11 features)

| Ordem | Achado original | Feature | Descrição resumida | Status |
|-------|------------------|---------|---------------------|--------|
| 1 | 1 | `IPI_TIPI_MOTOR_CALCULO` | Conectar `aliquotas_ipi_tipi` (9231 NCM já ingeridos) ao `motor_calculo`/`api/routers/simulate.py` — IPI deixa de ser "indisponível" quando o dado já existe | 🔵 Em brainstorm (esta sessão) |
| 2 | 2 | `REGRAS_TRIBUTARIAS_CACHE` | Decidir destino de `regras_tributarias_cache`/`buscar_regra_cache()` — plugar num consumidor real ou remover como código morto | ⚪ Não iniciado |
| 3 | 3 | `API_EMPRESA_SKUS` | Endpoints para tenant cadastrar/listar/upload de SKUs (`empresa_skus` — schema e RLS já existem, zero rota) | ⚪ Não iniciado |
| 4 | 5 | `LLM_REAL_VERTEX_AI` | Conectar Claude via Vertex AI de verdade (`anthropic`/`google-cloud-aiplatform` ausentes hoje) — pré-requisito técnico do item 5 | ⚪ Não iniciado |
| 5 | 4 | `ORQUESTRACAO_NOS_REAIS` | Tornar `classificador`/`pesquisador_legal`/`extrator_regras`/`sintetizador` reais (hoje fake), incluindo busca real no Qdrant — depende do item 4 (LLM conectado) | ⚪ Não iniciado |
| 6 | 6 | `REMOVER_FAKE_HISTORICO` | Eliminar o vazamento de `"[FAKE]"` em `/v1/tax/query` — resolvido como efeito colateral do item 5, mas registrado como feature própria para garantir verificação explícita | ⚪ Não iniciado |
| 7 | 7 | `CLOUD_COMPOSER_PROVISIONAMENTO` | Provisionar Cloud Composer real e executar `dags/ingestao_legal_dag.py` de verdade (hoje só revisão de código) | ⚪ Não iniciado |
| 8 | 8 | `VERIFICACAO_FRONTEND_NAVEGADOR` | Verificação manual do frontend num navegador real (pendência aberta desde o SHIPPED do `FRONTEND_SIMULADOR`) | ⚪ Não iniciado |
| 9 | 9 | `DIAGNOSTICO_BUSCA_HIBRIDA` | Root-cause do miss 4/5 no Bloco A de `ingestao.yml` (near-duplicado/boilerplate dentro da Resolução CGIBS nº 6/2026) | ⚪ Não iniciado |
| 10 | 10 | `BIGQUERY_DATA_WAREHOUSE` | Provisionar BigQuery para consultas analíticas em histórico de simulações (seção 5 do blueprint) | ⚪ Não iniciado |
| 11 | 11 | `FILA_ASSINCRONA_CELERY_REDIS` | Fila assíncrona (Celery/Redis) para sustentar 50.000+ SKUs dos planos Business/Enterprise | ⚪ Não iniciado |

## Item de monitoramento (fora da sequência ativa)

| Achado original | Item | Condição de reativação |
|------------------|------|-------------------------|
| 12 | Linha do tempo da reforma 2029-2033 (`motor_calculo/tabela_aliquotas.py`) | Só volta a ser uma feature executável quando a lei ordinária que fixa CBS/IS nesse período (ou a alíquota de referência do art. 347) for promulgada. Até lá, nenhuma alíquota deve ser estimada — mesma disciplina já aplicada a 2027-2028 |

## Achado 13 (não incluído na sequência)

Cosméticos, já marcados como baixa prioridade no levantamento original: Shadcn UI não é
dependência formal do frontend; modelo de negócio/pricing/billing (seção 9) sem
implementação (esperado nesta fase). Revisitar só se o usuário pedir explicitamente.
