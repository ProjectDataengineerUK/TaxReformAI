from typing import Protocol


class RawStorage(Protocol):
    def save(self, path: str, content: bytes) -> str:
        """Salva o conteúdo e retorna a URI final (gs://... ou memory://...)."""
        ...

    def read(self, path: str) -> bytes: ...


class GCSRawStorage:
    def __init__(self, bucket_name: str, project_id: str):
        from google.cloud import storage

        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def save(self, path: str, content: bytes) -> str:
        blob = self._bucket.blob(path)
        blob.upload_from_string(content)
        return f"gs://{self._bucket.name}/{path}"

    def read(self, path: str) -> bytes:
        return self._bucket.blob(path).download_as_bytes()


class FakeInMemoryStorage:
    """Usado apenas em tests/ — evita depender de credenciais GCP reais."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def save(self, path: str, content: bytes) -> str:
        self._data[path] = content
        return f"memory://{path}"

    def read(self, path: str) -> bytes:
        return self._data[path]
