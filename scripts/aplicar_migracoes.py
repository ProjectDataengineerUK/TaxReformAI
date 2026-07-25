"""Aplica db/migrations/*.sql contra DATABASE_URL. Roda só via
migrar_banco.yml, conectado pelo Cloud SQL Auth Proxy — nunca local, mesma
política do resto do projeto."""

import os
import sys

import psycopg

from db.migrador import aplicar_migracoes


def main() -> None:
    conexao = psycopg.connect(os.environ["DATABASE_URL"])
    aplicadas = aplicar_migracoes(conexao)
    if aplicadas:
        print(f"Migrações aplicadas: {', '.join(aplicadas)}")
    else:
        print("Nenhuma migração pendente — banco já estava atualizado.")
    conexao.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
