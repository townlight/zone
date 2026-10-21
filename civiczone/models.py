from __future__ import annotations

import uuid
from typing import ClassVar

from civiccore.db import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class Zone(IdMixin, TimestampMixin, Base):
    __tablename__ = "zones"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    source_section_ref: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Overlay(IdMixin, TimestampMixin, Base):
    __tablename__ = "overlays"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_section_ref: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Parcel(IdMixin, TimestampMixin, Base):
    __tablename__ = "parcels"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    parcel_number: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("civiczone.zones.id"), nullable=False)
    overlay_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    geometry_ref: Mapped[str | None] = mapped_column(Text)
    source_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class UseCategory(IdMixin, TimestampMixin, Base):
    __tablename__ = "use_categories"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    code: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class UseRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "use_rules"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("civiczone.zones.id"), nullable=False)
    use_category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("civiczone.use_categories.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    review_path: Mapped[str | None] = mapped_column(String(255))
    source_section_ref: Mapped[str | None] = mapped_column(String(255))
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class DimensionalRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "dimensional_rules"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("civiczone.zones.id"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(120), nullable=False)
    value_text: Mapped[str] = mapped_column(String(255), nullable=False)
    source_section_ref: Mapped[str | None] = mapped_column(String(255))
    applies_to: Mapped[str | None] = mapped_column(String(255))


class Citation(IdMixin, TimestampMixin, Base):
    __tablename__ = "citations"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    source_section_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    citation_text: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class Precedent(IdMixin, TimestampMixin, Base):
    __tablename__ = "precedents"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(80), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class InterpretationNote(IdMixin, TimestampMixin, Base):
    __tablename__ = "interpretation_notes"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("civiczone.zones.id"))
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)


class ZoneQuestion(IdMixin, TimestampMixin, Base):
    __tablename__ = "zone_questions"
    __table_args__: ClassVar[dict] = {"schema": "civiczone"}

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text)
    citation_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    escalation_reason: Mapped[str | None] = mapped_column(String(255))
