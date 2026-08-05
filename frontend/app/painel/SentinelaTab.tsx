"use client";

import { COR_PONTO_NIVEL, COR_TEXTO_NIVEL, useStatusObservabilidade } from "./status-shared";

export function SentinelaTab() {
  const { data, isLoading, isError, refetch, isFetching } = useStatusObservabilidade();

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando...</p>;
  if (isError || !data) {
    return <p className="text-sm text-destructive">Não foi possível carregar o status.</p>;
  }

  return (
    <div className="grid gap-3">
      <button
        onClick={() => refetch()}
        disabled={isFetching}
        className="w-fit text-xs text-muted-foreground underline hover:text-foreground"
      >
        {isFetching ? "Atualizando..." : "Atualizar"}
      </button>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Recurso</th>
              <th className="py-2 pr-4 font-medium">Status</th>
              <th className="py-2 font-medium">Detalhe</th>
            </tr>
          </thead>
          <tbody>
            {data.recursos.map((recurso) => (
              <tr key={recurso.recurso} className="border-b border-border/50">
                <td className="py-2 pr-4">{recurso.recurso}</td>
                <td className="py-2 pr-4">
                  <span
                    className={`inline-flex items-center gap-2 font-medium capitalize ${COR_TEXTO_NIVEL[recurso.nivel]}`}
                  >
                    <span className={`h-2 w-2 rounded-full ${COR_PONTO_NIVEL[recurso.nivel]}`} />
                    {recurso.nivel}
                  </span>
                </td>
                <td className="py-2 text-muted-foreground">{recurso.detalhe}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
