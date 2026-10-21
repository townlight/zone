# Z2 cited workflows — unreleased operator guide

Z2 extends Z1 in the shared Python/PostgreSQL runtime. It does not mount the
standalone sample app or populate sample rules. Run the canonical migration
chain through civiczone_0006_cited_questions. Zoning remains an internal
zoning-beta development profile; no installer default is changed.

## Staff workflow

1. Import a validated municipal GeoJSON dataset through the Z1 native import
   endpoint. The jurisdiction, parcel, zone and optional overlays must exist.
2. Import/adopt the authoritative legal text in Townlight Code using its existing
   source workflow.
3. In Zoning, register the exact topic key, use/dimension kind, value and Code
   section for that jurisdiction/zone and, where relevant, overlay. Registration
   snapshots the current effective Code identity and preserves superseded rules.
4. Look up the parcel and ask with the configured topic key. Free-text questions
   are retained as context, not interpreted by an AI model. Missing/conflicting
   rules, missing overlay support and changed Code bindings require attention.
5. Open Workspace to inspect questions, queue, reviews and basic analytics.
   Copy the relevant question ID to Review. Authorized staff may correct or
   reopen/resolve/close a question without an automated flag or mandatory
   justification. Corrections append history; they do not overwrite the original.
6. Select question IDs for a draft report outline. It retains source snapshots
   and citations; it does not publish, approve a determination or export to Records.

The Code-context form accepts an optional as-of date and distinguishes current,
historical and future context. A changed effective version does not rewrite old
answers; rebind a rule deliberately when its supporting law changes.

## API and access

Authenticated native routes: /desktop/v1/zoning/rules, /questions,
/questions/{id}/reviews, /workspace, /outlines and /code-context.
Existing native parcel/import routes remain. Identity comes from the mapped
native session, not a client-supplied actor field.

Resident routes /civiczone/parcels/lookup and /civiczone/questions expose only
informational results. There is no resident workspace/review route. Staff notes
and review history are not returned through resident answers. The desktop
public transport rejects staff operations independently of hidden controls.

## Limits and evidence

This is a structured informational tool, not legal advice, a zoning determination,
permit approval, natural-language AI interpretation or live GIS integration.
It requires sourced imported data and explicit staff-configured rules.
Local real-database/API checks and isolated browser-component checks are distinct
from packaged installed acceptance. Z3 adds Meetings/Records sources; Z4 supplies
the installer candidate and installed acceptance. Neither is completed by Z2.
