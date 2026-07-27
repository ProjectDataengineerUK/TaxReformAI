"""Lógica pura de resolução do IPI — sem banco, sem HTTP.

`normalizar_ncm` e `resolver_item` são funções puras exatamente para que as
5 situações de `SituacaoIpi` possam ser exercitadas aqui, e não só através de
um `TestClient` com pool fake (isso é `test_api_simulate_ipi.py`).
"""

from decimal import Decimal

import pytest

from api.ipi import (
    ConsultaIpi,
    SituacaoIpi,
    consultar_ipi_com_seguranca,
    normalizar_ncm,
    resolver_item,
)
from db.repositorio import AliquotaIpi

FONTE = "Decreto 11.158/2022 (TIPI), posição 2203.00.00"

CERVEJA = AliquotaIpi(
    ncm_code="2203.00.00",
    aliquota_percentual=Decimal("0.03250"),
    nao_tributado=False,
    dispositivo_legal_ref=FONTE,
)
NAO_TRIBUTADO = AliquotaIpi(
    ncm_code="0102.21.10",
    aliquota_percentual=None,
    nao_tributado=True,
    dispositivo_legal_ref="Decreto 11.158/2022 (TIPI), NT",
)

DISPONIVEL = ConsultaIpi(
    disponivel=True,
    por_ncm={"2203.00.00": CERVEJA, "0102.21.10": NAO_TRIBUTADO},
)


# normalizar_ncm ------------------------------------------------------------


@pytest.mark.parametrize(
    "bruto",
    ["22030000", "2203.00.00", "2203 00 00", "2203-00-00", " 2203.00.00 "],
)
def test_normaliza_todas_as_grafias_para_o_formato_da_tabela(bruto):
    """A tabela guarda o pontuado (formato do PDF oficial), ERPs emitem NFe com
    8 dígitos corridos, e o smoke test do deploy manda `22030000`. Sem esta
    equivalência a feature entregaria NCM_NAO_ENCONTRADO para o tráfego real."""
    assert normalizar_ncm(bruto) == "2203.00.00"


def test_normalizacao_e_injetiva_nenhum_codigo_vira_outro():
    """A garantia que separa "normalizar formato" de "fuzzy match": dois
    códigos distintos nunca colidem no mesmo valor canônico."""
    # O prefixo de 4 dígitos varia sempre (1000..1199) e os sufixos ficam em
    # `% 100`: um `i:02d` estourando de 99 para 100 geraria 9 dígitos, e o
    # teste passaria a comparar Nones em vez de códigos.
    codigos = [f"{1000 + i:04d}{i % 100:02d}{(i * 7) % 100:02d}" for i in range(200)]
    normalizados = [normalizar_ncm(c) for c in codigos]

    assert len(set(normalizados)) == len(codigos)


@pytest.mark.parametrize(
    "parcial",
    ["2203", "22.03", "220300", "2203.00", "220300000", "8471.30.12.EX01"],
)
def test_codigo_parcial_ou_com_digitos_demais_devolve_none(parcial):
    """Capítulo/posição são cabeçalhos de categoria sem alíquota própria.
    Devolver None (que vira NCM_NAO_ENCONTRADO) é o oposto de buscar por
    prefixo — que o DEFINE proíbe explicitamente."""
    assert normalizar_ncm(parcial) is None


@pytest.mark.parametrize("lixo", ["", "   ", "abcdefgh", "N/A", "-"])
def test_entrada_sem_8_digitos_devolve_none_em_vez_de_consultar(lixo):
    assert normalizar_ncm(lixo) is None


# resolver_item — as 5 situações -------------------------------------------


def test_ncm_com_aliquota_calcula_e_cita_o_dispositivo_da_propria_linha():
    resolucao = resolver_item("MERCADORIA", "22030000", Decimal("1000.00"), DISPONIVEL)

    assert resolucao.situacao is SituacaoIpi.CALCULADO
    assert resolucao.valor == Decimal("32.50")
    assert resolucao.percentual == Decimal("3.25000")
    assert resolucao.fonte_legal == FONTE
    assert resolucao.resolvido is True


def test_nao_tributado_e_resolvido_mas_sem_percentual_nem_valor():
    """NT é classificação tributária da TIPI, não alíquota 0%: sabemos a
    resposta jurídica (resolvido=True) e ela não vira percentual nenhum."""
    resolucao = resolver_item("MERCADORIA", "0102.21.10", Decimal("1000.00"), DISPONIVEL)

    assert resolucao.situacao is SituacaoIpi.NAO_TRIBUTADO
    assert resolucao.percentual is None
    assert resolucao.valor == Decimal(0)
    assert resolucao.fonte_legal is not None
    assert resolucao.resolvido is True


