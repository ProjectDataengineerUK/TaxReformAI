"""Lógica pura dos 10 Anexos de redução por NCM — sem banco, sem HTTP.

O seed dos 321 itens é **lido das próprias migrações** (005 para o Anexo I, 008
para os XII/XIII/XV, 010 para os IV/V/VI/VII/VIII/IX e 009 para o catálogo de
percentuais), não redigitado aqui: são dados legais transcritos à mão de tabelas
do DOU, e uma segunda cópia em Python seria uma segunda fonte de verdade capaz
de divergir em silêncio da que o banco de produção carrega. Assim, estes testes
exercitam os 540 prefixos reais (508 inclusões + 32 exceções) sem precisar de
PostgreSQL — o SQL de verdade é `test_reducao_db.py`.

O catálogo (percentual e ordinal por Anexo) também sai da migração 009 pelo
mesmo motivo: um mapa `{"IV": 0.6}` aqui divergiria do banco no primeiro Anexo
novo, e o desempate de 6 componentes depende dos dois números.
"""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from api.ncm import digitos_ncm, prefixos_ncm
from api.reducao import (
    ConsultaReducao,
    SituacaoReducao,
    consultar_com_seguranca,
    formatar_item,
    resolver_item,
)
from db.repositorio import PrefixoReducao
from motor_calculo.engine import ResultadoCalculo
from motor_calculo.reducoes import aplicar_reducao_a_zero

MIGRACOES = Path(__file__).resolve().parents[1] / "db" / "migrations"
MIGRACAO_ANEXO_I = MIGRACOES / "005_cesta_basica_anexo_i.sql"
MIGRACAO_XII_XIII_XV = MIGRACOES / "008_anexos_reducao_zero_xii_xiii_xv.sql"
MIGRACAO_CATALOGO = MIGRACOES / "009_generalizar_anexos_reducao.sql"
MIGRACAO_PERCENTUAL = MIGRACOES / "010_anexos_reducao_percentual_ncm.sql"

# Migração 005 — schema antigo: (item, prefixo, excecao, alinea, texto).
_LINHA_NCM_005 = re.compile(
    r"\((\d+),\s*'(\d+)',\s*(TRUE|FALSE),\s*(NULL|'[a-d]'),\s*'([\d.]+)'\)"
)
_LINHA_ITEM_005 = re.compile(r"\((\d+),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)'\)")

# Migração 008 — schema generalizado: o Anexo e o sub-item entram na chave.
_LINHA_NCM_008 = re.compile(
    r"\('(XII|XIII|XV)',\s*(\d+),\s*(\d+),\s*'(\d+)',\s*(TRUE|FALSE),"
    r"\s*(NULL|'[a-d]'),\s*'([\d.]+)'\)"
)
_LINHA_ITEM_008 = re.compile(
    r"\('(XII|XIII|XV)',\s*(\d+),\s*(\d+),\s*(\d+),\s*'((?:[^']|'')*)',"
    r"\s*'(LCP 214/2025[^']*)'\)"
)

# Migração 010 — mesma forma da 008, sem a coluna `anexo_ordem` (que passou a
# viver no catálogo da 009) e com os 6 rótulos novos.
_ANEXOS_60 = "IV|VII|VIII|VI|V|IX"
_LINHA_NCM_010 = re.compile(
    rf"\('({_ANEXOS_60})',\s*(\d+),\s*(\d+),\s*'(\d+)',\s*(TRUE|FALSE),"
    r"\s*(NULL|'[a-d]'),\s*'([\d.]+)'\)"
)
_LINHA_ITEM_010 = re.compile(
    rf"\('({_ANEXOS_60})',\s*(\d+),\s*(\d+),\s*'((?:[^']|'')*)',"
    r"\s*'(LCP 214/2025[^']*)'\)"
)

# Migração 009 — as 10 linhas do catálogo: rótulo, ordinal, percentual e (só
# para IV/V/VI) o dispositivo que zera a alíquota conforme o comprador.
_LINHA_CATALOGO = re.compile(
    r"\('([IVX]+)',\s*(\d+),\s*([\d.]+),\s*'[^']*',\s*'(?:[^']|'')*',"
    r"\s*(NULL|'[^']*')\)"
)


def _carregar_catalogo() -> dict[str, tuple[int, Decimal, str | None]]:
    """Ordinal, percentual e condição de comprador por Anexo, lidos da 009."""
    sql = MIGRACAO_CATALOGO.read_text(encoding="utf-8")
    bloco = sql.split("INSERT INTO anexos_reducao_catalogo")[1].split("ON CONFLICT")[0]
    return {
        anexo: (
            int(ordem),
            Decimal(percentual).quantize(Decimal("0.0001")),
            None if comprador == "NULL" else comprador.strip("'"),
        )
        for anexo, ordem, percentual, comprador in _LINHA_CATALOGO.findall(bloco)
    }


CATALOGO = _carregar_catalogo()


def _linha(anexo: str, item: int, sub_item: int, prefixo: str, excecao: str,
           alinea: str, texto: str, itens: dict) -> PrefixoReducao:
    """Monta a linha exatamente como o SELECT do repositório a devolveria —
    inclusive o LEFT JOIN do item-pai e o JOIN do catálogo."""
    descricao, dispositivo = itens[(anexo, item, sub_item)]
    pai = itens.get((anexo, item, 0)) if sub_item > 0 else None
    anexo_ordem, percentual, comprador_ref = CATALOGO[anexo]
    return PrefixoReducao(
        anexo=anexo,
        anexo_ordem=anexo_ordem,
        percentual_reducao=percentual,
        zero_por_comprador_ref=comprador_ref,
        item=item,
        sub_item=sub_item,
        prefixo=prefixo,
        excecao=excecao == "TRUE",
        texto_ncm=texto,
        alinea=None if alinea == "NULL" else alinea.strip("'"),
        descricao=descricao,
        descricao_contexto=pai[0] if pai else None,
        dispositivo_legal_ref=dispositivo,
    )


