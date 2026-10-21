from __future__ import annotations

from dataclasses import dataclass

ESCALATION_TRIGGERS = ("variance", "cup", "conditional use permit", "nonconforming", "appeal")


@dataclass(frozen=True)
class EscalationResult:
    status: str
    reason: str
    next_step: str


@dataclass(frozen=True)
class StaffPrecedent:
    title: str
    summary: str
    visibility: str = "staff_only"


STAFF_PRECEDENTS = {
    "historic-adu": StaffPrecedent(
        title="Historic overlay ADU review pattern",
        summary="Prior staff reports required design review before ADU exterior changes.",
    )
}


def classify_for_planner_review(question: str) -> EscalationResult:
    normalized = question.casefold()
    if any(trigger in normalized for trigger in ESCALATION_TRIGGERS):
        return EscalationResult(
            status="escalate",
            reason="Question appears to require planner judgment or discretionary review.",
            next_step="Route to planning staff before giving a resident-facing answer.",
        )
    return EscalationResult(
        status="not_escalated",
        reason="No discretionary-review trigger found in the sample classifier.",
        next_step="Continue with citation-grounded informational workflow.",
    )


def get_staff_precedent(precedent_id: str) -> StaffPrecedent | None:
    return STAFF_PRECEDENTS.get(precedent_id)
