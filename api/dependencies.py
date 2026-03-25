"""Shared FastAPI dependencies: DB sessions, Redis, auth."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with _session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# API Key auth (lightweight; full validation in middleware)
# ---------------------------------------------------------------------------

async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    """Require a valid X-Api-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    return x_api_key


APIKey = Annotated[str, Depends(require_api_key)]
