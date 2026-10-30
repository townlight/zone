"""FastAPI runtime foundation for Townlight Zoning."""

import os
from dataclasses import dataclass
from typing import Annotated

from civiccore import __version__ as CIVICCORE_VERSION
from civiccore.auth import (
    TrustedHeaderAuthConfig,
    authorize_trusted_header_roles,
    enforce_trusted_proxy_source,
    load_trusted_header_auth_config,
)
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from civiczone import __version__
from civiczone.parcel_lookup import ParcelLookupError, ParcelLookupRepository, lookup_parcel
from civiczone.public_ui import render_public_lookup_page
from civiczone.qa import answer_zoning_question
from civiczone.question_ledger import ZoneQuestionLedgerRepository
from civiczone.rule_lookup import (
    RuleLookupError,
    RuleLookupRepository,
    lookup_dimensional_rule,
    lookup_use_rule,
)
from civiczone.discretionary import (Unavailable, explain, nonconformity_review_note)
from civiczone.staff_context import classify_for_planner_review, get_staff_precedent
from civiczone.staff_ui import render_staff_workspace_page
from civiczone.staff_workflows import StaffWorkflowStore

app = FastAPI(
    title='Townlight Zoning',
    version=__version__,
    description='Parcel-aware zoning and land-use Q&A for Townlight.',
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = ", ".join(str(error["loc"][-1]) for error in exc.errors() if error.get("loc"))
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "Townlight Zoning could not process the request because required fields are missing or invalid.",
                "fix": (
                    "Send valid JSON with required fields. For resident Q&A, include "
                    "zone_code like 'R-2' and question like 'Can I build an ADU?'."
                ),
                "fields": fields,
            }
        },
    )

_parcel_lookup_repository: ParcelLookupRepository | None = None
_rule_lookup_repository: RuleLookupRepository | None = None
_question_ledger_repository: ZoneQuestionLedgerRepository | None = None
_parcel_rule_db_url: str | None = None
_staff_workflow_store = StaffWorkflowStore()
_staff_workflow_db_url: str | None = None


@dataclass(frozen=True)
class StaffPrincipal:
    subject: str
    roles: tuple[str, ...]


