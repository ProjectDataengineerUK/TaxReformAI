"""Popula `tenants` a partir do secret API_KEYS ({chave_api: tenant_slug}).

Necessário para `resolver_tenant()` funcionar: sem uma linha em `tenants` com
o slug configurado hoje na API ("taxreformai-dev"), o audit log logaria
"tenant não cadastrado" para toda requisição real. Idempotente via
ON CONFLICT — pode rodar de novo sem duplicar."""

import json
import os
import sys

import psycopg


def main() -> None:
    api_keys = json.loads(os.environ["API_KEYS"])
    slugs = sorted(set(api_keys.values()))
    if not slugs:
        print("API_KEYS vazio — nada a popular.")
        return

    conexao = psycopg.connect(os.environ["DATABASE_URL"])
    with conexao.cursor() as cur:
        for slug in slugs:
            cur.execute(
                "INSERT INTO tenants (slug, nome) VALUES (%s, %s) "
                "ON CONFLICT (slug) DO NOTHING",
                (slug, slug),
            )
    conexao.commit()
    conexao.close()
    print(f"Tenants garantidos: {', '.join(slugs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
