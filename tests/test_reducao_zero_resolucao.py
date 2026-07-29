"""Lógica pura dos 4 Anexos de redução a zero — sem banco, sem HTTP.

O seed dos 60 itens é **lido das próprias migrações** (005 para o Anexo I, 008
para os Anexos XII, XIII e XV), não redigitado aqui: são dados legais
transcritos à mão de tabelas do DOU, e uma segunda cópia em Python seria uma
segunda fonte de verdade capaz de divergir em silêncio da que o banco de
produção carrega. Assim, estes testes exercitam os 151 prefixos reais (127
inclusões + 24 exceções) sem precisar de PostgreSQL — o SQL de verdade é
`test_reducao_zero_db.py`.
"""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from api.ncm import digitos_ncm, prefixos_ncm
from api.reducao_zero import (
    ConsultaReducaoZero,
    SituacaoReducaoZero,
    consultar_com_seguranca,
    formatar_item,
    resolver_item,
)
from db.repositorio import PrefixoReducaoZero
from motor_calculo.engine import ResultadoCalculo
from motor_calculo.reducoes import aplicar_reducao_a_zero

MIGRACOES = Path(__file__).resolve().parents[1] / "db" / "migrations"
MIGRACAO_ANEXO_I = MIGRACOES / "005_cesta_basica_anexo_i.sql"
MIGRACAO_XII_XIII_XV = MIGRACOES / "008_anexos_reducao_zero_xii_xiii_xv.sql"

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

ORDINAL = {"I": 1, "XII": 12, "XIII": 13, "XV": 15}


