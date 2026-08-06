// Espelha api/schemas_simulate.py e api/schemas_query.py — mesmos nomes de campo

export interface ItemSimulacao {
  sku: string;
  ncm?: string | null;
  quantidade: number;
  valor_unitario: string; // Decimal serializado como string pelo FastAPI/Pydantic
  uf_origem: string;
  uf_destino: string;
  // Decide ICMS x ISS no regime atual (bases mutuamente exclusivas) — default
  // do backend é MERCADORIA quando ausente.
  natureza?: "MERCADORIA" | "SERVICO";
}

export interface PayloadSimulacao {
  tenant_id: string;
  ano_operacao: number;
  operacao_tipo: string;
  itens: ItemSimulacao[];
  // Ausente = "não informado", nunca um default — sem ele, PIS/COFINS
  // simplesmente não é calculado (RegimeApuracao: NAO_CUMULATIVO | CUMULATIVO).
  regime_apuracao?: string | null;
}

export interface AliquotasAplicadas {
  cbs_percentual: string;
  ibs_percentual: string;
  is_percentual: string;
}

export interface ItemDetalhado {
  sku: string;
  ncm: string;
  aliquotas_aplicadas: AliquotasAplicadas;
  fundamentacao_legal: string;
}

export interface ResumoFinanceiro {
  valor_bruto_total: string;
  total_cbs: string;
  total_ibs: string;
  total_is: string;
  valor_liquido_projetado_split_payment: string;
}

// Comparação com o regime atual (PIS/COFINS, ICMS, ISS, IPI) — a API já
// calculava e devolvia isso desde SCHEMA_POSTGRESQL/IPI_TIPI_MOTOR_CALCULO,
// mas nenhuma tela exibia (COMPARATIVO_REGIME_ATUAL_IVA_DUAL). `null` num
// campo significa "não calculado" (ex: PIS/COFINS sem regime_apuracao
// informado), nunca "zero" — sempre exibir como tal, nunca omitir.
export interface RegimeVigenteResumo {
  regime_apuracao: string | null;
  total_pis: string | null;
  total_cofins: string | null;
  total_icms_interestadual: string;
  total_icms_interno: string;
  total_icms_interno_fecp: string;
  total_iss_piso: string;
  total_iss_teto: string;
  total_ipi: string | null;
  tributos_nao_calculados: string[];
}

export interface ItemRegimeVigente {
  sku: string;
  natureza: string;
  icms_interestadual_percentual: string | null;
  fonte_legal_icms: string | null;
  icms_interno_percentual: string | null;
  fonte_legal_icms_interno: string | null;
  icms_interno_fecp_percentual: string | null;
  fonte_legal_icms_interno_fecp: string | null;
  iss_piso_percentual: string | null;
  iss_teto_percentual: string | null;
  fonte_legal_iss_piso: string | null;
  fonte_legal_iss_teto: string | null;
  pis_percentual: string | null;
  cofins_percentual: string | null;
  fonte_legal_pis: string | null;
  fonte_legal_cofins: string | null;
  ipi_percentual: string | null;
  fonte_legal_ipi: string | null;
  ipi_situacao: string;
}

export interface RespostaSimulacao {
  status: string;
  ano_operacao: number;
  resumo_financeiro: ResumoFinanceiro;
  itens_detalhados: ItemDetalhado[];
  regime_vigente: RegimeVigenteResumo;
  itens_regime_vigente: ItemRegimeVigente[];
  // Citação da fase vigente para CBS/IBS/IS — igual para todos os itens de
  // um mesmo ano_operacao.
  fonte_legal_fase: string;
}

export interface PayloadConsulta {
  texto_consulta: string;
  ano_operacao: number;
  // Mesmo shape de item que PayloadSimulacao — valor_base não existe mais
  // como campo manual, é derivado da soma dos itens pelo backend.
  itens: ItemSimulacao[];
  regime_apuracao?: string | null;
}

export interface TransicaoResposta {
  no: string;
  resumo_output: string;
}

export interface RespostaConsulta {
  parecer_final: string;
  // Compõe o MESMO schema que /simulador devolve — o mesmo componente
  // ComparativoRegime serve as duas telas sem adaptação de shape.
  resultado_simulacao: RespostaSimulacao;
  historico: TransicaoResposta[];
}

export type NivelStatus = "verde" | "amarelo" | "vermelho";

export interface RecursoStatus {
  recurso: string;
  nivel: NivelStatus;
  detalhe: string;
}

export interface RespostaStatus {
  recursos: RecursoStatus[];
}

export interface CustoPorModelo {
  modelo: string;
  tokens_entrada: number;
  tokens_saida: number;
  custo_usd: number;
}

export interface CustoInfraPorServico {
  servico: string;
  custo_usd: number;
}

export interface RespostaCusto {
  periodo_dias: number;
  custo_token_total_usd: number;
  custo_por_modelo: CustoPorModelo[];
  custo_infra_total_usd: number;
  custo_infra_por_servico: CustoInfraPorServico[];
  alertas_limiar: string[];
}

export interface EixoMaturidade {
  framework: string;
  nota: number;
  justificativa: string;
  por_funcao?: Record<string, number>;
}

export interface AchadoFinOps {
  achado: string;
  fonte: string;
  oportunidade: string;
}

export interface RespostaScorecard {
  mlops: EixoMaturidade;
  dataops: EixoMaturidade;
  llmops: EixoMaturidade;
  seguranca: EixoMaturidade;
  finops_achados: AchadoFinOps[];
}
