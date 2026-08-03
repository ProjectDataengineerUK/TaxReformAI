"""Acesso a dados com isolamento de tenant garantido pelo banco.

O ponto central deste módulo é `sessao_do_tenant`: toda operação sobre dados de
cliente passa por uma transação que declarou `app.tenant_id`. A policy de RLS
(migração 002) usa essa variável, então esquecer de declará-la resulta em zero
linhas — nunca em linhas de outro tenant.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ParecerAuditado:
    tenant_id: UUID
    prompt_consulta: str
    resposta_parecer_md: str
    contexto_recuperado_ids: list[str]
    payload_calculo: dict[str, Any]
    user_id: UUID | None = None


@dataclass(frozen=True)
class AliquotaIpi:
    """Uma linha de `aliquotas_ipi_tipi` (migração 004).

    `aliquota_percentual` é NULL exatamente quando `nao_tributado` é true — a
    CHECK `aliquota_xor_nao_tributado` torna os dois mutuamente exclusivos no
    banco. "NT" é classificação tributária da própria TIPI, não alíquota 0%.
    """

    ncm_code: str
    aliquota_percentual: Decimal | None
    nao_tributado: bool
    dispositivo_legal_ref: str


def buscar_ipi_por_ncm(conexao, ncms: list[str]) -> dict[str, AliquotaIpi]:
    """Lookup em lote da TIPI. Sem RLS: como `anexos_reducao`, é dado legal
    público, igual para todo tenant.

    UMA query para N códigos — `= ANY(%s)` com uma lista Python é o idioma
    nativo do psycopg para lote e usa `idx_aliquotas_ipi_ncm`. Um laço de
    `buscar_ipi(ncm)` seriam até 100 round-trips ao Cloud SQL por requisição.

    Propaga exceção de propósito: quem decide degradar é `api/ipi.py`, não este
    módulo (ver Decisão 6 do DESIGN). NCM ausente simplesmente não aparece no
    dicionário — o chamador distingue ausência de falha porque falha vira
    exceção, nunca um dicionário vazio.
    """
    if not ncms:
        return {}

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT ncm_code, aliquota_percentual, nao_tributado, dispositivo_legal_ref
            FROM aliquotas_ipi_tipi
            WHERE ncm_code = ANY(%s)
            """,
            (list(ncms),),
        )
        linhas = cur.fetchall()

    return {
        linha[0]: AliquotaIpi(
            ncm_code=linha[0],
            aliquota_percentual=linha[1],
            nao_tributado=linha[2],
            dispositivo_legal_ref=linha[3],
        )
        for linha in linhas
    }


@dataclass(frozen=True)
class PrefixoReducao:
    """Uma linha de `anexos_reducao_ncm` com o item e o Anexo já resolvidos.

    `excecao=True` significa que este prefixo EXCLUI a mercadoria do item — e
    exclui só DESTE item, nunca dos demais. A lei escreve a exclusão dentro do
    item ("9021.3 [...] exceto os produtos classificados nos códigos 9021.39.91
    e 9021.39.99"), então uma exceção global permitiria que uma exclusão do
    Anexo XV anulasse uma inclusão do Anexo XII sem que ninguém tivesse
    escrito isso.

    `anexo_ordem` e `percentual_reducao` vêm do CATÁLOGO (migração 009), não de
    constantes em Python: com dois lugares declarando a mesma verdade, o dia em
    que só um for atualizado produz ora uma ordem de desempate silenciosamente
    errada, ora o percentual do Anexo vizinho.

    `percentual_reducao` é a FRAÇÃO DA ALÍQUOTA REMOVIDA — 1.0000 para os
    Anexos de redução a zero (I, XII, XIII, XV), 0.6000 para os de 60% (IV, V,
    VI, VII, VIII, IX).

    `zero_por_comprador_ref` é não-nulo só nos Anexos IV, V e VI, e é o que
    permite ao runtime aplicar ZERO (não 60%) quando o payload informa
    `comprador_tipo` — arts. 144, II; 145, II; 146, § 2º.

    `descricao_contexto` é a descrição do item-pai quando esta linha pertence a
    um sub-item — sem ela, a resposta citaria "Sem mecanismo de propulsão"
    (Anexo XIII, item 2.1) como fundamentação legal de uma cadeira de rodas
    (Decisão 7 da feature anterior).
    """

    anexo: str
    anexo_ordem: int
    percentual_reducao: Decimal
    zero_por_comprador_ref: str | None
    item: int
    sub_item: int
    prefixo: str
    excecao: bool
    texto_ncm: str
    alinea: str | None
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str


