import type { Metadata } from "next";
import Link from "next/link";

import { ApiKeyBar } from "@/components/ApiKeyBar";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "TaxReform AI — Simulador",
  description: "Simulador tributário do TaxReform AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <Providers>
          <ApiKeyBar />
          <nav className="flex gap-4 border-b border-neutral-200 px-4 py-3 text-sm">
            <Link href="/" className="font-semibold">
              TaxReform AI
            </Link>
            <Link href="/simulador">Simulador (NCM)</Link>
            <Link href="/consulta">Consulta</Link>
          </nav>
          <main className="p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
