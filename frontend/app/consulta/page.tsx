"use client";

import { useMutation } from "@tanstack/react-query";

import { ConsultaForm } from "@/components/ConsultaForm";
import { ErrorBanner } from "@/components/ErrorBanner";
import { ParecerMarkdown } from "@/components/ParecerMarkdown";
import { useApiKey } from "@/hooks/useApiKey";
import { ApiError, apiPost } from "@/lib/api-client";
import type { PayloadConsulta, RespostaConsulta } from "@/lib/types";

export default function ConsultaPage() {
  const { apiKey } = useApiKey();
  const mutation = useMutation<RespostaConsulta, ApiError, PayloadConsulta>({
    mutationFn: (payload) => apiPost<RespostaConsulta>("/v1/tax/query", payload, apiKey),
  });

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-xl font-bold">Consulta Tributária (conversacional)</h1>
      <ConsultaForm onSubmit={(payload) => mutation.mutate(payload)} isPending={mutation.isPending} />
      {mutation.isError && <ErrorBanner error={mutation.error} />}
      {mutation.isSuccess && <ParecerMarkdown resposta={mutation.data} />}
    </div>
  );
}
