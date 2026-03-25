"""API key validation middleware."""

import hashlib

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger()

# Paths that don't require an API key
_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate X-Api-Key header for all protected routes."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Check API key before forwarding request."""
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        api_key = request.headers.get("x-api-key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "missing_api_key", "message": "X-Api-Key header required"}},
            )

        # TODO: validate key hash against DB; attach user/tier to request.state
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        request.state.api_key_hash = key_hash
        return await call_next(request)
