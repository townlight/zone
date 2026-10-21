"""Schema-aware idempotent Alembic helpers for CivicZone migrations."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector


def _inspector() -> Inspector:
    return sa.inspect(op.get_bind())


def idempotent_create_table(name: str, *columns: Any, **kwargs: Any) -> None:
    schema = kwargs.get("schema")
    if _inspector().has_table(name, schema=schema):
        return
    op.create_table(name, *columns, **kwargs)
