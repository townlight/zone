CivicZone
=========

UNRELEASED CONNECTED Z4 INSTALLER
The local Townlight 1.4.0-1 candidate adds an explicit zoning-beta profile with
Records, Meetings, Code, Core, Notice and Access. It packages PostgreSQL17.10,
PostGIS3.6.2 and the existing Python services. Staff import validated offline
GeoJSON bundles from Zoning's Import parcel dataset control. No live GIS or
model download is required. Structured answers are informational, not binding
determinations. Public Meetings history and immutable Zoning snapshots can be
attached to Records without approving or publishing a response. Private review
notes remain restricted. This candidate is unsigned and not publicly released;
installed fresh/upgrade/recovery verification is recorded separately.

UNRELEASED TOWNLIGHT ZONING Z1 INTEGRATION
The working branch uses Core 1.2.1 and the existing Townlight Python/PostgreSQL
runtime. Z1 adds offline GeoJSON/PostGIS parcel and overlay imports, immutable
source history, archival of missing parcels, native-session authentication and
actual Townlight Code citations. This path does not seed sample records.
It is not a public release or finished product. The standalone sample UI below
is not the connected desktop surface. Z2 structured cited workflows are described
below. Meetings/Records documents and installed acceptance remain later milestones.
Operator contract: docs/Z1-OFFLINE-IMPORT.md.

PUBLISHED V0.2.2 BASELINE (HISTORICAL)

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

Code license: Apache 2.0.
Documentation license: CC BY 4.0.
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