def buscar_reducao_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoReducao]:
    """Lookup em lote dos 10 Anexos de redução por NCM. Sem RLS: dado legal
    público, igual para todo tenant.

    UMA query — e ela precisa ser uma só, não por economia: a resposta certa
    depende de comparar linhas dos dois grupos entre si (117 pares de prefixo em
    sobreposição entre os 4 Anexos de zero e os 6 de 60%, inclusive o MESMO
    código de 8 dígitos). Duas consultas devolveriam duas listas que alguém
    teria de reconciliar em Python, com a ordem de desempate declarada em dois
    lugares.

    Devolve tanto inclusões quanto exceções — uma exceção só é relevante quando
    ela própria é prefixo do código, então ela cai no mesmo `= ANY` e não
    precisa de segunda consulta.

    O `= ANY(%s)` com lista Python é o mesmo idioma de `buscar_ipi_por_ncm`, e é
    o que a Decisão 2 do Anexo I preserva ao expandir o prefixo do lado do
    Python: a coluna fica do lado curto da igualdade, o índice continua valendo
    e nenhum trecho de SQL precisa saber o que conta como prefixo.

    Propaga exceção de propósito: quem decide degradar é `api/reducao.py`
    (mesma divisão da Decisão 6 do DESIGN de IPI_TIPI_MOTOR_CALCULO). Lista
    vazia de retorno significa "nenhum prefixo casou", nunca "falhou".
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT c.anexo, c.anexo_ordem, c.percentual_reducao,
                   c.zero_por_comprador_ref,
                   p.item, p.sub_item, p.prefixo, p.excecao,
                   p.texto_ncm, p.alinea, i.descricao, pai.descricao,
                   i.dispositivo_legal_ref
            FROM anexos_reducao_ncm p
            JOIN anexos_reducao i
              ON i.anexo = p.anexo AND i.item = p.item AND i.sub_item = p.sub_item
            JOIN anexos_reducao_catalogo c ON c.anexo = i.anexo
            LEFT JOIN anexos_reducao pai
              ON pai.anexo = i.anexo AND pai.item = i.item
             AND pai.sub_item = 0 AND i.sub_item > 0
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoReducao(*linha) for linha in cur.fetchall()]


@dataclass(frozen=True)
class PrefixoReducaoNbs:
    """Uma linha de `anexos_reducao_nbs_prefixo` com o item e o Anexo já
    resolvidos — irmã de `PrefixoReducao`, mas para o vocabulário NBS.

    `anexo_ordem` e `percentual_reducao` vêm do MESMO catálogo
    (`anexos_reducao_catalogo`) que já descreve os 10 Anexos NCM: II, III, X e
    XI só ganharam 4 linhas novas ali (Decisão 1 do DESIGN).

    As três colunas de condição são nulas quando o item NÃO exige a condição
    correspondente (Anexo II e III inteiros); `condicao_comprador_ref` e
    `condicao_vendedor_ref` são eixos INDEPENDENTES do Anexo XI (comprador OU
    vendedor, nunca os dois exigidos ao mesmo tempo) — ver Decisão 4 do
    DESIGN. `condicao_nacionalidade_ref` é do Anexo X, que esta migração NÃO
    semeia ainda (ver o cabeçalho da migração 011) — a coluna existe para
    quando a leitura do art. 139 for possível, sem exigir nova migração de
    schema.

    `descricao_contexto` é a descrição do item-pai quando esta linha pertence
    a um sub-item (Anexo XI, item 1 "Serviços") — mesmo mecanismo de
    self-join de `PrefixoReducao`, nunca uma coluna própria.
    """

    anexo: str
    anexo_ordem: int
    percentual_reducao: Decimal
    item: int
    sub_item: int
    prefixo: str
    texto_nbs: str
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str
    condicao_nacionalidade_ref: str | None
    condicao_comprador_ref: str | None
    condicao_vendedor_ref: str | None


def buscar_reducao_nbs_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoReducaoNbs]:
    """Lookup em lote dos Anexos de redução por NBS. Sem RLS: dado legal
    público, igual para todo tenant — mesmo padrão de `buscar_reducao_por_prefixo`.

    Consulta PRÓPRIA, sobre tabelas PRÓPRIAS (`anexos_reducao_nbs` /
    `anexos_reducao_nbs_prefixo`) — nunca a mesma consulta do NCM com um
    filtro de vocabulário a mais: um prefixo NBS truncado de 5 dígitos tem o
    MESMO comprimento que um prefixo NCM válido de 5 dígitos, e só tabelas
    separadas tornam essa colisão estruturalmente impossível (Achado crítico
    4 do /define; Decisão 1 do DESIGN).

    Propaga exceção de propósito: quem decide degradar é `api/reducao_nbs.py`
    (mesma divisão das features anteriores). Lista vazia de retorno significa
    "nenhum prefixo casou", nunca "falhou".
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT c.anexo, c.anexo_ordem, c.percentual_reducao,
                   p.item, p.sub_item, p.prefixo, p.texto_nbs,
                   i.descricao, pai.descricao, i.dispositivo_legal_ref,
                   i.condicao_nacionalidade_ref, i.condicao_comprador_ref,
                   i.condicao_vendedor_ref
            FROM anexos_reducao_nbs_prefixo p
            JOIN anexos_reducao_nbs i
              ON i.anexo = p.anexo AND i.item = p.item AND i.sub_item = p.sub_item
            JOIN anexos_reducao_catalogo c ON c.anexo = i.anexo
            LEFT JOIN anexos_reducao_nbs pai
              ON pai.anexo = i.anexo AND pai.item = i.item
             AND pai.sub_item = 0 AND i.sub_item > 0
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoReducaoNbs(*linha) for linha in cur.fetchall()]


