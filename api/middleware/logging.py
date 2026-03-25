"""Structured request/response logging middleware."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Attach request_id and log each request/response pair."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Log request metadata and response status."""
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        log = logger.bind(request_id=request_id, method=request.method, path=request.url.path)
        log.info("request.received")

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        log.info(
            "request.completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        response.headers["x-request-id"] = request_id
        return response
