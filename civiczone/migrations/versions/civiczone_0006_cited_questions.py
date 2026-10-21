from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "civiczone_0006_cited_questions"
down_revision = "civiczone_0005_geo_import"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("use_rules", "dimensional_rules"):
        op.add_column(
            table, sa.Column("code_snapshot", postgresql.JSONB(), nullable=True), schema="civiczone"
        )
        op.add_column(
            table, sa.Column("overlay_code", sa.Text(), nullable=True), schema="civiczone"
        )
        op.add_column(
            table,
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            schema="civiczone",
        )
    op.add_column(
        "zone_question_ledger_records",
        sa.Column(
            "context", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        schema="civiczone",
    )
    op.add_column(
        "zone_question_ledger_records",
        sa.Column("actor_id", sa.Text(), nullable=True),
        schema="civiczone",
    )
    op.create_table(
        "question_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="civiczone",
    )


def downgrade():
    op.drop_table("question_events", schema="civiczone")
    op.drop_column("zone_question_ledger_records", "actor_id", schema="civiczone")
    op.drop_column("zone_question_ledger_records", "context", schema="civiczone")
    for table in ("use_rules", "dimensional_rules"):
        op.drop_column(table, "is_active", schema="civiczone")
        op.drop_column(table, "overlay_code", schema="civiczone")
        op.drop_column(table, "code_snapshot", schema="civiczone")
