"""Resolve os 4 Anexos de REDUÇÃO A ZERO de CBS/IBS da LCP 214/2025 por NCM.

São eles: Anexo I (art. 125, Cesta Básica Nacional), Anexo XII (art. 144,
dispositivos médicos), Anexo XIII (art. 145, dispositivos de acessibilidade) e
Anexo XV (art. 148, produtos hortícolas, frutas e ovos). O art. 148 escreve
"ficam reduzidas a ZERO" ainda que o cabeçalho do Anexo XV diga "redução de
100%": vale o dispositivo, e por isso os quatro moram na mesma tabela e usam a
mesma função de cálculo (`aplicar_reducao_a_zero`), sem nenhum percentual.

Irmão de `api/ipi.py`: mesma garantia de não propagação de exceção, mesma
divisão em três camadas (SQL puro em `db/repositorio.py` → política aqui →
consumo em `api/routers/simulate.py`). A diferença é a DIREÇÃO da degradação —
aqui, não conseguir consultar significa aplicar a alíquota GERAL da fase, ou
seja, um tributo maior que o devido, nunca menor (Decisão 8 do Anexo I). No IPI
o número ausente era o próprio tributo; aqui é uma redução, e não aplicá-la erra
para cima, que é recuperável.

ATENÇÃO, e é a única exceção a esse conforto: o prefixo de 2 dígitos do Anexo
XV, item 4 ("Capítulo 6") erra na direção OPOSTA. Ele concede alíquota zero a
todo o capítulo, enquanto o texto do item qualifica ("relativos à horticultura e
cultivados para fins alimentares, ornamentais ou medicinais") — qualificação que
RESTRINGE e que o payload (`sku`, `ncm`, quantidade, valor) não permite
verificar. O erro possível ali é tributo A MENOS. Não é falha de degradação: é a
lei citando o capítulo inteiro, e a mitigação é declarativa — a `descricao`
literal do item volta na resposta e `fonte_legal` diz que as condições textuais
de cada item não são verificadas.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from api.ncm import digitos_ncm

logger = logging.getLogger("api.reducao_zero")


class SituacaoReducaoZero(StrEnum):
    APLICADA = "APLICADA"
    EXCLUIDA_EXPRESSAMENTE = "EXCLUIDA_EXPRESSAMENTE"  # o próprio Anexo exclui o código
    FORA_DO_ANEXO = "FORA_DO_ANEXO"  # fora dos QUATRO Anexos de alíquota zero
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaReducaoZero:
    """`disponivel` responde "consegui consultar?", nunca "achei alguma coisa?".

    Um lote em que nenhum prefixo casa é `disponivel=True` com `linhas` vazia —
    situação diferente do banco fora do ar.
    """

    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaReducaoZero:
    """Nunca levanta.

    `pool is None` (toda a suíte de testes e qualquer deploy sem Cloud SQL) é
    indisponibilidade, não ausência de dado.

    Lista vazia com pool presente é `disponivel=True`: não há NADA a perguntar,
    o que é diferente de não CONSEGUIR perguntar — mesma correção que o BUILD da
    feature 1 precisou fazer em `consultar_ipi_com_seguranca`, pelo mesmo
    motivo: senão um payload de NCMs todos ilegíveis acusaria o banco de um
    problema que está no payload. Nenhuma conexão é aberta nos dois casos.

    Também é aqui que cai a janela do rename das tabelas (Decisão 13): entre a
    migração 007 e o deploy da revisão nova, o `SELECT` fala com um nome que
    ainda/já não existe, vira `CONSULTA_INDISPONIVEL` e a simulação segue com a
    alíquota geral — 200, com `logger.exception` no Cloud Logging.

    Import tardio de `db.repositorio` pelo mesmo motivo de `api/audit.py`:
    `api.main` precisa importar sem `psycopg` instalado.
    """
    if pool is None:
        return ConsultaReducaoZero(disponivel=False)
    if not prefixos:
        return ConsultaReducaoZero(disponivel=True)

    try:
        from db.repositorio import buscar_reducao_zero_por_prefixo

        with pool.connection() as conexao:
            return ConsultaReducaoZero(
                disponivel=True,
                linhas=buscar_reducao_zero_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar os Anexos de redução a zero (I, XII, XIII, XV) — a "
            "simulação segue com a alíquota geral da fase, declarado na resposta"
        )
        return ConsultaReducaoZero(disponivel=False)


def formatar_item(item: int, sub_item: int) -> str:
    """Grafia canônica do DOU: "5", "1.2".

    DERIVADA da chave `(item, sub_item)`, nunca armazenada — e a CHECK
    `dispositivo_cita_o_proprio_item` (migração 007) garante que a citação legal
    gravada termina exatamente com esta string. `sub_item = 0` é o sentinela de
    "este item não tem sub-item": a lei numera a partir de 1 e jamais escreve
    "item 1.0".
    """
    return f"{item}.{sub_item}" if sub_item else str(item)


@dataclass(frozen=True)
class ResolucaoReducaoZero:
    situacao: SituacaoReducaoZero
    anexo: str | None = None
    item: str | None = None  # grafia canônica: "5", "1.2"
    dispositivo_legal_ref: str | None = None
    descricao: str | None = None
    descricao_contexto: str | None = None
    texto_ncm: str | None = None
    tipo_correspondencia: str | None = None  # EXATO | PREFIXO | EXCECAO
    itens_correspondentes: tuple[tuple[str, str], ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoReducaoZero.APLICADA

    @property
    def avaliada(self) -> bool:
        """Serviço e "fora dos Anexos" são respostas conhecidas; só as duas
        situações abaixo significam "não sei" (Decisão 9 do Anexo I)."""
        return self.situacao not in (
            SituacaoReducaoZero.CONSULTA_INDISPONIVEL,
            SituacaoReducaoZero.NCM_NAO_RECONHECIDO,
        )


def _chave_especificidade(linha: Any) -> tuple[int, int, int, int]:
    """Mais específico primeiro, com `max()`: prefixo mais longo; empate →
    menor Anexo; → menor item; → menor sub-item.

    Os dois critérios originais do Anexo I (comprimento, menor item) continuam
    sendo o 1º e o 3º — a ordem dos componentes é a ordem da hierarquia do
    documento legal: o Anexo entra antes do item porque item só é comparável
    dentro de um Anexo (todo Anexo tem um item 1), e o sub-item entra depois,
    porque só existe dentro de um item.

    Ordem TOTAL, portanto determinística: sem ela, `9018.19.80` citaria ora
    "Eletroencefalógrafos" (XII/1.2) ora "Monitor multiparâmetros" (XII/14)
    conforme a ordem em que o Postgres devolveu as linhas — não-determinismo que
    só apareceria em produção, num campo que o cliente leva para uma defesa
    fiscal (Decisão 5).

    `anexo_ordem` vem da coluna, não de um mapa romano→número aqui: numeral
    romano não ordena lexicograficamente, e duas declarações da mesma verdade
    divergem no primeiro Anexo novo.
    """
    return (len(linha.prefixo), -linha.anexo_ordem, -linha.item, -linha.sub_item)


def _ordenar_correspondentes(linhas: Iterable[Any]) -> tuple[tuple[str, str], ...]:
    """Ordem NUMÉRICA por (Anexo, item, sub-item) — nunca lexicográfica: como
    string, "14" < "1.2", que inverte o que a lei quer dizer."""
    ordenadas = sorted(
        linhas, key=lambda linha: (linha.anexo_ordem, linha.item, linha.sub_item)
    )
    return tuple(
        (linha.anexo, formatar_item(linha.item, linha.sub_item)) for linha in ordenadas
    )


def resolver_item(
    natureza: str, ncm: str, consulta: ConsultaReducaoZero
) -> ResolucaoReducaoZero:
    """Função pura — AT-001..AT-010 são testáveis sem banco e sem HTTP.

    A ordem das guardas é a mesma de `api/ipi.py::resolver_item`, pela mesma
    razão: um código que não canoniza para 8 dígitos é propriedade do payload,
    não do banco, e reportá-lo como CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta.
    """
    if natureza == "SERVICO":
        return ResolucaoReducaoZero(SituacaoReducaoZero.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoReducaoZero(SituacaoReducaoZero.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoReducaoZero(SituacaoReducaoZero.CONSULTA_INDISPONIVEL)

    # A chave do agrupamento é o ITEM INTEIRO — (anexo, item, sub_item) —, não
    # `item`: todo Anexo tem um item 1, e 1.2 e 1.3 são itens distintos que
    # citam o mesmo código (Anexo XII).
    por_item: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for linha in consulta.linhas:
        # O lote traz os prefixos de TODOS os códigos do payload — filtrar aqui
        # é o que impede um item casar com o prefixo de outra mercadoria.
        if codigo.startswith(linha.prefixo):
            por_item[(linha.anexo, linha.item, linha.sub_item)].append(linha)

    inclusoes, exclusoes = [], []
    for linhas in por_item.values():
        # Exceção do PRÓPRIO item vence a inclusão do próprio item — e não toca
        # nenhum outro item, nem de outro Anexo (Decisão 3 do Anexo I).
        excecoes = [linha for linha in linhas if linha.excecao]
        if excecoes:
            exclusoes.append(max(excecoes, key=_chave_especificidade))
        else:
            inclusoes.append(max(linhas, key=_chave_especificidade))

    if inclusoes:
        vencedora = max(inclusoes, key=_chave_especificidade)
        return ResolucaoReducaoZero(
            situacao=SituacaoReducaoZero.APLICADA,
            anexo=vencedora.anexo,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            # Derivado, nunca lido de uma coluna: dado derivado não pode
            # divergir do dado que o gera (Decisão 1 do Anexo I).
            tipo_correspondencia="EXATO" if len(vencedora.prefixo) == 8 else "PREFIXO",
            itens_correspondentes=_ordenar_correspondentes(inclusoes),
        )

    if exclusoes:
        vencedora = max(exclusoes, key=_chave_especificidade)
        return ResolucaoReducaoZero(
            situacao=SituacaoReducaoZero.EXCLUIDA_EXPRESSAMENTE,
            anexo=vencedora.anexo,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXCECAO",
            itens_correspondentes=_ordenar_correspondentes(exclusoes),
        )

    return ResolucaoReducaoZero(SituacaoReducaoZero.FORA_DO_ANEXO)
