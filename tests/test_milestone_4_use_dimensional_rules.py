from fastapi.testclient import TestClient

from civiczone.main import app
from civiczone.rule_lookup import (
    DimensionalRuleResult,
    RuleLookupError,
    UseRuleResult,
    lookup_dimensional_rule,
    lookup_use_rule,
)

client = TestClient(app)


def test_use_rule_lookup_normalizes_zone_and_use() -> None:
    result = lookup_use_rule(zone_code="r-2", use="ADU")

    assert isinstance(result, UseRuleResult)
    assert result.status == "conditional"
    assert result.citation == "CMC 18.42.030"
    assert "not a zoning determination" in result.disclaimer


def test_use_rule_unknown_is_actionable() -> None:
    result = lookup_use_rule(zone_code="R-9", use="helipad")

    assert isinstance(result, RuleLookupError)
    assert "not found" in result.message
    assert "ADU" in result.fix


def test_dimensional_rule_lookup_returns_citation() -> None:
    result = lookup_dimensional_rule(zone_code="R-2", rule_type="height")

    assert isinstance(result, DimensionalRuleResult)
    assert result.value == "35 feet maximum"
    assert result.citation == "CMC 18.20.050(B)"


def test_use_rule_api_success_shape() -> None:
    response = client.post("/api/v1/civiczone/rules/use", json={"zone_code": "R-2", "use": "restaurant"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not listed"
    assert payload["review_path"] == "Escalate to planning staff for interpretation."
    assert payload["citation"] == "CMC 18.20.020"
    assert "not a zoning determination" in payload["disclaimer"]


def test_dimensional_rule_api_success_shape() -> None:
    response = client.post(
        "/api/v1/civiczone/rules/dimensional",
        json={"zone_code": "R-2", "rule_type": "front_setback"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["value"] == "20 feet minimum"
    assert payload["citation"] == "CMC 18.20.050(A)"


def test_rule_apis_return_actionable_404() -> None:
    response = client.post("/api/v1/civiczone/rules/use", json={"zone_code": "R-2", "use": "airport"})

    assert response.status_code == 404
    assert "Try zone_code" in response.json()["detail"]["fix"]
