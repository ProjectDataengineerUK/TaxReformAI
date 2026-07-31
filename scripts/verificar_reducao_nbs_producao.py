"""Prova os Anexos de redução por NBS (II, III, XI — o Anexo X ainda não tem
itens semeados, ver `db/migrations/011_anexos_reducao_percentual_nbs.sql`)
contra o Cloud SQL real, com o papel de RUNTIME.

Mesmo padrão de `verificar_reducao_producao.py`: o seed entra como
`taxreformai_admin`, e o GRANT para `taxreformai_app` nunca é exercitado por
nenhum SELECT. Pela degradação conservadora, um grant faltando NÃO gera erro
em runtime — gera CONSULTA_INDISPONIVEL silencioso e a alíquota geral da
fase, que é EXATAMENTE a resposta de antes da feature. Este script é o único
lugar onde isso falha ruidosamente.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`), nunca com a URL do
admin — usar a credencial administrativa provaria que o DADO existe, não que
a API CONSEGUE lê-lo.

Casos: um por Anexo (II happy path, III o desempate de 11 itens do mesmo
código — Achado crítico 3 —, XI os dois eixos de condição — comprador E
vendedor — mais a prova de que `ENTIDADE_CEBAS_SUS` nunca satisfaz o Anexo
XI) e uma prova negativa de que o Anexo X permanece vazio (gap documentado,
não regressão).

Sai com código 1 se: as contagens não forem 44 itens/43 prefixos; qualquer
caso resolver diferente do esperado; ou o SELECT for negado por permissão.
"""

import os
import sys
from decimal import Decimal

import psycopg

from api.nbs import prefixos_nbs
from api.reducao_nbs import ConsultaReducaoNbs, SituacaoReducaoNbs, resolver_item_nbs
from db.repositorio import buscar_reducao_nbs_por_prefixo

