import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

// Server-only: FRONTEND_API_KEY nunca é NEXT_PUBLIC_*, então nunca é embutida
// no bundle JS nem visível a quem inspeciona o navegador — só este Route
// Handler, rodando no container, tem acesso a ela. Devolve a chave apenas
// para quem já tem sessão válida (login Google + allowlist, mesma checagem
// de frontend/lib/auth.ts), fechando o ciclo: usuário autenticado nunca mais
// precisa colar a API key manualmente.
export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ detail: "Não autenticado" }, { status: 401 });
  }

  const apiKey = process.env.FRONTEND_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ detail: "FRONTEND_API_KEY não configurada" }, { status: 503 });
  }

  return NextResponse.json({ apiKey });
}
