"""Comprehensive tests for WalletDNA FastAPI endpoints.

Tests are isolated — all external dependencies (pipeline, Redis, DB) are mocked.
Uses app.dependency_overrides for FastAPI DI. Run with:  pytest -x -q tests/
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_db
from api.main import app

# ──────────────────────────────────────────────────────────────────────────────
# Mock data
# ──────────────────────────────────────────────────────────────────────────────

_MOCK_PROFILE_STATE = {
    "wallet_address": "TestWallet123",
    "chain": "solana",
    "raw_transactions": [],
    "normalized_transactions": [],
    "features": {"txn_frequency_daily": 5.0, "hold_duration_avg": 24.0},
    "graph_features": {"cluster_size": 1.0},
    "activity_grid": [[i % 5 for _ in range(24)] for i in range(7)],
    "cluster_id": 1,
    "archetype_scores": {"sniper": 0.7, "degen": 0.2, "conviction_holder": 0.1},
    "sybil_data": {"is_sybil": False, "sybil_probability": 0.05, "cluster_size": 1,
                   "related_wallets": [], "contract_interaction_similarity": 0.0},
    "copytrade_data": {"is_follower": False, "whale_address": None,
                       "temporal_lag_avg_h": 0.0, "temporal_lag_std_h": 0.0,
                       "token_overlap_jaccard": 0.0, "granger_pvalue": 1.0,
                       "shared_trade_count": 0},
    "primary_archetype": "sniper",
    "secondary_archetype": "degen",
    "dimensions": {"speed": 85, "conviction": 30, "risk_appetite": 70,
                   "sophistication": 55, "originality": 60, "consistency": 45},
    "summary": "A fast-moving sniper with high entry speed.",
    "confidence": 0.82,
    "error": None,
}


def _make_mock_wallet_profile_db(**overrides):
    """Create a mock WalletProfile ORM object."""
    defaults = dict(
        address="TestWallet123",
        chain="solana",
        primary_archetype="sniper",
        secondary_archetype="degen",
        confidence=0.82,
        dimensions={"speed": 85, "conviction": 30, "risk_appetite": 70,
                     "sophistication": 55, "originality": 60, "consistency": 45},
        summary="A fast-moving sniper with high entry speed.",
        features={
            "txn_frequency_daily": 5.0,
            "_activity_grid": [[i % 5 for _ in range(24)] for i in range(7)],
        },
        sybil_flagged=False,
        copytrade_flagged=False,
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Create a mock async DB session and register it as a FastAPI override."""
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)

    # For execute().all() and execute().scalars().all() patterns
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[])
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    session.execute = AsyncMock(return_value=mock_result)

    session.add = MagicMock()
    session.commit = AsyncMock()

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_redis():
    """Mock the Redis client used by cache and rate_limiter."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)

    pipe_mock = AsyncMock()
    pipe_mock.execute = AsyncMock(return_value=[1, 1])
    pipe_mock.lpush = MagicMock(return_value=pipe_mock)
    mock.pipeline = MagicMock(return_value=pipe_mock)

    with patch("api.services.cache._redis", mock), \
         patch("api.services.cache.get_redis", return_value=mock), \
         patch("api.routers.batch.get_redis", return_value=mock):
        yield mock


@pytest.fixture
def mock_pipeline():
    """Mock the LangGraph analysis pipeline."""
    with patch("api.routers.wallet.analyze_wallet", new_callable=AsyncMock) as m:
        m.return_value = _MOCK_PROFILE_STATE
        yield m


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ──────────────────────────────────────────────────────────────────────────────
# Archetypes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archetypes_list(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /v1/archetypes returns all 6 archetypes."""
    resp = await client.get("/v1/archetypes")
    assert resp.status_code == 200
    data = resp.json()
    assert "archetypes" in data
    assert len(data["archetypes"]) == 6

    names = {a["name"] for a in data["archetypes"]}
    assert names == {"sniper", "conviction_holder", "degen", "researcher", "follower", "extractor"}


