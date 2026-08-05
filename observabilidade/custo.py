"""Agrega custo de token (real, via uso_llm) e de infra (espelhado de
GCP Billing Export via custo_infra_diario) + achados FinOps por limiar —
Decision 2/3 do DESIGN_PAINEL_OBSERVABILIDADE.md.

Preços por milhão de tokens (USD) — publicados pela Anthropic, não vêm de
nenhuma API por chamada: a Anthropic não devolve custo em dólar na resposta,
só contagem de tokens. Atualizar esta tabela quando os preços mudarem é
responsabilidade humana, mesma disciplina do scorecard.yaml.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

PRECO_POR_MILHAO_TOKENS_USD: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"entrada": 1.00, "saida": 5.00},
    "claude-haiku-4-5@20251001": {"entrada": 1.00, "saida": 5.00},
    "claude-sonnet-5": {"entrada": 3.00, "saida": 15.00},
}

LIMIAR_ALERTA_VARIACAO_SEMANAL = 0.20


@dataclass
class CustoPorModelo:
    modelo: str
    tokens_entrada: int
    tokens_saida: int
    custo_usd: float


@dataclass
class CustoInfraPorServico:
    servico: str
    custo_usd: float


@dataclass
class AlertaFinOps:
    achado: str
    fonte: str
    oportunidade: str


@dataclass
class ResumoCusto:
    periodo_dias: int
    custo_token_total_usd: float
    custo_por_modelo: list[CustoPorModelo]
    custo_infra_total_usd: float
    custo_infra_por_servico: list[CustoInfraPorServico]
    alertas_limiar: list[str] = field(default_factory=list)


def _custo_tokens_usd(modelo: str, tokens_entrada: int, tokens_saida: int) -> float:
    preco = PRECO_POR_MILHAO_TOKENS_USD.get(modelo)
    if preco is None:
        return 0.0
    return (tokens_entrada / 1_000_000) * preco["entrada"] + (tokens_saida / 1_000_000) * preco["saida"]


def agregar_custo_token(conexao, periodo_dias: int = 30) -> tuple[float, list[CustoPorModelo]]:
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT modelo, SUM(tokens_entrada), SUM(tokens_saida) FROM uso_llm "
            "WHERE sucesso = TRUE AND created_at >= NOW() - (%s || ' days')::interval "
            "GROUP BY modelo",
            (periodo_dias,),
        )
        linhas = cur.fetchall()

    por_modelo = []
    total = 0.0
    for modelo, tokens_entrada, tokens_saida in linhas:
        custo = _custo_tokens_usd(modelo, tokens_entrada, tokens_saida)
        total += custo
        por_modelo.append(
            CustoPorModelo(modelo=modelo, tokens_entrada=tokens_entrada, tokens_saida=tokens_saida, custo_usd=custo)
        )
    return total, por_modelo


def agregar_custo_infra(conexao, periodo_dias: int = 30) -> tuple[float, list[CustoInfraPorServico]]:
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT servico, SUM(custo_usd) FROM custo_infra_diario "
            "WHERE data >= CURRENT_DATE - %s::int GROUP BY servico ORDER BY SUM(custo_usd) DESC",
            (periodo_dias,),
        )
        linhas = cur.fetchall()

    por_servico = [CustoInfraPorServico(servico=servico, custo_usd=float(custo)) for servico, custo in linhas]
    total = sum(item.custo_usd for item in por_servico)
    return total, por_servico


def alertas_por_limiar(conexao, hoje: date | None = None) -> list[str]:
    """Compara o gasto de infra da última semana completa contra a anterior —
    limiar simples (Decision do /brainstorm: sem previsão/IA, só limiar)."""
    referencia = hoje or datetime.now(UTC).date()
    fim_semana_atual = referencia
    inicio_semana_atual = fim_semana_atual - timedelta(days=7)
    inicio_semana_anterior = inicio_semana_atual - timedelta(days=7)

    with conexao.cursor() as cur:
        cur.execute(
            "SELECT servico, "
            "SUM(custo_usd) FILTER (WHERE data >= %s) AS atual, "
            "SUM(custo_usd) FILTER (WHERE data >= %s AND data < %s) AS anterior "
            "FROM custo_infra_diario WHERE data >= %s GROUP BY servico",
            (inicio_semana_atual, inicio_semana_anterior, inicio_semana_atual, inicio_semana_anterior),
        )
        linhas = cur.fetchall()

    alertas = []
    for servico, atual, anterior in linhas:
        if not anterior or not atual:
            continue
        variacao = (float(atual) - float(anterior)) / float(anterior)
        if variacao >= LIMIAR_ALERTA_VARIACAO_SEMANAL:
            alertas.append(f"{servico}: gasto subiu {variacao:.0%} na última semana")
    return alertas


def calcular_resumo_custo(conexao, periodo_dias: int = 30) -> ResumoCusto:
    custo_token_total, por_modelo = agregar_custo_token(conexao, periodo_dias)
    custo_infra_total, por_servico = agregar_custo_infra(conexao, periodo_dias)
    alertas = alertas_por_limiar(conexao)
    return ResumoCusto(
        periodo_dias=periodo_dias,
        custo_token_total_usd=custo_token_total,
        custo_por_modelo=por_modelo,
        custo_infra_total_usd=custo_infra_total,
        custo_infra_por_servico=por_servico,
        alertas_limiar=alertas,
    )
