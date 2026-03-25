"""Pydantic v2 request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class Dimensions(BaseModel):
    """Six behavioral dimension scores (0–100)."""
    speed: int = Field(ge=0, le=100)
    conviction: int = Field(ge=0, le=100)
    risk_appetite: int = Field(ge=0, le=100)
    sophistication: int = Field(ge=0, le=100)
    originality: int = Field(ge=0, le=100)
    consistency: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# Wallet profile
# ---------------------------------------------------------------------------

class WalletProfileResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    address: str
    chain: str
    primary_archetype: str
    secondary_archetype: str | None = None
    confidence: float
    dimensions: Dimensions
    summary: str
    sybil_flagged: bool
    copytrade_flagged: bool
    analyzed_at: datetime


class TimelineEntry(BaseModel):
    archetype: str
    dimensions: Dimensions
    recorded_at: datetime


class TimelineResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    address: str
    timeline: list[TimelineEntry]


class SimilarWallet(BaseModel):
    address: str
    archetype: str
    similarity_score: float


class SimilarWalletsResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    address: str
    similar: list[SimilarWallet]


class CompareRequest(BaseModel):
    address_a: str
    address_b: str
    chain: str = "solana"


class CompareResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_a: WalletProfileResponse
    wallet_b: WalletProfileResponse
    similarity_score: float


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

class BatchRequest(BaseModel):
    addresses: list[str] = Field(min_length=1, max_length=100)
    chain: str = "solana"


class BatchJobResponse(BaseModel):
    job_id: str
    status: str
    total: int


class BatchResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job: BatchJobResponse


# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------

class ArchetypeInfo(BaseModel):
    name: str
    description: str
    key_features: list[str]
    wallet_count: int


class ArchetypeListResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    archetypes: list[ArchetypeInfo]


class PlatformStatsResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_wallets_analyzed: int
    archetype_distribution: dict[str, float]
    chains_supported: list[str]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class APIKeyCreateRequest(BaseModel):
    user_id: str
    label: str | None = None


class APIKeyResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key_id: str
    api_key: str  # raw key — returned only on creation
    label: str | None = None
