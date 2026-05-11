"""Case repository layer — CRUD operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.infra.models import Case, CaseStructured, RevisedHpiSentence


def create_case(db: Session, owner_user_id: str, raw_text: str) -> Case:
    """Create a new Case."""
    now = datetime.now(timezone.utc)
    case = Case(
        id=str(uuid.uuid4()),
        owner_user_id=owner_user_id,
        raw_text=raw_text,
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, case_id: str) -> Case | None:
    return db.query(Case).filter(Case.id == case_id).first()


def list_cases_by_owner(
    db: Session, owner_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[Case], int]:
    """Return a page of the user's cases along with the total count: (items, total)."""
    query = db.query(Case).filter(Case.owner_user_id == owner_id)
    total = query.count()
    items = (
        query.order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_structured(db: Session, case_id: str) -> CaseStructured | None:
    return db.query(CaseStructured).filter(CaseStructured.case_id == case_id).first()


def get_sentences(db: Session, case_id: str) -> list[RevisedHpiSentence]:
    return (
        db.query(RevisedHpiSentence)
        .filter(RevisedHpiSentence.case_id == case_id)
        .order_by(RevisedHpiSentence.sort_order)
        .all()
    )


def upsert_structured(db: Session, case_id: str, data: dict) -> CaseStructured:
    """Create or update the case_structured record."""
    now = datetime.now(timezone.utc)
    existing = get_structured(db, case_id)
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    structured = CaseStructured(case_id=case_id, created_at=now, updated_at=now, **data)
    db.add(structured)
    db.commit()
    db.refresh(structured)
    return structured


def replace_sentences(
    db: Session, case_id: str, sentences_data: list[dict]
) -> list[RevisedHpiSentence]:
    """Replace all sentences for a case (used during machine generation)."""
    now = datetime.now(timezone.utc)
    # Delete existing sentences
    db.query(RevisedHpiSentence).filter(
        RevisedHpiSentence.case_id == case_id
    ).delete()

    new_sentences = []
    for i, s in enumerate(sentences_data):
        sent = RevisedHpiSentence(
            id=str(uuid.uuid4()),
            case_id=case_id,
            sort_order=i,
            machine_text=s.get("text", ""),
            user_text=None,
            origin="machine",
            sources=json.dumps(s.get("sources", []), ensure_ascii=False),
            reason_clinical=s.get("reason_clinical", ""),
            reason_guideline=s.get("reason_guideline", ""),
            created_at=now,
            updated_at=now,
        )
        db.add(sent)
        new_sentences.append(sent)

    db.commit()
    return new_sentences


def apply_user_patch(db: Session, case_id: str, patch: dict) -> None:
    """Apply a user-edit patch to the structured record and sentences."""
    now = datetime.now(timezone.utc)
    structured = get_structured(db, case_id)
    if not structured:
        return

    # Scalar field patches
    scalar_fields = [
        "chief_complaint", "hpi_summary", "disposition",
    ]
    json_fields = ["key_findings", "suspected_conditions", "uncertainties"]

    origin_map = json.loads(structured.origin_map or "{}")

    for field in scalar_fields:
        key = _camel_to_snake(field)
        if key in patch:
            user_val = patch[key].get("userValue")
            setattr(structured, f"{key}_user", user_val)
            origin_map[field] = "user" if user_val is not None else "machine"

    for field in json_fields:
        key = _camel_to_snake(field)
        if key in patch:
            user_val = patch[key].get("userValue")
            if user_val is not None:
                setattr(structured, f"{key}_user", json.dumps(user_val, ensure_ascii=False))
                origin_map[field] = "user"
            else:
                setattr(structured, f"{key}_user", None)
                origin_map[field] = "machine"

    structured.origin_map = json.dumps(origin_map, ensure_ascii=False)
    structured.updated_at = now

    # Sentence patches
    if "sentences" in patch:
        _patch_sentences(db, case_id, patch["sentences"], now)

    # Delete sentences
    if "deleted_sentence_ids" in patch:
        for sid in patch["deleted_sentence_ids"]:
            db.query(RevisedHpiSentence).filter(
                RevisedHpiSentence.id == sid,
                RevisedHpiSentence.case_id == case_id,
            ).delete()

    db.commit()


def _patch_sentences(
    db: Session, case_id: str, sentences: list[dict], now: datetime
) -> None:
    """Update existing sentences or insert new ones."""
    for s in sentences:
        sid = s.get("id")
        if sid:
            # Update an existing sentence
            existing = db.query(RevisedHpiSentence).filter(
                RevisedHpiSentence.id == sid
            ).first()
            if existing:
                user_text = s.get("userText")
                existing.user_text = user_text
                existing.origin = "user" if user_text is not None else "machine"
                if "sources" in s:
                    existing.sources = json.dumps(s["sources"], ensure_ascii=False)
                if "reasonClinical" in s:
                    existing.reason_clinical = s["reasonClinical"]
                if "reasonGuideline" in s:
                    existing.reason_guideline = s["reasonGuideline"]
                if "sortOrder" in s:
                    existing.sort_order = s["sortOrder"]
                existing.updated_at = now
        else:
            # Insert a new sentence
            new_sent = RevisedHpiSentence(
                id=str(uuid.uuid4()),
                case_id=case_id,
                sort_order=s.get("sortOrder", 999),
                machine_text=None,
                user_text=s.get("userText", ""),
                origin="user",
                sources=json.dumps(s.get("sources", []), ensure_ascii=False),
                reason_clinical=s.get("reasonClinical", ""),
                reason_guideline=s.get("reasonGuideline", ""),
                created_at=now,
                updated_at=now,
            )
            db.add(new_sent)


def delete_case(db: Session, case_id: str) -> None:
    """Delete a case (cascades to structured + sentences + logs)."""
    case = get_case(db, case_id)
    if case:
        db.delete(case)
        db.commit()


def _camel_to_snake(name: str) -> str:
    """Simple camelCase → snake_case conversion."""
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
