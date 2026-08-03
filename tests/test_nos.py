from decimal import Decimal

import pytest

from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError
from orquestracao.dependencias import criar_dependencias_fake
from orquestracao.estado import State
from orquestracao.llm.cliente import MODELO_HAIKU, MODELO_SONNET, ClienteLLMFake
from orquestracao.nos.classificador import mascarar_pii, no_classificador
from orquestracao.nos.deterministico import no_deterministico
from orquestracao.nos.extrator_regras import no_extrator_regras
from orquestracao.nos.pesquisador_legal import no_pesquisador_legal
from orquestracao.nos.sintetizador import LLMRespostaInconsistenteError, no_sintetizador

FONTE_LEGAL_2026 = (
    "LCP 214/2025, arts. 343 e 346 — fase de teste 2026: CBS 0,9% e IBS 0,1% (alíquota estadual)"
)


def _state(texto="consulta de teste", ano=2026, valor_base="1000.00"):
    return State(texto_consulta=texto, ano_operacao=ano, valor_base=Decimal(valor_base))


def _parecer_fake(valor_base, valor_liquido, valor_cbs, valor_ibs, valor_is="0.00"):
    return (
        f"## Parecer\n\nValor base: R$ {valor_base}\nValor líquido: R$ {valor_liquido}\n"
        f"CBS: R$ {valor_cbs}\nIBS: R$ {valor_ibs}\nIS: R$ {valor_is}\n"
        f"Fundamentação: {FONTE_LEGAL_2026}"
    )


def _deps_extrator_sem_divergencia():
    cliente = ClienteLLMFake(
        respostas_por_modelo={MODELO_SONNET: '{"valor_base": null, "ano_operacao": null}'}
    )
    return criar_dependencias_fake(cliente_llm=cliente)


def test_mascarar_pii_cpf():
    assert mascarar_pii("meu CPF é 123.456.789-01") == "meu CPF é [CPF_MASCARADO]"
    assert mascarar_pii("cpf 12345678901 sem pontuação") == "cpf [CPF_MASCARADO] sem pontuação"


def test_mascarar_pii_cnpj():
    assert mascarar_pii("CNPJ 12.345.678/0001-99") == "CNPJ [CNPJ_MASCARADO]"


def test_mascarar_pii_sem_dado_sensivel_nao_altera_texto():
    texto = "quanto de IBS incide sobre eletrônicos em 2027?"
    assert mascarar_pii(texto) == texto


def test_no_classificador_mascara_pii_e_classifica_intencao_real():
    cliente = ClienteLLMFake(respostas_por_modelo={MODELO_HAIKU: "SIMULACAO_TRIBUTARIA"})
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(texto="CPF 123.456.789-01 quer simular")

    state = no_classificador(state, deps)

    assert "[CPF_MASCARADO]" in state.texto_mascarado
    assert "123.456.789-01" not in state.texto_mascarado
    assert state.intencao == "SIMULACAO_TRIBUTARIA"
    assert len(state.historico) == 1
    assert "123.456.789-01" not in state.historico[0].resumo_output


def test_no_classificador_intencao_fora_do_enum_vira_outro():
    cliente = ClienteLLMFake(respostas_por_modelo={MODELO_HAIKU: "algo inesperado"})
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state()

    state = no_classificador(state, deps)

    assert state.intencao == "OUTRO"


def test_no_classificador_nunca_envia_cpf_em_texto_plano_ao_client():
    cliente = ClienteLLMFake(respostas_por_modelo={MODELO_HAIKU: "SIMULACAO_TRIBUTARIA"})
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(texto="CPF 123.456.789-01 quer simular")

    no_classificador(state, deps)

    for chamada in cliente.chamadas:
        for mensagem in chamada["mensagens"]:
            assert "123.456.789-01" not in mensagem["content"]


def test_no_pesquisador_legal_retorna_chunks_reais_do_qdrant():
    import datetime

    from ingestion.chunking.chunk_models import Chunk

    chunk = Chunk(
        documento_id="LCP_214_2025",
        dispositivo="Art. 1, Inciso I",
        esfera="FEDERAL_CBS_IBS",
        data_vigencia_inicio=datetime.date(2026, 1, 1),
        texto="o Imposto sobre Bens e Serviços (IBS)",
        fonte_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
    )
    deps = criar_dependencias_fake(chunks=[chunk])
    state = _state()
    state.intencao = "SIMULACAO_TRIBUTARIA"
    state.texto_mascarado = state.texto_consulta

    state = no_pesquisador_legal(state, deps)

    assert len(state.chunks_legais) == 1
    assert state.chunks_legais[0].documento_id == "LCP_214_2025"
    assert "1 chunk" in state.historico[0].resumo_output


def test_no_pesquisador_legal_sem_resultado_nao_quebra():
    deps = criar_dependencias_fake(chunks=[])
    state = _state()
    state.texto_mascarado = state.texto_consulta

    state = no_pesquisador_legal(state, deps)

    assert state.chunks_legais == []


