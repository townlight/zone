from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

DISCLAIMER = "Informational only; this is not a zoning determination."


@dataclass(frozen=True)
class UseRuleResult:
    zone_code: str
    use: str
    status: str
    review_path: str
    citation: str
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class DimensionalRuleResult:
    zone_code: str
    rule_type: str
    value: str
    citation: str
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class RuleLookupError:
    message: str
    fix: str


USE_RULES = {
    ("R-2", "adu"): UseRuleResult(
        zone_code="R-2",
        use="ADU",
        status="conditional",
        review_path="Planner review required before relying on this answer.",
        citation="CMC 18.42.030",
    ),
    ("R-2", "single-family dwelling"): UseRuleResult(
        zone_code="R-2",
        use="single-family dwelling",
        status="allowed",
        review_path="Confirm parcel-specific overlays before permitting.",
        citation="CMC 18.20.020",
    ),
    ("R-2", "restaurant"): UseRuleResult(
        zone_code="R-2",
        use="restaurant",
        status="not listed",
        review_path="Escalate to planning staff for interpretation.",
        citation="CMC 18.20.020",
    ),
}

DIMENSIONAL_RULES = {
    ("R-2", "front_setback"): DimensionalRuleResult(
        zone_code="R-2",
        rule_type="front_setback",
        value="20 feet minimum",
        citation="CMC 18.20.050(A)",
    ),
    ("R-2", "height"): DimensionalRuleResult(
        zone_code="R-2",
        rule_type="height",
        value="35 feet maximum",
        citation="CMC 18.20.050(B)",
    ),
}


metadata = sa.MetaData()

use_rule_lookup_records = sa.Table(
    "use_rule_lookup_records",
    metadata,
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

dimensional_rule_lookup_records = sa.Table(
    "dimensional_rule_lookup_records",
    metadata,
    sa.Column("zone_code", sa.String(80), primary_key=True),
    sa.Column("rule_type", sa.String(120), primary_key=True),
    sa.Column("value", sa.String(255), nullable=False),
    sa.Column("citation", sa.String(255), nullable=False),
    sa.Column("disclaimer", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civiczone",
)


class RuleLookupRepository:
    """SQLAlchemy-backed zoning use and dimensional rule lookup records."""

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
            self.seed_use_rules(USE_RULES.values())
            self.seed_dimensional_rules(DIMENSIONAL_RULES.values())

    def seed_use_rules(self, rules: Iterable[UseRuleResult]) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            for rule in rules:
                zone_code = rule.zone_code.strip().upper()
                use_key = rule.use.strip().casefold()
                exists = connection.execute(
                    sa.select(use_rule_lookup_records.c.zone_code).where(
                        use_rule_lookup_records.c.zone_code == zone_code,
                        use_rule_lookup_records.c.use_key == use_key,
                    )
                ).first()
                if exists is not None:
                    continue
                connection.execute(
                    use_rule_lookup_records.insert().values(
                        zone_code=zone_code,
                        use_key=use_key,
                        use=rule.use,
                        status=rule.status,
                        review_path=rule.review_path,
                        citation=rule.citation,
                        disclaimer=rule.disclaimer,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def seed_dimensional_rules(self, rules: Iterable[DimensionalRuleResult]) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            for rule in rules:
                zone_code = rule.zone_code.strip().upper()
                rule_type = rule.rule_type.strip().casefold()
                exists = connection.execute(
                    sa.select(dimensional_rule_lookup_records.c.zone_code).where(
                        dimensional_rule_lookup_records.c.zone_code == zone_code,
                        dimensional_rule_lookup_records.c.rule_type == rule_type,
                    )
                ).first()
                if exists is not None:
                    continue
                connection.execute(
                    dimensional_rule_lookup_records.insert().values(
                        zone_code=zone_code,
                        rule_type=rule_type,
                        value=rule.value,
                        citation=rule.citation,
                        disclaimer=rule.disclaimer,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def lookup_use_rule(self, *, zone_code: str, use: str) -> UseRuleResult | RuleLookupError:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(use_rule_lookup_records).where(
                    use_rule_lookup_records.c.zone_code == zone_code.strip().upper(),
                    use_rule_lookup_records.c.use_key == use.strip().casefold(),
                )
            ).mappings().first()
        if row is not None:
            data = dict(row)
            return UseRuleResult(
                zone_code=data["zone_code"],
                use=data["use"],
                status=data["status"],
                review_path=data["review_path"],
                citation=data["citation"],
                disclaimer=data["disclaimer"],
            )
        return RuleLookupError(
            message="Use rule not found in the CivicZone configured rule dataset.",
            fix="Load use rules into CIVICZONE_PARCEL_RULE_DB_URL or try the sample R-2 ADU rule.",
        )

    def lookup_dimensional_rule(
        self, *, zone_code: str, rule_type: str
    ) -> DimensionalRuleResult | RuleLookupError:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(dimensional_rule_lookup_records).where(
                    dimensional_rule_lookup_records.c.zone_code == zone_code.strip().upper(),
                    dimensional_rule_lookup_records.c.rule_type == rule_type.strip().casefold(),
                )
            ).mappings().first()
        if row is not None:
            data = dict(row)
            return DimensionalRuleResult(
                zone_code=data["zone_code"],
                rule_type=data["rule_type"],
                value=data["value"],
                citation=data["citation"],
                disclaimer=data["disclaimer"],
            )
        return RuleLookupError(
            message="Dimensional rule not found in the CivicZone configured rule dataset.",
            fix="Load dimensional rules into CIVICZONE_PARCEL_RULE_DB_URL or try the sample R-2 height rule.",
        )


def lookup_use_rule(*, zone_code: str, use: str) -> UseRuleResult | RuleLookupError:
    key = (zone_code.strip().upper(), use.strip().casefold())
    result = USE_RULES.get(key)
    if result:
        return result
    return RuleLookupError(
        message="Use rule not found in the CivicZone sample dataset.",
        fix="Try zone_code 'R-2' with use 'ADU', 'single-family dwelling', or 'restaurant'.",
    )


def lookup_dimensional_rule(*, zone_code: str, rule_type: str) -> DimensionalRuleResult | RuleLookupError:
    key = (zone_code.strip().upper(), rule_type.strip().casefold())
    result = DIMENSIONAL_RULES.get(key)
    if result:
        return result
    return RuleLookupError(
        message="Dimensional rule not found in the CivicZone sample dataset.",
        fix="Try zone_code 'R-2' with rule_type 'front_setback' or 'height'.",
    )
