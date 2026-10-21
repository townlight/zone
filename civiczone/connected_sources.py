import hashlib
import json
import uuid
from contextlib import contextmanager

from sqlalchemy import text


@contextmanager
def _connect(engine):
    with engine.begin() as conn:
        yield conn


def _loads(v):
    if isinstance(v, (dict, list)) or v is None:
        return v
    try:
        return json.loads(v)
    except Exception:
        return v


def _dump(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(text_value):
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _question(conn, qid):
    row = (
        conn.execute(
            text(
                "SELECT id,question_text,audience,context,created_at,actor_id "
                "FROM civiczone.zone_question_ledger_records WHERE id=:qid"
            ),
            {"qid": qid},
        )
        .mappings()
        .first()
    )
    if not row:
        raise ValueError("question not found")
    q = dict(row)
    q["context"] = _loads(q.get("context"))
    return q


def _event(conn, qid, actor, kind, payload, eventid=None):
    eventid = eventid or str(uuid.uuid4())
    conn.execute(
        text(
            "INSERT INTO civiczone.question_events "
            "(id,question_id,actor_id,event_type,payload,created_at) "
            "VALUES (:id,:qid,:actor,:kind,CAST(:payload AS JSONB),NOW())"
        ),
        {
            "id": eventid,
            "qid": qid,
            "actor": actor,
            "kind": kind,
            "payload": _dump(payload),
        },
    )
    return eventid


def _as_docs(result):
    if result is None:
        return []
    if isinstance(result, dict):
        for key in ("documents", "results", "items"):
            if key in result and isinstance(result[key], list):
                return result[key]
        return [result]
    if isinstance(result, (list, tuple)):
        return list(result)
    return [result]


def _permitted(provider, source_id, sha):
    try:
        docs = _as_docs(provider(source_id=source_id))
    except Exception as exc:
        raise ValueError("source unavailable") from exc
    if len(docs) != 1:
        raise ValueError("source must resolve exactly once")
    doc = docs[0]
    if not isinstance(doc, dict):
        raise ValueError("invalid source")
    if doc.get("visibility") != "public":
        raise ValueError("source not public")
    text_value = doc.get("text")
    if not isinstance(text_value, str):
        raise ValueError("source text missing")
    actual = _sha(text_value)
    if actual != sha:
        raise ValueError("source hash mismatch")
    if doc.get("source_id") != source_id or doc.get("sha256") != actual:
        raise ValueError("source sha256 mismatch")
    return doc


def link_meeting(engine, qid, p, actor, provider):
    relation = p["relation"]
    if relation not in ("hearing", "context", "precedent"):
        raise ValueError("invalid relation")
    source_id = p["source_id"]
    expected_sha256 = p["expected_sha256"]
    with _connect(engine) as conn:
        _question(conn, qid)
        doc = _permitted(provider, source_id, expected_sha256)
        return _event(
            conn,
            qid,
            actor,
            "meeting_link",
            {"relation": relation, "source": doc},
        )


def history(engine, qid, provider):
    with _connect(engine) as conn:
        q = _question(conn, qid)
        rows = (
            conn.execute(
                text(
                    "SELECT id,question_id,actor_id,event_type,payload,created_at "
                    "FROM civiczone.question_events WHERE question_id=:qid "
                    "ORDER BY created_at,id"
                ),
                {"qid": qid},
            )
            .mappings()
            .all()
        )
        events = []
        for row in rows:
            event = dict(row)
            event["payload"] = _loads(event.get("payload"))
            if event.get("event_type") == "meeting_link":
                payload = event.get("payload") or {}
                source = payload.get("source") or {}
                source_id = source.get("source_id")
                sha = source.get("sha256")
                if source_id and sha:
                    try:
                        _permitted(provider, source_id, sha)
                        payload["source"] = source
                    except ValueError:
                        payload = {"source_id": source_id, "status": "unavailable"}
                else:
                    payload = {"source_id": source_id, "status": "unavailable"}
                event["payload"] = payload
            elif event.get("event_type") == "source_snapshot":
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    payload = {}
                source_id = payload.get("source_id")
                revoked = False
                for ms in payload.get("meeting_sources") or []:
                    if not isinstance(ms, dict):
                        revoked = True
                        break
                    ms_source_id = ms.get("source_id")
                    ms_sha = ms.get("sha256")
                    if not ms_source_id or not ms_sha:
                        revoked = True
                        break
                    try:
                        _permitted(provider, ms_source_id, ms_sha)
                    except ValueError:
                        revoked = True
                        break
                if revoked:
                    payload = {"source_id": source_id, "status": "unavailable"}
                event["payload"] = payload
            events.append(event)
        return {"question": q, "events": events}


def create_snapshot(engine, qid, p, actor, provider):
    visibility = p["visibility"]
    if visibility not in ("public", "staff_only"):
        raise ValueError("invalid visibility")
    meeting_event_ids = list(p.get("meeting_event_ids") or [])
    with _connect(engine) as conn:
        q = _question(conn, qid)
        if visibility == "public" and str(q.get("audience", "")).lower() == "staff":
            raise ValueError("staff question cannot be public")

        links = []
        meeting_sources = []
        for eid in meeting_event_ids:
            row = (
                conn.execute(
                    text(
                        "SELECT id,payload FROM civiczone.question_events "
                        "WHERE id::text=:eid AND question_id=:qid AND event_type='meeting_link'"
                    ),
                    {"eid": eid, "qid": qid},
                )
                .mappings()
                .first()
            )
            if not row:
                raise ValueError("missingrow")
            payload = _loads(row["payload"]) or {}
            relation = payload.get("relation")
            source = payload.get("source") or {}
            source_id = source.get("source_id")
            sha = source.get("sha256")
            if not source_id or not sha:
                raise ValueError("missingidentity")
            doc = _permitted(provider, source_id, sha)
            links.append(
                {**doc, "relation": relation, "context_kind": "historical_not_legal_authority"}
            )
            meeting_sources.append({"source_id": source_id, "sha256": sha})

        hc = (
            conn.execute(
                text(
                    "SELECT id,payload FROM civiczone.question_events "
                    "WHERE question_id=:qid AND event_type='human_correction' "
                    "ORDER BY created_at DESC,id DESC LIMIT 1"
                ),
                {"qid": qid},
            )
            .mappings()
            .first()
        )
        latest_answer = None
        latest_answer_event_id = None
        if hc:
            hp = _loads(hc["payload"]) or {}
            latest_answer = hp.get("answer")
            if latest_answer is not None:
                latest_answer_event_id = str(hc["id"])

        canonical_obj = {
            "question_id": qid,
            "question_text": q["question_text"],
            "context": q.get("context"),
            "created_at": _iso(q.get("created_at")),
            "historical_context": links,
            "answer": latest_answer
            if latest_answer is not None
            else (q.get("context") or {}).get("answer", ""),
            "human_answer_event_id": latest_answer_event_id,
            "disclaimer": "Informational only; not a determination.",
        }
        canonical_text = _dump(canonical_obj)
        canonical_sha = _sha(canonical_text)
        version_uuid = str(uuid.uuid4())
        source_id = f"townlight:zoning:snapshot:{version_uuid}"
        source = {
            "source_id": source_id,
            "kind": "zoning",
            "title": f"Zoning question {qid}",
            "text": canonical_text,
            "sha256": canonical_sha,
            "visibility": visibility,
            "version": version_uuid,
            "citation": f"Source snapshot {source_id}",
            "question_id": qid,
            "meeting_sources": meeting_sources,
        }
        _event(conn, qid, actor, "source_snapshot", source, eventid=version_uuid)
        return source


def public_documents(engine, provider, query="", source_id=None):
    with _connect(engine) as conn:
        sql = "SELECT payload FROM civiczone.question_events WHERE event_type='source_snapshot'"
        params = {}
        if source_id is not None:
            sql += " AND payload->>'source_id'=:source_id"
            params["source_id"] = source_id
        sql += " ORDER BY created_at,id"
        rows = conn.execute(text(sql), params).mappings().all()

    out = []
    qfold = query.casefold()
    for row in rows:
        payload = _loads(row["payload"]) or {}
        if payload.get("visibility") != "public":
            continue
        text_value = payload.get("text")
        sha = payload.get("sha256")
        if not isinstance(text_value, str) or not sha or _sha(text_value) != sha:
            continue
        revoked = False
        for ms in payload.get("meeting_sources") or []:
            try:
                _permitted(provider, ms["source_id"], ms["sha256"])
            except Exception:
                revoked = True
                break
        if revoked:
            continue
        title = payload.get("title", "")
        if qfold and qfold not in title.casefold() and qfold not in text_value.casefold():
            continue
        out.append(payload)
        if len(out) >= 51:
            break
    return out
