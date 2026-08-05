"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "taxreform:api-key";

interface ApiKeyContextValue {
  apiKey: string;
  setApiKey: (value: string) => void;
}

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setApiKeyState(stored);
  }, []);

  const setApiKey = useCallback((value: string) => {
    window.localStorage.setItem(STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  return <ApiKeyContext.Provider value={{ apiKey, setApiKey }}>{children}</ApiKeyContext.Provider>;
}

export function useApiKey(): ApiKeyContextValue {
  // Achado real (2026-08-05): antes deste Context, cada componente que
  // chamava useApiKey() tinha sua PRÓPRIA cópia de estado (useState local +
  // localStorage como único canal de sincronização) — salvar a chave na
  // ApiKeyBar nunca propagava para a cópia já montada em simulador/page.tsx
  // ou consulta/page.tsx, exigindo um reload completo da página para o
  // formulário "ver" a chave recém-salva. Context garante uma única fonte
  // de verdade em memória para toda a árvore.
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error("useApiKey precisa ser usado dentro de <ApiKeyProvider>");
  }
  return context;
}
