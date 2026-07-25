"""Pool de conexões com o Cloud SQL, para o audit log (seção 7).

Segue o padrão de `api/config.get_settings`: função com `Depends`,
overridável em teste via `app.dependency_overrides`. `@lru_cache` faz o pool
ser criado uma vez por processo, não por requisição — abrir conexão nova a
cada `/simulate`/`/query` somaria latência real contra o Cloud SQL.

Sem `DB_INSTANCE_CONNECTION_NAME` no ambiente (todo teste, e qualquer deploy
antes de o Cloud SQL existir), `get_db_pool()` devolve `None`. Os routers
tratam isso como "audit log indisponível", nunca como erro do request — uma
falha de banco não pode derrubar um cálculo tributário.
"""

import os
from functools import lru_cache


def _dsn() -> str | None:
    connection_name = os.environ.get("DB_INSTANCE_CONNECTION_NAME")
    if not connection_name:
        return None
    # Socket unix montado pelo Cloud Run quando o serviço sobe com
    # --add-cloudsql-instances (ver deploy.yml) — não é TCP, não precisa de
    # VPC. Mesmo caminho que gcloud/Cloud Run documentam para o conector nativo.
    return (
        f"host=/cloudsql/{connection_name} "
        f"dbname={os.environ.get('DB_NAME', 'taxreformai')} "
        f"user={os.environ.get('DB_USER', 'taxreformai_app')} "
        f"password={os.environ.get('DB_PASSWORD', '')}"
    )


@lru_cache
def get_db_pool():
    """Devolve o pool (`psycopg_pool.ConnectionPool`) ou `None` se o banco não
    está configurado no ambiente. Import de `psycopg_pool` fica dentro da
    função: o resto da API (rotas que não tocam o banco) não precisa que o
    pacote esteja instalado para importar `api.main`."""
    dsn = _dsn()
    if dsn is None:
        return None

    from psycopg_pool import ConnectionPool

    # min_size=0: não abre conexão no import do módulo, só na primeira
    # requisição que precisar — evita atrasar o boot do container com uma
    # conexão ao banco antes do healthcheck do Cloud Run responder.
    return ConnectionPool(dsn, min_size=0, max_size=5, open=True)