@dataclass(frozen=True)
class PrefixoIncidenciaIS:
    """Uma linha de `imposto_seletivo_incidencia_ncm` com a categoria (inciso)
    já resolvida — irmã de `PrefixoReducao`, mas SEM percentual: o Imposto
    Seletivo (LCP 214/2025, art. 409) não tem alíquota fixada, e este
    dataclass nunca a expressa (nem como `None` — o campo simplesmente não
    existe, Decisão 1 do DESIGN_ANEXO_XVII_IMPOSTO_SELETIVO_INCIDENCIA.md).

    `condicao_embalagem_primaria_ref` é não-nula só nos incisos III/IV
    (fumígenos, bebidas alcoólicas — art. 409, §2º). `excecao_uso_ref` é
    não-nula só nos incisos I/II (veículos, aeronaves/embarcações) — citada
    SEMPRE que a categoria casa, porque a exceção de finalidade de uso
    (Forças Armadas/Segurança Pública) nunca é verificada por este projeto.

    `excecao=True` só em `8802.60.00` — exclusão por CÓDIGO específico,
    diferente da exceção de uso (que não tem código próprio a apontar).
    """

    inciso: int
    categoria: str
    dispositivo_legal_ref: str
    condicao_embalagem_primaria_ref: str | None
    excecao_uso_ref: str | None
    prefixo: str
    excecao: bool
    texto_ncm: str


