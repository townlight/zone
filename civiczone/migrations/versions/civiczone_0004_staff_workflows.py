"""Create persisted staff workflow records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civiczone.migrations.guards import idempotent_create_table

revision = "civiczone_0004_staff_workflows"
down_revision = "civiczone_0003_question_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "staff_question_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zone_code", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("code_cross_references", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visibility", sa.String(80), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        schema="civiczone",
    )
    idempotent_create_table(
        "staff_ambiguity_review_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zone_code", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("source_question_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visibility", sa.String(80), nullable=False),
        schema="civiczone",
    )
    idempotent_create_table(
        "staff_flagged_answer_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zone_code", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("original_answer", sa.Text(), nullable=False),
        sa.Column("flag_reason", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("improved_answer", sa.Text(), nullable=True),
        sa.Column("improvement_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visibility", sa.String(80), nullable=False),
        schema="civiczone",
    )


def downgrade() -> None:
    op.drop_table("staff_flagged_answer_reviews", schema="civiczone")
    op.drop_table("staff_ambiguity_review_items", schema="civiczone")
    op.drop_table("staff_question_records", schema="civiczone")
