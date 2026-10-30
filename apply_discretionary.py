# SPDX-License-Identifier: AGPL-3.0-only
"""One-shot edit: expose cited variance/CUP explanation and nonconformity flags.

Adds one API route and one public page section over the existing rule/parcel
lookups. Adds no schema, no GIS service and no vendor. Idempotent.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE / 'civiczone'

# --- main.py: imports, route, page call -------------------------------------
target = PKG / 'main.py'
text = target.read_text(encoding='utf-8')
if 'discretionary_explanation' not in text:
    text = text.replace(
        'from civiczone.staff_context import classify_for_planner_review, get_staff_precedent',
        'from civiczone.discretionary import (Unavailable, explain, nonconformity_review_note)\n'
        'from civiczone.staff_context import classify_for_planner_review, get_staff_precedent')

    route = '''

class DiscretionaryExplanationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    zone_code: str = Field(default="", max_length=20)
    rule_types: list[str] = Field(default_factory=list, max_length=12)
    observed: dict[str, str] = Field(default_factory=dict)


@app.post("/api/v1/civiczone/standards/process-explanation")
def discretionary_explanation(request: DiscretionaryExplanationRequest) -> dict[str, object]:
    """Explain the variance/CUP process a question is about, with citations.

    Returns an explicit ``unavailable`` payload when the loaded rule dataset cannot
    support an answer; never a guessed standard, and never a determination.
    """
    result = explain(
        request.question,
        repository=_rules_for_explanation(),
        zone_code=request.zone_code,
        rule_types=request.rule_types,
        observed=request.observed,
    )
    note = nonconformity_review_note(request.question)
    if isinstance(result, Unavailable):
        return {
            "status": "unavailable",
            "reason": result.reason,
            "fix": result.fix,
            "review_required": True,
            "disclaimer": result.disclaimer,
            "nonconformity_note": note,
        }
    return {
        "status": "explained",
        "process": result.process,
        "label": result.label,
        "what": result.what,
        "standard_citation": result.standard_citation,
        "needs": result.needs,
        "review": result.review,
        "standards": result.standards,
        "flags": [flag.__dict__ for flag in result.flags],
        "nonconformity_note": note,
        "review_required": True,
        "determination_made": False,
        "disclaimer": result.disclaimer,
    }


def _rules_for_explanation():
    """The same rule source the dimensional lookup uses (no new data source)."""

    class _Adapter:
        """Adapt the module-level lookup to the repository shape ``explain`` wants."""

        @staticmethod
        def lookup_dimensional_rule(*, zone_code: str, rule_type: str):
            return _lookup_dimensional_rule(zone_code=zone_code, rule_type=rule_type)

    return _Adapter()
'''
    anchor = '\n\n@app.post("/api/v1/civiczone/questions/answer")'
    if anchor not in text:
        raise SystemExit('anchor not found')
    text = text.replace(anchor, route + anchor, 1)
    target.write_text(text, encoding='utf-8')
    print('patched', target)
else:
    print('already patched', target)

# --- public_ui.py: a cited standards/process section ------------------------
page = PKG / 'public_ui.py'
ptext = page.read_text(encoding='utf-8')
if 'Variance, conditional use and nonconformity' not in ptext:
    section = '''    <article class="card large">
      <p class="kicker">Variance, conditional use and nonconformity</p>
      <h2>What process applies, and what is cited</h2>
      <p>A <strong>variance</strong> asks to depart from a specific standard; a
      <strong>conditional use permit</strong> reviews a use the code already allows with
      conditions. Both are discretionary and both are decided by the body the code names
      after review.</p>
      <div class="result"><p>Dimensional standards, their code citations and anything that
      looks like a <strong>possible nonconformity</strong> come from the loaded rule
      dataset. A possible nonconformity is shown as a review flag, never as a finding:
      only staff can determine that status from the parcel record.</p></div>
      <p>If the loaded rules do not cover the standard you asked about, this page says so
      instead of estimating.</p>
    </article>
'''
    marker = '    <article class="card">\n      <p class="kicker">Planning boundary</p>'
    if marker not in ptext:
        raise SystemExit('page marker not found')
    page.write_text(ptext.replace(marker, section + marker, 1), encoding='utf-8')
    print('patched', page)
else:
    print('already patched', page)
