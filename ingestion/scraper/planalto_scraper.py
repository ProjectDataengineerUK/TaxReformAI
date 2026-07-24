from datetime import datetime, timezone
from typing import Protocol

from ingestion.storage.raw_storage import RawStorage


class LegalSource(Protocol):
    """Uma fonte legal capaz de baixar o HTML de um documento e salvá-lo via
    RawStorage. PlanaltoScraper é a primeira implementação (Decision 2 do
    DESIGN) — DOU/RFB/CONFAZ entram como novas implementações em ciclos futuros."""

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        """Retorna (html, raw_storage_uri)."""
        ...


class PlanaltoScraper:
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
                html = response.text
                break
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao baixar {url} após {self._max_retries} tentativas"
                    ) from last_error
        else:
            raise RuntimeError(f"Falha ao baixar {url}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/planalto/{documento_id}/{timestamp}.html"
        uri = self._storage.save(path, html.encode("utf-8"))
        return html, uri
