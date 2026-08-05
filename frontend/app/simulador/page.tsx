"use client";

import { useMutation } from "@tanstack/react-query";

import { ErrorBanner } from "@/components/ErrorBanner";
import { ResultadoSimulacao } from "@/components/ResultadoSimulacao";
import { SimuladorForm } from "@/components/SimuladorForm";
import { useApiKey } from "@/hooks/useApiKey";
import { ApiError, apiPost } from "@/lib/api-client";
import type { PayloadSimulacao, RespostaSimulacao } from "@/lib/types";

export default function SimuladorPage() {
  const { apiKey, tenantId } = useApiKey();
  const mutation = useMutation<RespostaSimulacao, ApiError, PayloadSimulacao>({
    mutationFn: (payload) => apiPost<RespostaSimulacao>("/v1/tax/simulate", payload, apiKey),
  });

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-xl font-bold">Simulador Estruturado (por NCM)</h1>
      <SimuladorForm
        onSubmit={(payload) => mutation.mutate(payload)}
        isPending={mutation.isPending}
        tenantId={tenantId}
      />
      {mutation.isError && <ErrorBanner error={mutation.error} />}
      {mutation.isSuccess && <ResultadoSimulacao resposta={mutation.data} />}
    </div>
  );
}
