"""Lógica pura da Cesta Básica (Anexo I) — sem banco, sem HTTP.

O seed dos 26 itens é **lido da própria migração 005**, não redigitado aqui: o
Anexo I é dado legal transcrito à mão de uma tabela do DOU, e uma segunda cópia
em Python seria uma segunda fonte de verdade capaz de divergir em silêncio da
que o banco de produção carrega. Assim, estes testes exercitam os 95 prefixos
reais (76 inclusões + 19 exceções) sem precisar de PostgreSQL — o SQL de verdade
é `test_cesta_basica_db.py`.
"""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from api.cesta_basica import (
    ConsultaCestaBasica,
    SituacaoCestaBasica,
    consultar_com_seguranca,
    resolver_item,
)
from api.ncm import digitos_ncm, prefixos_ncm
from db.repositorio import PrefixoCestaBasica
from motor_calculo.engine import ResultadoCalculo
from motor_calculo.reducoes import aplicar_reducao_a_zero

MIGRACAO = Path(__file__).resolve().parents[1] / "db" / "migrations" / (
    "005_cesta_basica_anexo_i.sql"
)

_LINHA_NCM = re.compile(
    r"\((\d+),\s*'(\d+)',\s*(TRUE|FALSE),\s*(NULL|'[a-d]'),\s*'([\d.]+)'\)"
)
_LINHA_ITEM = re.compile(r"\((\d+),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)'\)")


def _carregar_seed() -> list[PrefixoCestaBasica]:
    sql = MIGRACAO.read_text(encoding="utf-8")
    bloco_itens = sql.split("INSERT INTO cesta_basica_anexo_i ")[1].split(
        "ON CONFLICT"
    )[0]
    itens = {
        int(m[1]): (m[2].replace("''", "'"), m[3])
        for m in _LINHA_ITEM.finditer(bloco_itens)
    }

    bloco_ncm = sql.split("INSERT INTO cesta_basica_anexo_i_ncm")[1].split(
        "ON CONFLICT"
    )[0]
    linhas = []
    for item, prefixo, excecao, alinea, texto in _LINHA_NCM.findall(bloco_ncm):
        descricao, dispositivo = itens[int(item)]
        linhas.append(
            PrefixoCestaBasica(
                item=int(item),
                prefixo=prefixo,
                excecao=excecao == "TRUE",
                texto_ncm=texto,
                alinea=None if alinea == "NULL" else alinea.strip("'"),
                descricao=descricao,
                dispositivo_legal_ref=dispositivo,
            )
        )
    return linhas


SEED = _carregar_seed()
INCLUSOES = [linha for linha in SEED if not linha.excecao]
EXCECOES = [linha for linha in SEED if linha.excecao]


def _consulta(codigo: str) -> ConsultaCestaBasica:
    """Só as linhas que o `= ANY(%s)` devolveria para este código — é assim que
    o lote chega do banco, e não a tabela inteira."""
    candidatos = set(prefixos_ncm(codigo))
    return ConsultaCestaBasica(
        disponivel=True, linhas=[linha for linha in SEED if linha.prefixo in candidatos]
    )


def _resolver(codigo: str, natureza: str = "MERCADORIA"):
    return resolver_item(natureza, codigo, _consulta(codigo))


# Integridade do seed — as contagens de fechamento do DESIGN ------------------


def test_seed_tem_26_itens_76_inclusoes_e_19_excecoes():
    """Contagem é teste de truncamento: uma migração cortada pela metade passa
    em toda constraint e falha aqui."""
    assert len({linha.item for linha in SEED}) == 26
    assert len(SEED) == 95
    assert len(INCLUSOES) == 76
    assert len(EXCECOES) == 19


def test_comprimentos_de_prefixo_ficam_na_faixa_que_prefixos_ncm_enxerga():
    """Acoplamento explícito com `_COMPRIMENTOS_PREFIXO` e com a CHECK
    `prefixo_comprimento_valido`: um prefixo fora de 4..8 nunca casaria com
    nada — falso negativo permanente e mudo."""
    comprimentos = {len(linha.prefixo) for linha in SEED}

    assert comprimentos == {4, 5, 6, 7, 8}


