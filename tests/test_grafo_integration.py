from decimal import Decimal

import pytest

from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.estado import State
from orquestracao.executor import executar_consulta
from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal


def test_at001_happy_path_grafo_completo():
    state = State(
        texto_consulta="Simular CBS/IBS para venda de eletrônicos em 2026",
        ano_operacao=2026,
        valor_base=Decimal("2500.00"),
    )

    state = executar_consulta(state)

    assert state.resultado_calculo is not None
    assert state.resultado_calculo.valor_liquido == Decimal("2475.00")
    assert state.parecer_final is not None
    assert [t.no for t in state.historico] == [
        "classificador",
        "pesquisador_legal",
        "extrator_regras",
        "deterministico",
        "sintetizador",
    ]


def test_at002_ano_sem_aliquota_confirmada_interrompe_sem_parecer_inventado():
    state = State(
        texto_consulta="Simular para 2028",
        ano_operacao=2028,
        valor_base=Decimal("1000.00"),
    )

    state = no_classificador(state)
    state = no_pesquisador_legal(state)
    state = no_extrator_regras(state)

    with pytest.raises(AliquotaNaoDisponivelError):
        no_deterministico(state)

    assert state.resultado_calculo is None
    assert state.parecer_final is None


def test_at003_cpf_mascarado_antes_de_qualquer_no_subsequente():
    state = State(
        texto_consulta="CPF 987.654.321-00 quer simular para 2026",
        ano_operacao=2026,
        valor_base=Decimal("1000.00"),
    )

    state = executar_consulta(state)

    assert "987.654.321-00" not in state.texto_mascarado
    assert all("987.654.321-00" not in t.resumo_input for t in state.historico)
    assert all("987.654.321-00" not in t.resumo_output for t in state.historico)
