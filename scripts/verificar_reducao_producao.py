"""Prova os 10 Anexos de redução (4 a zero + 6 percentuais) contra o Cloud SQL
real, com o papel de RUNTIME.

Roda só via `migrar_banco.yml` (guarda MIGRAR), nunca local. O ponto é o papel:
o seed entra como `taxreformai_admin` (as migrações 005/007/008/009/010), e o
GRANT para `taxreformai_app` nunca é exercitado por nenhum SELECT. Pela
degradação conservadora, um grant faltando NÃO gera erro em runtime — gera
CONSULTA_INDISPONIVEL silencioso e a alíquota geral da fase, que é EXATAMENTE a
resposta de antes da feature. É o modo de falha mais perigoso possível: a
feature "funciona" (200, verde) sem fazer nada. Este script é o único lugar onde
isso falha ruidosamente.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`, privilégio mínimo), não
com a URL do admin: usar a credencial administrativa aqui provaria que o DADO
existe, que já se sabe, e não que a API CONSEGUE lê-lo, que é a pergunta.

Casos: os 7 já herdados da feature anterior (Anexos I/XII/XIII/XV, prova de
NÃO-REGRESSÃO) mais os novos desta feature — a precedência normativa Anexo
I/XV sobre o Anexo VII (AT-002/AT-003), o desempate de especificidade com
`comprador_tipo` (AT-010/AT-010b) e o prefixo multi-capítulo (AT-007).

Sai com código 1 se: as contagens não forem 321/508/32; qualquer caso resolver
diferente do esperado; ou o SELECT for negado por permissão.
"""

import os
import sys
from decimal import Decimal

import psycopg

from api.ncm import prefixos_ncm
from api.reducao import ConsultaReducao, SituacaoReducao, resolver_item
from db.repositorio import buscar_reducao_por_prefixo

ITENS_ESPERADOS = 321
INCLUSOES_ESPERADAS = 508
EXCECOES_ESPERADAS = 32

