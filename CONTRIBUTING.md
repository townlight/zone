# Contributing

Thank you for helping Townlight Zoning become useful municipal software.

## Development Loop

1. Read `AGENTS.md`, `docs/RECONCILIATION.md`, and `docs/MILESTONES.md`.
2. Create tests before implementation for each milestone.
3. Keep docs and tests in the same PR as code changes.
4. Run `bash scripts/verify-release.sh` before push.

## Boundaries

- Townlight Zoning gives cited zoning information, not zoning determinations.
- Do not expose staff-only precedent or interpretation notes to residents.
- Do not import Townlight Core placeholder packages.
- Do not claim planned behavior is shipped.
