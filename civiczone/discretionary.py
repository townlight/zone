# SPDX-License-Identifier: AGPL-3.0-only
"""Cited standards and process explanation for variances, CUPs and nonconformity.

What this answers, using only rules the deployment has actually loaded:

* which dimensional or use standard a parcel must meet, with its code citation;
* whether a request is a *variance* question or a *conditional use permit* (CUP)
  question, what the code's review path is, and what a resident should expect;
* a **nonconformity REVIEW flag** for a stated condition that looks like it may
  not meet a cited standard -- a flag that opens staff review, never a finding.

What it never does: decide entitlement, decide that a variance/CUP must be
granted or denied, or declare a parcel legally nonconforming. Every payload
carries ``review_required`` and the disclaimer, and an unsupported question
returns an explicit ``unavailable`` with the reason instead of a guess.

The dimensional/use lookups, the parcel projection, the escalation classifier and
the citation freshness all come from the modules already in this package
(``rule_lookup``, ``parcel_lookup``, ``staff_context``, ``cited_rules``); this
module composes them into the resident/staff explanation the beta promises and
adds the nonconformity review flag.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from civiczone.rule_lookup import RuleLookupError, RuleLookupRepository

DISCLAIMER = 'Informational only; this is not a zoning determination.'

#: Terms a resident actually uses, mapped to the process they are asking about.
PROCESS_HINTS = {
    'variance': ('variance', 'variances', 'vary', 'hardship', 'deviation', 'relief'),
    'cup': ('cup', 'conditional use', 'conditional use permit', 'special use'),
}

#: A stated condition/standard pair that may be nonconforming. Deliberately
#: narrow, and only ever produces a review flag.
NONCONFORMITY_HINTS = ('nonconforming', 'non-conforming', 'non conformity',
                       'preexisting', 'pre-existing', 'grandfathered', 'legally existing')


@dataclass(frozen=True)
class Unavailable:
    """An explicit refusal: the sources do not support an answer."""

    reason: str
    fix: str
    review_required: bool = True
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class NonconformityFlag:
    """A REVIEW flag raised from existing parcel/rule data. Never a finding."""

    observed: str
    standard: str
    citation: str
    basis: str
    review_required: bool = True
    determination_made: bool = False
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class ProcessExplanation:
    process: str
    label: str
    what: str
    standard_citation: str
    needs: list
    review: list
    source_citation: dict = field(default_factory=dict)
    standards: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    review_required: bool = True
    determination_made: bool = False
    disclaimer: str = DISCLAIMER
    as_of: str | None = None


def classify_process(text: str) -> str | None:
    """Which discretionary process is the question about, if any."""
    normalized = text.casefold()
    for process, hints in PROCESS_HINTS.items():
        if any(hint in normalized for hint in hints):
            return process
    return None


def _standard_value(value: str) -> tuple[float | None, str]:
    """Parse a leading number and its unit out of a code-derived rule value."""
    match = re.match(r'\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z%]+)?', value or '')
    if not match:
        return None, ''
    return float(match.group(1)), (match.group(2) or '').casefold()


def flag_nonconformity(*, observed: str, rule_value: str, rule_type: str,
                       citation: str, zone_code: str) -> NonconformityFlag | None:
    """Raise a REVIEW flag when a stated condition is short of a cited standard.

    The comparison is deliberately mechanical and one-directional: for the
    dimensional standards this product models, a *larger* number is more
    permissive (a setback you can exceed, a height you can stay under is the
    exception), so only the modelled direction is compared. Anything it cannot
    compare mechanically produces no flag at all rather than a guess.
    """
    observed_value, observed_unit = _standard_value(observed)
    standard_value, standard_unit = _standard_value(rule_value)
    if observed_value is None or standard_value is None:
        return None
    if observed_unit and standard_unit and observed_unit != standard_unit:
        return None
    kind = rule_type.casefold()
    if kind in ('front_setback', 'side_setback', 'rear_setback', 'setback',
                'minimum_lot_size', 'lot_size'):
        short = observed_value < standard_value
        basis = f'The stated {observed} is less than the cited minimum ({rule_value}).'
    elif kind in ('height', 'maximum_height'):
        short = observed_value > standard_value
        basis = f'The stated {observed} exceeds the cited maximum ({rule_value}).'
    else:
        # An unmodelled standard direction cannot be compared safely.
        return None
    if not short:
        return None
    return NonconformityFlag(observed=observed, standard=rule_value,
                             citation=citation, basis=basis + ' Possible nonconformity; '
                             'staff must review the parcel record and any approvals.')


def _rule(repository: RuleLookupRepository, *, zone_code, rule_type):
    """Fetch one dimensional standard, or return why it is unavailable."""
    result = repository.lookup_dimensional_rule(zone_code=zone_code, rule_type=rule_type)
    if isinstance(result, RuleLookupError):
        return None, result
    return {'rule_type': result.rule_type, 'value': result.value,
            'citation': result.citation}, None


def explain(question: str, *, repository: RuleLookupRepository, zone_code: str = '',
            rule_types: list | None = None, observed: dict | None = None,
            process_source: dict | None = None) -> object:
    """Explain the discretionary process the question is about, cited.

    ``observed`` maps a rule type to the condition the resident stated (for
    example ``{'front_setback': '8 feet'}``); those are only ever compared
    against the cited standard to raise review flags.
    """
    process = classify_process(question)
    if process is None:
        return Unavailable(
            reason=('This question is not about a variance, a conditional use permit or '
                    'a nonconformity, so there is no discretionary process to explain.'),
            fix=('Ask about a variance, a conditional use permit, or a condition that may '
                 'not meet a cited standard, and include the zone code.'))

    # The Code resolver must supply an active official public section. Its text
    # is the explanation; classifying a question cannot establish municipal law.
    if (not process_source or process_source.get('status') != 'ok'
            or not process_source.get('citation', {}).get('body_text')):
        return Unavailable(reason='No active official public process source resolved.',
                           fix='Select the applicable variance/CUP Code section and retry; staff must review applicability.')
    citation = process_source['citation']
    if classify_process(citation['body_text']) != process:
        return Unavailable(reason='The selected Code text does not identify this process.',
                           fix='Select the applicable process section; staff must confirm applicability.')
    detail = {'label': 'Variance' if process == 'variance' else 'Conditional use permit',
              'what': citation['body_text'],
              'standard_citation': citation.get('section_number', ''),
              'needs': ['Staff must review the cited process and its applicability to this proposal.'],
              'review': 'Review required. Process requirements are the quoted source text above.'}
    standards, flags, missing = [], [], []
    for rule_type in (rule_types or []):
        if not zone_code:
            missing.append(rule_type)
            continue
        standard, error = _rule(repository, zone_code=zone_code, rule_type=rule_type)
        if error is not None:
            missing.append(rule_type)
            continue
        standards.append(standard)
        stated = (observed or {}).get(rule_type)
        if stated:
            flag = flag_nonconformity(observed=stated, rule_value=standard['value'],
                                      rule_type=standard['rule_type'],
                                      citation=standard['citation'], zone_code=zone_code)
            if flag is not None:
                flags.append(flag)

    review = [detail['review']]
    if missing:
        review.append('The configured rule dataset has no standard for: '
                      + ', '.join(sorted(set(missing)))
                      + '. Those standards are unavailable, not assumed.')
    if not zone_code:
        review.append('No zone code was supplied, so no dimensional standard could be cited.')
    return ProcessExplanation(process=process, label=detail['label'], what=detail['what'],
                              standard_citation=detail['standard_citation'],
                              needs=list(detail['needs']), review=review,
                              source_citation=dict(citation), standards=standards, flags=flags)


def nonconformity_review_note(text: str) -> str | None:
    """Note when the resident's own wording raises the nonconformity question."""
    normalized = text.casefold()
    if any(hint in normalized for hint in NONCONFORMITY_HINTS):
        return ('The question describes a possible nonconformity. Existing conditions are '
                'reviewed against the code in effect when they were established; only staff '
                'can determine that status from the parcel record.')
    return None
