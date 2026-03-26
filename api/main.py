"""WalletDNA FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.middleware.auth import AuthMiddleware
from api.middleware.logging import LoggingMiddleware
from api.routers import archetypes, auth, batch, wallet

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan: startup and shutdown."""
    logger.info("walletdna.startup", version="0.1.0")
    yield
    logger.info("walletdna.shutdown")


app = FastAPI(
    title="WalletDNA API",
    description="On-chain personality profiling — Myers-Briggs for Wallets",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/response logging
app.add_middleware(LoggingMiddleware)

# API key authentication (applied after logging so requests are always logged)
app.add_middleware(AuthMiddleware)

# Routers
app.include_router(wallet.router, prefix="/v1")
app.include_router(batch.router, prefix="/v1")
app.include_router(archetypes.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler returning consistent error format."""
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    logger.error("unhandled_exception", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}, "request_id": request_id},
    )
