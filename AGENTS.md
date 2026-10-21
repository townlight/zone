<a id="civiczone-agent-contract"></a>

# Townlight Zoning Agent Contract

## Source Of Truth

- Upstream suite spec: `townlight/townlight/docs/CivicSuiteUnifiedSpec.md`, especially section 10.
- Suite ADRs: `townlight/townlight/docs/architecture/`.
- Townlight Code v0.1.0 release contract is required context for zoning-code citations.

## Non-Negotiables

- Townlight Zoning never makes a zoning determination.
- Every resident-facing answer must state it is informational and not a determination.
- Every answer must cite source zoning-code sections or refuse/escalate.
- Staff-only precedent and interpretation notes must never leak to residents.
- Out-of-jurisdiction, low-confidence, and determination requests must escalate to planner review.
- Townlight Zoning depends on Townlight Core and Townlight Code; Townlight Core must never depend on Townlight Zoning.
- Code is AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. Docs are CC BY 4.0.

## Placeholder Package Warning

Do not import from Townlight Core placeholder packages until Townlight Core ships real implementations for them: `audit`, `catalog`, `connectors`, `exemptions`, `ingest`, `notifications`, `onboarding`, `scaffold`, `search`, `verification`. Townlight Core `auth` is no longer treated as a placeholder for Townlight Zoning v1.0.0 because the current release uses its trusted-header helpers for staff access validation.

## Milestone Rule

Work one milestone at a time. When a milestone is done, report what changed, audit it once, fix findings once, re-audit once, then continue immediately unless there is a true blocker.
