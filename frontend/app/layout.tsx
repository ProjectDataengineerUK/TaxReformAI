import type { Metadata } from "next";
import Link from "next/link";

import { ApiKeyBar } from "@/components/ApiKeyBar";
import { SignOutButton } from "@/components/SignOutButton";
import { auth } from "@/lib/auth";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "TaxReform AI",
  description: "Inteligência tributária e compliance em tempo real para a transição do IVA Dual",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();

  return (
    <html lang="pt-BR" className="dark">
      <body>
        <Providers>
          {session ? (
            <>
              <ApiKeyBar />
              <nav className="flex items-center gap-4 border-b border-border px-4 py-3 text-sm">
                <Link href="/" className="font-semibold text-foreground">
                  TaxReform AI
                </Link>
                <Link href="/simulador" className="text-muted-foreground hover:text-foreground">
                  Simulador (NCM)
                </Link>
                <Link href="/consulta" className="text-muted-foreground hover:text-foreground">
                  Consulta
                </Link>
                <span className="ml-auto flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{session.user?.email}</span>
                  <SignOutButton />
                </span>
              </nav>
            </>
          ) : (
            <nav className="flex items-center border-b border-border px-4 py-3 text-sm">
              <Link href="/" className="font-semibold text-foreground">
                TaxReform AI
              </Link>
            </nav>
          )}
          <main className="p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
