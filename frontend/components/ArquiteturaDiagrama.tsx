function No({
  x,
  y,
  w,
  h,
  titulo,
  sub,
  destaque = false,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  titulo: string;
  sub?: string;
  destaque?: boolean;
}) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        className={destaque ? "fill-accent/10 stroke-accent" : "fill-surface stroke-border"}
        strokeWidth={1.3}
      />
      <text
        x={x + w / 2}
        y={y + h / 2 + (sub ? -4 : 5)}
        textAnchor="middle"
        className="fill-foreground text-[13px] font-semibold"
      >
        {titulo}
      </text>
      {sub && (
        <text
          x={x + w / 2}
          y={y + h / 2 + 14}
          textAnchor="middle"
          className="fill-muted-foreground text-[10.5px]"
        >
          {sub}
        </text>
      )}
    </g>
  );
}

function Seta({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      className="stroke-border"
      strokeWidth={1.3}
      markerEnd="url(#arq-seta)"
    />
  );
}

export function ArquiteturaDiagrama() {
  return (
    <svg
      viewBox="0 0 980 560"
      role="img"
      aria-label="Diagrama de arquitetura: o navegador fala com o frontend Next.js, que chama a API FastAPI; a API se bifurca entre um motor de cálculo determinístico e uma orquestração multi-agente com Claude real, apoiada em busca híbrida no Qdrant e legislação ingerida do Planalto e do TCU; tudo persistido em Cloud SQL com isolamento por tenant."
      className="w-full"
    >
      <defs>
        <marker
          id="arq-seta"
          viewBox="0 0 8 8"
          refX="7"
          refY="4"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L8,4 L0,8 Z" className="fill-border" />
        </marker>
      </defs>

      <No x={390} y={10} w={200} h={50} titulo="Você" sub="navegador, login Google" />
      <No x={370} y={100} w={240} h={54} titulo="Frontend" sub="Next.js" />
      <No x={370} y={194} w={240} h={54} titulo="API" sub="FastAPI, chave por cliente" />

      <No
        x={90}
        y={310}
        w={300}
        h={68}
        titulo="Motor Determinístico"
        sub="CBS · IBS · IS — sem LLM"
      />
      <No
        x={480}
        y={310}
        w={340}
        h={68}
        titulo="Orquestração Multi-Agente"
        sub="5 nós, Claude real"
        destaque
      />

      <No x={90} y={430} w={300} h={62} titulo="Cloud SQL" sub="schema real, isolado por cliente" />
      <No x={480} y={430} w={160} h={62} titulo="Qdrant" sub="busca híbrida" />
      <No x={660} y={430} w={160} h={62} titulo="Claude" sub="Haiku + Sonnet" />

      <text x={650} y={524} textAnchor="middle" className="fill-muted-foreground text-[10.5px]">
        legislação ingerida do Planalto e do TCU, chunk por artigo
      </text>

      <Seta x1={490} y1={60} x2={490} y2={100} />
      <Seta x1={490} y1={154} x2={490} y2={194} />
      <Seta x1={430} y1={248} x2={280} y2={310} />
      <Seta x1={550} y1={248} x2={640} y2={310} />
      <Seta x1={240} y1={378} x2={240} y2={430} />
      <Seta x1={620} y1={378} x2={560} y2={430} />
      <Seta x1={700} y1={378} x2={730} y2={430} />
    </svg>
  );
}
