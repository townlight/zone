from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiczone.qa import ZoneAnswer, answer_zoning_question
from civiczone.rule_lookup import DISCLAIMER

STAFF_VISIBILITY = "staff_only"
OPEN_QUEUE_STATUSES = {"open", "in_review"}
RESOLVED_QUEUE_STATUSES = {"resolved", "closed"}
QUEUE_STATUSES = OPEN_QUEUE_STATUSES | RESOLVED_QUEUE_STATUSES


metadata = sa.MetaData()

staff_question_records = sa.Table(
    "staff_question_records",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("zone_code", sa.String(80), nullable=False),
    sa.Column("question_text", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("answer_text", sa.Text(), nullable=False),
    sa.Column("citations", sa.JSON(), nullable=False),
    sa.Column("code_cross_references", sa.JSON(), nullable=False),
    sa.Column("created_by", sa.String(255), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("disclaimer", sa.Text(), nullable=False),
    schema="civiczone",
)

staff_ambiguity_review_items = sa.Table(
    "staff_ambiguity_review_items",
    metadata,
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

staff_flagged_answer_reviews = sa.Table(
    "staff_flagged_answer_reviews",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("zone_code", sa.String(80), nullable=False),
    sa.Column("question_text", sa.Text(), nullable=False),
    sa.Column("original_answer", sa.Text(), nullable=False),
    sa.Column("flag_reason", sa.Text(), nullable=False),
    sa.Column("citations", sa.JSON(), nullable=False),
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


@dataclass(frozen=True)
class CodeCrossReference:
    citation: str
    source: str
    relevance: str


@dataclass(frozen=True)
class StaffQuestionRecord:
    id: str
    zone_code: str
    question_text: str
    status: str
    answer_text: str
    citations: tuple[str, ...]
    code_cross_references: tuple[CodeCrossReference, ...]
    created_by: str
    created_at: datetime
    visibility: str = STAFF_VISIBILITY
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class AmbiguityReviewItem:
    id: str
    zone_code: str
    question_text: str
    reason: str
    status: str
    assigned_to: str | None
    resolution: str | None
    source_question_id: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    visibility: str = STAFF_VISIBILITY


@dataclass(frozen=True)
class HighVolumeQuestion:
    zone_code: str
    question_text: str
    count: int
    statuses: tuple[str, ...]
    latest_question_id: str


@dataclass(frozen=True)
class StaffQuestionAnalytics:
    total_questions: int
    by_status: dict[str, int]
    high_volume_questions: tuple[HighVolumeQuestion, ...]
    generated_at: datetime
    visibility: str = STAFF_VISIBILITY


@dataclass(frozen=True)
class StaffReportOutline:
    id: str
    title: str
    sections: tuple[dict[str, object], ...]
    source_question_ids: tuple[str, ...]
    source_queue_item_ids: tuple[str, ...]
    created_by: str
    created_at: datetime
    visibility: str = STAFF_VISIBILITY
    disclaimer: str = "Draft staff outline only; verify citations before publication."


@dataclass(frozen=True)
class FlaggedAnswerReview:
    id: str
    zone_code: str
    question_text: str
    original_answer: str
    flag_reason: str
    citations: tuple[str, ...]
    status: str
    improved_answer: str | None
    improvement_notes: str | None
    reviewed_by: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    visibility: str = STAFF_VISIBILITY


class StaffWorkflowStore:
    """Staff workflow data store with optional SQLAlchemy-backed durability."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        self._questions: dict[str, StaffQuestionRecord] = {}
        self._queue: dict[str, AmbiguityReviewItem] = {}
        self._flagged_answers: dict[str, FlaggedAnswerReview] = {}
        self.engine: Engine | None = None
        if db_url is not None or engine is not None:
            base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
            if base_engine.dialect.name == "sqlite":
                self.engine = base_engine.execution_options(schema_translate_map={"civiczone": None})
            else:
                self.engine = base_engine
                with self.engine.begin() as connection:
                    connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civiczone"))
            metadata.create_all(self.engine)
            self._hydrate()

    def answer_planner_question(
        self,
        *,
        zone_code: str,
        question_text: str,
        created_by: str,
    ) -> StaffQuestionRecord:
        answer = answer_zoning_question(zone_code=zone_code, question=question_text)
        record = StaffQuestionRecord(
            id=str(uuid4()),
            zone_code=zone_code.strip().upper(),
            question_text=question_text,
            status=answer.status,
            answer_text=answer.answer,
            citations=tuple(answer.citations),
            code_cross_references=_cross_references_from_answer(answer),
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._questions[record.id] = record
        self._persist_question(record)
        if answer.status in {"escalate", "refused"}:
            self.create_queue_item(
                zone_code=record.zone_code,
                question_text=record.question_text,
                reason=answer.next_step,
                created_by=created_by,
                source_question_id=record.id,
            )
        return record

    def create_queue_item(
        self,
        *,
        zone_code: str,
        question_text: str,
        reason: str,
        created_by: str,
        source_question_id: str | None = None,
    ) -> AmbiguityReviewItem:
        now = datetime.now(UTC)
        item = AmbiguityReviewItem(
            id=str(uuid4()),
            zone_code=zone_code.strip().upper(),
            question_text=question_text,
            reason=reason,
            status="open",
            assigned_to=None,
            resolution=None,
            source_question_id=source_question_id,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._queue[item.id] = item
        self._persist_queue_item(item)
        return item

    def list_queue_items(self, *, status: str | None = None) -> tuple[AmbiguityReviewItem, ...]:
        items = tuple(sorted(self._queue.values(), key=lambda item: item.created_at))
        if status is None:
            return items
        return tuple(item for item in items if item.status == status)

    def update_queue_item(
        self,
        *,
        item_id: str,
        status: str,
        assigned_to: str | None,
        resolution: str | None,
    ) -> AmbiguityReviewItem | None:
        if status not in QUEUE_STATUSES:
            raise ValueError("status must be one of: closed, in_review, open, resolved.")
        current = self._queue.get(item_id)
        if current is None:
            return None
        if status in RESOLVED_QUEUE_STATUSES and not resolution:
            raise ValueError("resolution is required when resolving or closing a queue item.")
        updated = AmbiguityReviewItem(
            id=current.id,
            zone_code=current.zone_code,
            question_text=current.question_text,
            reason=current.reason,
            status=status,
            assigned_to=assigned_to if assigned_to is not None else current.assigned_to,
            resolution=resolution if resolution is not None else current.resolution,
            source_question_id=current.source_question_id,
            created_by=current.created_by,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
        )
        self._queue[item_id] = updated
        self._persist_queue_item(updated)
        return updated

    def analytics(self, *, high_volume_threshold: int = 2) -> StaffQuestionAnalytics:
        status_counts = Counter(record.status for record in self._questions.values())
        grouped: dict[tuple[str, str], list[StaffQuestionRecord]] = {}
        for record in self._questions.values():
            key = (record.zone_code, _normalize_question(record.question_text))
            grouped.setdefault(key, []).append(record)

        high_volume: list[HighVolumeQuestion] = []
        for records in grouped.values():
            if len(records) < high_volume_threshold:
                continue
            latest = max(records, key=lambda record: record.created_at)
            high_volume.append(
                HighVolumeQuestion(
                    zone_code=latest.zone_code,
                    question_text=latest.question_text,
                    count=len(records),
                    statuses=tuple(sorted({record.status for record in records})),
                    latest_question_id=latest.id,
                )
            )

        return StaffQuestionAnalytics(
            total_questions=len(self._questions),
            by_status=dict(sorted(status_counts.items())),
            high_volume_questions=tuple(
                sorted(high_volume, key=lambda question: (-question.count, question.question_text))
            ),
            generated_at=datetime.now(UTC),
        )

    def draft_report_outline(
        self,
        *,
        title: str,
        question_ids: Iterable[str],
        queue_item_ids: Iterable[str],
        created_by: str,
    ) -> StaffReportOutline:
        selected_questions = tuple(
            self._questions[question_id]
            for question_id in question_ids
            if question_id in self._questions
        )
        selected_queue_items = tuple(
            self._queue[item_id] for item_id in queue_item_ids if item_id in self._queue
        )
        cited_sections = sorted(
            {citation for question in selected_questions for citation in question.citations}
        )
        sections: tuple[dict[str, object], ...] = (
            {
                "heading": "Issue Summary",
                "prompts": tuple(item.question_text for item in selected_queue_items)
                or tuple(question.question_text for question in selected_questions),
            },
            {
                "heading": "Code Cross-References",
                "citations": tuple(cited_sections),
                "instruction": "Verify each cited section against the authoritative code text.",
            },
            {
                "heading": "Recommended Staff Review",
                "open_queue_items": tuple(
                    item.id for item in selected_queue_items if item.status in OPEN_QUEUE_STATUSES
                ),
                "instruction": "Resolve open ambiguity items before issuing a determination.",
            },
        )
        return StaffReportOutline(
            id=str(uuid4()),
            title=title,
            sections=sections,
            source_question_ids=tuple(question.id for question in selected_questions),
            source_queue_item_ids=tuple(item.id for item in selected_queue_items),
            created_by=created_by,
            created_at=datetime.now(UTC),
        )

    def flag_answer(
        self,
        *,
        zone_code: str,
        question_text: str,
        original_answer: str,
        flag_reason: str,
        citations: Iterable[str],
        created_by: str,
    ) -> FlaggedAnswerReview:
        now = datetime.now(UTC)
        review = FlaggedAnswerReview(
            id=str(uuid4()),
            zone_code=zone_code.strip().upper(),
            question_text=question_text,
            original_answer=original_answer,
            flag_reason=flag_reason,
            citations=tuple(citations),
            status="flagged",
            improved_answer=None,
            improvement_notes=None,
            reviewed_by=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._flagged_answers[review.id] = review
        self._persist_flagged_answer(review)
        return review

    def improve_flagged_answer(
        self,
        *,
        review_id: str,
        improved_answer: str,
        improvement_notes: str,
        reviewed_by: str,
    ) -> FlaggedAnswerReview | None:
        current = self._flagged_answers.get(review_id)
        if current is None:
            return None
        updated = FlaggedAnswerReview(
            id=current.id,
            zone_code=current.zone_code,
            question_text=current.question_text,
            original_answer=current.original_answer,
            flag_reason=current.flag_reason,
            citations=current.citations,
            status="improved",
            improved_answer=improved_answer,
            improvement_notes=improvement_notes,
            reviewed_by=reviewed_by,
            created_by=current.created_by,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
        )
        self._flagged_answers[review_id] = updated
        self._persist_flagged_answer(updated)
        return updated

    def _hydrate(self) -> None:
        if self.engine is None:
            return
        with self.engine.begin() as connection:
            question_rows = connection.execute(
                sa.select(staff_question_records).order_by(staff_question_records.c.created_at)
            ).mappings()
            queue_rows = connection.execute(
                sa.select(staff_ambiguity_review_items).order_by(
                    staff_ambiguity_review_items.c.created_at
                )
            ).mappings()
            flagged_rows = connection.execute(
                sa.select(staff_flagged_answer_reviews).order_by(
                    staff_flagged_answer_reviews.c.created_at
                )
            ).mappings()
            self._questions = {
                row["id"]: _question_from_row(dict(row))
                for row in question_rows
            }
            self._queue = {
                row["id"]: _queue_item_from_row(dict(row))
                for row in queue_rows
            }
            self._flagged_answers = {
                row["id"]: _flagged_answer_from_row(dict(row))
                for row in flagged_rows
            }

    def _persist_question(self, record: StaffQuestionRecord) -> None:
        if self.engine is None:
            return
        with self.engine.begin() as connection:
            existing = connection.execute(
                sa.select(staff_question_records.c.id).where(staff_question_records.c.id == record.id)
            ).first()
            values = _question_values(record)
            if existing is None:
                connection.execute(staff_question_records.insert().values(**values))
            else:
                connection.execute(
                    staff_question_records.update()
                    .where(staff_question_records.c.id == record.id)
                    .values(**values)
                )

    def _persist_queue_item(self, item: AmbiguityReviewItem) -> None:
        if self.engine is None:
            return
        with self.engine.begin() as connection:
            existing = connection.execute(
                sa.select(staff_ambiguity_review_items.c.id).where(
                    staff_ambiguity_review_items.c.id == item.id
                )
            ).first()
            values = _queue_item_values(item)
            if existing is None:
                connection.execute(staff_ambiguity_review_items.insert().values(**values))
            else:
                connection.execute(
                    staff_ambiguity_review_items.update()
                    .where(staff_ambiguity_review_items.c.id == item.id)
                    .values(**values)
                )

    def _persist_flagged_answer(self, review: FlaggedAnswerReview) -> None:
        if self.engine is None:
            return
        with self.engine.begin() as connection:
            existing = connection.execute(
                sa.select(staff_flagged_answer_reviews.c.id).where(
                    staff_flagged_answer_reviews.c.id == review.id
                )
            ).first()
            values = _flagged_answer_values(review)
            if existing is None:
                connection.execute(staff_flagged_answer_reviews.insert().values(**values))
            else:
                connection.execute(
                    staff_flagged_answer_reviews.update()
                    .where(staff_flagged_answer_reviews.c.id == review.id)
                    .values(**values)
                )


def _cross_references_from_answer(answer: ZoneAnswer) -> tuple[CodeCrossReference, ...]:
    return tuple(
        CodeCrossReference(
            citation=citation,
            source="Townlight Code section reference",
            relevance="Supports the planner-facing informational answer.",
        )
        for citation in answer.citations
    )


def _normalize_question(question_text: str) -> str:
    return " ".join(question_text.casefold().split())


def _cross_reference_payload(reference: CodeCrossReference) -> dict[str, str]:
    return {
        "citation": reference.citation,
        "source": reference.source,
        "relevance": reference.relevance,
    }


def _cross_reference_from_payload(payload: dict[str, object]) -> CodeCrossReference:
    return CodeCrossReference(
        citation=str(payload["citation"]),
        source=str(payload["source"]),
        relevance=str(payload["relevance"]),
    )


def _question_values(record: StaffQuestionRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "zone_code": record.zone_code,
        "question_text": record.question_text,
        "status": record.status,
        "answer_text": record.answer_text,
        "citations": list(record.citations),
        "code_cross_references": [
            _cross_reference_payload(reference) for reference in record.code_cross_references
        ],
        "created_by": record.created_by,
        "created_at": record.created_at,
        "visibility": record.visibility,
        "disclaimer": record.disclaimer,
    }


def _queue_item_values(item: AmbiguityReviewItem) -> dict[str, object]:
    return {
        "id": item.id,
        "zone_code": item.zone_code,
        "question_text": item.question_text,
        "reason": item.reason,
        "status": item.status,
        "assigned_to": item.assigned_to,
        "resolution": item.resolution,
        "source_question_id": item.source_question_id,
        "created_by": item.created_by,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "visibility": item.visibility,
    }


def _flagged_answer_values(review: FlaggedAnswerReview) -> dict[str, object]:
    return {
        "id": review.id,
        "zone_code": review.zone_code,
        "question_text": review.question_text,
        "original_answer": review.original_answer,
        "flag_reason": review.flag_reason,
        "citations": list(review.citations),
        "status": review.status,
        "improved_answer": review.improved_answer,
        "improvement_notes": review.improvement_notes,
        "reviewed_by": review.reviewed_by,
        "created_by": review.created_by,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "visibility": review.visibility,
    }


def _question_from_row(row: dict[str, object]) -> StaffQuestionRecord:
    return StaffQuestionRecord(
        id=str(row["id"]),
        zone_code=str(row["zone_code"]),
        question_text=str(row["question_text"]),
        status=str(row["status"]),
        answer_text=str(row["answer_text"]),
        citations=tuple(row["citations"]),  # type: ignore[arg-type]
        code_cross_references=tuple(
            _cross_reference_from_payload(payload)
            for payload in row["code_cross_references"]  # type: ignore[union-attr]
        ),
        created_by=str(row["created_by"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        visibility=str(row["visibility"]),
        disclaimer=str(row["disclaimer"]),
    )


def _queue_item_from_row(row: dict[str, object]) -> AmbiguityReviewItem:
    return AmbiguityReviewItem(
        id=str(row["id"]),
        zone_code=str(row["zone_code"]),
        question_text=str(row["question_text"]),
        reason=str(row["reason"]),
        status=str(row["status"]),
        assigned_to=row["assigned_to"] if row["assigned_to"] is None else str(row["assigned_to"]),
        resolution=row["resolution"] if row["resolution"] is None else str(row["resolution"]),
        source_question_id=(
            row["source_question_id"]
            if row["source_question_id"] is None
            else str(row["source_question_id"])
        ),
        created_by=str(row["created_by"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        visibility=str(row["visibility"]),
    )


def _flagged_answer_from_row(row: dict[str, object]) -> FlaggedAnswerReview:
    return FlaggedAnswerReview(
        id=str(row["id"]),
        zone_code=str(row["zone_code"]),
        question_text=str(row["question_text"]),
        original_answer=str(row["original_answer"]),
        flag_reason=str(row["flag_reason"]),
        citations=tuple(row["citations"]),  # type: ignore[arg-type]
        status=str(row["status"]),
        improved_answer=(
            row["improved_answer"] if row["improved_answer"] is None else str(row["improved_answer"])
        ),
        improvement_notes=(
            row["improvement_notes"]
            if row["improvement_notes"] is None
            else str(row["improvement_notes"])
        ),
        reviewed_by=row["reviewed_by"] if row["reviewed_by"] is None else str(row["reviewed_by"]),
        created_by=str(row["created_by"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        visibility=str(row["visibility"]),
    )
