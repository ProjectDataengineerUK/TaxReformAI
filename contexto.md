
 TaxReform AI: Arquitetura de Sistemas, Multi-Agentes, Infraestrutura GCP e Blueprint Completo

1. Visão Geral e Posicionamento do Produto

1.1 Proposta de Valor

O TaxReform AI é uma plataforma SaaS B2B Enterprise de Inteligência Tributária e Compliance em Tempo Real, desenvolvida especificamente para apoiar departamentos fiscais, controllers, CFOs e consultorias tributárias na coexistência e transição do antigo modelo tributário brasileiro (PIS, COFINS, IPI, ICMS, ISS) para o novo IVA Dual (CBS, IBS e Imposto Seletivo - IS).

Diferente de copilotos de uso geral ou leitores simples de documentos, o TaxReform AI combina RAG Híbrido Avançado com AST (Abstract Syntax Tree) de Legislação a Regras Determinísticas de Cálculo e Guardrails Contábeis em Sandbox Python, garantindo que qualquer simulação ou orientação tributária seja 100% auditável, citando fontes oficiais (Leis Complementares, Soluções de Consulta da RFB e Resoluções do Comitê Gestor do IBS).

1.2 Ideal Customer Profile (ICP) & Persona Compradora

Empresas Alvo:

Grandes Varejistas e E-commerce: Alto volume de SKUs (50.000+ itens) e operações interestaduais com complexidade de substituição tributária e alíquotas diferenciadas.

Indústrias da Manufatura, Bens de Consumo, Automotiva e Química: Cadeias longas de crédito fiscal, regimes de diferimento e incentivos regionais.

Multinacionais e Holdings com Atuação Nacional: Coexistência de múltiplos regimes estaduais/municipais e necessidade de adequação às normas internacionais de auditoria.

Big 4, BPOs Financeiros e Bancas Fiscais: Atendimento a múltiplos clientes corporativos exigindo emissão de pareceres em escala.

Personas Compradoras (Buyers):

CFO / Diretor Financeiro: Focado na projeção do impacto do Split Payment no capital de giro e na carga tributária efetiva de curto/médio prazo.

Head de Tax / Gerente Tributário: Busca agilidade para reclassificar SKUs, analisar creditamento, reconfigurar parâmetros no ERP e orientar a equipe fiscal.

Controller / Diretor de Compliance: Mapeia o risco de autos de infração, inconsistências na emissão de NF-e e divergências nas obrigações acessórias.

1.3 ROI Demonstrável para Vendas B2B

Redução de 90% no tempo de análise tributária: Consultas de enquadramento por NCM/NBS que levavam de 4 a 8 horas passam para menos de 2 minutos.

Preservação de Capital de Giro (Split Payment): Antecipação e simulação do impacto da retenção automática no ato da liquidação financeira, evitando surpresas de caixa.

Otimização do Estoque de Créditos: Mapeamento e amortização acelerada de saldos credores acumulados de ICMS, PIS e COFINS no período transicional (2026–2032).

2. Linha do Tempo da Reforma & Regras Transicionais

O motor de regras do TaxReform AI aplica automaticamente o módulo temporal correspondente à data da transação ou emissão do documento fiscal:

┌──────────────────────────────────────────────────────────────────────────────────┐
│                             LINHA DO TEMPO DA TRANSIÇÃO                          │
├──────────────┬───────────────────────────────────────────────────────────────────┤
│ 2026         │ Fase de Teste: CBS (0,9%) + IBS (0,1%) compensáveis com PIS/COFINS│
├──────────────┼───────────────────────────────────────────────────────────────────┤
│ 2027         │ Extinção do PIS/COFINS | Vigência Plena da CBS                      │
│              │ Zera alíquota do IPI (exceto produtos ZFM) | Entrada do IS      │
├──────────────┼───────────────────────────────────────────────────────────────────┤
│ 2029 - 2032  │ Transição do ICMS e ISS: Redução gradual de 10% ao ano            │
│              │ Elevação proporcional das alíquotas do IBS                        │
├──────────────┼───────────────────────────────────────────────────────────────────┤
│ 2033         │ Vigência Plena do Novo Sistema (Extinção definitiva de ICMS e ISS)│
└──────────────┴───────────────────────────────────────────────────────────────────┘


