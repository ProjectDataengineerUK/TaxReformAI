import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RespostaSimulacao } from "@/lib/types";

function Valor({ valor, fonteLegal }: { valor: string | null; fonteLegal?: string | null }) {
  if (valor === null) {
    return <span className="text-muted-foreground">não calculado</span>;
  }
  return (
    <span title={fonteLegal ?? undefined}>
      R$ {valor}
      {fonteLegal && <span className="ml-1 text-xs text-muted-foreground">({fonteLegal})</span>}
    </span>
  );
}

export function ComparativoRegime({ resposta }: { resposta: RespostaSimulacao }) {
  const { resumo_financeiro, regime_vigente, itens_detalhados, itens_regime_vigente } = resposta;

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Regime atual x IVA Dual — ano {resposta.ano_operacao}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
          <div className="grid gap-2">
            <div className="font-medium text-foreground">Regime atual</div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">PIS</span>
              <Valor valor={regime_vigente.total_pis} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">COFINS</span>
              <Valor valor={regime_vigente.total_cofins} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">ICMS interestadual</span>
              <Valor valor={regime_vigente.total_icms_interestadual} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">ICMS interno</span>
              <Valor valor={regime_vigente.total_icms_interno} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">ICMS interno (FECP)</span>
              <Valor valor={regime_vigente.total_icms_interno_fecp} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">ISS (piso)</span>
              <Valor valor={regime_vigente.total_iss_piso} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">ISS (teto)</span>
              <Valor valor={regime_vigente.total_iss_teto} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">IPI</span>
              <Valor valor={regime_vigente.total_ipi} />
            </div>
            {regime_vigente.tributos_nao_calculados.length > 0 && (
              <div className="text-xs text-muted-foreground">
                Não calculados: {regime_vigente.tributos_nao_calculados.join(", ")}
              </div>
            )}
          </div>

          <div className="grid gap-2">
            <div className="font-medium text-foreground">IVA Dual (projeção)</div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">CBS</span>
              <Valor valor={resumo_financeiro.total_cbs} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">IBS</span>
              <Valor valor={resumo_financeiro.total_ibs} />
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">IS</span>
              <Valor valor={resumo_financeiro.total_is} />
            </div>
            <div className="mt-2 flex justify-between gap-2 border-t border-border pt-2 font-medium text-foreground">
              <span>Líquido projetado (Split Payment)</span>
              <span>R$ {resumo_financeiro.valor_liquido_projetado_split_payment}</span>
            </div>
            <div className="text-xs text-muted-foreground" title={resposta.fonte_legal_fase}>
              Fundamentação: {resposta.fonte_legal_fase}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Comparação por item</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {itens_detalhados.map((item, index) => {
            const regimeItem = itens_regime_vigente[index];
            return (
              <div key={item.sku} className="rounded-md border border-border p-3 text-sm">
                <div className="font-medium">
                  {item.sku}
                  {item.ncm && ` — NCM ${item.ncm}`}
                </div>
                <div className="mt-1 grid gap-1 sm:grid-cols-2">
                  <div className="text-muted-foreground">
                    Regime atual: ICMS interno{" "}
                    {regimeItem?.icms_interno_percentual ?? "não se aplica"}
                    {regimeItem?.icms_interno_percentual && "%"} · ICMS interestadual{" "}
                    {regimeItem?.icms_interestadual_percentual ?? "não se aplica"}
                    {regimeItem?.icms_interestadual_percentual && "%"} · ISS piso{" "}
                    {regimeItem?.iss_piso_percentual ?? "não se aplica"}
                    {regimeItem?.iss_piso_percentual && "%"} · IPI{" "}
                    {regimeItem?.ipi_percentual ?? regimeItem?.ipi_situacao}
                    {regimeItem?.ipi_percentual && "%"}
                  </div>
                  <div className="text-muted-foreground">
                    IVA Dual: CBS {item.aliquotas_aplicadas.cbs_percentual}% · IBS{" "}
                    {item.aliquotas_aplicadas.ibs_percentual}% · IS{" "}
                    {item.aliquotas_aplicadas.is_percentual}%
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
