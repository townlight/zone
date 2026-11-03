from __future__ import annotations

from dataclasses import dataclass

from townlight_zoning.rule_lookup import (
    DISCLAIMER,
    DimensionalRuleResult,
    RuleLookupError,
    UseRuleResult,
    lookup_dimensional_rule,
    lookup_use_rule,
)


@dataclass(frozen=True)
class ZoneAnswer:
    answer: str
    citations: tuple[str, ...]
    status: str
    reason: str
    confidence: str
    next_step: str
    disclaimer: str = DISCLAIMER


DETERMINATION_PHRASES = (
    "guarantee",
    "determination",
    "approve",
    "permit me",
    "legal",
    "will the city approve",
)
OUT_OF_JURISDICTION_PHRASES = (
    "outside city limits",
    "county land",
    "unincorporated",
    "another city",
    "neighboring town",
)
LOW_CONFIDENCE_PHRASES = (
    "maybe",
    "approximately",
    "not sure",
    "conflicting",
    "unclear",
    "unknown overlay",
)


def answer_zoning_question(
    *,
    zone_code: str,
    question: str,
    use_rule_lookup=lookup_use_rule,
    dimensional_rule_lookup=lookup_dimensional_rule,
) -> ZoneAnswer:
    normalized = question.strip().casefold()
    if any(phrase in normalized for phrase in OUT_OF_JURISDICTION_PHRASES):
        return ZoneAnswer(
            answer=(
                "TownlightZoning cannot answer out-of-jurisdiction zoning questions from the "
                "configured city dataset."
            ),
            citations=(),
            status="refused",
            reason="out_of_jurisdiction",
            confidence="none",
            next_step="Contact the jurisdiction that regulates the parcel before relying on zoning guidance.",
        )
    if any(phrase in normalized for phrase in LOW_CONFIDENCE_PHRASES):
        return ZoneAnswer(
            answer="This request needs planner review because the available zoning context is low confidence.",
            citations=(),
            status="escalate",
            reason="low_confidence",
            confidence="low",
            next_step="Route the question to planning staff with parcel, overlay, and source context attached.",
        )
    if any(phrase in normalized for phrase in DETERMINATION_PHRASES):
        return ZoneAnswer(
            answer="This request needs planner review because it asks for a determination.",
            citations=(),
            status="escalate",
            reason="determination_request",
            confidence="none",
            next_step="Route to planning staff; TownlightZoning provides information, not approvals or determinations.",
        )

    if "adu" in normalized:
        rule = use_rule_lookup(zone_code=zone_code, use="ADU")
        if isinstance(rule, UseRuleResult):
            return ZoneAnswer(
                answer=(
                    f"In {rule.zone_code}, an ADU is listed as {rule.status}. "
                    f"{rule.review_path}"
                ),
                citations=(rule.citation,),
                status="answered",
                reason="cited_use_rule",
                confidence="high",
                next_step="Confirm parcel-specific overlays before relying on the informational answer.",
            )
        if isinstance(rule, RuleLookupError):
            return _refused_from_rule_error(rule)

    if "setback" in normalized or "front yard" in normalized:
        rule = dimensional_rule_lookup(zone_code=zone_code, rule_type="front_setback")
        if isinstance(rule, DimensionalRuleResult):
            return ZoneAnswer(
                answer=f"In {rule.zone_code}, the sample front setback is {rule.value}.",
                citations=(rule.citation,),
                status="answered",
                reason="cited_dimensional_rule",
                confidence="high",
                next_step="Confirm parcel-specific overlays before relying on the informational answer.",
            )
        if isinstance(rule, RuleLookupError):
            return _refused_from_rule_error(rule)

    return ZoneAnswer(
        answer="TownlightZoning cannot answer this sample question with a citation yet.",
        citations=(),
        status="refused",
        reason="no_cited_rule",
        confidence="none",
        next_step="Ask with a supported zoning use or dimensional rule, or route to planning staff.",
    )


def _refused_from_rule_error(error: RuleLookupError) -> ZoneAnswer:
    return ZoneAnswer(
        answer=f"{error.message} Fix: {error.fix}",
        citations=(),
        status="refused",
        reason="rule_lookup_failed",
        confidence="none",
        next_step=error.fix,
    )
