import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ComparativoRegime } from "@/components/ComparativoRegime";
import type { RespostaSimulacao } from "@/lib/types";

function respostaFake(overrides: Partial<RespostaSimulacao> = {}): RespostaSimulacao {
  return {
    status: "SUCCESS",
    ano_operacao: 2026,
    resumo_financeiro: {
      valor_bruto_total: "1000.00",
      total_cbs: "9.00",
      total_ibs: "1.00",
      total_is: "0.00",
      valor_liquido_projetado_split_payment: "990.00",
    },
    itens_detalhados: [
      {
        sku: "PROD-1",
        ncm: "99999999",
        aliquotas_aplicadas: { cbs_percentual: "0.900", ibs_percentual: "0.100", is_percentual: "0" },
        fundamentacao_legal: "fase de teste 2026",
      },
    ],
    regime_vigente: {
      regime_apuracao: null,
      total_pis: null,
      total_cofins: null,
      total_icms_interestadual: "0.00",
      total_icms_interno: "180.00",
      total_icms_interno_fecp: "0.00",
      total_iss_piso: "0.00",
      total_iss_teto: "0.00",
      total_ipi: null,
      tributos_nao_calculados: ["PIS", "COFINS", "IPI"],
    },
    itens_regime_vigente: [
      {
        sku: "PROD-1",
        natureza: "MERCADORIA",
        icms_interestadual_percentual: null,
        fonte_legal_icms: null,
        icms_interno_percentual: "18.00",
        fonte_legal_icms_interno: "Art. 52, I, do RICMS/SP",
        icms_interno_fecp_percentual: null,
        fonte_legal_icms_interno_fecp: null,
        iss_piso_percentual: null,
        iss_teto_percentual: null,
        fonte_legal_iss_piso: null,
        fonte_legal_iss_teto: null,
        pis_percentual: null,
        cofins_percentual: null,
        fonte_legal_pis: null,
        fonte_legal_cofins: null,
        ipi_percentual: null,
        fonte_legal_ipi: null,
        ipi_situacao: "CONSULTA_INDISPONIVEL",
      },
    ],
    fonte_legal_fase: "LCP 214/2025, arts. 343 e 346 — fase de teste 2026",
    ...overrides,
  };
}

describe("ComparativoRegime", () => {
  it("exibe os totais agregados do regime atual e do IVA Dual", () => {
    render(<ComparativoRegime resposta={respostaFake()} />);

    expect(screen.getByText("R$ 180.00")).toBeInTheDocument();
    expect(screen.getByText(/R\$ 9.00/)).toBeInTheDocument();
    expect(screen.getByText(/R\$ 990.00/)).toBeInTheDocument();
  });

  it('declara tributo não calculado explicitamente, nunca omite a linha', () => {
    render(<ComparativoRegime resposta={respostaFake()} />);

    const naoCalculados = screen.getAllByText("não calculado");
    // PIS, COFINS e IPI (agregados) — 3 linhas, nunca omitidas.
    expect(naoCalculados.length).toBeGreaterThanOrEqual(3);
  });

  it("lista os tributos não calculados do escopo", () => {
    render(<ComparativoRegime resposta={respostaFake()} />);

    expect(screen.getByText(/Não calculados: PIS, COFINS, IPI/)).toBeInTheDocument();
  });

  it("renderiza a comparação por item com sku e ncm", () => {
    render(<ComparativoRegime resposta={respostaFake()} />);

    expect(screen.getByText(/PROD-1/)).toBeInTheDocument();
    expect(screen.getByText(/NCM 99999999/)).toBeInTheDocument();
  });

  it("cita a fonte legal da fase", () => {
    render(<ComparativoRegime resposta={respostaFake()} />);

    expect(screen.getByText(/LCP 214\/2025, arts. 343 e 346/)).toBeInTheDocument();
  });
});
