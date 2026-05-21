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
# to tolerate LLM-reported span drift, lab-table line wrapping, and column gaps.
# 80 was too tight for real ER lab tables where label and value can be 150+ chars apart.
_WINDOW_PADDING = 300
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

        # glucose-in-urine guard: if the source_span is inside a urinalysis section,
        # the value is urine glucose, not plasma glucose. Mark failed so the rules
        # engine treats glucose_mg_dl as missing rather than feeding urine glucose
        # into hyperglycemia / HHS thresholds.
        if lab.name == "glucose_mg_dl" and self._is_inside_urinalysis(raw_text, lab.source_span.start):
            return FactVerification(
                fact_kind="lab", fact_name=lab.name, fact_value=lab.value,
                status="failed",
                detail="glucose value located inside a urinalysis section; likely urine glucose, not plasma",
            )

        window = self._window(raw_text, lab.source_span.start, lab.source_span.end)
        result = self._check_numeric_or_qualitative(
            kind="lab", name=lab.name, expected=lab.value,
            window=window, pattern=pattern,
        )
        # Whole-text fallback when the window had no regex hit at all.
        if result.status == "unverifiable" and result.detail == "no regex hit in source window":
            full_result = self._check_numeric_or_qualitative(
                kind="lab", name=lab.name, expected=lab.value,
                window=raw_text, pattern=pattern,
            )
            if full_result.status == "verified":
                return full_result
        return result

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
            result = self._check_temperature(name=vital.name, expected=vital.value, window=window, pattern=pattern)
            if result.status == "unverifiable" and result.detail == "no regex hit in source window":
                full_result = self._check_temperature(
                    name=vital.name, expected=vital.value, window=raw_text, pattern=pattern,
                )
                if full_result.status == "verified":
                    return full_result
            return result

        result = self._check_numeric_or_qualitative(
            kind="vital", name=vital.name, expected=vital.value,
            window=window, pattern=pattern,
        )
        if result.status == "unverifiable" and result.detail == "no regex hit in source window":
            full_result = self._check_numeric_or_qualitative(
                kind="vital", name=vital.name, expected=vital.value,
                window=raw_text, pattern=pattern,
            )
            if full_result.status == "verified":
                return full_result
        return result

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

    @staticmethod
    def _is_inside_urinalysis(raw_text: str, pos: int) -> bool:
        """Return True if `pos` falls inside a urinalysis section.

        Strategy: scan the 600 chars *before* pos for UA markers; if a UA marker is
        the closest preceding section header (i.e. no blood/BMP/CMP marker appears
        between the UA marker and `pos`), we are still inside the UA section.
        Mirrors `Extractor._is_urinalysis_context` from extractor.py so both paths
        agree on what counts as "urine".
        """
        if pos <= 0 or pos > len(raw_text):
            return False
        prefix = raw_text[max(0, pos - 600):pos].lower()
        ua_markers = (
            "urine source", "urinalysis", "ua ",
            "spec gravity", "urine drug", "color:", "clarity:",
        )
        blood_markers = (
            "bmp", "cmp", "basic metabolic", "comprehensive metabolic",
            "abg", "vbg", "arterial blood", "venous blood",
            "poc glucose", "blood sugar", "serum", "blood gas",
        )
        ua_pos = -1
        for marker in ua_markers:
            p = prefix.rfind(marker)
            if p > ua_pos:
                ua_pos = p
        if ua_pos == -1:
            return False
        after_ua = prefix[ua_pos:]
        return not any(marker in after_ua for marker in blood_markers)


def _numbers_close(a: float, b: float) -> bool:
    """Approximate equality using relative tolerance only.

    We deliberately avoid abs_tol: field magnitudes vary enormously (pH ~7 vs
    glucose ~400), and a fixed abs_tol would be too loose on small values and
    too strict on large ones. rel_tol=2% is reasonable at both ends.
    """
    return math.isclose(a, b, rel_tol=_NUMERIC_REL_TOL, abs_tol=0.0)
