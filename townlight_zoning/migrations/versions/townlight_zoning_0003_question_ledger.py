"""Create persisted resident question ledger records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from townlight_zoning.migrations.guards import idempotent_create_table

revision = "townlight_zoning_0003"
down_revision = "townlight_zoning_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "zone_question_ledger_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zone_code", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(80), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("citation_payload", postgresql.JSONB(), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("escalation_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="townlight_zoning",
    )


def downgrade() -> None:
    op.drop_table("zone_question_ledger_records", schema="townlight_zoning")
