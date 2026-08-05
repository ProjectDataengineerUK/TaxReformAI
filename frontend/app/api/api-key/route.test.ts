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
  });

  it("devolve 401 sem sessão válida", async () => {
    authMock.mockResolvedValue(null);

    const resposta = await GET();

    expect(resposta.status).toBe(401);
  });

  it("devolve 503 quando FRONTEND_API_KEY não está configurada, mesmo com sessão válida", async () => {
    authMock.mockResolvedValue({ user: { email: "pessoa@empresa.com" } } as never);

    const resposta = await GET();

    expect(resposta.status).toBe(503);
  });

  it("devolve a chave real para sessão válida com FRONTEND_API_KEY configurada", async () => {
    authMock.mockResolvedValue({ user: { email: "pessoa@empresa.com" } } as never);
    process.env.FRONTEND_API_KEY = "chave-real-de-producao";

    const resposta = await GET();
    const corpo = (await resposta.json()) as { apiKey: string };

    expect(resposta.status).toBe(200);
    expect(corpo.apiKey).toBe("chave-real-de-producao");
  });
});