# (código, situação, Anexo, item, motivo pelo qual este caso está na lista)
CASOS = [
    (
        "04051000",
        SituacaoReducao.APLICADA,
        "I",
        "5",
        "manteiga — não-regressão do Anexo I (correspondência exata)",
    ),
    (
        "02074300",
        SituacaoReducao.EXCLUIDA_EXPRESSAMENTE,
        "I",
        "19",
        "foie gras — não-regressão da exceção do Anexo I",
    ),
    (
        "09012100",
        SituacaoReducao.APLICADA,
        "I",
        "8",
        "café — não-regressão do prefixo de 4 dígitos (posição 09.01)",
    ),
    (
        "87131000",
        SituacaoReducao.APLICADA,
        "XIII",
        "2.1",
        "cadeira de rodas — Anexo NOVO, com sub-item e descrição de contexto",
    ),
    (
        "90181980",
        SituacaoReducao.APLICADA,
        "XII",
        "1.2",
        "eletroencefalógrafo — desempate de 3 vias (itens 1.2, 1.3 e 14)",
    ),
    (
        "90213991",
        SituacaoReducao.EXCLUIDA_EXPRESSAMENTE,
        "XII",
        "5",
        "prótese dentária — exceção operante FORA do Anexo I",
    ),
    (
        "06031100",
        SituacaoReducao.APLICADA,
        "XV",
        "4",
        "flores — PREFIXO DE 2 DÍGITOS (Capítulo 6), o caso que pode falhar sozinho",
    ),
    (
        "34011190",
        SituacaoReducao.APLICADA,
        "VIII",
        "1",
        "sabão de toucador — AT-001, primeiro caso de 60% (não zero)",
    ),
    (
        "10063021",
        SituacaoReducao.APLICADA,
        "I",
        "1",
        "arroz — AT-002, precedência normativa: Anexo I (zero) vence o Anexo "
        "VII/15 (60%) para o mesmo NCM, exatamente como a lei escreve",
    ),
    (
        "08031000",
        SituacaoReducao.APLICADA,
        "XV",
        "3",
        "banana — AT-003, a remissão dupla do item 14 do Anexo VII cede ao "
        "Anexo XV, não só ao Anexo I",
    ),
    (
        "87089910",
        SituacaoReducao.APLICADA,
        "V",
        "1.1",
        "comando de embreagem manual — AT-006, sub-item do Anexo V com "
        "condição de comprador disponível e não informada",
    ),
    (
        "11090000",
        SituacaoReducao.APLICADA,
        "IX",
        "19",
        "glúten de trigo — AT-007, item que cita 3 capítulos (10, 11 e 12) "
        "ao mesmo tempo",
    ),
    (
        "22030000",
        SituacaoReducao.FORA_DO_ANEXO,
        None,
        None,
        "cerveja — AT-013, fora de todos os 10 Anexos, alíquota geral",
    ),
]


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _resolver(conexao, codigo: str, comprador_tipo: str | None = None):
    """O MESMO caminho de /v1/tax/simulate — lookup em lote e resolução pura —
    não um SELECT ad-hoc parecido. Verificar um caminho diferente do de produção
    deixaria justamente o caminho de produção por verificar."""
    linhas = buscar_reducao_por_prefixo(conexao, prefixos_ncm(codigo))
    return resolver_item("MERCADORIA", codigo, ConsultaReducao(True, linhas), comprador_tipo)


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
            cur.execute("SELECT count(*) FROM anexos_reducao")
            itens = cur.fetchone()[0]
            cur.execute(
                "SELECT excecao, count(*) FROM anexos_reducao_ncm GROUP BY excecao"
            )
            contagens = dict(cur.fetchall())
            cur.execute(
                "SELECT anexo, count(*) FROM anexos_reducao "
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
                f"Por Anexo: {por_anexo}. Ou as migrações 007/008/009/010 não "
                "foram aplicadas, ou algum INSERT foi truncado."
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

        # AT-010/AT-010b: o mesmo NCM, com e sem `comprador_tipo` — prova que a
        # condição de comprador dos Anexos IV/V/VI é lida do catálogo, não
        # hardcoded, e que o desempate prefere o zero quando ele se aplica.
        sem_comprador = _resolver(conexao, "39269030")
        if sem_comprador.percentual_reducao != Decimal("0.6"):
            _falhar(
                f"39269030 sem comprador_tipo resolveu percentual_reducao="
                f"{sem_comprador.percentual_reducao!r}, esperado 0.6 (60%)."
            )
        if not sem_comprador.zero_por_comprador_disponivel:
            _falhar(
                "39269030 (Anexo IV) veio com zero_por_comprador_disponivel=False — "
                "a condição do art. 144, II não foi carregada no catálogo."
            )

        com_comprador = _resolver(conexao, "39269030", comprador_tipo="ORGAO_PUBLICO")
        if com_comprador.percentual_reducao != 1:
            _falhar(
                f"39269030 COM comprador_tipo=ORGAO_PUBLICO resolveu percentual_reducao="
                f"{com_comprador.percentual_reducao!r}, esperado 1 (zero) — a condição "
                "de comprador não está sendo aplicada no desempate."
            )

        print(
            "REDUÇÃO VERIFICADA CONTRA O CLOUD SQL REAL: o papel de runtime lê "
            f"os 10 Anexos ({itens} itens, {inclusoes} inclusões, {excecoes} "
            f"exceções; por Anexo: {por_anexo}). Os {len(CASOS)} casos resolveram "
            "como o DESIGN previu, incluindo a precedência normativa Anexo I/XV "
            "sobre o Anexo VII, o multi-capítulo do Anexo IX e a condição de "
            "comprador dos Anexos IV/V/VI."
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
            "Se for 'permission denied for table anexos_reducao', o GRANT "
            "SELECT da migração 007 não chegou ao papel taxreformai_app. Se for "
            "'relation does not exist', a migração 007 (que RENOMEIA as tabelas do "
            "Anexo I) não foi aplicada.",
            file=sys.stderr,
        )
        sys.exit(1)
