"use client";

import type { NivelStatus, RecursoStatus } from "@/lib/types";

import { useStatusObservabilidade } from "./status-shared";

function corPreenchimento(nivel: NivelStatus | undefined): string {
  if (nivel === "verde") return "fill-accent/20 stroke-accent";
  if (nivel === "amarelo") return "fill-amber-400/20 stroke-amber-400";
  if (nivel === "vermelho") return "fill-destructive/20 stroke-destructive";
  return "fill-surface stroke-border";
}

function buscar(recursos: RecursoStatus[], nome: string): RecursoStatus | undefined {
  return recursos.find((r) => r.recurso === nome);
}

function No({
  x,
  y,
  w,
  h,
  titulo,
  recurso,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  titulo: string;
  recurso?: RecursoStatus;
}) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={4} strokeWidth={1.5} className={corPreenchimento(recurso?.nivel)} />
      <text x={x + w / 2} y={y + h / 2 - (recurso ? 6 : 0)} textAnchor="middle" className="fill-foreground text-[13px] font-medium">
        {titulo}
      </text>
      {recurso && (
        <text x={x + w / 2} y={y + h / 2 + 14} textAnchor="middle" className="fill-muted-foreground text-[10px]">
          {recurso.detalhe.length > 34 ? `${recurso.detalhe.slice(0, 34)}…` : recurso.detalhe}
        </text>
      )}
    </g>
  );
}

export function DiagramaTab() {
  const { data, isLoading, isError, refetch, isFetching } = useStatusObservabilidade();

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando...</p>;
  if (isError || !data) {
    return <p className="text-sm text-destructive">Não foi possível carregar o status.</p>;
  }

  const recursos = data.recursos;
  const dep = [
    { nome: "Cloud SQL", titulo: "Cloud SQL" },
    { nome: "Qdrant Cloud", titulo: "Qdrant Cloud" },
    { nome: "API Claude direta", titulo: "API Claude direta" },
    { nome: "Cloud Tasks", titulo: "Cloud Tasks" },
    { nome: "Sync BigQuery", titulo: "Sync BigQuery" },
  ];
  const largura = 900;
  const gap = 20;
  const boxW = (largura - 120 - gap * (dep.length - 1)) / dep.length;

  return (
    <div className="grid gap-3">
      <button
        onClick={() => refetch()}
        disabled={isFetching}
        className="w-fit text-xs text-muted-foreground underline hover:text-foreground"
      >
        {isFetching ? "Atualizando..." : "Atualizar"}
      </button>
      <div className="overflow-x-auto rounded-lg border border-border bg-surface p-2">
        <svg viewBox="0 0 900 340" role="img" aria-label="Diagrama dinâmico dos recursos do sistema, coloridos por status ao vivo" className="min-w-[720px]">
          <No x={330} y={10} w={240} h={44} titulo="Navegador" />
          <No x={330} y={84} w={240} h={50} titulo="Frontend" recurso={buscar(recursos, "Frontend")} />
          <No x={330} y={164} w={240} h={50} titulo="API" recurso={buscar(recursos, "API")} />

          <line x1={450} y1={54} x2={450} y2={84} stroke="currentColor" className="text-muted-foreground" markerEnd="url(#seta)" />
          <line x1={450} y1={134} x2={450} y2={164} stroke="currentColor" className="text-muted-foreground" markerEnd="url(#seta)" />

          <defs>
            <marker id="seta" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L8,4 L0,8 Z" fill="currentColor" className="text-muted-foreground" />
            </marker>
          </defs>

          {dep.map((item, i) => {
            const x = 60 + i * (boxW + gap);
            const cx = x + boxW / 2;
            return (
              <g key={item.nome}>
                <line x1={450} y1={214} x2={cx} y2={250} stroke="currentColor" className="text-muted-foreground" markerEnd="url(#seta)" />
                <No x={x} y={250} w={boxW} h={70} titulo={item.titulo} recurso={buscar(recursos, item.nome)} />
              </g>
            );
          })}
        </svg>
      </div>
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-accent" /> saudável</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-400" /> atenção</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-destructive" /> crítico</span>
      </div>
    </div>
  );
}
