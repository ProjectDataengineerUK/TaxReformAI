import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({
  auth: vi.fn(),
}));

import { auth } from "@/lib/auth";

import { GET } from "./route";

describe("GET /api/api-key", () => {
  const authMock = vi.mocked(auth);

  beforeEach(() => {
    authMock.mockReset();
    delete process.env.FRONTEND_API_KEY;
    delete process.env.FRONTEND_TENANT_ID;
  });

  it("devolve 401 sem sessão válida", async () => {
    authMock.mockResolvedValue(null);

    const resposta = await GET();

    expect(resposta.status).toBe(401);
  });

  it("devolve 503 quando FRONTEND_API_KEY não está configurada, mesmo com sessão válida", async () => {
    authMock.mockResolvedValue({ user: { email: "pessoa@empresa.com" } } as never);
    process.env.FRONTEND_TENANT_ID = "minha-empresa";

    const resposta = await GET();

    expect(resposta.status).toBe(503);
  });

  it("devolve 503 quando FRONTEND_TENANT_ID não está configurada, mesmo com FRONTEND_API_KEY presente — achado real: /v1/tax/simulate reprova (403) se tenant_id não bater com a chave", async () => {
    authMock.mockResolvedValue({ user: { email: "pessoa@empresa.com" } } as never);
    process.env.FRONTEND_API_KEY = "chave-real-de-producao";

    const resposta = await GET();

    expect(resposta.status).toBe(503);
  });

  it("devolve a chave e o tenant reais para sessão válida com as duas env vars configuradas", async () => {
    authMock.mockResolvedValue({ user: { email: "pessoa@empresa.com" } } as never);
    process.env.FRONTEND_API_KEY = "chave-real-de-producao";
    process.env.FRONTEND_TENANT_ID = "minha-empresa";

    const resposta = await GET();
    const corpo = (await resposta.json()) as { apiKey: string; tenantId: string };

    expect(resposta.status).toBe(200);
    expect(corpo.apiKey).toBe("chave-real-de-producao");
    expect(corpo.tenantId).toBe("minha-empresa");
  });
});
