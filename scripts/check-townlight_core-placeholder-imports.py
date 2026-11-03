from __future__ import annotations

import re
import sys
from pathlib import Path

PLACEHOLDERS = {
    "audit",
    "catalog",
    "connectors",
    "exemptions",
    "ingest",
    "notifications",
    "onboarding",
    "scaffold",
    "search",
    "verification",
}

SOURCE_ROOT = Path("townlight_zoning")
PATTERN = re.compile(r"^\s*(?:from|import)\s+townlight_core\.([a-z_]+)", re.MULTILINE)


def main() -> int:
    failures: list[str] = []
    scanned = 0
    for path in SOURCE_ROOT.rglob("*.py"):
        scanned += 1
        text = path.read_text(encoding="utf-8")
        for match in PATTERN.finditer(text):
            package = match.group(1)
            if package in PLACEHOLDERS:
                failures.append(
                    f"{path}: townlight_core.{package} is still treated as a placeholder package for TownlightZoning v1. "
                    "See AGENTS.md section 3.1."
                )

    if failures:
        print("PLACEHOLDER-IMPORT-CHECK: FAILED")
        for failure in failures:
            print(failure)
        return 1

    print(f"PLACEHOLDER-IMPORT-CHECK: PASSED ({scanned} source files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