@app.get("/")
def root() -> dict[str, str]:
    """Return current product state without overstating unshipped behavior."""

    return {
        "name": "CivicZone",
        "version": __version__,
        "status": "v1 parcel-aware zoning Q&A runtime",
        "message": (
            "Townlight Zoning v0.2.2 provides deterministic parcel lookup, cited use-rule lookup, cited dimensional prechecks, "
            "resident zoning Q&A with refusal and escalation rules, staff workflow APIs, optional database-backed parcel/rule and question-ledger records, "
            "canonical zoning schema migrations, adversarial local integration mocks, an accessible resident UI, and a staff workflow UI shell. "
            "It does not make zoning determinations, give legal advice, replace planner review, or call live external systems by default."
        ),
        "next_step": "Configure local parcel/rule data, set the trusted staff proxy CIDR list, and route official decisions to planning staff.",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Return dependency/version health for deployment smoke checks."""

    return {
        "status": "ok",
        "service": "civiczone",
        "version": __version__,
        "civiccore_version": CIVICCORE_VERSION,
    }


@app.get("/civiczone", response_class=HTMLResponse)
def public_civiczone_page() -> str:
    """Return the accessible public sample UI."""

    return render_public_lookup_page()


@app.get("/civiczone/staff", response_class=HTMLResponse)
def staff_civiczone_page() -> str:
    """Return the staff workflow shell without exposing staff data in HTML."""

    return render_staff_workspace_page()


class ParcelLookupRequest(BaseModel):
    parcel_number: str | None = Field(default=None)
    address: str | None = Field(default=None)


class UseRuleLookupRequest(BaseModel):
    zone_code: str
    use: str


class DimensionalRuleLookupRequest(BaseModel):
    zone_code: str
    rule_type: str


class ZoneQuestionRequest(BaseModel):
    zone_code: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=1000)


class PlannerReviewRequest(BaseModel):
    question: str


class StaffQuestionAnswerRequest(BaseModel):
    zone_code: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=1000)


class AmbiguityReviewCreateRequest(BaseModel):
    zone_code: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)


class AmbiguityReviewUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=80)
    assigned_to: str | None = Field(default=None, max_length=255)
    resolution: str | None = Field(default=None, max_length=1000)


class StaffReportOutlineRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    question_ids: list[str] = Field(default_factory=list)
    queue_item_ids: list[str] = Field(default_factory=list)


class FlaggedAnswerCreateRequest(BaseModel):
    zone_code: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=1000)
    original_answer: str = Field(min_length=1, max_length=2000)
    flag_reason: str = Field(min_length=1, max_length=1000)
    citations: list[str] = Field(default_factory=list)


class FlaggedAnswerImproveRequest(BaseModel):
    improved_answer: str = Field(min_length=1, max_length=2000)
    improvement_notes: str = Field(min_length=1, max_length=1000)


def _require_staff_access(request: Request) -> StaffPrincipal:
    allowed_roles = {"planner", "staff", "zoning_admin"}
    config = _staff_trusted_header_config()
    enforce_trusted_proxy_source(
        request.client.host if request.client else None,
        service_name='Townlight Zoning',
        feature_name="staff workflow access",
        config=config,
        trusted_proxy_env_var="CIVICZONE_STAFF_TRUSTED_PROXY_CIDRS",
    )
    principal = authorize_trusted_header_roles(
        request.headers,
        service_name='Townlight Zoning',
        feature_name="staff workflow access",
        principal_header_name=config.principal_header_name,
        roles_header_name=config.roles_header_name,
        allowed_roles=allowed_roles,
        provider_name=config.provider_name,
    )
    return StaffPrincipal(subject=principal.subject or "staff", roles=tuple(sorted(principal.roles)))


def _staff_trusted_header_config() -> TrustedHeaderAuthConfig:
    config = load_trusted_header_auth_config(
        provider_env_var="CIVICZONE_STAFF_AUTH_PROVIDER",
        provider_default="CivicZone staff shell",
        principal_header_env_var="CIVICZONE_STAFF_PRINCIPAL_HEADER",
        principal_header_default="X-CivicZone-Principal",
        roles_header_env_var="CIVICZONE_STAFF_ROLES_HEADER",
        roles_header_default="X-CivicZone-Role",
        trusted_proxy_env_var="CIVICZONE_STAFF_TRUSTED_PROXY_CIDRS",
    )
    if config.trusted_proxy_cidrs:
        return config
    return TrustedHeaderAuthConfig(
        provider_name=config.provider_name,
        principal_header_name=config.principal_header_name,
        roles_header_name=config.roles_header_name,
        trusted_proxy_cidrs=("127.0.0.1/32", "::1/128"),
    )


@app.post("/api/v1/civiczone/parcels/lookup")
def parcel_lookup(request: ParcelLookupRequest) -> dict[str, object]:
    if not request.parcel_number and not request.address:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Provide either parcel_number or address.",
                "fix": "Send parcel_number '100-200-300' or address '123 Main St', or load local parcel records into CIVICZONE_PARCEL_RULE_DB_URL.",
            },
        )

    result = _lookup_parcel(parcel_number=request.parcel_number, address=request.address)
    if isinstance(result, ParcelLookupError):
        raise HTTPException(status_code=404, detail={"message": result.message, "fix": result.fix})

    return {
        "parcel_number": result.parcel_number,
        "address": result.address,
        "zone": {"code": result.zone_code, "name": result.zone_name},
        "overlays": list(result.overlays),
        "constraints": list(result.constraints),
        "source": result.source,
        "disclaimer": result.disclaimer,
    }


@app.post("/api/v1/civiczone/rules/use")
def use_rule_lookup(request: UseRuleLookupRequest) -> dict[str, str]:
    result = _lookup_use_rule(zone_code=request.zone_code, use=request.use)
    if isinstance(result, RuleLookupError):
        raise HTTPException(status_code=404, detail={"message": result.message, "fix": result.fix})
    return {
        "zone_code": result.zone_code,
        "use": result.use,
        "status": result.status,
        "review_path": result.review_path,
        "citation": result.citation,
        "disclaimer": result.disclaimer,
    }


@app.post("/api/v1/civiczone/rules/dimensional")
def dimensional_rule_lookup(request: DimensionalRuleLookupRequest) -> dict[str, str]:
    result = _lookup_dimensional_rule(zone_code=request.zone_code, rule_type=request.rule_type)
    if isinstance(result, RuleLookupError):
        raise HTTPException(status_code=404, detail={"message": result.message, "fix": result.fix})
    return {
        "zone_code": result.zone_code,
        "rule_type": result.rule_type,
        "value": result.value,
        "citation": result.citation,
        "disclaimer": result.disclaimer,
    }


class DiscretionaryExplanationRequest(BaseModel):
    process_section: str = Field(default="", max_length=255)
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
        process_source=_process_source(request.process_section),
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


def _process_source(section):
    if not section:
        return None
    import civiccode.main as code
    from datetime import date
    try:
        lookup = code.SECTION_STORE.lookup_section(section, as_of=date.today())
        source = code._get_source_store().get(lookup["version"]["source_id"])
        if source.public_visible and source.is_official and source.status == "active":
            return code._build_citation_for_section(section, date.today())
    except (code.SectionLifecycleError, code.SourceRegistryError):
        return None
    return None


def _rules_for_explanation():
    """The same rule source the dimensional lookup uses (no new data source)."""

    class _Adapter:
        """Adapt the module-level lookup to the repository shape ``explain`` wants."""

        @staticmethod
        def lookup_dimensional_rule(*, zone_code: str, rule_type: str):
            return _lookup_dimensional_rule(zone_code=zone_code, rule_type=rule_type)

    return _Adapter()


@app.post("/api/v1/civiczone/questions/answer")
def zone_question_answer(request: ZoneQuestionRequest) -> dict[str, object]:
    result = answer_zoning_question(
        zone_code=request.zone_code,
        question=request.question,
        use_rule_lookup=_lookup_use_rule,
        dimensional_rule_lookup=_lookup_dimensional_rule,
    )
    ledger_record = _record_zone_question(
        zone_code=request.zone_code,
        question=request.question,
        result=result,
    )
    return {
        "status": result.status,
        "answer": result.answer,
        "citations": list(result.citations),
        "reason": result.reason,
        "confidence": result.confidence,
        "next_step": result.next_step,
        "disclaimer": result.disclaimer,
        "ledger_record_id": ledger_record.id if ledger_record is not None else None,
    }


@app.post("/api/v1/civiczone/planner-review/classify")
def planner_review_classify(request: PlannerReviewRequest) -> dict[str, str]:
    result = classify_for_planner_review(request.question)
    return {"status": result.status, "reason": result.reason, "next_step": result.next_step}


@app.get("/api/v1/civiczone/staff/precedents/{precedent_id}")
def staff_precedent(
    precedent_id: str,
    _principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, str]:
    precedent = get_staff_precedent(precedent_id)
    if precedent is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Staff precedent not found.", "fix": "Try precedent_id 'historic-adu'."},
        )
    return {
        "title": precedent.title,
        "summary": precedent.summary,
        "visibility": precedent.visibility,
    }


@app.post("/api/v1/civiczone/staff/questions/answer")
def staff_question_answer(
    request: StaffQuestionAnswerRequest,
    principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    record = _get_staff_workflow_store().answer_planner_question(
        zone_code=request.zone_code,
        question_text=request.question,
        created_by=principal.subject or "staff",
    )
    return _staff_question_record_payload(record)


@app.post("/api/v1/civiczone/staff/ambiguity-reviews")
def create_ambiguity_review(
    request: AmbiguityReviewCreateRequest,
    principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    item = _get_staff_workflow_store().create_queue_item(
        zone_code=request.zone_code,
        question_text=request.question,
        reason=request.reason,
        created_by=principal.subject or "staff",
    )
    return _queue_item_payload(item)


@app.get("/api/v1/civiczone/staff/ambiguity-reviews")
def list_ambiguity_reviews(
    _principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
    status: str | None = None,
) -> dict[str, object]:
    return {
        "items": [
            _queue_item_payload(item)
            for item in _get_staff_workflow_store().list_queue_items(status=status)
        ],
        "visibility": "staff_only",
    }


@app.patch("/api/v1/civiczone/staff/ambiguity-reviews/{item_id}")
def update_ambiguity_review(
    item_id: str,
    request: AmbiguityReviewUpdateRequest,
    _principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    try:
        item = _get_staff_workflow_store().update_queue_item(
            item_id=item_id,
            status=request.status,
            assigned_to=request.assigned_to,
            resolution=request.resolution,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "Ambiguity review update is invalid.", "fix": str(exc)},
        ) from exc
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Ambiguity review item was not found.",
                "fix": "List staff ambiguity reviews and retry with an existing item id.",
            },
        )
    return _queue_item_payload(item)


@app.get("/api/v1/civiczone/staff/questions/analytics")
def staff_question_analytics(
    _principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
    high_volume_threshold: int = 2,
) -> dict[str, object]:
    analytics = _get_staff_workflow_store().analytics(high_volume_threshold=high_volume_threshold)
    return {
        "total_questions": analytics.total_questions,
        "by_status": analytics.by_status,
        "high_volume_questions": [
            {
                "zone_code": question.zone_code,
                "question_text": question.question_text,
                "count": question.count,
                "statuses": list(question.statuses),
                "latest_question_id": question.latest_question_id,
            }
            for question in analytics.high_volume_questions
        ],
        "generated_at": analytics.generated_at.isoformat(),
        "visibility": analytics.visibility,
    }


@app.post("/api/v1/civiczone/staff/reports/outline")
def staff_report_outline(
    request: StaffReportOutlineRequest,
    principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    outline = _get_staff_workflow_store().draft_report_outline(
        title=request.title,
        question_ids=request.question_ids,
        queue_item_ids=request.queue_item_ids,
        created_by=principal.subject or "staff",
    )
    return {
        "id": outline.id,
        "title": outline.title,
        "sections": list(outline.sections),
        "source_question_ids": list(outline.source_question_ids),
        "source_queue_item_ids": list(outline.source_queue_item_ids),
        "created_by": outline.created_by,
        "created_at": outline.created_at.isoformat(),
        "visibility": outline.visibility,
        "disclaimer": outline.disclaimer,
    }


@app.post("/api/v1/civiczone/staff/flagged-answers")
def create_flagged_answer_review(
    request: FlaggedAnswerCreateRequest,
    principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    review = _get_staff_workflow_store().flag_answer(
        zone_code=request.zone_code,
        question_text=request.question,
        original_answer=request.original_answer,
        flag_reason=request.flag_reason,
        citations=request.citations,
        created_by=principal.subject or "staff",
    )
    return _flagged_answer_payload(review)


@app.patch("/api/v1/civiczone/staff/flagged-answers/{review_id}/improve")
def improve_flagged_answer_review(
    review_id: str,
    request: FlaggedAnswerImproveRequest,
    principal: Annotated[StaffPrincipal, Depends(_require_staff_access)],
) -> dict[str, object]:
    review = _get_staff_workflow_store().improve_flagged_answer(
        review_id=review_id,
        improved_answer=request.improved_answer,
        improvement_notes=request.improvement_notes,
        reviewed_by=principal.subject or "staff",
    )
    if review is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Flagged answer review was not found.",
                "fix": "Create or list the flagged answer review before submitting improvements.",
            },
        )
    return _flagged_answer_payload(review)


def _parcel_rule_database_url() -> str | None:
    return os.environ.get("CIVICZONE_PARCEL_RULE_DB_URL")


def _get_parcel_repository() -> ParcelLookupRepository:
    global _parcel_lookup_repository, _parcel_rule_db_url
    db_url = _parcel_rule_database_url()
    if db_url is None:
        raise RuntimeError("CIVICZONE_PARCEL_RULE_DB_URL is not configured.")
    if db_url != _parcel_rule_db_url:
        _reset_configured_repositories()
        _parcel_rule_db_url = db_url
    if _parcel_lookup_repository is None:
        _parcel_lookup_repository = ParcelLookupRepository(db_url=db_url)
    return _parcel_lookup_repository


def _get_rule_repository() -> RuleLookupRepository:
    global _parcel_rule_db_url, _rule_lookup_repository
    db_url = _parcel_rule_database_url()
    if db_url is None:
        raise RuntimeError("CIVICZONE_PARCEL_RULE_DB_URL is not configured.")
    if db_url != _parcel_rule_db_url:
        _reset_configured_repositories()
        _parcel_rule_db_url = db_url
    if _rule_lookup_repository is None:
        _rule_lookup_repository = RuleLookupRepository(db_url=db_url, seed_defaults=False)
    return _rule_lookup_repository


def _get_question_ledger_repository() -> ZoneQuestionLedgerRepository:
    global _parcel_rule_db_url, _question_ledger_repository
    db_url = _parcel_rule_database_url()
    if db_url is None:
        raise RuntimeError("CIVICZONE_PARCEL_RULE_DB_URL is not configured.")
    if db_url != _parcel_rule_db_url:
        _reset_configured_repositories()
        _parcel_rule_db_url = db_url
    if _question_ledger_repository is None:
        _question_ledger_repository = ZoneQuestionLedgerRepository(db_url=db_url)
    return _question_ledger_repository


def _get_staff_workflow_store() -> StaffWorkflowStore:
    global _staff_workflow_db_url, _staff_workflow_store
    db_url = _parcel_rule_database_url()
    if db_url is None:
        if _staff_workflow_db_url is not None:
            _reset_staff_workflow_store()
        return _staff_workflow_store
    if db_url != _staff_workflow_db_url:
        _dispose_repository(_staff_workflow_store)
        _staff_workflow_store = StaffWorkflowStore(db_url=db_url)
        _staff_workflow_db_url = db_url
    return _staff_workflow_store


def _lookup_parcel(*, parcel_number: str | None = None, address: str | None = None):
    if _parcel_rule_database_url() is None:
        return lookup_parcel(parcel_number=parcel_number, address=address)
    return _get_parcel_repository().lookup(parcel_number=parcel_number, address=address)


def _lookup_use_rule(*, zone_code: str, use: str):
    if _parcel_rule_database_url() is None:
        return lookup_use_rule(zone_code=zone_code, use=use)
    return _get_rule_repository().lookup_use_rule(zone_code=zone_code, use=use)


def _lookup_dimensional_rule(*, zone_code: str, rule_type: str):
    if _parcel_rule_database_url() is None:
        return lookup_dimensional_rule(zone_code=zone_code, rule_type=rule_type)
    return _get_rule_repository().lookup_dimensional_rule(zone_code=zone_code, rule_type=rule_type)


def _record_zone_question(*, zone_code: str, question: str, result):
    if _parcel_rule_database_url() is None:
        return None
    escalation_reason = None
    if result.status == "escalate" or result.status == "refused":
        escalation_reason = result.next_step
    return _get_question_ledger_repository().record_answer(
        zone_code=zone_code,
        question_text=question,
        audience="resident",
        status=result.status,
        answer_text=result.answer,
        citations=result.citations,
        disclaimer=result.disclaimer,
        escalation_reason=escalation_reason,
    )


def _staff_question_record_payload(record) -> dict[str, object]:
    return {
        "id": record.id,
        "zone_code": record.zone_code,
        "question": record.question_text,
        "status": record.status,
        "answer": record.answer_text,
        "citations": list(record.citations),
        "code_cross_references": [
            {
                "citation": reference.citation,
                "source": reference.source,
                "relevance": reference.relevance,
            }
            for reference in record.code_cross_references
        ],
        "created_by": record.created_by,
        "created_at": record.created_at.isoformat(),
        "visibility": record.visibility,
        "disclaimer": record.disclaimer,
    }


def _queue_item_payload(item) -> dict[str, object]:
    return {
        "id": item.id,
        "zone_code": item.zone_code,
        "question": item.question_text,
        "reason": item.reason,
        "status": item.status,
        "assigned_to": item.assigned_to,
        "resolution": item.resolution,
        "source_question_id": item.source_question_id,
        "created_by": item.created_by,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "visibility": item.visibility,
    }


def _flagged_answer_payload(review) -> dict[str, object]:
    return {
        "id": review.id,
        "zone_code": review.zone_code,
        "question": review.question_text,
        "original_answer": review.original_answer,
        "flag_reason": review.flag_reason,
        "citations": list(review.citations),
        "status": review.status,
        "improved_answer": review.improved_answer,
        "improvement_notes": review.improvement_notes,
        "reviewed_by": review.reviewed_by,
        "created_by": review.created_by,
        "created_at": review.created_at.isoformat(),
        "updated_at": review.updated_at.isoformat(),
        "visibility": review.visibility,
    }


def _reset_staff_workflow_store() -> None:
    global _staff_workflow_db_url, _staff_workflow_store
    _dispose_repository(_staff_workflow_store)
    _staff_workflow_store = StaffWorkflowStore()
    _staff_workflow_db_url = None


def _dispose_repository(repository: object | None) -> None:
    engine = getattr(repository, "engine", None)
    if engine is not None:
        engine.dispose()


def _reset_configured_repositories() -> None:
    global _parcel_lookup_repository, _rule_lookup_repository, _question_ledger_repository
    _dispose_repository(_parcel_lookup_repository)
    _dispose_repository(_rule_lookup_repository)
    _dispose_repository(_question_ledger_repository)
    _parcel_lookup_repository = None
    _rule_lookup_repository = None
    _question_ledger_repository = None
    _reset_staff_workflow_store()
