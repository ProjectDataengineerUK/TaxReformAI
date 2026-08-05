"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { useScorecard } from "./scorecard-shared";

export function SegurancaTab() {
  const { data, isLoading, isError } = useScorecard();

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando...</p>;
  if (isError || !data) {
    return <p className="text-sm text-destructive">Não foi possível carregar o scorecard.</p>;
  }

  const { seguranca } = data;

  return (
    <Card>
      <CardHeader className="flex-row items-baseline justify-between">
        <CardTitle>Segurança</CardTitle>
        <span className="text-2xl font-bold text-accent">{seguranca.nota}/5</span>
      </CardHeader>
      <CardContent className="grid gap-4">
        <p className="text-xs text-muted-foreground">{seguranca.framework}</p>
        <p className="text-sm">{seguranca.justificativa}</p>
        {seguranca.por_funcao && (
          <div className="grid grid-cols-5 gap-2">
            {Object.entries(seguranca.por_funcao).map(([funcao, nota]) => (
              <div key={funcao} className="rounded-md border border-border p-2 text-center">
                <p className="text-xs text-muted-foreground">{funcao}</p>
                <p className="text-lg font-semibold">{nota}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
