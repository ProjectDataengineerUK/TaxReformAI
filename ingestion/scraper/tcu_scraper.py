from ingestion.scraper.pdf_source import PdfLegalSource
from ingestion.storage.raw_storage import RawStorage


class TCUScraper(PdfLegalSource):
    """Segunda implementação de LegalSource (Decision 2 de PIPELINE_INGESTAO_LEGAL).

    Retorna texto extraído via `pdftotext`, não HTML — `LegalSource.fetch()`
    nunca exigiu HTML especificamente, só uma `str` de conteúdo + a URI de
    storage (Decision 1 de INGESTAO_TCU_E_ETL_AIRFLOW).

    A mecânica de download e extração vive em `PdfLegalSource` desde que o
    CGIBS entrou como terceira fonte: as duas diferiam só no prefixo do
    caminho no storage.
    """

    def __init__(
        self,
        storage: RawStorage,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        super().__init__(
            storage,
            prefixo_storage="tcu",
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