def _carregar_anexo_i() -> tuple[dict, list[PrefixoReducao]]:
    sql = MIGRACAO_ANEXO_I.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO cesta_basica_anexo_i ")[1].split("ON CONFLICT")[0]
    itens = {
        ("I", int(m[1]), 0): (m[2].replace("''", "'"), m[3])
        for m in _LINHA_ITEM_005.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO cesta_basica_anexo_i_ncm")[1].split("ON CONFLICT")[0]
    linhas = [
        # O Anexo I não tem sub-item, então nunca tem pai.
        _linha("I", int(item), 0, prefixo, excecao, alinea, texto, itens)
        for item, prefixo, excecao, alinea, texto in _LINHA_NCM_005.findall(bloco_ncm)
    ]
    return itens, linhas


def _carregar_xii_xiii_xv() -> tuple[dict, list[PrefixoReducao]]:
    sql = MIGRACAO_XII_XIII_XV.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO anexos_reducao_zero (")[1].split("ON CONFLICT")[0]
    itens = {
        (m[1], int(m[3]), int(m[4])): (m[5].replace("''", "'"), m[6])
        for m in _LINHA_ITEM_008.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO anexos_reducao_zero_ncm")[1].split("ON CONFLICT")[0]
    linhas = [
        _linha(anexo, int(item), int(sub), prefixo, excecao, alinea, texto, itens)
        for anexo, item, sub, prefixo, excecao, alinea, texto in _LINHA_NCM_008.findall(
            bloco_ncm
        )
    ]
    return itens, linhas


def _carregar_percentuais() -> tuple[dict, list[PrefixoReducao]]:
    """Os 6 Anexos de 60% da migração 010 — 261 itens, 389 linhas de prefixo."""
    sql = MIGRACAO_PERCENTUAL.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO anexos_reducao (")[1].split("ON CONFLICT")[0]
    itens = {
        (m[1], int(m[2]), int(m[3])): (m[4].replace("''", "'"), m[5])
        for m in _LINHA_ITEM_010.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO anexos_reducao_ncm")[1].split("ON CONFLICT")[0]
    linhas = [
        _linha(anexo, int(item), int(sub), prefixo, excecao, alinea, texto, itens)
        for anexo, item, sub, prefixo, excecao, alinea, texto in _LINHA_NCM_010.findall(
            bloco_ncm
        )
    ]
    return itens, linhas


ITENS_I, LINHAS_I = _carregar_anexo_i()
ITENS_ZERO_NOVOS, LINHAS_ZERO_NOVAS = _carregar_xii_xiii_xv()
ITENS_60, LINHAS_60 = _carregar_percentuais()

ITENS = {**ITENS_I, **ITENS_ZERO_NOVOS, **ITENS_60}
SEED = LINHAS_I + LINHAS_ZERO_NOVAS + LINHAS_60
INCLUSOES = [linha for linha in SEED if not linha.excecao]
EXCECOES = [linha for linha in SEED if linha.excecao]

ZERO = Decimal("1.0000")  # fração da alíquota removida: 100%
SESSENTA = Decimal("0.6000")

ANEXOS_ZERO = ("I", "XII", "XIII", "XV")
ANEXOS_60 = ("IV", "V", "VI", "VII", "VIII", "IX")


def _consulta(codigo: str) -> ConsultaReducao:
    """Só as linhas que o `= ANY(%s)` devolveria para este código — é assim que
    o lote chega do banco, e não a tabela inteira."""
    candidatos = set(prefixos_ncm(codigo))
    return ConsultaReducao(
        disponivel=True, linhas=[linha for linha in SEED if linha.prefixo in candidatos]
    )


def _resolver(codigo: str, natureza: str = "MERCADORIA", comprador: str | None = None):
    return resolver_item(natureza, codigo, _consulta(codigo), comprador)


def _fake(
    anexo: str,
    item: int,
    prefixo: str,
    *,
    sub_item: int = 0,
    percentual: Decimal = SESSENTA,
    comprador_ref: str | None = None,
    excecao: bool = False,
    texto: str = "",
    descricao: str = "inventado",
) -> PrefixoReducao:
    """Uma linha INVENTADA, para exercitar combinações que a lei não produz.

    Só onde o seed real não serve — o desempate precisa ser testado com pares
    que ainda não existem, senão ele só é provado nos casos que já se conhece.
    O `anexo_ordem` sai do catálogo de verdade, para não inventar ordinal.
    """
    return PrefixoReducao(
        anexo=anexo,
        anexo_ordem=CATALOGO[anexo][0],
        percentual_reducao=percentual,
        zero_por_comprador_ref=comprador_ref,
        item=item,
        sub_item=sub_item,
        prefixo=prefixo,
        excecao=excecao,
        texto_ncm=texto or prefixo,
        alinea=None,
        descricao=descricao,
        descricao_contexto=None,
        dispositivo_legal_ref=(
            f"LCP 214/2025, Anexo {anexo}, item {formatar_item(item, sub_item)}"
        ),
    )


# Integridade do seed — as contagens de fechamento do DESIGN ------------------


def test_seed_tem_321_itens_508_inclusoes_e_32_excecoes():
    """Contagem é teste de truncamento: uma migração cortada pela metade passa
    em toda constraint e falha aqui. São as contagens de fechamento do DESIGN —
    60 itens/151 prefixos já shipados mais 261/389 desta feature."""
    assert len(ITENS) == 321
    assert len(SEED) == 540
    assert len(INCLUSOES) == 508
    assert len(EXCECOES) == 32


@pytest.mark.parametrize(
    ("anexo", "itens", "prefixos"),
    [
        ("I", 26, 95),
        ("IV", 105, 112),
        ("V", 29, 30),
        ("VI", 81, 86),
        ("VII", 17, 53),
        ("VIII", 7, 7),
        ("IX", 22, 101),
        ("XII", 20, 24),
        ("XIII", 8, 7),
        ("XV", 6, 25),
    ],
)
def test_contagem_por_anexo_bate_com_a_transcricao(anexo, itens, prefixos):
    """Por Anexo, e não global, para que a falha diga ONDE.

    O Anexo V tem 29 itens (3 cabeçalhos + 26 sub-itens) e o item 7 do Anexo IX
    cita 29 códigos — as duas contagens que o `/design` corrigiu no `/define`
    depois de extrair a estrutura `<tr>` da tabela do DOU em vez de ler o texto
    renderizado.
    """
    assert len([chave for chave in ITENS if chave[0] == anexo]) == itens
    assert len([linha for linha in SEED if linha.anexo == anexo]) == prefixos


def test_o_anexo_ix_carrega_22_itens_e_nenhum_dos_13_sem_chave_ncm():
    """AT-008 e AT-009: os itens 22 a 33 do Anexo IX têm chave NBS e o 34 não
    tem chave nenhuma. Nenhum dos 13 entra na tabela — o que os torna
    "documentados como não resolvidos" em vez de "não encontrados em silêncio".

    Um NBS transcrito por engano seria recusado pelo próprio schema: sem
    pontuação ele tem NOVE dígitos (`1.1410.90.00` → `114109000`) e a CHECK
    `prefixo_comprimento_valido` só admite {2,4,5,6,7,8}.
    """
    itens_ix = sorted(chave[1] for chave in ITENS if chave[0] == "IX")

    assert itens_ix == [*range(1, 22), 35]
    assert not [n for n in itens_ix if 22 <= n <= 34]
    assert not [linha for linha in SEED if linha.anexo == "IX" and 22 <= linha.item <= 34]


def test_comprimentos_de_prefixo_ficam_na_lista_que_prefixos_ncm_enxerga():
    """Acoplamento explícito com `_COMPRIMENTOS_PREFIXO` e com a CHECK
    `prefixo_comprimento_valido`: um prefixo fora da lista nunca casaria com
    nada — falso negativo permanente e mudo. Nenhum comprimento NOVO entrou com
    os 6 Anexos de 60%: a feature anterior alargou a lista na medida exata."""
    comprimentos = {len(linha.prefixo) for linha in SEED}

    assert comprimentos == {2, 4, 5, 6, 7, 8}


def test_os_nove_capitulos_da_ncm_que_recebem_reducao_inteiros():
    """A limitação mais perigosa da feature, fixada por teste: 9 capítulos
    distintos (14 linhas, porque `10` e `12` aparecem em dois itens do Anexo IX
    cada) concedem a redução ao capítulo INTEIRO da NCM enquanto o texto do item
    restringe. Um décimo capítulo entrando sem ninguém notar é exatamente o que
    este teste existe para impedir.

    O pior é o `25` (Anexo IX, item 3, "corretivos de solo"): na NCM o Capítulo
    25 inclui cimento, mármore e gesso.
    """
    capitulos = sorted(
        (linha.prefixo, linha.anexo, formatar_item(linha.item, linha.sub_item))
        for linha in SEED
        if len(linha.prefixo) == 2
    )

    assert capitulos == [
        ("06", "XV", "4"),  # já shipado — o único até esta feature
        ("07", "IX", "10"),
        ("07", "VII", "14"),
        ("08", "VII", "14"),
        ("10", "IX", "10"),
        ("10", "IX", "19"),
        ("10", "VII", "15"),
        ("11", "IX", "19"),
        ("12", "IX", "10"),
        ("12", "IX", "19"),
        ("12", "VII", "15"),
        ("15", "IX", "21"),
        ("25", "IX", "3"),
        ("31", "IX", "2"),
    ]
    assert len({prefixo for prefixo, _, _ in capitulos}) == 9


def test_nenhuma_duplicata_de_anexo_item_subitem_prefixo_excecao():
    contagem = Counter(
        (linha.anexo, linha.item, linha.sub_item, linha.prefixo, linha.excecao)
        for linha in SEED
    )

    assert [chave for chave, n in contagem.items() if n > 1] == []


def test_os_prefixos_compartilhados_por_mais_de_um_item_do_mesmo_anexo():
    """Sobreposição DENTRO de um Anexo só muda a citação, nunca o número — mas
    o desempate precisa ser total, senão a citação vira loteria da ordem em que
    o Postgres devolveu as linhas.

    Os dois pares já shipados do Anexo I continuam aqui; os campeões novos são o
    `9018.90.99` (9 itens do Anexo IV) e o `2922.49.90` (10 itens do Anexo VI).
    """
    por_prefixo: dict[str, set[tuple[str, str]]] = {}
    for linha in SEED:
        por_prefixo.setdefault(linha.prefixo, set()).add(
            (linha.anexo, formatar_item(linha.item, linha.sub_item))
        )
    compartilhados = {p: itens for p, itens in por_prefixo.items() if len(itens) > 1}

    # Não-regressão: os dois itens do Anexo I e o trio do XII continuam citando
    # `2106.90.90` e `9018.19.80` — o que MUDOU é que outros Anexos entraram na
    # lista, não que algum dos já shipados tenha saído.
    assert {("I", "4"), ("I", "26")} <= compartilhados["21069090"]
    assert sorted(compartilhados["90181980"]) == [
        ("XII", "1.2"),
        ("XII", "1.3"),
        ("XII", "14"),
    ]

    # Os campeões novos, e a razão de `itens_correspondentes` não ter limite.
    assert {anexo for anexo, _ in compartilhados["90189099"]} == {"IV", "XII"}
    assert len([i for i in compartilhados["90189099"] if i[0] == "IV"]) == 9
    assert len([i for i in compartilhados["29224990"] if i[0] == "VI"]) == 10
    assert len([i for i in compartilhados["21069090"] if i[0] == "VI"]) == 8


def test_toda_excecao_desce_de_uma_inclusao_do_mesmo_item():
    """Invariante dos Anexos, e a asserção que a migração 008 também faz: uma
    exceção órfã é ou erro de transcrição, ou um "exceto" DESCRITIVO virado
    linha (Decisão 6). Nos dois casos a linha seria inerte."""
    orfas = [
        excecao
        for excecao in EXCECOES
        if not any(
            (inclusao.anexo, inclusao.item, inclusao.sub_item)
            == (excecao.anexo, excecao.item, excecao.sub_item)
            and excecao.prefixo.startswith(inclusao.prefixo)
            for inclusao in INCLUSOES
        )
    ]

    assert orfas == []


def test_os_excetos_descritivos_nao_viraram_linha_de_exclusao():
    """Os 9 códigos do XII/1.3 e os 2 do XII/11 são citados na descrição e NÃO
    geram exclusão: nenhum desce de uma inclusão do próprio item. Transcrevê-los
    como exceção é o erro natural de quem lê a tabela depressa."""
    excecoes_xii = {
        (linha.item, linha.sub_item, linha.prefixo)
        for linha in EXCECOES
        if linha.anexo == "XII"
    }

    assert excecoes_xii == {
        (5, 0, "90213991"),
        (5, 0, "90213999"),
        (7, 0, "90221991"),
    }
    assert "9018.11.00" in ITENS[("XII", 1, 3)][0], "o texto do item cita os códigos"


def test_apenas_os_cinco_cabecalhos_conhecidos_nao_tem_linha_de_prefixo():
    """XII/1, XIII/2 e os três itens-cabeçalho do Anexo V são células sem NCM no
    DOU (Decisão 7 da feature anterior). Um sexto item sem prefixo seria INSERT
    truncado."""
    com_prefixo = {(linha.anexo, linha.item, linha.sub_item) for linha in SEED}

    assert sorted(set(ITENS) - com_prefixo) == [
        ("V", 1, 0),
        ("V", 2, 0),
        ("V", 3, 0),
        ("XII", 1, 0),
        ("XIII", 2, 0),
    ]


def test_todo_sub_item_tem_o_cabecalho_que_lhe_da_sentido():
    sub_itens = [chave for chave in ITENS if chave[2] > 0]

    # 5 já shipados (XII/1.1-1.3 e XIII/2.1-2.2) + 26 do Anexo V (1.1-1.13,
    # 2.1-2.10, 3.1-3.3) — a contagem que o `/design` corrigiu de 23 para 26.
    assert len(sub_itens) == 31
    assert len([c for c in sub_itens if c[0] == "V"]) == 26
    for anexo, item, _ in sub_itens:
        assert (anexo, item, 0) in ITENS


def _pares_zero_x_sessenta() -> list[tuple]:
    """Todo par (inclusão de Anexo zero, inclusão de Anexo 60%) que compartilha
    ao menos um código concreto.

    A equivalência "dois prefixos compartilham um código de 8 dígitos se, e
    somente se, um é prefixo do outro" é EXATA, então nada aqui precisa da
    tabela da NCM nem inventa código nenhum.
    """
    return [
        (zero, sessenta)
        for zero in INCLUSOES
        if zero.anexo in ANEXOS_ZERO
        for sessenta in INCLUSOES
        if sessenta.anexo in ANEXOS_60
        and (
            sessenta.prefixo.startswith(zero.prefixo)
            or zero.prefixo.startswith(sessenta.prefixo)
        )
    ]


def test_a_premissa_a003_do_define_e_falsa_e_a_sobreposicao_e_estrutural():
    """A `A-003` do DEFINE dizia "não há overlap além da remissão textual do
    Anexo VII". São **117 pares**, e é o achado que reorganizou o design
    inteiro: se os dois grupos fossem resolvidos em separado, uma consulta que
    devolvesse o Anexo IV sem saber que o XII cobre o mesmo código responderia
    60% onde a lei dá zero.

    Sobreposição NÃO é ilegal — a lei criou 117 delas. Por isso este teste
    descreve o que existe em vez de proibir, que é o que impediria de ser
    desligado no primeiro Anexo novo (Decisão 12).
    """
    pares = _pares_zero_x_sessenta()
    mais_curto = [p for p in pares if len(p[0].prefixo) < len(p[1].prefixo)]
    igual = [p for p in pares if len(p[0].prefixo) == len(p[1].prefixo)]
    mais_longo = [p for p in pares if len(p[0].prefixo) > len(p[1].prefixo)]

    assert len(pares) == 117
    assert (len(mais_longo), len(igual), len(mais_curto)) == (78, 35, 4)


def test_decisao_12a_os_quatro_casos_em_que_o_60_por_cento_vence_o_zero():
    """A lista FECHADA da Decisão 4, executada. O perigo real não é o caso
    conhecido: é o QUINTO, que entraria numa revisão de 120 dias (art. 131, §2º)
    sem ninguém notar. Este teste é o alarme.

    Nos quatro, o legislador escreveu um código MAIS PRECISO no Anexo de 60% e
    um mais amplo no de zero — e o erro é na direção SEGURA (cobra mais tributo).
    """
    invertidos = sorted(
        {
            (
                zero.anexo,
                formatar_item(zero.item, zero.sub_item),
                zero.prefixo,
                sessenta.anexo,
                formatar_item(sessenta.item, sessenta.sub_item),
                sessenta.prefixo,
            )
            for zero, sessenta in _pares_zero_x_sessenta()
            if len(zero.prefixo) < len(sessenta.prefixo)
        }
    )

    assert invertidos == [
        ("XII", "12", "9025", "V", "2.3", "90251990"),
        ("XII", "2", "901820", "IV", "70", "90182010"),
        ("XV", "4", "06", "IX", "11", "0601"),
        ("XV", "4", "06", "IX", "11", "0602"),
    ]


def test_decisao_12b_os_35_empates_de_comprimento_sao_todos_resolvidos_a_favor_do_zero():
    """Onde os dois grupos citam prefixos do MESMO comprimento não há
    especificidade que os separe, e aí a escolha entre 0% e 40% da alíquota não
    pode cair num ordinal de Anexo (`-anexo_ordem` faria IV vencer XII, porque
    4 < 12). Quem decide é o componente 2 — a MAIOR redução.

    São 7 códigos de 8 dígitos idênticos nos dois grupos, e este teste resolve
    cada um pelo caminho real de produção.
    """
    empates = {
        zero.prefixo
        for zero, sessenta in _pares_zero_x_sessenta()
        if len(zero.prefixo) == len(sessenta.prefixo)
    }
    oito_digitos = sorted(p for p in empates if len(p) == 8)

    assert oito_digitos == [
        "21069090",  # I/4 e I/26 x 8 itens do Anexo VI
        "25010090",  # I/22 (sal) x VI/30
        "90189010",  # XII/15 (bomba de infusão) x IV/10
        "90189099",  # XII/9 x 9 itens do Anexo IV
        "90211010",  # XII/3 x IV/42
        "90211020",  # XII/4 x IV/42
        "90219019",  # XIII/6 (implantes cocleares) x 6 itens do Anexo IV
    ]
    for codigo in oito_digitos:
        resolucao = _resolver(codigo)

        assert resolucao.percentual_reducao == ZERO, (
            f"{codigo} empatou em comprimento entre um Anexo de zero e um de "
            f"60% e resolveu {resolucao.percentual_reducao} — sem o componente "
            "2 do desempate, este caso devolve 60% onde a lei dá zero"
        )
        assert resolucao.anexo in ANEXOS_ZERO


def test_decisao_12c_sobreposicao_entre_dois_anexos_de_60_muda_a_citacao_nao_o_numero():
    """Dentro do grupo de 60% o percentual é o mesmo dos dois lados, então o
    desempate escolhe qual dispositivo CITAR — nunca quanto cobrar. O teste
    barato que pega a classe mais chata de erro de transcrição: um prefixo
    digitado no Anexo errado apareceria aqui como sobreposição nova."""
    divergentes = [
        (a.anexo, a.prefixo, b.anexo, b.prefixo)
        for a in INCLUSOES
        if a.anexo in ANEXOS_60
        for b in INCLUSOES
        if b.anexo in ANEXOS_60
        and a.anexo < b.anexo
        and (b.prefixo.startswith(a.prefixo) or a.prefixo.startswith(b.prefixo))
        and a.percentual_reducao != b.percentual_reducao
    ]

    assert divergentes == []


def test_decisao_12d_o_anexo_com_condicao_de_comprador_vence_os_demais_de_60():
    """Se um item de IV/V/VI (que a lei zera conforme o comprador) perdesse o
    desempate para um de VII/VIII/IX, o zero do comprador qualificado sumiria
    SEM SINTOMA — a resposta continuaria dizendo 60%, com a citação do Anexo
    errado, e ninguém saberia que uma redução maior estava disponível.

    Até esta feature isso valia por sorte (o prefixo de IV/V/VI é mais longo em
    20 dos 27 pares, e nos 7 empates 4 < 5 < 6 < 7 < 8 < 9). Com o componente 3
    passa a valer por construção, e este teste fixa a propriedade.
    """
    perdas = []
    for com_condicao in INCLUSOES:
        if com_condicao.zero_por_comprador_ref is None:
            continue
        for sem_condicao in INCLUSOES:
            sem_overlap = not sem_condicao.prefixo.startswith(
                com_condicao.prefixo
            ) and not com_condicao.prefixo.startswith(sem_condicao.prefixo)
            if sem_condicao.anexo not in ("VII", "VIII", "IX") or sem_overlap:
                continue
            codigo = max(
                com_condicao.prefixo, sem_condicao.prefixo, key=len
            ).ljust(8, "0")
            vencedor = _resolver(codigo, comprador="ORGAO_PUBLICO")
            if vencedor.percentual_reducao != ZERO:
                perdas.append((codigo, vencedor.anexo, vencedor.item))

    assert perdas == []


def test_todo_item_cita_o_proprio_anexo_e_numero_no_dispositivo_legal():
    """Mesma garantia da CHECK `dispositivo_cita_o_proprio_item` (migração 007),
    aqui como segunda rede: transcrever "item 13" numa linha cujo item é 14 é
    invisível — o número certo continua na chave e o cliente recebe a citação
    errada."""
    divergentes = [
        chave
        for chave, (_, dispositivo) in ITENS.items()
        if not dispositivo.endswith(
            f"Anexo {chave[0]}, item {formatar_item(chave[1], chave[2])}"
        )
    ]

    assert divergentes == []


# api/ncm.py -----------------------------------------------------------------


@pytest.mark.parametrize(
    "bruto", ["04051000", "0405.10.00", "0405 10 00", "0405-10-00", " 0405.10.00 "]
)
def test_digitos_ncm_canoniza_todas_as_grafias(bruto):
    assert digitos_ncm(bruto) == "04051000"


@pytest.mark.parametrize("bruto", ["", "0405", "0405.10.00.1", "abc", "040510001"])
def test_digitos_ncm_recusa_o_que_nao_tem_8_digitos(bruto):
    assert digitos_ncm(bruto) is None


def test_digitos_ncm_aceita_none_sem_estourar():
    assert digitos_ncm(None) is None


def test_prefixos_ncm_gera_exatamente_os_seis_niveis_da_hierarquia():
    """O capítulo (2 dígitos) entrou por causa do Anexo XV, item 4. NÃO existe
    nível de 3 dígitos na NCM/SH — por isso é lista, não intervalo."""
    assert prefixos_ncm("02074300") == [
        "02",
        "0207",
        "02074",
        "020743",
        "0207430",
        "02074300",
    ]


def test_normalizar_ncm_do_ipi_continua_delegando_sem_mudar_comportamento():
    """A Decisão 10 do Anexo I refatora `api/ipi.py::normalizar_ncm` para cima
    de `digitos_ncm` — `tests/test_ipi_resolucao.py` prova o comportamento; aqui
    fica registrado que as duas features enxergam o MESMO conjunto de códigos
    válidos, que é o ponto da decisão."""
    from api.ipi import normalizar_ncm

    for bruto in ("22030000", "2203.00.00", "2203", "", "lixo"):
        assert (normalizar_ncm(bruto) is None) == (digitos_ncm(bruto) is None)


# formatar_item — a grafia canônica é DERIVADA da chave ----------------------


@pytest.mark.parametrize(
    ("item", "sub_item", "esperado"),
    [(5, 0, "5"), (1, 2, "1.2"), (14, 0, "14"), (2, 1, "2.1"), (26, 0, "26")],
)
def test_formatar_item_devolve_a_grafia_do_dou(item, sub_item, esperado):
    assert formatar_item(item, sub_item) == esperado


# AT-001 — correspondência exata em Anexo novo, com sub-item ------------------


def test_at001_cadeira_de_rodas_casa_o_item_2_1_do_anexo_xiii():
    resolucao = _resolver("87131000")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert resolucao.anexo == "XIII"
    assert resolucao.item == "2.1"
    assert (
        resolucao.dispositivo_legal_ref == "LCP 214/2025, art. 145, Anexo XIII, item 2.1"
    )
    assert resolucao.texto_ncm == "8713.10.00"
    assert resolucao.tipo_correspondencia == "EXATO"
    assert resolucao.itens_correspondentes == (("XIII", "2.1"),)


def test_at001_o_sub_item_traz_o_cabecalho_que_lhe_da_sentido():
    """Sem `descricao_contexto`, a fundamentação de uma cadeira de rodas seria a
    frase "Sem mecanismo de propulsão" — passa em qualquer teste automatizado e
    é inútil para o humano que precisa dela (Decisão 7)."""
    resolucao = _resolver("87131000")

    assert resolucao.descricao == "Sem mecanismo de propulsão"
    assert resolucao.descricao_contexto is not None
    assert resolucao.descricao_contexto.startswith("CADEIRA DE RODAS")


def test_item_sem_pai_nao_inventa_contexto():
    assert _resolver("04051000").descricao_contexto is None
    assert _resolver("90221200").descricao_contexto is None


def test_todas_as_508_inclusoes_dos_dez_anexos_resolvem_aplicada():
    """Cobre os 321 itens de uma vez: cada prefixo, completado com zeros até 8
    dígitos, precisa cair no próprio item. `in itens_correspondentes` em vez de
    `== item` por causa das 117 sobreposições, onde o desempate escolhe um."""
    for inclusao in INCLUSOES:
        codigo = inclusao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducao.APLICADA, (
            f"{inclusao.texto_ncm} (Anexo {inclusao.anexo}, item "
            f"{formatar_item(inclusao.item, inclusao.sub_item)}) não resolveu: "
            f"{resolucao.situacao}"
        )
        assert (
            inclusao.anexo,
            formatar_item(inclusao.item, inclusao.sub_item),
        ) in resolucao.itens_correspondentes


# AT-004 e AT-005 — prefixo puro, incluindo o capítulo de 2 dígitos -----------


@pytest.mark.parametrize(
    ("codigo", "anexo", "item", "texto"),
    [
        ("07141000", "XV", "5", "07.14"),  # raízes e tubérculos — posição de 4
        ("04072100", "XV", "1", "0407.2"),  # ovos — subposição de 5
        ("08011200", "XV", "6", "0801.1"),  # cocos — subposição de 5
        ("90182000", "XII", "2", "9018.20"),  # raios UV — subposição de 6
        ("90250000", "XII", "12", "90.25"),  # termômetros — posição de 4
        ("90181200", "XII", "17", "9018.12"),  # ultrassom — subposição de 6
    ],
)
def test_at004_prefixo_puro_resolve_com_a_grafia_literal_da_lei(
    codigo, anexo, item, texto
):
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.tipo_correspondencia == "PREFIXO"
    # "casou com a posição 07.14" é auditável; "casou com 0714" não é a grafia
    # que o DOU publicou.
    assert resolucao.texto_ncm == texto


@pytest.mark.parametrize("codigo", ["06031100", "06049000"])
def test_at005_capitulo_6_continua_resolvendo_pelo_prefixo_de_dois_digitos(codigo):
    """Não-regressão do caso que prova a Decisão 4 da feature anterior ponta a
    ponta: `_COMPRIMENTOS_PREFIXO` e a CHECK da migração 007 mudaram juntos. Se
    só um tivesse mudado, tudo o mais continuaria verde.

    MUDANÇA DE VALOR AUTORIZADA (Decisão 7): `tipo_correspondencia` passa de
    `PREFIXO` para `CAPITULO`. É a única mudança neste teste, e ela torna a
    resposta MAIS verdadeira sobre o que aconteceu — não menos. Anexo, item e
    grafia do código seguem idênticos.

    `06011000` e `06029090` saíram desta lista porque a lei os coloca noutro
    lugar a partir desta feature — ver o teste dos 4 casos invertidos.
    """
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("XV", "4")
    assert resolucao.texto_ncm == "06"
    assert resolucao.tipo_correspondencia == "CAPITULO"


@pytest.mark.parametrize(
    ("codigo", "anexo", "item", "texto"),
    [
        ("06011000", "IX", "11", "06.01"),  # bulbos/tubérculos — mudas
        ("06029090", "IX", "11", "06.02"),  # outras plantas vivas
        ("90251990", "V", "2.3", "9025.19.90"),  # termômetro digital com voz
        ("90182010", "IV", "70", "9018.20.10"),  # fotocoagulador a laser
    ],
)
def test_decisao_4_os_quatro_casos_em_que_o_60_por_cento_vence_o_zero(
    codigo, anexo, item, texto
):
    """MUDANÇA DE COMPORTAMENTO ESPERADA, e a mais contraintuitiva da feature.

    Em 4 pares (e só 4, de 117) o prefixo do Anexo de ZERO é mais CURTO que o do
    Anexo de 60%, então o componente 1 do desempate — especificidade — dá a
    vitória ao de 60%. Uma leitura ingênua esperaria zero.

    É defensável porque em todos os quatro o legislador escreveu um código mais
    preciso no Anexo de 60% e um mais amplo no de zero: um fotocoagulador a
    laser É um aparelho de raios infravermelhos (XII/2, `9018.20`), e o Anexo IV
    o NOMEIA em 8 dígitos. E o erro é na direção SEGURA — cobra mais tributo, não
    menos.

    `itens_correspondentes` mostra os dois lados, então quem estranhar
    "Fotocoagulador a laser 60%" vê o XII/2 na lista e decide sozinho.
    """
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.percentual_reducao == SESSENTA
    assert resolucao.texto_ncm == texto
    # O Anexo de zero que perdeu continua visível na resposta.
    assert [a for a, _ in resolucao.itens_correspondentes if a in ANEXOS_ZERO]


def test_o_capitulo_6_devolve_a_descricao_literal_que_qualifica_o_item():
    """A limitação mais perigosa do projeto — e a única que erra na direção do
    tributo A MENOS: `06` concede zero a todo o capítulo, enquanto o item
    qualifica. Não sendo verificável a partir do payload, a mitigação é
    devolver o texto do item para o cliente conferir."""
    resolucao = _resolver("06031100")

    assert "cultivados para fins alimentares" in resolucao.descricao
    assert "Capítulo 6" in resolucao.descricao


def test_at007_um_item_com_tres_capitulos_resolve_por_qualquer_um_deles():
    """AT-007. Os itens 10 e 19 do Anexo IX citam TRÊS capítulos cada
    ("Capítulos 7, 10 e 12"; "Capítulos 10, 11 e 12") — um padrão que nenhum
    Anexo já shipado tinha (lá, um item tinha no máximo 1 prefixo curto). O
    mecanismo 1:N já suportava, mas nunca havia sido exercitado.

    `1109.00.00` (glúten de trigo) é o caso do DESIGN: capítulo 11, citado só
    pelo item 19.
    """
    gluten = _resolver("11090000")

    assert gluten.situacao is SituacaoReducao.APLICADA
    assert (gluten.anexo, gluten.item) == ("IX", "19")
    assert gluten.percentual_reducao == SESSENTA
    assert gluten.tipo_correspondencia == "CAPITULO"
    assert gluten.texto_ncm == "11"

    # Os três capítulos do item 19 e os três do item 10, como linhas distintas.
    assert {linha.prefixo for linha in SEED if linha.anexo == "IX" and linha.item == 19} == {
        "10",
        "11",
        "12",
    }
    assert {linha.prefixo for linha in SEED if linha.anexo == "IX" and linha.item == 10} == {
        "07",
        "10",
        "12",
    }


def test_o_capitulo_25_concede_60_por_cento_a_cimento_marmore_e_gesso():
    """O pior caso da limitação declarada nº 1, fixado por teste em vez de
    prosa: o item 3 do Anexo IX fala de "corretivos de solo (inclusive
    condicionadores), remineralizadores e substratos para plantas", e cita o
    Capítulo 25 inteiro — que na NCM inclui cimento (25.23), mármore (25.15) e
    gesso (25.20).

    A simulação aplica 60% aos três, porque foi isso que a lei escreveu. A
    mitigação é `CAPITULO` + a descrição literal, não deixar de aplicar: não
    carregar os capítulos foi considerado e recusado, porque negaria uma redução
    que a lei concede em cima de código que a lei escreveu.
    """
    for codigo in ("25232910", "25151100", "25202010"):
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducao.APLICADA
        assert (resolucao.anexo, resolucao.item) == ("IX", "3")
        assert resolucao.tipo_correspondencia == "CAPITULO"
        assert "Corretivos de solo" in resolucao.descricao
        assert "legislação específica" in resolucao.descricao


def test_prefixo_de_7_digitos_continua_resolvendo():
    """`0210.99.1` era o único prefixo de 7 dígitos do projeto; os 6 Anexos
    novos trouxeram mais seis. Comprimento que a lista precisa continuar
    enxergando."""
    resolucao = _resolver("02109911")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("I", "19")
    assert resolucao.texto_ncm == "0210.99.1"

    brocas = _resolver("90184911")  # `9018.49.1`, Anexo IV, item 65

    assert (brocas.anexo, brocas.item) == ("IV", "65")
    assert brocas.tipo_correspondencia == "PREFIXO"


# AT-006 e AT-007 — exceções operantes nos Anexos novos -----------------------


@pytest.mark.parametrize(
    ("codigo", "anexo", "item", "texto"),
    [
        ("90213991", "XII", "5", "9021.39.91"),  # prótese excluída pelo próprio item
        ("90213999", "XII", "5", "9021.39.99"),
        ("90221991", "XII", "7", "9022.19.91"),  # raio X excluído do item 7
        ("03061100", "VII", "1", "0306.11"),  # AT-004 — dentro de `0306.1`
        ("03063100", "VII", "1", "0306.31.00"),
        ("03061500", "VII", "1", "0306.15.00"),
    ],
)
def test_at004_codigo_excluido_pelo_proprio_item_nunca_recebe_reducao(
    codigo, anexo, item, texto
):
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.EXCLUIDA_EXPRESSAMENTE
    assert resolucao.aplicada is False, "exceção do item jamais vira redução"
    assert resolucao.percentual_reducao is None, (
        "item excluído não pode carregar percentual: citar '60%' num item que a "
        "lei retirou afirmaria um benefício inexistente"
    )
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.texto_ncm == texto
    assert resolucao.tipo_correspondencia == "EXCECAO"


def test_as_32_excecoes_bloqueiam_o_proprio_item_e_so_tres_perdem_para_outro_anexo():
    """A exceção continua ESCOPADA AO ITEM (Decisão 3 do Anexo I, mantida pela
    Decisão 8): ela exclui daquele item, nunca dos demais. Com os 10 Anexos na
    mesma resolução isso produz um efeito novo — uma inclusão de OUTRO Anexo
    pode cobrir um código que este item retirou.

    São exatamente TRÊS casos, todos previstos e nominalmente autorizados pelo
    DESIGN. Um quarto significaria que a transcrição mudou sem ninguém notar.
    """
    nao_bloqueadas = []
    for excecao in EXCECOES:
        codigo = excecao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)
        # O item que excluiu tem de aparecer SEMPRE em `itens_excluidos`, mesmo
        # quando outro item venceu com uma inclusão — é o que torna o caso
        # inspecionável em vez de confuso.
        assert (
            excecao.anexo,
            formatar_item(excecao.item, excecao.sub_item),
        ) in resolucao.itens_excluidos, (
            f"{excecao.texto_ncm} (Anexo {excecao.anexo}) excluiu o código mas "
            "não aparece em itens_excluidos — a exclusão sumiu da resposta"
        )
        if resolucao.situacao is not SituacaoReducao.EXCLUIDA_EXPRESSAMENTE:
            nao_bloqueadas.append(
                (
                    excecao.anexo,
                    formatar_item(excecao.item, excecao.sub_item),
                    excecao.prefixo,
                    resolucao.anexo,
                    resolucao.item,
                )
            )

    assert sorted(nao_bloqueadas) == [
        # Decisão 8: o cogumelo é RETIRADO do Anexo XV, e o Anexo VII/14
        # ressalva "os produtos RELACIONADOS nos Anexos I e XV" — um cogumelo
        # não é relacionado lá, então o capítulo 07 do VII/14 o alcança.
        ("VII", "14", "0711", "IX", "10"),
        ("XV", "2", "07095", "VII", "14"),
        ("XV", "2", "07108000", "VII", "14"),
    ]


def test_decisao_8_o_cogumelo_passa_de_excluido_para_60_por_cento_e_declara_os_dois_lados():
    """MUDANÇA DE COMPORTAMENTO AUTORIZADA, e a mais fácil de confundir com
    regressão: `0709.51.00` respondia `EXCLUIDA_EXPRESSAMENTE` (alíquota cheia)
    e passa a responder `APLICADA` a 60%.

    É a leitura CERTA. O Anexo VII, item 14 ressalva "os produtos relacionados
    nos Anexos I e XV", e um cogumelo não é relacionado no XV — ele é RETIRADO
    de lá pela exceção do item 2. Flexibilizar a regra (deixar uma exceção mais
    longa vencer uma inclusão mais curta) acertaria o `0711.20.10` e erraria
    este; como não há critério uniforme que acerte os dois, mantém-se o que a
    lei escreve item a item, e a resposta mostra OS DOIS LADOS.
    """
    for codigo in ("07095100", "07108000"):
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducao.APLICADA
        assert (resolucao.anexo, resolucao.item) == ("VII", "14")
        assert resolucao.percentual_reducao == SESSENTA
        assert resolucao.tipo_correspondencia == "CAPITULO"
        # O raciocínio que um auditor faria, na própria resposta.
        assert ("XV", "2") in resolucao.itens_excluidos


def test_limitacao_2_a_posicao_0711_recebe_60_por_cento_apesar_da_excecao_do_anexo_vii():
    """AT-005 e a limitação declarada nº 2 — o espelho do cogumelo.

    O Anexo VII/14 excetua EXPRESSAMENTE a posição 07.11, mas o Anexo IX/10
    cobre o Capítulo 7 inteiro (sementes) e não excetua nada. Pela exceção ser
    escopada ao item, o `0711.20.10` recebe 60% por IX/10 — nunca por VII/14 —,
    com VII/14 declarado em `itens_excluidos`.

    Mesma causa raiz da limitação nº 1 (capítulos inteiros), e o motivo pelo
    qual as duas moram juntas no DESIGN.
    """
    resolucao = _resolver("07112010")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("IX", "10")
    assert resolucao.percentual_reducao == SESSENTA
    assert resolucao.tipo_correspondencia == "CAPITULO"
    assert ("VII", "14") in resolucao.itens_excluidos
    assert ("VII", "14") not in resolucao.itens_correspondentes


def test_at008_o_exceto_descritivo_nao_bloqueia_o_proprio_item():
    """`9018.19.80` é o código do item 1.3, cuja descrição diz "exceto os
    produtos classificados nos códigos 9018.11.00 …". Nenhum daqueles códigos
    desce de `90181980`: a cláusula é DESCRITIVA e não pode ter virado uma
    linha de exclusão que bloqueasse o próprio item."""
    resolucao = _resolver("90181980")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert resolucao.aplicada is True


def test_excluida_e_distinta_de_fora_do_anexo():
    """A resposta mais valiosa da feature: "sua prótese está na subposição
    9021.3, mas o Anexo XII exclui expressamente o 9021.39.91" é informação
    jurídica que o cliente não obteria de outro jeito, e é o oposto de "não está
    em Anexo nenhum"."""
    excluido = _resolver("90213991")
    fora = _resolver("22030000")

    assert excluido.situacao is not fora.situacao
    assert excluido.item == "5" and excluido.dispositivo_legal_ref is not None
    assert fora.item is None and fora.anexo is None
    assert fora.dispositivo_legal_ref is None


def test_excecao_de_um_anexo_nao_afeta_a_inclusao_de_outro():
    """A exclusão qualifica o item onde a lei a escreveu (Decisão 3 do Anexo I),
    e agora "o item" inclui o Anexo: uma exceção do XV não pode anular uma
    inclusão do XII."""
    consulta = ConsultaReducao(
        disponivel=True,
        linhas=[
            _fake("XII", 5, "90213", percentual=ZERO, texto="9021.3"),
            # Exceção de OUTRO Anexo, com o mesmo prefixo do código consultado.
            _fake(
                "XV", 2, "90213991", percentual=ZERO, excecao=True, texto="9021.39.91"
            ),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "90213991", consulta)

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("XII", "5")


# AT-013 — vizinhança de prefixo ---------------------------------------------


@pytest.mark.parametrize(
    "codigo",
    [
        "90223000",  # dentro de 9022, fora de 9022.12/13/14/19/21
        "90211090",  # 9021.10.90: irmão do 9021.10.10/9021.10.20 (itens 3 e 4)
        "87139090",  # 8713.90.90 não existe: XIII/2.2 é o 8713.90.00 exato
        "22030000",  # cerveja — o NCM do smoke test atual (AT-013)
        "84713000",  # capítulo 84: máquinas, fora dos 9 capítulos citados
        "61091000",  # capítulo 61: vestuário
    ],
)
def test_at013_vizinho_de_prefixo_nao_recebe_reducao(codigo):
    """Prova que o match respeita os limites reais de capítulo/posição/subposição
    e não é "contém a substring".

    Quatro códigos saíram desta lista nesta feature, e nenhum por bug: `07130000`
    (feijões) e `08020000` caem nos capítulos 7 e 8 do Anexo VII/14; `05119990`
    cai em `0511.9` do Anexo IX/14; `10061010` cai no capítulo 10 do Anexo
    VII/15. Os quatro passam a receber 60% por prefixos que a lei escreveu — o
    teste antigo os chamava de "vizinhos" porque só existiam 4 Anexos.
    """
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.FORA_DO_ANEXO
    assert resolucao.aplicada is False
    assert resolucao.percentual_reducao is None


@pytest.mark.parametrize(
    ("codigo", "anexo", "item"),
    [
        ("07130000", "VII", "14"),  # feijões — capítulo 7
        ("08020000", "VII", "14"),  # posição 08.02 — capítulo 8
        ("05119990", "IX", "14"),  # `0511.9` — produtos de origem animal
        ("10061010", "VII", "15"),  # arroz com casca — capítulo 10
    ],
)
def test_os_quatro_ex_vizinhos_agora_recebem_60_por_cento_por_prefixo_da_lei(
    codigo, anexo, item
):
    """O contra-teste do anterior: cada um dos quatro códigos que deixaram de ser
    "vizinhos" é nomeado aqui com o Anexo, o item e o percentual que passou a
    receber. Sem isto, a remoção deles da lista acima seria indistinguível de
    alguém enfraquecendo um teste que incomodou.
    """
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.percentual_reducao == SESSENTA


# AT-009 e não-regressão — desempate (Decisão 5) ------------------------------


def test_at009_desempate_de_tres_vias_do_anexo_xii():
    """Os itens 1.2, 1.3 e 14 citam o MESMO código `9018.19.80`. Todos os três
    dão zero — o desempate escolhe qual dispositivo CITAR, e por isso a lista
    completa volta na resposta: o auditor que estranhar "item 1.2" num monitor
    multiparâmetros vê os três e conclui sozinho."""
    resolucao = _resolver("90181980")

    assert (resolucao.anexo, resolucao.item) == ("XII", "1.2")
    assert resolucao.itens_correspondentes == (
        ("XII", "1.2"),
        ("XII", "1.3"),
        ("XII", "14"),
    )


def test_correspondentes_saem_em_ordem_numerica_e_nao_lexicografica():
    """A ordenação é pelos INTEIROS `(anexo_ordem, item, sub_item)`, nunca pela
    grafia.

    Nota de fidelidade: o DEFINE e o DESIGN justificam esta decisão dizendo que
    `"14" < "1.2"` lexicograficamente. Isso está **invertido** — '.' (0x2E) vem
    antes de '4' (0x34), então `"1.2" < "14"` como string também, e o trio
    1.2/1.3/14 do Anexo XII sai na mesma ordem das duas formas. A decisão
    continua certa, mas quem a prova é outro par: itens 2 e 10 do mesmo Anexo,
    onde a grafia daria "10" antes de "2". Anexo XI (fora desta feature) já tem
    itens 1.4/1.5/1.8/1.9, então o caso é iminente, não hipotético.
    """
    assert [item for _, item in _resolver("90181980").itens_correspondentes] == [
        "1.2",
        "1.3",
        "14",
    ]

    consulta = ConsultaReducao(
        disponivel=True,
        linhas=[
            _fake("XII", 10, "90222120", percentual=ZERO, texto="9022.21.20"),
            _fake("XII", 2, "90222120", percentual=ZERO, texto="9022.21.20"),
        ],
    )

    ordem = [
        item
        for _, item in resolver_item(
            "MERCADORIA", "90222120", consulta
        ).itens_correspondentes
    ]

    assert ordem == ["2", "10"]
    assert ordem != sorted(ordem), "ordenar as strings daria 10 antes de 2"

    # O caso real que a feature trouxe: 9 itens do Anexo IV em `9018.90.99`,
    # onde a ordenação lexicográfica poria "105" antes de "2".
    reais = [item for a, item in _resolver("90189099").itens_correspondentes if a == "IV"]

    assert reais == ["2", "29", "30", "31", "32", "68", "72", "92", "105"]
    assert reais != sorted(reais)


def test_sobreposicao_15_e_25_do_anexo_i_cita_o_mesmo_item_de_antes():
    """Não-regressão do desempate já shipado: `1902.19.00` (item 25) está dentro
    de `1902.1` (item 15). Vence o prefixo mais longo — regra 1, inalterada
    pela chave de 4 componentes."""
    resolucao = _resolver("19021900")

    assert (resolucao.anexo, resolucao.item) == ("I", "25")
    assert resolucao.itens_correspondentes == (("I", "15"), ("I", "25"))
    assert resolucao.texto_ncm == "1902.19.00"


def test_sobreposicao_4_e_26_do_anexo_i_cita_o_mesmo_item_de_antes():
    """Os dois citam `2106.90.90` com 8 dígitos — o desempate cai no critério do
    menor item, que na chave de SEIS componentes é o quinto e continua decidindo
    igual.

    O que mudou é que 8 itens do Anexo VI (fórmulas metabólicas) citam o mesmo
    código a 60%, e entram em `itens_correspondentes`. O VENCEDOR não muda: o
    componente 2 (maior redução) põe os quatro Anexos de zero à frente antes que
    qualquer ordinal seja consultado.
    """
    resolucao = _resolver("21069090")

    assert (resolucao.anexo, resolucao.item) == ("I", "4")
    assert resolucao.percentual_reducao == ZERO
    assert resolucao.itens_correspondentes[:2] == (("I", "4"), ("I", "26"))
    assert len([a for a, _ in resolucao.itens_correspondentes if a == "VI"]) == 8


def test_desempate_independe_da_ordem_das_linhas_do_banco():
    for codigo in ("21069090", "90181980", "19021900"):
        linhas = _consulta(codigo).linhas

        direta = resolver_item(
            "MERCADORIA", codigo, ConsultaReducao(True, list(linhas))
        )
        invertida = resolver_item(
            "MERCADORIA", codigo, ConsultaReducao(True, list(reversed(linhas)))
        )

        assert direta == invertida


def test_prefixo_mais_longo_vence_o_anexo_menor():
    """A ordem dos componentes importa: comprimento vem ANTES do Anexo, então um
    item mais específico de um Anexo posterior ganha de um genérico do Anexo I —
    o que descreve melhor a mercadoria."""
    consulta = ConsultaReducao(
        disponivel=True,
        linhas=[
            _fake("I", 8, "0901", percentual=ZERO, texto="09.01", descricao="café"),
            _fake("XV", 3, "09012100", percentual=ZERO, texto="0901.21.00"),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "09012100", consulta)

    assert (resolucao.anexo, resolucao.item) == ("XV", "3")


# Decisão 3 — os SEIS componentes do desempate, um a um -----------------------


def test_componente_2_a_maior_reducao_vence_um_ordinal_de_anexo_menor():
    """O componente que corrige os 35 empates, isolado num par inventado.

    Sem ele, `-anexo_ordem` faria o Anexo IV (4) vencer o XII (12) e a resposta
    seria 60% onde a lei dá zero — na direção PERIGOSA. Com ele, a escolha entre
    0% e 40% da alíquota nunca cai num número de Anexo.
    """
    consulta = ConsultaReducao(
        disponivel=True,
        linhas=[
            _fake("IV", 2, "90189099", percentual=SESSENTA),
            _fake("XII", 9, "90189099", percentual=ZERO),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "90189099", consulta)

    assert (resolucao.anexo, resolucao.item) == ("XII", "9")
    assert resolucao.percentual_reducao == ZERO


def test_componente_3_a_reducao_incondicional_vence_a_condicionada_na_citacao():
    """Quando o comprador é qualificado, `9021.10.10` vale ZERO por dois
    caminhos: IV/42 (art. 131 + art. 144, II — condicionado ao comprador) e
    XII/3 (art. 144, I — incondicional). O número é o mesmo; a CITAÇÃO não.

    Citar o incondicional é mais forte numa defesa fiscal, porque não depende de
    provar a qualidade do adquirente. Sem o componente 3, `-anexo_ordem` citaria
    o Anexo IV (4 < 12) — o número certo com a fundamentação mais frágil.
    """
    resolucao = _resolver("90211010", comprador="ORGAO_PUBLICO")

    assert (resolucao.anexo, resolucao.item) == ("XII", "3")
    assert resolucao.percentual_reducao == ZERO
    assert resolucao.dispositivo_legal_ref.endswith("Anexo XII, item 3")
    assert resolucao.dispositivo_legal_comprador is None, (
        "o vencedor é incondicional: não há condição de comprador a citar"
    )
    assert ("IV", "42") in resolucao.itens_correspondentes


def test_o_desempate_e_uma_ordem_total_sobre_o_seed_inteiro():
    """Ordem TOTAL, não parcial: para todo código que casa com mais de uma linha,
    inverter a ordem em que o banco devolveu as linhas não pode mudar nada.

    Sem isso, `2106.90.90` citaria ora I/4, ora I/26, ora um dos 8 itens do
    Anexo VI conforme o plano de execução do Postgres — não-determinismo que só
    apareceria em produção, num campo que vai para uma defesa fiscal.
    """
    codigos = sorted(
        {linha.prefixo.ljust(8, "0") for linha in SEED},
    )
    for codigo in codigos:
        linhas = list(_consulta(codigo).linhas)
        direta = resolver_item("MERCADORIA", codigo, ConsultaReducao(True, linhas))
        invertida = resolver_item(
            "MERCADORIA", codigo, ConsultaReducao(True, list(reversed(linhas)))
        )

        assert direta == invertida, f"{codigo} depende da ordem das linhas do banco"


# Os 6 Anexos novos, um a um — AT-001, AT-002, AT-003, AT-006, AT-011 ---------


def test_at001_o_sabao_de_toucador_recebe_60_por_cento_pelo_anexo_viii():
    """AT-001, o caminho novo no caso mais simples que existe: Anexo sem
    exceção, sem sub-item, sem condição de comprador e com correspondência
    exata de 8 dígitos. Se este falhar, nada do mecanismo de 60% funciona."""
    resolucao = _resolver("34011190")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("VIII", "1")
    assert resolucao.percentual_reducao == SESSENTA
    assert (
        resolucao.dispositivo_legal_ref == "LCP 214/2025, art. 136, Anexo VIII, item 1"
    )
    assert resolucao.tipo_correspondencia == "EXATO"
    assert resolucao.texto_ncm == "3401.11.90"
    assert resolucao.zero_por_comprador_disponivel is False
    assert resolucao.dispositivo_legal_comprador is None


def test_at002_o_arroz_do_anexo_i_vence_o_capitulo_10_do_anexo_vii():
    """AT-002 — a precedência que a LEI ESCREVE, saindo do componente 1 sem
    nenhuma regra própria.

    O Anexo VII, item 15 cobre "cereais do capítulo 10", mas ressalva
    expressamente "os produtos relacionados no Anexo I". O `1006.30.21` (arroz
    parboilizado) está no Anexo I, item 1, com o prefixo `1006.30` — seis
    dígitos contra os dois do capítulo. Especificidade resolve, e a migração 010
    prova por asserção que é assim em TODOS os 13 pares em que isso importa.
    """
    resolucao = _resolver("10063021")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("I", "1")
    assert resolucao.percentual_reducao == ZERO, "zero do Anexo I, nunca 60% do VII"
    assert resolucao.texto_ncm == "1006.30"
    # Os dois lados visíveis: quem estranhar vê o VII/15 na lista.
    assert ("VII", "15") in resolucao.itens_correspondentes


def test_at003_a_banana_do_anexo_xv_vence_o_capitulo_8_do_anexo_vii():
    """AT-003 — a remissão DUPLA do item 14 do Anexo VII ("ressalvados os
    produtos relacionados nos Anexos I e XV"). `0803.10.00` é banana, no Anexo
    XV item 3 (`08.03`, quatro dígitos) contra o capítulo `08` do VII/14."""
    resolucao = _resolver("08031000")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("XV", "3")
    assert resolucao.percentual_reducao == ZERO
    assert ("VII", "14") in resolucao.itens_correspondentes


def test_a_ressalva_do_anexo_vii_e_honrada_em_todos_os_itens_que_a_escrevem():
    """A generalização de AT-002/AT-003: para os itens 4, 5, 6, 14 e 15 do Anexo
    VII, TODA inclusão de Anexo zero que se sobreponha tem prefixo
    estritamente mais longo — que é a condição sob a qual o desempate genérico
    honra a ressalva sem regra própria.

    É a mesma asserção que a migração 010 executa em SQL (a única lá que protege
    uma regra JURÍDICA em vez de uma contagem). Aqui em Python, para falhar no CI
    antes de chegar ao banco.
    """
    violacoes = [
        (sete.item, sete.prefixo, zero.anexo, zero.item, zero.prefixo)
        for sete in INCLUSOES
        if sete.anexo == "VII" and sete.item in (4, 5, 6, 14, 15)
        for zero in INCLUSOES
        if zero.anexo in ANEXOS_ZERO
        and zero.prefixo.startswith(sete.prefixo)
        and len(zero.prefixo) <= len(sete.prefixo)
    ]

    assert violacoes == []


def test_at006_o_comando_de_embreagem_casa_o_sub_item_1_1_do_anexo_v():
    """AT-006 — cabeçalho + sub-item num Anexo de 60%. O item 1 do Anexo V é um
    cabeçalho sem NCM próprio ("Acessórios e adaptações especiais para
    veículos..."); o código mora no 1.1."""
    resolucao = _resolver("87089910")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("V", "1.1")
    assert resolucao.percentual_reducao == SESSENTA
    assert (
        resolucao.dispositivo_legal_ref == "LCP 214/2025, art. 132, Anexo V, item 1.1"
    )
    # Sem o cabeçalho, a fundamentação seria só a descrição do sub-item.
    assert resolucao.descricao_contexto is not None
    assert "veículos" in resolucao.descricao_contexto.lower()


def test_at011_o_item_2_do_anexo_vii_traz_o_texto_original_e_nao_a_redacao_vetada():
    """AT-011 — a LC 227/2026 tentou dar nova redação ao item 2 do Anexo VII e a
    alteração foi INTEGRALMENTE VETADA (o texto publicado mostra literalmente
    "2 (VETADO)"). O texto vigente é o ORIGINAL, e é ele que está na tabela.

    Os três códigos do item 2 são a prova de que a transcrição usou a publicação
    original e não a "(NR)" que nunca entrou em vigor.
    """
    for codigo in ("04032000", "04039000", "22029900"):
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducao.APLICADA, codigo
        assert resolucao.percentual_reducao == SESSENTA
        # `2202.99.00` também está no Anexo VI (itens 47 e 48), que vence por
        # ordinal — o percentual é o mesmo, só a citação muda (Decisão 12-C).
        assert ("VII", "2") in resolucao.itens_correspondentes

    leite = _resolver("04032000")

    assert (leite.anexo, leite.item) == ("VII", "2")
    assert "Leite fermentado" in leite.descricao
    assert "VETADO" not in leite.descricao


def test_o_9619_recebe_60_por_cento_apesar_do_art_147_dar_zero_ao_mesmo_codigo():
    """A limitação declarada nº 4 — o único conflito REAL da lei consigo mesma
    nesta feature, e a razão de ele estar documentado em vez de escondido.

    `9619.00.00` é 60% pelo Anexo VIII, item 7 (fraldas e artigos higiênicos
    semelhantes) e é ZERO pelo art. 147, que reduz a zero tampões, absorventes,
    calcinhas absorventes e coletores menstruais — no MESMO código, e SEM Anexo,
    o que o deixa fora desta tabela.

    Indecidível por NCM: os dois produtos compartilham o código. Aplica-se 60%,
    que over-tributa o absorvente — a direção SEGURA —, e o art. 147 vai para o
    roadmap como feature própria.
    """
    resolucao = _resolver("96190000")

    assert resolucao.situacao is SituacaoReducao.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("VIII", "7")
    assert resolucao.percentual_reducao == SESSENTA
    assert resolucao.percentual_reducao != ZERO, (
        "aplicar zero aqui presumiria que a mercadoria é um absorvente, e o "
        "payload não tem como distinguir — a direção segura é cobrar mais"
    )


# Decisão 6 — a condição de comprador dos Anexos IV, V e VI -------------------


@pytest.mark.parametrize(
    ("codigo", "anexo", "item", "dispositivo"),
    [
        ("39269030", "IV", "1", "LCP 214/2025, art. 144, II"),
        ("87089910", "V", "1.1", "LCP 214/2025, art. 145, II"),
        ("29362812", "VI", "1", "LCP 214/2025, art. 146, § 2º"),
    ],
)
def test_at010_sem_comprador_informado_aplica_60_e_DECLARA_que_poderia_ser_zero(
    codigo, anexo, item, dispositivo
):
    """AT-010 — o MUST do DEFINE, na metade que o campo ausente ainda cobre.

    Sem `comprador_tipo`, aplica-se 60% (nunca zero: presumir comprador
    qualificado subestimaria a tributação da maioria privada). Mas a resposta
    NÃO fica em silêncio: `zero_por_comprador_disponivel` diz que a alíquota
    real seria ZERO para órgão público ou entidade CEBAS, e
    `dispositivo_legal_comprador` diz por qual dispositivo.
    """
    resolucao = _resolver(codigo)

    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.percentual_reducao == SESSENTA
    assert resolucao.zero_por_comprador_disponivel is True
    assert resolucao.dispositivo_legal_comprador == dispositivo


@pytest.mark.parametrize("comprador", ["ORGAO_PUBLICO", "ENTIDADE_CEBAS_SUS"])
@pytest.mark.parametrize(
    ("codigo", "anexo", "item"),
    [("39269030", "IV", "1"), ("87089910", "V", "1.1"), ("29362812", "VI", "1")],
)
def test_at010b_com_comprador_qualificado_a_aliquota_vai_a_zero(
    codigo, anexo, item, comprador
):
    """AT-010b — a outra metade do MUST, que só existe porque o campo entrou no
    payload: "nunca aplicar 60% quando o comprador é conhecido como órgão
    público/CEBAS" é insatisfazível se o payload não tem como dizer quem compra.

    Os DOIS dispositivos continuam citados: o do item (art. 131/132/133) e o da
    condição (art. 144, II / 145, II / 146, § 2º).
    """
    resolucao = _resolver(codigo, comprador=comprador)

    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.percentual_reducao == ZERO
    assert resolucao.dispositivo_legal_ref is not None
    assert resolucao.dispositivo_legal_comprador is not None
    # Já está no zero: não há mais nada "disponível" a declarar.
    assert resolucao.zero_por_comprador_disponivel is False


def test_o_comprador_nao_toca_os_anexos_sem_condicao():
    """A condição é dos Anexos IV, V e VI — e só. Um sabão de toucador do Anexo
    VIII continua a 60% para órgão público, porque o art. 136 não tem inciso
    equivalente. Estender a condição "por simetria" inventaria um benefício."""
    for comprador in (None, "ORGAO_PUBLICO"):
        resolucao = _resolver("34011190", comprador=comprador)

        assert resolucao.percentual_reducao == SESSENTA
        assert resolucao.zero_por_comprador_disponivel is False
        assert resolucao.dispositivo_legal_comprador is None


def test_o_comprador_nao_muda_nada_nos_quatro_anexos_ja_shipados():
    """Não-regressão: os Anexos de zero não têm — nem podem ter — condição de
    comprador (seria uma condição para chegar onde já estão, e a CHECK
    `so_percentual_tem_condicao_de_comprador` recusa isso no banco)."""
    for codigo in ("04051000", "87131000", "90181980", "06031100"):
        sem = _resolver(codigo)
        com = _resolver(codigo, comprador="ORGAO_PUBLICO")

        assert sem == com, f"{codigo} mudou de resposta por causa do comprador"
        assert sem.percentual_reducao == ZERO


def test_apenas_os_anexos_iv_v_e_vi_tem_condicao_de_comprador_no_catalogo():
    """Os três, e exatamente os três — arts. 144, II; 145, II; 146, § 2º. Um
    quarto significaria que alguém estendeu a condição sem ler a lei."""
    com_condicao = {
        anexo for anexo, (_, _, ref) in CATALOGO.items() if ref is not None
    }

    assert com_condicao == {"IV", "V", "VI"}
    assert all(CATALOGO[a][1] == SESSENTA for a in com_condicao)


# Situações restantes do enum ------------------------------------------------


def test_servico_e_nao_aplicavel_sem_sequer_olhar_o_ncm():
    resolucao = resolver_item("SERVICO", "87131000", _consulta("87131000"))

    assert resolucao.situacao is SituacaoReducao.NAO_APLICAVEL
    assert resolucao.item is None and resolucao.anexo is None


@pytest.mark.parametrize(
    "consulta", [ConsultaReducao(True), ConsultaReducao(False)]
)
def test_ncm_ilegivel_e_propriedade_do_payload_nao_do_banco(consulta):
    """A guarda de formato vem ANTES da de disponibilidade: `0405` é subposição,
    nenhum Anexo o conteria, e CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta (lição da feature 1)."""
    resolucao = resolver_item("MERCADORIA", "0405", consulta)

    assert resolucao.situacao is SituacaoReducao.NCM_NAO_RECONHECIDO


def test_consulta_indisponivel_nao_e_fora_do_anexo():
    """Dizer "este produto não tem redução" sem ter conseguido consultar é
    afirmação jurídica falsa emitida por omissão."""
    resolucao = resolver_item("MERCADORIA", "87131000", ConsultaReducao(False))

    assert resolucao.situacao is SituacaoReducao.CONSULTA_INDISPONIVEL
    assert resolucao.avaliada is False


def test_fora_do_anexo_e_servico_contam_como_avaliados():
    """Decisão 9: só "não sei" impede o total dispensado; "sei que não tem
    benefício" não."""
    assert _resolver("22030000").avaliada is True
    assert _resolver("87131000", natureza="SERVICO").avaliada is True
    assert _resolver("90213991").avaliada is True


# consultar_com_seguranca ----------------------------------------------------


class PoolFalso:
    def __init__(self, erro: Exception | None = None):
        self.erro = erro
        self.conexoes = 0

    def connection(self):
        self.conexoes += 1
        if self.erro:
            raise self.erro
        raise AssertionError("não deveria chegar aqui nestes testes")


def test_pool_ausente_e_indisponibilidade_nao_ausencia_de_dado():
    consulta = consultar_com_seguranca(None, ["0405"])

    assert consulta.disponivel is False
    assert list(consulta.linhas) == []


def test_lista_vazia_com_pool_presente_nao_abre_conexao_e_e_disponivel():
    """Não ter NADA a perguntar é diferente de não CONSEGUIR perguntar — a
    correção que a feature 1 precisou fazer, replicada aqui de propósito."""
    pool = PoolFalso()

    consulta = consultar_com_seguranca(pool, [])

    assert consulta.disponivel is True
    assert pool.conexoes == 0


def test_falha_do_banco_vira_indisponibilidade_e_nunca_propaga(caplog):
    """Cobre também a janela do rename da Decisão 13: durante ela o SELECT fala
    com um nome de tabela que ainda/já não existe."""
    pool = PoolFalso(ConnectionError("Cloud SQL fora do ar (simulado)"))

    consulta = consultar_com_seguranca(pool, ["04051000"])

    assert consulta.disponivel is False
    assert "Falha ao consultar os Anexos de redução" in caplog.text


# motor_calculo/reducoes.py — INTOCADO pela feature (Decisão 9) --------------


def _resultado(valor_base="1000.00", is_="0.00", cbs="9.00", ibs="1.00"):
    total = Decimal(is_) + Decimal(cbs) + Decimal(ibs)
    return ResultadoCalculo(
        valor_base=Decimal(valor_base),
        valor_is=Decimal(is_),
        valor_cbs=Decimal(cbs),
        valor_ibs=Decimal(ibs),
        total_tributos=total,
        valor_liquido=Decimal(valor_base) - total,
        fonte_legal="LCP 214/2025, arts. 343 e 346",
    )


def test_reducao_zera_cbs_e_ibs_e_preserva_o_imposto_seletivo():
    """Os arts. 125/144/145/148 reduzem a zero as alíquotas "do IBS e da CBS" —
    e só. O IS tem lista própria (Anexo XVII), fora do escopo: zerá-lo seria
    inventar um benefício que a lei não deu."""
    reduzido = aplicar_reducao_a_zero(_resultado(is_="50.00"))

    assert reduzido.valor_cbs == Decimal("0.00")
    assert reduzido.valor_ibs == Decimal("0.00")
    assert reduzido.valor_is == Decimal("50.00")


def test_invariante_do_liquido_sobrevive_a_reducao():
    """Zerar CBS/IBS sem recompor o líquido produziria uma resposta
    internamente contraditória: líquido menor que o bruto sem tributo que o
    justifique."""
    reduzido = aplicar_reducao_a_zero(_resultado(is_="50.00"))

    assert reduzido.total_tributos == reduzido.valor_is
    assert reduzido.valor_liquido == reduzido.valor_base - reduzido.total_tributos


def test_sem_split_payment_o_liquido_e_o_bruto():
    reduzido = aplicar_reducao_a_zero(_resultado(is_="50.00"), split_payment_active=False)

    assert reduzido.valor_liquido == reduzido.valor_base


def test_em_2026_o_liquido_reduzido_e_o_valor_cheio():
    """O IS não incide em 2026, então zerar CBS/IBS zera a carga inteira do IVA
    Dual — o líquido volta a ser o bruto."""
    reduzido = aplicar_reducao_a_zero(_resultado())

    assert reduzido.total_tributos == Decimal("0.00")
    assert reduzido.valor_liquido == Decimal("1000.00")


def test_reducao_nao_muta_o_resultado_original():
    original = _resultado()

    aplicar_reducao_a_zero(original)

    assert original.valor_cbs == Decimal("9.00")
    assert original.fonte_legal.startswith("LCP 214/2025")
