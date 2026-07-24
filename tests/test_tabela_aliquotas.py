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
    assert regra.aliq_is == Decimal("0")
    assert regra.confirmado_em_lei is True
    assert regra.fonte_legal


@pytest.mark.parametrize(
    "fase",
    [
        FaseTransicao.PLENO_CBS_IS_2027,
        FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032,
        FaseTransicao.REGIME_PLENO_2033,
    ],
)
def test_fases_sem_alíquota_confirmada_levantam_erro_explicito(fase):
    tabela = TabelaAliquotasSeed()
    with pytest.raises(AliquotaNaoDisponivelError) as exc_info:
        tabela.buscar(fase)
    assert fase.value in str(exc_info.value)
    assert exc_info.value.fase == fase
