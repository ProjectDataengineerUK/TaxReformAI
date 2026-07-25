"""Parser das ementas de Soluções de Consulta da RFB (SIJUT2).

A fixture é o HTML real de uma consulta ao SIJUT2, salvo em 2026-07-25.
"""

from pathlib import Path

import pytest

from ingestion.parser.ementa_parser import (
    PREFIXO_DISPOSITIVO,
    EmentaParseError,
    extrair_ementas,
    parse_ementas,
    total_declarado,
)
from ingestion.scraper.rfb_scraper import montar_url_busca

FIXTURE = Path(__file__).parent / "fixtures" / "rfb_sijut2_resultados.html"


@pytest.fixture
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8", errors="replace")


def test_extrai_as_ementas_do_resultado_real(html):
    ementas = extrair_ementas(html)

    assert len(ementas) == 73
    assert all(e.texto for e in ementas)
    assert all(e.numero for e in ementas)


def test_dispositivo_inclui_orgao_porque_o_numero_nao_e_unico(html):
    """Cosit e cada Disit numeram em séries próprias — existem várias
    "Solução de Consulta nº 214". Sem o órgão, o point id do Qdrant (derivado
    de documento_id:dispositivo) colidiria e um ato sobrescreveria o outro."""
    ementas = extrair_ementas(html)
    numeros_214 = [e for e in ementas if e.numero == "214"]

    assert len(numeros_214) > 1, "a fixture tem mais de um ato nº 214"
    assert len({e.dispositivo for e in numeros_214}) == len(numeros_214)


def test_cabecalho_da_tabela_nao_vira_ementa(html):
    assert not any(e.numero.lower().startswith("nº do ato") for e in extrair_ementas(html))


def test_parse_produz_um_artigo_por_ato(html):
    lei = parse_ementas(html, "RFB_SC", "Soluções de Consulta", "http://x")

    assert len(lei.artigos_soltos) == 73
    assert lei.secoes == [], "ementas não têm hierarquia"


def test_citacao_nao_chama_solucao_de_consulta_de_artigo(html):
    """"Art. 6006" para uma Solução de Consulta seria citação falsa, e a
    citação é o que o produto promete como auditável."""
    from datetime import date

    from ingestion.chunking.chunker import gerar_chunks

    lei = parse_ementas(html, "RFB_SC", "Soluções de Consulta", "http://x")
    chunks = gerar_chunks(
        lei,
        esfera="FEDERAL_CBS",
        data_vigencia_inicio=date(2026, 1, 1),
        prefixo_dispositivo=PREFIXO_DISPOSITIVO,
    )

    assert len(chunks) == 73
    assert all(c.dispositivo.startswith("Solução de Consulta nº") for c in chunks)
    assert not any(c.dispositivo.startswith("Art.") for c in chunks)


def test_resultado_truncado_falha_alto_em_vez_de_ingerir_pela_metade():
    """O caso que mais preocupa: a busca do SIJUT2 casa palavras soltas e
    "reforma tributária" devolve 463 atos. Sem esta guarda, ingerir a página 1
    de 30 pareceria sucesso — o pior tipo de falha, silenciosa e plausível."""
    html = """
    <p>Total de atos localizados: 463</p>
    <table><tr><td>Tipo do ato</td><td>Nº do ato</td><td>Órgão / unidade</td>
    <td>Publicação</td><td>Ementa</td></tr>
    <tr><td>Solução de Consulta</td><td>1</td><td>Cosit</td><td>01/01/2026</td>
    <td>Assunto: alguma coisa</td></tr></table>
    """
    with pytest.raises(EmentaParseError, match="truncado"):
        parse_ementas(html, "RFB_SC", "t", "http://x")


def test_total_declarado_bate_com_o_extraido_na_fixture(html):
    assert total_declarado(html) == len(extrair_ementas(html)) == 73


def test_pagina_sem_ementas_falha_explicitamente():
    with pytest.raises(EmentaParseError, match="Nenhuma ementa"):
        parse_ementas("<html><body>nada</body></html>", "RFB_SC", "t", "http://x")


def test_url_de_busca_leva_o_tipo_de_ato_e_o_termo():
    url = montar_url_busca("Lei Complementar 214, de 2025", ano_ato="2026")

    assert "tiposAtosSelecionados=72" in url, "72 = Solução de Consulta"
    assert "termoBusca=Lei+Complementar+214" in url
    assert "ano_ato=2026" in url
