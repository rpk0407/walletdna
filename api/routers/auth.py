"""API key management endpoints."""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import DBSession
from api.models.schemas import APIKeyCreateRequest, APIKeyResponse
from api.models.user import APIKey

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_key_pair() -> tuple[str, str]:
    """Return (raw_key, sha256_hash). Raw key is shown once on creation."""
    raw = "wdna_live_" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


@router.post("/keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(body: APIKeyCreateRequest, db: DBSession) -> APIKeyResponse:
    """Create a new API key. Returns the raw key once — store it securely."""
    try:
        user_uuid = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_user_id", "message": "user_id must be a valid UUID"}})

    raw_key, key_hash = _generate_key_pair()
    key_id = uuid.uuid4()

    db.add(APIKey(
        id=key_id,
        user_id=user_uuid,
        key_hash=key_hash,
        label=body.label,
        is_active=True,
    ))
    await db.commit()

    return APIKeyResponse(key_id=str(key_id), api_key=raw_key, label=body.label)


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str, db: DBSession) -> None:
    """Revoke an API key. The key is soft-deleted (is_active=False)."""
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_key_id", "message": "key_id must be a valid UUID"}})

    stmt = select(APIKey).where(APIKey.id == key_uuid)
    key = await db.scalar(stmt)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "API key not found"}},
        )

    key.is_active = False
    await db.commit()
