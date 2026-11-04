# Security

Current source package: `townlight-zoning` 0.2.3. Windows MSI 1.7.0.1 is [published](https://github.com/townlight/townlight/releases/tag/townlight-beta-1-windows-1.7.0.1). Its [acceptance summary](https://github.com/townlight/townlight/releases/download/townlight-beta-1-windows-1.7.0.1/ACCEPTANCE-Windows-1.7.0.1.md) identifies the tested workflows and limits; standalone source checks remain separate.

Townlight Zoning Current version: 0.2.3. This is a narrow truth-repair release with no functional upgrade. The previous v1.0.0 release was published in error and does not prove public-use readiness. Deploy it only for local scaffold evaluation behind the city's trusted access layer, set `TOWNLIGHT_ZONING_STAFF_TRUSTED_PROXY_CIDRS` for the reverse proxy allowed to inject staff headers, review local parcel/rule data with planning staff, and route official zoning determinations to municipal staff.

Report suspected vulnerabilities privately to the project maintainer. Do not open public issues containing exploit details, secrets, or sensitive municipal data.
