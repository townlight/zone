import pytest
from fastapi.testclient import TestClient

import civiczone.main as main_module
from civiczone.main import app

client = TestClient(app, client=("127.0.0.1", 50000))
untrusted_client = TestClient(app, client=("203.0.113.10", 50000))
STAFF_HEADERS = {"X-CivicZone-Principal": "planner@example.gov", "X-CivicZone-Role": "staff"}
RESIDENT_HEADERS = {"X-CivicZone-Principal": "resident@example.gov", "X-CivicZone-Role": "resident"}


@pytest.fixture(autouse=True)
def reset_staff_workflows() -> None:
    main_module._reset_staff_workflow_store()


def test_staff_workflow_api_rejects_missing_and_underprivileged_auth() -> None:
    missing = client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
    )
    underprivileged = client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
        headers=RESIDENT_HEADERS,
    )

    assert missing.status_code == 401
    assert "X-CivicZone-Principal" in missing.json()["detail"]["fix"]
    assert underprivileged.status_code == 403
    assert underprivileged.json()["detail"]["required_roles"] == [
        "planner",
        "staff",
        "zoning_admin",
    ]


def test_staff_workflow_api_rejects_spoofed_headers_from_untrusted_source() -> None:
    response = untrusted_client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
        headers=STAFF_HEADERS,
    )

    assert response.status_code == 403
    assert "approved proxy" in response.json()["detail"]["message"]
    assert "strip client-supplied copies" in response.json()["detail"]["fix"]


def test_planner_question_answer_returns_code_cross_references() -> None:
    response = client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
        headers=STAFF_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["visibility"] == "staff_only"
    assert payload["citations"] == ["CMC 18.20.050(A)"]
    assert payload["code_cross_references"][0]["citation"] == "CMC 18.20.050(A)"
    assert payload["code_cross_references"][0]["source"] == "CivicCode section reference"


def test_staff_only_workflow_data_does_not_leak_to_resident_answer() -> None:
    flagged = client.post(
        "/api/v1/civiczone/staff/flagged-answers",
        json={
            "zone_code": "R-2",
            "question": "What staff precedent applies?",
            "original_answer": "Prior staff reports required design review.",
            "flag_reason": "Staff-only precedent should not be resident-facing.",
            "citations": ["CMC 18.42.030"],
        },
        headers=STAFF_HEADERS,
    )
    resident = client.post(
        "/api/v1/civiczone/questions/answer",
        json={"zone_code": "R-2", "question": "Can I build an ADU?"},
    )

    assert flagged.status_code == 200
    assert resident.status_code == 200
    resident_text = str(resident.json())
    assert "Prior staff reports" not in resident_text
    assert "staff_only" not in resident_text
    assert "flagged" not in resident_text


def test_ambiguity_review_queue_lifecycle() -> None:
    created = client.post(
        "/api/v1/civiczone/staff/ambiguity-reviews",
        json={
            "zone_code": "R-2",
            "question": "The overlay and base zone conflict. Which controls?",
            "reason": "Conflicting overlay interpretation needs planner review.",
        },
        headers=STAFF_HEADERS,
    )
    item_id = created.json()["id"]
    listed = client.get("/api/v1/civiczone/staff/ambiguity-reviews", headers=STAFF_HEADERS)
    updated = client.patch(
        f"/api/v1/civiczone/staff/ambiguity-reviews/{item_id}",
        json={
            "status": "resolved",
            "assigned_to": "senior-planner@example.gov",
            "resolution": "Overlay controls; cite the overlay section before responding.",
        },
        headers=STAFF_HEADERS,
    )

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["items"][0]["status"] == "open"
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    assert updated.json()["resolution"].startswith("Overlay controls")


def test_staff_question_analytics_flags_high_volume_questions() -> None:
    for _ in range(2):
        response = client.post(
            "/api/v1/civiczone/staff/questions/answer",
            json={"zone_code": "R-2", "question": "What is the front setback?"},
            headers=STAFF_HEADERS,
        )
        assert response.status_code == 200

    analytics = client.get(
        "/api/v1/civiczone/staff/questions/analytics?high_volume_threshold=2",
        headers=STAFF_HEADERS,
    )

    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["total_questions"] == 2
    assert payload["by_status"] == {"answered": 2}
    assert payload["high_volume_questions"][0]["count"] == 2
    assert payload["high_volume_questions"][0]["question_text"] == "What is the front setback?"


