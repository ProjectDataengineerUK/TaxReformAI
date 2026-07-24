from decimal import Decimal
from typing import ClassVar, Protocol

from motor_calculo.fases import FaseTransicao
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError, RegraFiscal


class TabelaAliquotas(Protocol):
    def buscar(self, fase: FaseTransicao) -> RegraFiscal: ...


class TabelaAliquotasSeed:
    """Só contém a fase 2026 — a única com alíquota 100% confirmada em lei
    no momento desta feature (ver DEFINE, Data Contract)."""

    _REGRAS: ClassVar[dict[FaseTransicao, RegraFiscal]] = {
        FaseTransicao.TESTE_2026: RegraFiscal(
            fase=FaseTransicao.TESTE_2026,
            aliq_cbs=Decimal("0.009"),
            aliq_ibs=Decimal("0.001"),
            aliq_is=Decimal(0),
            fonte_legal="Linha do tempo da transição — CBS 0,9% + IBS 0,1%, fase de teste 2026",
            confirmado_em_lei=True,
        ),
    }

    def buscar(self, fase: FaseTransicao) -> RegraFiscal:
        regra = self._REGRAS.get(fase)
        if regra is None:
            raise AliquotaNaoDisponivelError(fase)
        return regra
