"""Prova o lookup de IPI contra o Cloud SQL real, com o papel de RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
a ingestão gravou como `taxreformai_admin`, e o `GRANT SELECT` da migração 004
para `taxreformai_app` nunca foi exercitado por nenhum SELECT. Pela Decisão 2
do DESIGN, um grant faltando NÃO gera erro em runtime — gera
CONSULTA_INDISPONIVEL silencioso, que some no log. Este script é o único lugar
onde isso vira uma falha ruidosa.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`, privilégio mínimo),
não com a URL do admin: usar a credencial administrativa aqui provaria que o
DADO existe, que já se sabe, e não que a API CONSEGUE lê-lo, que é a pergunta.
"""

import os
import sys

import psycopg

from db.repositorio import buscar_ipi_por_ncm


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    dsn = os.environ.get("DATABASE_URL_APP")
    if not dsn:
        _falhar(
            "DATABASE_URL_APP ausente. Este script precisa do papel de RUNTIME "
            "(taxreformai_app) — com o admin ele provaria a coisa errada."
        )

    conexao = psycopg.connect(dsn)
    try:
        with conexao.cursor() as cur:
            cur.execute("SELECT current_user")
            papel = cur.fetchone()[0]
        print(f"Conectado como {papel!r}.")
        if papel != "taxreformai_app":
            _falhar(
                f"conectado como {papel!r}, esperado 'taxreformai_app'. A "
                "verificação só vale com o papel que a API usa em runtime."
            )

        # Um NCM com alíquota e um NT — as duas classificações que a resposta
        # precisa distinguir. Escolhidos por consulta, não fixados no código:
        # a TIPI é reeditada por ADE da RFB e um código fixo aqui poderia sumir
        # numa reedição e reprovar o job por motivo errado.
        with conexao.cursor() as cur:
            cur.execute(
                "SELECT ncm_code FROM aliquotas_ipi_tipi "
                "WHERE nao_tributado IS FALSE ORDER BY ncm_code LIMIT 1"
            )
            linha = cur.fetchone()
            com_aliquota = linha[0] if linha else None

            cur.execute(
                "SELECT ncm_code FROM aliquotas_ipi_tipi "
                "WHERE nao_tributado IS TRUE ORDER BY ncm_code LIMIT 1"
            )
            linha = cur.fetchone()
            nt = linha[0] if linha else None

        if com_aliquota is None or nt is None:
            _falhar(
                "a tabela não tem os dois casos (alíquota e NT) visíveis para o "
                f"papel de runtime — com_aliquota={com_aliquota!r}, nt={nt!r}. "
                "Ou a ingestão não rodou, ou o GRANT SELECT da migração 004 não "
                "foi aplicado."
            )

        # O MESMO lookup em lote que /v1/tax/simulate faz — não um SELECT
        # ad-hoc parecido. Verificar um caminho diferente do de produção
        # deixaria justamente o caminho de produção por verificar.
        resultado = buscar_ipi_por_ncm(conexao, [com_aliquota, nt])

        if set(resultado) != {com_aliquota, nt}:
            _falhar(
                f"lookup em lote devolveu {sorted(resultado)}, esperado "
                f"{sorted([com_aliquota, nt])}."
            )

        linha_aliquota = resultado[com_aliquota]
        if linha_aliquota.aliquota_percentual is None or linha_aliquota.nao_tributado:
            _falhar(
                f"{com_aliquota} deveria ter alíquota e não ser NT — veio "
                f"aliquota={linha_aliquota.aliquota_percentual!r}, "
                f"nao_tributado={linha_aliquota.nao_tributado!r}."
            )
        if not linha_aliquota.dispositivo_legal_ref:
            _falhar(f"{com_aliquota} veio sem dispositivo_legal_ref — a resposta cita a fonte.")

        linha_nt = resultado[nt]
        if not linha_nt.nao_tributado or linha_nt.aliquota_percentual is not None:
            _falhar(
                f"{nt} deveria ser NT com alíquota NULL — veio "
                f"nao_tributado={linha_nt.nao_tributado!r}, "
                f"aliquota={linha_nt.aliquota_percentual!r}. NT achatado em 0% "
                "é exatamente o que esta feature existe para evitar."
            )

        with conexao.cursor() as cur:
            cur.execute("SELECT count(*) FROM aliquotas_ipi_tipi")
            total = cur.fetchone()[0]

        print(
            "IPI VERIFICADO CONTRA O CLOUD SQL REAL: o papel de runtime lê "
            f"aliquotas_ipi_tipi ({total} linhas). {com_aliquota} = "
            f"{linha_aliquota.aliquota_percentual}; {nt} = NT (alíquota NULL)."
        )
    finally:
        conexao.close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        print(
            "Se for 'permission denied for table aliquotas_ipi_tipi', o GRANT "
            "SELECT da migração 004 não chegou ao papel taxreformai_app.",
            file=sys.stderr,
        )
        sys.exit(1)
