"""geo import snapshot support

Revision ID: townlight_zoning_0005_geo_import
Revises: townlight_zoning_0004_staff_workflows
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "townlight_zoning_0005"
down_revision = "townlight_zoning_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    for table in ("zones", "overlays", "parcels"):
        op.execute(
            f"ALTER TABLE townlight_zoning.{table} "
            f"ADD COLUMN IF NOT EXISTS geom geography(MultiPolygon, 4326)"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_townlight_zoning_{table}_geom_gist "
            f"ON townlight_zoning.{table} USING GIST (geom)"
        )

    op.add_column(
        "overlays",
        sa.Column("jurisdiction", sa.Text(), nullable=True),
        schema="townlight_zoning",
    )
    op.add_column(
        "parcels",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        schema="townlight_zoning",
    )

    op.create_table(
        "geo_imports",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("source_date", sa.Date(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.UniqueConstraint(
            "jurisdiction",
            "source_id",
            "version",
            name="uq_townlight_zoning_geo_imports_identity",
        ),
        schema="townlight_zoning",
    )

    op.add_column(
        "parcels",
        sa.Column(
            "dataset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("townlight_zoning.geo_imports.id"),
            nullable=True,
        ),
        schema="townlight_zoning",
    )

    for table in ("zones", "overlays"):
        op.add_column(
            table,
            sa.Column(
                "source_payload",
                JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            schema="townlight_zoning",
        )


def downgrade() -> None:
    for table in ("zones", "overlays"):
        op.drop_column(table, "source_payload", schema="townlight_zoning")

    op.drop_column("parcels", "dataset_id", schema="townlight_zoning")
    op.drop_table("geo_imports", schema="townlight_zoning")

    for table in ("zones", "overlays", "parcels"):
        op.execute(f"DROP INDEX IF EXISTS townlight_zoning.ix_townlight_zoning_{table}_geom_gist")

    op.drop_column("parcels", "is_active", schema="townlight_zoning")
    op.drop_column("overlays", "jurisdiction", schema="townlight_zoning")

    for table in ("zones", "overlays", "parcels"):
        op.execute(f"ALTER TABLE townlight_zoning.{table} DROP COLUMN IF EXISTS geom")

    # PostGIS is shared infrastructure and is intentionally not dropped here.
