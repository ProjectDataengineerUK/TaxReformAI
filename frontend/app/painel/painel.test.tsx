import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiKeyProvider } from "@/hooks/useApiKey";
import { ApiError } from "@/lib/api-client";
import type { RespostaCusto, RespostaScorecard, RespostaStatus } from "@/lib/types";

import PainelPage from "./page";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
  return { ...actual, apiGet: vi.fn() };
});

import { apiGet } from "@/lib/api-client";

const STATUS_FAKE: RespostaStatus = {
  recursos: [
    { recurso: "API", nivel: "verde", detalhe: "respondendo" },
    { recurso: "Cloud SQL", nivel: "amarelo", detalhe: "72/100 conexões (72%)" },
  ],
};

const SCORECARD_FAKE: RespostaScorecard = {
  mlops: { framework: "Google MLOps MM", nota: 2, justificativa: "j1" },
  dataops: { framework: "DataOps MM", nota: 3, justificativa: "j2" },
  llmops: { framework: "Composto próprio", nota: 4, justificativa: "j3" },
  seguranca: {
    framework: "OWASP + NIST CSF",
    nota: 4,
    justificativa: "j4",
    por_funcao: { Identify: 4, Protect: 4, Detect: 3, Respond: 3, Recover: 3 },
  },
  finops_achados: [
    { achado: "Cloud SQL esgotou pool", fonte: "FILA_ASSINCRONA", oportunidade: "upgrade de tier" },
  ],
};

const CUSTO_FAKE: RespostaCusto = {
  periodo_dias: 30,
  custo_token_total_usd: 12.5,
  custo_por_modelo: [
    { modelo: "claude-sonnet-5", tokens_entrada: 1000, tokens_saida: 500, custo_usd: 10.5 },
  ],
  custo_infra_total_usd: 40.0,
  custo_infra_por_servico: [{ servico: "Cloud Run", custo_usd: 40.0 }],
  alertas_limiar: ["Cloud SQL: gasto subiu 25% na última semana"],
};

function renderPainel() {
  const client = new QueryClient();
  window.localStorage.setItem("taxreform:api-key", "chave-teste");
  return render(
    <QueryClientProvider client={client}>
      <ApiKeyProvider>
        <PainelPage />
      </ApiKeyProvider>
    </QueryClientProvider>,
  );
}

describe("PainelPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(apiGet).mockReset();
  });

  it("aba Diagrama é a inicial e mostra os recursos coloridos por status", async () => {
    vi.mocked(apiGet).mockResolvedValue(STATUS_FAKE);

    renderPainel();

    await waitFor(() => expect(screen.getAllByText("Cloud SQL")[0]).toBeInTheDocument());
    expect(apiGet).toHaveBeenCalledWith("/v1/observabilidade/status", "chave-teste");
  });

  it("troca para a aba Sentinela e lista o status em tabela", async () => {
    vi.mocked(apiGet).mockResolvedValue(STATUS_FAKE);

    renderPainel();
    await userEvent.click(screen.getByRole("tab", { name: "Sentinela" }));

    await waitFor(() => expect(screen.getByText("amarelo")).toBeInTheDocument());
    expect(screen.getByText("72/100 conexões (72%)")).toBeInTheDocument();
  });

  it("troca para a aba Maturidade e mostra as 3 notas", async () => {
    // A aba Diagrama (inicial) já dispara /status antes do clique — roteia
    // por path, um mock único devolvendo o scorecard pra tudo quebra o
    // DiagramaTab (achado real deste teste, não só cautela).
    vi.mocked(apiGet).mockImplementation((path: string) =>
      path === "/v1/observabilidade/scorecard"
        ? Promise.resolve(SCORECARD_FAKE)
        : Promise.resolve(STATUS_FAKE),
    );

    renderPainel();
    await userEvent.click(screen.getByRole("tab", { name: "Maturidade" }));

    await waitFor(() => expect(screen.getByText("MLOps")).toBeInTheDocument());
    expect(screen.getByText("2/5")).toBeInTheDocument();
    expect(screen.getByText("3/5", { exact: false })).toBeInTheDocument();
  });

  it("troca para a aba Segurança e mostra a nota por função do NIST CSF", async () => {
    vi.mocked(apiGet).mockImplementation((path: string) =>
      path === "/v1/observabilidade/scorecard"
        ? Promise.resolve(SCORECARD_FAKE)
        : Promise.resolve(STATUS_FAKE),
    );

    renderPainel();
    await userEvent.click(screen.getByRole("tab", { name: "Segurança" }));

    await waitFor(() => expect(screen.getByText("4/5")).toBeInTheDocument());
    expect(screen.getByText("Detect")).toBeInTheDocument();
  });

  it("troca para a aba Custo & FinOps e mostra custo de token, infra e achados", async () => {
    vi.mocked(apiGet).mockImplementation((path: string) => {
      if (path === "/v1/observabilidade/custo") return Promise.resolve(CUSTO_FAKE);
      if (path === "/v1/observabilidade/scorecard") return Promise.resolve(SCORECARD_FAKE);
      return Promise.resolve(STATUS_FAKE);
    });

    renderPainel();
    await userEvent.click(screen.getByRole("tab", { name: "Custo & FinOps" }));

    await waitFor(() => expect(screen.getByText(/US\$\s*12,50/)).toBeInTheDocument());
    expect(screen.getByText(/gasto subiu 25%/)).toBeInTheDocument();
    expect(screen.getByText("Cloud SQL esgotou pool")).toBeInTheDocument();
  });

  it("exibe erro claro quando o status falha ao carregar", async () => {
    vi.mocked(apiGet).mockRejectedValue(new ApiError(503, "Cloud SQL não configurado"));

    renderPainel();

    await waitFor(() =>
      expect(screen.getByText(/Não foi possível carregar o status/)).toBeInTheDocument(),
    );
  });
});
