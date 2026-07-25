"""Testes do registro de fontes usado pela CLI (e portanto pelo workflow de
ingestão). Cobrem o que a CLI em si não permite testar: `typer` não instala
neste sandbox, então `construir_fonte()` foi mantida fora de `_build_cli()`
exatamente para poder ser exercitada aqui."""

import pytest

from ingestion.parser.ast_parser import parse_lei
from ingestion.parser.resolucao_parser import parse_resolucao
from ingestion.pipeline import construir_fonte
from ingestion.scraper.planalto_scraper import PlanaltoScraper
from ingestion.scraper.tcu_scraper import TCUScraper
from ingestion.storage.raw_storage import FakeInMemoryStorage


@pytest.fixture
def storage():
    return FakeInMemoryStorage()


def test_planalto_usa_scraper_html_e_parser_de_lei(storage):
    scraper, parser = construir_fonte("planalto", storage)
    assert isinstance(scraper, PlanaltoScraper)
    assert parser is parse_lei


def test_tcu_usa_scraper_pdf_e_parser_de_resolucao(storage):
    scraper, parser = construir_fonte("tcu", storage)
    assert isinstance(scraper, TCUScraper)
    assert parser is parse_resolucao


def test_fonte_desconhecida_falha_dizendo_quais_existem(storage):
    """Um typo em `--fonte` no workflow não pode virar uma ingestão silenciosa
    da fonte errada nem um traceback obscuro: a mensagem lista as válidas."""
    with pytest.raises(ValueError, match="Fonte desconhecida") as exc:
        construir_fonte("planaltoo", storage)
    assert "planalto" in str(exc.value)
    assert "tcu" in str(exc.value)


def test_timeout_e_retries_chegam_no_scraper(storage):
    """Settings.request_timeout_seconds/max_retries precisam atravessar o
    registro — se ficassem no default, a config de ambiente seria ignorada
    sem nenhum sinal."""
    for fonte in ("planalto", "tcu"):
        scraper, _ = construir_fonte(fonte, storage, timeout_seconds=99, max_retries=7)
        assert scraper._timeout_seconds == 99, fonte
        assert scraper._max_retries == 7, fonte
