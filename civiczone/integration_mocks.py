from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

SUPPORTED_PROVIDERS = frozenset(
    {
        "esri_arcgis_rest",
        "geojson_fallback",
        "civiccode_section_resolution",
        "civicclerk_precedent_minutes",
        "civicplan_policy_context",
        "civicaccess_plain_language_rewrite",
        "county_assessor_import",
        "ckan_anonymized_trend_export",
    }
)

NETWORK_PREFIXES = ("http://", "https://")
SENSITIVE_TREND_FIELDS = frozenset(
    {"address", "applicant", "email", "name", "owner", "owner_name", "parcel_number", "phone"}
)


@dataclass(frozen=True)
class IntegrationError:
    provider: str
    message: str
    fix: str
    code: str


@dataclass(frozen=True)
class IntegrationResult:
    provider: str
    records: tuple[dict[str, Any], ...]
    source: str
    warnings: tuple[str, ...] = ()
    stale: bool = False


class LocalIntegrationAdapter:
    provider: str
    dependency: str | None = None

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        raise NotImplementedError


class CivicZoneIntegrationMockLayer:
    """Local-only integration contract runner for v1 adversarial validation."""

    def __init__(
        self,
        *,
        adapters: tuple[LocalIntegrationAdapter, ...] | None = None,
        dependency_state: dict[str, bool] | None = None,
        now: datetime | None = None,
    ) -> None:
        configured = adapters or (
            EsriArcGISRestMockAdapter(),
            GeoJSONFallbackMockAdapter(),
            CivicCodeSectionResolutionMockAdapter(),
            CivicClerkPrecedentMinutesMockAdapter(),
            CivicPlanPolicyContextMockAdapter(),
            CivicAccessPlainLanguageRewriteMockAdapter(),
            CountyAssessorImportMockAdapter(),
            CKANAnonymizedTrendExportMockAdapter(),
        )
        self.adapters = {adapter.provider: adapter for adapter in configured}
        self.dependency_state = dependency_state or {}
        self.now = now or datetime.now(UTC)

    def run(self, provider: str, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        if provider not in SUPPORTED_PROVIDERS or provider not in self.adapters:
            return IntegrationError(
                provider=provider,
                message="Unsupported CivicZone mock integration provider.",
                fix="Use one of the supported local mock provider identifiers for v1 validation.",
                code="unsupported_provider",
            )
        declared_provider = payload.get("provider")
        if declared_provider is not None and declared_provider != provider:
            return IntegrationError(
                provider=provider,
                message="Payload provider does not match the requested integration provider.",
                fix="Set payload.provider to the same supported provider name used by the adapter call.",
                code="spoofed_provider",
            )
        network_error = _reject_live_endpoint(provider, payload)
        if network_error is not None:
            return network_error
        adapter = self.adapters[provider]
        if adapter.dependency and self.dependency_state.get(adapter.dependency) is False:
            return IntegrationError(
                provider=provider,
                message=f"{adapter.dependency} dependency is unavailable in the local mock layer.",
                fix="Use the adapter's fixture payload or mark the dependency available before validation.",
                code="dependency_unavailable",
            )
        result = adapter.fetch(payload)
        if isinstance(result, IntegrationError):
            return result
        if _is_stale(payload.get("source_updated_at"), now=self.now):
            return IntegrationResult(
                provider=result.provider,
                records=result.records,
                source=result.source,
                warnings=(*result.warnings, "Source data is stale; refresh the local fixture before relying on it."),
                stale=True,
            )
        return result


class EsriArcGISRestMockAdapter(LocalIntegrationAdapter):
    provider = "esri_arcgis_rest"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            return _malformed(self.provider, "features must be a non-empty list of ArcGIS feature objects.")
        records = []
        for feature in features:
            attributes = feature.get("attributes") if isinstance(feature, dict) else None
            if not isinstance(attributes, dict) or not attributes.get("APN") or not attributes.get("ZoneCode"):
                return _malformed(self.provider, "Each feature must include attributes.APN and attributes.ZoneCode.")
            records.append(
                {
                    "parcel_number": attributes["APN"],
                    "zone_code": attributes["ZoneCode"],
                    "zone_name": attributes.get("ZoneName", "Unknown zone"),
                    "geometry": feature.get("geometry", {}),
                }
            )
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local ArcGIS REST fixture")


class GeoJSONFallbackMockAdapter(LocalIntegrationAdapter):
    provider = "geojson_fallback"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
            return _malformed(self.provider, "GeoJSON fallback payload must be a FeatureCollection with features.")
        records = []
        for feature in payload["features"]:
            properties = feature.get("properties") if isinstance(feature, dict) else None
            if not isinstance(properties, dict) or not properties.get("parcel_number"):
                return _malformed(self.provider, "Each GeoJSON feature needs properties.parcel_number.")
            records.append(
                {
                    "parcel_number": properties["parcel_number"],
                    "zone_code": properties.get("zone_code", "UNKNOWN"),
                    "geometry": feature.get("geometry"),
                }
            )
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local GeoJSON fixture")


class CivicCodeSectionResolutionMockAdapter(LocalIntegrationAdapter):
    provider = "civiccode_section_resolution"
    dependency = "civiccode"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        section_id = payload.get("section_id")
        sections = payload.get("sections")
        if not section_id or not isinstance(sections, dict) or section_id not in sections:
            return _malformed(self.provider, "Provide section_id and a sections map containing that section.")
        section = sections[section_id]
        if not isinstance(section, dict) or not section.get("citation") or not section.get("text"):
            return _malformed(self.provider, "Resolved CivicCode sections need citation and text.")
        return IntegrationResult(
            provider=self.provider,
            records=({"citation": section["citation"], "text": section["text"]},),
            source="local CivicCode section fixture",
        )


class CivicClerkPrecedentMinutesMockAdapter(LocalIntegrationAdapter):
    provider = "civicclerk_precedent_minutes"
    dependency = "civicclerk"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        minutes = payload.get("minutes")
        if not isinstance(minutes, list):
            return _malformed(self.provider, "Provide minutes as a list of local precedent records.")
        records = []
        for minute in minutes:
            if not isinstance(minute, dict) or not minute.get("minute_id") or not minute.get("summary"):
                return _malformed(self.provider, "Each minute needs minute_id and summary.")
            records.append(
                {
                    "minute_id": minute["minute_id"],
                    "summary": minute["summary"],
                    "visibility": minute.get("visibility", "staff_only"),
                }
            )
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local CivicClerk minutes fixture")


class CivicPlanPolicyContextMockAdapter(LocalIntegrationAdapter):
    provider = "civicplan_policy_context"
    dependency = "civicplan"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        policies = payload.get("policies")
        if not isinstance(policies, list) or not policies:
            return _malformed(self.provider, "Provide policies as a non-empty list of local plan policy records.")
        records = []
        for policy in policies:
            if not isinstance(policy, dict) or not policy.get("policy_id") or not policy.get("context"):
                return _malformed(self.provider, "Each policy needs policy_id and context.")
            records.append({"policy_id": policy["policy_id"], "context": policy["context"]})
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local CivicPlan policy fixture")


class CivicAccessPlainLanguageRewriteMockAdapter(LocalIntegrationAdapter):
    provider = "civicaccess_plain_language_rewrite"
    dependency = "civicaccess"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return _malformed(self.provider, "Provide non-empty text to rewrite.")
        rewritten = text.replace("pursuant to", "under").replace("shall", "must")
        return IntegrationResult(
            provider=self.provider,
            records=({"plain_language": rewritten, "disclaimer": "Informational summary only."},),
            source="local CivicAccess rewrite fixture",
        )


class CountyAssessorImportMockAdapter(LocalIntegrationAdapter):
    provider = "county_assessor_import"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        parcels = payload.get("parcels")
        if not isinstance(parcels, list) or not parcels:
            return _malformed(self.provider, "Provide parcels as a non-empty list from the local assessor fixture.")
        records = []
        for parcel in parcels:
            if not isinstance(parcel, dict) or not parcel.get("parcel_number") or not parcel.get("land_use"):
                return _malformed(self.provider, "Each assessor parcel needs parcel_number and land_use.")
            records.append(
                {
                    "parcel_number": parcel["parcel_number"],
                    "land_use": parcel["land_use"],
                    "assessed_year": parcel.get("assessed_year"),
                }
            )
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local assessor import fixture")


class CKANAnonymizedTrendExportMockAdapter(LocalIntegrationAdapter):
    provider = "ckan_anonymized_trend_export"

    def fetch(self, payload: dict[str, Any]) -> IntegrationResult | IntegrationError:
        trends = payload.get("trends")
        if not isinstance(trends, list) or not trends:
            return _malformed(self.provider, "Provide anonymized trends as a non-empty list.")
        records = []
        for trend in trends:
            if not isinstance(trend, dict) or not trend.get("bucket") or "count" not in trend:
                return _malformed(self.provider, "Each CKAN trend needs bucket and count.")
            sensitive = SENSITIVE_TREND_FIELDS.intersection(trend)
            if sensitive:
                return IntegrationError(
                    provider=self.provider,
                    message="CKAN trend export contains fields that could identify a person or parcel.",
                    fix=f"Remove sensitive fields before export: {', '.join(sorted(sensitive))}.",
                    code="not_anonymized",
                )
            records.append(dict(trend))
        return IntegrationResult(provider=self.provider, records=tuple(records), source="local CKAN trend fixture")


def _reject_live_endpoint(provider: str, payload: dict[str, Any]) -> IntegrationError | None:
    for key in ("url", "endpoint", "service_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith(NETWORK_PREFIXES):
            return IntegrationError(
                provider=provider,
                message="Live external calls are disabled for CivicZone v1 integration mocks.",
                fix="Use local fixture data and omit http/https endpoints when running adversarial validation.",
                code="air_gap_violation",
            )
    return None


def _is_stale(value: object, *, now: datetime) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = _parse_datetime(value)
    if parsed is None:
        return True
    return parsed < now - timedelta(days=370)


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _malformed(provider: str, detail: str) -> IntegrationError:
    return IntegrationError(
        provider=provider,
        message=f"Malformed local fixture payload: {detail}",
        fix="Repair the local mock fixture shape before retrying; no live fallback will be attempted.",
        code="malformed_payload",
    )
