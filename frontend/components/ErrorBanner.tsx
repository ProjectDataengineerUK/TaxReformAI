import { ApiError } from "@/lib/api-client";

export function ErrorBanner({ error }: { error: ApiError }) {
  const message =
    error.status === 401
      ? "API key inválida ou ausente — configure-a acima"
      : error.status === 422
        ? error.detail
        : error.status === 0
          ? error.detail
          : `Erro inesperado (${error.status}): ${error.detail}`;

  return (
    <div
      role="alert"
      className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
    >
      {message}
    </div>
  );
}
