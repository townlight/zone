# SPDX-License-Identifier: AGPL-3.0-only
"""One-shot edit: add the cited standards/process panel to the Zoning public page.

Adds a static, honest explanation panel (no client-side data source, no new
endpoint call from the page) that describes the two discretionary processes and
states that standards, citations and possible-nonconformity review flags come
from the loaded rule dataset -- with an explicit unavailable state.
Idempotent; retained as the record of this edit.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
page = HERE / 'civiczone/public_ui.py'
text = page.read_text(encoding='utf-8')
marker = '  <aside class="panel" aria-labelledby="states-title">'
section = '''  <section class="panel" aria-labelledby="process-title">
    <h2 id="process-title">Variance, conditional use and nonconformity</h2>
    <p>A <strong>variance</strong> asks to depart from one specific standard (for example a
    setback), because applying it here is unusually burdensome. A <strong>conditional use
    permit</strong> reviews a use the code already allows, subject to conditions. Both are
    discretionary: a body named in the code decides after review, and neither is granted or
    denied by this page.</p>
    <p>Dimensional standards and their code citations come from the loaded rule dataset.
    Where a stated condition does not meet a cited standard, this product raises a
    <strong>possible nonconformity review flag</strong>. It never declares a condition
    legally nonconforming: only staff can determine that from the parcel record and the
    code in effect when the condition was established.</p>
    <p class="boundary">If the loaded rules do not cover a standard, the answer is
    &ldquo;unavailable&rdquo; with the reason. No standard is estimated.</p>
  </section>
'''
if 'process-title' not in text:
    if marker not in text:
        raise SystemExit('marker not found')
    page.write_text(text.replace(marker, section + marker, 1), encoding='utf-8')
    print('patched', page)
else:
    print('already patched', page)
