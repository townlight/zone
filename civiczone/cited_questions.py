import json
import uuid
from collections import Counter

from sqlalchemy import text


def _norm(row):
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return json.loads(json.dumps(d, default=str))


def record(engine, payload, actor_id, result):
    lid = str(uuid.uuid4())
    parcel = getattr(result, "parcel", None) or (
        result.get("parcel") if isinstance(result, dict) else None
    )
    zone = getattr(parcel, "zone", None) or (
        parcel.get("zone") if isinstance(parcel, dict) else None
    )
    zone_code = getattr(zone, "code", None) or (
        zone.get("code") if isinstance(zone, dict) else None
    )
    question_text = (
        payload.get("question") if isinstance(payload, dict) else getattr(payload, "question", "")
    )
    audience = (
        payload.get("audience") if isinstance(payload, dict) else getattr(payload, "audience", None)
    ) or "resident"
    status = (
        getattr(result, "status", None) if not isinstance(result, dict) else result.get("status")
    )
    answer = (
        getattr(result, "answer", None) if not isinstance(result, dict) else result.get("answer")
    )
    citations = list(
        (
            getattr(result, "citations", None)
            if not isinstance(result, dict)
            else result.get("citations")
        )
        or []
    )
    disclaimer = (
        getattr(result, "disclaimer", None)
        if not isinstance(result, dict)
        else result.get("disclaimer")
    )
    reason = (
        getattr(result, "reason", None) if not isinstance(result, dict) else result.get("reason")
    )
    needs_planner = result.get("status") == "needs_planner"
    full_result = result if isinstance(result, dict) else result.__dict__
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO civiczone.zone_question_ledger_records
            (id, zone_code, question_text, audience, status, answer_text, citation_payload,
             disclaimer, escalation_reason, created_at, updated_at, context, actor_id)
            VALUES (:id, :zone_code, :question_text, :audience, :status, :answer,
                    CAST(:citations AS JSONB), :disclaimer, :reason, NOW(), NOW(),
                    CAST(:context AS JSONB), :actor_id)
        """),
            {
                "id": lid,
                "zone_code": zone_code or "unknown",
                "question_text": question_text,
                "audience": audience,
                "status": status,
                "answer": answer,
                "citations": json.dumps(citations, default=str),
                "disclaimer": disclaimer,
                "reason": reason,
                "context": json.dumps(full_result, default=str),
                "actor_id": actor_id,
            },
        )
        if needs_planner:
            conn.execute(
                text("""
                INSERT INTO civiczone.staff_ambiguity_review_items
                (id, zone_code, question_text, reason, status, source_question_id,
                 created_by, created_at, updated_at, visibility)
                VALUES (:id, :zone_code, :question_text, :reason, 'open', :source_id,
                        :created_by, NOW(), NOW(), 'staff_only')
            """),
                {
                    "id": str(uuid.uuid4()),
                    "zone_code": zone_code or "unknown",
                    "question_text": question_text,
                    "reason": reason or "needs_planner",
                    "source_id": lid,
                    "created_by": actor_id,
                },
            )
    out = dict(full_result)
    out["id"] = lid
    return out


def workspace(engine):
    with engine.connect() as conn:
        q_rows = conn.execute(
            text(
                "SELECT * FROM civiczone.zone_question_ledger_records ORDER BY created_at DESC LIMIT 200"
            )
        ).fetchall()
        queue_rows = conn.execute(
            text(
                "SELECT * FROM civiczone.staff_ambiguity_review_items ORDER BY created_at DESC LIMIT 200"
            )
        ).fetchall()
        review_rows = conn.execute(
            text(
                "SELECT * FROM civiczone.staff_flagged_answer_reviews ORDER BY created_at DESC LIMIT 200"
            )
        ).fetchall()
        totals = conn.execute(
            text("SELECT COUNT(*) AS n FROM civiczone.zone_question_ledger_records")
        ).scalar_one()
        status_rows = conn.execute(
            text(
                "SELECT status, COUNT(*) AS n FROM civiczone.zone_question_ledger_records GROUP BY status"
            )
        ).fetchall()
        high_volume_rows = (
            conn.execute(
                text("""
            SELECT zone_code, lower(trim(question_text)) AS question_text, COUNT(*) AS count
            FROM civiczone.zone_question_ledger_records
            GROUP BY zone_code, lower(trim(question_text))
            HAVING COUNT(*) >= 2 ORDER BY COUNT(*) DESC LIMIT 20
        """)
            )
            .mappings()
            .all()
        )
    counts = Counter()
    for r in status_rows:
        counts[r._mapping["status"]] = int(r._mapping["n"])
    return {
        "questions": [_norm(r) for r in q_rows],
        "queue": [_norm(r) for r in queue_rows],
        "reviews": [_norm(r) for r in review_rows],
        "analytics": {
            "total_questions": int(totals),
            "status_counts": dict(counts),
            "high_volume_questions": [_norm(row) for row in high_volume_rows],
        },
    }


def review(engine, question_id, payload, actor_id):
    data = dict(payload or {})
    answer = data.get("answer") or ""
    notes = data.get("notes") or ""
    queue_status = data.get("queue_status") or "resolved"
    if queue_status not in ("open", "in_review", "resolved", "closed"):
        raise ValueError("invalid queue_status")
    eid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM civiczone.zone_question_ledger_records WHERE id = :id"),
            {"id": question_id},
        ).fetchone()
        if row is None:
            raise ValueError(f"question {question_id} not found")
        rec = dict(row._mapping)
        conn.execute(
            text("""
            INSERT INTO civiczone.question_events
            (id, question_id, actor_id, event_type, payload, created_at)
            VALUES (:id, :question_id, :actor_id, 'human_correction', CAST(:payload AS JSONB), NOW())
        """),
            {
                "id": eid,
                "question_id": question_id,
                "actor_id": actor_id,
                "payload": json.dumps(
                    {"answer": answer, "notes": notes, "queue_status": queue_status}
                ),
            },
        )
        conn.execute(
            text("""
            INSERT INTO civiczone.staff_flagged_answer_reviews
            (id, zone_code, question_text, original_answer, flag_reason, citations,
             status, improved_answer, improvement_notes, reviewed_by, created_by,
             created_at, updated_at, visibility)
            VALUES (:id, :zone_code, :question_text, :original_answer, :flag_reason,
                    CAST(:citations AS JSONB), 'improved', :improved_answer,
                    :improvement_notes, :reviewed_by, :created_by, NOW(), NOW(), 'staff_only')
        """),
            {
                "id": rid,
                "zone_code": rec.get("zone_code") or "unknown",
                "question_text": rec.get("question_text") or "",
                "original_answer": rec.get("answer_text") or "",
                "flag_reason": notes or "Human review",
                "citations": json.dumps(rec.get("citation_payload") or [], default=str),
                "improved_answer": answer,
                "improvement_notes": notes,
                "reviewed_by": actor_id,
                "created_by": actor_id,
            },
        )
        conn.execute(
            text("""
            UPDATE civiczone.staff_ambiguity_review_items SET status = :status, resolution = :resolution,
                assigned_to = :assigned_to, updated_at = NOW() WHERE source_question_id = :qid
        """),
            {
                "status": queue_status,
                "resolution": answer,
                "assigned_to": actor_id,
                "qid": question_id,
            },
        )
        if queue_status in ("open", "in_review"):
            existing_queue_item = conn.execute(
                text(
                    "SELECT * FROM civiczone.staff_ambiguity_review_items WHERE source_question_id = :question_id LIMIT 1"
                ),
                {"question_id": question_id},
            ).first()
            if existing_queue_item is None:
                conn.execute(
                    text("""
                    INSERT INTO civiczone.staff_ambiguity_review_items
                    (id,zone_code,question_text,reason,status,source_question_id,created_by,created_at,updated_at,visibility)
                    VALUES (:id,:zone_code,:question_text,:reason,:status,:source_question_id,:created_by,now(),now(),'staff_only')
                """),
                    {
                        "id": str(uuid.uuid4()),
                        "zone_code": rec["zone_code"],
                        "question_text": rec["question_text"],
                        "reason": notes or "Staff requested planner review",
                        "status": queue_status,
                        "source_question_id": question_id,
                        "created_by": actor_id,
                    },
                )
    return {
        "event_id": eid,
        "review": {"id": rid, "answer": answer, "notes": notes, "queue_status": queue_status},
    }


def outline(engine, title, question_ids, actor):
    if not question_ids:
        raise ValueError("question_ids must not be empty")
    if not isinstance(title, str) or len(title) > 255:
        raise ValueError("title must be a string <= 255 chars")
    placeholders = ",".join([f":id{i}" for i in range(len(question_ids))])
    params = {f"id{i}": qid for i, qid in enumerate(question_ids)}
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"SELECT * FROM civiczone.zone_question_ledger_records WHERE id IN ({placeholders})"
            ),
            params,
        ).fetchall()
        found = {r._mapping["id"]: dict(r._mapping) for r in rows}
        missing = [q for q in question_ids if q not in found]
        if missing:
            raise ValueError(f"missing questions: {missing}")
        source_questions = [_norm(found[q]) for q in question_ids]
        for qid in question_ids:
            conn.execute(
                text("""
                INSERT INTO civiczone.question_events
                (id, question_id, actor_id, event_type, payload, created_at)
                VALUES (:id, :question_id, :actor_id, 'report_outline', CAST(:payload AS JSONB), NOW())
            """),
                {
                    "id": str(uuid.uuid4()),
                    "question_id": qid,
                    "actor_id": actor,
                    "payload": json.dumps({"title": title, "question_id": qid}, default=str),
                },
            )
    sections = {
        "IssueSummary": [q["question_text"] for q in source_questions],
        "CodeReferences": [
            citation
            for q in source_questions
            for citation in (q.get("context") or {}).get("citations", [])
        ],
        "StaffReview": "Human review; draft only. Original snapshots retained.",
    }
    return {
        "title": title,
        "disclaimer": "Draft staff outline only.",
        "source_questions": source_questions,
        "sections": sections,
    }
