"""Unit normalization — convert non-standard units to canonical ones."""

import re

# Glucose: mmol/L → mg/dL (multiply by 18.018)
_GLUCOSE_MMOL_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*(?:mmol/?L|mmol)", re.IGNORECASE
)

# Temperature: °F → °C
_TEMP_F_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*°?\s*F\b", re.IGNORECASE
)


def normalize_glucose(value: float, unit_hint: str | None = None) -> tuple[float, str]:
    """Normalize a glucose value to mg/dL.

    If `unit_hint` contains "mmol", convert; otherwise assume the value is already mg/dL.
    Returns (normalized_value, unit).
    """
    if unit_hint and re.search(r"mmol", unit_hint, re.IGNORECASE):
        return round(value * 18.018, 1), "mg/dL"
    # Heuristic: a value < 50 with no unit hint is likely mmol/L.
    if unit_hint is None and value < 33.3:
        return round(value * 18.018, 1), "mg/dL (converted from mmol/L)"
    return value, "mg/dL"


def normalize_temperature(value: float, unit_hint: str | None = None) -> tuple[float, str]:
    """Normalize a temperature value to °C.

    If `unit_hint` contains "F", or the value is > 45, treat it as Fahrenheit and convert.
    """
    if unit_hint and re.search(r"F", unit_hint, re.IGNORECASE):
        return round((value - 32) * 5 / 9, 1), "°C"
    # Heuristic: a body temperature > 45 is almost certainly Fahrenheit.
    if value > 45:
        return round((value - 32) * 5 / 9, 1), "°C"
    return value, "°C"


def try_parse_float(raw: str) -> float | None:
    """Try to parse a string as a float; return None on failure."""
    cleaned = re.sub(r"[<>≤≥]", "", raw).strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None
