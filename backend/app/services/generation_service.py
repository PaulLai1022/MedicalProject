"""GenerationService — orchestrates LLMExtractor + RegexVerifier + RulesEngine + NarrativeComposer + persistence.

Two public entry points:

- `run(db, case_id, force)` — synchronous; returns the full CaseDetail dict.
- `run_streaming(db, case_id, force)` — generator yielding SSE byte frames for the FastAPI
  StreamingResponse. Internally consumes the same `_run_pipeline()` generator, only the
  framing differs.
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.extractor.llm_extractor import LLMExtractor
from app.core.extractor.verifier import RegexVerifier, VerifiedFacts
from app.core.llm.composer import NarrativeComposer
from app.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.rules.engine import RulesEngine
from app.core.sse import format_event
from app.infra.repositories import case_repo, llm_log_repo

logger = logging.getLogger(__name__)


# Pipeline stage descriptors (index order must match the yields in `_run_pipeline`).
_STAGES = [
    {"stage": "reading",            "label": "Reading note"},
    {"stage": "extracting",         "label": "Extracting facts with LLM"},
    {"stage": "verifying_matching", "label": "Cross-checking values & matching MCG rules"},
    {"stage": "composing",          "label": "Composing Revised HPI"},
]
_TOTAL_STAGES = len(_STAGES)


def _stage_event(index: int) -> tuple[str, dict]:
    """Build a `(event_type, payload)` tuple for stage index 0..3."""
    s = _STAGES[index]
    return ("stage", {**s, "index": index, "total": _TOTAL_STAGES})


def _run_pipeline(db: Session, case_id: str, force: bool) -> Iterator[tuple[str, dict]]:
    """Run the pipeline, yielding `(event_type, payload)` tuples.

    Event sequence:
        ("stage", {stage,label,index,total})  × 4
        ("done",  CaseDetail)

    Or:
        ("error", {message})  on unrecoverable error.
    """
    settings = get_settings()

    # Stage 0: reading
    yield _stage_event(0)
    case = case_repo.get_case(db, case_id)
    if not case:
        yield ("error", {"message": f"Case not found: {case_id}"})
        return

    existing = case_repo.get_structured(db, case_id)
    if existing and not force:
        # Idempotent return; still emit a final 'done' event so the client transitions cleanly.
        yield ("done", _build_detail(db, case))
        return

    # Stage 1: LLMExtractor
    yield _stage_event(1)
    llm_extractor = LLMExtractor()
    facts, extract_call = llm_extractor.extract(case.raw_text)

    # Stage 2: RegexVerifier + RulesEngine (combined — verifier alone is sub-second)
    yield _stage_event(2)
    verifier = RegexVerifier()
    verified = verifier.verify(case.raw_text, facts)
    engine = RulesEngine()
    rule_result = engine.evaluate(verified)

    # Stage 3: NarrativeComposer
    yield _stage_event(3)
    composer = NarrativeComposer()
    narrative, compose_call = composer.compose(case.raw_text, verified, rule_result)

    # Persist + done
    warnings: list[str] = []
    if extract_call is None:
        warnings.append("llm_not_configured")
    elif extract_call.status == "error":
        warnings.append("llm_extractor_error")
    if compose_call and compose_call.status == "error":
        warnings.append("llm_composer_error")
    warnings.extend(verified.warnings())

    structured_data = {
        "chief_complaint_machine": narrative.chief_complaint,
        "hpi_summary_machine": narrative.hpi_summary,
        "disposition_machine": rule_result.disposition,
        "key_findings_machine": json.dumps(narrative.key_findings, ensure_ascii=False),
        "suspected_conditions_machine": json.dumps(narrative.suspected_conditions, ensure_ascii=False),
        "uncertainties_machine": json.dumps(narrative.uncertainties, ensure_ascii=False),
        "origin_map": json.dumps({
            "chiefComplaint": "machine",
            "hpiSummary": "machine",
            "disposition": "machine",
            "keyFindings": "machine",
            "suspectedConditions": "machine",
            "uncertainties": "machine",
        }),
        "decision_path": rule_result.decision_path,
        "mcg_hits": json.dumps(
            [_hit_to_dict(h) for h in rule_result.hits], ensure_ascii=False
        ),
        "missing_core_fields": json.dumps(rule_result.missing_core_fields, ensure_ascii=False),
        "warnings": json.dumps(warnings, ensure_ascii=False),
        "extracted_facts": json.dumps(_facts_to_dict(verified), ensure_ascii=False),
    }

    if force and existing:
        for key, val in structured_data.items():
            setattr(existing, key, val)
        existing.chief_complaint_user = None
        existing.hpi_summary_user = None
        existing.disposition_user = None
        existing.key_findings_user = None
        existing.suspected_conditions_user = None
        existing.uncertainties_user = None
        from datetime import datetime, timezone
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
    else:
        case_repo.upsert_structured(db, case_id, structured_data)

    sentences_data = []
    for s in narrative.revised_hpi.sentences:
        sentences_data.append({
            "text": s.text,
            "sources": s.sources,
            "reason_clinical": s.reason_clinical,
            "reason_guideline": s.reason_guideline,
        })
    case_repo.replace_sentences(db, case_id, sentences_data)

    if settings.llm_log_enabled:
        if extract_call is not None:
            llm_log_repo.create(
                db,
                case_id=case_id,
                prompt=f"[STAGE]extractor\n[SYSTEM]\n(see llm_extractor.py)\n",
                raw_response=extract_call.raw_response,
                duration_ms=extract_call.duration_ms,
                status=extract_call.status,
                model=extract_call.model,
            )
        if compose_call is not None:
            user_prompt = build_user_prompt(case.raw_text, verified, rule_result)
            prompt_text = f"[STAGE]composer\n[SYSTEM]\n{SYSTEM_PROMPT}\n\n[USER]\n{user_prompt}"
            llm_log_repo.create(
                db,
                case_id=case_id,
                prompt=prompt_text,
                raw_response=compose_call.raw_response,
                duration_ms=compose_call.duration_ms,
                status=compose_call.status,
                model=compose_call.model,
            )

    from datetime import datetime, timezone
    case.updated_at = datetime.now(timezone.utc)
    db.commit()

    yield ("done", _build_detail(db, case))


def run(db: Session, case_id: str, force: bool = False) -> dict:
    """Synchronous run — drains the pipeline generator and returns the final CaseDetail.

    Used by the existing non-streaming code paths (e.g. seed.py prewarm).
    """
    final: dict | None = None
    last_error: dict | None = None
    for event_type, payload in _run_pipeline(db, case_id, force):
        if event_type == "done":
            final = payload
        elif event_type == "error":
            last_error = payload
    if final is not None:
        return final
    raise ValueError(last_error.get("message") if last_error else "generation produced no result")


def run_streaming(db: Session, case_id: str, force: bool = False) -> Iterator[bytes]:
    """Streaming run — yields SSE byte frames for FastAPI StreamingResponse."""
    try:
        for event_type, payload in _run_pipeline(db, case_id, force):
            yield format_event(event_type, payload)
    except Exception as e:  # last-resort safety net for unhandled errors mid-stream
        logger.exception("run_streaming crashed")
        yield format_event("error", {"message": str(e) or "internal error"})


def _build_detail(db: Session, case) -> dict:
    """Assemble the full CaseDetail response."""
    structured = case_repo.get_structured(db, case.id)
    sentences = case_repo.get_sentences(db, case.id)

    result = {
        "id": case.id,
        "rawText": case.raw_text,
        "createdAt": case.created_at.isoformat() if case.created_at else None,
        "updatedAt": case.updated_at.isoformat() if case.updated_at else None,
        "structured": None,
    }

    if structured:
        result["structured"] = _build_structured_response(structured, sentences)

    return result


def _build_structured_response(structured, sentences) -> dict:
    """Build the structured response body."""
    def resolve(machine, user):
        if user is not None:
            return {"value": user, "machineValue": machine, "origin": "user"}
        return {"value": machine, "machineValue": machine, "origin": "machine"}

    def resolve_json(machine_json, user_json):
        machine = json.loads(machine_json) if machine_json else []
        user = json.loads(user_json) if user_json else None
        if user is not None:
            return {"value": user, "machineValue": machine, "origin": "user"}
        return {"value": machine, "machineValue": machine, "origin": "machine"}

    sent_list = []
    for s in sentences:
        text = s.user_text if s.user_text is not None else s.machine_text
        sent_list.append({
            "id": s.id,
            "text": text,
            "machineText": s.machine_text,
            "origin": s.origin,
            "sources": json.loads(s.sources) if s.sources else [],
            "reasonClinical": s.reason_clinical,
            "reasonGuideline": s.reason_guideline,
        })

    full_text = " ".join(s["text"] or "" for s in sent_list)

    return {
        "chiefComplaint": resolve(structured.chief_complaint_machine, structured.chief_complaint_user),
        "hpiSummary": resolve(structured.hpi_summary_machine, structured.hpi_summary_user),
        "disposition": resolve(structured.disposition_machine, structured.disposition_user),
        "keyFindings": resolve_json(structured.key_findings_machine, structured.key_findings_user),
        "suspectedConditions": resolve_json(structured.suspected_conditions_machine, structured.suspected_conditions_user),
        "uncertainties": resolve_json(structured.uncertainties_machine, structured.uncertainties_user),
        "revisedHPI": {
            "fullText": full_text,
            "sentences": sent_list,
        },
        "decisionPath": structured.decision_path,
        "mcgHits": json.loads(structured.mcg_hits) if structured.mcg_hits else [],
        "missingCoreFields": json.loads(structured.missing_core_fields) if structured.missing_core_fields else [],
        "warnings": json.loads(structured.warnings) if structured.warnings else [],
        "extractedFacts": _camel_facts(structured.extracted_facts),
    }


def _camel_facts(extracted_facts_json: str | None) -> dict | None:
    """Deserialize the persisted snake_case facts and convert keys to camelCase for the frontend."""
    if not extracted_facts_json:
        return None
    data = json.loads(extracted_facts_json)
    return {
        "chiefComplaint": data.get("chief_complaint", ""),
        "hpiSummary": data.get("hpi_summary", ""),
        "suspectedConditions": data.get("suspected_conditions", []),
        "labs": data.get("labs", []),
        "vitals": data.get("vitals", []),
        "symptoms": data.get("symptoms", []),
        "medications": data.get("medications", []),
        "imagingFindings": data.get("imaging_findings", []),
        "interventions": data.get("interventions", []),
        "history": data.get("history", []),
        "verifications": data.get("verifications", []),
    }


def _hit_to_dict(hit) -> dict:
    return {
        "ruleId": hit.rule_id,
        "category": hit.category,
        "severity": hit.severity,
        "citation": hit.citation,
        "clinicalExplanation": hit.clinical_explanation,
        "evidence": hit.evidence,
    }


def _facts_to_dict(verified: VerifiedFacts) -> dict:
    """Serialize VerifiedFacts to a JSON-friendly structure (for `extracted_facts` persistence)."""
    facts = verified.facts
    return {
        "chief_complaint": facts.chief_complaint,
        "hpi_summary": facts.hpi_summary,
        "suspected_conditions": list(facts.suspected_conditions),
        "labs": [
            {
                "name": lab.name, "value": lab.value, "unit": lab.unit,
                "span": [lab.source_span.start, lab.source_span.end],
            }
            for lab in facts.labs
        ],
        "vitals": [
            {
                "name": v.name, "value": v.value, "unit": v.unit,
                "span": [v.source_span.start, v.source_span.end],
            }
            for v in facts.vitals
        ],
        "symptoms": [
            {
                "name": s.name, "description": s.description,
                "span": [s.source_span.start, s.source_span.end],
            }
            for s in facts.symptoms
        ],
        "medications": [
            {
                "name": m.name, "dose": m.dose, "route": m.route,
                "span": [m.source_span.start, m.source_span.end],
            }
            for m in facts.medications
        ],
        "imaging_findings": list(facts.imaging_findings),
        "interventions": list(facts.interventions),
        "history": list(facts.history),
        "verifications": [
            {
                "kind": v.fact_kind, "name": v.fact_name, "value": v.fact_value,
                "status": v.status, "detail": v.detail,
            }
            for v in verified.verifications
        ],
    }
