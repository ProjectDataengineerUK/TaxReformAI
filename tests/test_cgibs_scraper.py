"""Descoberta de resoluções do CGIBS — terceira fonte legal.

A fixture é a página real de https://www.cgibs.gov.br/resolucoes, salva em
2026-07-25. Testar contra o HTML real importa: os defeitos de ingestão deste
projeto (User-Agent recusado, charset não declarado, encoding corrompido)
todos passaram por revisão de código e só apareceram contra a fonte de verdade.
"""

from pathlib import Path

import pytest

from ingestion.scraper.cgibs_scraper import (
    CGIBSScraper,
    ResolucaoCGIBS,
    listar_resolucoes,
)
from ingestion.storage.raw_storage import FakeInMemoryStorage

FIXTURE = Path(__file__).parent / "fixtures" / "cgibs_resolucoes.html"


@pytest.fixture
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8", errors="replace")


def test_descobre_as_resolucoes_da_pagina_real(html):
    resolucoes = listar_resolucoes(html)

    assert len(resolucoes) == 13
    assert [r.numero for r in resolucoes] == list(range(1, 14))


def test_urls_sao_absolutas_e_apontam_para_pdf(html):
    """Os href da listagem são relativos ('/upload/arquivos/...'); baixá-los
    sem resolver contra a base falharia."""
    for resolucao in listar_resolucoes(html):
        assert resolucao.url.startswith("https://www.cgibs.gov.br/"), resolucao.numero
        assert resolucao.url.lower().endswith(".pdf"), resolucao.numero


def test_resolucao_6_e_a_que_regulamenta_o_ibs(html):
    """A nº 6 é a substantiva para o produto: 252 páginas e 617 artigos
    regulamentando o IBS, com seção de alíquotas e de split payment."""
    seis = next(r for r in listar_resolucoes(html) if r.numero == 6)

    assert "regulamenta" in seis.titulo.lower()
    assert seis.documento_id == "CGIBS_RES_6_2026"


def test_aceita_a_grafia_csibs_da_resolucao_1(html):
    """A resolução nº 1 está publicada como "CSIBS", não "CGIBS" — provavelmente
    erro de digitação na origem. Um padrão que exigisse "CGIBS" perderia
    silenciosamente o primeiro documento da série."""
    numeros = {r.numero for r in listar_resolucoes(html)}

    assert 1 in numeros


def test_links_sem_numero_identificavel_sao_ignorados_sem_quebrar():
    """Uma resolução futura com título fora do padrão não pode derrubar a
    ingestão das demais."""
    html = """
    <a href="/a/resolucao-cgibs-n-99-de-2026.pdf">Resolução CGIBS nº 99 de 2026</a>
    <a href="/a/documento-qualquer.pdf">Anexo sem número de resolução</a>
    <a href="/a/pagina.html">Resolução CGIBS nº 98 (não é PDF)</a>
    """
    resolucoes = listar_resolucoes(html)

    assert [r.numero for r in resolucoes] == [99]


def test_pagina_vazia_devolve_lista_vazia():
    assert listar_resolucoes("<html><body>sem links</body></html>") == []


def test_scraper_grava_sob_prefixo_proprio_no_storage():
    """Prefixo separado do TCU: os dois usam PdfLegalSource, e misturar as
    fontes no mesmo caminho quebraria a rastreabilidade do data lake."""
    scraper = CGIBSScraper(FakeInMemoryStorage())

    assert scraper._prefixo_storage == "cgibs"


def test_documento_id_e_estavel_por_numero():
    """O point id do Qdrant deriva de documento_id:dispositivo — se o
    documento_id oscilar, a reingestão duplica em vez de sobrescrever."""
    resolucao = ResolucaoCGIBS(numero=6, titulo="qualquer", url="https://x/y.pdf")

    assert resolucao.documento_id == "CGIBS_RES_6_2026"
