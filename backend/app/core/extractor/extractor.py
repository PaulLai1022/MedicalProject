"""Extractor — extract atomic facts from raw clinical notes. Pure functions, no external deps.

NOTE: This regex-based extractor has been superseded by `LLMExtractor` + `RegexVerifier`
on the primary path. The regex patterns in `patterns.py` are now reused by the verifier
to cross-check LLM-produced facts, and this module is retained for reference / backup only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.extractor.dictionaries import SGLT2I_PATTERN, DIABETES_DRUGS_PATTERN
from app.core.extractor.normalizers import try_parse_float
from app.core.extractor.patterns import (
    CLINICAL_PHRASE_PATTERNS,
    LAB_PATTERNS,
    VITAL_PATTERNS,
    BP_PATTERN,
    PH_PATTERN,
    KETONES_PATTERN,
    GLUCOSE_PATTERN,
)


@dataclass(frozen=True)
class AtomicFact:
    """A single atomic fact."""
    name: str
    value: float | str | None
    unit: str | None
    source_span: tuple[int, int]
    raw_match: str


@dataclass
class ExtractedFacts:
    """Collection of extraction results."""
    vitals: dict[str, list[AtomicFact]] = field(default_factory=dict)
    labs: dict[str, list[AtomicFact]] = field(default_factory=dict)
    clinical_phrases: list[AtomicFact] = field(default_factory=list)
    medications: list[AtomicFact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Extractor:
    """Rule-based extractor — deterministic and replayable."""

    def extract(self, raw_text: str) -> ExtractedFacts:
        facts = ExtractedFacts()
        self._extract_labs(raw_text, facts)
        self._extract_vitals(raw_text, facts)
        self._extract_clinical_phrases(raw_text, facts)
        self._extract_medications(raw_text, facts)
        return facts

    def _extract_labs(self, text: str, facts: ExtractedFacts) -> None:
        """Extract lab values."""
        # Specially handled fields should only be invoked once.
        ph_done = False
        ketones_done = False
        glucose_done = False

        for field_name, pattern in LAB_PATTERNS.items():
            # pH requires disambiguating arterial vs venous
            if field_name in ("arterial_ph", "venous_ph"):
                if not ph_done:
                    self._extract_ph(text, facts)
                    ph_done = True
                continue
            # ketones need qualitative-value handling
            if field_name in ("serum_ketones", "urine_ketones"):
                if not ketones_done:
                    self._extract_ketones(text, facts)
                    ketones_done = True
                continue
            if field_name == "glucose_mg_dl":
                if not glucose_done:
                    self._extract_glucose(text, facts)
                    glucose_done = True
                continue

            for match in pattern.finditer(text):
                raw_val = match.group(1)
                numeric = try_parse_float(raw_val)
                fact = AtomicFact(
                    name=field_name,
                    value=numeric if numeric is not None else raw_val,
                    unit=None,
                    source_span=(match.start(), match.end()),
                    raw_match=match.group(0),
                )
                facts.labs.setdefault(field_name, []).append(fact)

    def _extract_ph(self, text: str, facts: ExtractedFacts) -> None:
        """Disambiguate arterial vs venous pH and exclude pH values from urinalysis sections."""
        for match in PH_PATTERN.finditer(text):
            raw_match = match.group(0).lower()

            # Exclude pH hits that are actually urine pH (not blood gas).
            prefix_ctx = text[max(0, match.start() - 500):match.start()].lower()
            if self._is_urinalysis_context(prefix_ctx):
                continue

            if "aph" in raw_match or "arterial" in raw_match or "a." in raw_match:
                name = "arterial_ph"
            elif "vph" in raw_match or "venous" in raw_match or "v." in raw_match or raw_match.startswith("v ph"):
                name = "venous_ph"
            else:
                # Bare "pH" with no prefix — use context to decide the source.
                if "venous" in prefix_ctx or "vbg" in prefix_ctx:
                    name = "venous_ph"
                elif "arterial" in prefix_ctx or "abg" in prefix_ctx:
                    name = "arterial_ph"
                else:
                    name = "arterial_ph"  # default to arterial

            val = try_parse_float(match.group(1))
            # Safety check: blood gas pH is typically 6.8–7.8; anything outside is not a blood gas value.
            if val is not None and (val < 6.8 or val > 7.8):
                continue

            fact = AtomicFact(
                name=name, value=val, unit=None,
                source_span=(match.start(), match.end()),
                raw_match=match.group(0),
            )
            facts.labs.setdefault(name, []).append(fact)

    def _extract_ketones(self, text: str, facts: ExtractedFacts) -> None:
        """Extract ketones (qualitative or numeric) and classify as urine vs serum."""
        for match in KETONES_PATTERN.finditer(text):
            raw_val = match.group(1)
            raw_match = match.group(0).lower()
            # Use a wider window to detect urinalysis context (UA sections are verbose).
            prefix = text[max(0, match.start() - 500):match.start()].lower()

            if "urine" in raw_match or self._is_urinalysis_context(prefix):
                name = "urine_ketones"
            elif "serum" in prefix[:200] or "serum" in raw_match or "acetone" in raw_match:
                name = "serum_ketones"
            else:
                name = "serum_ketones"  # default

            numeric = try_parse_float(raw_val)
            fact = AtomicFact(
                name=name,
                value=numeric if numeric is not None else raw_val.upper().replace(" ", ""),
                unit=None,
                source_span=(match.start(), match.end()),
                raw_match=match.group(0),
            )
            facts.labs.setdefault(name, []).append(fact)

    def _extract_glucose(self, text: str, facts: ExtractedFacts) -> None:
        """Split urine glucose (→ urine_glucose) vs serum/POC glucose (→ glucose_mg_dl)."""
        for match in GLUCOSE_PATTERN.finditer(text):
            prefix = text[max(0, match.start() - 500):match.start()].lower()
            if self._is_urinalysis_context(prefix):
                name = "urine_glucose"
            else:
                name = "glucose_mg_dl"

            raw_val = match.group(1)
            numeric = try_parse_float(raw_val)
            fact = AtomicFact(
                name=name,
                value=numeric if numeric is not None else raw_val,
                unit=None,
                source_span=(match.start(), match.end()),
                raw_match=match.group(0),
            )
            facts.labs.setdefault(name, []).append(fact)

    def _extract_vitals(self, text: str, facts: ExtractedFacts) -> None:
        """Extract vital signs."""
        for field_name, pattern in VITAL_PATTERNS.items():
            if field_name == "bp":
                for match in BP_PATTERN.finditer(text):
                    sys_val = try_parse_float(match.group(1))
                    dia_val = try_parse_float(match.group(2))
                    span = (match.start(), match.end())
                    if sys_val is not None:
                        facts.vitals.setdefault("bp_systolic", []).append(
                            AtomicFact("bp_systolic", sys_val, "mmHg", span, match.group(0))
                        )
                    if dia_val is not None:
                        facts.vitals.setdefault("bp_diastolic", []).append(
                            AtomicFact("bp_diastolic", dia_val, "mmHg", span, match.group(0))
                        )
                continue

            for match in pattern.finditer(text):
                raw_val = match.group(1)
                numeric = try_parse_float(raw_val)
                fact = AtomicFact(
                    name=field_name, value=numeric, unit=None,
                    source_span=(match.start(), match.end()),
                    raw_match=match.group(0),
                )
                facts.vitals.setdefault(field_name, []).append(fact)

    def _extract_clinical_phrases(self, text: str, facts: ExtractedFacts) -> None:
        """Extract clinical phrases."""
        for phrase_name, pattern in CLINICAL_PHRASE_PATTERNS.items():
            for match in pattern.finditer(text):
                fact = AtomicFact(
                    name=phrase_name, value=match.group(0), unit=None,
                    source_span=(match.start(), match.end()),
                    raw_match=match.group(0),
                )
                facts.clinical_phrases.append(fact)

    def _extract_medications(self, text: str, facts: ExtractedFacts) -> None:
        """Extract medications (SGLT2i and other diabetes drugs)."""
        for match in SGLT2I_PATTERN.finditer(text):
            fact = AtomicFact(
                name="SGLT2i", value=match.group(1), unit=None,
                source_span=(match.start(), match.end()),
                raw_match=match.group(0),
            )
            facts.medications.append(fact)

        for match in DIABETES_DRUGS_PATTERN.finditer(text):
            fact = AtomicFact(
                name="diabetes_drug", value=match.group(1), unit=None,
                source_span=(match.start(), match.end()),
                raw_match=match.group(0),
            )
            facts.medications.append(fact)

    @staticmethod
    def _is_urinalysis_context(prefix: str) -> bool:
        """Return True if the prefix context belongs to a urinalysis section.

        Strategy: search the prefix (up to 500 chars) for urinalysis section markers,
        and confirm that no subsequent serum/blood/ABG/VBG/BMP/CMP markers interrupt
        the section.
        """
        # Urinalysis-section markers
        ua_markers = ("urine source", "urinalysis", "ua ", "spec gravity", "urine drug")
        # Blood-section markers (if any of these appear after a UA marker, we have left the UA section)
        blood_markers = (
            "bmp", "cmp", "basic metabolic", "comprehensive metabolic",
            "abg", "vbg", "arterial blood", "venous blood",
            "poc glucose", "serum", "blood gas",
        )

        ua_pos = -1
        for marker in ua_markers:
            pos = prefix.rfind(marker)
            if pos > ua_pos:
                ua_pos = pos

        if ua_pos == -1:
            return False

        # If a blood-section marker appears after the UA marker, we are no longer in the UA section.
        after_ua = prefix[ua_pos:]
        for marker in blood_markers:
            if marker in after_ua:
                return False

        return True
