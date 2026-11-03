from datetime import UTC, datetime

from townlight_zoning.integration_mocks import (
    TownlightZoningIntegrationMockLayer,
    IntegrationError,
    IntegrationResult,
)


def test_all_v1_mock_integrations_return_local_contract_records() -> None:
    layer = TownlightZoningIntegrationMockLayer(
        dependency_state={
            "townlight_access": True,
            "townlight_meetings": True,
            "townlight_code": True,
            "townlight_planning": True,
        }
    )

    payloads = {
        "esri_arcgis_rest": {
            "provider": "esri_arcgis_rest",
            "features": [
                {
                    "attributes": {
                        "APN": "100-200-300",
                        "ZoneCode": "R-2",
                        "ZoneName": "Medium Density Residential",
                    },
                    "geometry": {"x": -105.1, "y": 39.7},
                }
            ],
        },
        "geojson_fallback": {
            "provider": "geojson_fallback",
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"parcel_number": "100-200-300", "zone_code": "R-2"},
                    "geometry": {"type": "Point", "coordinates": [-105.1, 39.7]},
                }
            ],
        },
        "townlight_code_section_resolution": {
            "provider": "townlight_code_section_resolution",
            "section_id": "18.20.020",
            "sections": {"18.20.020": {"citation": "CMC 18.20.020", "text": "R-2 uses table."}},
        },
        "townlight_meetings_precedent_minutes": {
            "provider": "townlight_meetings_precedent_minutes",
            "minutes": [{"minute_id": "M-1", "summary": "Historic overlay ADU review noted."}],
        },
        "townlight_planning_policy_context": {
            "provider": "townlight_planning_policy_context",
            "policies": [{"policy_id": "LU-1", "context": "Encourage infill near services."}],
        },
        "townlight_access_plain_language_rewrite": {
            "provider": "townlight_access_plain_language_rewrite",
            "text": "Applicants shall comply pursuant to CMC 18.20.020.",
        },
        "county_assessor_import": {
            "provider": "county_assessor_import",
            "parcels": [{"parcel_number": "100-200-300", "land_use": "Residential", "assessed_year": 2026}],
        },
        "ckan_anonymized_trend_export": {
            "provider": "ckan_anonymized_trend_export",
            "trends": [{"bucket": "R-2 ADU inquiries", "count": 12}],
        },
    }

    for provider, payload in payloads.items():
        result = layer.run(provider, payload)

        assert isinstance(result, IntegrationResult), provider
        assert result.provider == provider
        assert result.records
        assert result.source.startswith("local ")


def test_malformed_arcgis_payload_returns_actionable_error_without_fallback() -> None:
    layer = TownlightZoningIntegrationMockLayer()

    result = layer.run("esri_arcgis_rest", {"provider": "esri_arcgis_rest", "features": [{}]})

    assert isinstance(result, IntegrationError)
    assert result.code == "malformed_payload"
    assert "attributes.APN" in result.message
    assert "no live fallback" in result.fix


def test_unavailable_dependency_blocks_local_adapter_with_fix_path() -> None:
    layer = TownlightZoningIntegrationMockLayer(dependency_state={"townlight_planning": False})

    result = layer.run(
        "townlight_planning_policy_context",
        {
            "provider": "townlight_planning_policy_context",
            "policies": [{"policy_id": "LU-1", "context": "Encourage infill."}],
        },
    )

    assert isinstance(result, IntegrationError)
    assert result.code == "dependency_unavailable"
    assert "townlight_planning dependency is unavailable" in result.message
    assert "fixture payload" in result.fix


def test_spoofed_or_unsupported_provider_is_rejected_before_processing() -> None:
    layer = TownlightZoningIntegrationMockLayer()

    spoofed = layer.run(
        "geojson_fallback",
        {
            "provider": "esri_arcgis_rest",
            "type": "FeatureCollection",
            "features": [],
        },
    )
    unsupported = layer.run("shadow_provider", {"provider": "shadow_provider"})

    assert isinstance(spoofed, IntegrationError)
    assert spoofed.code == "spoofed_provider"
    assert isinstance(unsupported, IntegrationError)
    assert unsupported.code == "unsupported_provider"


def test_stale_data_is_flagged_but_local_records_are_preserved() -> None:
    layer = TownlightZoningIntegrationMockLayer(now=datetime(2026, 5, 7, tzinfo=UTC))

    result = layer.run(
        "county_assessor_import",
        {
            "provider": "county_assessor_import",
            "source_updated_at": "2024-01-01T00:00:00Z",
            "parcels": [{"parcel_number": "100-200-300", "land_use": "Residential"}],
        },
    )

    assert isinstance(result, IntegrationResult)
    assert result.stale is True
    assert result.records[0]["parcel_number"] == "100-200-300"
    assert any("stale" in warning for warning in result.warnings)


def test_air_gap_rejects_live_endpoints_before_adapter_logic() -> None:
    layer = TownlightZoningIntegrationMockLayer()

    result = layer.run(
        "esri_arcgis_rest",
        {
            "provider": "esri_arcgis_rest",
            "service_url": "https://example.test/arcgis/rest/services/zoning",
            "features": [],
        },
    )

    assert isinstance(result, IntegrationError)
    assert result.code == "air_gap_violation"
    assert "Live external calls are disabled" in result.message
    assert "local fixture data" in result.fix


def test_ckan_export_rejects_non_anonymized_trend_fields() -> None:
    layer = TownlightZoningIntegrationMockLayer()

    result = layer.run(
        "ckan_anonymized_trend_export",
        {
            "provider": "ckan_anonymized_trend_export",
            "trends": [{"bucket": "R-2 ADU inquiries", "count": 1, "parcel_number": "100-200-300"}],
        },
    )

    assert isinstance(result, IntegrationError)
    assert result.code == "not_anonymized"
    assert "identify a person or parcel" in result.message
    assert "parcel_number" in result.fix