def _carregar_anexo_i() -> tuple[dict, list[PrefixoReducaoZero]]:
    sql = MIGRACAO_ANEXO_I.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO cesta_basica_anexo_i ")[1].split("ON CONFLICT")[0]
    itens = {
        ("I", int(m[1]), 0): (m[2].replace("''", "'"), m[3])
        for m in _LINHA_ITEM_005.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO cesta_basica_anexo_i_ncm")[1].split("ON CONFLICT")[0]
    linhas = []
    for item, prefixo, excecao, alinea, texto in _LINHA_NCM_005.findall(bloco_ncm):
        descricao, dispositivo = itens[("I", int(item), 0)]
        linhas.append(
            PrefixoReducaoZero(
                anexo="I",
                anexo_ordem=1,
                item=int(item),
                sub_item=0,
                prefixo=prefixo,
                excecao=excecao == "TRUE",
                texto_ncm=texto,
                alinea=None if alinea == "NULL" else alinea.strip("'"),
                descricao=descricao,
                # O Anexo I não tem sub-item, então nunca tem pai.
                descricao_contexto=None,
                dispositivo_legal_ref=dispositivo,
            )
        )
    return itens, linhas


def _carregar_xii_xiii_xv() -> tuple[dict, list[PrefixoReducaoZero]]:
    sql = MIGRACAO_XII_XIII_XV.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO anexos_reducao_zero (")[1].split("ON CONFLICT")[0]
    itens = {
        (m[1], int(m[3]), int(m[4])): (m[5].replace("''", "'"), m[6])
        for m in _LINHA_ITEM_008.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO anexos_reducao_zero_ncm")[1].split("ON CONFLICT")[0]
    linhas = []
    for anexo, item, sub_item, prefixo, excecao, alinea, texto in _LINHA_NCM_008.findall(
        bloco_ncm
    ):
        descricao, dispositivo = itens[(anexo, int(item), int(sub_item))]
        # Mesmo LEFT JOIN do repositório: o pai de (XIII, 2, 1) é (XIII, 2, 0).
        pai = itens.get((anexo, int(item), 0)) if int(sub_item) > 0 else None
        linhas.append(
            PrefixoReducaoZero(
                anexo=anexo,
                anexo_ordem=ORDINAL[anexo],
                item=int(item),
                sub_item=int(sub_item),
                prefixo=prefixo,
                excecao=excecao == "TRUE",
                texto_ncm=texto,
                alinea=None if alinea == "NULL" else alinea.strip("'"),
                descricao=descricao,
                descricao_contexto=pai[0] if pai else None,
                dispositivo_legal_ref=dispositivo,
            )
        )
    return itens, linhas


ITENS_I, LINHAS_I = _carregar_anexo_i()
ITENS_NOVOS, LINHAS_NOVAS = _carregar_xii_xiii_xv()

ITENS = {**ITENS_I, **ITENS_NOVOS}
SEED = LINHAS_I + LINHAS_NOVAS
INCLUSOES = [linha for linha in SEED if not linha.excecao]
EXCECOES = [linha for linha in SEED if linha.excecao]


def _consulta(codigo: str) -> ConsultaReducaoZero:
    """Só as linhas que o `= ANY(%s)` devolveria para este código — é assim que
    o lote chega do banco, e não a tabela inteira."""
    candidatos = set(prefixos_ncm(codigo))
    return ConsultaReducaoZero(
        disponivel=True, linhas=[linha for linha in SEED if linha.prefixo in candidatos]
    )


def _resolver(codigo: str, natureza: str = "MERCADORIA"):
    return resolver_item(natureza, codigo, _consulta(codigo))


# Integridade do seed — as contagens de fechamento do DESIGN ------------------


def test_seed_tem_60_itens_127_inclusoes_e_24_excecoes():
    """Contagem é teste de truncamento: uma migração cortada pela metade passa
    em toda constraint e falha aqui."""
    assert len(ITENS) == 60
    assert len(SEED) == 151
    assert len(INCLUSOES) == 127
    assert len(EXCECOES) == 24


@pytest.mark.parametrize(
    ("anexo", "itens", "prefixos"),
    [("I", 26, 95), ("XII", 20, 24), ("XIII", 8, 7), ("XV", 6, 25)],
)
def test_contagem_por_anexo_bate_com_a_transcricao(anexo, itens, prefixos):
    """Por Anexo, e não global, para que a falha diga ONDE."""
    assert len([chave for chave in ITENS if chave[0] == anexo]) == itens
    assert len([linha for linha in SEED if linha.anexo == anexo]) == prefixos


def test_comprimentos_de_prefixo_ficam_na_lista_que_prefixos_ncm_enxerga():
    """Acoplamento explícito com `_COMPRIMENTOS_PREFIXO` e com a CHECK
    `prefixo_comprimento_valido`: um prefixo fora da lista nunca casaria com
    nada — falso negativo permanente e mudo. O 2 só existe no Anexo XV, item 4
    (Capítulo 6); o 7 só no Anexo I (`0210.99.1`)."""
    comprimentos = {len(linha.prefixo) for linha in SEED}

    assert comprimentos == {2, 4, 5, 6, 7, 8}
    assert [linha.prefixo for linha in SEED if len(linha.prefixo) == 2] == ["06"]
    assert [linha.prefixo for linha in SEED if len(linha.prefixo) == 7] == ["0210991"]


def test_nenhuma_duplicata_de_anexo_item_subitem_prefixo_excecao():
    contagem = Counter(
        (linha.anexo, linha.item, linha.sub_item, linha.prefixo, linha.excecao)
        for linha in SEED
    )

    assert [chave for chave, n in contagem.items() if n > 1] == []


def test_os_dois_unicos_prefixos_compartilhados_entre_itens():
    """Se aparecer um terceiro, a regra de desempate da Decisão 5 passa a valer
    para um caso que ninguém examinou."""
    por_prefixo: dict[str, set[tuple[str, str]]] = {}
    for linha in SEED:
        por_prefixo.setdefault(linha.prefixo, set()).add(
            (linha.anexo, formatar_item(linha.item, linha.sub_item))
        )

    assert {p: sorted(i) for p, i in por_prefixo.items() if len(i) > 1} == {
        "21069090": [("I", "26"), ("I", "4")],
        "90181980": [("XII", "1.2"), ("XII", "1.3"), ("XII", "14")],
    }


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


def test_apenas_os_dois_cabecalhos_conhecidos_nao_tem_linha_de_prefixo():
    """XII/1 e XIII/2 são cabeçalhos sem célula de NCM no DOU (Decisão 7). Um
    terceiro item sem prefixo seria INSERT truncado."""
    com_prefixo = {(linha.anexo, linha.item, linha.sub_item) for linha in SEED}

    assert sorted(set(ITENS) - com_prefixo) == [("XII", 1, 0), ("XIII", 2, 0)]


def test_todo_sub_item_tem_o_cabecalho_que_lhe_da_sentido():
    sub_itens = [chave for chave in ITENS if chave[2] > 0]

    assert len(sub_itens) == 5  # XII/1.1-1.3 e XIII/2.1-2.2
    for anexo, item, _ in sub_itens:
        assert (anexo, item, 0) in ITENS


def test_nenhum_codigo_concreto_e_compartilhado_entre_anexos_diferentes():
    """Decisão 12 em Python (a versão SQL roda contra o Postgres do CI): dois
    Anexos compartilham um código de 8 dígitos se, e somente se, um prefixo de
    inclusão de um for prefixo do outro. A margem hoje é de UMA posição NCM —
    o Anexo I usa `0713` (feijões) e o Anexo XV vai de `0701` a `0710` mais
    `0714` —, exatamente o tipo de coisa que a leitura manual erra na próxima."""
    colisoes = [
        (a.anexo, a.prefixo, b.anexo, b.prefixo)
        for a in INCLUSOES
        for b in INCLUSOES
        if a.anexo < b.anexo
        and (b.prefixo.startswith(a.prefixo) or a.prefixo.startswith(b.prefixo))
    ]

    assert colisoes == []


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

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
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


def test_todas_as_127_inclusoes_dos_quatro_anexos_resolvem_aplicada():
    """Cobre os 60 itens de uma vez: cada prefixo, completado com zeros até 8
    dígitos, precisa cair no próprio item. `in itens_correspondentes` em vez de
    `== item` por causa das sobreposições, onde o desempate escolhe um."""
    for inclusao in INCLUSOES:
        codigo = inclusao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducaoZero.APLICADA, (
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

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.tipo_correspondencia == "PREFIXO"
    # "casou com a posição 07.14" é auditável; "casou com 0714" não é a grafia
    # que o DOU publicou.
    assert resolucao.texto_ncm == texto


@pytest.mark.parametrize("codigo", ["06031100", "06029090", "06011000", "06049000"])
def test_at005_capitulo_6_e_o_unico_prefixo_de_dois_digitos_e_ele_funciona(codigo):
    """O caso que prova a Decisão 4 ponta a ponta: `_COMPRIMENTOS_PREFIXO` e a
    CHECK da migração 007 mudaram juntos. Se só um tivesse mudado, tudo o mais
    continuaria verde."""
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("XV", "4")
    assert resolucao.texto_ncm == "06"
    assert resolucao.tipo_correspondencia == "PREFIXO"


def test_o_capitulo_6_devolve_a_descricao_literal_que_qualifica_o_item():
    """A limitação mais perigosa da feature — e a única que erra na direção do
    tributo A MENOS: `06` concede zero a todo o capítulo, enquanto o item
    qualifica. Não sendo verificável a partir do payload, a mitigação é
    devolver o texto do item para o cliente conferir."""
    resolucao = _resolver("06031100")

    assert "cultivados para fins alimentares" in resolucao.descricao
    assert "Capítulo 6" in resolucao.descricao


def test_prefixo_de_7_digitos_do_anexo_i_continua_resolvendo():
    """`0210.99.1` é o único prefixo de 7 dígitos do projeto — comprimento que a
    lista precisa continuar enxergando depois da entrada do 2."""
    resolucao = _resolver("02109911")

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("I", "19")
    assert resolucao.texto_ncm == "0210.99.1"


# AT-006 e AT-007 — exceções operantes nos Anexos novos -----------------------


@pytest.mark.parametrize(
    ("codigo", "anexo", "item", "texto"),
    [
        ("90213991", "XII", "5", "9021.39.91"),  # prótese excluída pelo próprio item
        ("90213999", "XII", "5", "9021.39.99"),
        ("90221991", "XII", "7", "9022.19.91"),  # raio X excluído do item 7
        ("07095100", "XV", "2", "0709.5"),  # cogumelos
        ("07108000", "XV", "2", "0710.80.00"),  # trufas congeladas
    ],
)
def test_at006_codigo_excluido_pelo_proprio_item_nunca_recebe_zero(
    codigo, anexo, item, texto
):
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducaoZero.EXCLUIDA_EXPRESSAMENTE
    assert resolucao.aplicada is False, "exceção do Anexo jamais vira alíquota zero"
    assert (resolucao.anexo, resolucao.item) == (anexo, item)
    assert resolucao.texto_ncm == texto
    assert resolucao.tipo_correspondencia == "EXCECAO"


def test_todas_as_24_excecoes_dos_quatro_anexos_bloqueiam_a_reducao():
    for excecao in EXCECOES:
        codigo = excecao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoReducaoZero.EXCLUIDA_EXPRESSAMENTE, (
            f"{excecao.texto_ncm} (Anexo {excecao.anexo}, item "
            f"{formatar_item(excecao.item, excecao.sub_item)}) deveria estar excluído"
        )


def test_at008_o_exceto_descritivo_nao_bloqueia_o_proprio_item():
    """`9018.19.80` é o código do item 1.3, cuja descrição diz "exceto os
    produtos classificados nos códigos 9018.11.00 …". Nenhum daqueles códigos
    desce de `90181980`: a cláusula é DESCRITIVA e não pode ter virado uma
    linha de exclusão que bloqueasse o próprio item."""
    resolucao = _resolver("90181980")

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
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
    consulta = ConsultaReducaoZero(
        disponivel=True,
        linhas=[
            PrefixoReducaoZero(
                "XII", 12, 5, 0, "90213", False, "9021.3", None,
                "próteses", None, "LCP 214/2025, art. 144, Anexo XII, item 5",
            ),
            # Exceção de OUTRO Anexo, com o mesmo prefixo do código consultado.
            PrefixoReducaoZero(
                "XV", 15, 2, 0, "90213991", True, "9021.39.91", None,
                "hortícolas", None, "LCP 214/2025, art. 148, Anexo XV, item 2",
            ),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "90213991", consulta)

    assert resolucao.situacao is SituacaoReducaoZero.APLICADA
    assert (resolucao.anexo, resolucao.item) == ("XII", "5")


# AT-010 — vizinhança de prefixo ---------------------------------------------


@pytest.mark.parametrize(
    "codigo",
    [
        "90223000",  # dentro de 9022, fora de 9022.12/13/14/19/21
        "90211090",  # 9021.10.90: irmão do 9021.10.10/9021.10.20 (itens 3 e 4)
        "87139090",  # 8713.90.90 não existe: XIII/2.2 é o 8713.90.00 exato
        "07130000",  # posição 07.13 (feijões): fora das 07.01-07.10 do Anexo XV
        "08020000",  # posição 08.02: vizinha das 08.03-08.11 do item 3
        "05119990",  # capítulo 05, vizinho do capítulo 06 do item 4
        "22030000",  # cerveja — o NCM do smoke test atual
        "10061010",  # arroz com casca: dentro de 1006, fora de 1006.20/30/40.00
    ],
)
def test_at010_vizinho_de_prefixo_nao_recebe_reducao(codigo):
    """Prova que o match respeita os limites reais de capítulo/posição/subposição
    e não é "contém a substring"."""
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoReducaoZero.FORA_DO_ANEXO
    assert resolucao.aplicada is False


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

    consulta = ConsultaReducaoZero(
        disponivel=True,
        linhas=[
            PrefixoReducaoZero(
                "XII", 12, 10, 0, "90222120", False, "9022.21.20", None,
                "gamaterapia", None, "LCP 214/2025, art. 144, Anexo XII, item 10",
            ),
            PrefixoReducaoZero(
                "XII", 12, 2, 0, "90222120", False, "9022.21.20", None,
                "inventado", None, "LCP 214/2025, art. 144, Anexo XII, item 2",
            ),
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
    menor item, que na chave nova é o terceiro componente e continua decidindo
    igual."""
    resolucao = _resolver("21069090")

    assert (resolucao.anexo, resolucao.item) == ("I", "4")
    assert resolucao.itens_correspondentes == (("I", "4"), ("I", "26"))


def test_desempate_independe_da_ordem_das_linhas_do_banco():
    for codigo in ("21069090", "90181980", "19021900"):
        linhas = _consulta(codigo).linhas

        direta = resolver_item(
            "MERCADORIA", codigo, ConsultaReducaoZero(True, list(linhas))
        )
        invertida = resolver_item(
            "MERCADORIA", codigo, ConsultaReducaoZero(True, list(reversed(linhas)))
        )

        assert direta == invertida


def test_prefixo_mais_longo_vence_o_anexo_menor():
    """A ordem dos componentes importa: comprimento vem ANTES do Anexo, então um
    item mais específico de um Anexo posterior ganha de um genérico do Anexo I —
    o que descreve melhor a mercadoria."""
    consulta = ConsultaReducaoZero(
        disponivel=True,
        linhas=[
            PrefixoReducaoZero(
                "I", 1, 8, 0, "0901", False, "09.01", None,
                "café", None, "LCP 214/2025, art. 125, Anexo I, item 8",
            ),
            PrefixoReducaoZero(
                "XV", 15, 3, 0, "09012100", False, "0901.21.00", None,
                "inventado", None, "LCP 214/2025, art. 148, Anexo XV, item 3",
            ),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "09012100", consulta)

    assert (resolucao.anexo, resolucao.item) == ("XV", "3")


# Situações restantes do enum ------------------------------------------------


def test_servico_e_nao_aplicavel_sem_sequer_olhar_o_ncm():
    resolucao = resolver_item("SERVICO", "87131000", _consulta("87131000"))

    assert resolucao.situacao is SituacaoReducaoZero.NAO_APLICAVEL
    assert resolucao.item is None and resolucao.anexo is None


@pytest.mark.parametrize(
    "consulta", [ConsultaReducaoZero(True), ConsultaReducaoZero(False)]
)
def test_ncm_ilegivel_e_propriedade_do_payload_nao_do_banco(consulta):
    """A guarda de formato vem ANTES da de disponibilidade: `0405` é subposição,
    nenhum Anexo o conteria, e CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta (lição da feature 1)."""
    resolucao = resolver_item("MERCADORIA", "0405", consulta)

    assert resolucao.situacao is SituacaoReducaoZero.NCM_NAO_RECONHECIDO


def test_consulta_indisponivel_nao_e_fora_do_anexo():
    """Dizer "este produto não tem redução" sem ter conseguido consultar é
    afirmação jurídica falsa emitida por omissão."""
    resolucao = resolver_item("MERCADORIA", "87131000", ConsultaReducaoZero(False))

    assert resolucao.situacao is SituacaoReducaoZero.CONSULTA_INDISPONIVEL
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
    assert "Falha ao consultar os Anexos de redução a zero" in caplog.text


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
