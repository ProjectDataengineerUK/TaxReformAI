import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useApiKey } from "./useApiKey";

describe("useApiKey", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("começa vazio quando não há nada no localStorage", () => {
    const { result } = renderHook(() => useApiKey());
    expect(result.current.apiKey).toBe("");
  });

  it("persiste a chave no localStorage ao chamar setApiKey", () => {
    const { result } = renderHook(() => useApiKey());

    act(() => {
      result.current.setApiKey("minha-chave");
    });

    expect(result.current.apiKey).toBe("minha-chave");
    expect(window.localStorage.getItem("taxreform:api-key")).toBe("minha-chave");
  });

  it("carrega a chave já salva no localStorage ao montar", () => {
    window.localStorage.setItem("taxreform:api-key", "chave-existente");

    const { result } = renderHook(() => useApiKey());

    expect(result.current.apiKey).toBe("chave-existente");
  });
});
