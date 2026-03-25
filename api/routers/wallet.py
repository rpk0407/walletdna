"""Wallet profile endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query

from api.models.schemas import (
    CompareRequest,
    CompareResponse,
    SimilarWalletsResponse,
    TimelineResponse,
    WalletProfileResponse,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/{address}/profile", response_model=WalletProfileResponse)
async def get_wallet_profile(
    address: Annotated[str, Path(description="Wallet address (Solana or EVM)")],
    chain: Annotated[str, Query(description="Chain identifier")] = "solana",
    refresh: Annotated[bool, Query(description="Force re-analysis, bypass cache")] = False,
) -> WalletProfileResponse:
    """Return the full personality profile for a wallet address."""
    # TODO: check cache, invoke agent pipeline, store result
    raise NotImplementedError


@router.get("/{address}/timeline", response_model=TimelineResponse)
async def get_wallet_timeline(
    address: Annotated[str, Path()],
    chain: Annotated[str, Query()] = "solana",
) -> TimelineResponse:
    """Return archetype evolution over time for a wallet."""
    raise NotImplementedError


@router.get("/{address}/similar", response_model=SimilarWalletsResponse)
async def get_similar_wallets(
    address: Annotated[str, Path()],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SimilarWalletsResponse:
    """Return wallets with similar behavioral profiles."""
    raise NotImplementedError


@router.post("/compare", response_model=CompareResponse)
async def compare_wallets(body: CompareRequest) -> CompareResponse:
    """Compare two wallet profiles side-by-side."""
    raise NotImplementedError
