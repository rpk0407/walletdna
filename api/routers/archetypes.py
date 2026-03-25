"""Archetype metadata and platform statistics endpoints."""

from fastapi import APIRouter

from api.models.schemas import ArchetypeListResponse, PlatformStatsResponse

router = APIRouter(tags=["archetypes"])


@router.get("/archetypes", response_model=ArchetypeListResponse)
async def list_archetypes() -> ArchetypeListResponse:
    """Return all supported archetypes with descriptions and feature weights."""
    raise NotImplementedError


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_stats() -> PlatformStatsResponse:
    """Return platform-wide statistics: wallet counts, archetype distribution."""
    raise NotImplementedError
