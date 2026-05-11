"""ORM model definitions — matches design §4.2 SQL schema exactly."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.infra.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_new_uuid)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    cases = relationship("Case", back_populates="owner", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=_new_uuid)
    owner_user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="cases")
    structured = relationship(
        "CaseStructured", back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    sentences = relationship(
        "RevisedHpiSentence", back_populates="case", cascade="all, delete-orphan"
    )
    llm_logs = relationship(
        "LlmCallLog", back_populates="case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_cases_owner_created", "owner_user_id", "created_at"),
    )


class CaseStructured(Base):
    __tablename__ = "case_structured"

    case_id = Column(
        String, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    chief_complaint_machine = Column(Text)
    chief_complaint_user = Column(Text)
    hpi_summary_machine = Column(Text)
    hpi_summary_user = Column(Text)
    disposition_machine = Column(Text)
    disposition_user = Column(Text)
    key_findings_machine = Column(Text)  # JSON array
    key_findings_user = Column(Text)
    suspected_conditions_machine = Column(Text)  # JSON array
    suspected_conditions_user = Column(Text)
    uncertainties_machine = Column(Text)  # JSON array
    uncertainties_user = Column(Text)
    origin_map = Column(Text, nullable=False, default="{}")
    decision_path = Column(Text, nullable=False, default="")
    mcg_hits = Column(Text, nullable=False, default="[]")
    missing_core_fields = Column(Text, nullable=False, default="[]")
    warnings = Column(Text, default="[]")
    extracted_facts = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    case = relationship("Case", back_populates="structured")


class RevisedHpiSentence(Base):
    __tablename__ = "revised_hpi_sentences"

    id = Column(String, primary_key=True, default=_new_uuid)
    case_id = Column(
        String, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    sort_order = Column(Integer, nullable=False)
    machine_text = Column(Text)
    user_text = Column(Text)
    origin = Column(String, nullable=False, default="machine")
    sources = Column(Text, nullable=False, default="[]")  # JSON array
    reason_clinical = Column(Text, nullable=False, default="")
    reason_guideline = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    case = relationship("Case", back_populates="sentences")

    __table_args__ = (
        Index("idx_sentences_case_order", "case_id", "sort_order"),
    )


class LlmCallLog(Base):
    __tablename__ = "llm_call_log"

    id = Column(String, primary_key=True, default=_new_uuid)
    case_id = Column(
        String, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    prompt = Column(Text, nullable=False)
    raw_response = Column(Text, nullable=False)
    duration_ms = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    model = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    case = relationship("Case", back_populates="llm_logs")

    __table_args__ = (
        Index("idx_llm_log_case", "case_id", "created_at"),
    )
