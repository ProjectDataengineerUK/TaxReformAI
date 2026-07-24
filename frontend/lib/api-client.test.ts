import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiPost } from "./api-client";

describe("apiPost", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("retorna o corpo tipado em caso de sucesso", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "SUCCESS" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiPost<{ status: string }>("/v1/tax/simulate", { a: 1 }, "chave");

    expect(result).toEqual({ status: "SUCCESS" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/v1/tax/simulate"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "chave" }),
      }),
    );
  });

  it("lança ApiError com status 401 quando a API retorna 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "API key inválida ou ausente" }),
      }),
    );

    await expect(apiPost("/v1/tax/simulate", {}, "")).rejects.toMatchObject({
      status: 401,
      detail: "API key inválida ou ausente",
    });
  });

  it("lança ApiError com status 422 e a mensagem de AliquotaNaoDisponivelError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        statusText: "Unprocessable Content",
        json: async () => ({
          detail: "Alíquota não disponível para a fase PLENO_CBS_IS_2027",
        }),
      }),
    );

    const error = await apiPost("/v1/tax/query", {}, "chave").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.detail).toContain("Alíquota não disponível");
  });

  it("lança ApiError com status 0 quando o fetch falha (rede)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down")),
    );

    await expect(apiPost("/v1/tax/query", {}, "chave")).rejects.toMatchObject({
      status: 0,
    });
  });
});
