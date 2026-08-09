"""Authentication and authorization dependencies."""

from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Verify API Key if configured in environment settings."""
    # If API key setting is empty or disabled, allow requests
    api_key_required = getattr(settings, "API_KEY_REQUIRED", False)
    expected_key = getattr(settings, "API_KEY", "")

    if api_key_required and expected_key:
        if not x_api_key or x_api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header.",
            )
    return x_api_key
