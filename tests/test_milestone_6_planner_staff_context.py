from fastapi.testclient import TestClient

from civiczone.main import app
from civiczone.qa import answer_zoning_question
from civiczone.staff_context import classify_for_planner_review, get_staff_precedent

client = TestClient(app, client=("127.0.0.1", 50000))


def test_variance_question_escalates_to_planner_review() -> None:
    result = classify_for_planner_review("Do I need a variance for this setback?")

    assert result.status == "escalate"
    assert "planner judgment" in result.reason


def test_non_trigger_question_does_not_escalate() -> None:
    result = classify_for_planner_review("What is the front setback?")

    assert result.status == "not_escalated"


def test_staff_precedent_is_staff_only() -> None:
    precedent = get_staff_precedent("historic-adu")

    assert precedent is not None
    assert precedent.visibility == "staff_only"


def test_resident_answer_never_exposes_staff_precedent() -> None:
    result = answer_zoning_question(zone_code="R-2", question="Can I build an ADU?")

    assert "Historic overlay ADU review pattern" not in result.answer
    assert "staff reports" not in result.answer


def test_planner_review_api_success_shape() -> None:
    response = client.post(
        "/api/v1/civiczone/planner-review/classify",
        json={"question": "Do I need a CUP for this use?"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "escalate"


def test_staff_precedent_api_is_explicitly_staff_only() -> None:
    response = client.get("/api/v1/civiczone/staff/precedents/historic-adu")

    assert response.status_code == 401
    assert "Trusted identity header missing" in response.json()["detail"]["message"]


def test_staff_precedent_api_allows_staff_header() -> None:
    response = client.get(
        "/api/v1/civiczone/staff/precedents/historic-adu",
        headers={"X-CivicZone-Principal": "planner@example.gov", "X-CivicZone-Role": "staff"},
    )

    assert response.status_code == 200
    assert response.json()["visibility"] == "staff_only"
