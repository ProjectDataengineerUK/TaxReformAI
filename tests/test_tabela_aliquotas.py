from decimal import Decimal

import pytest

from motor_calculo.fases import FaseTransicao
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from motor_calculo.tabela_aliquotas import TabelaAliquotasSeed


def test_2026_retorna_regra_confirmada_com_fonte_legal():
    tabela = TabelaAliquotasSeed()
    regra = tabela.buscar(FaseTransicao.TESTE_2026)

    assert regra.aliq_cbs == Decimal("0.009")
    assert regra.aliq_ibs == Decimal("0.001")
    assert regra.aliq_is == Decimal(0)
    assert regra.confirmado_em_lei is True
    assert regra.fonte_legal


def test_2026_cita_os_artigos_que_fixam_cada_aliquota():
    """A fundamentação vai para a tela do usuário. "Linha do tempo da
    transição" não é fonte auditável; "LCP 214/2025, art. 346" é."""
    regra = TabelaAliquotasSeed().buscar(FaseTransicao.TESTE_2026)

    assert "art. 346" in regra.fontes_por_tributo["CBS"]
    assert "art. 343" in regra.fontes_por_tributo["IBS"]
    assert "343" in regra.fonte_legal and "346" in regra.fonte_legal


def test_2027_tem_ibs_fixado_em_lei_e_cbs_pendente():
    """O caso que motivou permitir alíquota `None`: o art. 344 fixa o IBS de
    2027-2028, enquanto o art. 347 deixa a CBS dependente de uma alíquota de
    referência ainda não fixada. Descartar o IBS conhecido seria perder fato
    jurídico real; inventar a CBS seria pior."""
    regra = TabelaAliquotasSeed().buscar(FaseTransicao.PLENO_CBS_IS_2027)

    assert regra.aliq_ibs == Decimal("0.001"), "0,05% estadual + 0,05% municipal"
    assert regra.aliq_cbs is None
    assert regra.aliq_is is None
    assert regra.confirmado_em_lei is False
    assert regra.tributos_indisponiveis() == ["CBS", "IS"]
    assert "art. 344" in regra.fontes_por_tributo["IBS"]
    assert "art. 347" in regra.fontes_por_tributo["CBS"]


@pytest.mark.parametrize(
    "fase",
    [
        FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032,
        FaseTransicao.REGIME_PLENO_2033,
    ],
)
def test_fases_de_2029_em_diante_nem_existem_na_tabela(fase):
    """De 2029 em diante a própria LCP 214/2025 remete a alíquotas de
    referência a fixar (arts. 353 a 369) — não há número a registrar."""
    tabela = TabelaAliquotasSeed()
    with pytest.raises(AliquotaNaoDisponivelError) as exc_info:
        tabela.buscar(fase)
    assert fase.value in str(exc_info.value)
    assert exc_info.value.fase == fase


def test_erro_de_fase_parcial_diz_o_que_falta_e_o_que_ja_se_sabe():
    regra = TabelaAliquotasSeed().buscar(FaseTransicao.PLENO_CBS_IS_2027)
    erro = AliquotaNaoDisponivelError(
        regra.fase, tributos=regra.tributos_indisponiveis(), regra=regra
    )
    mensagem = str(erro)

    assert "CBS, IS" in mensagem
    assert "art. 347" in mensagem, "precisa dizer qual dispositivo rege o que falta"
    assert "IBS=0.001" in mensagem, "e o que já está fixado, para não parecer ignorância total"
    assert erro.tributos == ["CBS", "IS"]
