"""Lógica pura da base de incidência do Imposto Seletivo — sem banco, sem HTTP.

O seed é lido da PRÓPRIA migração 013, mesmo motivo de `test_reducao_resolucao.py`:
uma segunda cópia em Python destas 6 categorias/24 prefixos divergiria em
silêncio do que o banco de produção carrega. O SQL de verdade é
`test_imposto_seletivo_db.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from api.imposto_seletivo import (
    ConsultaImpostoSeletivo,
    SituacaoImpostoSeletivo,
    resolver_item,
)

MIGRACAO = Path(__file__).resolve().parents[1] / "db" / "migrations" / "013_imposto_seletivo_incidencia.sql"
_SQL = MIGRACAO.read_text(encoding="utf-8")

_LINHA_CATEGORIA = re.compile(
    r"\((\d),\s*'((?:[^']|'')*)',\s*'(LCP 214/2025[^']*)',\s*"
    r"(NULL|'(?:[^']|'')*'),\s*(NULL|'(?:[^']|'')*')\s*\)"
)
_LINHA_PREFIXO = re.compile(
    r"\(\s*(\d+),\s*'(\d+)',\s*(TRUE|FALSE),\s*'((?:[^']|'')*)'\s*\)"
)


def _texto_ou_none(bruto: str) -> str | None:
    return None if bruto == "NULL" else bruto.strip("'")


@dataclass(frozen=True)
class _Linha:
    inciso: int
    categoria: str
    dispositivo_legal_ref: str
    condicao_embalagem_primaria_ref: str | None
    excecao_uso_ref: str | None
    prefixo: str
    excecao: bool
    texto_ncm: str


def _carregar_seed() -> list[_Linha]:
    bloco_categorias = _SQL.split("INSERT INTO imposto_seletivo_incidencia\n")[1].split(
        "ON CONFLICT DO NOTHING;"
    )[0]
    categorias = {}
    for inciso, categoria, dispositivo, condicao, excecao_uso in _LINHA_CATEGORIA.findall(
        bloco_categorias
    ):
        categorias[int(inciso)] = {
            "categoria": categoria,
            "dispositivo_legal_ref": dispositivo,
            "condicao_embalagem_primaria_ref": _texto_ou_none(condicao),
            "excecao_uso_ref": _texto_ou_none(excecao_uso),
        }

    bloco_prefixos = _SQL.split(
        "INSERT INTO imposto_seletivo_incidencia_ncm (inciso, prefixo, excecao, texto_ncm) VALUES"
    )[1].split("ON CONFLICT DO NOTHING;")[0]

    linhas = []
    for inciso, prefixo, excecao, texto_ncm in _LINHA_PREFIXO.findall(bloco_prefixos):
        info = categorias[int(inciso)]
        linhas.append(
            _Linha(
                inciso=int(inciso),
                categoria=info["categoria"],
                dispositivo_legal_ref=info["dispositivo_legal_ref"],
                condicao_embalagem_primaria_ref=info["condicao_embalagem_primaria_ref"],
                excecao_uso_ref=info["excecao_uso_ref"],
                prefixo=prefixo,
                excecao=(excecao == "TRUE"),
                texto_ncm=texto_ncm,
            )
        )
    return linhas


SEED = _carregar_seed()


def test_seed_tem_as_contagens_esperadas():
    assert len(SEED) == 24
    por_inciso: dict[int, int] = {}
    for linha in SEED:
        por_inciso[linha.inciso] = por_inciso.get(linha.inciso, 0) + 1
    assert por_inciso == {1: 7, 2: 3, 3: 4, 4: 5, 5: 1, 6: 4}


def _consulta(prefixos_candidatos: list[str]) -> ConsultaImpostoSeletivo:
    candidatos = set(prefixos_candidatos)
    return ConsultaImpostoSeletivo(
        disponivel=True, linhas=[linha for linha in SEED if linha.prefixo in candidatos]
    )


def _resolver(ncm: str, **kwargs) -> object:
    from api.ncm import digitos_ncm, prefixos_ncm

    codigo = digitos_ncm(ncm)
    consulta = _consulta(prefixos_ncm(codigo)) if codigo else ConsultaImpostoSeletivo(disponivel=True)
    return resolver_item("MERCADORIA", ncm, consulta, **kwargs)


# AT-001 — happy path, veículo -------------------------------------------------


def test_at001_veiculo_e_sujeito_ao_is_citando_o_inciso_i():
    r = _resolver("8704.21.10")

    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO
    assert r.categoria == "Veículos"
    assert r.dispositivo_legal_ref == "LCP 214/2025, art. 409, §1º, I, Anexo XVII"
    # Sempre declarada quando a categoria casa — a exceção de uso nunca é
    # verificada (Decisão 4 do DESIGN).
    assert r.excecao_uso_ref is not None


# AT-002 — bem mineral ----------------------------------------------------------


def test_at002_bem_mineral_e_sujeito_ao_is():
    r = _resolver("2601.00.00")
    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO
    assert r.categoria == "Bens minerais"
    assert r.excecao_uso_ref is None


# AT-003 — fumígeno, condição de embalagem primária ----------------------------


def test_at003_fumigeno_sem_embalagem_primaria_fica_nao_confirmado():
    r = _resolver("2402.20.00")

    assert r.situacao is SituacaoImpostoSeletivo.CONDICAO_NAO_SATISFEITA
    assert r.categoria == "Produtos fumígenos"
    assert r.condicao_embalagem_primaria_ref is not None


def test_at003_fumigeno_com_embalagem_primaria_confirmada_e_sujeito():
    r = _resolver("2402.20.00", embalagem_primaria_consumidor_final=True)
    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO
    assert r.categoria == "Produtos fumígenos"


# AT-004 — bebida açucarada, sem condição --------------------------------------


def test_at004_bebida_acucarada_nao_exige_condicao():
    r = _resolver("2202.10.00")
    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO
    assert r.condicao_embalagem_primaria_ref is None


# AT-005 — fora da base ---------------------------------------------------------


def test_at005_ncm_fora_das_categorias_nao_e_sujeito():
    r = _resolver("04051000")  # manteiga, já usado em outros testes
    assert r.situacao is SituacaoImpostoSeletivo.NAO_SUJEITO
    assert r.categoria is None


# Exceção de código — 8802.60.00 -----------------------------------------------


def test_aeronave_excluida_por_codigo_especifico_e_nao_sujeita():
    r = _resolver("8802.60.00")
    assert r.situacao is SituacaoImpostoSeletivo.NAO_SUJEITO


def test_aeronave_fora_da_excecao_e_sujeita():
    r = _resolver("8802.10.00")
    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO
    assert r.categoria == "Embarcações e aeronaves"


def test_embarcacao_com_motor_e_sujeita_via_posicao_8903():
    r = _resolver("8903.10.00")
    assert r.situacao is SituacaoImpostoSeletivo.SUJEITO


# AT-006 — categoria VII (sem código) nunca existe na tabela -------------------


def test_at006_inciso_vii_concursos_de_prognosticos_nunca_esta_no_seed():
    assert not any(linha.inciso == 7 for linha in SEED)


# AT-008 — nenhum valor monetário/percentual é modelado ------------------------


def test_at008_resolucao_nunca_tem_campo_de_valor_ou_percentual():
    import dataclasses

    from api.imposto_seletivo import ResolucaoImpostoSeletivo

    campos = {f.name for f in dataclasses.fields(ResolucaoImpostoSeletivo)}
    assert not any("percentual" in nome or "valor" in nome or "aliquota" in nome for nome in campos)


# Casos de infraestrutura -------------------------------------------------------


def test_item_de_servico_nunca_alcanca_a_trilha_do_is():
    r = resolver_item("SERVICO", "8704.21.10", ConsultaImpostoSeletivo(disponivel=True))
    assert r.situacao is SituacaoImpostoSeletivo.NAO_APLICAVEL


def test_consulta_indisponivel_nunca_derruba_a_requisicao():
    r = resolver_item("MERCADORIA", "8704.21.10", ConsultaImpostoSeletivo(disponivel=False))
    assert r.situacao is SituacaoImpostoSeletivo.CONSULTA_INDISPONIVEL
    assert r.aplicavel is False


def test_ncm_malformado_e_nao_reconhecido():
    r = resolver_item("MERCADORIA", "xx", ConsultaImpostoSeletivo(disponivel=True))
    assert r.situacao is SituacaoImpostoSeletivo.NCM_NAO_RECONHECIDO
