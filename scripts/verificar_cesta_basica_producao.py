"""Prova o Anexo I contra o Cloud SQL real, com o papel de RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
o seed entra como `taxreformai_admin` (a própria migração 005), e o GRANT para
`taxreformai_app` nunca é exercitado por nenhum SELECT. Pela Decisão 8, um grant
faltando NÃO gera erro em runtime — gera CONSULTA_INDISPONIVEL silencioso e a
alíquota geral da fase, que é EXATAMENTE a resposta de antes desta feature. É o
modo de falha mais perigoso possível: a feature "funciona" (200, verde) sem
fazer nada. Este script é o único lugar onde isso falha ruidosamente.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`, privilégio mínimo), não
com a URL do admin: usar a credencial administrativa aqui provaria que o DADO
existe, que já se sabe, e não que a API CONSEGUE lê-lo, que é a pergunta.

Sai com código 1 se: as contagens não forem 26/76/19; `04051000` (manteiga) não
resolver APLICADA no item 5; `02074300` (foie gras) não resolver
EXCLUIDA_EXPRESSAMENTE; ou o SELECT for negado por permissão.
"""

import os
import sys

import psycopg

from api.cesta_basica import ConsultaCestaBasica, SituacaoCestaBasica, resolver_item
from api.ncm import prefixos_ncm
from db.repositorio import buscar_cesta_basica_por_prefixo

ITENS_ESPERADOS = 26
INCLUSOES_ESPERADAS = 76
EXCECOES_ESPERADAS = 19


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _resolver(conexao, codigo: str):
    """O MESMO caminho de /v1/tax/simulate — lookup em lote e resolução pura —
    não um SELECT ad-hoc parecido. Verificar um caminho diferente do de produção
    deixaria justamente o caminho de produção por verificar."""
    linhas = buscar_cesta_basica_por_prefixo(conexao, prefixos_ncm(codigo))
    return resolver_item("MERCADORIA", codigo, ConsultaCestaBasica(True, linhas))


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

        with conexao.cursor() as cur:
            cur.execute("SELECT count(*) FROM cesta_basica_anexo_i")
            itens = cur.fetchone()[0]
            cur.execute(
                "SELECT excecao, count(*) FROM cesta_basica_anexo_i_ncm GROUP BY excecao"
            )
            contagens = dict(cur.fetchall())

        inclusoes = contagens.get(False, 0)
        excecoes = contagens.get(True, 0)
        if (itens, inclusoes, excecoes) != (
            ITENS_ESPERADOS,
            INCLUSOES_ESPERADAS,
            EXCECOES_ESPERADAS,
        ):
            _falhar(
                f"seed incompleto para o papel de runtime: {itens} itens, "
                f"{inclusoes} inclusões, {excecoes} exceções — esperado "
                f"{ITENS_ESPERADOS}/{INCLUSOES_ESPERADAS}/{EXCECOES_ESPERADAS}. "
                "Ou a migração 005 não foi aplicada, ou o INSERT foi truncado."
            )

        # Manteiga: correspondência exata, o caso do smoke test do deploy.
        manteiga = _resolver(conexao, "04051000")
        if manteiga.situacao is not SituacaoCestaBasica.APLICADA or manteiga.item != 5:
            _falhar(
                f"04051000 (manteiga) resolveu {manteiga.situacao} item="
                f"{manteiga.item!r}, esperado APLICADA no item 5."
            )

        # Foie gras: excluído pelo PRÓPRIO item 19. Se este vier APLICADA, a
        # feature estaria concedendo alíquota zero a um produto que o Anexo
        # exclui expressamente — erro na direção perigosa (tributo a menos).
        foie_gras = _resolver(conexao, "02074300")
        if foie_gras.situacao is not SituacaoCestaBasica.EXCLUIDA_EXPRESSAMENTE:
            _falhar(
                f"02074300 (foie gras) resolveu {foie_gras.situacao}, esperado "
                "EXCLUIDA_EXPRESSAMENTE. As exceções dos itens 19/20 não estão "
                "sendo respeitadas."
            )

        # Café: prefixo de 4 dígitos (posição 09.01), o comprimento que só
        # existe por causa dos 6 itens não-triviais.
        cafe = _resolver(conexao, "09012100")
        if cafe.situacao is not SituacaoCestaBasica.APLICADA or cafe.item != 8:
            _falhar(
                f"09012100 (café) resolveu {cafe.situacao} item={cafe.item!r}, "
                "esperado APLICADA no item 8 pela posição 09.01."
            )

        print(
            "CESTA BÁSICA VERIFICADA CONTRA O CLOUD SQL REAL: o papel de runtime "
            f"lê o Anexo I ({itens} itens, {inclusoes} inclusões, {excecoes} "
            f"exceções). 04051000 = item {manteiga.item} ({manteiga.texto_ncm}); "
            f"09012100 = item {cafe.item} ({cafe.texto_ncm}); 02074300 = excluído "
            f"pelo item {foie_gras.item} ({foie_gras.texto_ncm})."
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
            "Se for 'permission denied for table cesta_basica_anexo_i', o GRANT "
            "SELECT da migração 005 não chegou ao papel taxreformai_app. Se for "
            "'relation does not exist', a migração 005 não foi aplicada.",
            file=sys.stderr,
        )
        sys.exit(1)
