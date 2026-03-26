"""SQLAlchemy models for wallet profiles and analysis results."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WalletProfile(Base):
    """Persisted wallet personality profile."""

    __tablename__ = "wallet_profiles"
    __table_args__ = (UniqueConstraint("address", "chain", name="uq_wallet_profiles_address_chain"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    primary_archetype: Mapped[str] = mapped_column(String(50), nullable=False)
    secondary_archetype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sybil_flagged: Mapped[bool] = mapped_column(default=False)
    copytrade_flagged: Mapped[bool] = mapped_column(default=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class AnalysisResult(Base):
    """Raw analysis result snapshots for timeline tracking."""

    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    archetype: Mapped[str] = mapped_column(String(50), nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
