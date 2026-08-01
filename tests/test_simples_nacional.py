from decimal import Decimal

import pytest

from motor_calculo.simples_nacional import (
    Atividade,
    calcular_aliquota_efetiva,
    calcular_mei,
    calcular_percentual_por_tributo,
    calcular_simples_nacional,
)


def test_aliquota_efetiva_formula_art_18():
    # LC 123/2006, art. 18, §1º-A: (RBT12 x Aliq - PD) / RBT12.
    resultado = calcular_aliquota_efetiva(
        Decimal(360000), Decimal("0.073"), Decimal("5940.00")
    )
    esperado = (Decimal(360000) * Decimal("0.073") - Decimal("5940.00")) / Decimal(360000)
    assert resultado == esperado


def test_percentual_por_tributo_formula_art_18():
    # LC 123/2006, art. 18, §1º-B: percentual efetivo = aliquota efetiva x
    # percentual de repartição.
    resultado = calcular_percentual_por_tributo(Decimal("0.05"), Decimal("0.1533"))
    assert resultado == Decimal("0.05") * Decimal("0.1533")


class TestComercioAnexoXVIII:
    def test_primeira_faixa_2027(self):
        r = calcular_simples_nacional(
            Atividade.COMERCIO, Decimal(150000), Decimal(12500), 2027
        )
        assert r.faixa == 1
        assert r.aliquota_nominal == Decimal("0.04")
        assert r.valor_deduzir == Decimal("0.00")
        assert r.partilha_percentual["CBS"] == r.aliquota_efetiva * Decimal("0.1533")
        assert r.partilha_percentual["IBS"] == r.aliquota_efetiva * Decimal("0.0017")
        assert r.icms_iss_fora_do_das is False
        assert "Anexo XVIII" in r.dispositivo_legal_ref
        assert "1ª Faixa" in r.dispositivo_legal_ref

    def test_regime_permanente_2033_e_2050_identicos(self):
        r33 = calcular_simples_nacional(
            Atividade.COMERCIO, Decimal(150000), Decimal(10000), 2033
        )
        r50 = calcular_simples_nacional(
            Atividade.COMERCIO, Decimal(150000), Decimal(10000), 2050
        )
        assert r33.partilha_percentual == r50.partilha_percentual
        assert "ICMS" not in r33.partilha_percentual
        assert r33.partilha_percentual["IBS"] == r33.aliquota_efetiva * Decimal("0.34")

    def test_sexta_faixa_icms_iss_fora_do_das(self):
        r = calcular_simples_nacional(
            Atividade.COMERCIO, Decimal(4000000), Decimal(300000), 2027
        )
        assert r.faixa == 6
        assert r.icms_iss_fora_do_das is True
        assert "ICMS" not in r.partilha_percentual
        assert "IBS" not in r.partilha_percentual
        assert set(r.partilha_percentual) == {"IRPJ", "CSLL", "CBS", "CPP"}

    def test_receita_acima_do_teto_do_simples_levanta_erro(self):
        with pytest.raises(ValueError, match="excede o teto"):
            calcular_simples_nacional(
                Atividade.COMERCIO, Decimal("4800000.01"), Decimal(100000), 2027
            )


class TestIndustriaAnexoXIX:
    def test_tem_coluna_ipi(self):
        r = calcular_simples_nacional(
            Atividade.INDUSTRIA, Decimal(500000), Decimal(40000), 2027
        )
        assert r.faixa == 3
        assert "IPI" in r.partilha_percentual
        assert r.partilha_percentual["IPI"] == r.aliquota_efetiva * Decimal("0.075")

    def test_2033_ibs_absorve_icms_mantem_ipi(self):
        r = calcular_simples_nacional(
            Atividade.INDUSTRIA, Decimal(500000), Decimal(40000), 2033
        )
        assert "ICMS" not in r.partilha_percentual
        assert r.partilha_percentual["IBS"] == r.aliquota_efetiva * Decimal("0.32")
        assert r.partilha_percentual["IPI"] == r.aliquota_efetiva * Decimal("0.075")


