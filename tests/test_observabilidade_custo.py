"""Agregação de custo (token real + infra espelhada) e alertas por limiar —
Decision 2/3 do DESIGN_PAINEL_OBSERVABILIDADE.md."""

from datetime import date

from observabilidade.custo import (
    LIMIAR_ALERTA_VARIACAO_SEMANAL,
    agregar_custo_infra,
    agregar_custo_token,
    alertas_por_limiar,
)


class FakeCursor:
    def __init__(self, linhas):
        self._linhas = linhas

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._linhas


class FakeConexao:
    def __init__(self, linhas):
        self._linhas = linhas

    def cursor(self):
        return FakeCursor(self._linhas)


def test_agregar_custo_token_calcula_preco_por_modelo():
    conexao = FakeConexao([("claude-sonnet-5", 1_000_000, 1_000_000)])

    total, por_modelo = agregar_custo_token(conexao)

    assert total == 3.00 + 15.00
    assert por_modelo[0].modelo == "claude-sonnet-5"
    assert por_modelo[0].custo_usd == 18.00


def test_agregar_custo_token_modelo_desconhecido_custa_zero():
    conexao = FakeConexao([("modelo-nunca-visto", 1000, 1000)])

    total, por_modelo = agregar_custo_token(conexao)

    assert total == 0.0
    assert por_modelo[0].custo_usd == 0.0


def test_agregar_custo_token_sem_chamadas_devolve_lista_vazia():
    conexao = FakeConexao([])

    total, por_modelo = agregar_custo_token(conexao)

    assert total == 0.0
    assert por_modelo == []


def test_agregar_custo_infra_soma_por_servico():
    conexao = FakeConexao([("Cloud Run", 12.5), ("Cloud SQL", 7.5)])

    total, por_servico = agregar_custo_infra(conexao)

    assert total == 20.0
    assert {item.servico for item in por_servico} == {"Cloud Run", "Cloud SQL"}


def test_alertas_por_limiar_dispara_acima_do_limiar():
    servico = "Cloud SQL"
    atual = 100.0
    anterior = 100.0 / (1 + LIMIAR_ALERTA_VARIACAO_SEMANAL) - 1  # garante variação > limiar
    conexao = FakeConexao([(servico, atual, max(anterior, 1.0))])

    alertas = alertas_por_limiar(conexao, hoje=date(2026, 8, 5))

    assert len(alertas) == 1
    assert "Cloud SQL" in alertas[0]


def test_alertas_por_limiar_nao_dispara_variacao_pequena():
    conexao = FakeConexao([("Cloud SQL", 101.0, 100.0)])

    alertas = alertas_por_limiar(conexao, hoje=date(2026, 8, 5))

    assert alertas == []


def test_alertas_por_limiar_ignora_semana_anterior_sem_dado():
    conexao = FakeConexao([("Cloud SQL", 50.0, None)])

    alertas = alertas_por_limiar(conexao, hoje=date(2026, 8, 5))

    assert alertas == []
