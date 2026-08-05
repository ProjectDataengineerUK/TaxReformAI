import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiKeyProvider, useApiKey } from "./useApiKey";

function wrapper({ children }: { children: ReactNode }) {
  return <ApiKeyProvider>{children}</ApiKeyProvider>;
}

describe("useApiKey", () => {
  beforeEach(() => {
    window.localStorage.clear();
    // Simula /api/api-key indisponível (sem sessão/sem FRONTEND_API_KEY) —
    // todo teste abaixo, exceto o de auto-fetch, exercita o fallback manual.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("começa vazio quando não há nada no localStorage nem sessão automática", async () => {
    const { result } = renderHook(() => useApiKey(), { wrapper });
    await waitFor(() => expect(result.current.apiKey).toBe(""));
  });

  it("persiste a chave no localStorage ao chamar setApiKey", async () => {
    const { result } = renderHook(() => useApiKey(), { wrapper });

    // Espera o fetch automático (401 simulado) assentar antes do setApiKey
    // manual, para não sobrepor um ato do usuário com uma resposta pendente.
    await waitFor(() => expect(result.current.apiKey).toBe(""));

    act(() => {
      result.current.setApiKey("minha-chave");
    });

    expect(result.current.apiKey).toBe("minha-chave");
    expect(window.localStorage.getItem("taxreform:api-key")).toBe("minha-chave");
  });

  it("carrega a chave já salva no localStorage ao montar, se o fetch automático falhar", async () => {
    window.localStorage.setItem("taxreform:api-key", "chave-existente");

    const { result } = renderHook(() => useApiKey(), { wrapper });

    await waitFor(() => expect(result.current.apiKey).toBe("chave-existente"));
  });

  it("busca a chave automaticamente de /api/api-key quando disponível (usuário logado)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ apiKey: "chave-automatica-via-login" }),
      }),
    );
    window.localStorage.setItem("taxreform:api-key", "chave-manual-antiga");

    const { result } = renderHook(() => useApiKey(), { wrapper });

    // A chave automática vence a manual antiga guardada localmente.
    await waitFor(() => expect(result.current.apiKey).toBe("chave-automatica-via-login"));
  });

  it("sincroniza a chave entre dois consumidores diferentes sem reload — achado real: ApiKeyBar salvava, o formulário nunca via a chave nova", async () => {
    function Writer() {
      const { setApiKey } = useApiKey();
      return <button onClick={() => setApiKey("chave-sincronizada")}>salvar</button>;
    }
    function Reader() {
      const { apiKey } = useApiKey();
      return <span data-testid="leitor">{apiKey || "(vazio)"}</span>;
    }

    render(
      <ApiKeyProvider>
        <Writer />
        <Reader />
      </ApiKeyProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("leitor").textContent).toBe("(vazio)"));
    fireEvent.click(screen.getByText("salvar"));
    expect(screen.getByTestId("leitor").textContent).toBe("chave-sincronizada");
  });
});
