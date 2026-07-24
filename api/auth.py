from fastapi import Depends, Header, HTTPException, status

from api.config import ApiSettings, get_settings


def verificar_api_key(
    x_api_key: str | None = Header(None),
    settings: ApiSettings = Depends(get_settings),
) -> str:
    tenant_id = settings.api_keys_to_tenant.get(x_api_key) if x_api_key else None
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        )
    return tenant_id
