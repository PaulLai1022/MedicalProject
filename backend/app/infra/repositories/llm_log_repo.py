"""LLM call-log repository layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.infra.models import LlmCallLog


def create(
    db: Session,
    case_id: str,
    prompt: str,
    raw_response: str,
    duration_ms: int,
    status: str,
    model: str,
) -> LlmCallLog:
    """Create an LLM-call log record."""
    log = LlmCallLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        prompt=prompt,
        raw_response=raw_response,
        duration_ms=duration_ms,
        status=status,
        model=model,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_by_case(db: Session, case_id: str) -> list[LlmCallLog]:
    """Return all LLM-call logs for a case, sorted by time descending."""
    return (
        db.query(LlmCallLog)
        .filter(LlmCallLog.case_id == case_id)
        .order_by(LlmCallLog.created_at.desc())
        .all()
    )
