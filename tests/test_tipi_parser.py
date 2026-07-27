"""Parser da TIPI (IPI por NCM). Os trechos de fixture são cópia literal do
texto extraído (`pdftotext -layout`) do PDF oficial da RFB em 2026-07-27, não
inventados — inclusive as quebras de linha reais que motivaram o parser.
"""

from decimal import Decimal

from db.tipi import parse_tipi

TRECHO_SIMPLES = """\
0104.10      - Ovinos
0104.10.1        Reprodutores de raça pura
0104.10.11         Prenhes ou com cria ao pé                                                         NT
0104.10.19         Outros                                                                            NT
0104.10.90       Outros                                                                              NT
0104.20      - Caprinos
0104.20.10       Reprodutores de raça pura                                                           NT
0104.20.90       Outros                                                                              NT
"""

TRECHO_COM_NUMERICO = """\
0305.41.00   -- Salmões-do-pacífico (Oncorhynchus nerka, Oncorhynchus gorbuscha, Oncorhynchus
               keta, Oncorhynchus tschawytscha, Oncorhynchus kisutch, Oncorhynchus masou e
               Oncorhynchus rhodurus), salmão-do-atlântico (Salmo salar) e salmão-do-danúbio
               (Hucho hucho)                                                                                 3,25
0305.42.00   -- Arenques (Clupea harengus, Clupea pallasii)                                                   3,25
0305.43.00   -- Trutas (Salmo trutta, Oncorhynchus mykiss, Oncorhynchus clarki, Oncorhynchus
               aguabonita, Oncorhynchus gilae, Oncorhynchus apache e Oncorhynchus chrysogaster)               0
"""

TRECHO_COM_WRAP_LONGO = """\
0106.11.00   -- Primatas                                                                             NT
0106.12.00   -- Baleias, golfinhos e botos (mamíferos da ordem Cetacea); peixes-boi (manatins) e
                 dugongos (mamíferos da ordem Sirenia); otárias e focas, leões-marinhos e morsas
                 (mamíferos da subordem Pinnipedia)                                                  NT
"""

TRECHO_COM_CABECALHOS_DE_CATEGORIA = """\
01.05        Aves da espécie Gallus domesticus, patos, gansos, perus, peruas e galinhas-d'angola
             (pintadas), das espécies domésticas, vivos.
0105.1       - De peso não superior a 185 g:
0105.11      -- Aves da espécie Gallus domesticus
0105.11.10       De linhas puras ou híbridas, para reprodução                                        NT
0105.11.90       Outros                                                                              NT
0105.12.00   -- Peruas e perus                                                                       NT
"""


def test_codigos_completos_com_nt_na_propria_linha():
    linhas = parse_tipi(TRECHO_SIMPLES)
    codigos = {item.ncm_code: item for item in linhas}

    assert set(codigos) == {"0104.10.11", "0104.10.19", "0104.10.90", "0104.20.10", "0104.20.90"}
    for linha in codigos.values():
        assert linha.nao_tributado is True
        assert linha.aliquota_percentual is None


def test_codigos_parciais_de_categoria_sao_ignorados():
    """"0104.10" (- Ovinos) e "0104.10.1" (Reprodutores de raça pura) são
    cabeçalhos de categoria, sem NCM completo nem alíquota própria — não
    devem virar registro."""
    linhas = parse_tipi(TRECHO_SIMPLES)
    codigos = {item.ncm_code for item in linhas}

    assert "0104.10" not in codigos
    assert "0104.10.1" not in codigos


def test_valor_numerico_e_convertido_para_fracao():
    """"3,25" (3,25%) vira Decimal("0.0325") — mesma convenção de
    regime_atual.py: fração, não percentual bruto."""
    linhas = {item.ncm_code: item for item in parse_tipi(TRECHO_COM_NUMERICO)}

    assert linhas["0305.42.00"].aliquota_percentual == Decimal("0.0325")
    assert linhas["0305.42.00"].nao_tributado is False


def test_aliquota_zero_explicita_e_diferente_de_nao_tributado():
    """"0" é uma alíquota real de 0%, distinta de "NT" — a norma faz essa
    distinção e o parser não pode apagá-la."""
    linhas = {item.ncm_code: item for item in parse_tipi(TRECHO_COM_NUMERICO)}

    assert linhas["0305.43.00"].aliquota_percentual == Decimal(0)
    assert linhas["0305.43.00"].nao_tributado is False


def test_descricao_multilinha_reconstituida_sem_o_valor_embutido():
    linhas = {item.ncm_code: item for item in parse_tipi(TRECHO_COM_NUMERICO)}

    descricao = linhas["0305.41.00"].descricao
    assert "Salmões-do-pacífico" in descricao
    assert "Hucho hucho" in descricao
    assert "3,25" not in descricao, "o valor da alíquota vazou para dentro da descrição"


def test_wrap_de_tres_linhas_ainda_encontra_o_valor():
    """O caso real que motivou o parser: descrição quebrando em até 10 linhas
    no documento oficial, com o valor só na última."""
    linhas = {item.ncm_code: item for item in parse_tipi(TRECHO_COM_WRAP_LONGO)}

    assert linhas["0106.12.00"].nao_tributado is True
    assert "Sirenia" in linhas["0106.12.00"].descricao


def test_titulo_de_secao_no_meio_do_texto_nao_quebra_o_parser():
    linhas = {item.ncm_code: item for item in parse_tipi(TRECHO_COM_CABECALHOS_DE_CATEGORIA)}

    assert set(linhas) == {"0105.11.10", "0105.11.90", "0105.12.00"}
    assert "01.05" not in linhas
    assert "0105.1" not in linhas
    assert "0105.11" not in linhas


def test_texto_vazio_devolve_lista_vazia():
    assert parse_tipi("") == []


def test_texto_sem_nenhum_ncm_devolve_lista_vazia():
    assert parse_tipi("TABELA DE INCIDÊNCIA DO IMPOSTO\n\nSUMÁRIO\n") == []
