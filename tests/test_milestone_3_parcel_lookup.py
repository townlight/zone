from fastapi.testclient import TestClient

from civiczone.main import app
from civiczone.parcel_lookup import ParcelLookupError, ParcelLookupResult, lookup_parcel

client = TestClient(app)


def test_lookup_parcel_by_number_returns_zone_context() -> None:
    result = lookup_parcel(parcel_number="100-200-300")

    assert isinstance(result, ParcelLookupResult)
    assert result.zone_code == "R-2"
    assert "Historic District" in result.overlays
    assert "not a zoning determination" in result.disclaimer


def test_lookup_parcel_by_address_is_case_insensitive() -> None:
    result = lookup_parcel(address="123 main st")

    assert isinstance(result, ParcelLookupResult)
    assert result.parcel_number == "100-200-300"


def test_lookup_unknown_parcel_returns_actionable_error() -> None:
    result = lookup_parcel(parcel_number="missing")

    assert isinstance(result, ParcelLookupError)
    assert "not found" in result.message
    assert "100-200-300" in result.fix


def test_api_lookup_success_shape() -> None:
    response = client.post("/api/v1/civiczone/parcels/lookup", json={"parcel_number": "100-200-300"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["zone"] == {"code": "R-2", "name": "Medium Density Residential"}
    assert payload["overlays"] == ["Historic District"]
    assert payload["source"].startswith("Sample fixture")
    assert "not a zoning determination" in payload["disclaimer"]


def test_api_lookup_requires_identifier() -> None:
    response = client.post("/api/v1/civiczone/parcels/lookup", json={})

    assert response.status_code == 422
    assert response.json()["detail"]["fix"].startswith("Send parcel_number")


def test_api_lookup_unknown_parcel_is_actionable_404() -> None:
    response = client.post("/api/v1/civiczone/parcels/lookup", json={"address": "999 Nowhere"})

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["message"] == "Parcel not found in the CivicZone sample dataset."
    assert "CIVICZONE_PARCEL_RULE_DB_URL" in detail["fix"]
