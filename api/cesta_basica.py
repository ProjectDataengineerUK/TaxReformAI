"""Resolve a Cesta Básica Nacional (LCP 214/2025, art. 125, Anexo I) por NCM.

Irmão de `api/ipi.py`: mesma garantia de não propagação de exceção, mesma
divisão em três camadas (SQL puro em `db/repositorio.py` → política aqui →
consumo em `api/routers/simulate.py`). A diferença é a DIREÇÃO da degradação —
aqui, não conseguir consultar significa aplicar a alíquota GERAL da fase, ou
seja, um tributo maior que o devido, nunca menor (Decisão 8). No IPI o número
ausente era o próprio tributo; aqui é uma redução, e não aplicá-la erra para
cima, que é recuperável.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm

logger = logging.getLogger("api.cesta_basica")


class SituacaoCestaBasica(StrEnum):
    APLICADA = "APLICADA"
    EXCLUIDA_EXPRESSAMENTE = "EXCLUIDA_EXPRESSAMENTE"  # o próprio Anexo exclui o código
    FORA_DO_ANEXO = "FORA_DO_ANEXO"
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaCestaBasica:
    """`disponivel` responde "consegui consultar?", nunca "achei alguma coisa?".

    Um lote em que nenhum prefixo casa é `disponivel=True` com `linhas` vazia —
    situação diferente do banco fora do ar.
    """

    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaCestaBasica:
    """Nunca levanta.

    `pool is None` (toda a suíte de testes e qualquer deploy sem Cloud SQL) é
    indisponibilidade, não ausência de dado.

    Lista vazia com pool presente é `disponivel=True`: não há NADA a perguntar,
    o que é diferente de não CONSEGUIR perguntar — mesma correção que o BUILD da
    feature 1 precisou fazer em `consultar_ipi_com_seguranca`, pelo mesmo
    motivo: senão um payload de NCMs todos ilegíveis acusaria o banco de um
    problema que está no payload. Nenhuma conexão é aberta nos dois casos.

    Import tardio de `db.repositorio` pelo mesmo motivo de `api/audit.py`:
    `api.main` precisa importar sem `psycopg` instalado.
    """
    if pool is None:
        return ConsultaCestaBasica(disponivel=False)
    if not prefixos:
        return ConsultaCestaBasica(disponivel=True)

    try:
        from db.repositorio import buscar_cesta_basica_por_prefixo

        with pool.connection() as conexao:
            return ConsultaCestaBasica(
                disponivel=True,
                linhas=buscar_cesta_basica_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar a Cesta Básica (Anexo I) — a simulação segue com a "
            "alíquota geral da fase, declarado na resposta"
        )
        return ConsultaCestaBasica(disponivel=False)


@dataclass(frozen=True)
class ResolucaoCestaBasica:
    situacao: SituacaoCestaBasica
    item: int | None = None
    dispositivo_legal_ref: str | None = None
    descricao: str | None = None
    texto_ncm: str | None = None
    tipo_correspondencia: str | None = None  # EXATO | PREFIXO | EXCECAO
    itens_correspondentes: tuple[int, ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoCestaBasica.APLICADA

    @property
    def avaliada(self) -> bool:
        """Serviço e "fora do anexo" são respostas conhecidas; só as duas
        situações abaixo significam "não sei" (Decisão 9)."""
        return self.situacao not in (
            SituacaoCestaBasica.CONSULTA_INDISPONIVEL,
            SituacaoCestaBasica.NCM_NAO_RECONHECIDO,
        )


def _mais_especifica(linhas: Iterable[Any]) -> Any:
    """Prefixo mais longo; empate resolvido pelo MENOR número de item.

    Ordenação total e determinística: sem ela, `1902.19.00` citaria ora o item 15
    (massas alimentícias) ora o 25 (massas de baixo teor de proteína) conforme a
    ordem em que o Postgres devolveu as linhas — não-determinismo que só
    apareceria em produção (Decisão 4).
    """
    return max(linhas, key=lambda linha: (len(linha.prefixo), -linha.item))


def resolver_item(
    natureza: str, ncm: str, consulta: ConsultaCestaBasica
) -> ResolucaoCestaBasica:
    """Função pura — AT-001..AT-005 são testáveis sem banco e sem HTTP.

    A ordem das guardas é a mesma de `api/ipi.py::resolver_item`, pela mesma
    razão: um código que não canoniza para 8 dígitos é propriedade do payload,
    não do banco, e reportá-lo como CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta.
    """
    if natureza == "SERVICO":
        return ResolucaoCestaBasica(SituacaoCestaBasica.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoCestaBasica(SituacaoCestaBasica.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoCestaBasica(SituacaoCestaBasica.CONSULTA_INDISPONIVEL)

    por_item: dict[int, list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        # O lote traz os prefixos de TODOS os códigos do payload — filtrar aqui
        # é o que impede um item casar com o prefixo de outra mercadoria.
        if codigo.startswith(linha.prefixo):
            por_item[linha.item].append(linha)

    inclusoes, exclusoes = [], []
    for linhas in por_item.values():
        # Exceção do PRÓPRIO item vence a inclusão do próprio item — e não toca
        # nenhum outro item (Decisão 3).
        excecoes = [linha for linha in linhas if linha.excecao]
        if excecoes:
            exclusoes.append(_mais_especifica(excecoes))
        else:
            inclusoes.append(_mais_especifica(linhas))

    if inclusoes:
        vencedora = _mais_especifica(inclusoes)
        return ResolucaoCestaBasica(
            situacao=SituacaoCestaBasica.APLICADA,
            item=vencedora.item,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            texto_ncm=vencedora.texto_ncm,
            # Derivado, nunca lido de uma coluna: dado derivado não pode
            # divergir do dado que o gera (Decisão 1).
            tipo_correspondencia="EXATO" if len(vencedora.prefixo) == 8 else "PREFIXO",
            itens_correspondentes=tuple(sorted(linha.item for linha in inclusoes)),
        )

    if exclusoes:
        vencedora = _mais_especifica(exclusoes)
        return ResolucaoCestaBasica(
            situacao=SituacaoCestaBasica.EXCLUIDA_EXPRESSAMENTE,
            item=vencedora.item,
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXCECAO",
            itens_correspondentes=tuple(sorted(linha.item for linha in exclusoes)),
        )

    return ResolucaoCestaBasica(SituacaoCestaBasica.FORA_DO_ANEXO)
