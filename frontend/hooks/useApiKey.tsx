"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "taxreform:api-key";
// Placeholder de dev local/manual — nunca usado quando o auto-fetch de
// /api/api-key funciona (ver achado abaixo). Sem UI para o usuário digitar
// um tenant manualmente, mantém o valor histórico do fallback.
const TENANT_FALLBACK = "frontend-demo";

interface ApiKeyContextValue {
  apiKey: string;
  tenantId: string;
  setApiKey: (value: string) => void;
}

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>(TENANT_FALLBACK);

  useEffect(() => {
    let cancelado = false;

    // Achado real (2026-08-05): a chave deixa de ser 100% manual — um
    // usuário com sessão válida (login Google, mesma allowlist que já
    // protege /simulador e /consulta via middleware) recebe a chave (e o
    // tenant_id correspondente — /v1/tax/simulate reprova com 403 se o
    // tenant_id do corpo não bater com o da API key) automaticamente de um
    // endpoint interno server-side (app/api/api-key/route.ts), que nunca
    // expõe FRONTEND_API_KEY/FRONTEND_TENANT_ID ao navegador. localStorage
    // continua como fallback manual — sem sessão (página pública/login),
    // sem as env vars configuradas (dev local), ou rede indisponível, cai
    // para o fluxo antigo via ApiKeyBar (tenant_id fica no placeholder).
    async function carregar() {
      try {
        const resposta = await fetch("/api/api-key");
        if (!cancelado && resposta.ok) {
          const dados = (await resposta.json()) as { apiKey: string; tenantId: string };
          setApiKeyState(dados.apiKey);
          setTenantId(dados.tenantId);
          return;
        }
      } catch {
        // endpoint indisponível ou ambiente sem fetch relativo (ex: testes) —
        // cai para o fallback de localStorage abaixo, sem propagar erro
      }

      if (!cancelado) {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        if (stored) setApiKeyState(stored);
      }
    }

    carregar();
    return () => {
      cancelado = true;
    };
  }, []);

  const setApiKey = useCallback((value: string) => {
    window.localStorage.setItem(STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  return (
    <ApiKeyContext.Provider value={{ apiKey, tenantId, setApiKey }}>
      {children}
    </ApiKeyContext.Provider>
  );
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
