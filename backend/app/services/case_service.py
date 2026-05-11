"""Case business service — CRUD + authorization checks."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infra.models import User
from app.infra.repositories import case_repo
from app.services import generation_service


def create_case(db: Session, user: User, raw_text: str) -> dict:
    """Create a new case."""
    case = case_repo.create_case(db, user.id, raw_text)
    return {
        "id": case.id,
        "rawText": case.raw_text,
        "createdAt": case.created_at.isoformat(),
        "updatedAt": case.updated_at.isoformat(),
        "hasStructured": False,
    }


def list_cases(db: Session, user: User, page: int = 1, page_size: int = 20) -> dict:
    """Paginated list."""
    items, total = case_repo.list_cases_by_owner(db, user.id, page, page_size)
    result_items = []
    for case in items:
        structured = case_repo.get_structured(db, case.id)
        preview = _build_preview(case, structured)
        result_items.append(preview)

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


def get_case_detail(db: Session, user: User, case_id: str) -> dict:
    """Fetch case detail (with authorization check)."""
    case = _get_case_or_404(db, case_id)
    _check_ownership(case, user)
    return generation_service._build_detail(db, case)


def generate(db: Session, user: User, case_id: str, force: bool = False) -> dict:
    """Trigger generation."""
    case = _get_case_or_404(db, case_id)
    _check_ownership(case, user)
    return generation_service.run(db, case_id, force=force)


def generate_streaming(db: Session, user: User, case_id: str, force: bool = False):
    """Trigger streaming generation; returns the SSE byte iterator."""
    case = _get_case_or_404(db, case_id)
    _check_ownership(case, user)
    return generation_service.run_streaming(db, case_id, force=force)


def patch_case(db: Session, user: User, case_id: str, patch: dict) -> dict:
    """Save user edits."""
    case = _get_case_or_404(db, case_id)
    _check_ownership(case, user)
    case_repo.apply_user_patch(db, case_id, patch)
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    return generation_service._build_detail(db, case)


def delete_case(db: Session, user: User, case_id: str) -> None:
    """Delete a case."""
    case = _get_case_or_404(db, case_id)
    _check_ownership(case, user)
    case_repo.delete_case(db, case_id)


def _get_case_or_404(db: Session, case_id: str):
    case = case_repo.get_case(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Case not found"},
        )
    return case


def _check_ownership(case, user: User) -> None:
    if case.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You do not have access to this case"},
        )


def _build_preview(case, structured) -> dict:
    """Build the list-item preview."""
    preview = {
        "id": case.id,
        "chiefComplaintPreview": "",
        "disposition": None,
        "origin": "machine",
        "createdAt": case.created_at.isoformat() if case.created_at else None,
        "updatedAt": case.updated_at.isoformat() if case.updated_at else None,
    }
    if structured:
        cc = structured.chief_complaint_user or structured.chief_complaint_machine or ""
        preview["chiefComplaintPreview"] = cc[:60]
        preview["disposition"] = structured.disposition_user or structured.disposition_machine
        import json
        origin_map = json.loads(structured.origin_map or "{}")
        preview["origin"] = origin_map.get("chiefComplaint", "machine")
    return preview
