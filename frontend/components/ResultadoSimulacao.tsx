import { ComparativoRegime } from "@/components/ComparativoRegime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RespostaSimulacao } from "@/lib/types";

export function ResultadoSimulacao({ resposta }: { resposta: RespostaSimulacao }) {
  const { resumo_financeiro, itens_detalhados } = resposta;

  return (
    <div className="grid gap-4">
      <ComparativoRegime resposta={resposta} />

      <Card>
        <CardHeader>
          <CardTitle>Resumo financeiro — ano {resposta.ano_operacao}</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-5">
          <div>
            <div className="text-muted-foreground">Valor bruto</div>
            <div className="font-medium">R$ {resumo_financeiro.valor_bruto_total}</div>
          </div>
          <div>
            <div className="text-muted-foreground">CBS</div>
            <div className="font-medium">R$ {resumo_financeiro.total_cbs}</div>
          </div>
          <div>
            <div className="text-muted-foreground">IBS</div>
            <div className="font-medium">R$ {resumo_financeiro.total_ibs}</div>
          </div>
          <div>
            <div className="text-muted-foreground">IS</div>
            <div className="font-medium">R$ {resumo_financeiro.total_is}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Líquido (Split Payment)</div>
            <div className="font-medium">
              R$ {resumo_financeiro.valor_liquido_projetado_split_payment}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Itens detalhados</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {itens_detalhados.map((item) => (
            <div key={item.sku} className="rounded-md border border-border p-3 text-sm">
              <div className="font-medium">
                {item.sku} — NCM {item.ncm}
              </div>
              <div className="text-muted-foreground">
                CBS {item.aliquotas_aplicadas.cbs_percentual}% · IBS{" "}
                {item.aliquotas_aplicadas.ibs_percentual}% · IS{" "}
                {item.aliquotas_aplicadas.is_percentual}%
              </div>
              <div className="text-xs text-muted-foreground">{item.fundamentacao_legal}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
