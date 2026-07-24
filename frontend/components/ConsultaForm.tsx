"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { PayloadConsulta } from "@/lib/types";

export function ConsultaForm({
  onSubmit,
  isPending,
}: {
  onSubmit: (payload: PayloadConsulta) => void;
  isPending: boolean;
}) {
  const [textoConsulta, setTextoConsulta] = useState("");
  const [anoOperacao, setAnoOperacao] = useState(2026);
  const [valorBase, setValorBase] = useState("1000.00");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({ texto_consulta: textoConsulta, ano_operacao: anoOperacao, valor_base: valorBase });
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <div className="grid gap-1">
        <Label htmlFor="texto-consulta">Sua pergunta</Label>
        <Textarea
          id="texto-consulta"
          value={textoConsulta}
          onChange={(e) => setTextoConsulta(e.target.value)}
          placeholder="Ex: quanto de imposto incide sobre a venda de eletrônicos de SP para MG?"
          required
        />
      </div>
      <div className="grid max-w-md grid-cols-2 gap-2">
        <div className="grid gap-1">
          <Label htmlFor="ano-operacao-consulta">Ano da operação</Label>
          <Input
            id="ano-operacao-consulta"
            type="number"
            value={anoOperacao}
            onChange={(e) => setAnoOperacao(Number(e.target.value))}
          />
        </div>
        <div className="grid gap-1">
          <Label htmlFor="valor-base-consulta">Valor base (R$)</Label>
          <Input
            id="valor-base-consulta"
            value={valorBase}
            onChange={(e) => setValorBase(e.target.value)}
          />
        </div>
      </div>
      <Button type="submit" disabled={isPending} className="w-fit">
        {isPending ? "Consultando..." : "Consultar"}
      </Button>
    </form>
  );
}
