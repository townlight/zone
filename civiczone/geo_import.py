from __future__ import annotations

import json
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .geo_spatial import validate_spatial
from .geo_validate import DISCLAIMER, GeoImportError, prepare

SCHEMA = "civiczone"
GEOM = "ST_Multi(ST_GeomFromGeoJSON(:geom))::geography"


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _source_payload(prov: dict, feature: dict) -> str:
    return json.dumps(
        {
            **prov,
            "feature_id": feature.get("feature_id"),
            "properties": feature.get("properties") or {},
        },
        sort_keys=True,
    )


def _sid(jurisdiction: str, kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, json.dumps([jurisdiction, kind, key])))


def import_geojson(engine, payload, actor_id):
    prep = prepare(payload, actor_id)
    jurisdiction = prep["jurisdiction"]
    source_id = prep["source_id"]
    version = prep["version"]
    digest = prep["content_sha256"]

    with engine.begin() as conn:
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:j))"),
            {"j": jurisdiction},
        )

        existing = conn.execute(
            text(
                "SELECT id, content_sha256, is_current "
                "FROM civiczone.geo_imports "
                "WHERE jurisdiction=:j AND source_id=:s AND version=:v"
            ),
            {"j": jurisdiction, "s": source_id, "v": version},
        ).mappings().first()
        if existing:
            if existing["content_sha256"] != digest:
                raise GeoImportError("import version already exists with different content")
            return {
                "status": "imported",
                "id": str(existing["id"]),
                "version": version,
                "content_sha256": digest,
                "idempotent": True,
                "is_current": bool(existing["is_current"]),
            }

        spatial = validate_spatial(conn, prep)

        conn.execute(
            text(
                "UPDATE civiczone.geo_imports SET is_current=false "
                "WHERE jurisdiction=:j AND is_current=true"
            ),
            {"j": jurisdiction},
        )
        conn.execute(
            text(
                "UPDATE civiczone.parcels p SET is_active=false, updated_at=now() "
                "FROM civiczone.zones z "
                "WHERE p.zone_id=z.id AND z.jurisdiction=:j"
            ),
            {"j": jurisdiction},
        )
        conn.execute(
            text(
                "UPDATE civiczone.zones SET is_active=false, updated_at=now() "
                "WHERE jurisdiction=:j"
            ),
            {"j": jurisdiction},
        )
        conn.execute(
            text(
                "UPDATE civiczone.overlays SET is_active=false, updated_at=now() "
                "WHERE jurisdiction=:j"
            ),
            {"j": jurisdiction},
        )

        import_id = conn.execute(
            text(
                "INSERT INTO civiczone.geo_imports "
                "(jurisdiction, source_id, version, source_date, content_sha256, "
                " payload, actor_id, is_current) "
                "VALUES (:j, :s, :v, CAST(:sd AS date), :h, "
                "        CAST(:payload AS jsonb), :actor, true) "
                "RETURNING id"
            ),
            {
                "j": jurisdiction,
                "s": source_id,
                "v": version,
                "sd": prep.get("source_date"),
                "h": digest,
                "payload": prep["payload"],
                "actor": actor_id,
            },
        ).scalar_one()

        prov = {
            "source_id": source_id,
            "version": version,
            "content_sha256": digest,
            "import_id": str(import_id),
        }
        zone_ids = {}

        for feature in prep["zones"]:
            props = (feature.get("properties") or {})
            code = props["code"]
            zone_id = _sid(jurisdiction, "zone", code)
            zone_ids[code] = zone_id
            conn.execute(
                text(
                    "INSERT INTO civiczone.zones "
                    "(id, code, name, jurisdiction, source_section_ref, is_active, geom, source_payload) "
                    "VALUES (:id, :code, :name, :j, :section, true, "
                    f"{GEOM}, CAST(:source_payload AS jsonb)) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "code=EXCLUDED.code, name=EXCLUDED.name, jurisdiction=EXCLUDED.jurisdiction, "
                    "source_section_ref=EXCLUDED.source_section_ref, is_active=EXCLUDED.is_active, "
                    "geom=EXCLUDED.geom, source_payload=EXCLUDED.source_payload, updated_at=now()"
                ),
                {
                    "id": zone_id,
                    "code": code,
                    "name": props.get("name"),
                    "j": jurisdiction,
                    "section": props.get("section_number"),
                    "geom": json.dumps(feature["geometry"]),
                    "source_payload": _source_payload(prov, feature),
                },
            )

        for feature in prep["overlays"]:
            props = (feature.get("properties") or {})
            code = props["code"]
            overlay_id = _sid(jurisdiction, "overlay", code)
            conn.execute(
                text(
                    "INSERT INTO civiczone.overlays "
                    "(id, code, name, jurisdiction, source_section_ref, is_active, geom, source_payload) "
                    "VALUES (:id, :code, :name, :j, :section, true, "
                    f"{GEOM}, CAST(:source_payload AS jsonb)) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "code=EXCLUDED.code, name=EXCLUDED.name, jurisdiction=EXCLUDED.jurisdiction, "
                    "source_section_ref=EXCLUDED.source_section_ref, is_active=EXCLUDED.is_active, "
                    "geom=EXCLUDED.geom, source_payload=EXCLUDED.source_payload, updated_at=now()"
                ),
                {
                    "id": overlay_id,
                    "code": code,
                    "name": props.get("name"),
                    "j": jurisdiction,
                    "section": props.get("section_number"),
                    "geom": json.dumps(feature["geometry"]),
                    "source_payload": _source_payload(prov, feature),
                },
            )

        for feature in prep["parcels"]:
            props = (feature.get("properties") or {})
            parcel_number = props["parcel_number"]
            parcel_id = _sid(jurisdiction, "parcel", parcel_number)
            derived = spatial.get(parcel_number) or {}
            conn.execute(
                text(
                    "INSERT INTO civiczone.parcels "
                    "(id, parcel_number, address, zone_id, overlay_payload, source_payload, "
                    " geom, dataset_id, is_active) "
                    "VALUES (:id, :parcel_number, :address, :zone_id, "
                    "        CAST(:overlay_payload AS jsonb), CAST(:source_payload AS jsonb), "
                    f"        {GEOM}, :dataset_id, true) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "parcel_number=EXCLUDED.parcel_number, address=EXCLUDED.address, "
                    "zone_id=EXCLUDED.zone_id, overlay_payload=EXCLUDED.overlay_payload, "
                    "source_payload=EXCLUDED.source_payload, geom=EXCLUDED.geom, "
                    "dataset_id=EXCLUDED.dataset_id, is_active=EXCLUDED.is_active, updated_at=now()"
                ),
                {
                    "id": parcel_id,
                    "parcel_number": parcel_number,
                    "address": props.get("address"),
                    "zone_id": zone_ids.get(derived.get("zone_code")),
                    "overlay_payload": json.dumps(derived.get("overlays") or []),
                    "source_payload": _source_payload(prov, feature),
                    "geom": json.dumps(feature["geometry"]),
                    "dataset_id": import_id,
                },
            )

    return {
        "status": "imported",
        "id": str(import_id),
        "version": version,
        "content_sha256": digest,
        "idempotent": False,
        "is_current": True,
    }


