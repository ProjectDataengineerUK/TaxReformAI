import pytest

from motor_calculo.fases import FaseTransicao, fase_para


@pytest.mark.parametrize(
    "ano,fase_esperada",
    [
        (2026, FaseTransicao.TESTE_2026),
        (2027, FaseTransicao.PLENO_CBS_IS_2027),
        (2028, FaseTransicao.PLENO_CBS_IS_2027),
        (2029, FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032),
        (2030, FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032),
        (2031, FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032),
        (2032, FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032),
        (2033, FaseTransicao.REGIME_PLENO_2033),
        (2040, FaseTransicao.REGIME_PLENO_2033),
    ],
)
def test_fase_para_cobre_toda_a_linha_do_tempo(ano, fase_esperada):
    assert fase_para(ano) == fase_esperada


@pytest.mark.parametrize("ano", [2025, 2000, 1])
def test_fase_para_rejeita_ano_anterior_a_reforma(ano):
    with pytest.raises(ValueError, match="anterior ao início da reforma"):
        fase_para(ano)
