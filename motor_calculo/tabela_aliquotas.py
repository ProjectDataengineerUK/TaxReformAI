from decimal import Decimal
from typing import ClassVar, Protocol

from motor_calculo.fases import FaseTransicao
from motor_calculo.regras_fiscais import AliquotaNaoDisponivelError, RegraFiscal


class TabelaAliquotas(Protocol):
    def buscar(self, fase: FaseTransicao) -> RegraFiscal: ...


class TabelaAliquotasSeed:
    """Alíquotas extraídas do texto real da LCP 214/2025 (com as alterações da
    LCP 227/2026), conferido no HTML ingerido do Planalto.

    O que a lei fixa como número, está aqui com o artigo. O que ela delega a
    norma futura fica `None` — não estimado. Para 2029 em diante a própria lei
    remete a alíquotas de referência a fixar (arts. 353 a 369), então nem a
    fase existe nesta tabela.
    """

    _REGRAS: ClassVar[dict[FaseTransicao, RegraFiscal]] = {
        FaseTransicao.TESTE_2026: RegraFiscal(
            fase=FaseTransicao.TESTE_2026,
            aliq_cbs=Decimal("0.009"),
            aliq_ibs=Decimal("0.001"),
            aliq_is=Decimal(0),
            fonte_legal=(
                "LCP 214/2025, arts. 343 e 346 — fase de teste 2026: "
                "CBS 0,9% e IBS 0,1% (alíquota estadual)"
            ),
            confirmado_em_lei=True,
            fontes_por_tributo={
                "CBS": "LCP 214/2025, art. 346 — 0,9% (nove décimos por cento)",
                "IBS": "LCP 214/2025, art. 343 — alíquota estadual de 0,1% (um décimo por cento)",
                "IS": (
                    "Não incide em 2026: para os fatos geradores de 2026 a LCP 214/2025 "
                    "fixa apenas CBS (art. 346) e IBS (art. 343)"
                ),
            },
        ),
        # 2027-2028 é parcialmente conhecida, e é justamente por isso que o
        # modelo aceita alíquota `None`. O art. 344 fixa o IBS em 0,05%
        # estadual + 0,05% municipal (0,1% somados). Já o art. 347 manda aplicar
        # à CBS "aquela fixada nos termos do inciso I do caput e dos §§ 2º e 3º
        # do art. 14, reduzida em 0,1 ponto percentual" — uma alíquota de
        # referência que ainda não existe como número. E as alíquotas do IS são
        # fixadas por lei ordinária e variam por produto (a LCP 214 só define
        # tetos por categoria, como os 0,25% de bens minerais no art. 409, § 2º),
        # de modo que não há um número único de IS por fase.
        FaseTransicao.PLENO_CBS_IS_2027: RegraFiscal(
            fase=FaseTransicao.PLENO_CBS_IS_2027,
            aliq_cbs=None,
            aliq_ibs=Decimal("0.001"),
            aliq_is=None,
            fonte_legal=(
                "LCP 214/2025, art. 344 — 2027-2028: IBS 0,05% estadual + 0,05% municipal. "
                "CBS e IS ainda dependem de norma futura"
            ),
            confirmado_em_lei=False,
            fontes_por_tributo={
                "CBS": (
                    "LCP 214/2025, art. 347 — alíquota de referência fixada nos termos do "
                    "art. 14, I e §§ 2º e 3º, reduzida em 0,1 ponto percentual; a alíquota "
                    "de referência ainda não foi fixada"
                ),
                "IBS": (
                    "LCP 214/2025, art. 344 — 0,05% (cinco centésimos por cento) estadual "
                    "e 0,05% municipal"
                ),
                "IS": (
                    "Fixadas por lei ordinária e variáveis por produto; a LCP 214/2025 "
                    "define apenas tetos por categoria (p. ex. art. 409, § 2º, teto de "
                    "0,25% para bens minerais extraídos)"
                ),
            },
        ),
    }

    def buscar(self, fase: FaseTransicao) -> RegraFiscal:
        regra = self._REGRAS.get(fase)
        if regra is None:
            raise AliquotaNaoDisponivelError(fase)
        return regra