def buscar_incidencia_is_por_prefixo(conexao, prefixos: list[str]) -> list[PrefixoIncidenciaIS]:
    """Lookup em lote da base de incidência do Imposto Seletivo. Sem RLS:
    dado legal público, igual para todo tenant — mesmo padrão das demais
    consultas deste módulo.

    Consulta PRÓPRIA, sobre tabelas PRÓPRIAS (`imposto_seletivo_incidencia`/
    `imposto_seletivo_incidencia_ncm`) — sem desempate cross-categoria: as 6
    categorias com código cobrem faixas de NCM disjuntas, provado pela
    própria migração 013 (Decisão 2 do DESIGN).

    Propaga exceção de propósito: quem decide degradar é
    `api/imposto_seletivo.py` (mesma divisão de responsabilidade das demais
    features). Lista vazia de retorno significa "nenhum prefixo casou",
    nunca "falhou".
    """
    if not prefixos:
        return []

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT i.inciso, i.categoria, i.dispositivo_legal_ref,
                   i.condicao_embalagem_primaria_ref, i.excecao_uso_ref,
                   p.prefixo, p.excecao, p.texto_ncm
            FROM imposto_seletivo_incidencia_ncm p
            JOIN imposto_seletivo_incidencia i ON i.inciso = p.inciso
            WHERE p.prefixo = ANY(%s)
            """,
            (list(prefixos),),
        )
        # A ordem dos campos do SELECT é a ordem do dataclass — se um mudar, o
        # outro muda junto.
        return [PrefixoIncidenciaIS(*linha) for linha in cur.fetchall()]


@contextmanager
def sessao_do_tenant(conexao, tenant_id: UUID):
    """Transação com `app.tenant_id` declarado, para o RLS enxergar o tenant.

    O escopo é a transação (`is_local=true`): a variável não vaza para a próxima
    operação que reusar a mesma conexão de um pool. Sem isso, uma conexão
    devolvida ao pool carregaria o tenant do request anterior — vazamento entre
    clientes difícil de reproduzir e fácil de não notar.
    """
    try:
        with conexao.cursor() as cur:
            # set_config(), não `SET LOCAL app.tenant_id = %s`: SET é comando
            # utilitário do PostgreSQL e NÃO aceita parâmetro vinculado —
            # devolve `syntax error at or near "$1"`. Interpolar o UUID na
            # string seria injeção de SQL num ponto que decide isolamento entre
            # clientes. set_config é função e aceita parâmetro; o terceiro
            # argumento `true` é o is_local, equivalente ao LOCAL do SET.
            cur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
            yield cur
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise


def resolver_tenant(conexao, identificador: str) -> UUID | None:
    """Aceita UUID ou slug.

    A API em produção mapeia `API_KEYS` para strings livres ("taxreformai-dev")
    enquanto o schema exige UUID. Aceitar os dois permite migrar o secret sem
    derrubar o serviço no meio — ver Decisão 2 do DESIGN.
    """
    try:
        return UUID(identificador)
    except (ValueError, AttributeError):
        pass

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT id FROM tenants WHERE slug = %s AND ativo IS TRUE", (identificador,)
        )
        linha = cur.fetchone()
    return linha[0] if linha else None


@dataclass(frozen=True)
class SkuCatalogo:
    id: UUID
    tenant_id: UUID
    codigo_sku: str
    descricao: str
    natureza: str
    ncm_code: str | None
    nbs_code: str | None
    created_at: datetime


def criar_sku(
    conexao,
    tenant_id: UUID,
    codigo_sku: str,
    descricao: str,
    natureza: str,
    ncm_code: str | None,
    nbs_code: str | None,
) -> SkuCatalogo:
    """Levanta psycopg.errors.UniqueViolation em codigo_sku duplicado no mesmo
    tenant — o router traduz para 409, não esta função."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            """,
            (str(tenant_id), codigo_sku, descricao, natureza, ncm_code, nbs_code),
        )
        return SkuCatalogo(*cur.fetchone())


def listar_skus(
    conexao, tenant_id: UUID, pagina: int, tamanho_pagina: int
) -> tuple[list[SkuCatalogo], int]:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute("SELECT count(*) FROM empresa_skus")
        total = cur.fetchone()[0]
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus ORDER BY created_at DESC, id LIMIT %s OFFSET %s
            """,
            (tamanho_pagina, (pagina - 1) * tamanho_pagina),
        )
        itens = [SkuCatalogo(*linha) for linha in cur.fetchall()]
    return itens, total


def buscar_sku(conexao, tenant_id: UUID, codigo_sku: str) -> SkuCatalogo | None:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus WHERE codigo_sku = %s
            """,
            (codigo_sku,),
        )
        linha = cur.fetchone()
    return SkuCatalogo(*linha) if linha else None


