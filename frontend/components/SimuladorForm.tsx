"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ItemSimulacao, PayloadSimulacao } from "@/lib/types";

const ITEM_VAZIO: ItemSimulacao = {
  sku: "",
  ncm: "",
  quantidade: 1,
  valor_unitario: "0.00",
  uf_origem: "SP",
  uf_destino: "SP",
};

export function SimuladorForm({
  onSubmit,
  isPending,
}: {
  onSubmit: (payload: PayloadSimulacao) => void;
  isPending: boolean;
}) {
  const [anoOperacao, setAnoOperacao] = useState(2026);
  const [itens, setItens] = useState<ItemSimulacao[]>([{ ...ITEM_VAZIO }]);

  function atualizarItem(index: number, campo: keyof ItemSimulacao, valor: string | number) {
    setItens((atual) =>
      atual.map((item, i) => (i === index ? { ...item, [campo]: valor } : item)),
    );
  }

  function adicionarItem() {
    setItens((atual) => [...atual, { ...ITEM_VAZIO }]);
  }

  function removerItem(index: number) {
    setItens((atual) => atual.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      tenant_id: "frontend-demo",
      ano_operacao: anoOperacao,
      operacao_tipo: "VENDA_ESTADUAL_B2B",
      itens,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <div className="grid max-w-xs gap-1">
        <Label htmlFor="ano-operacao">Ano da operação</Label>
        <Input
          id="ano-operacao"
          type="number"
          value={anoOperacao}
          onChange={(e) => setAnoOperacao(Number(e.target.value))}
        />
      </div>

      <div className="grid gap-3">
        {itens.map((item, index) => (
          <div key={index} className="grid grid-cols-2 gap-2 rounded-md border border-border p-3 sm:grid-cols-6">
            <Input
              placeholder="SKU"
              value={item.sku}
              onChange={(e) => atualizarItem(index, "sku", e.target.value)}
            />
            <Input
              placeholder="NCM"
              value={item.ncm}
              onChange={(e) => atualizarItem(index, "ncm", e.target.value)}
            />
            <Input
              type="number"
              placeholder="Quantidade"
              value={item.quantidade}
              onChange={(e) => atualizarItem(index, "quantidade", Number(e.target.value))}
            />
            <Input
              placeholder="Valor unitário"
              value={item.valor_unitario}
              onChange={(e) => atualizarItem(index, "valor_unitario", e.target.value)}
            />
            <Input
              placeholder="UF origem"
              value={item.uf_origem}
              onChange={(e) => atualizarItem(index, "uf_origem", e.target.value)}
            />
            <div className="flex gap-2">
              <Input
                placeholder="UF destino"
                value={item.uf_destino}
                onChange={(e) => atualizarItem(index, "uf_destino", e.target.value)}
              />
              {itens.length > 1 && (
                <Button type="button" variant="outline" size="sm" onClick={() => removerItem(index)}>
                  Remover
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <Button type="button" variant="outline" onClick={adicionarItem}>
          + Adicionar item
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? "Simulando..." : "Simular"}
        </Button>
      </div>
    </form>
  );
}
