"use client";

import { useState } from "react";

import { CustoFinOpsTab } from "./CustoFinOpsTab";
import { DiagramaTab } from "./DiagramaTab";
import { MaturidadeTab } from "./MaturidadeTab";
import { SegurancaTab } from "./SegurancaTab";
import { SentinelaTab } from "./SentinelaTab";

const ABAS = [
  { id: "diagrama", label: "Diagrama" },
  { id: "sentinela", label: "Sentinela" },
  { id: "maturidade", label: "Maturidade" },
  { id: "seguranca", label: "Segurança" },
  { id: "custo", label: "Custo & FinOps" },
] as const;

type AbaId = (typeof ABAS)[number]["id"];

export default function PainelPage() {
  const [aba, setAba] = useState<AbaId>("diagrama");

  return (
    <div className="mx-auto grid max-w-5xl gap-6">
      <div>
        <h1 className="text-xl font-bold">Painel de Observabilidade</h1>
        <p className="text-sm text-muted-foreground">
          Status ao vivo, custo real (infra + token) e maturidade do sistema.
        </p>
      </div>

      <div className="flex gap-1 border-b border-border" role="tablist">
        {ABAS.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={aba === item.id}
            onClick={() => setAba(item.id)}
            className={
              aba === item.id
                ? "border-b-2 border-accent px-3 py-2 text-sm font-medium text-foreground"
                : "border-b-2 border-transparent px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
            }
          >
            {item.label}
          </button>
        ))}
      </div>

      {aba === "diagrama" && <DiagramaTab />}
      {aba === "sentinela" && <SentinelaTab />}
      {aba === "maturidade" && <MaturidadeTab />}
      {aba === "seguranca" && <SegurancaTab />}
      {aba === "custo" && <CustoFinOpsTab />}
    </div>
  );
}
