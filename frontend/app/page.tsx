import Link from "next/link";

import { ArquiteturaDiagrama } from "@/components/ArquiteturaDiagrama";
import { EstatisticasFaixa } from "@/components/EstatisticasFaixa";
import { Glossario } from "@/components/Glossario";
import { HistoriasReais } from "@/components/HistoriasReais";
import { Metodologia } from "@/components/Metodologia";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const RECURSOS = [
  {
    titulo: "Cálculo determinístico",
    descricao:
      "CBS, IBS e Imposto Seletivo calculados por regras auditáveis, nunca por estimativa de modelo de linguagem.",
  },
  {
    titulo: "Fundamentação legal citável",
    descricao:
      "Toda alíquota aplicada aponta para o artigo real da LCP 214/2025 que a rege — sem citação inventada.",
  },
  {
    titulo: "Cobertura da transição 2026–2033",
    descricao:
      "Do regime atual (PIS/COFINS, ICMS, ISS, IPI) até o IVA Dual pleno, incluindo os Anexos de redução e o Imposto Seletivo.",
  },
];

export default function LandingPage() {
  return (
    <div className="mx-auto grid max-w-4xl gap-16 py-12">
      <section className="grid gap-6 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Inteligência tributária para a transição do IVA Dual
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Simule CBS, IBS e Imposto Seletivo com precisão auditável e fundamentação legal em cada
          resultado — feito para departamentos fiscais, controllers e consultorias tributárias.
        </p>
        <div>
          <Link
            href="/login"
            className="inline-flex h-11 items-center justify-center rounded-md bg-accent px-6 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent/90"
          >
            Entrar com Google
          </Link>
        </div>
        <EstatisticasFaixa />
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {RECURSOS.map((recurso) => (
          <Card key={recurso.titulo}>
            <CardHeader>
              <CardTitle>{recurso.titulo}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {recurso.descricao}
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-foreground">Como funciona por dentro</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Nenhum número sai de uma estimativa de modelo de linguagem. O cálculo é sempre
            determinístico; a orquestração com IA existe só para conversar e citar a legislação
            certa — nunca para decidir uma alíquota.
          </p>
        </div>
        <Card>
          <CardContent className="overflow-x-auto pt-4">
            <ArquiteturaDiagrama />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-foreground">Histórias reais de engenharia</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Cada uma aconteceu em produção, com evidência real — log, teste ou usuário reportando.
            Não é cenário hipotético.
          </p>
        </div>
        <HistoriasReais />
      </section>

      <section className="grid gap-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-foreground">Como o time trabalha</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Cada feature passa pelo mesmo funil, sem atalho — mesmo numa sessão de poucas horas.
          </p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <Metodologia />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-foreground">Glossário rápido</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Para quem não vive o dia a dia tributário brasileiro.
          </p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <Glossario />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
