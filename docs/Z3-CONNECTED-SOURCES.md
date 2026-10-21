# Z3 — Meetings context and Records sources

Unreleased local integration, October20,2026. The published three-product
1.3.0-beta.1 release is unchanged. Z4 packaging/installed acceptance is separate.

## Link source history deliberately

In the Zoning staff workspace, search Meetings for an explicitly public archive
document. Results contain the archive/meeting identity, document kind, version,
source references and content hash. Select the intended document by copying its
source ID and hash into Link meeting with the question ID. Choose hearing,
context or precedent. The operation records staff intent and preserves the source
snapshot; no automatic flag, prior approval or minutes adoption is added as a
prerequisite. Restricted archive records, raw transcripts and private attachments
are not supplied by this bounded public-document connection.

History returns the question and append-only events. Source permissions and hashes
are checked again on retrieval. If a linked document is no longer permitted or
its bytes changed, history reports it unavailable rather than exposing the saved
document text. The stored historical event is not deleted or rewritten.

A precedent or meeting vote is historical context, not current legal authority.
Zoning does not amend Code. Continue using the existing Code–Meetings legislative
connection for actual legal changes.

## Create and attach a Records source

Use Snapshot with a question ID and optional comma-separated meeting-link event
IDs. There is no requirement to link a meeting first. The default is staff_only.
Choose public deliberately to make a permitted snapshot eligible for authenticated
Records source selection; this does not publish it on the internet. Questions
classified for staff cannot be converted into public sources through this route.

The snapshot includes the original question/answer context, parcel and dataset
provenance, Code citations/version/effective dates, the latest explicit human
answer and its event reference, selected permitted Meetings history and the
informational disclaimer. Private review notes are excluded. Each snapshot has
its own immutable ID/version, canonical text and SHA-256. Later corrections
produce new snapshots; they do not update earlier source bytes.

In Records, Find Zoning documents searches eligible snapshots. Select the intended
request, search, then attach. The server rechecks visibility, linked Meetings
permissions, cited Code-source availability and the selected hash before using the
existing managed Records evidence path. Repeating the identical attachment does
not duplicate evidence. No response approval or publication occurs automatically.
The existing human-controlled Records response/release workflow remains.

Historical legal versions stay historical: availability is checked at their
recorded effective date, not replaced with today's law. An unavailable or
restricted source is not substituted with cached or sample content.

## Local API boundary

All new Zoning routes below require the existing mapped native staff session:

- POST /desktop/v1/zoning/meetings/search
- POST /desktop/v1/zoning/questions/{id}/meetings
- GET /desktop/v1/zoning/questions/{id}/history
- POST /desktop/v1/zoning/questions/{id}/snapshots

Records uses its existing native authorization:

- POST /desktop/v1/zoning-sources/search
- POST /desktop/v1/requests/{id}/zoning-sources

There is no resident question-history/review/source-management route. Native
public transport also rejects these staff operations. Rust only transports
requests; Python and the existing PostgreSQL tables own the domain behavior.

## Verification boundary

Real database/API tests and isolated browser-component tests are separate from a
packaged native/WebView journey. Source-level checks do not establish installed
fresh-install, upgrade or recovery behavior; that acceptance remains Z4.
