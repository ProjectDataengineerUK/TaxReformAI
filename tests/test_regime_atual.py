"""Alíquotas do regime vigente (PIS/COFINS, ICMS interestadual/interno, ISS),
conferidas contra o texto oficial do Planalto/LexML/SEFAZ de cada estado —
nenhuma vem de memória.

Fontes lidas (2026-07-25):
  Lei 10.637/2002 (compilada), art. 2º — PIS não-cumulativo 1,65%
  Lei 10.833/2003 (compilada), art. 2º — COFINS não-cumulativo 7,6%
  Lei 9.715/1998, art. 8º, I — PIS cumulativo 0,65%
  Lei 9.718/1998, art. 8º — COFINS cumulativo 3%
  Resolução do Senado 22/1989, art. 1º — ICMS interestadual 12% / 7%
  Resolução do Senado 13/2012, art. 1º — ICMS interestadual bem importado 4%

Fontes lidas (2026-07-27) — ICMS interno (27 estados + DF) e ISS:
  RICMS/lei de cada UF (ver `fonte_legal` de cada entrada em
  `_TABELA_ICMS_INTERNO`) — verificação individual, sem agregador federal.
  Lei Complementar 116/2003, arts. 8º e 8º-A — piso/teto do ISS
"""

from decimal import Decimal

import pytest

from motor_calculo.regime_atual import (
    RegimeApuracao,
    TabelaPisCofins,
    icms_interestadual,
    icms_interno,
    iss_faixa,
)


def test_pis_cofins_nao_cumulativo():
    regra = TabelaPisCofins().buscar(RegimeApuracao.NAO_CUMULATIVO)

    assert regra.aliq_pis == Decimal("0.0165")
    assert regra.aliq_cofins == Decimal("0.076")
    assert "art. 2º" in regra.fonte_legal_pis
    assert "10.637" in regra.fonte_legal_pis
    assert "10.833" in regra.fonte_legal_cofins


def test_pis_cofins_cumulativo():
    regra = TabelaPisCofins().buscar(RegimeApuracao.CUMULATIVO)

    assert regra.aliq_pis == Decimal("0.0065")
    assert regra.aliq_cofins == Decimal("0.03")
    assert "9.715" in regra.fonte_legal_pis
    assert "9.718" in regra.fonte_legal_cofins


def test_soma_nao_cumulativo_bate_com_o_conhecido_do_mercado():
    """1,65% + 7,6% = 9,25%, a soma citada universalmente em material contábil
    — se isto quebrar, uma das duas leis foi lida errado."""
    regra = TabelaPisCofins().buscar(RegimeApuracao.NAO_CUMULATIVO)
    assert regra.aliq_pis + regra.aliq_cofins == Decimal("0.0925")


def test_icms_interestadual_regra_geral_doze_por_cento():
    """SP -> SP não é interestadual, mas SP -> BA (Sudeste -> Nordeste) cai na
    regra reduzida, não na geral. Uso SP -> RJ, os dois em Sudeste, sem
    destino beneficiado: cai na regra geral."""
    regra = icms_interestadual("SP", "RJ")

    assert regra.aliquota == Decimal("0.12")
    assert "22/1989" in regra.fonte_legal
    assert "art. 1º" in regra.fonte_legal


def test_icms_interestadual_sul_sudeste_para_norte_nordeste_centro_oeste():
    for origem in ("SP", "RS", "PR", "MG"):
        for destino in ("BA", "AM", "GO", "PE"):
            regra = icms_interestadual(origem, destino)
            assert regra.aliquota == Decimal("0.07"), f"{origem}->{destino}"
            assert "22/1989" in regra.fonte_legal


def test_icms_interestadual_es_como_destino_e_beneficiado_mesmo_sendo_sudeste():
    """A resolução original inclui ES como destino beneficiado apesar de ES
    ser Sudeste — não é erro nosso, é como o texto de 1989 está redigido."""
    regra = icms_interestadual("SP", "ES")
    assert regra.aliquota == Decimal("0.07")


def test_icms_interestadual_es_como_origem_segue_regra_de_sudeste():
    """ES como ORIGEM entra no grupo Sul/Sudeste normalmente."""
    regra = icms_interestadual("ES", "BA")
    assert regra.aliquota == Decimal("0.07")


def test_icms_interestadual_norte_para_sul_e_regra_geral():
    """A redução só vale no sentido Sul/Sudeste -> N/NE/CO/ES. No sentido
    inverso é a regra geral de 12%."""
    regra = icms_interestadual("AM", "SP")
    assert regra.aliquota == Decimal("0.12")


def test_icms_interestadual_bem_importado_e_quatro_por_cento():
    """Prevalece mesmo num par de UFs que cairia na regra de 7% — a Resolução
    13/2012 é norma mais específica."""
    regra = icms_interestadual("SP", "BA", bem_importado=True)

    assert regra.aliquota == Decimal("0.04")
    assert "13/2012" in regra.fonte_legal


@pytest.mark.parametrize("uf", ["sp", "Sp", "SP"])
def test_icms_interestadual_e_insensivel_a_caixa(uf):
    assert icms_interestadual(uf, "RJ").aliquota == Decimal("0.12")


