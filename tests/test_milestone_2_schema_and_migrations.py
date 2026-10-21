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


def test_canonical_models_use_civiccore_base_and_schema() -> None:
    models = importlib.import_module("civiczone.models")
    civiccore_db = importlib.import_module("civiccore.db")

    assert models.Base is civiccore_db.Base
    civiczone_tables = {
        table.fullname
        for table in models.Base.metadata.tables.values()
        if table.schema == "civiczone"
    }
    assert civiczone_tables == {
        f"civiczone.{table_name}" for table_name in CANONICAL_TABLES
    }
    for table_name in CANONICAL_TABLES:
        assert models.Base.metadata.tables[f"civiczone.{table_name}"].schema == "civiczone"


def test_each_canonical_table_has_foundation_columns() -> None:
    models = importlib.import_module("civiczone.models")

    for table_name in CANONICAL_TABLES:
        table = models.Base.metadata.tables[f"civiczone.{table_name}"]
        assert {"id", "created_at", "updated_at"} <= set(table.columns.keys())


def test_alembic_scaffold_exists_and_uses_separate_version_table() -> None:
    expected = [
        ROOT / "civiczone" / "migrations" / "alembic.ini",
        ROOT / "civiczone" / "migrations" / "env.py",
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0001_schema.py",
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0002_parcel_rule_lookup_records.py",
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0003_question_ledger.py",
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0004_staff_workflows.py",
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0005_geo_import.py",
    ]
    for path in expected:
        assert path.exists()

    env_text = (ROOT / "civiczone" / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "civiccore.migrations.runner" in env_text
    assert "subprocess.run" in env_text
    assert 'version_table="alembic_version_civiczone"' in env_text


def test_migration_declares_all_canonical_tables() -> None:
    migration_text = (
        ROOT / "civiczone" / "migrations" / "versions" / "civiczone_0001_schema.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "civiczone_0001_schema"' in migration_text
    assert 'op.execute("CREATE SCHEMA IF NOT EXISTS civiczone")' in migration_text
    assert "idempotent_create_table" in migration_text
    for table_name in CANONICAL_TABLES:
        assert f'"{table_name}"' in migration_text


def test_parcel_rule_lookup_records_migration_declares_runtime_tables() -> None:
    migration_text = (
        ROOT
        / "civiczone"
        / "migrations"
        / "versions"
        / "civiczone_0002_parcel_rule_lookup_records.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "civiczone_0002_parcel_rules"' in migration_text
    assert 'down_revision = "civiczone_0001_schema"' in migration_text
    assert '"parcel_lookup_records"' in migration_text
    assert '"use_rule_lookup_records"' in migration_text
    assert '"dimensional_rule_lookup_records"' in migration_text
    assert "postgresql.JSONB()" in migration_text


def test_staff_workflows_migration_declares_runtime_tables() -> None:
    migration_text = (
        ROOT
        / "civiczone"
        / "migrations"
        / "versions"
        / "civiczone_0004_staff_workflows.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "civiczone_0004_staff_workflows"' in migration_text
    assert 'down_revision = "civiczone_0003_question_ledger"' in migration_text
    assert '"staff_question_records"' in migration_text
    assert '"staff_ambiguity_review_items"' in migration_text
    assert '"staff_flagged_answer_reviews"' in migration_text
    assert "postgresql.JSONB()" in migration_text


def test_alembic_command_upgrades_real_pgvector_database() -> None:
    db_url = os.environ.get("CIVICZONE_TEST_DATABASE_URL")
    created_container = False
    container_name: str | None = None
    engine = None
    try:
        if db_url is None:
            container_name = f"civiczone-m2-{uuid.uuid4().hex[:12]}"
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
                    "POSTGRES_DB=civiczone_test",
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
            db_url = f"postgresql+psycopg2://postgres:postgres@localhost:{port}/civiczone_test"

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

        cfg = Config(str(ROOT / "civiczone" / "migrations" / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")

        with engine.connect() as connection:
            civiccore_revision = connection.execute(
                text("select version_num from alembic_version_civiccore")
            ).scalar_one()
            civiczone_revision = connection.execute(
                text("select version_num from alembic_version_civiczone")
            ).scalar_one()
            civiczone_tables = set(
                connection.execute(
                    text(
                        """
                        select table_name
                        from information_schema.tables
                        where table_schema = 'civiczone'
                        """
                    )
                ).scalars()
            )

        assert civiccore_revision == "civiccore_0003_local_task_queue"
        assert civiczone_revision == "civiczone_0006_cited_questions"
        assert civiczone_tables == set(CANONICAL_TABLES) | {
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
