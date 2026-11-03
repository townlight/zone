from __future__ import annotations

import importlib
import os
import subprocess
import time
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]

CANONICAL_TABLES = [
    "zones",
    "overlays",
    "parcels",
    "use_categories",
    "use_rules",
    "dimensional_rules",
    "citations",
    "precedents",
    "interpretation_notes",
    "zone_questions",
]


def test_canonical_models_use_townlight_core_base_and_schema() -> None:
    models = importlib.import_module("townlight_zoning.models")
    townlight_core_db = importlib.import_module("townlight_core.db")

    assert models.Base is townlight_core_db.Base
    townlight_zoning_tables = {
        table.fullname
        for table in models.Base.metadata.tables.values()
        if table.schema == "townlight_zoning"
    }
    assert townlight_zoning_tables == {
        f"townlight_zoning.{table_name}" for table_name in CANONICAL_TABLES
    }
    for table_name in CANONICAL_TABLES:
        assert models.Base.metadata.tables[f"townlight_zoning.{table_name}"].schema == "townlight_zoning"


def test_each_canonical_table_has_foundation_columns() -> None:
    models = importlib.import_module("townlight_zoning.models")

    for table_name in CANONICAL_TABLES:
        table = models.Base.metadata.tables[f"townlight_zoning.{table_name}"]
        assert {"id", "created_at", "updated_at"} <= set(table.columns.keys())


def test_alembic_scaffold_exists_and_uses_separate_version_table() -> None:
    expected = [
        ROOT / "townlight_zoning" / "migrations" / "alembic.ini",
        ROOT / "townlight_zoning" / "migrations" / "env.py",
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0001_schema.py",
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0002_parcel_rule_lookup_records.py",
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0003_question_ledger.py",
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0004_staff_workflows.py",
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0005_geo_import.py",
    ]
    for path in expected:
        assert path.exists()

    env_text = (ROOT / "townlight_zoning" / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "townlight_core.migrations.runner" in env_text
    assert "subprocess.run" in env_text
    assert 'version_table="alembic_version_townlight_zoning"' in env_text


def test_migration_declares_all_canonical_tables() -> None:
    migration_text = (
        ROOT / "townlight_zoning" / "migrations" / "versions" / "townlight_zoning_0001_schema.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "townlight_zoning_0001"' in migration_text
    assert 'op.execute("CREATE SCHEMA IF NOT EXISTS townlight_zoning")' in migration_text
    assert "idempotent_create_table" in migration_text
    for table_name in CANONICAL_TABLES:
        assert f'"{table_name}"' in migration_text


def test_parcel_rule_lookup_records_migration_declares_runtime_tables() -> None:
    migration_text = (
        ROOT
        / "townlight_zoning"
        / "migrations"
        / "versions"
        / "townlight_zoning_0002_parcel_rule_lookup_records.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "townlight_zoning_0002"' in migration_text
    assert 'down_revision = "townlight_zoning_0001"' in migration_text
    assert '"parcel_lookup_records"' in migration_text
    assert '"use_rule_lookup_records"' in migration_text
    assert '"dimensional_rule_lookup_records"' in migration_text
    assert "postgresql.JSONB()" in migration_text


def test_staff_workflows_migration_declares_runtime_tables() -> None:
    migration_text = (
        ROOT
        / "townlight_zoning"
        / "migrations"
        / "versions"
        / "townlight_zoning_0004_staff_workflows.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "townlight_zoning_0004"' in migration_text
    assert 'down_revision = "townlight_zoning_0003"' in migration_text
    assert '"staff_question_records"' in migration_text
    assert '"staff_ambiguity_review_items"' in migration_text
    assert '"staff_flagged_answer_reviews"' in migration_text
    assert "postgresql.JSONB()" in migration_text


def test_alembic_command_upgrades_real_pgvector_database() -> None:
    db_url = os.environ.get("TOWNLIGHT_ZONING_TEST_DATABASE_URL")
    created_container = False
    container_name: str | None = None
    engine = None
    try:
        if db_url is None:
            container_name = f"townlight_zoning-m2-{uuid.uuid4().hex[:12]}"
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--name",
                    container_name,
                    "-e",
                    "POSTGRES_PASSWORD=postgres",
                    "-e",
                    "POSTGRES_USER=postgres",
                    "-e",
                    "POSTGRES_DB=townlight_zoning_test",
                    "-p",
                    "5432",
                    "-d",
                    "pgvector/pgvector:pg17",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            created_container = True
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container_name,
                    "bash",
                    "-lc",
                    "apt-get update && apt-get install -y postgresql-17-postgis-3",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            mapped = subprocess.run(
                ["docker", "port", container_name, "5432/tcp"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            port = mapped.rsplit(":", maxsplit=1)[-1]
            db_url = f"postgresql+psycopg2://postgres:postgres@localhost:{port}/townlight_zoning_test"

        engine = create_engine(db_url)

        deadline = time.monotonic() + 30
        while True:
            try:
                with engine.connect() as connection:
                    connection.execute(text("select 1"))
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)

        cfg = Config(str(ROOT / "townlight_zoning" / "migrations" / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")

        with engine.connect() as connection:
            townlight_core_revision = connection.execute(
                text("select version_num from alembic_version_townlight_core")
            ).scalar_one()
            townlight_zoning_revision = connection.execute(
                text("select version_num from alembic_version_townlight_zoning")
            ).scalar_one()
            townlight_zoning_tables = set(
                connection.execute(
                    text(
                        """
                        select table_name
                        from information_schema.tables
                        where table_schema = 'townlight_zoning'
                        """
                    )
                ).scalars()
            )

        assert townlight_core_revision == "townlight_core_0009"
        assert townlight_zoning_revision == "townlight_zoning_0006"
        assert townlight_zoning_tables == set(CANONICAL_TABLES) | {
            'question_events',
            "dimensional_rule_lookup_records",
            "geo_imports",
            "parcel_lookup_records",
            "staff_ambiguity_review_items",
            "staff_flagged_answer_reviews",
            "staff_question_records",
            "zone_question_ledger_records",
            "use_rule_lookup_records",
        }
    finally:
        if engine is not None:
            engine.dispose()
        if created_container and container_name is not None:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                check=False,
                capture_output=True,
                text=True,
            )
