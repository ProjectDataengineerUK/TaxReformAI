const TERMOS = [
  {
    termo: "IVA Dual",
    definicao:
      "O novo modelo de imposto sobre consumo do Brasil — um imposto só, cobrado em duas esferas (federal e estadual/municipal), substituindo 5 tributos antigos.",
  },
  {
    termo: "CBS",
    definicao: "Contribuição sobre Bens e Serviços — a parte federal do IVA Dual, substitui PIS e COFINS.",
  },
  {
    termo: "IBS",
    definicao: "Imposto sobre Bens e Serviços — a parte estadual/municipal do IVA Dual, substitui ICMS e ISS.",
  },
  {
    termo: "Imposto Seletivo",
    definicao:
      "Imposto extra sobre produtos específicos (cigarro, bebida alcoólica, veículos) — parecido com um \"imposto do pecado\".",
  },
  {
    termo: "Split Payment",
    definicao:
      "Mecanismo em que o imposto é separado e recolhido automaticamente no momento do pagamento, não depois.",
  },
  {
    termo: "Busca híbrida",
    definicao:
      "Técnica de IA que busca o trecho certo de um documento (aqui, a lei) antes de gerar uma resposta — combina busca por significado e por palavra exata.",
  },
  {
    termo: "Guardrail",
    definicao:
      "Uma verificação automática que barra uma resposta de IA antes dela chegar no usuário, se ela não passar num critério de segurança/correção.",
  },
  {
    termo: "Multi-tenancy",
    definicao:
      "Arquitetura em que vários clientes compartilham a mesma infraestrutura com isolamento garantido pelo próprio banco de dados, não só pelo código da aplicação.",
  },
];

export function Glossario() {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      {TERMOS.map((item) => (
        <div key={item.termo} className="border-l-2 border-accent pl-4">
          <dt className="font-mono text-sm font-semibold text-accent">{item.termo}</dt>
          <dd className="mt-0.5 text-sm text-muted-foreground">{item.definicao}</dd>
        </div>
      ))}
    </dl>
  );
}
