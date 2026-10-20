CivicZone
=========

CivicZone is CivicSuite's parcel-aware zoning and land-use Q&A module.

Current state: CivicZone v0.2.2 corrective demotion state. This narrow truth-repair release is no functional upgrade; it exists solely to supersede the false v1.0.0 release from 2026-05-21 in GitHub's Latest impression, with the CivicCore pin unchanged. This repo contains a FastAPI service, health/root endpoints, documentation gates, canonical zoning schema models, Alembic migrations, deterministic parcel/zone lookup, cited use-rule lookup, cited dimensional-rule prechecks, resident Q&A with refusal and escalation rules, optional database-backed parcel/rule, resident-question ledger, and staff-workflow records through CIVICZONE_PARCEL_RULE_DB_URL, staff-only precedent protection, a browser-usable resident UI at /civiczone, a staff workflow shell at /civiczone/staff, adversarial local integration mocks, trusted-proxy staff access validation, and CivicCore v1.1.0 release-wheel dependency alignment. See docs/release-recovery-status.md for historical recovery context and current release evidence.

Product boundaries:

- CivicZone gives informational zoning context with citations.
- CivicZone refuses or escalates zoning-determination, legal-advice, out-of-jurisdiction, stale-data, low-confidence, and uncited-answer requests.
- CivicZone does not make zoning determinations, approve permits, replace planner review, or call live external vendor systems by default.
- CivicZone integration behavior is validated with local adversarial mocks for Esri ArcGIS REST, GeoJSON fallback, CivicCode, CivicClerk, CivicPlan, CivicAccess, county assessor, and CKAN boundaries.

Set CIVICZONE_PARCEL_RULE_DB_URL to enable persistent parcel, use-rule, dimensional-rule, resident-question ledger, and staff workflow records. When unset, CivicZone uses deterministic in-memory sample data and does not persist question or staff workflow rows.

Staff workflow endpoints require trusted municipal access headers from a configured trusted proxy/source. Local development accepts loopback by default. Shared deployments should set CIVICZONE_STAFF_TRUSTED_PROXY_CIDRS and strip client-supplied staff headers before requests reach CivicZone.

- X-CivicZone-Principal
- X-CivicZone-Role: planner, staff, or zoning_admin

Developer quickstart:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
bash scripts/verify-release.sh

Code license: AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. See LICENSE and LICENSE-EXCEPTION.md.
Documentation license: CC BY 4.0.
