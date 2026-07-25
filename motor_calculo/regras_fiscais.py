from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from motor_calculo.fases import FaseTransicao


@dataclass(frozen=True)
class RegraFiscal:
    """Alíquotas de uma fase da transição.

    Cada alíquota é `None` quando a lei **não** fixa um número — caso real e
    frequente: o art. 344 fixa o IBS de 2027-2028 em 0,05% + 0,05%, enquanto o
    art. 347 deixa a CBS do mesmo período dependente de uma alíquota de
    referência ainda a ser fixada. Uma fase pode, portanto, ser parcialmente
    conhecida, e o modelo precisa saber dizer isso em vez de escolher entre
    inventar um número e fingir que nada se sabe.

    `fontes_por_tributo` mapeia "CBS"/"IBS"/"IS" ao dispositivo que fixa a
    alíquota — ou, quando ela não está fixada, ao que remete à norma futura.
    É o que permite ao erro dizer *por que* o cálculo não pode ser feito.
    """

    fase: FaseTransicao
    aliq_cbs: Decimal | None
    aliq_ibs: Decimal | None
    aliq_is: Decimal | None
    fonte_legal: str
    confirmado_em_lei: bool = True
    fontes_por_tributo: Mapping[str, str] = field(default_factory=dict)

    def tributos_indisponiveis(self) -> list[str]:
        return [
            nome
            for nome, valor in (
                ("CBS", self.aliq_cbs),
                ("IBS", self.aliq_ibs),
                ("IS", self.aliq_is),
            )
            if valor is None
        ]


class AliquotaNaoDisponivelError(Exception):
    """Erguido em vez de estimar. Num produto que promete simulação auditável
    para departamento fiscal, um percentual inventado é pior que resposta
    nenhuma: na tela do usuário ele é indistinguível de um correto."""

    def __init__(
        self,
        fase: FaseTransicao,
        *,
        tributos: list[str] | None = None,
        regra: RegraFiscal | None = None,
    ):
        self.fase = fase
        self.tributos = tributos or []

        if not tributos:
            mensagem = (
                f"Alíquota não disponível para a fase {fase.value} — "
                "requer Resolução do Senado/TCU ainda não ingerida. "
                "Nenhum cálculo é retornado para evitar simular com dado não confirmado."
            )
        else:
            mensagem = (
                f"Fase {fase.value}: sem alíquota fixada em lei para "
                f"{', '.join(tributos)}. Nenhum cálculo é retornado para evitar "
                "simular com dado não confirmado."
            )
            if regra is not None:
                detalhes = [
                    f"{t}: {regra.fontes_por_tributo[t]}"
                    for t in tributos
                    if t in regra.fontes_por_tributo
                ]
                if detalhes:
                    mensagem += " " + " | ".join(detalhes) + "."
                conhecidos = [
                    f"{t}={v}"
                    for t, v in (
                        ("CBS", regra.aliq_cbs),
                        ("IBS", regra.aliq_ibs),
                        ("IS", regra.aliq_is),
                    )
                    if v is not None
                ]
                if conhecidos:
                    mensagem += (
                        f" Já fixado nesta fase: {', '.join(conhecidos)} — "
                        "a simulação exige os três."
                    )

        super().__init__(mensagem)
