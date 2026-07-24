from enum import Enum


class FaseTransicao(Enum):
    TESTE_2026 = "TESTE_2026"
    PLENO_CBS_IS_2027 = "PLENO_CBS_IS_2027"
    TRANSICAO_ICMS_ISS_2029_2032 = "TRANSICAO_ICMS_ISS_2029_2032"
    REGIME_PLENO_2033 = "REGIME_PLENO_2033"


def fase_para(ano: int) -> FaseTransicao:
    if ano == 2026:
        return FaseTransicao.TESTE_2026
    if 2027 <= ano <= 2028:
        return FaseTransicao.PLENO_CBS_IS_2027
    if 2029 <= ano <= 2032:
        return FaseTransicao.TRANSICAO_ICMS_ISS_2029_2032
    if ano >= 2033:
        return FaseTransicao.REGIME_PLENO_2033
    raise ValueError(f"Ano {ano} anterior ao início da reforma tributária (2026)")
