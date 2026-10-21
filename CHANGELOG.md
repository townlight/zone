# Changelog

## Unreleased — Townlight Zoning Z3

- Persist explicit permitted Meetings source links as append-only question events.
- Create immutable source snapshots with parcel/Code/Meetings provenance and
  explicit human-answer history, excluding private review notes.
- Add permission/hash-checked source selection and managed attachment in Records.
- Preserve existing response approval/publication behavior; no automatic release,
  legal determination, Code amendment or new public version is introduced.

## Unreleased — Townlight Zoning Z2

- Add version-bound structured use/dimensional rules and honest conflict/stale
  handling using authoritative Code identities.
- Persist questions, staff queue, append-only human corrections and draft outline
  references in the existing canonical PostgreSQL schema.
- Add separate typed desktop client/component and native transport only.
- Preserve resident/staff boundaries and original answer provenance.
- No public version, Meetings/Records source integration or installed acceptance
  is claimed by this local increment.

## Unreleased — Townlight Zoning Z1

- Align the working dependency with hash-pinned Core 1.2.1.
- Add canonical-table PostGIS geometry and offline GeoJSON import provenance.
- Preserve previous import payloads; archive missing parcels without deletion.
- Add authenticated native import/lookup through the shared runtime, with
  actual authoritative Code citations and no sample application mount.
- Preserve v0.2.2 and the historical corrective demotion below. No new release
  version, public readiness claim, UI or installer acceptance is implied.

## [0.2.2] - 2026-05-23

- Narrow truth-repair release. No functional upgrade.
- Exists solely to supersede the false v1.0.0 release from 2026-05-21 in
  GitHub's Latest impression.
- CivicCore pin unchanged.

## [0.2.0] - 2026-05-10

- Demoted the false v1.0.0 release label after the external CivicSuite audit found this module is a recovery/foundation module, not a canonical spec-complete v1 product.
- Preserved the useful recovery work while resetting the public package version to 0.2.0.
- Kept the CivicCore v1.0.0 wheel dependency and pinned it with SHA256 for release integrity.
- Supersedes the prior public v1.0.0 posture; do not treat v1.0.0 as production-ready or spec-complete.

All notable changes to CivicZone will be documented in this file.

The format follows Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.2.1] - 2026-05-21

### Corrected

- Corrected the false v1.0.0 release label after the independent CivicSuite release-integrity audit found CivicZone does not meet the Section 2 FINISHED and SHIPPING bar.
- Set the honest current label to v0.2.1 and superseded the mistaken v1.0.0 posture without deleting the historical record.
- Current classification: scaffold with partial persistence/workflow plumbing; no real AI layer, full frontend, real municipal data/search, or public-use gate.
- CivicZone must not be described as finished, shipping, city-ready, product-ready, or public-use ready until a future independent audit signs off against the full Section 2 gate.

## [1.0.0] - 2026-05-21

### Release note

- CivicZone is promoted from the demoted `0.2.0` recovery posture to the active
  `1.0.0` public-use module release after the current scope, UX, docs, tests,
  adversarial validation, and release-gate pass.

### Added

- v1 resident zoning Q&A runtime with deterministic cited answers, refusal and escalation reasons, confidence metadata, and actionable next steps.
- Staff workflow APIs for planner Q&A, ambiguity review queue, high-volume question analytics, staff-report outline support, and flagged-answer review.
- Database-backed staff workflow records for planner questions, ambiguity queue items, and flagged answer reviews when `CIVICZONE_PARCEL_RULE_DB_URL` is configured.
- Local adversarial integration mocks for Esri ArcGIS REST, GeoJSON fallback, CivicCode, CivicClerk, CivicPlan, CivicAccess, county assessor, and CKAN boundary validation.
- Browser-usable resident UI for live parcel lookup, cited Q&A, empty, error, and planner-review states.
- Browser staff workflow shell for planner Q&A, ambiguity queue creation, analytics, and staff-report outline support.

### Changed

- CivicCore dependency alignment moves to the published CivicCore `1.1.0` wheel.
- Staff workflow APIs now validate trusted municipal staff headers through the CivicCore trusted-proxy helper with loopback-only local defaults.
- Updated runtime and documentation boundaries to describe the v1 product without claiming legal advice, official zoning determinations, or live external vendor calls by default.

## [0.1.2] - 2026-05-07

### Added

- Production-depth parcel/rule lookup persistence slice with `CIVICZONE_PARCEL_RULE_DB_URL`, seeded sample parcel/use/dimensional records, and Alembic revision `civiczone_0002_parcel_rules`.
- Production-depth resident question ledger persistence for deterministic cited Q&A, including Alembic revision `civiczone_0003_question_ledger`.

### Changed

- Aligned CivicZone's release gate, CI install path, docs, and health-contract test with the published CivicCore v1.0.0 wheel before the next production-depth sprint.

## [0.1.1] - 2026-04-28

### Changed

- Aligned CivicZone to `civiccore==0.3.0` while preserving the v0.1 public UI foundation behavior.
- Updated version surfaces, release gate, CI CivicCore wheel install, documentation, and health-contract tests for the v0.1.1 dependency-alignment release.

## [0.1.0] - 2026-04-27

### Added

- Milestone 0 professional scaffold and reconciliation documents.
- Milestone 1 runtime foundation with package shell, root endpoint, health endpoint, tests, and release/documentation gates.
- Milestone 2 canonical zoning schema with SQLAlchemy models, Alembic scaffold, real pgvector migration test, and schema documentation.
- Milestone 3 sample parcel/zone lookup API with actionable unknown-parcel errors and zoning-determination disclaimer.
- Milestone 4 sample use and dimensional rule APIs with citations, disclaimers, and actionable 404s.
- Milestone 5 citation-grounded sample resident Q&A with escalation/refusal for determination or uncited questions.
- Milestone 6 planner-escalation classifier and staff-only precedent context sample, with leakage guard tests.
- Milestone 7 accessible public sample UI at `/civiczone`, with parcel context, cited rule cards, planner-escalation guidance, and browser QA evidence.
- Milestone 8 v0.1.0 release packaging, version synchronization, and GitHub release artifacts.
