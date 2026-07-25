"""Alíquotas do regime vigente (PIS/COFINS, ICMS interestadual), conferidas
contra o texto oficial do Planalto/LexML — nenhuma vem de memória.

Fontes lidas (2026-07-25):
  Lei 10.637/2002 (compilada), art. 2º — PIS não-cumulativo 1,65%
  Lei 10.833/2003 (compilada), art. 2º — COFINS não-cumulativo 7,6%
  Lei 9.715/1998, art. 8º, I — PIS cumulativo 0,65%
  Lei 9.718/1998, art. 8º — COFINS cumulativo 3%
  Resolução do Senado 22/1989, art. 1º — ICMS interestadual 12% / 7%
  Resolução do Senado 13/2012, art. 1º — ICMS interestadual bem importado 4%
"""

from decimal import Decimal

import pytest

from motor_calculo.regime_atual import (
    RegimeApuracao,
    TabelaPisCofins,
    icms_interestadual,
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
