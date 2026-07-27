"""Parser da tabela TIPI (IPI por NCM) e escrita em `aliquotas_ipi_tipi`.

A TIPI não é um documento com hierarquia de artigos — é uma tabela
NCM → descrição → alíquota, então não usa o parser AST (`ast_parser.py`) nem
o de ementas (`ementa_parser.py`). É dado tabular, e vai para o Postgres, não
para o Qdrant — mesma razão da decisão de SPED/IBPT.

Duas armadilhas reais do texto extraído via `pdftotext -layout`, encontradas
ao inspecionar o PDF oficial da RFB (2026-07-27), não deduzidas:

1. "NT" (não tributado) é uma classificação tributária válida, distinta de
   uma alíquota explícita de 0% — não é ausência de dado.
2. Descrições de produto longas quebram em várias linhas (até 10, no
   documento real), e a alíquota aparece só na ÚLTIMA linha da descrição, não
   na linha onde o código NCM começa. Um parser que olhasse só a primeira
   linha do código perderia a alíquota de ~650 dos 9231 códigos completos.

Só códigos NCM completos (padrão `NNNN.NN.NN`) carregam alíquota — códigos
parciais (capítulo, posição) são cabeçalhos de categoria, sem alíquota
própria. Verificado: nenhum código completo no documento fica sem alíquota
depois de seguir as continuações.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_PADRAO_CODIGO = re.compile(r"^([0-9]{4}\.[0-9]{2}\.[0-9]{2})\s+(.*)$")
_PADRAO_VALOR_FINAL = re.compile(r"(NT|[0-9]+(?:,[0-9]+)?)\s*$")


@dataclass(frozen=True)
class LinhaTipi:
    ncm_code: str
    descricao: str
    aliquota_percentual: Decimal | None
    nao_tributado: bool


def _valor_para_fracao(valor: str) -> Decimal:
    """"3,25" (3,25%) -> Decimal("0.0325"). A TIPI imprime o número já como
    percentual, mesma convenção usada em `regime_atual.py` para as demais
    alíquotas — armazenar como fração, não como o percentual bruto."""
    return Decimal(valor.replace(",", ".")) / 100


def parse_tipi(texto: str) -> list[LinhaTipi]:
    linhas = texto.split("\n")
    resultado: list[LinhaTipi] = []

    for i, linha in enumerate(linhas):
        match_codigo = _PADRAO_CODIGO.match(linha)
        if not match_codigo:
            continue

        codigo, resto = match_codigo.groups()
        partes_descricao = [resto]

        match_valor = _PADRAO_VALOR_FINAL.search(resto)
        j = i
        while match_valor is None:
            j += 1
            if j >= len(linhas) or _PADRAO_CODIGO.match(linhas[j]):
                # Nenhum valor encontrado antes do próximo código (ou fim do
                # documento) — não observado no documento real, mas um código
                # sem alíquota não pode virar um valor inventado.
                break
            partes_descricao.append(linhas[j].strip())
            match_valor = _PADRAO_VALOR_FINAL.search(linhas[j])

        if match_valor is None:
            continue

        valor_bruto = match_valor.group(1)
        # O valor encontrado está embutido na última parte da descrição —
        # remove-o de lá antes de juntar o texto.
        partes_descricao[-1] = _PADRAO_VALOR_FINAL.sub("", partes_descricao[-1]).strip()
        descricao = " ".join(p for p in partes_descricao if p).strip()

        nao_tributado = valor_bruto == "NT"
        resultado.append(
            LinhaTipi(
                ncm_code=codigo,
                descricao=descricao,
                aliquota_percentual=None if nao_tributado else _valor_para_fracao(valor_bruto),
                nao_tributado=nao_tributado,
            )
        )

    return resultado


def gravar_tipi(
    conexao, linhas: list[LinhaTipi], dispositivo_legal_ref: str, lote: int = 200
) -> int:
    """Upsert em lotes — mesma razão de `TAMANHO_LOTE_UPSERT` no indexador do
    Qdrant: milhares de linhas numa transação só custam memória e tempo de
    lock sem necessidade, e um lote pequeno falha rápido e localizado."""
    if not linhas:
        return 0

    with conexao.cursor() as cur:
        for inicio in range(0, len(linhas), lote):
            for item in linhas[inicio : inicio + lote]:
                cur.execute(
                    """
                    INSERT INTO aliquotas_ipi_tipi
                        (ncm_code, descricao, aliquota_percentual, nao_tributado, dispositivo_legal_ref)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (ncm_code) DO UPDATE SET
                        descricao = EXCLUDED.descricao,
                        aliquota_percentual = EXCLUDED.aliquota_percentual,
                        nao_tributado = EXCLUDED.nao_tributado,
                        dispositivo_legal_ref = EXCLUDED.dispositivo_legal_ref,
                        updated_at = NOW()
                    """,
                    (
                        item.ncm_code,
                        item.descricao,
                        item.aliquota_percentual,
                        item.nao_tributado,
                        dispositivo_legal_ref,
                    ),
                )
    conexao.commit()
    return len(linhas)
