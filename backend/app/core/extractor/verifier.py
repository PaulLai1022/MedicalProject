"""RegexVerifier — cross-check LLM-extracted facts against the raw text (hallucination guard).

Strategy:
- For each numeric lab/vital, re-run the corresponding regex within a window around
  `source_span` reported by the LLM.
- Three possible outcomes:
  - verified: the regex finds a matching value near the span
  - failed: the regex finds a different value near the span (LLM may have hallucinated)
  - unverifiable: no regex pattern hits the window (the LLM captured a semantic fact
    that cannot be machine-verified)
- The verifier does NOT extract new facts; it only verifies. The rules engine treats
  any fact with status "failed" as if it were missing.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.core.extractor.normalizers import try_parse_float
from app.core.extractor.patterns import LAB_PATTERNS, VITAL_PATTERNS, BP_PATTERN
from app.core.llm.schema import ExtractedFactsSchema, LabFact, VitalFact

logger = logging.getLogger(__name__)


# Verification window: expand N characters around the reported source_span
# to tolerate small span reporting drift from the LLM.
_WINDOW_PADDING = 80
# Numeric tolerance (relative), accounting for float rounding and unit-conversion drift.
_NUMERIC_REL_TOL = 0.02


@dataclass(frozen=True)
class FactVerification:
    """Verification result for a single fact."""

    fact_kind: str          # "lab" | "vital"
    fact_name: str
    fact_value: float | str
    status: str             # "verified" | "failed" | "unverifiable"
    detail: str             # Diagnostic message on failure / unverifiable


@dataclass
class VerifiedFacts:
    """LLM-extracted facts plus verification records.

    Holds an immutable reference to the original schema and an index of verification
    outcomes. The rules engine uses `labs_for_engine()` / `vitals_for_engine()` to
    skip any fact whose status is "failed".
    """

    facts: ExtractedFactsSchema
    verifications: list[FactVerification]

    def labs_for_engine(self) -> list[LabFact]:
        """Return labs that are not "failed" (both verified and unverifiable are allowed)."""
        failed_keys = {
            (v.fact_name, v.fact_value)
            for v in self.verifications
            if v.fact_kind == "lab" and v.status == "failed"
        }
        return [
            lab for lab in self.facts.labs
            if (lab.name, lab.value) not in failed_keys
        ]

    def vitals_for_engine(self) -> list[VitalFact]:
        failed_keys = {
            (v.fact_name, v.fact_value)
            for v in self.verifications
            if v.fact_kind == "vital" and v.status == "failed"
        }
        return [
            vital for vital in self.facts.vitals
            if (vital.name, vital.value) not in failed_keys
        ]

    def warnings(self) -> list[str]:
        """Return warning strings for GenerationService to record in structured.warnings."""
        out: list[str] = []
        for v in self.verifications:
            if v.status == "failed":
                out.append(
                    f"verification_failed: {v.fact_kind}.{v.fact_name}={v.fact_value} ({v.detail})"
                )
        return out


class RegexVerifier:
    """Cross-check LLM-extracted facts using regex matches."""

    def verify(self, raw_text: str, facts: ExtractedFactsSchema) -> VerifiedFacts:
        verifications: list[FactVerification] = []

        for lab in facts.labs:
            verifications.append(self._verify_lab(raw_text, lab))

        for vital in facts.vitals:
            verifications.append(self._verify_vital(raw_text, vital))

        return VerifiedFacts(facts=facts, verifications=verifications)

    # ─── lab verification ───────────────────────────────────────────

    def _verify_lab(self, raw_text: str, lab: LabFact) -> FactVerification:
        pattern = LAB_PATTERNS.get(lab.name)
        if not pattern:
            return FactVerification(
                fact_kind="lab", fact_name=lab.name, fact_value=lab.value,
                status="unverifiable",
                detail=f"no regex pattern for lab '{lab.name}'",
            )

        window = self._window(raw_text, lab.source_span.start, lab.source_span.end)
        return self._check_numeric_or_qualitative(
            kind="lab", name=lab.name, expected=lab.value,
            window=window, pattern=pattern,
        )

    # ─── vital verification ─────────────────────────────────────────

    def _verify_vital(self, raw_text: str, vital: VitalFact) -> FactVerification:
        if vital.name in ("bp_systolic", "bp_diastolic"):
            return self._verify_bp(raw_text, vital)

        pattern = VITAL_PATTERNS.get(vital.name)
        if not pattern:
            return FactVerification(
                fact_kind="vital", fact_name=vital.name, fact_value=vital.value,
                status="unverifiable",
                detail=f"no regex pattern for vital '{vital.name}'",
            )

        window = self._window(raw_text, vital.source_span.start, vital.source_span.end)

        # temp_c special-case: the LLM typically normalizes Fahrenheit to Celsius,
        # while the raw text often says "Temp: 98 F". Normalize the regex-captured
        # value via `normalize_temperature` before comparing.
        if vital.name == "temp_c":
            return self._check_temperature(name=vital.name, expected=vital.value, window=window, pattern=pattern)

        return self._check_numeric_or_qualitative(
            kind="vital", name=vital.name, expected=vital.value,
            window=window, pattern=pattern,
        )

    def _check_temperature(
        self, *, name: str, expected: float | str, window: str, pattern,
    ) -> FactVerification:
        """Temperature-specific check: tolerate °F → °C conversion."""
        from app.core.extractor.normalizers import normalize_temperature

        matches = list(pattern.finditer(window))
        if not matches:
            return FactVerification(
                fact_kind="vital", fact_name=name, fact_value=expected,
                status="unverifiable",
                detail="no regex hit in source window",
            )
        if not isinstance(expected, (int, float)):
            return FactVerification(
                fact_kind="vital", fact_name=name, fact_value=expected,
                status="unverifiable",
                detail="non-numeric expected value for temperature",
            )

        for match in matches:
            regex_val = try_parse_float(match.group(1))
            if regex_val is None:
                continue
            unit_hint = match.group(0)  # full match, may contain "F" / "C"
            normalized, _ = normalize_temperature(regex_val, unit_hint=unit_hint)
            if _numbers_close(normalized, float(expected)):
                return FactVerification(
                    fact_kind="vital", fact_name=name, fact_value=expected,
                    status="verified",
                    detail=f"matched '{match.group(0)}' -> {normalized}°C",
                )

        sample = matches[0].group(0)
        return FactVerification(
            fact_kind="vital", fact_name=name, fact_value=expected,
            status="failed",
            detail=f"regex found '{sample}' but LLM said {expected}°C",
        )

    def _verify_bp(self, raw_text: str, vital: VitalFact) -> FactVerification:
        """For bp_systolic / bp_diastolic, pull the right side out of the systolic/diastolic pair."""
        window = self._window(raw_text, vital.source_span.start, vital.source_span.end)
        for match in BP_PATTERN.finditer(window):
            sys_v = try_parse_float(match.group(1))
            dia_v = try_parse_float(match.group(2))
            target = sys_v if vital.name == "bp_systolic" else dia_v
            if target is None:
                continue
            if _numbers_close(target, vital.value):
                return FactVerification(
                    fact_kind="vital", fact_name=vital.name, fact_value=vital.value,
                    status="verified",
                    detail=f"matched '{match.group(0)}' -> {target}",
                )
        return FactVerification(
            fact_kind="vital", fact_name=vital.name, fact_value=vital.value,
            status="unverifiable",
            detail="no BP pattern hit in source window",
        )

    # ─── common checker ─────────────────────────────────────────────

    def _check_numeric_or_qualitative(
        self, *, kind: str, name: str, expected: float | str,
        window: str, pattern,
    ) -> FactVerification:
        matches = list(pattern.finditer(window))
        if not matches:
            return FactVerification(
                fact_kind=kind, fact_name=name, fact_value=expected,
                status="unverifiable",
                detail="no regex hit in source window",
            )

        # Numeric expected
        if isinstance(expected, (int, float)):
            for match in matches:
                regex_val = try_parse_float(match.group(1))
                if regex_val is None:
                    continue
                if _numbers_close(regex_val, float(expected)):
                    return FactVerification(
                        fact_kind=kind, fact_name=name, fact_value=expected,
                        status="verified",
                        detail=f"matched '{match.group(0)}' -> {regex_val}",
                    )
            # No matching value found but other numbers are present → failed
            sample = matches[0].group(0)
            return FactVerification(
                fact_kind=kind, fact_name=name, fact_value=expected,
                status="failed",
                detail=f"regex found '{sample}' but LLM said {expected}",
            )

        # String expected (qualitative lab, e.g. LARGE/MODERATE)
        target_norm = str(expected).upper().strip()
        for match in matches:
            regex_val = match.group(1).upper().strip()
            if regex_val == target_norm:
                return FactVerification(
                    fact_kind=kind, fact_name=name, fact_value=expected,
                    status="verified",
                    detail=f"matched qualitative '{regex_val}'",
                )
        sample = matches[0].group(1)
        return FactVerification(
            fact_kind=kind, fact_name=name, fact_value=expected,
            status="failed",
            detail=f"regex found '{sample}' but LLM said '{expected}'",
        )

    @staticmethod
    def _window(raw_text: str, start: int, end: int) -> str:
        """Build a window around `source_span`, tolerating small LLM-reported drift."""
        if start < 0 or end < 0 or end <= start or end > len(raw_text):
            # Untrusted span → fall back to whole-text verification.
            return raw_text
        lo = max(0, start - _WINDOW_PADDING)
        hi = min(len(raw_text), end + _WINDOW_PADDING)
        return raw_text[lo:hi]


def _numbers_close(a: float, b: float) -> bool:
    """Approximate equality using relative tolerance only.

    We deliberately avoid abs_tol: field magnitudes vary enormously (pH ~7 vs
    glucose ~400), and a fixed abs_tol would be too loose on small values and
    too strict on large ones. rel_tol=2% is reasonable at both ends.
    """
    return math.isclose(a, b, rel_tol=_NUMERIC_REL_TOL, abs_tol=0.0)
