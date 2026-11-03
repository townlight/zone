#!/usr/bin/env bash
set -euo pipefail

required=(
  "README.md"
  "README.txt"
  "CHANGELOG.md"
  "CONTRIBUTING.md"
  "LICENSE"
  "LICENSE-CODE"
  "LICENSE-DOCS"
  ".gitignore"
  "AGENTS.md"
  "USER-MANUAL.md"
  "SECURITY.md"
  "SUPPORT.md"
  "CODE_OF_CONDUCT.md"
  ".github/PULL_REQUEST_TEMPLATE.md"
  ".github/ISSUE_TEMPLATE/bug_report.md"
  ".github/ISSUE_TEMPLATE/feature_request.md"
  ".github/ISSUE_TEMPLATE/config.yml"
  "docs/RECONCILIATION.md"
  "docs/MILESTONES.md"
  "docs/IMPLEMENTATION_PLAN.md"
  "docs/github-discussions-seed.md"
  "docs/index.html"
  "pyproject.toml"
  "townlight_zoning/__init__.py"
  "townlight_zoning/main.py"
  "townlight_zoning/models.py"
  "townlight_zoning/parcel_lookup.py"
  "townlight_zoning/rule_lookup.py"
  "townlight_zoning/qa.py"
  "townlight_zoning/question_ledger.py"
  "townlight_zoning/staff_context.py"
  "townlight_zoning/public_ui.py"
  "townlight_zoning/migrations/alembic.ini"
  "townlight_zoning/migrations/env.py"
  "townlight_zoning/migrations/guards.py"
  "townlight_zoning/migrations/versions/townlight_zoning_0001_schema.py"
  "townlight_zoning/migrations/versions/townlight_zoning_0002_parcel_rule_lookup_records.py"
  "townlight_zoning/migrations/versions/townlight_zoning_0003_question_ledger.py"
  "townlight_zoning/migrations/versions/townlight_zoning_0004_staff_workflows.py"
  "MILESTONE_7_DONE.md"
  "MILESTONE_8_DONE.md"
  "PRODUCTION_DEPTH_PARCEL_RULE_PERSISTENCE_DONE.md"
  "PRODUCTION_DEPTH_QUESTION_LEDGER_DONE.md"
)

echo "==> Required-artifact check"
for file in "${required[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "FAIL: missing required artifact: $file" >&2
    exit 1
  fi
done

echo "==> Current-facing shipped/planned truth check"
current_files=("README.md" "README.txt" "USER-MANUAL.md" "docs/index.html")
bad_markers=(
  "TownlightZoning is shipping"
  "Shipping v0.1.0"
  "zoning answers are available"
  "parcel lookup is available"
  "GIS import is available"
  "zoning determinations are available"
  "legal advice is available"
  "planner review queue is available"
  "staff-only precedent is public"
  "v0.2.0 recovery release"
  "0.2.0 recovery release"
  "current product release"
  "current state: published v0.2.0"
  "recovery label recovered"
)

for file in "${current_files[@]}"; do
  for marker in "${bad_markers[@]}"; do
    if grep -Fqi "$marker" "$file"; then
      echo "FAIL: stale/planned-as-shipped marker '$marker' found in $file" >&2
      exit 1
    fi
  done
done

echo "VERIFY-DOCS: PASSED"