class TestLocacaoServicoGeralAnexoXX:
    def test_teto_iss_acionado(self):
        # 5a Faixa, RBT12 no teto superior: aliquota efetiva > 14,92537%.
        r = calcular_simples_nacional(
            Atividade.LOCACAO_SERVICO_GERAL, Decimal(3600000), Decimal(300000), 2027
        )
        assert r.faixa == 5
        assert r.aliquota_efetiva > Decimal("0.1492537")
        assert r.teto_iss_aplicado is True
        assert r.partilha_percentual["ISS"] == Decimal("0.05")
        excedente = r.aliquota_efetiva - Decimal("0.05")
        assert r.partilha_percentual["IRPJ"] == excedente * Decimal("0.0602")
        assert r.partilha_percentual["CPP"] == excedente * Decimal("0.6526")
        assert r.partilha_percentual["IBS"] == excedente * Decimal("0.0026")

    def test_teto_iss_nao_acionado(self):
        # 5a Faixa, RBT12 baixo: aliquota efetiva abaixo do gatilho.
        r = calcular_simples_nacional(
            Atividade.LOCACAO_SERVICO_GERAL, Decimal("1800000.01"), Decimal(50000), 2027
        )
        assert r.faixa == 5
        assert r.aliquota_efetiva < Decimal("0.1492537")
        assert r.teto_iss_aplicado is False
        assert r.partilha_percentual["ISS"] == r.aliquota_efetiva * Decimal("0.335")

    def test_coeficientes_de_teto_mudam_por_ano(self):
        r2027 = calcular_simples_nacional(
            Atividade.LOCACAO_SERVICO_GERAL, Decimal(3600000), Decimal(300000), 2027
        )
        r2032 = calcular_simples_nacional(
            Atividade.LOCACAO_SERVICO_GERAL, Decimal(3600000), Decimal(300000), 2032
        )
        assert r2027.partilha_percentual["ISS"] != r2032.partilha_percentual["ISS"]
        assert r2027.partilha_percentual["IBS"] != r2032.partilha_percentual["IBS"]


class TestServicoPar5cAnexoXXI:
    def test_nunca_tem_cpp(self):
        for ano in (2027, 2029, 2030, 2031, 2032, 2033):
            r = calcular_simples_nacional(
                Atividade.SERVICO_PAR_5C, Decimal(150000), Decimal(10000), ano
            )
            assert "CPP" not in r.partilha_percentual
            assert "CPP" not in r.valores_devidos

    def test_teto_iss_acionado_gatilho_proprio(self):
        # Gatilho do Anexo XXI e 12,5% (diferente do Anexo XX, 14,92537%).
        r = calcular_simples_nacional(
            Atividade.SERVICO_PAR_5C, Decimal(3600000), Decimal(300000), 2029
        )
        assert r.faixa == 5
        assert r.aliquota_efetiva > Decimal("0.125")
        assert r.teto_iss_aplicado is True
        assert r.partilha_percentual["ISS"] == Decimal("0.045")
        assert "CPP" not in r.partilha_percentual
        excedente = r.aliquota_efetiva - Decimal("0.045")
        assert r.partilha_percentual["IRPJ"] == excedente * Decimal("0.2938")
        assert r.partilha_percentual["CSLL"] == excedente * Decimal("0.30")
        assert r.partilha_percentual["CBS"] == excedente * Decimal("0.3438")
        assert r.partilha_percentual["IBS"] == excedente * Decimal("0.0625")


class TestServicoPar5iAnexoXXII:
    def test_sem_clausula_de_teto(self):
        r = calcular_simples_nacional(
            Atividade.SERVICO_PAR_5I, Decimal(3600000), Decimal(300000), 2027
        )
        assert r.faixa == 5
        assert r.teto_iss_aplicado is False
        assert set(r.partilha_percentual) == {"IRPJ", "CSLL", "CBS", "CPP", "ISS", "IBS"}


class TestMei:
    def test_valores_fixos_nao_variam_com_receita(self):
        r1 = calcular_mei(Decimal(1), 2029)
        r2 = calcular_mei(Decimal(999999), 2029)
        assert r1.valores_devidos == r2.valores_devidos

    def test_2027_2028(self):
        r = calcular_mei(Decimal(1), 2027)
        assert r.valores_devidos == {
            "CBS": Decimal("0.994"),
            "IBS": Decimal("0.006"),
            "ICMS": Decimal("1.00"),
            "ISS": Decimal("5.00"),
        }
        assert r.faixa is None
        assert r.aliquota_efetiva is None

    def test_2033_sem_icms_iss(self):
        r = calcular_mei(Decimal(1), 2033)
        assert r.valores_devidos == {"CBS": Decimal("1.00"), "IBS": Decimal("2.00")}
        assert "ICMS" not in r.valores_devidos
        assert "ISS" not in r.valores_devidos

    def test_via_dispatch_publico(self):
        r = calcular_simples_nacional(Atividade.MEI, None, Decimal(1), 2029)
        assert r.atividade is Atividade.MEI
        assert r.valores_devidos["CBS"] == Decimal("1.00")


def test_rbt12_obrigatoria_fora_do_mei():
    with pytest.raises(ValueError, match="receita_bruta_acumulada_12_meses"):
        calcular_simples_nacional(Atividade.COMERCIO, None, Decimal(10000), 2027)
