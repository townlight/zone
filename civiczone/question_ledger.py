from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

metadata = sa.MetaData()

zone_question_ledger_records = sa.Table(
    "zone_question_ledger_records",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("zone_code", sa.String(80), nullable=False),
    sa.Column("question_text", sa.Text(), nullable=False),
    sa.Column("audience", sa.String(80), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("answer_text", sa.Text(), nullable=True),
    sa.Column("citation_payload", sa.JSON(), nullable=False),
    sa.Column("disclaimer", sa.Text(), nullable=False),
    sa.Column("escalation_reason", sa.String(255), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civiczone",
)


@dataclass(frozen=True)
class ZoneQuestionLedgerRecord:
    id: str
    zone_code: str
    question_text: str
    audience: str
    status: str
    answer_text: str | None
    citation_payload: tuple[str, ...]
    disclaimer: str
    escalation_reason: str | None
    created_at: datetime
    updated_at: datetime


class ZoneQuestionLedgerRepository:
    """SQLAlchemy-backed resident question ledger for local auditability."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civiczone": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civiczone"))
        metadata.create_all(self.engine)

    def record_answer(
        self,
        *,
        zone_code: str,
        question_text: str,
        audience: str,
        status: str,
        answer_text: str | None,
        citations: Iterable[str],
        disclaimer: str,
        escalation_reason: str | None,
    ) -> ZoneQuestionLedgerRecord:
        now = datetime.now(UTC)
        record_id = str(uuid4())
        citation_payload = list(citations)
        with self.engine.begin() as connection:
            connection.execute(
                zone_question_ledger_records.insert().values(
                    id=record_id,
                    zone_code=zone_code.strip().upper(),
                    question_text=question_text,
                    audience=audience,
                    status=status,
                    answer_text=answer_text,
                    citation_payload=citation_payload,
                    disclaimer=disclaimer,
                    escalation_reason=escalation_reason,
                    created_at=now,
                    updated_at=now,
                )
            )
        return ZoneQuestionLedgerRecord(
            id=record_id,
            zone_code=zone_code.strip().upper(),
            question_text=question_text,
            audience=audience,
            status=status,
            answer_text=answer_text,
            citation_payload=tuple(citation_payload),
            disclaimer=disclaimer,
            escalation_reason=escalation_reason,
            created_at=now,
            updated_at=now,
        )

    def list_records(self) -> tuple[ZoneQuestionLedgerRecord, ...]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(zone_question_ledger_records).order_by(
                    zone_question_ledger_records.c.created_at
                )
            ).mappings()
            return tuple(_record_from_row(dict(row)) for row in rows)


def _record_from_row(row: dict[str, object]) -> ZoneQuestionLedgerRecord:
    return ZoneQuestionLedgerRecord(
        id=str(row["id"]),
        zone_code=str(row["zone_code"]),
        question_text=str(row["question_text"]),
        audience=str(row["audience"]),
        status=str(row["status"]),
        answer_text=row["answer_text"] if row["answer_text"] is None else str(row["answer_text"]),
        citation_payload=tuple(row["citation_payload"]),
        disclaimer=str(row["disclaimer"]),
        escalation_reason=(
            row["escalation_reason"]
            if row["escalation_reason"] is None
            else str(row["escalation_reason"])
        ),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )
