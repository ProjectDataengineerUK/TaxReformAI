"""Resolve os 10 Anexos de REDUÇÃO de CBS/IBS por NCM/SH da LCP 214/2025.

Dois mecanismos, uma resolução só:

- **Redução a ZERO** — Anexo I (art. 125, Cesta Básica), XII (art. 144, I,
  dispositivos médicos), XIII (art. 145, I, acessibilidade) e XV (art. 148,
  hortícolas/frutas/ovos). O art. 148 escreve "ficam reduzidas a ZERO" ainda que
  o cabeçalho do Anexo XV diga "redução de 100%": vale o dispositivo.
- **Redução de 60%** — Anexo IV (art. 131, dispositivos médicos), V (art. 132,
  acessibilidade), VI (art. 133, § 1º, nutrição enteral/parenteral), VII (art.
  135, alimentos), VIII (art. 136, higiene/limpeza) e IX (art. 138, insumos
  agropecuários).

**Por que uma resolução só, e não duas**: os dois grupos NÃO são independentes.
São 117 pares de prefixo em sobreposição, e em 35 deles o MESMO código de 8
dígitos está nos dois lados (`9018.90.99` é o XII/9 a zero e é 9 itens do Anexo
IV a 60%). Resolver em separado responderia 60% onde a lei dá zero. É isto — e
não a comodidade — que faz o desempate ter SEIS componentes e a consulta ser uma
só (Decisões 1 e 3).

Irmão de `api/ipi.py`: mesma garantia de não propagação de exceção, mesma
divisão em três camadas (SQL puro em `db/repositorio.py` → política aqui →
consumo em `api/routers/simulate.py`). A diferença é a DIREÇÃO da degradação —
aqui, não conseguir consultar significa aplicar a alíquota GERAL da fase, ou
seja, um tributo maior que o devido, nunca menor (Decisão 8 do Anexo I).

ATENÇÃO, e é a única exceção a esse conforto: os **14 prefixos de 2 dígitos**
(`tipo_correspondencia == "CAPITULO"`) erram na direção OPOSTA. Eles concedem a
redução a um capítulo INTEIRO da NCM enquanto o texto do item restringe por
destinação, natureza ou conformidade — o pior caso é o Capítulo 25 (Anexo IX,
item 3, "corretivos de solo"), que na NCM inclui cimento, mármore e gesso. O
erro possível ali é tributo A MENOS. Não é falha de degradação: é a lei citando
o capítulo inteiro, e a mitigação é dupla — `CAPITULO` torna o caso filtrável
por máquina (Decisão 7) e a `descricao` literal do item volta na resposta.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from functools import partial
from typing import Any

from api.ncm import digitos_ncm

logger = logging.getLogger("api.reducao")

UM = Decimal("1.0000")


class SituacaoReducao(StrEnum):
    APLICADA = "APLICADA"
    EXCLUIDA_EXPRESSAMENTE = "EXCLUIDA_EXPRESSAMENTE"  # o próprio item exclui o código
    FORA_DO_ANEXO = "FORA_DO_ANEXO"  # fora dos DEZ Anexos de redução por NCM
    NCM_NAO_RECONHECIDO = "NCM_NAO_RECONHECIDO"
    CONSULTA_INDISPONIVEL = "CONSULTA_INDISPONIVEL"
    NAO_APLICAVEL = "NAO_APLICAVEL"  # natureza == SERVICO


@dataclass(frozen=True)
class ConsultaReducao:
    """`disponivel` responde "consegui consultar?", nunca "achei alguma coisa?".

    Um lote em que nenhum prefixo casa é `disponivel=True` com `linhas` vazia —
    situação diferente do banco fora do ar.
    """

    disponivel: bool
    linhas: Sequence[Any] = field(default_factory=tuple)


def consultar_com_seguranca(pool: Any, prefixos: list[str]) -> ConsultaReducao:
    """Nunca levanta.

    `pool is None` (toda a suíte de testes e qualquer deploy sem Cloud SQL) é
    indisponibilidade, não ausência de dado.

    Lista vazia com pool presente é `disponivel=True`: não há NADA a perguntar,
    o que é diferente de não CONSEGUIR perguntar — mesma correção que o BUILD da
    feature 1 precisou fazer em `consultar_ipi_com_seguranca`, pelo mesmo
    motivo: senão um payload de NCMs todos ilegíveis acusaria o banco de um
    problema que está no payload. Nenhuma conexão é aberta nos dois casos.

    Também é aqui que cai a janela do rename das tabelas (Decisão 13): entre a
    migração 009 e o deploy da revisão nova, o `SELECT` fala com um nome que
    ainda/já não existe, vira `CONSULTA_INDISPONIVEL` e a simulação segue com a
    alíquota geral — 200, com `logger.exception` no Cloud Logging.

    Import tardio de `db.repositorio` pelo mesmo motivo de `api/audit.py`:
    `api.main` precisa importar sem `psycopg` instalado.
    """
    if pool is None:
        return ConsultaReducao(disponivel=False)
    if not prefixos:
        return ConsultaReducao(disponivel=True)

    try:
        from db.repositorio import buscar_reducao_por_prefixo

        with pool.connection() as conexao:
            return ConsultaReducao(
                disponivel=True,
                linhas=buscar_reducao_por_prefixo(conexao, prefixos),
            )
    except Exception:
        logger.exception(
            "Falha ao consultar os Anexos de redução (I, IV, V, VI, VII, VIII, IX, "
            "XII, XIII e XV) — a simulação segue com a alíquota geral da fase, "
            "declarado na resposta"
        )
        return ConsultaReducao(disponivel=False)


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
class ResolucaoReducao:
    situacao: SituacaoReducao
    anexo: str | None = None
    anexo_ordem: int | None = None
    item: str | None = None  # grafia canônica: "5", "1.2"
    # Fração da ALÍQUOTA removida, já EFETIVA para esta requisição: 1.0000
    # (zero) ou 0.6000 (60%). Um item dos Anexos IV/V/VI com comprador
    # qualificado devolve 1.0000, não 0.6000 — arts. 144, II; 145, II; 146, §2º.
    percentual_reducao: Decimal | None = None
    dispositivo_legal_ref: str | None = None
    # Não-nulo em TODO item dos Anexos IV, V e VI: com `comprador_tipo` ausente
    # é o aviso de que a alíquota real seria zero; com ele presente é a
    # fundamentação do zero aplicado.
    dispositivo_legal_comprador: str | None = None
    # True quando 60% foi aplicado MAS a alíquota seria zero se o comprador
    # fosse órgão público/entidade CEBAS e o payload tivesse informado.
    zero_por_comprador_disponivel: bool = False
    descricao: str | None = None
    descricao_contexto: str | None = None
    texto_ncm: str | None = None
    tipo_correspondencia: str | None = None  # EXATO | PREFIXO | CAPITULO | EXCECAO
    itens_correspondentes: tuple[tuple[str, str], ...] = ()
    # Itens que EXCLUEM expressamente este código, mesmo quando outro item o
    # inclui (Decisão 8): o cogumelo é retirado do XV/2 e incluído pelo VII/14.
    itens_excluidos: tuple[tuple[str, str], ...] = ()

    @property
    def aplicada(self) -> bool:
        return self.situacao is SituacaoReducao.APLICADA

    @property
    def avaliada(self) -> bool:
        """Serviço e "fora dos Anexos" são respostas conhecidas; só as duas
        situações abaixo significam "não sei" (Decisão 9 do Anexo I)."""
        return self.situacao not in (
            SituacaoReducao.CONSULTA_INDISPONIVEL,
            SituacaoReducao.NCM_NAO_RECONHECIDO,
        )


def _percentual_efetivo(linha: Any, comprador_qualificado: bool) -> Decimal:
    """O percentual que de fato se aplica a ESTA requisição.

    Os arts. 144, II; 145, II e 146, § 2º reduzem a ZERO — não a 60% — os
    Anexos IV, V e VI quando o adquirente é órgão da administração pública
    direta/autarquia/fundação pública ou entidade de saúde imune com CEBAS
    comprovando prestação de serviços ao SUS. É condição sobre o COMPRADOR,
    então só pode ser avaliada com `comprador_tipo` no payload (Decisão 6).
    """
    if comprador_qualificado and linha.zero_por_comprador_ref is not None:
        return UM
    return linha.percentual_reducao


def _chave_especificidade(
    linha: Any, comprador_qualificado: bool
) -> tuple[int, Decimal, Decimal, int, int, int]:
    """Mais específico primeiro, com `max()`:

    1. prefixo mais LONGO — a única regra que a lei escreve para todos os casos,
       e a que honra sozinha a remissão expressa do Anexo VII ("ressalvados os
       produtos relacionados no Anexo I"): nos 13 pares em que isso importa, o
       prefixo do Anexo zero é estritamente mais longo (provado por asserção na
       migração 010, não afirmado aqui);
    2. MAIOR redução — decide os 35 pares em que os dois grupos citam o mesmo
       código de 8 dígitos e não há especificidade que os separe (`9018.90.99`
       é XII/9 a zero e 9 itens do Anexo IV a 60%). A escolha entre 0% e 40% da
       alíquota não pode cair num ordinal de Anexo;
    3. redução INCONDICIONAL antes da condicionada — quando o comprador é
       qualificado, um item do IV e um do XII passam a valer zero os dois;
       citar o art. 144, I é mais forte na defesa fiscal que citar o art. 144,
       II, porque não depende de provar a qualidade do comprador;
    4-6. ordem do documento legal (Anexo, item, sub-item) — o Anexo entra antes
       do item porque item só é comparável dentro de um Anexo (todo Anexo tem um
       item 1), e o sub-item depois, porque só existe dentro de um item.

    Ordem TOTAL, portanto determinística (a UNIQUE `(anexo, item, sub_item,
    prefixo, excecao)` garante que não existem duas linhas distintas com a chave
    inteira igual): sem ela, `2106.90.90` citaria ora I/4, ora I/26, ora um dos
    8 itens do Anexo VI, conforme a ordem em que o Postgres devolvesse as linhas
    — não-determinismo que só apareceria em produção, num campo que o cliente
    leva para uma defesa fiscal.

    `anexo_ordem` e `percentual_reducao` vêm do catálogo no banco, não de mapas
    em Python: duas declarações da mesma verdade divergem no primeiro Anexo novo.
    """
    return (
        len(linha.prefixo),
        _percentual_efetivo(linha, comprador_qualificado),
        linha.percentual_reducao,
        -linha.anexo_ordem,
        -linha.item,
        -linha.sub_item,
    )


def _tipo_correspondencia(prefixo: str) -> str:
    """EXATO (8) · CAPITULO (2) · PREFIXO (4-7).

    `CAPITULO` existe porque um prefixo de 2 dígitos cobre um capítulo INTEIRO
    da NCM — o Capítulo 25 do Anexo IX/3 inclui cimento, mármore e gesso,
    enquanto o item fala de corretivos de solo. É a única classe de
    correspondência cujo erro é na direção PERIGOSA (tributo a menos), e por
    isso é a única que o cliente consegue filtrar por máquina (Decisão 7).

    O corte em 2 não é arbitrário: é o único nível da NCM em que um prefixo
    cobre milhares de códigos. De 4 a 7 (posição/subposição/item) a
    correspondência ainda é razoavelmente específica.

    Derivado, nunca lido de uma coluna: dado derivado não pode divergir do dado
    que o gera (Decisão 1 do Anexo I).
    """
    if len(prefixo) == 8:
        return "EXATO"
    if len(prefixo) == 2:
        return "CAPITULO"
    return "PREFIXO"


def _ordenar_correspondentes(linhas: Iterable[Any]) -> tuple[tuple[str, str], ...]:
    """Ordem NUMÉRICA por (Anexo, item, sub-item) — nunca lexicográfica: como
    string, "10" viria antes de "2", invertendo o que a lei quer dizer.

    Sem limite artificial: 9 itens do Anexo IV citam `9018.90.99` e 10 itens do
    Anexo VI citam `2922.49.90`. Truncar a lista seria esconder do auditor
    exatamente o que ele foi procurar.
    """
    ordenadas = sorted(
        linhas, key=lambda linha: (linha.anexo_ordem, linha.item, linha.sub_item)
    )
    return tuple(
        (linha.anexo, formatar_item(linha.item, linha.sub_item)) for linha in ordenadas
    )


def resolver_item(
    natureza: str,
    ncm: str,
    consulta: ConsultaReducao,
    comprador_tipo: str | None = None,
) -> ResolucaoReducao:
    """Função pura — AT-001..AT-013 são testáveis sem banco e sem HTTP.

    A ordem das guardas é a mesma de `api/ipi.py::resolver_item`, pela mesma
    razão: um código que não canoniza para 8 dígitos é propriedade do payload,
    não do banco, e reportá-lo como CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta.

    `comprador_tipo` é DECLARATÓRIO: a simulação não verifica imunidade, não
    valida CEBAS e não consulta o SUS. Ele só escolhe um `Decimal` em memória e
    nunca chega ao SQL.
    """
    if natureza == "SERVICO":
        return ResolucaoReducao(SituacaoReducao.NAO_APLICAVEL)

    codigo = digitos_ncm(ncm)
    if codigo is None:
        return ResolucaoReducao(SituacaoReducao.NCM_NAO_RECONHECIDO)

    if not consulta.disponivel:
        return ResolucaoReducao(SituacaoReducao.CONSULTA_INDISPONIVEL)

    qualificado = comprador_tipo is not None
    chave = partial(_chave_especificidade, comprador_qualificado=qualificado)

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
        # nenhum outro item, nem de outro Anexo. É por isso que um cogumelo
        # (excluído do XV/2) recebe 60% pelo VII/14: ele não é "relacionado no
        # Anexo XV", é RETIRADO de lá (Decisão 8).
        excecoes = [linha for linha in linhas if linha.excecao]
        (exclusoes if excecoes else inclusoes).append(max(excecoes or linhas, key=chave))

    if inclusoes:
        vencedora = max(inclusoes, key=chave)
        return ResolucaoReducao(
            situacao=SituacaoReducao.APLICADA,
            anexo=vencedora.anexo,
            anexo_ordem=vencedora.anexo_ordem,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            percentual_reducao=_percentual_efetivo(vencedora, qualificado),
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            # Citado SEMPRE que o Anexo tem a condição — informado ou não. Com
            # `comprador_tipo` ausente é o aviso de que a alíquota real pode ser
            # ZERO; com ele presente é a fundamentação do zero aplicado.
            dispositivo_legal_comprador=vencedora.zero_por_comprador_ref,
            zero_por_comprador_disponivel=(
                vencedora.zero_por_comprador_ref is not None and not qualificado
            ),
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia=_tipo_correspondencia(vencedora.prefixo),
            itens_correspondentes=_ordenar_correspondentes(inclusoes),
            # Sempre preenchido quando houve exclusão, mesmo que uma inclusão
            # tenha vencido: é o que transforma o caso confuso do cogumelo em
            # caso inspecionável — "60% pelo VII/14" E "o XV/2 exclui
            # expressamente este código", que é o raciocínio de um auditor.
            itens_excluidos=_ordenar_correspondentes(exclusoes),
        )

    if exclusoes:
        vencedora = max(exclusoes, key=chave)
        return ResolucaoReducao(
            situacao=SituacaoReducao.EXCLUIDA_EXPRESSAMENTE,
            anexo=vencedora.anexo,
            anexo_ordem=vencedora.anexo_ordem,
            item=formatar_item(vencedora.item, vencedora.sub_item),
            dispositivo_legal_ref=vencedora.dispositivo_legal_ref,
            descricao=vencedora.descricao,
            descricao_contexto=vencedora.descricao_contexto,
            texto_ncm=vencedora.texto_ncm,
            tipo_correspondencia="EXCECAO",
            itens_correspondentes=_ordenar_correspondentes(exclusoes),
            itens_excluidos=_ordenar_correspondentes(exclusoes),
        )

    return ResolucaoReducao(SituacaoReducao.FORA_DO_ANEXO)
