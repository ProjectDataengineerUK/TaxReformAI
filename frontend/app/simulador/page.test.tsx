import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import type { RespostaSimulacao } from "@/lib/types";
import { ApiKeyProvider } from "@/hooks/useApiKey";

import SimuladorPage from "./page";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
  return { ...actual, apiPost: vi.fn() };
});

import { apiPost } from "@/lib/api-client";

const REGIME_VIGENTE_FAKE = {
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
};

function renderComQueryClient() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <ApiKeyProvider>
        <SimuladorPage />
      </ApiKeyProvider>
    </QueryClientProvider>,
  );
}

describe("SimuladorPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(apiPost).mockReset();
  });

  it("AT-001: happy path exibe resumo_financeiro e itens_detalhados reais", async () => {
    const respostaFake: RespostaSimulacao = {
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
          ncm: "1234.56.78",
          aliquotas_aplicadas: { cbs_percentual: "0.900", ibs_percentual: "0.100", is_percentual: "0" },
          fundamentacao_legal: "fase de teste 2026",
        },
      ],
      regime_vigente: REGIME_VIGENTE_FAKE,
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
      fonte_legal_fase: "fase de teste 2026",
    };
    vi.mocked(apiPost).mockResolvedValueOnce(respostaFake);

    renderComQueryClient();
    await userEvent.click(screen.getByRole("button", { name: /simular/i }));

    await waitFor(() => expect(screen.getAllByText(/R\$ 990.00/).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/PROD-1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/fase de teste 2026/).length).toBeGreaterThan(0);
  });

  it("AT-002: exibe mensagem clara quando a API retorna 401", async () => {
    vi.mocked(apiPost).mockRejectedValueOnce(new ApiError(401, "API key inválida ou ausente"));

    renderComQueryClient();
    await userEvent.click(screen.getByRole("button", { name: /simular/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/configure-a acima/i),
    );
  });

  it("AT-003: usa o tenant_id real do auto-fetch, não mais um valor fixo — achado real: 'frontend-demo' hardcoded divergia da API key e /v1/tax/simulate reprovava com 403", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ apiKey: "chave-real", tenantId: "minha-empresa" }),
      }),
    );

    const respostaFake: RespostaSimulacao = {
      status: "SUCCESS",
      ano_operacao: 2026,
      resumo_financeiro: {
        valor_bruto_total: "1000.00",
        total_cbs: "9.00",
        total_ibs: "1.00",
        total_is: "0.00",
        valor_liquido_projetado_split_payment: "990.00",
      },
      itens_detalhados: [],
      regime_vigente: REGIME_VIGENTE_FAKE,
      itens_regime_vigente: [],
      fonte_legal_fase: "fase de teste 2026",
    };
    vi.mocked(apiPost).mockResolvedValueOnce(respostaFake);

    renderComQueryClient();
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/api-key"));
    await userEvent.click(screen.getByRole("button", { name: /simular/i }));

    await waitFor(() => expect(apiPost).toHaveBeenCalled());
    const payload = vi.mocked(apiPost).mock.calls[0][1] as { tenant_id: string };
    expect(payload.tenant_id).toBe("minha-empresa");

    vi.unstubAllGlobals();
  });
});
