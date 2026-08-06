const ESTATISTICAS = [
  { numero: "24", rotulo: "features em produção" },
  { numero: "600+", rotulo: "testes automatizados" },
  { numero: "5", rotulo: "agentes de IA na orquestração" },
  { numero: "6.866", rotulo: "trechos de legislação indexados" },
  { numero: "4", rotulo: "fontes legais oficiais" },
  { numero: "0", rotulo: "credenciais geradas pela IA" },
];

export function EstatisticasFaixa() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {ESTATISTICAS.map((item) => (
        <div
          key={item.rotulo}
          className="rounded-lg border border-border bg-surface px-4 py-3 text-center"
        >
          <div className="font-mono text-2xl font-bold text-accent">{item.numero}</div>
          <div className="mt-1 text-[11px] text-muted-foreground">{item.rotulo}</div>
        </div>
      ))}
    </div>
  );
}
