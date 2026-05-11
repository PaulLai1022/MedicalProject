"""LLM fallback — produce a minimal structured narrative from the rules-layer output when the LLM call fails."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.core.llm.schema import LLMNarrativeSchema, RevisedHPISchema, SentenceSchema

if TYPE_CHECKING:
    from app.core.extractor.verifier import VerifiedFacts
    from app.core.rules.engine import RuleResult


def fallback_narrative(
    raw_text: str,
    verified: "VerifiedFacts",
    rule_result: "RuleResult",
) -> LLMNarrativeSchema:
    """Produce a fallback narrative based on rule-layer output, without calling the LLM."""
    facts = verified.facts
    chief = facts.chief_complaint or _extract_chief_complaint_heuristic(raw_text)
    key_findings = [h.evidence for h in rule_result.hits if h.evidence]
    suspected = list(facts.suspected_conditions) or _infer_suspected_conditions(verified, rule_result)
    uncertainties = [f"missing: {f}" for f in rule_result.missing_core_fields]
    uncertainties.append("LLM narrative composition failed; rule-based summary only")

    return LLMNarrativeSchema(
        chiefComplaint=chief,
        hpiSummary=facts.hpi_summary,
        keyFindings=key_findings,
        suspectedConditions=suspected,
        uncertainties=uncertainties,
        revisedHPI=RevisedHPISchema(sentences=_build_fallback_sentences(rule_result)),
    )


def _build_fallback_sentences(rule_result: "RuleResult") -> list[SentenceSchema]:
    """Plan B requires `sentences` to be non-empty; return a single fallback sentence."""
    text = (
        f"Disposition determined by rules engine as {rule_result.disposition} "
        f"via path {rule_result.decision_path}. LLM narrative was unavailable."
    )
    return [SentenceSchema(text=text, sources=[], reasonClinical="", reasonGuideline="")]


def _extract_chief_complaint_heuristic(raw_text: str) -> str:
    """Heuristic chief-complaint extraction — look for common markers."""
    patterns = [
        r"(?:chief\s+complaint|CC|reason\s+for\s+visit)\s*[:：]\s*(.+?)(?:\n|$)",
        r"(?:presents?\s+(?:with|for|to))\s+(.+?)(?:\.|,|\n)",
    ]
    for pat in patterns:
        match = re.search(pat, raw_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]

    first_line = raw_text.strip().split("\n")[0][:100]
    return first_line


def _infer_suspected_conditions(
    verified: "VerifiedFacts", rule_result: "RuleResult"
) -> list[str]:
    """Infer suspected diagnoses from facts and rule hits."""
    conditions: list[str] = []
    categories = {h.category for h in rule_result.hits}

    if "DKA_INPATIENT" in categories or "DKA_INPATIENT_ESCALATION" in categories:
        conditions.append("Diabetic Ketoacidosis (DKA)")
    if "HHS" in categories:
        conditions.append("Hyperosmolar Hyperglycemic State (HHS)")
    if "HYPERGLYCEMIA_INPATIENT" in categories:
        conditions.append("Hyperglycemia requiring inpatient management")

    # SGLT2i exposure + DKA → euglycemic DKA
    has_sglt2i = any(
        m.name.lower() in {"jardiance", "farxiga", "invokana", "steglatro",
                            "empagliflozin", "dapagliflozin", "canagliflozin", "ertugliflozin"}
        for m in verified.facts.medications
    )
    if has_sglt2i and "DKA_INPATIENT" in categories:
        conditions.append("Euglycemic DKA (SGLT2i-associated)")

    return conditions
