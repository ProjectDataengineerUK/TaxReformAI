"""Prova a base de incidência do Imposto Seletivo (LCP 214/2025, art. 409,
Anexo XVII) contra o Cloud SQL real, com o papel de RUNTIME.

Mesmo padrão dos scripts anteriores: o seed entra como `taxreformai_admin`, e
o GRANT para `taxreformai_app` nunca é exercitado por nenhum SELECT. Pela
degradação conservadora, um grant faltando NÃO gera erro em runtime — gera
CONSULTA_INDISPONIVEL silencioso e o item simplesmente não é classificado
(nunca afeta CBS/IBS/IPI, que vivem em consultas separadas). Este script é o
único lugar onde isso falha ruidosamente.

Conecta com `DATABASE_URL_APP` (papel `taxreformai_app`), nunca com a URL do
admin — usar a credencial administrativa provaria que o DADO existe, não que
a API CONSEGUE lê-lo.

Casos: veículo (happy path, com a exceção de uso sempre declarada), fumígeno
(condição de embalagem primária, com e sem confirmação), bebida açucarada
(sem condição), exceção de código (8802.60.00), e um NCM fora das 6
categorias (prova negativa).

Sai com código 1 se: as contagens não forem 6 categorias/24 prefixos;
qualquer caso resolver diferente do esperado; ou o SELECT for negado por
permissão.
"""

import os
import sys

import psycopg

from api.imposto_seletivo import (
    ConsultaImpostoSeletivo,
    SituacaoImpostoSeletivo,
    resolver_item,
)
from api.ncm import prefixos_ncm
from db.repositorio import buscar_incidencia_is_por_prefixo

ITENS_ESPERADOS = 6
PREFIXOS_ESPERADOS = 24


def _falhar(mensagem: str) -> None:
    print(f"FALHA: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _resolver(conexao, ncm: str, embalagem_primaria_consumidor_final: bool | None = None):
    """O MESMO caminho de /v1/tax/simulate — lookup em lote e resolução pura."""
    from api.ncm import digitos_ncm

    codigo = digitos_ncm(ncm)
    linhas = buscar_incidencia_is_por_prefixo(conexao, prefixos_ncm(codigo))
    return resolver_item(
        "MERCADORIA", ncm, ConsultaImpostoSeletivo(True, linhas),
        embalagem_primaria_consumidor_final,
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
            cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia")
            itens = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM imposto_seletivo_incidencia_ncm")
            prefixos = cur.fetchone()[0]

        if (itens, prefixos) != (ITENS_ESPERADOS, PREFIXOS_ESPERADOS):
            _falhar(
                f"seed incompleto para o papel de runtime: {itens} categorias, "
                f"{prefixos} prefixos — esperado {ITENS_ESPERADOS}/{PREFIXOS_ESPERADOS}. "
                "Ou a migração 013 não foi aplicada, ou algum INSERT foi truncado."
            )

        veiculo = _resolver(conexao, "8704.21.10")
        if veiculo.situacao is not SituacaoImpostoSeletivo.SUJEITO or veiculo.excecao_uso_ref is None:
            _falhar(
                f"8704.21.10 (veículo) resolveu {veiculo.situacao}, "
                f"excecao_uso_ref={veiculo.excecao_uso_ref!r} — esperado SUJEITO com a "
                "ressalva de uso sempre declarada."
            )
        print(f"  OK 8704.21.10 → SUJEITO, categoria={veiculo.categoria!r}")

        fumigeno_sem = _resolver(conexao, "2402.20.00")
        if fumigeno_sem.situacao is not SituacaoImpostoSeletivo.CONDICAO_NAO_SATISFEITA:
            _falhar(
                f"2402.20.00 sem embalagem_primaria_consumidor_final resolveu "
                f"{fumigeno_sem.situacao}, esperado CONDICAO_NAO_SATISFEITA."
            )
        fumigeno_com = _resolver(conexao, "2402.20.00", embalagem_primaria_consumidor_final=True)
        if fumigeno_com.situacao is not SituacaoImpostoSeletivo.SUJEITO:
            _falhar(
                f"2402.20.00 com embalagem_primaria_consumidor_final=True resolveu "
                f"{fumigeno_com.situacao}, esperado SUJEITO."
            )
        print("  OK 2402.20.00 → condição de embalagem primária respeitada nos dois sentidos")

        bebida = _resolver(conexao, "2202.10.00")
        if bebida.situacao is not SituacaoImpostoSeletivo.SUJEITO or bebida.condicao_embalagem_primaria_ref is not None:
            _falhar(
                f"2202.10.00 (bebida açucarada) resolveu {bebida.situacao} com condição "
                f"{bebida.condicao_embalagem_primaria_ref!r} — esperado SUJEITO sem condição."
            )
        print("  OK 2202.10.00 (bebida açucarada) → SUJEITO, sem condição")

        excluida = _resolver(conexao, "8802.60.00")
        if excluida.situacao is not SituacaoImpostoSeletivo.NAO_SUJEITO:
            _falhar(
                f"8802.60.00 (exceção de código) resolveu {excluida.situacao}, "
                "esperado NAO_SUJEITO."
            )
        print("  OK 8802.60.00 → NAO_SUJEITO (exceção de código)")

        fora = _resolver(conexao, "04051000")
        if fora.situacao is not SituacaoImpostoSeletivo.NAO_SUJEITO or fora.categoria is not None:
            _falhar(
                f"04051000 (manteiga, fora das 6 categorias) resolveu {fora.situacao} "
                f"categoria={fora.categoria!r} — esperado NAO_SUJEITO sem categoria."
            )
        print("  OK 04051000 (manteiga) → NAO_SUJEITO, fora da base")

        print(
            "BASE DE INCIDÊNCIA DO IMPOSTO SELETIVO VERIFICADA CONTRA O CLOUD SQL REAL: "
            f"o papel de runtime lê as {itens} categorias / {prefixos} prefixos. Os casos "
            "resolveram como o DESIGN previu, incluindo a condição de embalagem primária "
            "e a exceção de código 8802.60.00."
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
            "Se for 'permission denied for table imposto_seletivo_incidencia' (ou "
            "'..._ncm'), o GRANT SELECT da migração 013 não chegou ao papel "
            "taxreformai_app. Se for 'relation does not exist', a migração 013 não "
            "foi aplicada.",
            file=sys.stderr,
        )
        sys.exit(1)
