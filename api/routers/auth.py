"""API key management endpoints."""

from fastapi import APIRouter

from api.models.schemas import APIKeyCreateRequest, APIKeyResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/keys", response_model=APIKeyResponse)
async def create_api_key(body: APIKeyCreateRequest) -> APIKeyResponse:
    """Create a new API key for a user."""
    raise NotImplementedError


@router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str) -> dict[str, str]:
    """Revoke an existing API key."""
    raise NotImplementedError
