"""Tabela e lookup do piso do art. 371/Anexo XVI — sem banco, sem HTTP."""

from decimal import Decimal

from motor_calculo.piso_aliquota_ibs import _TABELA_PISO, FONTE_LEGAL, piso_aliquota_ibs


def test_tabela_tem_49_anos_de_2029_a_2077():
    assert len(_TABELA_PISO) == 49
    assert min(_TABELA_PISO) == 2029
    assert max(_TABELA_PISO) == 2077


# AT-001 — início da janela -----------------------------------------------


def test_at001_ano_2029_e_o_inicio_da_janela():
    piso = piso_aliquota_ibs(2029)
    assert piso is not None
    assert piso.ano_operacao == 2029
    assert piso.limite_inferior_percentual == Decimal("81.0")
    assert piso.dispositivo_legal_ref == FONTE_LEGAL


# AT-002 — o único ano de salto ---------------------------------------------


def test_at002_ano_2033_e_o_unico_salto_para_cima():
    piso = piso_aliquota_ibs(2033)
    assert piso.limite_inferior_percentual == Decimal("90.5")
    # 2032 (fim do platô) e 2034 (início do declínio) confirmam que 2033 é
    # um pico isolado, não um erro de leitura monotônica.
    assert piso_aliquota_ibs(2032).limite_inferior_percentual == Decimal("81.0")
    assert piso_aliquota_ibs(2034).limite_inferior_percentual == Decimal("88.6")


# AT-003 — fim da janela -----------------------------------------------------


def test_at003_ano_2077_e_o_fim_da_janela():
    piso = piso_aliquota_ibs(2077)
    assert piso.limite_inferior_percentual == Decimal("6.9")


# AT-004 — antes da janela ---------------------------------------------------


def test_at004_ano_anterior_a_2029_nao_se_aplica():
    assert piso_aliquota_ibs(2026) is None
    assert piso_aliquota_ibs(2028) is None


# AT-005 — depois da janela --------------------------------------------------


def test_at005_ano_posterior_a_2077_nao_se_aplica():
    assert piso_aliquota_ibs(2078) is None
    assert piso_aliquota_ibs(3000) is None


# AT-008 — sem dependência de infraestrutura ---------------------------------


def test_at008_modulo_nao_importa_psycopg_nem_banco():
    import ast
    import inspect

    import motor_calculo.piso_aliquota_ibs as modulo

    arvore = ast.parse(inspect.getsource(modulo))
    importados = {
        alias.name
        for node in ast.walk(arvore)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(arvore)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("psycopg" in (nome or "") or nome == "db" for nome in importados)


def test_todos_os_valores_sao_decimal_de_1_casa():
    for ano, percentual in _TABELA_PISO.items():
        texto = str(percentual)
        casas = texto.split(".")[1] if "." in texto else ""
        assert len(casas) <= 1, f"ano {ano} tem mais de 1 casa decimal: {percentual}"
