import json
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ApiSettings:
    api_keys_to_tenant: dict[str, str]
    max_itens_por_requisicao: int = 100

    @classmethod
    def from_env(cls) -> "ApiSettings":
        raw = os.environ.get("API_KEYS", "{}")
        try:
            mapa = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                'API_KEYS deve ser um JSON válido: {"chave": "tenant_id"}'
            ) from exc
        return cls(api_keys_to_tenant=mapa)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings.from_env()
