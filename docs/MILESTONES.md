<a id="civiczone-milestones"></a>

# Townlight Zoning Milestones

## Milestone 0 - Reconciliation And Repo Scaffold

Acceptance criteria:
- Professional repository docs exist.
- AGPL-3.0-only code and CC BY 4.0 docs licenses exist.
- Unified spec section 10 requirements are captured.
- Documentation and CI gates exist.

## Milestone 1 - Runtime Foundation

Acceptance criteria:
- Python package imports.
- FastAPI app starts.
- `/` and `/health` endpoints report current state without overstating behavior.
- Historical v0.1.0 foundation pinned the then-current Townlight Core release; current compatibility is tracked in `pyproject.toml`, `/health`, README, and the release gate.

## Milestone 2 - Canonical Zoning Schema And Migrations

Acceptance criteria:
- Tables for zones, overlays, parcels, use categories, use rules, dimensional rules, citations, precedents, interpretation notes, and zone questions exist.
- Alembic upgrade runs against pgvector Postgres.

## Milestone 3 - Parcel And Zone Lookup

Acceptance criteria:
- Address/parcel lookup returns zone, overlays, constraints, and source metadata.
- Unknown parcels return actionable errors.

## Milestone 4 - Use And Dimensional Rules

Acceptance criteria:
- Allowed/conditional/prohibited use lookup works with citations.
- Setback, height, lot coverage, and overlay rules are cited.

## Milestone 5 - Citation-Grounded Resident Q&A

Acceptance criteria:
- Informational answers cite zoning code sections.
- No answer claims to be a zoning determination.
- Uncited answers are refused.
- Configured database-backed rule data can feed resident answers.
- Configured resident questions are recorded in a local question ledger.

## Milestone 6 - Planner Escalation And Staff Context

Acceptance criteria:
- Low-confidence, out-of-jurisdiction, variance, CUP, and determination requests escalate.
- Staff-only precedent context never leaks to residents.

## Milestone 7 - Public UI And Accessibility

Acceptance criteria:
- Resident lookup page renders desktop and mobile states.
- Loading, empty, success, error, and escalation states are browser-verified.

## Milestone 8 - v0.1.0 Release

Acceptance criteria:
- `verify-release.sh` passes.
- Version surfaces match.
- GitHub release publishes wheel, sdist, and checksums.
- Umbrella compatibility matrix is updated.

## Milestone 9 - v1.0.0 Public-Use Release

Acceptance criteria:
- Version surfaces match `1.0.0`.
- Townlight Core compatibility is aligned to the published Townlight Core v1.1.0 wheel.
- Resident UI runs live parcel lookup, cited Q&A, empty, error, and
  planner-review states.
- Staff UI shell supports planner Q&A, ambiguity review, analytics, and
  staff-report outline actions through trusted municipal access headers.
- Staff APIs validate headers through the trusted proxy/source allowlist.
- Full tests, docs gate, Ruff, release gate, browser QA, adversarial validation,
  release-gate audit, CI, tag/release, and Townlight installer/module-selection
  truth pass.