3. Arquitetura Multi-Agêntica e Roteamento de LLM (Claude / Anthropic)

Para responder consultas tributárias complexas sem gargalos de latência, estresse financeiro por consumo desnecessário de tokens ou risco de alucinação numérica, o sistema adota uma Arquitetura Multi-Agêntica Orientada a Grafos com Estado (LangGraph / CrewAI).

                        ┌──────────────────────────────┐
                        │   1. AGENTE CLASSIFICADOR    │
                        │    (Intent & PII Anonymizer) │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │    2. AGENTE PESQUISADOR     │
                        │    LEGAL (Hybrid AST RAG)    │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │    3. AGENTE DE EXTRAÇÃO     │
                        │   E REGRAS (JSON Enforcer)   │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   4. AGENTE DETERMINÍSTICO   │
                        │    (Python Sandbox Execution)│
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │  5. AGENTE SINTETIZADOR DE   │
                        │     PARECERES AUDITÁVEIS     │
                        └──────────────┴───────────────┘


3.1 Agentes Especialistas e Matriz de Modelos Claude (Vertex AI)

Agente Especialista

Função Principal

Modelo Recomendado

Justificativa Técnica

1. Classificador & PII

Identifica a intenção (simulação, NCM, crédito) e mascara CPFs, CNPJs e dados confidenciais (LGPD).

Claude 3.5 Haiku

Baixíssima latência (< 300 ms), baixíssimo custo e alta precisão para classificação e Regex.

2. Pesquisador Legal (RAG)

Formula buscas híbridas e recupera dispositivos legais válidos para a data da operação.

Claude 3.5 Sonnet

Compreensão impecável de contexto jurídico, português formal e raciocínio semântico avançado.

3. Extrator de Regras

Mapeia o texto legal recuperado e constrói um payload JSON estrito (validador Pydantic).

Claude 3.5 Sonnet

Líder de mercado em Structured Outputs, garantindo aderência absoluta a schemas JSON.

4. Motor Determinístico

Executa o cálculo numérico em sandbox isolado Python (retenções, IVA Dual, Split Payment).

Nenhum (Python Nativo)

Código Python puro sem LLM. Elimina alucinações matemáticas e reduz custo a zero tokens.

5. Sintetizador de Pareceres

Une a resposta matemática aos fundamentos legais e compõe o relatório final em Markdown/PDF.

Claude 3.5 Sonnet

Excelente coesão textual corporativa, citações estruturadas e redação fluida.

4. Pipeline de Ingestão de Dados Públicos & ETL

4.1 Fontes Públicas Mapeadas

Diário Oficial da União (DOU): Seção 1 (Leis Complementares, Decretos e Instruções Normativas).

Receita Federal do Brasil (RFB): Soluções de Consulta COSIT, Atos Declaratórios Executivos e Tabela de NCM/TIPI.

Comitê Gestor do IBS: Resoluções estaduais/municipais consolidadas e tabelas de alíquotas por ente federativo.

SPED & IBPT: Tabelas oficiais de alíquotas médias e correlação NCM/NBS.

4.2 Arquitetura do Pipeline ETL

[ DOU / RFB / Comitê IBS ] ──► (Scrapy / Playwright Airflow DAGs)
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │ Raw Storage (Google GCS)     │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │ Parsing AST Legal & Chunking │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │ Hybrid Embedding (BGE-M3 +   │
                       │ Sparse BM25 Indexing)        │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │ Database Storage             │
                       │ (Qdrant + PostgreSQL 16)     │
                       └──────────────┴───────────────┘


4.3 Chunking Hierárquico baseado em AST (Abstract Syntax Tree)

Modelos tradicionais que dividem arquivos por contagem de caracteres quebram a coerência de normas legais. O TaxReform AI constrói uma Árvore Sintática da Norma Legal:

$$\text{Lei} \rightarrow \text{Título} \rightarrow \text{Capítulo} \rightarrow \text{Artigo} \rightarrow \text{Parágrafo} \rightarrow \text{Inciso}$$

