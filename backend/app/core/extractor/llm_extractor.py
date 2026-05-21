"""LLMExtractor — call the LLM to extract structured facts (ExtractedFactsSchema) from a raw clinical note.

This is the primary extraction path, replacing the regex-based extractor. The regex
patterns are now used downstream by `RegexVerifier` to cross-check numeric facts.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.core.llm.client import LLMCallResult, LLMClient
from app.core.llm.schema import ExtractedFactsSchema

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a clinical fact extractor. Your job is to read an unstructured clinical note (ER notes, H&P, etc.) and produce a structured JSON object of atomic clinical facts.

## HARD CONSTRAINTS:
1. **ZERO FABRICATION**: Never invent values, units, or findings not explicitly present in the note. If a value is missing or unclear, omit the entire fact entry rather than guessing.
2. **VERBATIM SOURCE_SPAN**: Each fact MUST carry a `source_span` (start/end character offsets in the original note) pointing to the exact substring that supports the value.
3. **EMPTY VS MISSING**: If you genuinely have no facts of a given type, return an empty array `[]` for that field. NEVER omit a required field.
4. **DESCRIPTIVE FINDINGS GO TO `symptoms` OR `imaging_findings`**: Findings without numeric values (e.g. "fever", "leukocytosis", "RLQ pain", "CT concerning diverticulitis") must be captured in `symptoms` or `imaging_findings`, not in `labs` or `vitals`.
5. **`labs` AND `vitals` REQUIRE NUMERIC OR STANDARD QUALITATIVE VALUES**: Labs accept numeric (e.g. 412.0) or standard qualitative codes (LARGE, MODERATE, SMALL, TRACE, NEG, POS). Vitals must be numeric.
6. **UNITS**: Always include a `unit` string. For qualitative lab results, use empty string `""`.
7. **DEDUPLICATION**: If the same value appears multiple times (e.g. repeat glucose), include each occurrence as a separate fact with its own source_span.
8. **CONFIRMED vs DIFFERENTIAL — STRICT SEPARATION**:
   - `suspected_conditions` is ONLY for ACTIVE WORKING DIAGNOSES the clinician is currently treating or has documented as the leading impression. Look for them in sections labelled Assessment, Impression, Final Diagnosis, Diagnoses, Plan, or where the note clearly states the patient HAS / IS BEING TREATED FOR that condition.
   - `differential_diagnoses` is for anything the note frames as a possibility, alternative, or rule-out. Move a diagnosis here if it appears under headings like "Differential diagnosis", "Diagnostic considerations", "Considered", or near hedge words: "possible", "concern for", "concern for possible", "suspected", "suspicion", "may represent", "cannot rule out", "rule out", "r/o", "less likely", "unlikely", "ruled out".
   - A diagnosis appearing in BOTH a confirmed section AND a hedge context goes to `suspected_conditions` (confirmed wins).
   - When in doubt → put it in `differential_diagnoses`, never both.
9. **`urine_glucose` vs `glucose_mg_dl`**: glucose values reported inside a urinalysis section (after headings like "Urinalysis", "Urine Source", "Spec Gravity", "Color:") must use `name="urine_glucose"`. Only plasma / serum / POC glucose may use `name="glucose_mg_dl"`. If unsure, prefer `urine_glucose`.

## FIELD NAMING (use snake_case, stable across cases):
- `labs[].name`: glucose_mg_dl, urine_glucose, arterial_ph, venous_ph, bicarbonate, serum_ketones, urine_ketones, anion_gap, wbc, creatinine, bun, sodium, potassium, chloride, co2, lactate, troponin, hemoglobin, gfr (extend if needed)
- `vitals[].name`: hr, rr, temp_c, bp_systolic, bp_diastolic, spo2
- `symptoms[].name`: snake_case slug (e.g. fever, rlq_pain, ams, kussmaul_breathing, dehydration, leukocytosis)
- `medications[].name`: drug name as written in the note (preserve case for brand names like Jardiance)

## OUTPUT FORMAT:
Return a valid JSON object with EXACTLY these fields (all required, lists may be empty `[]`, strings may be empty `""`):
{
  "chief_complaint": "string - the patient's main complaint as a short phrase",
  "hpi_summary": "string - 1-2 sentence summary of HPI",
  "suspected_conditions": ["array - ONLY active working diagnoses the clinician is treating"],
  "differential_diagnoses": ["array - possibilities, alternatives, rule-outs, hedge-worded diagnoses"],
  "labs": [{"name": "...", "value": <number or qualitative-string>, "unit": "...", "source_span": {"start": 0, "end": 0}}],
  "vitals": [{"name": "...", "value": <number>, "unit": "...", "source_span": {"start": 0, "end": 0}}],
  "symptoms": [{"name": "...", "description": "...", "source_span": {"start": 0, "end": 0}}],
  "medications": [{"name": "...", "dose": "...", "route": "...", "source_span": {"start": 0, "end": 0}}],
  "imaging_findings": ["array of imaging report conclusions, e.g. 'CT concerning acute diverticulitis'"],
  "interventions": ["array of ER treatments already given, e.g. 'IV fluids', 'Insulin drip started'"],
  "history": ["array of relevant past medical history items"]
}

## REQUIRED FIELDS (all 11 top-level keys are MANDATORY):
chief_complaint, hpi_summary, suspected_conditions, differential_diagnoses, labs, vitals, symptoms, medications, imaging_findings, interventions, history

If the note contains no facts of a given type, return `[]` for that array (or `""` for the two string fields). NEVER omit a key.

## Pre-output checklist (mentally verify before returning):
- [ ] All 11 top-level keys present (including `differential_diagnoses`)
- [ ] Every hedge-worded or rule-out diagnosis is in `differential_diagnoses`, NOT in `suspected_conditions`
- [ ] Every glucose inside a urinalysis section uses `name="urine_glucose"`, never `glucose_mg_dl`
- [ ] Each lab has: name, value, unit, source_span{start,end}
- [ ] Each vital has: name, value, unit, source_span{start,end}
- [ ] Each symptom has: name, description, source_span{start,end}
- [ ] Each medication has: name, dose, route, source_span{start,end}
- [ ] No extra top-level keys
- [ ] No markdown fences

No markdown fences. No commentary. Only the JSON object.
"""


