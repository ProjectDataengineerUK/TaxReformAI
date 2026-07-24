from dataclasses import dataclass
from decimal import Decimal

from motor_calculo.fases import FaseTransicao


@dataclass(frozen=True)
class RegraFiscal:
    fase: FaseTransicao
    aliq_cbs: Decimal
    aliq_ibs: Decimal
    aliq_is: Decimal
    fonte_legal: str
    confirmado_em_lei: bool = True


class AliquotaNaoDisponivelError(Exception):
    def __init__(self, fase: FaseTransicao):
        super().__init__(
            f"Alíquota não disponível para a fase {fase.value} — "
            "requer Resolução do Senado/TCU ainda não ingerida. "
            "Nenhum cálculo é retornado para evitar simular com dado não confirmado."
        )
        self.fase = fase