def test_nenhuma_duplicata_de_item_prefixo_excecao():
    contagem = Counter((linha.item, linha.prefixo, linha.excecao) for linha in SEED)

    assert [chave for chave, n in contagem.items() if n > 1] == []


def test_unico_prefixo_compartilhado_entre_itens_e_o_das_formulas():
    """Se aparecer um segundo, a regra de desempate da Decisão 4 passa a valer
    para um caso que ninguém examinou."""
    por_prefixo: dict[str, set[int]] = {}
    for linha in SEED:
        por_prefixo.setdefault(linha.prefixo, set()).add(linha.item)

    assert {p: sorted(i) for p, i in por_prefixo.items() if len(i) > 1} == {
        "21069090": [4, 26]
    }


def test_toda_excecao_desce_de_uma_inclusao_do_mesmo_item():
    """Invariante do Anexo: uma exceção órfã produziria
    EXCLUIDA_EXPRESSAMENTE para um código que o item jamais incluiu — ou seja,
    citaria um item que nada tem a ver com a mercadoria."""
    orfas = [
        excecao
        for excecao in EXCECOES
        if not any(
            inclusao.item == excecao.item and excecao.prefixo.startswith(inclusao.prefixo)
            for inclusao in INCLUSOES
        )
    ]

    assert orfas == []


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


def test_prefixos_ncm_gera_exatamente_os_cinco_niveis_da_hierarquia():
    assert prefixos_ncm("02074300") == [
        "0207",
        "02074",
        "020743",
        "0207430",
        "02074300",
    ]


def test_normalizar_ncm_do_ipi_continua_delegando_sem_mudar_comportamento():
    """A Decisão 10 refatora `api/ipi.py::normalizar_ncm` para cima de
    `digitos_ncm` — `tests/test_ipi_resolucao.py` prova o comportamento; aqui
    fica registrado que as duas features enxergam o MESMO conjunto de códigos
    válidos, que é o ponto da decisão."""
    from api.ipi import normalizar_ncm

    for bruto in ("22030000", "2203.00.00", "2203", "", "lixo"):
        assert (normalizar_ncm(bruto) is None) == (digitos_ncm(bruto) is None)


# AT-001 — correspondência exata ---------------------------------------------


def test_at001_manteiga_casa_o_item_5_por_codigo_de_8_digitos():
    resolucao = _resolver("04051000")

    assert resolucao.situacao is SituacaoCestaBasica.APLICADA
    assert resolucao.item == 5
    assert resolucao.dispositivo_legal_ref == "LCP 214/2025, art. 125, Anexo I, item 5"
    assert resolucao.texto_ncm == "0405.10.00"
    assert resolucao.tipo_correspondencia == "EXATO"
    assert resolucao.itens_correspondentes == (5,)


def test_todas_as_76_inclusoes_do_anexo_resolvem_aplicada():
    """Cobre os 26 itens de uma vez, incluindo os 6 de correspondência
    não-trivial (1, 8, 15, 19, 20, 23): cada prefixo, completado com zeros até
    8 dígitos, precisa cair no próprio item. `in itens_correspondentes` em vez
    de `== item` por causa da sobreposição 4/26, onde o desempate escolhe um."""
    for inclusao in INCLUSOES:
        codigo = inclusao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoCestaBasica.APLICADA, (
            f"{inclusao.texto_ncm} (item {inclusao.item}) não resolveu: "
            f"{resolucao.situacao}"
        )
        assert inclusao.item in resolucao.itens_correspondentes


# AT-003 — prefixo puro ------------------------------------------------------


@pytest.mark.parametrize(
    ("codigo", "item", "texto"),
    [
        ("09012100", 8, "09.01"),  # café em grão — posição de 4 dígitos
        ("21011100", 8, "2101.1"),  # extratos de café — subposição de 5
        ("09032000", 23, "09.03"),  # mate — posição de 4
        ("10062010", 1, "1006.20"),  # arroz descascado — subposição de 6
        ("19021100", 15, "1902.1"),  # massas com ovos — subposição de 5
    ],
)
def test_at003_prefixo_puro_resolve_com_a_grafia_literal_da_lei(codigo, item, texto):
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoCestaBasica.APLICADA
    assert resolucao.item == item
    assert resolucao.tipo_correspondencia == "PREFIXO"
    # "casou com a posição 02.07" é auditável; "casou com 0207" não é a grafia
    # que o DOU publicou.
    assert resolucao.texto_ncm == texto


