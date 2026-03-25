"""Initial database schema migration.

Revision ID: 001
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(100), nullable=False),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("primary_archetype", sa.String(50), nullable=False),
        sa.Column("secondary_archetype", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("dimensions", JSONB(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("features", JSONB(), nullable=False, server_default="{}"),
        sa.Column("sybil_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("copytrade_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_wallet_profiles_address", "wallet_profiles", ["address"])
    op.create_index("ix_wallet_profiles_chain_archetype", "wallet_profiles", ["chain", "primary_archetype"])

    op.create_table(
        "analysis_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_address", sa.String(100), nullable=False),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("archetype", sa.String(50), nullable=False),
        sa.Column("dimensions", JSONB(), nullable=False, server_default="{}"),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_analysis_results_wallet_address", "analysis_results", ["wallet_address"])
    op.create_index("ix_analysis_results_created_at", "analysis_results", ["wallet_address", "created_at"])

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("analysis_results")
    op.drop_table("wallet_profiles")
