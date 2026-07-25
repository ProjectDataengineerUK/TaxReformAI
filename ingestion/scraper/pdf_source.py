"""Fonte legal genérica para documentos em PDF.

Extraída de `TCUScraper` quando o CGIBS entrou: as duas fontes diferiam
exclusivamente no prefixo do caminho no storage. A feature do TCU já havia
provado que `LegalSource` não exige HTML — só uma `str` de conteúdo e a URI
de storage; esta classe torna essa genericidade explícita em vez de deixá-la
implícita numa classe com nome de uma fonte só.
"""

import subprocess
import tempfile
from datetime import UTC, datetime

from ingestion.scraper.planalto_scraper import _HEADERS
from ingestion.storage.raw_storage import RawStorage


class PdfLegalSource:
    def __init__(
        self,
        storage: RawStorage,
        *,
        prefixo_storage: str,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        self._storage = storage
        self._prefixo_storage = prefixo_storage
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        pdf_bytes = self._baixar_pdf(url)

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/{self._prefixo_storage}/{documento_id}/{timestamp}.pdf"
        uri = self._storage.save(path, pdf_bytes)

        texto = self._extrair_texto(pdf_bytes)
        return texto, uri

    def _baixar_pdf(self, url: str) -> bytes:
        import httpx

        last_error: Exception | None = None
        for tentativa in range(1, self._max_retries + 1):
            try:
                # Mesmo User-Agent de navegador do Planalto: sites .gov.br
                # tendem a pendurar a conexão com UA não-navegador, sem 403 nem
                # resposta legível (ver planalto_scraper._HEADERS).
                response = httpx.get(
                    url,
                    timeout=self._timeout_seconds,
                    headers=_HEADERS,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao baixar {url} após {self._max_retries} tentativas: "
                        f"{type(last_error).__name__}: {last_error}"
                    ) from last_error
        raise RuntimeError(f"Falha ao baixar {url}")

    def _extrair_texto(self, pdf_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            try:
                resultado = subprocess.run(
                    ["pdftotext", "-layout", tmp.name, "-"],
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds,
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"pdftotext falhou ao extrair texto do PDF: {exc.stderr}"
                ) from exc
        if not resultado.stdout.strip():
            raise RuntimeError(
                "pdftotext não extraiu nenhum texto do PDF (arquivo vazio ou protegido)"
            )
        return resultado.stdout
