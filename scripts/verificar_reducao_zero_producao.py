"""Prova os 4 Anexos de redução a zero contra o Cloud SQL real, com o papel de
RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
o seed entra como `taxreformai_admin` (as migrações 005/007/008), e o GRANT para
`taxreformai_app` nunca é exercitado por nenhum SELECT. Pela degradação
conservadora, um grant faltando NÃO gera erro em runtime — gera
CONSULTA_INDISPONIVEL silencioso e a alíquota geral da fase, que é EXATAMENTE a
resposta de antes desta feature. É o modo de falha mais perigoso possível: a
feature "funciona" (200, verde) sem fazer nada. Este script é o único lugar onde
isso falha ruidosamente.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`, privilégio mínimo), não
com a URL do admin: usar a credencial administrativa aqui provaria que o DADO
existe, que já se sabe, e não que a API CONSEGUE lê-lo, que é a pergunta.

São 7 casos — 3 herdados do Anexo I, que provam a NÃO-REGRESSÃO, e 4 novos, um
para cada mecanismo que esta feature introduziu e que pode falhar sozinho sem
afetar o Anexo I: Anexo novo com sub-item, desempate de 3 vias, exceção operante
fora do Anexo I e o prefixo de 2 dígitos (Capítulo 6).

Sai com código 1 se: as contagens não forem 60/127/24; qualquer um dos 7 casos
resolver diferente do esperado; ou o SELECT for negado por permissão.
"""

import os
import sys

import psycopg

from api.ncm import prefixos_ncm
from api.reducao_zero import ConsultaReducaoZero, SituacaoReducaoZero, resolver_item
from db.repositorio import buscar_reducao_zero_por_prefixo

ITENS_ESPERADOS = 60
INCLUSOES_ESPERADAS = 127
EXCECOES_ESPERADAS = 24

# (código, situação, Anexo, item, motivo pelo qual este caso está na lista)
CASOS = [
    (
        "04051000",
        SituacaoReducaoZero.APLICADA,
        "I",
        "5",
        "manteiga — não-regressão do Anexo I (correspondência exata)",
    ),
    (
        "02074300",
        SituacaoReducaoZero.EXCLUIDA_EXPRESSAMENTE,
        "I",
        "19",
        "foie gras — não-regressão da exceção do Anexo I",
    ),
    (
        "09012100",
        SituacaoReducaoZero.APLICADA,
        "I",
        "8",
        "café — não-regressão do prefixo de 4 dígitos (posição 09.01)",
    ),
    (
        "87131000",
        SituacaoReducaoZero.APLICADA,
        "XIII",
        "2.1",
        "cadeira de rodas — Anexo NOVO, com sub-item e descrição de contexto",
    ),
    (
        "90181980",
        SituacaoReducaoZero.APLICADA,
        "XII",
        "1.2",
        "eletroencefalógrafo — desempate de 3 vias (itens 1.2, 1.3 e 14)",
    ),
    (
        "90213991",
        SituacaoReducaoZero.EXCLUIDA_EXPRESSAMENTE,
        "XII",
        "5",
        "prótese dentária — exceção operante FORA do Anexo I",
    ),
    (
        "06031100",
        SituacaoReducaoZero.APLICADA,
        "XV",
        "4",
        "flores — PREFIXO DE 2 DÍGITOS (Capítulo 6), o caso que pode falhar sozinho",
    ),
]


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _resolver(conexao, codigo: str):
    """O MESMO caminho de /v1/tax/simulate — lookup em lote e resolução pura —
    não um SELECT ad-hoc parecido. Verificar um caminho diferente do de produção
    deixaria justamente o caminho de produção por verificar."""
    linhas = buscar_reducao_zero_por_prefixo(conexao, prefixos_ncm(codigo))
    return resolver_item("MERCADORIA", codigo, ConsultaReducaoZero(True, linhas))


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
            cur.execute("SELECT count(*) FROM anexos_reducao_zero")
            itens = cur.fetchone()[0]
            cur.execute(
                "SELECT excecao, count(*) FROM anexos_reducao_zero_ncm GROUP BY excecao"
            )
            contagens = dict(cur.fetchall())
            cur.execute(
                "SELECT anexo, count(*) FROM anexos_reducao_zero "
                "GROUP BY anexo ORDER BY min(anexo_ordem)"
            )
            por_anexo = cur.fetchall()

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
                f"Por Anexo: {por_anexo}. Ou as migrações 007/008 não foram "
                "aplicadas, ou algum INSERT foi truncado."
            )

        for codigo, situacao, anexo, item, motivo in CASOS:
            resolucao = _resolver(conexao, codigo)
            if (resolucao.situacao, resolucao.anexo, resolucao.item) != (
                situacao,
                anexo,
                item,
            ):
                _falhar(
                    f"{codigo} ({motivo}) resolveu {resolucao.situacao} "
                    f"Anexo={resolucao.anexo!r} item={resolucao.item!r}, esperado "
                    f"{situacao} Anexo={anexo!r} item={item!r}."
                )
            print(
                f"  OK {codigo} → {resolucao.situacao.value} "
                f"Anexo {resolucao.anexo}, item {resolucao.item} "
                f"({resolucao.texto_ncm}) — {motivo}"
            )

        # Três verificações que a igualdade acima não cobre, uma por decisão de
        # design que só existe nesta feature.
        cadeira = _resolver(conexao, "87131000")
        if not cadeira.descricao_contexto:
            _falhar(
                "87131000 (cadeira de rodas) veio sem descricao_contexto: o LEFT "
                "JOIN do item-pai não trouxe o cabeçalho do item 2 do Anexo XIII, "
                'e a fundamentação seria só "Sem mecanismo de propulsão".'
            )

        eeg = _resolver(conexao, "90181980")
        if len(eeg.itens_correspondentes) != 3:
            _falhar(
                f"90181980 listou {len(eeg.itens_correspondentes)} correspondentes, "
                "esperado 3 (XII/1.2, XII/1.3 e XII/14). O seed do Anexo XII está "
                "incompleto ou o agrupamento por (anexo, item, sub_item) quebrou."
            )

        flores = _resolver(conexao, "06031100")
        if flores.texto_ncm != "06":
            _falhar(
                f"06031100 casou com {flores.texto_ncm!r}, esperado '06'. O prefixo "
                "de 2 dígitos é o único caso que pode falhar sozinho e em silêncio: "
                "se _COMPRIMENTOS_PREFIXO e a CHECK da migração 007 saírem de "
                "sincronia, todo o resto continua verde."
            )

        print(
            "REDUÇÃO A ZERO VERIFICADA CONTRA O CLOUD SQL REAL: o papel de runtime "
            f"lê os 4 Anexos ({itens} itens, {inclusoes} inclusões, {excecoes} "
            f"exceções; por Anexo: {por_anexo}). Os 7 casos resolveram como o "
            "DESIGN previu, incluindo o sub-item do Anexo XIII, o desempate triplo "
            "do Anexo XII e o Capítulo 6 do Anexo XV."
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
            "Se for 'permission denied for table anexos_reducao_zero', o GRANT "
            "SELECT da migração 007 não chegou ao papel taxreformai_app. Se for "
            "'relation does not exist', a migração 007 (que RENOMEIA as tabelas do "
            "Anexo I) não foi aplicada.",
            file=sys.stderr,
        )
        sys.exit(1)
