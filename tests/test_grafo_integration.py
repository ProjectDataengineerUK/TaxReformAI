from decimal import Decimal

import pytest

from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.dependencias import criar_dependencias_fake
from orquestracao.estado import State
from orquestracao.executor import ConsultaForaDeEscopoError, executar_consulta
from orquestracao.llm.cliente import MODELO_HAIKU, MODELO_SONNET, ClienteLLMFake
from orquestracao.nos.classificador import no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal

FONTE_LEGAL_2026 = (
    "LCP 214/2025, arts. 343 e 346 — fase de teste 2026: CBS 0,9% e IBS 0,1% (alíquota estadual)"
)


def _cliente_fake_feliz(
    valor_base: str, valor_liquido: str, valor_cbs: str, valor_ibs: str
) -> ClienteLLMFake:
    return ClienteLLMFake(
        respostas_por_modelo={
            MODELO_HAIKU: "SIMULACAO_TRIBUTARIA",
            MODELO_SONNET: (
                f"## Parecer\n\nValor base: R$ {valor_base}\nValor líquido: R$ {valor_liquido}\n"
                f"CBS: R$ {valor_cbs}\nIBS: R$ {valor_ibs}\nIS: R$ 0.00\n"
                f"Fundamentação: {FONTE_LEGAL_2026}"
            ),
        }
    )


def test_at001_happy_path_grafo_completo():
    state = State(
        texto_consulta="Simular CBS/IBS para venda de eletrônicos em 2026",
        ano_operacao=2026,
        valor_base=Decimal("2500.00"),
    )
    deps = criar_dependencias_fake(
        cliente_llm=_cliente_fake_feliz(
            valor_base="2500.00", valor_liquido="2475.00", valor_cbs="22.50", valor_ibs="2.50"
        )
    )

    state = executar_consulta(state, deps)

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
    deps = criar_dependencias_fake(
        cliente_llm=_cliente_fake_feliz(
            valor_base="1000.00", valor_liquido="990.00", valor_cbs="9.00", valor_ibs="1.00"
        )
    )

    state = no_classificador(state, deps)
    state = no_pesquisador_legal(state, deps)
    state = no_extrator_regras(state, deps)

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
    deps = criar_dependencias_fake(
        cliente_llm=_cliente_fake_feliz(
            valor_base="1000.00", valor_liquido="990.00", valor_cbs="9.00", valor_ibs="1.00"
        )
    )

    state = executar_consulta(state, deps)

    assert "987.654.321-00" not in state.texto_mascarado
    assert all("987.654.321-00" not in t.resumo_input for t in state.historico)
    assert all("987.654.321-00" not in t.resumo_output for t in state.historico)


def test_at004_intencao_outro_interrompe_sem_simulacao_fabricada():
    """Achado real (2026-08-05): "uma receita de bolo de chocolate" gerava um
    parecer completo de simulação tributária, usando valor_base/ano_operacao
    que sobravam no payload — o classificador já dizia intencao=OUTRO, mas
    nada usava essa classificação para interromper o pipeline."""
    state = State(
        texto_consulta="uma receita de bolo de chocolate",
        ano_operacao=2026,
        valor_base=Decimal("1000.00"),
    )
    deps = criar_dependencias_fake(
        cliente_llm=ClienteLLMFake(respostas_por_modelo={MODELO_HAIKU: "OUTRO"})
    )

    with pytest.raises(ConsultaForaDeEscopoError):
        executar_consulta(state, deps)

    assert state.resultado_calculo is None
    assert state.parecer_final is None
    assert [t.no for t in state.historico] == ["classificador"]