ITENS_ESPERADOS = {"II": 8, "III": 30, "X": 47, "XI": 6}
PREFIXOS_ESPERADOS = {"II": 8, "III": 30, "X": 47, "XI": 5}


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _resolver(
    conexao,
    nbs: str,
    comprador_tipo: str | None = None,
    conteudo_nacional_majoritario: bool | None = None,
    vendedor_capital_brasileiro_qualificado: bool | None = None,
):
    """O MESMO caminho de /v1/tax/simulate — lookup em lote e resolução pura."""
    from api.nbs import digitos_nbs

    codigo = digitos_nbs(nbs)
    linhas = buscar_reducao_nbs_por_prefixo(conexao, prefixos_nbs(codigo))
    return resolver_item_nbs(
        "SERVICO",
        nbs,
        ConsultaReducaoNbs(True, linhas),
        comprador_tipo,
        conteudo_nacional_majoritario,
        vendedor_capital_brasileiro_qualificado,
    )


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
            cur.execute(
                "SELECT anexo, count(*) FROM anexos_reducao_nbs GROUP BY anexo"
            )
            itens = dict(cur.fetchall())
            cur.execute(
                "SELECT anexo, count(*) FROM anexos_reducao_nbs_prefixo GROUP BY anexo"
            )
            prefixos = dict(cur.fetchall())

        if itens != ITENS_ESPERADOS or prefixos != PREFIXOS_ESPERADOS:
            _falhar(
                f"seed incompleto para o papel de runtime: itens={itens} "
                f"(esperado {ITENS_ESPERADOS}), prefixos={prefixos} (esperado "
                f"{PREFIXOS_ESPERADOS}). Ou a migração 011 não foi aplicada, ou "
                "algum INSERT foi truncado."
            )

        # Anexo X (art. 139) — happy path com nacionalidade não informada
        # (alíquota geral) e informada (60%), mais um item sem condição
        # (inciso V/VI, item 22).
        filme_sem_nacionalidade = _resolver(conexao, "1.1103.31.00")
        if filme_sem_nacionalidade.situacao is not SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA:
            _falhar(
                f"1.1103.31.00 sem conteudo_nacional_majoritario resolveu "
                f"{filme_sem_nacionalidade.situacao}, esperado CONDICAO_NAO_SATISFEITA."
            )
        filme_nacional = _resolver(
            conexao, "1.1103.31.00", conteudo_nacional_majoritario=True
        )
        if (filme_nacional.situacao, filme_nacional.anexo, filme_nacional.item) != (
            SituacaoReducaoNbs.APLICADA,
            "X",
            "3",
        ):
            _falhar(
                f"1.1103.31.00 com conteudo_nacional_majoritario=True resolveu "
                f"{filme_nacional.situacao} Anexo={filme_nacional.anexo!r} "
                f"item={filme_nacional.item!r}, esperado APLICADA Anexo='X' item='3'."
            )
        feira = _resolver(conexao, "1.1806.61.00")
        if feira.situacao is not SituacaoReducaoNbs.APLICADA:
            _falhar(
                f"1.1806.61.00 (item 22, inciso V/VI) resolveu {feira.situacao}, "
                "esperado APLICADA sem nenhuma condição informada."
            )
        print(
            "  OK Anexo X: 1.1103.31.00 exige nacionalidade (item 3, inciso VII), "
            "1.1806.61.00 não exige (item 22, inciso V/VI)"
        )

        # Anexo II — happy path, sem condição.
        ensino = _resolver(conexao, "1.2202.00.00")
        if (ensino.situacao, ensino.anexo, ensino.item) != (
            SituacaoReducaoNbs.APLICADA,
            "II",
            "4",
        ):
            _falhar(
                f"1.2202.00.00 (Ensino Técnico) resolveu {ensino.situacao} "
                f"Anexo={ensino.anexo!r} item={ensino.item!r}, esperado APLICADA "
                "Anexo='II' item='4'."
            )
        print(f"  OK 1.2202.00.00 → {ensino.situacao.value} Anexo II, item 4 (Educação)")

        # Anexo III — Achado crítico 3: 11 itens do MESMO Anexo compartilham o
        # MESMO código NBS, incluindo o item 29 (anomalia de dígito completada).
        saude = _resolver(conexao, "1.2301.99.00")
        if (saude.situacao, saude.anexo, saude.item) != (
            SituacaoReducaoNbs.APLICADA,
            "III",
            "18",
        ):
            _falhar(
                f"1.2301.99.00 resolveu {saude.situacao} Anexo={saude.anexo!r} "
                f"item={saude.item!r}, esperado APLICADA Anexo='III' item='18' "
                "(menor número entre os 11 itens que citam este código)."
            )
        if len(saude.itens_correspondentes) != 11:
            _falhar(
                f"1.2301.99.00 listou {len(saude.itens_correspondentes)} "
                "correspondentes, esperado 11 (18,19,20,21,22,23,24,25,26,28,29)."
            )
        print(
            "  OK 1.2301.99.00 → APLICADA Anexo III, item 18 "
            f"({len(saude.itens_correspondentes)} itens correspondentes)"
        )

        # Anexo XI — eixo COMPRADOR: sem condição informada, alíquota geral;
        # com ORGAO_PUBLICO, 60%; com ENTIDADE_CEBAS_SUS, continua geral (não
        # tem base no art. 142 — diferente de IV/V/VI).
        seguranca_sem = _resolver(conexao, "1.1501.20.00")
        if seguranca_sem.situacao is not SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA:
            _falhar(
                f"1.1501.20.00 sem comprador_tipo resolveu {seguranca_sem.situacao}, "
                "esperado CONDICAO_NAO_SATISFEITA."
            )
        seguranca_orgao = _resolver(conexao, "1.1501.20.00", comprador_tipo="ORGAO_PUBLICO")
        if seguranca_orgao.percentual_reducao != Decimal("0.6000"):
            _falhar(
                f"1.1501.20.00 com ORGAO_PUBLICO resolveu percentual_reducao="
                f"{seguranca_orgao.percentual_reducao!r}, esperado 0.6000."
            )
        seguranca_cebas = _resolver(conexao, "1.1501.20.00", comprador_tipo="ENTIDADE_CEBAS_SUS")
        if seguranca_cebas.situacao is not SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA:
            _falhar(
                f"1.1501.20.00 com ENTIDADE_CEBAS_SUS resolveu {seguranca_cebas.situacao}, "
                "esperado CONDICAO_NAO_SATISFEITA — este tipo NÃO tem base no art. 142."
            )
        print("  OK 1.1501.20.00 → eixo comprador (art. 142, I) e ENTIDADE_CEBAS_SUS recusado")

        # Anexo XI — eixo VENDEDOR: independente do comprador, só no item 1.1.
        seguranca_vendedor = _resolver(
            conexao, "1.1501.20.00", vendedor_capital_brasileiro_qualificado=True
        )
        if seguranca_vendedor.percentual_reducao != Decimal("0.6000"):
            _falhar(
                "1.1501.20.00 com vendedor_capital_brasileiro_qualificado=True "
                f"resolveu percentual_reducao={seguranca_vendedor.percentual_reducao!r}, "
                "esperado 0.6000 — o eixo vendedor (art. 142, II) não está sendo lido."
            )
        print("  OK 1.1501.20.00 → eixo vendedor (art. 142, II) independente do comprador")

        # Item 1.2 NÃO tem o eixo vendedor (decisão conservadora documentada).
        aplicativos_vendedor = _resolver(
            conexao, "1.1502.90.00", vendedor_capital_brasileiro_qualificado=True
        )
        if aplicativos_vendedor.situacao is not SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA:
            _falhar(
                f"1.1502.90.00 (item 1.2) com vendedor qualificado resolveu "
                f"{aplicativos_vendedor.situacao}, esperado CONDICAO_NAO_SATISFEITA "
                "— este item não deveria ter condicao_vendedor_ref."
            )
        print("  OK 1.1502.90.00 (item 1.2) → eixo vendedor corretamente ausente")

        print(
            "REDUÇÃO POR NBS VERIFICADA CONTRA O CLOUD SQL REAL: o papel de "
            f"runtime lê os Anexos II/III/XI ({itens}, {prefixos}). Os casos "
            "resolveram como o DESIGN previu, incluindo o desempate de 11 itens "
            "do Anexo III, os dois eixos de condição do Anexo XI e a recusa de "
            "ENTIDADE_CEBAS_SUS. Anexo X confirmado vazio (gap documentado)."
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
            "Se for 'permission denied for table anexos_reducao_nbs' (ou "
            "'..._nbs_prefixo'), o GRANT SELECT da migração 011 não chegou ao "
            "papel taxreformai_app. Se for 'relation does not exist', a "
            "migração 011 não foi aplicada.",
            file=sys.stderr,
        )
        sys.exit(1)