@pytest.mark.asyncio
async def test_archetypes_have_descriptions(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Each archetype has non-empty description and key_features."""
    resp = await client.get("/v1/archetypes")
    assert resp.status_code == 200
    for arch in resp.json()["archetypes"]:
        assert arch["description"], f"Empty description for {arch['name']}"
        assert arch["key_features"], f"Empty key_features for {arch['name']}"


@pytest.mark.asyncio
async def test_platform_stats(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /v1/stats returns platform statistics."""
    mock_db_session.scalar = AsyncMock(return_value=0)
    resp = await client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_wallets_analyzed" in data
    assert "chains_supported" in data
    assert set(data["chains_supported"]) == {"solana", "ethereum", "base", "arbitrum"}


# ──────────────────────────────────────────────────────────────────────────────
# Wallet profile
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wallet_profile_calls_pipeline(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
    mock_pipeline: AsyncMock,
) -> None:
    """GET /v1/wallet/{address}/profile triggers pipeline on cache miss."""
    resp = await client.get("/v1/wallet/TestWallet123/profile?chain=solana")
    assert resp.status_code == 200
    mock_pipeline.assert_awaited_once_with("TestWallet123", "solana")


@pytest.mark.asyncio
async def test_wallet_profile_response_schema(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
    mock_pipeline: AsyncMock,
) -> None:
    """Profile response has all required fields with correct types."""
    resp = await client.get("/v1/wallet/TestWallet123/profile")
    assert resp.status_code == 200
    data = resp.json()

    assert data["primary_archetype"] == "sniper"
    assert data["secondary_archetype"] == "degen"
    assert data["confidence"] == pytest.approx(0.82, rel=0.01)
    assert "request_id" in data
    assert "analyzed_at" in data

    dims = data["dimensions"]
    for key in ("speed", "conviction", "risk_appetite", "sophistication", "originality", "consistency"):
        assert key in dims, f"Missing dimension: {key}"
        assert 0 <= dims[key] <= 100, f"Dimension {key}={dims[key]} out of range"


@pytest.mark.asyncio
async def test_wallet_profile_cache_hit(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
    mock_pipeline: AsyncMock,
) -> None:
    """Cache hit bypasses pipeline entirely."""
    cached = {
        "request_id": str(uuid.uuid4()),
        "address": "TestWallet123",
        "chain": "solana",
        "primary_archetype": "researcher",
        "secondary_archetype": None,
        "confidence": 0.9,
        "dimensions": {"speed": 20, "conviction": 80, "risk_appetite": 30,
                       "sophistication": 95, "originality": 85, "consistency": 70},
        "summary": "Cached researcher",
        "sybil_flagged": False,
        "copytrade_flagged": False,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_redis.get = AsyncMock(return_value=json.dumps(cached))

    resp = await client.get("/v1/wallet/TestWallet123/profile")
    assert resp.status_code == 200
    mock_pipeline.assert_not_awaited()
    assert resp.json()["primary_archetype"] == "researcher"


@pytest.mark.asyncio
async def test_wallet_profile_refresh_bypasses_cache(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
    mock_pipeline: AsyncMock,
) -> None:
    """refresh=true forces pipeline even if cache has data."""
    cached = {
        "request_id": str(uuid.uuid4()),
        "address": "TestWallet123", "chain": "solana",
        "primary_archetype": "researcher", "secondary_archetype": None,
        "confidence": 0.9,
        "dimensions": {"speed": 20, "conviction": 80, "risk_appetite": 30,
                       "sophistication": 95, "originality": 85, "consistency": 70},
        "summary": "Cached", "sybil_flagged": False, "copytrade_flagged": False,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_redis.get = AsyncMock(return_value=json.dumps(cached))

    resp = await client.get("/v1/wallet/TestWallet123/profile?refresh=true")
    assert resp.status_code == 200
    mock_pipeline.assert_awaited_once()
    assert resp.json()["primary_archetype"] == "sniper"  # from pipeline, not cache


# ──────────────────────────────────────────────────────────────────────────────
# Activity heatmap
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_not_found(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /activity returns 404 when wallet not in DB."""
    mock_db_session.scalar = AsyncMock(return_value=None)
    resp = await client.get("/v1/wallet/UnknownWallet/activity")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_activity_returns_168_cells(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Activity response has 7×24 = 168 cells with valid intensity."""
    mock_db_session.scalar = AsyncMock(return_value=_make_mock_wallet_profile_db())

    resp = await client.get("/v1/wallet/TestWallet123/activity")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["cells"]) == 168
    assert "peak_hour" in data
    assert "peak_day" in data
    assert data["total_txns"] > 0

    for cell in data["cells"]:
        assert 0.0 <= cell["intensity"] <= 1.0
        assert 0 <= cell["day"] <= 6
        assert 0 <= cell["hour"] <= 23


# ──────────────────────────────────────────────────────────────────────────────
# Timeline
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeline_empty(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /timeline returns empty list for wallet with no snapshots."""
    resp = await client.get("/v1/wallet/TestWallet123/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"] == "TestWallet123"
    assert data["timeline"] == []


# ──────────────────────────────────────────────────────────────────────────────
# Batch
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_submit(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """POST /v1/batch returns a job_id and queued status."""
    resp = await client.post(
        "/v1/batch",
        json={"addresses": ["Wallet1", "Wallet2", "Wallet3"], "chain": "solana"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["job"]["status"] == "queued"
    assert data["job"]["total"] == 3
    assert len(data["job"]["job_id"]) == 36  # UUID


@pytest.mark.asyncio
async def test_batch_submit_validation(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """POST /v1/batch rejects empty address list."""
    resp = await client.post("/v1/batch", json={"addresses": [], "chain": "solana"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_status_not_found(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /v1/batch/{id} returns 404 for unknown job."""
    mock_redis.get = AsyncMock(return_value=None)
    resp = await client.get(f"/v1/batch/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_status_found(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """GET /v1/batch/{id} returns correct status for known job."""
    job_id = str(uuid.uuid4())
    meta = json.dumps({"job_id": job_id, "status": "processing", "total": 5,
                       "completed": 3, "failed": 0})
    mock_redis.get = AsyncMock(return_value=meta)

    resp = await client.get(f"/v1/batch/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["total"] == 5


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_api_key(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """POST /v1/auth/keys creates a key with wdna_live_ prefix."""
    resp = await client.post(
        "/v1/auth/keys",
        json={"user_id": str(uuid.uuid4()), "label": "test key"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["api_key"].startswith("wdna_live_")
    assert "key_id" in data


@pytest.mark.asyncio
async def test_create_api_key_missing_user_id(
    client: AsyncClient, mock_db_session: AsyncMock, mock_redis: AsyncMock
) -> None:
    """POST /v1/auth/keys with missing user_id returns 422."""
    resp = await client.post("/v1/auth/keys", json={"label": "test"})
    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insufficient_data_returns_422(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """insufficient_data error returns 422."""
    error_state = {**_MOCK_PROFILE_STATE, "error": "insufficient_data: only 3 txns"}
    with patch("api.routers.wallet.analyze_wallet", new_callable=AsyncMock,
               return_value=error_state):
        resp = await client.get("/v1/wallet/SmallWallet/profile")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pipeline_error_returns_500(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Generic pipeline error returns 500."""
    error_state = {**_MOCK_PROFILE_STATE, "error": "ingest_failed: network timeout"}
    with patch("api.routers.wallet.analyze_wallet", new_callable=AsyncMock,
               return_value=error_state):
        resp = await client.get("/v1/wallet/BrokenWallet/profile")
    assert resp.status_code == 500
    data = resp.json()
    assert "error" in data.get("detail", {})
