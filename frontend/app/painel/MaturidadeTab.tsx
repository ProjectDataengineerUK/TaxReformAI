"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EixoMaturidade } from "@/lib/types";

import { useScorecard } from "./scorecard-shared";

function CardEixo({ titulo, eixo }: { titulo: string; eixo: EixoMaturidade }) {
  return (
    <Card>
      <CardHeader className="flex-row items-baseline justify-between">
        <CardTitle>{titulo}</CardTitle>
        <span className="text-2xl font-bold text-accent">{eixo.nota}/5</span>
      </CardHeader>
      <CardContent className="grid gap-2">
        <p className="text-xs text-muted-foreground">{eixo.framework}</p>
        <p className="text-sm">{eixo.justificativa}</p>
      </CardContent>
    </Card>
  );
}

export function MaturidadeTab() {
  const { data, isLoading, isError } = useScorecard();

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando...</p>;
  if (isError || !data) {
    return <p className="text-sm text-destructive">Não foi possível carregar o scorecard.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <CardEixo titulo="MLOps" eixo={data.mlops} />
      <CardEixo titulo="DataOps" eixo={data.dataops} />
      <CardEixo titulo="LLMOps" eixo={data.llmops} />
    </div>
  );
}
