"""Lógica pura dos Anexos de redução por NBS (II, III, X, XI) — sem banco, sem
HTTP.

O seed é lido das PRÓPRIAS migrações 011 (II, III, XI) e 012 (X), mesmo
motivo de `test_reducao_resolucao.py`: uma segunda cópia em Python destes
91 itens/90 prefixos divergiria em silêncio do que o banco de produção
carrega. O SQL de verdade é `test_reducao_nbs_db.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest

from api.reducao_nbs import (
    ConsultaReducaoNbs,
    SituacaoReducaoNbs,
    formatar_item,
    resolver_item_nbs,
)

MIGRACOES = Path(__file__).resolve().parents[1] / "db" / "migrations"
_SQL = (
    (MIGRACOES / "011_anexos_reducao_percentual_nbs.sql").read_text(encoding="utf-8")
    + (MIGRACOES / "012_anexo_x_producoes_nacionais.sql").read_text(encoding="utf-8")
)

_LINHA_CATALOGO_NOVA = re.compile(
    r"\('(II|III|X|XI)',\s*(\d+),\s*([\d.]+),\s*'[^']*',\s*'[^']*',\s*NULL\)"
)
_LINHA_ITEM_SIMPLES = re.compile(
    r"\('([A-Z]+)',\s*(\d+),\s*(\d+),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)'\)"
)
_LINHA_ITEM_XI = re.compile(
    r"\('(XI)',\s*(\d+),\s*(\d+),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)',"
    r"\s*(NULL|'[^']*'),\s*(NULL|'[^']*')\)"
)
_LINHA_ITEM_X = re.compile(
    r"\('(X)',\s*(\d+),\s*(\d+),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)',"
    r"\s*(NULL|'[^']*')\)"
)
_LINHA_PREFIXO = re.compile(
    r"\('([A-Z]+)',\s*(\d+),\s*(\d+),\s*'(\d+)',\s*'([\d.]+)'\)"
)


def _texto_ou_none(bruto: str) -> str | None:
    return None if bruto == "NULL" else bruto.strip("'")


@dataclass(frozen=True)
class _Linha:
    anexo: str
    anexo_ordem: int
    percentual_reducao: Decimal
    item: int
    sub_item: int
    prefixo: str
    texto_nbs: str
    descricao: str
    descricao_contexto: str | None
    dispositivo_legal_ref: str
    condicao_nacionalidade_ref: str | None
    condicao_comprador_ref: str | None
    condicao_vendedor_ref: str | None


def _carregar_seed() -> list[_Linha]:
    catalogo = {
        anexo: (int(ordem), Decimal(percentual).quantize(Decimal("0.0001")))
        for anexo, ordem, percentual in _LINHA_CATALOGO_NOVA.findall(_SQL)
    }

    itens: dict[tuple[str, int, int], dict] = {}
    for anexo, item, sub_item, descricao, dispositivo in _LINHA_ITEM_SIMPLES.findall(_SQL):
        chave = (anexo, int(item), int(sub_item))
        itens[chave] = {
            "descricao": descricao,
            "dispositivo_legal_ref": dispositivo,
            "condicao_nacionalidade_ref": None,
            "condicao_comprador_ref": None,
            "condicao_vendedor_ref": None,
        }
    for anexo, item, sub_item, descricao, dispositivo, comprador, vendedor in _LINHA_ITEM_XI.findall(_SQL):
        chave = (anexo, int(item), int(sub_item))
        itens[chave] = {
            "descricao": descricao,
            "dispositivo_legal_ref": dispositivo,
            "condicao_nacionalidade_ref": None,
            "condicao_comprador_ref": _texto_ou_none(comprador),
            "condicao_vendedor_ref": _texto_ou_none(vendedor),
        }
    for anexo, item, sub_item, descricao, dispositivo, nacionalidade in _LINHA_ITEM_X.findall(_SQL):
        chave = (anexo, int(item), int(sub_item))
        itens[chave] = {
            "descricao": descricao,
            "dispositivo_legal_ref": dispositivo,
            "condicao_nacionalidade_ref": _texto_ou_none(nacionalidade),
            "condicao_comprador_ref": None,
            "condicao_vendedor_ref": None,
        }

    def _contexto(anexo: str, item: int, sub_item: int) -> str | None:
        if sub_item == 0:
            return None
        pai = itens.get((anexo, item, 0))
        return pai["descricao"] if pai else None

    linhas = []
    for anexo, item, sub_item, prefixo, texto_nbs in _LINHA_PREFIXO.findall(_SQL):
        chave = (anexo, int(item), int(sub_item))
        info = itens[chave]
        ordem, percentual = catalogo[anexo]
        linhas.append(
            _Linha(
                anexo=anexo,
                anexo_ordem=ordem,
                percentual_reducao=percentual,
                item=int(item),
                sub_item=int(sub_item),
                prefixo=prefixo,
                texto_nbs=texto_nbs,
                descricao=info["descricao"],
                descricao_contexto=_contexto(anexo, int(item), int(sub_item)),
                dispositivo_legal_ref=info["dispositivo_legal_ref"],
                condicao_nacionalidade_ref=info["condicao_nacionalidade_ref"],
                condicao_comprador_ref=info["condicao_comprador_ref"],
                condicao_vendedor_ref=info["condicao_vendedor_ref"],
            )
        )
    return linhas


SEED = _carregar_seed()


def test_seed_tem_as_contagens_esperadas():
    """Truncamento na migração passaria em qualquer teste que não conte —
    mesma razão da asserção `DO $$` das próprias migrações 011/012."""
    por_anexo: dict[str, int] = {}
    for linha in SEED:
        por_anexo[linha.anexo] = por_anexo.get(linha.anexo, 0) + 1
    assert por_anexo == {"II": 8, "III": 30, "XI": 5, "X": 47}


def _consulta(prefixos_candidatos: list[str]) -> ConsultaReducaoNbs:
    candidatos = set(prefixos_candidatos)
    return ConsultaReducaoNbs(
        disponivel=True, linhas=[linha for linha in SEED if linha.prefixo in candidatos]
    )


def _resolver(nbs: str, **kwargs) -> object:
    from api.nbs import digitos_nbs, prefixos_nbs

    codigo = digitos_nbs(nbs)
    consulta = _consulta(prefixos_nbs(codigo)) if codigo else ConsultaReducaoNbs(disponivel=True)
    return resolver_item_nbs("SERVICO", nbs, consulta, **kwargs)


# AT-001 — happy path, Anexo II, sem condição --------------------------------


def test_at001_ensino_tecnico_reduz_60_por_cento_citando_o_anexo_ii_item_4():
    r = _resolver("1.2202.00.00")

    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.anexo == "II"
    assert r.item == "4"
    assert r.percentual_reducao == Decimal("0.6000")
    assert r.dispositivo_legal_ref == "LCP 214/2025, art. 129, Anexo II, item 4"


# AT-002 — prefixo parcial de subposição -------------------------------------


def test_at002_prefixo_parcial_de_1_digito_da_subposicao_casa_com_o_item_1():
    r = _resolver("1.2201.15.00")  # dentro do prefixo truncado "1.2201.1"

    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.anexo == "II" and r.item == "1"


# AT-003 — múltiplos itens do MESMO Anexo, MESMO código NBS ------------------


def test_at003_onze_itens_do_anexo_iii_compartilham_o_mesmo_codigo():
    """10 do /define (18-26, 28) + o item 29 (anomalia de dígito completada —
    ver Decisão 6 do DESIGN): o /build encontrou que a completude natural do
    dígito faltante faz o item 29 coincidir com o grupo, não ficar isolado."""
    r = _resolver("1.2301.99.00")

    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.anexo == "III" and r.item == "18"  # menor número vence
    numeros = sorted(int(n) for _, n in r.itens_correspondentes)
    assert numeros == [18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29]


# AT-004 — item sem código nunca "resolve por acidente" ----------------------


def test_at004_item_sem_codigo_do_anexo_ii_nunca_e_resolvido():
    """Item 9 do Anexo II não tem código citável — nenhum código real casa
    com ele porque ele nunca foi inserido na tabela."""
    r = _resolver("1.2209.99.00")  # código fantasiado, não publicado
    assert r.situacao is SituacaoReducaoNbs.FORA_DO_ANEXO


# AT-006 — itens sem código do Anexo X (obras teatrais) nunca resolvem ------


def test_at006_itens_sem_codigo_do_anexo_x_nunca_existem_na_tabela():
    """Itens 49-54 (obras teatrais) são célula vazia na fonte — nunca
    inseridos, mesma disciplina do item 9 do Anexo II."""
    refs = {linha.dispositivo_legal_ref for linha in SEED if linha.anexo == "X"}
    for pendente in (49, 50, 51, 52, 53, 54):
        assert not any(ref.endswith(f"item {pendente}") for ref in refs)


# AT-007 — Anexo X, condição de nacionalidade ---------------------------------


def test_at007_producao_estrangeira_sem_nacionalidade_informada_fica_na_geral():
    """Item 3 (licenciamento de obra cinematográfica) exige nacionalidade —
    sem o campo informado, a alíquota geral se aplica e a resposta declara
    o que destravaria os 60%."""
    r = _resolver("1.1103.31.00")

    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA
    assert r.percentual_reducao is None
    assert r.condicao_pendente_ref == "LCP 214/2025, art. 139, §1º c/c inciso VII"
    assert r.reducao_condicionada_disponivel is True


def test_at007_producao_nacional_declarada_ganha_60_por_cento():
    r = _resolver("1.1103.31.00", conteudo_nacional_majoritario=True)

    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.percentual_reducao == Decimal("0.6000")
    assert r.dispositivo_legal_ref == "LCP 214/2025, art. 139, Anexo X, item 3"


def test_item_22_feiras_de_negocios_nunca_exige_nacionalidade():
    """Inciso V/VI — fora do §1º, 60% incondicional dentro do Anexo X.
    "1.1806.61.00" é um código completo hipotético dentro do prefixo
    truncado "1.1806.6" publicado pela lei para o item 22."""
    r = _resolver("1.1806.61.00")
    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.percentual_reducao == Decimal("0.6000")


def test_item_40_museus_nunca_exige_nacionalidade():
    r = _resolver("1.2504.11.00")
    assert r.situacao is SituacaoReducaoNbs.APLICADA


def test_itens_de_producao_audiovisual_tem_nacionalidade_embutida_no_texto():
    """Itens 23-35 já dizem "produções nacionais" na própria descrição —
    mesmo assim exigem o campo declaratório, nunca presumido True."""
    r = _resolver("1.2501.11.00")  # item 23
    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA


def test_itens_42_a_45_nao_existem_na_tabela_nbs_chave_ncm():
    """Fotografias/quadros/gravuras/esculturas (Anexo X, itens 42-45) são
    NCM, não NBS — nunca inseridos nesta tabela (AT-005)."""
    itens_x = {linha.item for linha in SEED if linha.anexo == "X"}
    assert not ({42, 43, 44, 45} & itens_x)


# AT-008 — Anexo XI, item vetado nunca resolvido -----------------------------


def test_at008_itens_vetados_do_anexo_xi_nunca_resolvem():
    for codigo in ("1.1802.90.00", "1.1802.30.00"):  # itens 1.4 e 1.5, vetados
        r = _resolver(codigo)
        assert r.situacao is SituacaoReducaoNbs.FORA_DO_ANEXO


# AT-009 — itens "pendente de classificação" nunca resolvem ------------------


def test_at009_itens_pendentes_de_classificacao_nunca_estao_na_tabela():
    codigos_dos_itens = {linha.dispositivo_legal_ref for linha in SEED if linha.anexo == "XI"}
    for pendente in ("1.6", "1.7", "1.10", "1.11", "1.12"):
        assert not any(ref.endswith(f"item {pendente}") for ref in codigos_dos_itens)


# AT-010/AT-011/AT-012 — Anexo XI, eixo comprador ----------------------------


def test_at010_sem_comprador_informado_fica_na_aliquota_geral_mas_declara_a_condicao():
    r = _resolver("1.1501.20.00")  # item 1.1

    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA
    assert r.percentual_reducao is None
    assert r.condicao_pendente_ref == "LCP 214/2025, art. 142, I"
    assert r.reducao_condicionada_disponivel is True


def test_at011_comprador_orgao_publico_destrava_os_60_por_cento():
    r = _resolver("1.1501.20.00", comprador_tipo="ORGAO_PUBLICO")

    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.percentual_reducao == Decimal("0.6000")
    assert r.dispositivo_legal_ref == "LCP 214/2025, art. 142, Anexo XI, item 1.1"


def test_at012_entidade_cebas_sus_nunca_satisfaz_a_condicao_do_anexo_xi():
    """Diferente dos Anexos IV/V/VI: o art. 142 só nomeia órgão público —
    `ENTIDADE_CEBAS_SUS` não tem base legal aqui."""
    r = _resolver("1.1501.20.00", comprador_tipo="ENTIDADE_CEBAS_SUS")
    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA


def test_eixo_vendedor_e_independente_do_eixo_comprador():
    r = _resolver("1.1501.20.00", vendedor_capital_brasileiro_qualificado=True)
    assert r.situacao is SituacaoReducaoNbs.APLICADA
    assert r.percentual_reducao == Decimal("0.6000")


def test_eixo_vendedor_nao_se_aplica_ao_item_1_2_conservadoramente():
    """Item 1.2 (projeto/desenvolvimento de aplicativos) não recebeu
    `condicao_vendedor_ref` — decisão conservadora do /build documentada na
    migração 011: só 1.1 é inequivocamente "segurança da informação"."""
    r = _resolver("1.1502.90.00", vendedor_capital_brasileiro_qualificado=True)
    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA


# AT-015 — campo `nbs` ausente não quebra nada --------------------------------


def test_at015_item_de_servico_sem_nbs_e_nao_aplicavel():
    r = resolver_item_nbs("SERVICO", None, ConsultaReducaoNbs(disponivel=True))
    assert r.situacao is SituacaoReducaoNbs.NAO_APLICAVEL


def test_item_de_mercadoria_nunca_alcanca_a_trilha_nbs():
    r = resolver_item_nbs("MERCADORIA", "1.2202.00.00", ConsultaReducaoNbs(disponivel=True))
    assert r.situacao is SituacaoReducaoNbs.NAO_APLICAVEL


def test_consulta_indisponivel_nunca_derruba_a_requisicao():
    r = resolver_item_nbs("SERVICO", "1.2202.00.00", ConsultaReducaoNbs(disponivel=False))
    assert r.situacao is SituacaoReducaoNbs.CONSULTA_INDISPONIVEL
    assert r.avaliada is False


def test_nbs_malformado_e_nao_reconhecido():
    r = resolver_item_nbs("SERVICO", "isto-nao-e-nbs", ConsultaReducaoNbs(disponivel=True))
    assert r.situacao is SituacaoReducaoNbs.NBS_NAO_RECONHECIDO


def test_descricao_contexto_recupera_o_cabecalho_do_item_1_do_anexo_xi():
    r = _resolver("1.1501.20.00", comprador_tipo="ORGAO_PUBLICO")
    assert r.descricao_contexto == "Serviços"


@pytest.mark.parametrize("item", ["1.13", "1.14"])
def test_manutencao_militar_exige_so_comprador_nunca_vendedor(item):
    codigo = "1.2001.35.00" if item == "1.13" else "1.2001.83.00"
    r = _resolver(codigo, vendedor_capital_brasileiro_qualificado=True)
    assert r.situacao is SituacaoReducaoNbs.CONDICAO_NAO_SATISFEITA
    r_comprador = _resolver(codigo, comprador_tipo="ORGAO_PUBLICO")
    assert r_comprador.situacao is SituacaoReducaoNbs.APLICADA


def test_formatar_item_usa_grafia_canonica():
    assert formatar_item(1, 0) == "1"
    assert formatar_item(1, 1) == "1.1"
