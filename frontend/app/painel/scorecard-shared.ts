"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiKey } from "@/hooks/useApiKey";
import { apiGet } from "@/lib/api-client";
import type { RespostaScorecard } from "@/lib/types";

// Scorecard é YAML versionado no repo, lido uma vez por deploy (Decision 5
// do DESIGN) — staleTime longo, não faz sentido reconsultar a cada foco de
// aba.
export function useScorecard() {
  const { apiKey } = useApiKey();
  return useQuery({
    queryKey: ["observabilidade-scorecard"],
    queryFn: () => apiGet<RespostaScorecard>("/v1/observabilidade/scorecard", apiKey),
    enabled: Boolean(apiKey),
    staleTime: 5 * 60_000,
  });
}
