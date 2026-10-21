<a id="civiczone"></a>

# Townlight Zoning

## Published connected desktop: 1.4.0-beta.1

This module participates in the signed Townlight Records + Meetings + Code +
Zoning desktop beta published October 21, 2026. Select zoning-beta for all four
products; Records-only remains default and city-core excludes Zoning.
[Download and release limits](https://github.com/townlight/townlight/releases/tag/townlight-records-meetings-code-zoning-v1.4.0-beta.1) ·
[Current operator manual](https://github.com/townlight/townlight/blob/main/USER-MANUAL.md) ·
[Signed acceptance](https://github.com/townlight/townlight/blob/main/docs/installer/townlight-zoning-beta1-signed-acceptance.md).

This is a connected desktop release, not a new standalone package version.
Package/import/API names remain compatibility identifiers. Historical development
checkpoints below retain their original scope; they are superseded for current
desktop publication status. No signed installer or historical evidence is changed.

## Historical integration checkpoint — Z4 local installer candidate (unreleased)

The desktop1.4.0-1 candidate exposes the opt-in `zoning-beta` connected profile.
Records remains the default and the public1.3release is unchanged. Installer
verification is in progress; this is not a published or signed Zoning release.

In the staff Zoning screen, choose a JSON file with **Import parcel dataset**.
Use the complete GeoJSON envelope described in `docs/Z1-OFFLINE-IMPORT.md`:
source identity/date/version, EPSG:4326 boundary, zones, parcels and optional
 overlays. No invented municipality is loaded automatically. Code must contain
an active, official, public source for the cited sections. Lookup reports actual
source identity/hash/date; unsupported or ambiguous answers remain informational
and can be corrected by authorized staff without a new workflow approval gate.
Private notes remain staff-only; public source snapshots require explicit human
selection. See `docs/Z3-CONNECTED-SOURCES.md` for history and Records attachment.


## Historical integration checkpoint — Unreleased Townlight Zoning Z1 integration

The working branch now targets the released Core 1.2.1 dependency and the
existing Townlight Python/PostgreSQL runtime. Z1 adds offline GeoJSON imports,
PostGIS-backed parcel/zone/overlay matching, immutable import provenance,
archival rather than deletion of missing parcels, and native-session-protected
import/lookup endpoints. It resolves citations through Townlight Code rather
than generating a second codifier. No sample records are seeded by this path.

This is not a new public release or a finished Zoning product. The existing
standalone sample UI described below is not the connected Z1 desktop surface.
Z2 extends this foundation with the structured cited workflows documented below.
Meetings/Records documents and installer acceptance remain later milestones. See
[the Z1 operator contract](docs/Z1-OFFLINE-IMPORT.md).

## Published v0.2.2 baseline (historical)

CivicZone is CivicSuite's parcel-aware zoning and land-use Q&A module.

Current state: **v0.2.2 corrective demotion state - scaffold with partial persistence/workflow plumbing; no real AI layer, full frontend, real municipal data/search, or public-use gate. This narrow truth-repair release is no functional upgrade; it exists solely to supersede the false v1.0.0 release from 2026-05-21 in GitHub's Latest impression. The CivicCore pin is unchanged.**. This repo contains a FastAPI service, health/root endpoints, documentation gates, canonical zoning schema models, Alembic migrations, deterministic parcel/zone lookup, cited use-rule lookup, cited dimensional-rule prechecks, resident Q&A with refusal and escalation rules, optional database-backed parcel/rule, resident-question ledger, and staff-workflow records through `CIVICZONE_PARCEL_RULE_DB_URL`, staff-only precedent protection, a browser-usable resident UI at `/civiczone`, a staff workflow shell at `/civiczone/staff`, adversarial local integration mocks, trusted-proxy staff access validation, and CivicCore v1.1.0 release-wheel dependency alignment. See [docs/release-recovery-status.md](docs/release-recovery-status.md) for historical recovery context and current release evidence.

## Product Boundaries

- Townlight Zoning gives informational zoning context with citations.
- Townlight Zoning refuses or escalates zoning-determination, legal-advice, out-of-jurisdiction, stale-data, low-confidence, and uncited-answer requests.
- Townlight Zoning does not make zoning determinations, approve permits, replace planner review, or call live external vendor systems by default.
- Townlight Zoning integration behavior is validated with local adversarial mocks for Esri ArcGIS REST, GeoJSON fallback, Townlight Code, Townlight Meetings, Townlight Planning, Townlight Access, county assessor, and CKAN boundaries.

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
- `GET /health` returns package and Townlight Core version information.
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

Set `CIVICZONE_PARCEL_RULE_DB_URL` to enable persistent parcel, use-rule, dimensional-rule, resident-question ledger, and staff workflow records. When unset, Townlight Zoning uses deterministic in-memory sample data and does not persist question or staff workflow rows.

Staff workflow endpoints require trusted municipal access headers from a configured trusted proxy/source. Local development accepts loopback by default. Shared deployments should set `CIVICZONE_STAFF_TRUSTED_PROXY_CIDRS` and strip client-supplied staff headers before requests reach Townlight Zoning.

- `X-CivicZone-Principal`
- `X-CivicZone-Role: planner`, `staff`, or `zoning_admin`

## License

Code: AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. See [LICENSE](LICENSE) and [LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md).
Documentation: CC BY 4.0 ([LICENSE-DOCS](LICENSE-DOCS)).

## Unreleased connected Zoning Z2

The local development branch adds parcel-scoped allowed/conditional/prohibited-use
and dimensional answers bound to actual Townlight Code section, version, effective
date and source identities. Unsupported, conflicting or stale bindings are shown
as needing planner attention, not invented determinations. This is structured
staff-configured lookup, not AI interpretation or legal advice.

The separate Zoning desktop component has resident lookup/question controls and
an authenticated staff workspace: cited rule registration, persisted question
history, planner queue, corrections, basic counts/repeated questions and draft
report outlines. Human corrections do not require an earlier automated flag,
nonempty justification or an extra approval. Original answers and audit history
remain intact. Staff notes/reviews are not included in resident responses.

This is not a released or installed Zoning candidate. The published
Records–Meetings–Code 1.3.0-beta.1 is unchanged. The Z2 operator guide is
zone/docs/Z2-CITED-WORKFLOWS.md.

## Unreleased connected Zoning Z3

Authorized staff can explicitly link a permitted public Meetings archive document
to a Zoning question as hearing context, context or precedent. This is historical
context, not a Code amendment or binding determination. Links retain source IDs,
archive/version identities, content hashes and actor history.

Staff can create a separate immutable Zoning source snapshot and select eligible
snapshots from Records. Staff-only snapshots and private review notes are not
offered as public Records sources. Permissions and content hashes are rechecked
when retrieving or attaching sources; a saved link does not bypass later access
restrictions. Existing stored evidence is preserved rather than rewritten.

Creating or attaching a snapshot does not approve a response or publish anything.
Human corrections remain available without an automatic flag or mandatory
justification. Packaged/installed acceptance and opt-in profile delivery remain
Z4. See zone/docs/Z3-CONNECTED-SOURCES.md. No new public release is claimed.