def test_prefixo_de_7_digitos_do_item_19_resolve():
    """`0210.99.1` é o único prefixo de 7 dígitos do Anexo I — comprimento que
    não aparece em nenhum outro lugar do projeto."""
    resolucao = _resolver("02109911")

    assert resolucao.situacao is SituacaoCestaBasica.APLICADA
    assert resolucao.item == 19
    assert resolucao.texto_ncm == "0210.99.1"


# AT-004 — exceções escopadas ao item ----------------------------------------


@pytest.mark.parametrize(
    ("codigo", "item", "texto"),
    [
        ("02074300", 19, "0207.43.00"),  # foie gras de ganso
        ("02075300", 19, "0207.53.00"),  # foie gras de pato
        ("03021100", 20, "0302.1"),  # salmonídeos frescos
        ("03023100", 20, "0302.3"),  # atuns frescos
        ("03025100", 20, "0302.51.00"),  # bacalhau fresco
        ("03031100", 20, "0303.1"),  # salmonídeos congelados
        ("03044100", 20, "0304.4"),  # filés de salmonídeos
    ],
)
def test_at004_codigo_excluido_pelo_proprio_item_nunca_recebe_zero(codigo, item, texto):
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoCestaBasica.EXCLUIDA_EXPRESSAMENTE
    assert resolucao.aplicada is False, "exceção do Anexo jamais vira alíquota zero"
    assert resolucao.item == item
    assert resolucao.texto_ncm == texto
    assert resolucao.tipo_correspondencia == "EXCECAO"


def test_todas_as_19_excecoes_do_anexo_bloqueiam_a_reducao():
    for excecao in EXCECOES:
        codigo = excecao.prefixo.ljust(8, "0")
        resolucao = _resolver(codigo)

        assert resolucao.situacao is SituacaoCestaBasica.EXCLUIDA_EXPRESSAMENTE, (
            f"{excecao.texto_ncm} (item {excecao.item}) deveria estar excluído"
        )


def test_excluida_e_distinta_de_fora_do_anexo():
    """A resposta mais valiosa da feature: "está na posição 02.07, mas o Anexo
    exclui expressamente o 0207.43.00" é informação jurídica que o cliente não
    obteria de outro jeito, e é o oposto de "não está no Anexo"."""
    excluido = _resolver("02074300")
    fora = _resolver("22030000")

    assert excluido.situacao is not fora.situacao
    assert excluido.item == 19 and excluido.dispositivo_legal_ref is not None
    assert fora.item is None and fora.dispositivo_legal_ref is None


def test_excecao_de_um_item_nao_afeta_a_inclusao_de_outro():
    """A exclusão qualifica o item onde a lei a escreveu (Decisão 3). Hoje as
    listas dos itens 19 e 20 são disjuntas, então os dois modelos dariam a mesma
    resposta — este teste é o que trava a diferença antes de outro Anexo entrar."""
    consulta = ConsultaCestaBasica(
        disponivel=True,
        linhas=[
            PrefixoCestaBasica(19, "0207", False, "02.07", "d", "carnes", "art. 125/19"),
            # Exceção de OUTRO item, com o mesmo prefixo do código consultado.
            PrefixoCestaBasica(20, "02074300", True, "0207.43.00", "a", "peixes", "art. 125/20"),
        ],
    )

    resolucao = resolver_item("MERCADORIA", "02074300", consulta)

    assert resolucao.situacao is SituacaoCestaBasica.APLICADA
    assert resolucao.item == 19


# AT-005 — vizinhança de prefixo ---------------------------------------------


@pytest.mark.parametrize(
    "codigo",
    [
        "10061010",  # arroz com casca: dentro de 1006, fora de 1006.20/30/40.00
        "10064010",  # 1006.40.10 não existe no Anexo (só o 1006.40.00 exato)
        "22030000",  # cerveja — o NCM do smoke test atual
        "01022110",  # bovino vivo (o NT da TIPI): capítulo 01, não 02
        "09024000",  # chá: posição 09.02, vizinha de 09.01 e 09.03
        "21069010",  # 2106.90.10: irmão do 2106.90.90 dos itens 4/26
    ],
)
def test_at005_vizinho_de_prefixo_nao_recebe_reducao(codigo):
    """Prova que o match respeita os limites reais da posição/subposição e não é
    "contém a substring"."""
    resolucao = _resolver(codigo)

    assert resolucao.situacao is SituacaoCestaBasica.FORA_DO_ANEXO
    assert resolucao.aplicada is False


