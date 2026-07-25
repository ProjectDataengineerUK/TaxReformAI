from datetime import UTC, datetime
from typing import Protocol

from ingestion.storage.raw_storage import RawStorage

# O Planalto não responde a User-Agent não-navegador: a requisição fica pendurada
# até estourar o timeout, e não devolve 403 nem nada legível. A primeira ingestão
# real morreu assim, com "Falha ao baixar ... após 3 tentativas" e nenhuma pista.
# Reproduzido fora do CI:
#   curl -A "TaxReformAI-Ingestion/0.1" ...  -> timeout após 30s, 0 bytes
#   curl -A "Mozilla/5.0 ... Chrome/120"  ...  -> 301 -> 200, 5,4 MB
# Não há autenticação, paywall nem robots proibindo: é legislação pública, o
# mesmo documento que o site entrega a qualquer navegador. O UA de navegador é
# só compatibilidade com um servidor antigo (o HTML se anuncia como FrontPage 6).
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


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
                    headers=_HEADERS,
                    follow_redirects=True,
                )
                response.raise_for_status()
                html = response.text
                break
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao baixar {url} após {self._max_retries} tentativas: "
                        f"{type(last_error).__name__}: {last_error}"
                    ) from last_error
        else:
            raise RuntimeError(f"Falha ao baixar {url}")

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/planalto/{documento_id}/{timestamp}.html"
        uri = self._storage.save(path, html.encode("utf-8"))
        return html, uri
