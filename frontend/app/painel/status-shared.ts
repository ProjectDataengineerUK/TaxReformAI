"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiKey } from "@/hooks/useApiKey";
import { apiGet } from "@/lib/api-client";
import type { NivelStatus, RespostaStatus } from "@/lib/types";

export const COR_TEXTO_NIVEL: Record<NivelStatus, string> = {
  verde: "text-accent",
  amarelo: "text-amber-400",
  vermelho: "text-destructive",
};

export const COR_PONTO_NIVEL: Record<NivelStatus, string> = {
  verde: "bg-accent",
  amarelo: "bg-amber-400",
  vermelho: "bg-destructive",
};

export const COR_BORDA_NIVEL: Record<NivelStatus, string> = {
  verde: "border-accent",
  amarelo: "border-amber-400",
  vermelho: "border-destructive",
};

// Cache de 60s no backend (mesma janela) — staleTime evita re-render/pedido
// duplicado só porque duas abas diferentes montam o mesmo useQuery.
export function useStatusObservabilidade() {
  const { apiKey } = useApiKey();
  return useQuery({
    queryKey: ["observabilidade-status"],
    queryFn: () => apiGet<RespostaStatus>("/v1/observabilidade/status", apiKey),
    enabled: Boolean(apiKey),
    staleTime: 60_000,
  });
}