# Sobreposições entre itens (Decisão 4) --------------------------------------


def test_sobreposicao_15_e_25_cita_o_item_mais_especifico():
    """`1902.19.00` (item 25, massas para aminoacidopatias) está dentro de
    `1902.1` (item 15, massas em geral). Vence o prefixo mais longo, porque
    descreve melhor o produto."""
    resolucao = _resolver("19021900")

    assert resolucao.item == 25
    assert resolucao.itens_correspondentes == (15, 25)
    assert resolucao.texto_ncm == "1902.19.00"


def test_sobreposicao_4_e_26_empata_no_comprimento_e_cita_o_menor_item():
    """Os dois citam `2106.90.90` com 8 dígitos — o desempate cai no segundo
    critério. Sem ordenação total, a resposta variaria com a ordem em que o
    Postgres devolveu as linhas."""
    resolucao = _resolver("21069090")

    assert resolucao.item == 4
    assert resolucao.itens_correspondentes == (4, 26)


def test_desempate_independe_da_ordem_das_linhas_do_banco():
    linhas = _consulta("21069090").linhas

    direta = resolver_item(
        "MERCADORIA", "21069090", ConsultaCestaBasica(True, list(linhas))
    )
    invertida = resolver_item(
        "MERCADORIA", "21069090", ConsultaCestaBasica(True, list(reversed(linhas)))
    )

    assert direta == invertida


# Situações restantes do enum ------------------------------------------------


def test_servico_e_nao_aplicavel_sem_sequer_olhar_o_ncm():
    resolucao = resolver_item("SERVICO", "04051000", _consulta("04051000"))

    assert resolucao.situacao is SituacaoCestaBasica.NAO_APLICAVEL
    assert resolucao.item is None


@pytest.mark.parametrize("consulta", [ConsultaCestaBasica(True), ConsultaCestaBasica(False)])
def test_ncm_ilegivel_e_propriedade_do_payload_nao_do_banco(consulta):
    """A guarda de formato vem ANTES da de disponibilidade: `0405` é subposição,
    nenhum Anexo o conteria, e CONSULTA_INDISPONIVEL mandaria o cliente
    reprocessar algo que jamais mudaria de resposta (lição da feature 1)."""
    resolucao = resolver_item("MERCADORIA", "0405", consulta)

    assert resolucao.situacao is SituacaoCestaBasica.NCM_NAO_RECONHECIDO


def test_consulta_indisponivel_nao_e_fora_do_anexo():
    """Dizer "este produto não está na cesta básica" sem ter conseguido
    consultar é afirmação jurídica falsa emitida por omissão."""
    resolucao = resolver_item("MERCADORIA", "04051000", ConsultaCestaBasica(False))

    assert resolucao.situacao is SituacaoCestaBasica.CONSULTA_INDISPONIVEL
    assert resolucao.avaliada is False


def test_fora_do_anexo_e_servico_contam_como_avaliados():
    """Decisão 9: só "não sei" impede o total dispensado; "sei que não tem
    benefício" não."""
    assert _resolver("22030000").avaliada is True
    assert _resolver("04051000", natureza="SERVICO").avaliada is True
    assert _resolver("02074300").avaliada is True


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
    pool = PoolFalso(ConnectionError("Cloud SQL fora do ar (simulado)"))

    consulta = consultar_com_seguranca(pool, ["04051000"])

    assert consulta.disponivel is False
    assert "Falha ao consultar a Cesta Básica" in caplog.text


# motor_calculo/reducoes.py --------------------------------------------------


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
    """O art. 125 reduz a zero as alíquotas "do IBS e da CBS" — e só. O IS tem
    lista própria (Anexo XVII), fora do escopo: zerá-lo seria inventar um
    benefício que a lei não deu."""
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
