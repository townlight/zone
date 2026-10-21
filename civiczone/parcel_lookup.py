from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine


@dataclass(frozen=True)
class ParcelLookupResult:
    parcel_number: str
    address: str
    zone_code: str
    zone_name: str
    overlays: tuple[str, ...]
    constraints: tuple[str, ...]
    source: str
    disclaimer: str


@dataclass(frozen=True)
class ParcelLookupError:
    message: str
    fix: str


SAMPLE_PARCELS: dict[str, ParcelLookupResult] = {
    "100-200-300": ParcelLookupResult(
        parcel_number="100-200-300",
        address="123 Main St",
        zone_code="R-2",
        zone_name="Medium Density Residential",
        overlays=("Historic District",),
        constraints=("Planner review required for exterior changes in the historic overlay.",),
        source="Sample fixture: city zoning map extract 2026-04-27",
        disclaimer="Informational only; this is not a zoning determination.",
    )
}

ADDRESS_INDEX = {value.address.casefold(): key for key, value in SAMPLE_PARCELS.items()}


metadata = sa.MetaData()

parcel_lookup_records = sa.Table(
    "parcel_lookup_records",
    metadata,
    sa.Column("parcel_number", sa.String(120), primary_key=True),
    sa.Column("address", sa.String(500), nullable=False),
    sa.Column("zone_code", sa.String(80), nullable=False),
    sa.Column("zone_name", sa.String(255), nullable=False),
    sa.Column("overlays", sa.JSON(), nullable=False),
    sa.Column("constraints", sa.JSON(), nullable=False),
    sa.Column("source", sa.Text(), nullable=False),
    sa.Column("disclaimer", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civiczone",
)


class ParcelLookupRepository:
    """SQLAlchemy-backed parcel lookup records for local GIS/file-drop slices."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None, seed_defaults: bool = True) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civiczone": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civiczone"))
        metadata.create_all(self.engine)
        if seed_defaults:
            self.seed(SAMPLE_PARCELS.values())

    def seed(self, parcels: Iterable[ParcelLookupResult]) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            for parcel in parcels:
                exists = connection.execute(
                    sa.select(parcel_lookup_records.c.parcel_number).where(
                        parcel_lookup_records.c.parcel_number == parcel.parcel_number
                    )
                ).first()
                if exists is not None:
                    continue
                connection.execute(
                    parcel_lookup_records.insert()
                    .values(
                        parcel_number=parcel.parcel_number,
                        address=parcel.address,
                        zone_code=parcel.zone_code,
                        zone_name=parcel.zone_name,
                        overlays=list(parcel.overlays),
                        constraints=list(parcel.constraints),
                        source=parcel.source,
                        disclaimer=parcel.disclaimer,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def lookup(
        self, *, parcel_number: str | None = None, address: str | None = None
    ) -> ParcelLookupResult | ParcelLookupError:
        with self.engine.begin() as connection:
            row = None
            if parcel_number:
                row = connection.execute(
                    sa.select(parcel_lookup_records).where(
                        parcel_lookup_records.c.parcel_number == parcel_number.strip()
                    )
                ).mappings().first()
            if row is None and address:
                row = connection.execute(
                    sa.select(parcel_lookup_records).where(
                        sa.func.lower(parcel_lookup_records.c.address) == address.strip().casefold()
                    )
                ).mappings().first()
        if row is not None:
            return _row_to_parcel(row)
        return ParcelLookupError(
            message="Parcel not found in the CivicZone configured parcel dataset.",
            fix="Load parcel data into the configured CIVICZONE_PARCEL_RULE_DB_URL store or use the sample parcel '100-200-300'.",
        )


def lookup_parcel(*, parcel_number: str | None = None, address: str | None = None) -> ParcelLookupResult | ParcelLookupError:
    """Return a sample parcel lookup without claiming live GIS integration."""

    if parcel_number:
        key = parcel_number.strip()
        if key in SAMPLE_PARCELS:
            return SAMPLE_PARCELS[key]

    if address:
        key = ADDRESS_INDEX.get(address.strip().casefold())
        if key:
            return SAMPLE_PARCELS[key]

    return ParcelLookupError(
        message="Parcel not found in the CivicZone sample dataset.",
        fix=(
            "Use parcel_number '100-200-300' or address '123 Main St', or load local parcel records "
            "into the configured CIVICZONE_PARCEL_RULE_DB_URL store."
        ),
    )


def _row_to_parcel(row: object) -> ParcelLookupResult:
    data = dict(row)
    return ParcelLookupResult(
        parcel_number=data["parcel_number"],
        address=data["address"],
        zone_code=data["zone_code"],
        zone_name=data["zone_name"],
        overlays=tuple(data["overlays"]),
        constraints=tuple(data["constraints"]),
        source=data["source"],
        disclaimer=data["disclaimer"],
    )
