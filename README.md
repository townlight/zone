# CivicZone

CivicZone is CivicSuite's parcel-aware zoning and land-use Q&A module.

Current state: **v0.2.2 corrective demotion state - scaffold with partial persistence/workflow plumbing; no real AI layer, full frontend, real municipal data/search, or public-use gate. This narrow truth-repair release is no functional upgrade; it exists solely to supersede the false v1.0.0 release from 2026-05-21 in GitHub's Latest impression. The CivicCore pin is unchanged.**. This repo contains a FastAPI service, health/root endpoints, documentation gates, canonical zoning schema models, Alembic migrations, deterministic parcel/zone lookup, cited use-rule lookup, cited dimensional-rule prechecks, resident Q&A with refusal and escalation rules, optional database-backed parcel/rule, resident-question ledger, and staff-workflow records through `CIVICZONE_PARCEL_RULE_DB_URL`, staff-only precedent protection, a browser-usable resident UI at `/civiczone`, a staff workflow shell at `/civiczone/staff`, adversarial local integration mocks, trusted-proxy staff access validation, and CivicCore v1.1.0 release-wheel dependency alignment. See [docs/release-recovery-status.md](docs/release-recovery-status.md) for historical recovery context and current release evidence.

## Product Boundaries

- CivicZone gives informational zoning context with citations.
- CivicZone refuses or escalates zoning-determination, legal-advice, out-of-jurisdiction, stale-data, low-confidence, and uncited-answer requests.
- CivicZone does not make zoning determinations, approve permits, replace planner review, or call live external vendor systems by default.
- CivicZone integration behavior is validated with local adversarial mocks for Esri ArcGIS REST, GeoJSON fallback, CivicCode, CivicClerk, CivicPlan, CivicAccess, county assessor, and CKAN boundaries.

## Developer Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
bash scripts/verify-release.sh
```

## API Foundation

- `GET /` returns current module status and operator next step.
- `GET /health` returns package and CivicCore version information.
- `GET /civiczone` returns the accessible resident lookup UI.
- `GET /civiczone/staff` returns the staff workflow shell; staff API actions require trusted municipal access headers from an approved proxy/source.
- `POST /api/v1/civiczone/parcels/lookup` returns sample parcel zone context for `100-200-300` / `123 Main St`.
- `POST /api/v1/civiczone/rules/use` returns sample use status with citation.
- `POST /api/v1/civiczone/rules/dimensional` returns sample dimensional rule values with citation.
- `POST /api/v1/civiczone/questions/answer` answers sample resident questions only when citations are available and records a local question-ledger row when `CIVICZONE_PARCEL_RULE_DB_URL` is configured.
- `POST /api/v1/civiczone/planner-review/classify` identifies sample discretionary-review triggers.
- `GET /api/v1/civiczone/staff/precedents/{precedent_id}` returns staff-only sample precedent context.
- `POST /api/v1/civiczone/staff/questions/answer` gives staff Q&A with citations and informational boundaries.
- `POST /api/v1/civiczone/staff/ambiguity-reviews` creates planner review queue items.
- `GET /api/v1/civiczone/staff/questions/analytics` returns high-volume question analytics.
- `POST /api/v1/civiczone/staff/reports/outline` creates cited staff-report outline support.
- `POST /api/v1/civiczone/staff/flagged-answers` and `/improve` support staff review and improvement of flagged answers.

Resident question text is stored only when `CIVICZONE_PARCEL_RULE_DB_URL` is configured. Cities should treat those rows as operational records, avoid entering sensitive personal details into sample Q&A, and apply local retention/privacy policy before exposing the ledger outside staff operations.

Set `CIVICZONE_PARCEL_RULE_DB_URL` to enable persistent parcel, use-rule, dimensional-rule, resident-question ledger, and staff workflow records. When unset, CivicZone uses deterministic in-memory sample data and does not persist question or staff workflow rows.

Staff workflow endpoints require trusted municipal access headers from a configured trusted proxy/source. Local development accepts loopback by default. Shared deployments should set `CIVICZONE_STAFF_TRUSTED_PROXY_CIDRS` and strip client-supplied staff headers before requests reach CivicZone.

- `X-CivicZone-Principal`
- `X-CivicZone-Role: planner`, `staff`, or `zoning_admin`

## License

Code: AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. See [LICENSE](LICENSE) and [LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md).
Documentation: CC BY 4.0 ([LICENSE-DOCS](LICENSE-DOCS)).
