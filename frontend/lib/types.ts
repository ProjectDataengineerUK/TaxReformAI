// Espelha api/schemas_simulate.py e api/schemas_query.py — mesmos nomes de campo

export interface ItemSimulacao {
  sku: string;
  ncm: string;
  quantidade: number;
  valor_unitario: string; // Decimal serializado como string pelo FastAPI/Pydantic
  uf_origem: string;
  uf_destino: string;
}

export interface PayloadSimulacao {
  tenant_id: string;
  ano_operacao: number;
  operacao_tipo: string;
  itens: ItemSimulacao[];
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

export interface RespostaSimulacao {
  status: string;
  ano_operacao: number;
  resumo_financeiro: ResumoFinanceiro;
  itens_detalhados: ItemDetalhado[];
}

export interface PayloadConsulta {
  texto_consulta: string;
  ano_operacao: number;
  valor_base: string;
}

export interface TransicaoResposta {
  no: string;
  resumo_output: string;
}

export interface RespostaConsulta {
  parecer_final: string;
  valor_liquido: string;
  fonte_legal: string;
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