def lookup_parcel(engine, *, jurisdiction, query):
    if not isinstance(jurisdiction, str) or not isinstance(query, str):
        raise GeoImportError("jurisdiction and query are required")
    jurisdiction = jurisdiction.strip()
    query = query.strip()
    if not jurisdiction or not query:
        raise GeoImportError("jurisdiction and query are required")
    try:
        with engine.connect() as conn:
            current = conn.execute(
                text(
                    "SELECT id, source_id, version, source_date, content_sha256, imported_at "
                    "FROM civiczone.geo_imports "
                    "WHERE jurisdiction=:j AND is_current=true "
                    "ORDER BY imported_at DESC LIMIT 1"
                ),
                {"j": jurisdiction},
            ).mappings().first()
            if not current:
                return {"status": "out_of_jurisdiction"}

            rows = conn.execute(
                text(
                    "SELECT p.id, p.parcel_number, p.address, p.overlay_payload, "
                    "       z.code, z.name, z.source_section_ref "
                    "FROM civiczone.parcels p "
                    "JOIN civiczone.zones z ON z.id=p.zone_id "
                    "WHERE p.dataset_id=:imp AND p.is_active=true AND z.is_active=true "
                    "AND (p.parcel_number=:q OR lower(p.address)=lower(:q)) "
                    "LIMIT 2"
                ),
                {"imp": current["id"], "q": query},
            ).mappings().all()

            if not rows:
                return {"status": "not_found"}
            if len(rows) > 1:
                return {"status": "ambiguous"}

            row = rows[0]
            overlays = row["overlay_payload"] or []
            if isinstance(overlays, str):
                overlays = json.loads(overlays)
            return {
                "status": "ok",
                "parcel_id": str(row["id"]),
                "parcel_number": row["parcel_number"],
                "address": row["address"],
                "jurisdiction": jurisdiction,
                "zone": {
                    "code": row["code"],
                    "name": row["name"],
                    "section_number": row["source_section_ref"],
                },
                "overlays": overlays,
                "source": {
                    "source_id": current["source_id"],
                    "version": current["version"],
                    "source_date": _iso(current["source_date"]),
                    "content_sha256": current["content_sha256"],
                    "imported_at": _iso(current["imported_at"]),
                },
                "disclaimer": DISCLAIMER,
            }
    except SQLAlchemyError:
        return {"status": "data_unavailable"}


def readiness(engine) -> bool:
    required = {
        "geo_imports": {
            "id", "jurisdiction", "source_id", "version", "source_date",
            "content_sha256", "payload", "actor_id", "imported_at", "is_current",
        },
        "zones": {
            "id", "code", "name", "jurisdiction", "source_section_ref",
            "is_active", "geom", "source_payload",
        },
        "overlays": {
            "id", "code", "name", "jurisdiction", "source_section_ref",
            "is_active", "geom", "source_payload",
        },
        "parcels": {
            "id", "parcel_number", "address", "zone_id", "overlay_payload",
            "source_payload", "geom", "dataset_id", "is_active",
        },
    }
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT postgis_version()")).scalar_one()
            rows = conn.execute(
                text(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema='civiczone' "
                    "AND table_name IN ('geo_imports','zones','overlays','parcels')"
                )
            ).all()
            have: dict[str, set[str]] = {}
            for table, column in rows:
                have.setdefault(table, set()).add(column)
            if any(not columns <= have.get(table, set()) for table, columns in required.items()):
                return False
            stmt = text(
                "SELECT id, question_id, actor_id, event_type, payload, created_at "
                "FROM civiczone.question_events LIMIT 0"
            )
            conn.execute(stmt)
            revision = conn.execute(
                text("SELECT 1 FROM alembic_version_civiczone WHERE version_num=:rev"),
                {"rev": "civiczone_0006_cited_questions"},
            ).first()
            return revision is not None
    except SQLAlchemyError:
        return False
