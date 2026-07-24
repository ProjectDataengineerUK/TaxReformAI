import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="mx-auto grid max-w-2xl gap-4">
      <h1 className="text-2xl font-bold">TaxReform AI — Simulador</h1>
      <p className="text-neutral-600">
        Configure sua API key acima e escolha um dos modos de simulação abaixo.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/simulador">
          <Card className="h-full transition-shadow hover:shadow-md">
            <CardHeader>
              <CardTitle>Simulador Estruturado</CardTitle>
            </CardHeader>
            <CardContent>
              Envie uma lista de itens (NCM, quantidade, valor) e receba a simulação agregada.
            </CardContent>
          </Card>
        </Link>
        <Link href="/consulta">
          <Card className="h-full transition-shadow hover:shadow-md">
            <CardHeader>
              <CardTitle>Consulta Tributária</CardTitle>
            </CardHeader>
            <CardContent>
              Faça uma pergunta em texto livre e receba um parecer com fundamentação legal.
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
