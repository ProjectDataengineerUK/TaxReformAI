import subprocess
from pathlib import Path

import pytest

from ingestion.scraper.tcu_scraper import TCUScraper
from ingestion.storage.raw_storage import FakeInMemoryStorage

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "resolucao_tcu_sample.pdf"

# Nota de escopo: assim como PlanaltoScraper (feature anterior, sem teste
# unitário próprio — só via FakeLegalSource em test_pipeline_integration.py),
# a chamada HTTP real de TCUScraper.fetch() não é mockada aqui. O que estes
# testes validam é a lógica nova desta feature: extração de texto via
# `pdftotext` a partir de bytes de PDF reais (Decision 2 do DESIGN).


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_at001_extrai_texto_real_do_pdf_via_pdftotext(pdf_bytes):
    scraper = TCUScraper(storage=FakeInMemoryStorage())
    texto = scraper._extrair_texto(pdf_bytes)
    assert "RESOLUÇÃO - TCU Nº 388" in texto
    assert "Art. 1" in texto
    assert "Art. 16" in texto


def test_at002_pdf_corrompido_levanta_erro_claro():
    scraper = TCUScraper(storage=FakeInMemoryStorage())
    with pytest.raises(RuntimeError):
        scraper._extrair_texto(b"isto nao e um pdf valido")


def test_fetch_salva_pdf_bruto_no_storage_e_retorna_texto(pdf_bytes, monkeypatch):
    storage = FakeInMemoryStorage()
    scraper = TCUScraper(storage=storage)

    monkeypatch.setattr(scraper, "_baixar_pdf", lambda url: pdf_bytes)

    texto, uri = scraper.fetch(url="https://x/resolucao.pdf", documento_id="TCU_RES_388_2026")

    assert "Art. 1" in texto
    assert uri.startswith("memory://raw/tcu/TCU_RES_388_2026/")
    assert storage.read(uri.removeprefix("memory://")) == pdf_bytes


def test_pdftotext_binario_de_sistema_disponivel():
    """Confirma a premissa da Decision 2 do DESIGN: poppler-utils presente."""
    resultado = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=False)
    assert resultado.returncode == 0