def build_user_prompt(raw_text: str) -> str:
    """Build the user prompt for the extraction stage."""
    return f"""## Clinical note (verbatim, do not modify)
{raw_text}

## Task
Extract all atomic clinical facts present in the note above. Follow the HARD CONSTRAINTS strictly. Return a JSON object matching the OUTPUT FORMAT.

For every fact you include, the `source_span` MUST be the exact start/end character indices (0-based, end-exclusive) of the supporting substring in the note above.
"""


def empty_facts() -> ExtractedFactsSchema:
    """Return empty facts (used when the LLM is unconfigured or the call fails)."""
    return ExtractedFactsSchema(
        chief_complaint="",
        hpi_summary="",
        suspected_conditions=[],
        differential_diagnoses=[],
        labs=[],
        vitals=[],
        symptoms=[],
        medications=[],
        imaging_findings=[],
        interventions=[],
        history=[],
    )


class LLMExtractor:
    """Primary LLM-based fact extractor."""

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or LLMClient()

    @property
    def is_configured(self) -> bool:
        return self._client.is_configured

    def extract(
        self, raw_text: str
    ) -> tuple[ExtractedFactsSchema, LLMCallResult | None]:
        """Extract structured facts from raw text.

        Returns:
            (facts, call_result) — on failure `facts` is empty and `call_result` reflects the error.
            When the client is not configured, `call_result` is None.
        """
        if not self._client.is_configured:
            logger.warning("LLM is not configured; LLMExtractor returning empty facts")
            return (empty_facts(), None)

        schema = ExtractedFactsSchema.model_json_schema()
        parsed, call_result = self._client.chat_with_repair(
            SYSTEM_PROMPT,
            build_user_prompt(raw_text),
            validate=self._parse_response,
            schema=schema,
            schema_name="extracted_facts",
        )

        if parsed is None:
            return (empty_facts(), call_result)
        return (parsed, call_result)

    def _parse_response(self, raw_response: str) -> ExtractedFactsSchema | None:
        """Parse the LLM JSON response and run Pydantic validation."""
        try:
            data = json.loads(raw_response)
            # Tolerate older LLM outputs that still omit `differential_diagnoses`.
            # The field is required in the schema, but we'd rather backfill an empty
            # list than discard a full-formed labs/vitals payload over a single key.
            if isinstance(data, dict) and "differential_diagnoses" not in data:
                data["differential_diagnoses"] = []
            return ExtractedFactsSchema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("LLMExtractor response parse failed: %s", str(e)[:300])
            return None
