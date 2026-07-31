"""Canonização e prefixos do vocabulário NBS — sem banco, sem HTTP."""

from api.nbs import digitos_nbs, prefixos_nbs


def test_codigo_completo_canoniza_para_9_digitos():
    assert digitos_nbs("1.2202.00.00") == "122020000"


def test_pontuacao_nao_muda_o_resultado():
    assert digitos_nbs("1.2202.00.00") == digitos_nbs("122020000")


def test_rejeita_codigo_com_8_digitos_grafia_ncm():
    """"04051000" é um NCM real, não um NBS — a canonização recusa, nunca
    devolve um valor que pareça válido para os dois vocabulários."""
    assert digitos_nbs("04051000") is None


def test_rejeita_classificador_de_topo_diferente_de_1():
    """Assunção A-002 do /define — todo código observado começa com "1". A
    canonização recusa qualquer outro valor em vez de aceitar silenciosamente."""
    assert digitos_nbs("2.2202.00.00") is None


def test_rejeita_vazio_e_none():
    assert digitos_nbs("") is None
    assert digitos_nbs(None) is None


def test_rejeita_comprimento_diferente_de_9():
    assert digitos_nbs("1.220.00.00") is None  # 8 dígitos
    assert digitos_nbs("1.22020.00.00") is None  # 10 dígitos


def test_prefixos_do_codigo_completo_sao_os_quatro_comprimentos_aceitos():
    assert prefixos_nbs("122020000") == ["12202", "122020", "1220200", "122020000"]


def test_prefixo_truncado_de_1_digito_da_subposicao_e_alcancavel():
    """Anexo II, item 1: "1.2201.1" — 6 dígitos, truncamento parcial dentro da
    subposição. Um código completo cujo prefixo de 6 dígitos bate com essa
    linha precisa aparecer entre os candidatos."""
    codigo = digitos_nbs("1.2201.15.00")
    assert codigo is not None
    assert "122011" in prefixos_nbs(codigo)
