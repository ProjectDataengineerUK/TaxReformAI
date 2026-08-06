"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ItemSimulacao, PayloadConsulta } from "@/lib/types";

const ITEM_VAZIO: ItemSimulacao = {
  sku: "",
  ncm: "",
  quantidade: 1,
  valor_unitario: "1000.00",
  uf_origem: "SP",
  uf_destino: "SP",
  natureza: "MERCADORIA",
};

const selectClassName =
  "flex h-10 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

export function ConsultaForm({
  onSubmit,
  isPending,
}: {
  onSubmit: (payload: PayloadConsulta) => void;
  isPending: boolean;
}) {
  const [textoConsulta, setTextoConsulta] = useState("");
  const [anoOperacao, setAnoOperacao] = useState(2026);
  const [regimeApuracao, setRegimeApuracao] = useState("");
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
      texto_consulta: textoConsulta,
      ano_operacao: anoOperacao,
      itens,
      regime_apuracao: regimeApuracao || null,
    });
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
          <Label htmlFor="regime-apuracao-consulta">Regime de apuração (PIS/COFINS)</Label>
          <select
            id="regime-apuracao-consulta"
            className={selectClassName}
            value={regimeApuracao}
            onChange={(e) => setRegimeApuracao(e.target.value)}
          >
            <option value="">Não informado</option>
            <option value="NAO_CUMULATIVO">Não cumulativo (Lucro Real)</option>
            <option value="CUMULATIVO">Cumulativo (Lucro Presumido)</option>
          </select>
        </div>
      </div>

      <div className="grid gap-3">
        {itens.map((item, index) => (
          <div key={index} className="grid grid-cols-2 gap-2 rounded-md border border-border p-3 sm:grid-cols-7">
            <Input
              placeholder="SKU"
              value={item.sku}
              onChange={(e) => atualizarItem(index, "sku", e.target.value)}
            />
            <select
              className={selectClassName}
              value={item.natureza ?? "MERCADORIA"}
              onChange={(e) => atualizarItem(index, "natureza", e.target.value)}
            >
              <option value="MERCADORIA">Mercadoria</option>
              <option value="SERVICO">Serviço</option>
            </select>
            <Input
              placeholder="NCM"
              value={item.ncm ?? ""}
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
        <Button type="submit" disabled={isPending} className="w-fit">
          {isPending ? "Consultando..." : "Consultar"}
        </Button>
      </div>
    </form>
  );
}
