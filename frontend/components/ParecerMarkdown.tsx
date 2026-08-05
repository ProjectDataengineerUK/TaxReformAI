import ReactMarkdown from "react-markdown";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RespostaConsulta } from "@/lib/types";

export function ParecerMarkdown({ resposta }: { resposta: RespostaConsulta }) {
  return (
    <div className="grid gap-4">
      <Card>
        <CardContent className="prose prose-sm max-w-none pt-4">
          <ReactMarkdown>{resposta.parecer_final}</ReactMarkdown>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Histórico auditável</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-1 text-sm">
          {resposta.historico.map((transicao, index) => (
            <div key={index} className="border-b border-border py-1 last:border-0">
              <span className="font-medium">{transicao.no}</span>: {transicao.resumo_output}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