def test_no_extrator_regras_monta_payload_compativel_com_motor():
    deps = _deps_extrator_sem_divergencia()
    state = _state(valor_base="500.00", ano=2026)
    state.texto_mascarado = state.texto_consulta

    state = no_extrator_regras(state, deps)

    assert state.payload_extraido["valor_base"] == Decimal("500.00")
    assert state.payload_extraido["ano_operacao"] == 2026
    assert "DIVERGÊNCIA" not in state.historico[0].resumo_output


def test_no_extrator_regras_registra_divergencia_sem_alterar_payload():
    cliente = ClienteLLMFake(
        respostas_por_modelo={MODELO_SONNET: '{"valor_base": 999.00, "ano_operacao": 2027}'}
    )
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="500.00", ano=2026)
    state.texto_mascarado = state.texto_consulta

    state = no_extrator_regras(state, deps)

    # Campos estruturados sempre vencem (Decision 3 do DESIGN) — o payload
    # que alimenta motor_calculo nunca muda por causa de uma extração de LLM.
    assert state.payload_extraido["valor_base"] == Decimal("500.00")
    assert state.payload_extraido["ano_operacao"] == 2026
    assert "DIVERGÊNCIA" in state.historico[0].resumo_output


def test_no_extrator_regras_resposta_llm_sem_json_nao_quebra():
    cliente = ClienteLLMFake(respostas_por_modelo={MODELO_SONNET: "não consegui extrair nada"})
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="500.00", ano=2026)
    state.texto_mascarado = state.texto_consulta

    state = no_extrator_regras(state, deps)

    assert state.payload_extraido["valor_base"] == Decimal("500.00")
    assert state.payload_extraido["ano_operacao"] == 2026


def test_no_deterministico_integra_de_verdade_com_motor_calculo():
    deps = _deps_extrator_sem_divergencia()
    state = _state(valor_base="1000.00", ano=2026)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)

    assert state.resultado_calculo is not None
    assert state.resultado_calculo.valor_cbs == Decimal("9.00")
    assert state.resultado_calculo.valor_ibs == Decimal("1.00")
    assert "2026" in state.resultado_calculo.fonte_legal


def test_no_deterministico_propaga_erro_para_fase_sem_aliquota():
    deps = _deps_extrator_sem_divergencia()
    state = _state(valor_base="1000.00", ano=2028)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)

    with pytest.raises(AliquotaNaoDisponivelError):
        no_deterministico(state)


def test_no_sintetizador_gera_parecer_com_fonte_legal_e_sem_marcador_fake():
    cliente = ClienteLLMFake(
        respostas_por_modelo={
            MODELO_SONNET: _parecer_fake(
                valor_base="1000.00", valor_liquido="990.00", valor_cbs="9.00", valor_ibs="1.00"
            )
        }
    )
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="1000.00", ano=2026)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)
    state = no_sintetizador(state, deps)

    assert state.parecer_final is not None
    assert "990.00" in state.parecer_final
    assert "[FAKE]" not in state.parecer_final
    assert "[FAKE]" not in state.historico[-1].resumo_output


def test_no_sintetizador_guardrail_rejeita_parecer_sem_valor_liquido_exato():
    cliente = ClienteLLMFake(
        respostas_por_modelo={MODELO_SONNET: "## Parecer\n\nValor líquido: R$ 999999.99"}
    )
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="1000.00", ano=2026)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)

    with pytest.raises(LLMRespostaInconsistenteError):
        no_sintetizador(state, deps)


def test_no_sintetizador_guardrail_rejeita_parecer_com_fonte_legal_alterada():
    # Valor líquido correto, mas fonte_legal divergente — a versão anterior
    # do guardrail (só checava valor_liquido) deixaria passar; achado da
    # revisão de segurança de LLM_REAL_VERTEX_AI.
    cliente = ClienteLLMFake(
        respostas_por_modelo={
            MODELO_SONNET: (
                "## Parecer\n\nValor base: R$ 1000.00\nValor líquido: R$ 990.00\n"
                "CBS: R$ 9.00\nIBS: R$ 1.00\nIS: R$ 0.00\n"
                "Fundamentação: um artigo qualquer inventado"
            )
        }
    )
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="1000.00", ano=2026)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)

    with pytest.raises(LLMRespostaInconsistenteError):
        no_sintetizador(state, deps)


def test_no_sintetizador_aceita_valor_com_separador_decimal_pt_br():
    cliente = ClienteLLMFake(
        respostas_por_modelo={
            MODELO_SONNET: (
                "## Parecer\n\nValor base: R$ 500,00\nValor líquido: R$ 495,00\n"
                f"CBS: R$ 4,50\nIBS: R$ 0,50\nIS: R$ 0,00\nFundamentação: {FONTE_LEGAL_2026}"
            )
        }
    )
    deps = criar_dependencias_fake(cliente_llm=cliente)
    state = _state(valor_base="500.00", ano=2026)
    state.texto_mascarado = state.texto_consulta
    state = no_extrator_regras(state, deps)
    state = no_deterministico(state)

    state = no_sintetizador(state, deps)
    assert state.parecer_final is not None
