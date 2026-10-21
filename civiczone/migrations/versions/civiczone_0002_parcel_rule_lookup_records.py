"""Create persisted parcel and rule lookup records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civiczone.migrations.guards import idempotent_create_table

revision = "civiczone_0002_parcel_rules"
down_revision = "civiczone_0001_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "parcel_lookup_records",
        sa.Column("parcel_number", sa.String(120), primary_key=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("zone_code", sa.String(80), nullable=False),
        sa.Column("zone_name", sa.String(255), nullable=False),
        sa.Column("overlays", postgresql.JSONB(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civiczone",
    )
    idempotent_create_table(
        "use_rule_lookup_records",
        sa.Column("zone_code", sa.String(80), primary_key=True),
        sa.Column("use_key", sa.String(255), primary_key=True),
        sa.Column("use", sa.String(255), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("review_path", sa.String(255), nullable=False),
        sa.Column("citation", sa.String(255), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civiczone",
    )
    idempotent_create_table(
        "dimensional_rule_lookup_records",
        sa.Column("zone_code", sa.String(80), primary_key=True),
        sa.Column("rule_type", sa.String(120), primary_key=True),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("citation", sa.String(255), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civiczone",
    )


def downgrade() -> None:
    for table_name in [
        "dimensional_rule_lookup_records",
        "use_rule_lookup_records",
        "parcel_lookup_records",
    ]:
        op.drop_table(table_name, schema="civiczone")
