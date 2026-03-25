"""API key validation middleware with database lookup."""

import hashlib

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.config import settings
from api.models.user import APIKey

logger = structlog.get_logger()

_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
_PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi")

# Dedicated engine for middleware (separate from request-scoped sessions)
_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate X-Api-Key header against the api_keys table.

    On success, attaches api_key_id, user_id, and tier to request.state
    for use by rate limiter and downstream handlers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path
        if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        api_key = request.headers.get("x-api-key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "missing_api_key", "message": "X-Api-Key header required"}},
            )

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with _session_factory() as session:
            stmt = (
                select(APIKey)
                .where(APIKey.key_hash == key_hash, APIKey.is_active == True)  # noqa: E712
            )
            key_record = await session.scalar(stmt)

        if not key_record:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "invalid_api_key", "message": "API key not found or revoked"}},
            )

        # Attach identity to request state for downstream use
        request.state.api_key_id = str(key_record.id)
        request.state.user_id = str(key_record.user_id)
        request.state.tier = "free"  # TODO: join User.tier once User table is populated

        return await call_next(request)
