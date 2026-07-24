import subprocess
import tempfile
from datetime import datetime, timezone

from ingestion.storage.raw_storage import RawStorage


class TCUScraper:
    """Segunda implementação de LegalSource (Decision 2 de PIPELINE_INGESTAO_LEGAL).

    Retorna texto extraído via `pdftotext`, não HTML — `LegalSource.fetch()`
    nunca exigiu HTML especificamente, só uma `str` de conteúdo + a URI de
    storage (Decision 1 de INGESTAO_TCU_E_ETL_AIRFLOW)."""

    def __init__(
        self,
        storage: RawStorage,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        self._storage = storage
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        pdf_bytes = self._baixar_pdf(url)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/tcu/{documento_id}/{timestamp}.pdf"
        uri = self._storage.save(path, pdf_bytes)

        texto = self._extrair_texto(pdf_bytes)
        return texto, uri

    def _baixar_pdf(self, url: str) -> bytes:
        import httpx

        last_error: Exception | None = None
        for tentativa in range(1, self._max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    timeout=self._timeout_seconds,
                    headers={"User-Agent": "TaxReformAI-Ingestion/0.1 (uso publico, sem PII)"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao baixar {url} após {self._max_retries} tentativas"
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
            raise RuntimeError("pdftotext não extraiu nenhum texto do PDF (arquivo vazio ou protegido)")
        return resultado.stdout