def atualizar_sku(
    conexao,
    tenant_id: UUID,
    codigo_sku: str,
    descricao: str,
    natureza: str,
    ncm_code: str | None,
    nbs_code: str | None,
) -> SkuCatalogo | None:
    """Substituição TOTAL das colunas mutáveis — o router monta os valores
    finais (merge do payload PATCH sobre o registro existente) antes de chamar
    esta função, para nunca precisar de SQL dinâmico."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            UPDATE empresa_skus SET descricao=%s, natureza=%s, ncm_code=%s, nbs_code=%s
            WHERE codigo_sku=%s
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            """,
            (descricao, natureza, ncm_code, nbs_code, codigo_sku),
        )
        linha = cur.fetchone()
    return SkuCatalogo(*linha) if linha else None


def excluir_sku(conexao, tenant_id: UUID, codigo_sku: str) -> bool:
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute("DELETE FROM empresa_skus WHERE codigo_sku=%s", (codigo_sku,))
        apagado = cur.rowcount > 0
    return apagado


def upsert_sku(
    conexao,
    tenant_id: UUID,
    codigo_sku: str,
    descricao: str,
    natureza: str,
    ncm_code: str | None,
    nbs_code: str | None,
) -> tuple[SkuCatalogo, bool]:
    """`(xmax = 0)` é o truque padrão do Postgres para distinguir INSERT de
    UPDATE num só INSERT ... ON CONFLICT — evita um SELECT prévio (condição de
    corrida) só para saber se o SKU já existia."""
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO empresa_skus (tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, codigo_sku) DO UPDATE SET
                descricao = EXCLUDED.descricao, natureza = EXCLUDED.natureza,
                ncm_code = EXCLUDED.ncm_code, nbs_code = EXCLUDED.nbs_code
            RETURNING id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at,
                      (xmax = 0) AS foi_criado
            """,
            (str(tenant_id), codigo_sku, descricao, natureza, ncm_code, nbs_code),
        )
        *campos, foi_criado = cur.fetchone()
    return SkuCatalogo(*campos), foi_criado


def buscar_skus_por_codigo(conexao, tenant_id: UUID, codigos_sku: list[str]) -> dict[str, SkuCatalogo]:
    """Lookup em LOTE, escopado por RLS — consumido por `api/empresa_skus.py`
    para o wiring de `/v1/tax/simulate`."""
    if not codigos_sku:
        return {}
    with sessao_do_tenant(conexao, tenant_id) as cur:
        cur.execute(
            """
            SELECT id, tenant_id, codigo_sku, descricao, natureza, ncm_code, nbs_code, created_at
            FROM empresa_skus WHERE codigo_sku = ANY(%s)
            """,
            (list(codigos_sku),),
        )
        linhas = cur.fetchall()
    return {linha[2]: SkuCatalogo(*linha) for linha in linhas}


def registrar_parecer(conexao, parecer: ParecerAuditado) -> UUID:
    """Grava na trilha de auditoria. É o que sustenta "simulação 100%
    auditável" — sem isto nenhuma resposta emitida pode ser reconstituída."""
    with sessao_do_tenant(conexao, parecer.tenant_id) as cur:
        cur.execute(
            """
            INSERT INTO pareceres_audit_log (
                tenant_id, user_id, prompt_consulta,
                contexto_recuperado_ids, payload_calculo_json, resposta_parecer_md
            ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)
            RETURNING id
            """,
            (
                str(parecer.tenant_id),
                str(parecer.user_id) if parecer.user_id else None,
                parecer.prompt_consulta,
                json.dumps(parecer.contexto_recuperado_ids),
                json.dumps(parecer.payload_calculo, default=str),
                parecer.resposta_parecer_md,
            ),
        )
        return cur.fetchone()[0]
