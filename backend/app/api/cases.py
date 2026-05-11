"""Case routes — /api/cases/*"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_current_user
from app.infra.db import get_db
from app.infra.models import User
from app.infra.repositories import llm_log_repo
from app.schemas.case import CreateCaseReq
from app.schemas.structured import PatchCaseReq
from app.services import case_service

router = APIRouter()


@router.post("", status_code=201)
def create_case(
    body: CreateCaseReq,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return case_service.create_case(db, user, body.raw_text)


@router.post("/{case_id}/generate")
def generate(
    case_id: str,
    force: bool = Query(default=False),
    stream: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate structured output.

    By default returns an SSE stream (`text/event-stream`) with stage events
    and a final 'done' event carrying the full CaseDetail. Pass `?stream=false`
    to get a plain JSON response instead (used by tests and seed prewarm).
    """
    if stream:
        iterator = case_service.generate_streaming(db, user, case_id, force=force)
        return StreamingResponse(
            iterator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",  # disable nginx response buffering
            },
        )
    return case_service.generate(db, user, case_id, force=force)


@router.get("")
def list_cases(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return case_service.list_cases(db, user, page=page, page_size=pageSize)


@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return case_service.get_case_detail(db, user, case_id)


@router.patch("/{case_id}")
def patch_case(
    case_id: str,
    body: PatchCaseReq,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    patch_data = _build_patch_dict(body)
    return case_service.patch_case(db, user, case_id, patch_data)


@router.get("/{case_id}/llm-log")
def get_llm_log(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Authorization check
    case_service._get_case_or_404(db, case_id)
    case_service._check_ownership(
        case_service._get_case_or_404(db, case_id), user
    )
    settings = get_settings()
    if not settings.llm_log_enabled:
        return {"enabled": False, "items": []}

    logs = llm_log_repo.list_by_case(db, case_id)
    return {
        "enabled": True,
        "items": [
            {
                "id": log.id,
                "prompt": log.prompt,
                "rawResponse": log.raw_response,
                "durationMs": log.duration_ms,
                "status": log.status,
                "model": log.model,
                "createdAt": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case_service.delete_case(db, user, case_id)
    return None


def _build_patch_dict(body: PatchCaseReq) -> dict:
    """Convert a PatchCaseReq into the dict shape expected by case_repo.apply_user_patch."""
    patch: dict = {}
    s = body.structured

    if s.chief_complaint:
        patch["chief_complaint"] = {"userValue": s.chief_complaint.user_value}
    if s.hpi_summary:
        patch["hpi_summary"] = {"userValue": s.hpi_summary.user_value}
    if s.disposition:
        patch["disposition"] = {"userValue": s.disposition.user_value}
    if s.key_findings:
        patch["key_findings"] = {"userValue": s.key_findings.user_value}
    if s.suspected_conditions:
        patch["suspected_conditions"] = {"userValue": s.suspected_conditions.user_value}
    if s.uncertainties:
        patch["uncertainties"] = {"userValue": s.uncertainties.user_value}

    if s.revised_hpi:
        if s.revised_hpi.sentences:
            patch["sentences"] = [
                {
                    "id": sent.id,
                    "userText": sent.user_text,
                    "sources": sent.sources,
                    "reasonClinical": sent.reason_clinical,
                    "reasonGuideline": sent.reason_guideline,
                    "sortOrder": sent.sort_order,
                }
                for sent in s.revised_hpi.sentences
            ]
        if s.revised_hpi.deleted_sentence_ids:
            patch["deleted_sentence_ids"] = s.revised_hpi.deleted_sentence_ids

    return patch
