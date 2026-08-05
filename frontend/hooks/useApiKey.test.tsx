import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { ApiKeyProvider, useApiKey } from "./useApiKey";

function wrapper({ children }: { children: ReactNode }) {
  return <ApiKeyProvider>{children}</ApiKeyProvider>;
}

describe("useApiKey", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("começa vazio quando não há nada no localStorage", () => {
    const { result } = renderHook(() => useApiKey(), { wrapper });
    expect(result.current.apiKey).toBe("");
  });

  it("persiste a chave no localStorage ao chamar setApiKey", () => {
    const { result } = renderHook(() => useApiKey(), { wrapper });

    act(() => {
      result.current.setApiKey("minha-chave");
    });

    expect(result.current.apiKey).toBe("minha-chave");
    expect(window.localStorage.getItem("taxreform:api-key")).toBe("minha-chave");
  });

  it("carrega a chave já salva no localStorage ao montar", () => {
    window.localStorage.setItem("taxreform:api-key", "chave-existente");

    const { result } = renderHook(() => useApiKey(), { wrapper });

    expect(result.current.apiKey).toBe("chave-existente");
  });

  it("sincroniza a chave entre dois consumidores diferentes sem reload — achado real: ApiKeyBar salvava, o formulário nunca via a chave nova", () => {
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

    expect(screen.getByTestId("leitor").textContent).toBe("(vazio)");
    fireEvent.click(screen.getByText("salvar"));
    expect(screen.getByTestId("leitor").textContent).toBe("chave-sincronizada");
  });
});
