from __future__ import annotations

from fastapi.testclient import TestClient

import civiczone.main as main_module
from civiczone.main import app
from civiczone.parcel_lookup import ParcelLookupRepository
from civiczone.rule_lookup import DIMENSIONAL_RULES, USE_RULES, RuleLookupRepository

client = TestClient(app)


def test_parcel_and_rule_records_persist_seeded_lookup_data(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'parcel-rules.db'}"
    parcels = ParcelLookupRepository(db_url=db_url)
    rules = RuleLookupRepository(db_url=db_url)

    parcel = parcels.lookup(parcel_number="100-200-300")
    use_rule = rules.lookup_use_rule(zone_code="r-2", use="ADU")
    dimensional = rules.lookup_dimensional_rule(zone_code="R-2", rule_type="height")

    second_parcels = ParcelLookupRepository(db_url=db_url, seed_defaults=False)
    second_rules = RuleLookupRepository(db_url=db_url, seed_defaults=False)

    assert second_parcels.lookup(address="123 main st") == parcel
    assert second_rules.lookup_use_rule(zone_code="R-2", use="adu") == use_rule
    assert second_rules.lookup_dimensional_rule(zone_code="r-2", rule_type="HEIGHT") == dimensional


def test_api_uses_configured_parcel_rule_database(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api-parcel-rules.db"
    db_url = f"sqlite:///{db_path}"
    seed_rules = RuleLookupRepository(db_url=db_url, seed_defaults=False)
    seed_rules.seed_use_rules(USE_RULES.values())
    seed_rules.seed_dimensional_rules(DIMENSIONAL_RULES.values())
    seed_rules.engine.dispose()
    monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", db_url)

    try:
        parcel_response = client.post(
            "/api/v1/civiczone/parcels/lookup",
            json={"address": "123 main st"},
        )
        use_response = client.post(
            "/api/v1/civiczone/rules/use",
            json={"zone_code": "r-2", "use": "ADU"},
        )
        dimensional_response = client.post(
            "/api/v1/civiczone/rules/dimensional",
            json={"zone_code": "R-2", "rule_type": "height"},
        )
    finally:
        if main_module._parcel_lookup_repository is not None:
            main_module._parcel_lookup_repository.engine.dispose()
            main_module._parcel_lookup_repository = None
        if main_module._rule_lookup_repository is not None:
            main_module._rule_lookup_repository.engine.dispose()
            main_module._rule_lookup_repository = None
        if main_module._question_ledger_repository is not None:
            main_module._question_ledger_repository.engine.dispose()
            main_module._question_ledger_repository = None
        main_module._parcel_rule_db_url = None

    assert parcel_response.status_code == 200
    assert parcel_response.json()["zone"] == {"code": "R-2", "name": "Medium Density Residential"}
    assert use_response.status_code == 200
    assert use_response.json()["status"] == "conditional"
    assert dimensional_response.status_code == 200
    assert dimensional_response.json()["value"] == "35 feet maximum"
    db_path.unlink()


def test_repository_cache_resets_when_database_url_changes(monkeypatch, tmp_path) -> None:
    first_db_url = f"sqlite:///{tmp_path / 'first.db'}"
    second_db_url = f"sqlite:///{tmp_path / 'second.db'}"

    try:
        monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", first_db_url)
        first_parcels = main_module._get_parcel_repository()

        monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", second_db_url)
        second_rules = main_module._get_rule_repository()

        assert first_parcels is not None
        assert second_rules is not None
        assert main_module._parcel_lookup_repository is None
        assert main_module._parcel_rule_db_url == second_db_url
    finally:
        if main_module._parcel_lookup_repository is not None:
            main_module._parcel_lookup_repository.engine.dispose()
            main_module._parcel_lookup_repository = None
        if main_module._rule_lookup_repository is not None:
            main_module._rule_lookup_repository.engine.dispose()
            main_module._rule_lookup_repository = None
        if main_module._question_ledger_repository is not None:
            main_module._question_ledger_repository.engine.dispose()
            main_module._question_ledger_repository = None
        main_module._parcel_rule_db_url = None