def test_ncm_ausente_da_tabela_nao_e_zero_por_cento():
    resolucao = resolver_item("MERCADORIA", "99999999", Decimal("1000.00"), DISPONIVEL)

    assert resolucao.situacao is SituacaoIpi.NCM_NAO_ENCONTRADO
    assert resolucao.percentual is None
    assert resolucao.resolvido is False


@pytest.mark.parametrize("consulta", [DISPONIVEL, ConsultaIpi(disponivel=False)])
def test_ncm_irreconhecivel_nao_encontra_ate_com_o_banco_fora_do_ar(consulta):
    """A guarda de formato vem ANTES da de disponibilidade: nenhuma TIPI
    conteria "2203" (posição, cabeçalho de categoria), então dizer
    CONSULTA_INDISPONIVEL mandaria o cliente reprocessar algo que jamais
    mudaria de resposta."""
    resolucao = resolver_item("MERCADORIA", "2203", Decimal("1000.00"), consulta)

    assert resolucao.situacao is SituacaoIpi.NCM_NAO_ENCONTRADO


def test_consulta_indisponivel_e_distinta_de_ncm_nao_encontrado():
    """A distinção que a Decisão 6 existe para preservar: o cliente precisa
    saber se o dado não existe (não adianta reprocessar) ou se o sistema não
    conseguiu consultar (adianta)."""
    resolucao = resolver_item(
        "MERCADORIA", "22030000", Decimal("1000.00"), ConsultaIpi(disponivel=False)
    )

    assert resolucao.situacao is SituacaoIpi.CONSULTA_INDISPONIVEL
    assert resolucao.resolvido is False


def test_servico_nao_aplicavel_mesmo_com_ncm_valido_na_tabela():
    """Serviço não paga IPI — a guarda vem antes de qualquer consulta, então
    nem a indisponibilidade do banco altera esta resposta."""
    for consulta in (DISPONIVEL, ConsultaIpi(disponivel=False)):
        resolucao = resolver_item("SERVICO", "22030000", Decimal("1000.00"), consulta)
        assert resolucao.situacao is SituacaoIpi.NAO_APLICAVEL
        assert resolucao.percentual is None


def test_arredondamento_segue_round_half_up_em_centavos():
    """Mesma disciplina do engine e de PIS/COFINS/ICMS: divergir aqui seria
    erro de cálculo silencioso num sistema financeiro."""
    linha = AliquotaIpi("1111.11.11", Decimal("0.10000"), False, FONTE)
    consulta = ConsultaIpi(disponivel=True, por_ncm={"1111.11.11": linha})

    resolucao = resolver_item("MERCADORIA", "11111111", Decimal("0.05"), consulta)

    assert resolucao.valor == Decimal("0.01")


# consultar_ipi_com_seguranca — a fronteira que nunca levanta ---------------


class _PoolQueExplode:
    def connection(self):
        raise ConnectionError("Cloud SQL indisponível (simulado)")


class _PoolComGrantNegado:
    def connection(self):
        raise PermissionError("permission denied for table aliquotas_ipi_tipi")


def test_pool_none_e_indisponibilidade_nao_ausencia_de_dado():
    consulta = consultar_ipi_com_seguranca(None, ["2203.00.00"])

    assert consulta.disponivel is False
    assert consulta.por_ncm == {}


def test_lista_vazia_nao_abre_conexao_e_nao_e_indisponibilidade():
    """Payload só de serviços não toca o banco — o caminho mais rápido continua
    tão rápido quanto antes desta feature (Decisão 7/AT-005).

    E `disponivel` continua True: não ter NADA a perguntar é diferente de não
    CONSEGUIR perguntar. Confundir os dois faria um payload cujos NCMs são
    todos irreconhecíveis acusar o banco de um problema que está no payload.
    """

    class _PoolQueNaoDeveSerUsado:
        def connection(self):
            raise AssertionError("nenhuma conexão deveria ter sido aberta")

    consulta = consultar_ipi_com_seguranca(_PoolQueNaoDeveSerUsado(), [])

    assert consulta.disponivel is True
    assert consulta.por_ncm == {}


@pytest.mark.parametrize("pool", [_PoolQueExplode(), _PoolComGrantNegado()])
def test_qualquer_falha_vira_indisponibilidade_e_nunca_propaga(pool, caplog):
    consulta = consultar_ipi_com_seguranca(pool, ["2203.00.00"])

    assert consulta.disponivel is False
    assert "Falha ao consultar IPI/TIPI" in caplog.text, (
        "degradar não é silenciar: sem o log, um GRANT faltando some em produção"
    )
