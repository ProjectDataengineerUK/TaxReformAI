const ETAPAS = [
  {
    titulo: "Brainstorm",
    texto:
      "Perguntas de descoberta antes de qualquer código — mínimo de 3, uma de cada vez, com opções concretas em vez de perguntas abertas demais.",
  },
  {
    titulo: "Define",
    texto:
      "Requisitos, critérios de sucesso mensuráveis e testes de aceitação — com uma nota de clareza mínima antes de seguir.",
  },
  {
    titulo: "Design",
    texto:
      "Decisões de arquitetura documentadas com o porquê, não só o quê — incluindo o que foi rejeitado e por quê.",
  },
  {
    titulo: "Build",
    texto:
      "Implementação com verificação a cada passo — lint, testes, e sempre que possível, prova contra infraestrutura real, não só simulada.",
  },
  {
    titulo: "Ship",
    texto:
      "Arquivamento com lições aprendidas — o que funcionou, o que quebrou, e o que fica documentado pra próxima vez.",
  },
];

export function Metodologia() {
  return (
    <div className="grid gap-5">
      {ETAPAS.map((etapa, index) => (
        <div key={etapa.titulo} className="flex gap-4">
          <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full border border-border font-mono text-sm text-accent">
            {index + 1}
          </div>
          <div>
            <h4 className="font-semibold text-foreground">{etapa.titulo}</h4>
            <p className="mt-0.5 text-sm text-muted-foreground">{etapa.texto}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