Cada Child Chunk herda o contexto do Parent Chunk e salva metadados estruturados para filtragem vetorial:

{
  "documento_id": "LC_XX_2024",
  "dispositivo": "Art. 18, §2º, Inciso II",
  "esfera": "SUBNACIONAL_IBS",
  "data_vigencia_inicio": "2027-01-01",
  "data_vigencia_fim": "2032-12-31",
  "ncm_relacionadas": ["2202.10.00", "2202.90.00"],
  "regime": "DIFERENCIADO_REDUCAO_60"
}


5. Recomendação de Infraestrutura no GCP e Stack da Aplicação

5.1 Avaliação do GCP (Google Cloud Platform)

O GCP é a melhor escolha de infraestrutura para o TaxReform AI por 5 motivos centrais:

Claude (Anthropic) via Vertex AI: Permite consumir o Claude 3.5 Sonnet e Haiku nativamente via API dentro da VPC corporativa e na mesma fatura GCP.

Hospedagem Serverless com Cloud Run: Ideal para contêineres FastAPI e agentes LangGraph com auto-scaling automático até zero e baixíssimo custo.

Orquestração com Cloud Composer: Apache Airflow totalmente gerenciado para agendar e monitorar as DAGs de raspagem do DOU e da RFB.

Região São Paulo (southamerica-east1): Latência inferior a 15 ms para integrar com os ERPs instalados no Brasil.

BigQuery: Data Warehouse de alta velocidade para consultas analíticas em histórico de milhões de notas fiscais simuladas.

5.2 Stack Completa da Aplicação (App Stack)

┌─────────────────────────────────────────────────────────────────────────┐
│                                FRONTEND                                 │
│  Next.js 14 (App Router) + TailwindCSS + Shadcn UI + TanStack Query    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (HTTPS / WebSockets)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND / API                              │
│  FastAPI (Python 3.11+) + Pydantic v2 + Celery / Redis (Task Queue)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│   ORQUESTRAÇÃO MULTI-AGÊNTICA    │  │    ENGINE DETERMINÍSTICO         │
│   LangGraph / CrewAI             │  │    Python Math Sandbox           │
│   + Anthropic Claude (Vertex AI) │  │    (Cálculos de IVA / Split Pay) │
└──────────────────────────────────┘  └──────────────────────────────────┘


Componente

Tecnologia

Função no Sistema

Frontend

Next.js 14 + TailwindCSS + Shadcn UI

Interface web corporativa, dashboards de simulação e pareceres.

Backend / API

FastAPI (Python 3.11+)

API assíncrona REST/gRPC de alta performance para ERPs e web app.

Fila Assíncrona

Celery + Memorystore (Redis)

Processamento em segundo plano de planilhas com 50.000+ SKUs.

Banco Relacional

Cloud SQL (PostgreSQL 16)

Gestão de multi-tenancy, SKUs, usuários e audit logs.

Banco Vetorial

Qdrant Cloud (Marketplace GCP)

Busca híbrida (esparsa/densa) com filtros por metadados de vigência.

Data Lake

Google Cloud Storage (GCS)

Armazenamento imutável dos PDFs e HTMLs originais raspados.

6. Motor Determinístico de Cálculo & Code Sandbox

6.1 Motor de Sandbox Python para Cálculo do IVA Dual

from decimal import Decimal, ROUND_HALF_UP

class TaxCalculatorEngine:
    @staticmethod
    def calculate_transaction_2028(
        valor_base: Decimal,
        aliq_cbs: Decimal,
        aliq_ibs: Decimal,
        aliq_is: Decimal,
        split_payment_active: bool = True
    ) -> dict:
        # 1. Imposto Seletivo (IS)
        valor_is = (valor_base * aliq_is).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 2. Base do IVA Dual (CBS + IBS)
        base_iva = valor_base + valor_is
        
        # 3. Alíquotas CBS e IBS
        valor_cbs = (base_iva * aliq_cbs).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        valor_ibs = (base_iva * aliq_ibs).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        total_tributos = valor_cbs + valor_ibs + valor_is
        valor_liquido_vendedor = valor_base - (total_tributos if split_payment_active else Decimal('0.00'))
        
        return {
            "valor_base": float(valor_base),
            "valor_is": float(valor_is),
            "valor_cbs": float(valor_cbs),
            "valor_ibs": float(valor_ibs),
            "total_impostos": float(total_tributos),
            "valor_liquido_retido_split_payment": float(valor_liquido_vendedor)
        }


