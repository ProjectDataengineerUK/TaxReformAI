"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useApiKey } from "@/hooks/useApiKey";
import { apiGet } from "@/lib/api-client";
import type { RespostaCusto } from "@/lib/types";

import { useScorecard } from "./scorecard-shared";

function formatarUsd(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "USD" });
}

export function CustoFinOpsTab() {
  const { apiKey } = useApiKey();
  const custo = useQuery({
    queryKey: ["observabilidade-custo"],
    queryFn: () => apiGet<RespostaCusto>("/v1/observabilidade/custo", apiKey),
    enabled: Boolean(apiKey),
  });
  const scorecard = useScorecard();

  if (custo.isLoading) return <p className="text-sm text-muted-foreground">Carregando...</p>;
  if (custo.isError || !custo.data) {
    return <p className="text-sm text-destructive">Não foi possível carregar o custo.</p>;
  }

  const { data } = custo;

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Custo de token (LLM), {data.periodo_dias} dias</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            <p className="text-2xl font-bold">{formatarUsd(data.custo_token_total_usd)}</p>
            {data.custo_por_modelo.length === 0 && (
              <p className="text-xs text-muted-foreground">Nenhuma chamada real registrada no período.</p>
            )}
            {data.custo_por_modelo.map((item) => (
              <div key={item.modelo} className="flex justify-between text-sm text-muted-foreground">
                <span>{item.modelo}</span>
                <span>
                  {formatarUsd(item.custo_usd)} ({item.tokens_entrada + item.tokens_saida} tokens)
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Custo de infra, {data.periodo_dias} dias</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            <p className="text-2xl font-bold">{formatarUsd(data.custo_infra_total_usd)}</p>
            {data.custo_infra_por_servico.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Sem dados — o sync de Billing Export ainda não rodou ou não foi habilitado.
              </p>
            )}
            {data.custo_infra_por_servico.map((item) => (
              <div key={item.servico} className="flex justify-between text-sm text-muted-foreground">
                <span>{item.servico}</span>
                <span>{formatarUsd(item.custo_usd)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {data.alertas_limiar.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Alertas</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1">
            {data.alertas_limiar.map((alerta) => (
              <p key={alerta} className="text-sm text-amber-400">
                {alerta}
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Oportunidades de FinOps</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          {scorecard.isLoading && <p className="text-sm text-muted-foreground">Carregando...</p>}
          {scorecard.data?.finops_achados.map((item) => (
            <div key={item.achado} className="grid gap-1 border-b border-border/50 pb-3 last:border-0 last:pb-0">
              <p className="text-sm font-medium">{item.achado}</p>
              <p className="text-xs text-muted-foreground">Fonte: {item.fonte}</p>
              <p className="text-sm text-muted-foreground">{item.oportunidade}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