# ICMS interno — alíquota geral/modal por UF -------------------------------

_ALIQUOTAS_ICMS_INTERNO_ESPERADAS = {
    "AC": Decimal("0.20"),
    "AL": Decimal("0.205"),
    "AP": Decimal("0.18"),
    "AM": Decimal("0.20"),
    "BA": Decimal("0.205"),
    "CE": Decimal("0.20"),
    "DF": Decimal("0.20"),
    "ES": Decimal("0.17"),
    "GO": Decimal("0.19"),
    "MA": Decimal("0.23"),
    "MT": Decimal("0.17"),
    "MS": Decimal("0.17"),
    "MG": Decimal("0.18"),
    "PA": Decimal("0.19"),
    "PB": Decimal("0.20"),
    "PR": Decimal("0.195"),
    "PE": Decimal("0.205"),
    "PI": Decimal("0.225"),
    "RJ": Decimal("0.20"),
    "RN": Decimal("0.20"),
    "RS": Decimal("0.17"),
    "RO": Decimal("0.195"),
    "RR": Decimal("0.20"),
    "SC": Decimal("0.17"),
    "SP": Decimal("0.18"),
    "SE": Decimal("0.19"),
    "TO": Decimal("0.20"),
}


def test_tabela_icms_interno_cobre_as_27_ufs_mais_df():
    """26 estados + DF = 27 chaves. Se uma UF faltar, silenciosamente
    `icms_interno` levantaria ValueError para ela — o teste pega isso aqui,
    não em produção."""
    assert set(_ALIQUOTAS_ICMS_INTERNO_ESPERADAS) == {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
        "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
        "RR", "SC", "SP", "SE", "TO",
    }
    assert len(_ALIQUOTAS_ICMS_INTERNO_ESPERADAS) == 27


@pytest.mark.parametrize("uf,esperado", list(_ALIQUOTAS_ICMS_INTERNO_ESPERADAS.items()))
def test_icms_interno_aliquota_geral_por_uf(uf, esperado):
    regra = icms_interno(uf)

    assert regra.aliquota == esperado, uf
    assert regra.fonte_legal, uf
    assert regra.uf == uf


def test_icms_interno_sao_paulo_cita_o_artigo_certo():
    regra = icms_interno("SP")

    assert "52" in regra.fonte_legal
    assert "45.490" in regra.fonte_legal


def test_icms_interno_rio_de_janeiro_tem_fecp_separado_do_icms():
    """FECP é um adicional com base legal própria (LC Estadual 210/2023),
    juridicamente distinto do ICMS — não pode ser somado silenciosamente
    dentro de `aliquota`, ou a citação ficaria errada."""
    regra = icms_interno("RJ")

    assert regra.aliquota == Decimal("0.20")
    assert regra.fecp == Decimal("0.02")
    assert "210/2023" in regra.fonte_legal_fecp


def test_icms_interno_sergipe_tem_fecp_de_um_por_cento():
    regra = icms_interno("SE")

    assert regra.aliquota == Decimal("0.19")
    assert regra.fecp == Decimal("0.01")


def test_icms_interno_estados_sem_fecp_tem_campo_none():
    regra = icms_interno("SP")

    assert regra.fecp is None
    assert regra.fonte_legal_fecp is None


@pytest.mark.parametrize("uf", ["sp", "Sp", "SP"])
def test_icms_interno_e_insensivel_a_caixa(uf):
    assert icms_interno(uf).aliquota == Decimal("0.18")


def test_icms_interno_uf_desconhecida_levanta_value_error():
    with pytest.raises(ValueError, match="UF desconhecida"):
        icms_interno("XX")


def test_icms_interno_ceara_e_pernambuco_citam_leis_de_mesmo_numero_por_coincidencia():
    """Os dois estados promulgaram, de fato, uma "Lei 18.305/2023" cada —
    confirmado independentemente contra fontes .gov.br dos dois SEFAZ antes
    de aceitar isso como não sendo erro de busca."""
    ce, pe = icms_interno("CE"), icms_interno("PE")

    assert "18.305/2023" in ce.fonte_legal
    assert "18.305/2023" in pe.fonte_legal
    assert ce.aliquota != pe.aliquota  # 20% vs 20,5% — leis distintas, coincidência só no número


# ISS — piso e teto federais (LC 116/2003), não a alíquota municipal exata -


def test_iss_faixa_piso_e_dois_por_cento():
    faixa = iss_faixa()

    assert faixa.piso == Decimal("0.02")
    assert "8º-A" in faixa.fonte_legal_piso
    assert "116/2003" in faixa.fonte_legal_piso


def test_iss_faixa_teto_e_cinco_por_cento():
    faixa = iss_faixa()

    assert faixa.teto == Decimal("0.05")
    assert "8º" in faixa.fonte_legal_teto
    assert "116/2003" in faixa.fonte_legal_teto


def test_iss_faixa_piso_e_menor_que_teto():
    faixa = iss_faixa()
    assert faixa.piso < faixa.teto