def test_staff_report_outline_uses_questions_and_queue_items() -> None:
    answer = client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
        headers=STAFF_HEADERS,
    )
    queue = client.post(
        "/api/v1/civiczone/staff/ambiguity-reviews",
        json={
            "zone_code": "R-2",
            "question": "Does the historic overlay change ADU review?",
            "reason": "Potential overlay ambiguity.",
        },
        headers=STAFF_HEADERS,
    )
    outline = client.post(
        "/api/v1/civiczone/staff/reports/outline",
        json={
            "title": "ADU and setback staff review",
            "question_ids": [answer.json()["id"]],
            "queue_item_ids": [queue.json()["id"]],
        },
        headers=STAFF_HEADERS,
    )

    assert outline.status_code == 200
    payload = outline.json()
    assert payload["visibility"] == "staff_only"
    assert payload["source_question_ids"] == [answer.json()["id"]]
    assert payload["source_queue_item_ids"] == [queue.json()["id"]]
    assert payload["sections"][1]["citations"] == ["CMC 18.20.050(A)"]
    assert "verify citations" in payload["disclaimer"].casefold()


def test_flagged_answer_review_can_be_improved() -> None:
    created = client.post(
        "/api/v1/civiczone/staff/flagged-answers",
        json={
            "zone_code": "R-2",
            "question": "Can I build an ADU?",
            "original_answer": "ADUs are always approved.",
            "flag_reason": "Overstates approval and misses the non-determination boundary.",
            "citations": ["CMC 18.42.030"],
        },
        headers=STAFF_HEADERS,
    )
    improved = client.patch(
        f"/api/v1/civiczone/staff/flagged-answers/{created.json()['id']}/improve",
        json={
            "improved_answer": (
                "In R-2, an ADU is conditional and requires planner review before reliance."
            ),
            "improvement_notes": "Restored citation-grounding and non-determination copy.",
        },
        headers=STAFF_HEADERS,
    )

    assert created.status_code == 200
    assert created.json()["status"] == "flagged"
    assert improved.status_code == 200
    assert improved.json()["status"] == "improved"
    assert improved.json()["reviewed_by"] == "planner@example.gov"


def test_staff_workflows_persist_when_database_is_configured(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'staff-workflows.db'}"
    monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", db_url)

    answer = client.post(
        "/api/v1/civiczone/staff/questions/answer",
        json={"zone_code": "R-2", "question": "What is the front setback?"},
        headers=STAFF_HEADERS,
    )
    queue = client.post(
        "/api/v1/civiczone/staff/ambiguity-reviews",
        json={
            "zone_code": "R-2",
            "question": "Does the overlay change the answer?",
            "reason": "Potential overlay conflict.",
        },
        headers=STAFF_HEADERS,
    )
    flagged = client.post(
        "/api/v1/civiczone/staff/flagged-answers",
        json={
            "zone_code": "R-2",
            "question": "Can I build an ADU?",
            "original_answer": "ADUs are always approved.",
            "flag_reason": "Overstates approval.",
            "citations": ["CMC 18.42.030"],
        },
        headers=STAFF_HEADERS,
    )

    assert answer.status_code == 200
    assert queue.status_code == 200
    assert flagged.status_code == 200

    main_module._reset_staff_workflow_store()

    analytics = client.get(
        "/api/v1/civiczone/staff/questions/analytics?high_volume_threshold=1",
        headers=STAFF_HEADERS,
    )
    listed = client.get("/api/v1/civiczone/staff/ambiguity-reviews", headers=STAFF_HEADERS)
    improved = client.patch(
        f"/api/v1/civiczone/staff/flagged-answers/{flagged.json()['id']}/improve",
        json={
            "improved_answer": "ADUs require conditional review before reliance.",
            "improvement_notes": "Persisted review survived store reset.",
        },
        headers=STAFF_HEADERS,
    )

    assert analytics.status_code == 200
    assert analytics.json()["total_questions"] == 1
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == queue.json()["id"]
    assert improved.status_code == 200
    assert improved.json()["status"] == "improved"
