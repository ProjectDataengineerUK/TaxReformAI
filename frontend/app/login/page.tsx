import { signIn } from "@/lib/auth";

export default function LoginPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="grid w-full max-w-sm gap-6 rounded-lg border border-border bg-surface p-8 text-center shadow-sm">
        <div className="grid gap-1">
          <h1 className="text-lg font-semibold text-foreground">Acesso restrito</h1>
          <p className="text-sm text-muted-foreground">
            Entre com uma conta Google autorizada para acessar o TaxReform AI.
          </p>
        </div>
        <form
          action={async () => {
            "use server";
            await signIn("google", { redirectTo: "/simulador" });
          }}
        >
          <button
            type="submit"
            className="inline-flex h-10 w-full items-center justify-center rounded-md bg-accent px-4 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent/90"
          >
            Entrar com Google
          </button>
        </form>
      </div>
    </div>
  );
}