7. Modelagem de Banco de Dados Relacional (PostgreSQL)

-- Tabela de Produtos / SKUs dos Clientes
CREATE TABLE empresa_skus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    codigo_sku VARCHAR(64) NOT NULL,
    descricao TEXT NOT NULL,
    ncm_code VARCHAR(10) NOT NULL,
    nbs_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Regras Fiscais Consolidadas
CREATE TABLE regras_tributarias_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncm_code VARCHAR(10) NOT NULL,
    ano_vigencia INT NOT NULL,
    aliquota_cbs NUMERIC(5,4) NOT NULL,
    aliquota_ibs NUMERIC(5,4) NOT NULL,
    incide_is BOOLEAN DEFAULT FALSE,
    aliquota_is NUMERIC(5,4) DEFAULT 0.0000,
    regime_especial VARCHAR(64) DEFAULT 'GERAL',
    dispositivo_legal_ref TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit Trail de Pareceres Emitidos
CREATE TABLE pareceres_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    prompt_consulta TEXT NOT NULL,
    contexto_recuperado_ids JSONB NOT NULL,
    payload_calculo_json JSONB NOT NULL,
    resposta_parecer_md TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


8. Especificação de API para Integração com ERPs (SAP, TOTVS)

8.1 Endpoint /v1/tax/simulate (POST)

Request Body:

{
  "tenant_id": "c39a8281-9b1a-4d2c-8822-123456789abc",
  "ano_operacao": 2027,
  "operacao_tipo": "VENDA_ESTADUAL_B2B",
  "itens": [
    {
      "sku": "PROD-1092",
      "ncm": "8471.30.12",
      "quantidade": 10,
      "valor_unitario": 2500.00,
      "uf_origem": "SP",
      "uf_destino": "MG"
    }
  ]
}


Response (200 OK):

{
  "status": "SUCCESS",
  "ano_operacao": 2027,
  "resumo_financeiro": {
    "valor_bruto_total": 25000.00,
    "total_cbs": 2200.00,
    "total_ibs": 4425.00,
    "total_is": 0.00,
    "valor_liquido_projetado_split_payment": 18375.00
  },
  "itens_detalhados": [
    {
      "sku": "PROD-1092",
      "ncm": "8471.30.12",
      "aliquotas_aplicadas": {
        "cbs_percentual": 8.80,
        "ibs_percentual": 17.70,
        "is_percentual": 0.00
      },
      "fundamentacao_legal": "Lei Complementar nº XX/2024, Art. 5º, Inciso I"
    }
  ]
}


9. Modelo de Negócios (SaaS Enterprise)

┌─────────────────────────────────────────────────────────────────────────┐
│                           PLANOS E PRECIFICAÇÃO                         │
├───────────────────┬─────────────────────────────┬───────────────────────┤
│ PLANO             │ RECURSOS                    │ VALOR MENSAL          │
├───────────────────┼─────────────────────────────┼───────────────────────┤
│ Professional      │ 3 usuários                  │ R$ 2.500 /mês         │
│                   │ Simulador manual NCM        │                       │
│                   │ Pareceres ilimitados        │                       │
├───────────────────┼─────────────────────────────┼───────────────────────┤
│ Business          │ 10 usuários                 │ R$ 7.500 /mês         │
│                   │ Upload de até 10.000 SKUs   │                       │
│                   │ Simulador de Split Payment  │                       │
├───────────────────┼─────────────────────────────┼───────────────────────┤
│ Enterprise        │ Usuários ilimitados         │ R$ 18.000 a           │
│                   │ API dedicada para ERP       │ R$ 45.000 /mês        │
│                   │ RAG em banco isolado (VPC)  │                       │
└─────────────────────────────────────────────────────────────────────────┘

