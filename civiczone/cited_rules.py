import hashlib
import json
import uuid
from sqlalchemy import text

DISCLAIMER = "Informational only; not a zoning determination, permit approval or legal advice."


def register_rule(engine, p, actor, resolve):
    jur = p["jurisdiction"]
    zone_code = p["zone_code"]
    kind = p["kind"]
    key = p["key"]
    value = p["value"]
    section_number = p["section_number"]
    overlay = p.get("overlay_code")
    for name, val, limit in (
        ("jurisdiction", jur, 255),
        ("zone_code", zone_code, 255),
        ("kind", kind, 255),
        ("key", key, 255),
        ("value", value, 1000),
        ("section_number", section_number, 255),
    ):
        if not isinstance(val, str) or not val.strip() or len(val) > limit:
            raise ValueError("invalid %s" % name)
    if kind == "use":
        if value not in ("allowed", "conditional", "prohibited"):
            raise ValueError("invalid use status")
    elif kind != "dimension":
        raise ValueError("invalid kind")
    if overlay is not None:
        if not isinstance(overlay, str) or not overlay.strip() or len(overlay) > 255:
            raise ValueError("invalid overlay_code")
    resolved = resolve(section_number)
    if not resolved or resolved.get("status") != "ok":
        raise ValueError("section resolution failed")
    citation = resolved["citation"]
    digest = citation_digest(citation)
    snapshot = {"citation": citation, "digest": digest, "actor_id": actor}
    snapshot_json = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    new_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:j)::bigint)"), {"j": jur})
        zone_row = conn.execute(
            text(
                "SELECT id FROM civiczone.zones WHERE jurisdiction=:j AND code=:c AND is_active=true"
            ),
            {"j": jur, "c": zone_code},
        ).first()
        if not zone_row:
            raise ValueError("zone not found")
        zone_id = zone_row[0]
        if overlay is not None:
            ov = conn.execute(
                text(
                    "SELECT 1 FROM civiczone.overlays WHERE code=:c AND jurisdiction=:j AND is_active=true"
                ),
                {"c": overlay, "j": jur},
            ).first()
            if not ov:
                raise ValueError("overlay not found")
        if kind == "use":
            uc_id = uuid.uuid5(uuid.NAMESPACE_URL, "civiczone:use_category:%s" % key)
            conn.execute(
                text(
                    "INSERT INTO civiczone.use_categories (id, code, label) VALUES (:i, :c, :l) ON CONFLICT (id) DO NOTHING"
                ),
                {"i": uc_id, "c": key, "l": key},
            )
            conn.execute(
                text(
                    "UPDATE civiczone.use_rules SET is_active=false WHERE zone_id=:z AND use_category_id=:u AND overlay_code IS NOT DISTINCT FROM :o AND is_active=true"
                ),
                {"z": zone_id, "u": uc_id, "o": overlay},
            )
            conn.execute(
                text(
                    "INSERT INTO civiczone.use_rules (id, zone_id, use_category_id, status, source_section_ref, conditions, code_snapshot, overlay_code, is_active) VALUES (:i, :z, :u, :s, :ref, CAST(:cond AS jsonb), CAST(:snap AS jsonb), :o, true)"
                ),
                {
                    "i": new_id,
                    "z": zone_id,
                    "u": uc_id,
                    "s": value,
                    "ref": section_number,
                    "cond": json.dumps({}),
                    "snap": snapshot_json,
                    "o": overlay,
                },
            )
        else:
            conn.execute(
                text(
                    "UPDATE civiczone.dimensional_rules SET is_active=false WHERE zone_id=:z AND rule_type=:k AND overlay_code IS NOT DISTINCT FROM :o AND is_active=true"
                ),
                {"z": zone_id, "k": key, "o": overlay},
            )
            conn.execute(
                text(
                    "INSERT INTO civiczone.dimensional_rules (id, zone_id, rule_type, value_text, source_section_ref, code_snapshot, overlay_code, is_active) VALUES (:i, :z, :k, :v, :ref, CAST(:snap AS jsonb), :o, true)"
                ),
                {
                    "i": new_id,
                    "z": zone_id,
                    "k": key,
                    "v": value,
                    "ref": section_number,
                    "snap": snapshot_json,
                    "o": overlay,
                },
            )
    return str(new_id)


def citation_digest(cit):
    keys = (
        "section_id",
        "section_number",
        "version_id",
        "source_id",
        "body_text",
        "effective_start",
        "effective_end",
    )
    payload = {k: (cit or {}).get(k) for k in keys}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _rule_rows(engine, jurisdiction, zone_code, kind, key):
    if kind not in ("use", "dimension"):
        raise ValueError(f"unsupported rule kind: {kind!r}")
    if kind == "use":
        sql = (
            "SELECT r.id, r.status AS value, r.code_snapshot, "
            "r.source_section_ref, r.overlay_code "
            "FROM civiczone.use_rules r "
            "JOIN civiczone.zones z ON z.id = r.zone_id "
            "JOIN civiczone.use_categories u ON u.id = r.use_category_id "
            "WHERE z.jurisdiction = :jurisdiction AND z.code = :zone_code "
            "AND z.is_active AND r.is_active AND u.code = :key"
        )
    else:
        sql = (
            "SELECT r.id, r.value_text AS value, r.code_snapshot, "
            "r.source_section_ref, r.overlay_code "
            "FROM civiczone.dimensional_rules r "
            "JOIN civiczone.zones z ON z.id = r.zone_id "
            "WHERE z.jurisdiction = :jurisdiction AND z.code = :zone_code "
            "AND z.is_active AND r.is_active AND r.rule_type = :key"
        )
    params = {"jurisdiction": jurisdiction, "zone_code": zone_code, "key": key}
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]


def answer(engine, parcel, kind, key, resolve):
    out = {
        "disclaimer": DISCLAIMER,
        "parcel": parcel,
        "kind": kind,
        "key": key,
        "citations": [],
        "answer": None,
        "status": "needs_planner",
        "reason": None,
    }
    if (
        not parcel
        or parcel.get("status") != "ok"
        or kind not in ("use", "dimension")
        or not key
        or not parcel.get("jurisdiction")
        or not parcel.get("zone", {}).get("code")
    ):
        out["reason"] = "invalid_parcel"
        return out
    oc = [o["code"] for o in parcel.get("overlays", [])]
    rows = _rule_rows(engine, parcel["jurisdiction"], parcel["zone"]["code"], kind, key)
    rows = [r for r in rows if r.get("overlay_code") is None or r["overlay_code"] in oc]
    if not rows:
        out["reason"] = "unsupported"
        return out
    have = {r["overlay_code"] for r in rows if r.get("overlay_code")}
    if set(oc) - have:
        out["reason"] = "overlay_rule_unavailable"
        return out
    cits, vals = [], set()
    for r in rows:
        s = r.get("code_snapshot") or {}
        sec = r.get("source_section_ref")
        res = resolve(sec) if sec else None
        if not res or res.get("status") != "ok":
            out["reason"] = "unresolved"
            out["citations"] = cits
            return out
        if citation_digest(res["citation"]) != s.get("digest"):
            out["reason"] = "stale_code"
            out["citations"] = [s.get("citation")]
            return out
        cits.append(res.get("citation") or s.get("citation"))
        vals.add(r.get("value"))
    if len(vals) > 1:
        out["reason"] = "conflicting_rules"
        out["citations"] = cits
        return out
    v = next(iter(vals)) if vals else None
    out.update(status="answered", answer=str(v) if v is not None else None, citations=cits)
    return out
