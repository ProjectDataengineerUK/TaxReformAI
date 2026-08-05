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
  const tenantId = process.env.FRONTEND_TENANT_ID;
  // Achado real (2026-08-05): /v1/tax/simulate exige que tenant_id do corpo
  // bata com o tenant da própria API key (403 caso contrário) — SimuladorForm
  // mandava um "frontend-demo" fixo, divergente do tenant real configurado
  // em API_KEYS. As duas env vars precisam vir do MESMO par escolhido pelo
  // usuário ao cadastrar API_KEYS; sem qualquer uma delas, degrada para 503
  // (fallback manual do frontend), nunca serve uma delas sozinha.
  if (!apiKey || !tenantId) {
    return NextResponse.json(
      { detail: "FRONTEND_API_KEY e/ou FRONTEND_TENANT_ID não configuradas" },
      { status: 503 },
    );
  }

  return NextResponse.json({ apiKey, tenantId });
}
