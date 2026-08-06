import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import { ApiKeyProvider } from "@/hooks/useApiKey";

import ConsultaPage from "./page";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
  return { ...actual, apiPost: vi.fn() };
});

import { apiPost } from "@/lib/api-client";

function renderComQueryClient() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <ApiKeyProvider>
        <ConsultaPage />
      </ApiKeyProvider>
    </QueryClientProvider>,
  );
}

describe("ConsultaPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(apiPost).mockReset();
  });

  it("AT-003: erro 422 (alíquota indisponível) é exibido sem parecer inventado", async () => {
    vi.mocked(apiPost).mockRejectedValueOnce(
      new ApiError(422, "Alíquota não disponível para a fase PLENO_CBS_IS_2027"),
    );

    renderComQueryClient();
    await userEvent.type(
      screen.getByLabelText(/sua pergunta/i),
      "quanto de imposto incide em 2028?",
    );
    await userEvent.click(screen.getByRole("button", { name: /consultar/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/Alíquota não disponível/),
    );
    expect(screen.queryByText(/Parecer de Simulação/i)).not.toBeInTheDocument();
  });

  it("AT-002: erro 401 é exibido com mensagem clara", async () => {
    vi.mocked(apiPost).mockRejectedValueOnce(new ApiError(401, "API key inválida ou ausente"));

    renderComQueryClient();
    await userEvent.type(screen.getByLabelText(/sua pergunta/i), "teste");
    await userEvent.click(screen.getByRole("button", { name: /consultar/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/configure-a acima/i),
    );
  });

  it("happy path exibe o parecer e o histórico", async () => {
    vi.mocked(apiPost).mockResolvedValueOnce({
      parecer_final: "## Parecer de Simulação Tributária\n\nTexto do parecer",
      resultado_simulacao: {
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
        itens_regime_vigente: [],
        fonte_legal_fase: "fase de teste 2026",
      },
      historico: [{ no: "classificador", resumo_output: "intencao=SIMULACAO_TRIBUTARIA" }],
    });

    renderComQueryClient();
    await userEvent.type(screen.getByLabelText(/sua pergunta/i), "teste");
    await userEvent.click(screen.getByRole("button", { name: /consultar/i }));

    await waitFor(() => expect(screen.getByText(/Texto do parecer/)).toBeInTheDocument());
    expect(screen.getByText(/classificador/)).toBeInTheDocument();
  });
});
