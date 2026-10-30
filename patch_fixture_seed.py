# SPDX-License-Identifier: AGPL-3.0-only
"""One-shot edit: seed the fixture rule database before exercising citations.

A configured rule database starts empty by design (rules are loaded explicitly,
never invented), so the fixture must load the package's own sample dataset before
asserting cited standards. Idempotent; retained as the record of this edit.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
target = HERE / 'tests/test_discretionary.py'
text = target.read_text(encoding='utf-8')
old = '    monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", f"sqlite:///{tmp_path / \'rules.db\'}")'
new = '''    url = f"sqlite:///{tmp_path / 'rules.db'}"
    monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", url)
    # A configured rule database starts EMPTY on purpose: rules are loaded
    # explicitly and never invented. Seed the package's own sample dataset so the
    # cited-standard path can be exercised against real persistence.
    from civiczone.rule_lookup import RuleLookupRepository
    RuleLookupRepository(db_url=url, seed_defaults=True).engine.dispose()'''
if old in text and 'seed_defaults=True).engine.dispose()' not in text:
    target.write_text(text.replace(old, new), encoding='utf-8')
    print('patched', target)
else:
    print('already patched' if 'seed_defaults=True' in text else 'PATTERN NOT FOUND')
