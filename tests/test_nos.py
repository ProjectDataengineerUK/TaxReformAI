from decimal import Decimal

import pytest

from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.estado import State
from orquestracao.nos.classificador import mascarar_pii, no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import no_sintetizador


def _state(texto="consulta de teste", ano=2026, valor_base="1000.00"):
    return State(texto_consulta=texto, ano_operacao=ano, valor_base=Decimal(valor_base))


def test_mascarar_pii_cpf():
    assert mascarar_pii("meu CPF é 123.456.789-01") == "meu CPF é [CPF_MASCARADO]"
    assert mascarar_pii("cpf 12345678901 sem pontuação") == "cpf [CPF_MASCARADO] sem pontuação"


def test_mascarar_pii_cnpj():
    assert mascarar_pii("CNPJ 12.345.678/0001-99") == "CNPJ [CNPJ_MASCARADO]"


def test_mascarar_pii_sem_dado_sensivel_nao_altera_texto():
    texto = "quanto de IBS incide sobre eletrônicos em 2027?"
    assert mascarar_pii(texto) == texto


def test_no_classificador_mascara_pii_e_classifica_intencao_fake():
    state = _state(texto="CPF 123.456.789-01 quer simular")
    state = no_classificador(state)

    assert "[CPF_MASCARADO]" in state.texto_mascarado
    assert "123.456.789-01" not in state.texto_mascarado
    assert state.intencao == "SIMULACAO_TRIBUTARIA"
    assert len(state.historico) == 1
    assert "123.456.789-01" not in state.historico[0].resumo_output


def test_no_pesquisador_legal_retorna_chunk_real_schema():
    state = _state()
    state.intencao = "SIMULACAO_TRIBUTARIA"
    state = no_pesquisador_legal(state)

    assert len(state.chunks_legais) == 1
    chunk = state.chunks_legais[0]
    assert chunk.documento_id == "LCP_214_2025"
    assert chunk.dispositivo
    assert chunk.fonte_url


def test_no_extrator_regras_monta_payload_compativel_com_motor():
    state = _state(valor_base="500.00", ano=2026)
    state = no_extrator_regras(state)

    assert state.payload_extraido["valor_base"] == Decimal("500.00")
    assert state.payload_extraido["ano_operacao"] == 2026


def test_no_deterministico_integra_de_verdade_com_motor_calculo():
    state = _state(valor_base="1000.00", ano=2026)
    state = no_extrator_regras(state)
    state = no_deterministico(state)

    assert state.resultado_calculo is not None
    assert state.resultado_calculo.valor_cbs == Decimal("9.00")
    assert state.resultado_calculo.valor_ibs == Decimal("1.00")
    assert "2026" in state.resultado_calculo.fonte_legal


def test_no_deterministico_propaga_erro_para_fase_sem_aliquota():
    state = _state(valor_base="1000.00", ano=2028)
    state = no_extrator_regras(state)

    with pytest.raises(AliquotaNaoDisponivelError):
        no_deterministico(state)


def test_no_sintetizador_gera_parecer_com_fonte_legal():
    state = _state(valor_base="1000.00", ano=2026)
    state = no_extrator_regras(state)
    state = no_deterministico(state)
    state = no_sintetizador(state)

    assert state.parecer_final is not None
    assert "990.00" in state.parecer_final
    assert state.resultado_calculo.fonte_legal in state.parecer_final
