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
    };
    vi.mocked(apiPost).mockResolvedValueOnce(respostaFake);

    renderComQueryClient();
    await userEvent.click(screen.getByRole("button", { name: /simular/i }));

    await waitFor(() => expect(screen.getByText(/R\$ 990.00/)).toBeInTheDocument());
    expect(screen.getByText(/PROD-1/)).toBeInTheDocument();
    expect(screen.getByText(/fase de teste 2026/)).toBeInTheDocument();
  });

  it("AT-002: exibe mensagem clara quando a API retorna 401", async () => {
    vi.mocked(apiPost).mockRejectedValueOnce(new ApiError(401, "API key inválida ou ausente"));

    renderComQueryClient();
    await userEvent.click(screen.getByRole("button", { name: /simular/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/configure-a acima/i),
    );
  });
});
