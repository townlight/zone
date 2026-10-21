<a id="civiczone-reconciliation"></a>

# Townlight Zoning Reconciliation

Milestone 0 compares this new repository against the Townlight unified spec and current shipped suite state.

| File path | Current text | Required correction | Driver |
|---|---|---|---|
| `README.md` | `# civiczone` | Replace generated GitHub stub with professional module README. | Unified spec section 10 |
| `README.md` | `CivicZone: parcel-aware zoning and land-use Q&A module for CivicSuite.` | Add shipped/planned boundary and installation/testing instructions. | Suite documentation standard |
| missing | `CHANGELOG.md` absent | Add Keep a Changelog file with `0.1.0.dev0` scaffold/runtime-foundation entry. | Suite release convention |
| missing | `pyproject.toml` absent | Add Python package metadata and a released Townlight Core pin; current compatibility is tracked in `pyproject.toml` and `/health`. | Townlight Core compatibility rule |
| missing | `civiczone/main.py` absent | Add root and health endpoints only; no zoning-answer behavior. | Milestone 1 runtime foundation |
| missing | `scripts/verify-docs.sh` absent | Add documentation artifact and stale-claim gate. | Suite QA standard |
| missing | `scripts/verify-release.sh` absent | Add automated release gate. | Suite QA standard |
| missing | `docs/index.html` absent | Add honest landing page. | Professional product docs requirement |
| missing | `USER-MANUAL.md` absent | Add non-technical and IT/user manual. | Professional product docs requirement |
| missing | `.github/workflows/verify.yml` absent | Add CI gate for tests, docs, placeholder imports, and ruff. | Suite CI convention |
| missing | `LICENSE-CODE` absent | Add AGPL-3.0-only code license. | Suite licensing decision |
| missing | `LICENSE-DOCS` absent | Add CC BY 4.0 docs license. | Suite licensing decision |

## ADR Queue

Milestone 0 identifies these future decision topics:

- Parcel-source precedence: city GIS, county assessor, Esri, GeoJSON, and manual override order.
- Staff-only precedent visibility and retention.
- Zoning determination disclaimer language.
- Townlight Code citation handoff and section-resolution failure behavior.
