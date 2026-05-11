"""NarrativeComposer — orchestrates the LLM call, validation, and fallback.

Input: VerifiedFacts (LLMExtractor + RegexVerifier output) + RuleResult.
Output: LLMNarrativeSchema (Revised HPI + structured fields).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.core.llm.client import LLMCallResult, LLMClient
from app.core.llm.fallback import fallback_narrative
from app.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.llm.schema import LLMNarrativeSchema

if TYPE_CHECKING:
    from app.core.extractor.verifier import VerifiedFacts
    from app.core.rules.engine import RuleResult

logger = logging.getLogger(__name__)


class NarrativeComposer:
    """Compose the Revised HPI narrative."""

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or LLMClient()

    def compose(
        self,
        raw_text: str,
        verified: "VerifiedFacts",
        rule_result: "RuleResult",
    ) -> tuple[LLMNarrativeSchema, LLMCallResult | None]:
        """Call the LLM to compose the narrative. Falls back on failure.

        Returns:
            (narrative, llm_call_result) — `llm_call_result` is None when the LLM was not called.
        """
        if not self._client.is_configured:
            logger.warning("LLM not configured; using fallback")
            narrative = fallback_narrative(raw_text, verified, rule_result)
            return (narrative, None)

        user_prompt = build_user_prompt(raw_text, verified, rule_result)
        schema = LLMNarrativeSchema.model_json_schema()
        narrative, call_result = self._client.chat_with_repair(
            SYSTEM_PROMPT,
            user_prompt,
            validate=self._validate_schema_only,
            schema=schema,
            schema_name="narrative",
        )

        if narrative is not None:
            return (
                self._sanitize_narrative(narrative, raw_text, verified, rule_result),
                call_result,
            )

        logger.warning("LLM call or parsing failed (status=%s); using fallback", call_result.status)
        narrative = fallback_narrative(raw_text, verified, rule_result)
        return (narrative, call_result)

    def _validate_schema_only(self, raw_response: str) -> LLMNarrativeSchema | None:
        """JSON parse + Pydantic schema validation only, for use by chat_with_repair."""
        try:
            data = json.loads(raw_response)
            return LLMNarrativeSchema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("LLM response schema validation failed: %s", str(e)[:200])
            return None

    def _sanitize_narrative(
        self,
        narrative: LLMNarrativeSchema,
        raw_text: str,
        verified: "VerifiedFacts",
        rule_result: "RuleResult",
    ) -> LLMNarrativeSchema:
        """Sanitize LLM output so it does not conflict with rule-layer facts or verification results."""
        missing = set(rule_result.missing_core_fields)
        if missing:
            narrative.uncertainties = _merge_unique(
                narrative.uncertainties,
                [f"missing: {field}" for field in rule_result.missing_core_fields],
            )
            narrative.key_findings = [
                finding for finding in narrative.key_findings
                if not _mentions_missing_field(finding, missing)
            ]

        # verification_failed facts are treated as missing; surface them as uncertainties.
        verification_warnings = verified.warnings()
        if verification_warnings:
            narrative.uncertainties = _merge_unique(
                narrative.uncertainties, verification_warnings,
            )

        allowed_citations = {hit.citation for hit in rule_result.hits}
        allowed_evidence = {hit.evidence for hit in rule_result.hits if hit.evidence}
        extracted_values = _collect_extracted_value_strings(verified)

        for sentence in narrative.revised_hpi.sentences:
            if sentence.reason_guideline:
                if not allowed_citations or not any(
                    citation in sentence.reason_guideline for citation in allowed_citations
                ):
                    sentence.reason_guideline = ""
            if _mentions_missing_field(sentence.text, missing):
                sentence.reason_clinical = _append_note(
                    sentence.reason_clinical,
                    "Potentially conflicts with missing core fields from rules engine.",
                )
            sentence.sources = [source for source in sentence.sources if source and source in raw_text]

        if rule_result.disposition == "Unknown":
            narrative.uncertainties = _merge_unique(
                narrative.uncertainties,
                ["Rules engine could not determine disposition from available core evidence"],
            )
            narrative.key_findings = [
                finding for finding in narrative.key_findings
                if finding in allowed_evidence or any(value in finding for value in extracted_values)
            ]

        return narrative


def _merge_unique(current: list[str], additions: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in [*current, *additions]:
        clean = item.strip()
        if clean and clean not in seen:
            seen.add(clean)
            merged.append(clean)
    return merged


def _mentions_missing_field(text: str, missing_fields: set[str]) -> bool:
    lowered = text.lower()
    aliases = {
        "glucose": ("glucose", "blood sugar", "bs"),
        "ketones": ("ketone", "ketones", "acetone"),
        "acidosis_marker": ("ph", "bicarbonate", "co2", "acidosis"),
    }
    for field in missing_fields:
        terms = aliases.get(field, (field,))
        if any(term in lowered for term in terms):
            return True
    return False


def _collect_extracted_value_strings(verified) -> set[str]:
    values: set[str] = set()
    for lab in verified.facts.labs:
        values.add(str(lab.value))
    for vital in verified.facts.vitals:
        values.add(str(vital.value))
    for s in verified.facts.symptoms:
        if s.description:
            values.add(s.description)
        values.add(s.name)
    for m in verified.facts.medications:
        values.add(m.name)
    return {v for v in values if v}


def _append_note(text: str, note: str) -> str:
    if not text:
        return note
    if note in text:
        return text
    return f"{text} {note}"
