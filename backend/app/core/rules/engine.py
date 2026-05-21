"""MCG rules engine — pure function: identical input must yield identical output.

Input: VerifiedFacts (facts extracted by LLMExtractor and cross-checked by RegexVerifier).
Output: disposition + hits + missing_core_fields.

Facts with verification status "failed" are treated as missing (filtered out by
`VerifiedFacts.labs_for_engine()`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.extractor.verifier import VerifiedFacts
from app.core.llm.schema import LabFact, VitalFact
from app.core.rules.loader import RuleSet, load_rules
from app.core.rules.predicate import eval_predicate


@dataclass(frozen=True)
class RuleHit:
    """Record of a single matched rule."""
    rule_id: str
    category: str
    severity: str
    citation: str
    clinical_explanation: str
    evidence: str


@dataclass(frozen=True)
class RuleResult:
    """Rules-engine evaluation result."""
    disposition: str
    decision_path: str
    hits: list[RuleHit]
    missing_core_fields: list[str]


# Admission-class category set
_ADMIT_CATEGORIES = frozenset({
    "DKA_INPATIENT",
    "DKA_INPATIENT_ESCALATION",
    "HHS",
    "HYPERGLYCEMIA_INPATIENT",
})


# Alias table: LLM symptom names → canonical `clinical_phrase` namespace used by the rules engine.
# Keys are lowercase + underscores; values must match the field names in mcg_diabetes.json exactly.
_PHRASE_ALIASES: dict[str, str] = {
    # AMS
    "ams": "AMS",
    "altered_mental_status": "AMS",
    "confusion": "AMS",
    "obtundation": "AMS",
    "lethargy": "AMS",
    # Kussmaul
    "kussmaul": "Kussmaul",
    "kussmaul_breathing": "Kussmaul",
    "kussmaul_respirations": "Kussmaul",
    # DKA / HHS
    "dka": "DKA",
    "diabetic_ketoacidosis": "DKA",
    "hhs": "HHS",
    "hyperosmolar_hyperglycemic_state": "HHS",
    "euglycemic_dka": "euglycemic_DKA",
    # AKI / dehydration / infection
    "aki": "AKI",
    "acute_kidney_injury": "AKI",
    "dehydration": "dehydration",
    "volume_depletion": "dehydration",
    "hypovolemia": "dehydration",
    "infection": "infection",
    "sepsis": "infection",
    "uti": "infection",
    "pneumonia": "infection",
    "cellulitis": "infection",
}

# Drug → class alias. The LLM emits specific drug names; the rules engine matches by class.
_DRUG_TO_CLASS: dict[str, str] = {
    "jardiance": "SGLT2i",
    "farxiga": "SGLT2i",
    "invokana": "SGLT2i",
    "steglatro": "SGLT2i",
    "empagliflozin": "SGLT2i",
    "dapagliflozin": "SGLT2i",
    "canagliflozin": "SGLT2i",
    "ertugliflozin": "SGLT2i",
}

# Hedge / differential markers — if a symptom description contains any of these,
# the LLM was likely capturing a differential or rule-out, not an active finding.
# Filtering them out prevents INFECTION_TRIGGER / DEHYDRATION from firing on
# "possible sepsis" or "concern for dehydration" style hedge language.
_DIFFERENTIAL_MARKERS = (
    "differential",
    "considered",
    "less likely",
    "unlikely",
    "ruled out",
    "rule out",
    "r/o",
    "diagnostic considerations",
    "possible",
    "concern for",
    "concern for possible",
    "suspected",
    "suspicion",
    "cannot rule out",
    "may represent",
    "vs.",
    "versus",
)


def _is_differential_or_negated(text: str) -> bool:
    """Return True if `text` contains a differential / rule-out / hedge marker.

    Used to suppress symptom-derived clinical_phrase context entries that were
    captured from a differential-diagnosis section rather than an active finding.
    """
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _DIFFERENTIAL_MARKERS)


class RulesEngine:
    """MCG rules engine."""

    def __init__(self, rule_set: RuleSet | None = None):
        self._rule_set = rule_set or load_rules()

    def evaluate(self, verified: VerifiedFacts) -> RuleResult:
        """Evaluate all rules and return the disposition decision.

        Args:
            verified: facts extracted by LLMExtractor and cross-checked by RegexVerifier.
                      Facts with verification_failed status are already filtered out by
                      labs_for_engine / vitals_for_engine.
        """
        labs = verified.labs_for_engine()
        vitals = verified.vitals_for_engine()
        symptoms = verified.facts.symptoms
        medications = verified.facts.medications

        context = self._build_context(labs, vitals, symptoms, medications)
        hits = self._evaluate_rules(context)
        missing_core = self._compute_missing_core(labs)
        disposition, path = self._decide_disposition(hits, missing_core)
        return RuleResult(
            disposition=disposition,
            decision_path=path,
            hits=hits,
            missing_core_fields=missing_core,
        )

    # ─── context construction ───────────────────────────────────────

    def _build_context(
        self,
        labs: list[LabFact],
        vitals: list[VitalFact],
        symptoms,
        medications,
    ) -> dict[str, Any]:
        ctx: dict[str, Any] = {}

        # Labs — group by name and pick the most severe value
        labs_by_name: dict[str, list[LabFact]] = {}
        for lab in labs:
            labs_by_name.setdefault(lab.name, []).append(lab)

        for name, items in labs_by_name.items():
            if "ph" in name:
                # pH → take the minimum value
                numeric_vals = [it.value for it in items if isinstance(it.value, (int, float))]
                if numeric_vals:
                    ctx[name] = min(numeric_vals)
            elif name in ("serum_ketones", "urine_ketones"):
                # Qualitative value → take the first occurrence
                ctx[name] = items[0].value
            else:
                # Numeric → take the first valid value
                for it in items:
                    if isinstance(it.value, (int, float)):
                        ctx[name] = it.value
                        break

        # Vitals
        vitals_by_name: dict[str, list[VitalFact]] = {}
        for v in vitals:
            vitals_by_name.setdefault(v.name, []).append(v)
        for name, items in vitals_by_name.items():
            if items and isinstance(items[0].value, (int, float)):
                ctx[name] = items[0].value

        # Symptoms → clinical_phrase:XXX namespace (canonicalized via alias table).
        # Skip symptoms whose description / name is wrapped in differential or hedge language
        # ("possible sepsis", "concern for dehydration", "r/o infection") so admission rules
        # like INFECTION_TRIGGER / DEHYDRATION do not fire on rule-outs.
        for s in symptoms:
            descriptive_text = (s.description or "") + " " + (s.name or "")
            if _is_differential_or_negated(descriptive_text):
                continue
            slug = s.name.lower().strip().replace(" ", "_")
            canonical = _PHRASE_ALIASES.get(slug, s.name)
            ctx[f"clinical_phrase:{canonical}"] = True

        # Medications → medication:CLASS namespace (match by class)
        for m in medications:
            drug_key = m.name.lower().strip()
            drug_class = _DRUG_TO_CLASS.get(drug_key)
            if drug_class:
                ctx[f"medication:{drug_class}"] = True

        return ctx

    # ─── rule evaluation ────────────────────────────────────────────

    def _evaluate_rules(self, context: dict[str, Any]) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for rule in self._rule_set.rules:
            if eval_predicate(rule.predicate, context):
                evidence = self._extract_evidence(rule.predicate, context)
                hits.append(RuleHit(
                    rule_id=rule.id,
                    category=rule.category,
                    severity=rule.severity,
                    citation=rule.citation,
                    clinical_explanation=rule.clinical_explanation,
                    evidence=evidence,
                ))
        return hits

    def _extract_evidence(self, predicate: dict, context: dict[str, Any]) -> str:
        op = predicate.get("op", "")
        if op in ("and", "or"):
            parts = []
            for p in predicate.get("operands", []):
                e = self._extract_evidence(p, context)
                if e:
                    parts.append(e)
            return "; ".join(parts)
        if op == "not":
            return self._extract_evidence(predicate.get("operand", {}), context)

        field_name = predicate.get("field", "")
        value = context.get(field_name)
        if value is not None:
            return f"{field_name}={value}"
        return ""

    # ─── missing core-field computation ─────────────────────────────

    def _compute_missing_core(self, labs: list[LabFact]) -> list[str]:
        """Determine which core diagnostic fields are missing, based on the ruleset's core_fields config."""
        present_lab_names = {lab.name for lab in labs}
        missing: list[str] = []
        for cf in self._rule_set.core_fields:
            if not any(field_name in present_lab_names for field_name in cf.satisfied_by):
                missing.append(cf.name)
        return missing

    # ─── disposition decision ───────────────────────────────────────

    def _decide_disposition(
        self, hits: list[RuleHit], missing_core: list[str]
    ) -> tuple[str, str]:
        """Decide disposition using the ruleset's missing_threshold_unknown and matched categories."""
        total_core = len(self._rule_set.core_fields)
        threshold = self._rule_set.missing_threshold_unknown

        # 5.1 all core fields missing
        if total_core > 0 and len(missing_core) == total_core:
            return ("Unknown", "5.1_ALL_CORE_MISSING")

        # 5.2 missing >= threshold
        if len(missing_core) >= threshold:
            return ("Unknown", "5.2_TWO_OR_MORE_CORE_MISSING")

        # 5.3 any admit-class rule matched
        if any(h.category in _ADMIT_CATEGORIES for h in hits):
            return ("Admit", "5.3_ADMIT_RULE_HIT")

        # 5.4 only observation-class rules matched
        if any(h.category == "OBSERVATION" for h in hits):
            return ("Observe", "5.4_OBSERVATION_ONLY")

        # 5.5 no rules matched
        return ("Discharge", "5.5_NO_RULE_HIT")
