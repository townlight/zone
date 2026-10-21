# Townlight Zoning Z1 — offline import and access contract

Unreleased developer integration. Legacy package/schema names remain `civiczone`.
This document does not announce a public Zoning release.

## Runtime and access

The internal `zoning-beta` Python runtime profile inherits the released
Records–Meetings–Code capabilities and adds Zoning. It does not change the
installer's defaults or saved product selection. Installer selection, payload
preparation and installed acceptance remain Z4 work.

- `POST /desktop/v1/zoning/imports`: import a complete jurisdiction snapshot.
- `POST /desktop/v1/zoning/parcels/lookup`: body `jurisdiction` and `query`.
- Both require the existing `X-Townlight-Session` proof and a mapped active
  account allowed to use Zoning. Existing city-staff/local-admin capabilities
  apply; caller-supplied actor or role fields do not grant authority.
- The existing runtime migration entry point applies Core, Records, Meetings,
  Code, supporting schemas and then Zoning's migrations. PostGIS must already
  be present in the PostgreSQL binary distribution; a successful process or
  module import is not domain readiness.
- `/ready` includes Zoning schema/PostGIS readiness for this profile.

The legacy `civiczone.main` sample app is not mounted. No new Rust domain
implementation, second database or sample fallback is used.

## Import envelope

Required top-level fields: nonempty `jurisdiction`, `source_id`, `version`,
`source_date` in YYYY-MM-DD form, `crs` equal to `EPSG:4326`, `boundary`,
and `zones`, `parcels`, `overlays` FeatureCollections.

- Boundary and feature geometry: valid, nonempty Polygon/MultiPolygon with
  closed two-dimensional WGS84 coordinate rings, inside the jurisdiction.
- Every feature has type `Feature`, a stable string `id`, and properties.
- Zone properties: `code`, `name`, `section_number`.
- Parcel properties: `parcel_number`, `address`.
- Overlay properties: `code`, `name`, optional `section_number`.
- Zones and parcels must be nonempty; an empty overlay collection is valid.
- Current bounds: 10 MiB canonical JSON and 20,000 features per collection.
  These are input bounds, not a certified 20,000-feature performance result.

The fictional example is `tests/fixtures/z1-town.json`. It is not municipal data.
The API accepts decoded JSON; it does not fetch supplied URLs or read arbitrary
filesystem paths. A desktop import picker belongs to the later UI milestone.

## Spatial behavior and history

PostGIS validates source geometry and derives zone/overlay relationships. A
parcel must be covered by exactly one zone, without another positive-area zone
intersection. Conflicting/cross-zone input is rejected, not silently assigned
by a model. Mere edge/point contact does not count as an overlay intersection.

An import is one database transaction, serialized per jurisdiction. It retains
the canonical source hash, raw payload, version, source date, actor and import
time. Repeating identical source/version/hash is idempotent; changed bytes under
the same identity are rejected. Replaying a historical import does not reactivate
it. A valid new snapshot archives absent parcels and retains historical imports;
it does not delete them. Stable parcel identity survives updates.

Lookup distinguishes `ok`, `not_found`, `ambiguous`, `out_of_jurisdiction` and
`data_unavailable`. The native bridge resolves zone and supplied overlay section
references using Code's active official public-source citation rules. It reports
`citation_unavailable` rather than claiming verified information without the
required source. Database/schema failures are not disguised as empty results.

Every successful parcel response carries the informational/non-determination
disclaimer and dataset provenance. Linking source material does not grant an
approval, permit, binding determination or public-release decision. No staff
interpretation/precedent notes are returned by this slice.

## Verification boundary

Z1 checks use the existing packaged Python/Core and a task-local copy of the
shipped PostgreSQL17.10 with official PG17 PostGIS3.6.2. No machine-wide install
or modification of the released payload is needed for developer acceptance.
The separate execution/check records identify actual passed evidence.

Compatibility source: the official Windows bundle linked from
[PostGIS released versions](https://postgis.net/documentation/getting_started/install_windows/released_versions/),
`https://download.osgeo.org/postgis/windows/pg17/postgis-bundle-pg17-3.6.2x64.zip`.
Locally computed SHA256:
`7ba180ee2a352987b9a2f194673652c59483b55852295ccf401dceccd8765425`.
The exact existing PostgreSQL17.10 binaries loaded that extension and executed
WGS84 geography operations. This establishes compatibility, not production
payload inclusion. Z4 must preserve required DLLs, license notices and source
integrity when preparing the distributable payload.

Connected rule-answer UI, Code-change answer handling, Meetings/Records document
connections, performance qualification and final installer verification remain
Z2–Z4. No push, merge, signing or publication is authorized by this document.
