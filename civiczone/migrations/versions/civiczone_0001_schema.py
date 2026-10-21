"""Create CivicZone canonical schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civiczone.migrations.guards import idempotent_create_table

revision = "civiczone_0001_schema"
down_revision = None
branch_labels = None
depends_on = None


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS civiczone")

    idempotent_create_table("zones", _id_column(), sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("jurisdiction", sa.String(255), nullable=False), sa.Column("source_section_ref", sa.String(255), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), *_timestamps(), schema="civiczone")
    idempotent_create_table("overlays", _id_column(), sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("source_section_ref", sa.String(255), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), *_timestamps(), schema="civiczone")
    idempotent_create_table("parcels", _id_column(), sa.Column("parcel_number", sa.String(120), nullable=False), sa.Column("address", sa.String(500), nullable=False), sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("overlay_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), sa.Column("geometry_ref", sa.Text(), nullable=True), sa.Column("source_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), *_timestamps(), sa.ForeignKeyConstraint(["zone_id"], ["civiczone.zones.id"]), schema="civiczone")
    idempotent_create_table("use_categories", _id_column(), sa.Column("code", sa.String(120), nullable=False), sa.Column("label", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), *_timestamps(), schema="civiczone")
    idempotent_create_table("use_rules", _id_column(), sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("use_category_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(80), nullable=False), sa.Column("review_path", sa.String(255), nullable=True), sa.Column("source_section_ref", sa.String(255), nullable=True), sa.Column("conditions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), *_timestamps(), sa.ForeignKeyConstraint(["zone_id"], ["civiczone.zones.id"]), sa.ForeignKeyConstraint(["use_category_id"], ["civiczone.use_categories.id"]), schema="civiczone")
    idempotent_create_table("dimensional_rules", _id_column(), sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("rule_type", sa.String(120), nullable=False), sa.Column("value_text", sa.String(255), nullable=False), sa.Column("source_section_ref", sa.String(255), nullable=True), sa.Column("applies_to", sa.String(255), nullable=True), *_timestamps(), sa.ForeignKeyConstraint(["zone_id"], ["civiczone.zones.id"]), schema="civiczone")
    idempotent_create_table("citations", _id_column(), sa.Column("source_section_ref", sa.String(255), nullable=False), sa.Column("citation_text", sa.String(500), nullable=False), sa.Column("url", sa.Text(), nullable=True), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True), *_timestamps(), schema="civiczone")
    idempotent_create_table("precedents", _id_column(), sa.Column("title", sa.String(500), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("visibility", sa.String(80), nullable=False), sa.Column("source_ref", sa.String(255), nullable=True), sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), *_timestamps(), schema="civiczone")
    idempotent_create_table("interpretation_notes", _id_column(), sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("note_text", sa.Text(), nullable=False), sa.Column("visibility", sa.String(80), nullable=False), sa.Column("status", sa.String(80), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["zone_id"], ["civiczone.zones.id"]), schema="civiczone")
    idempotent_create_table("zone_questions", _id_column(), sa.Column("question_text", sa.Text(), nullable=False), sa.Column("audience", sa.String(80), nullable=False), sa.Column("status", sa.String(80), nullable=False), sa.Column("answer_text", sa.Text(), nullable=True), sa.Column("citation_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), sa.Column("escalation_reason", sa.String(255), nullable=True), *_timestamps(), schema="civiczone")


def downgrade() -> None:
    for table_name in [
        "zone_questions",
        "interpretation_notes",
        "precedents",
        "citations",
        "dimensional_rules",
        "use_rules",
        "use_categories",
        "parcels",
        "overlays",
        "zones",
    ]:
        op.drop_table(table_name, schema="civiczone")
