"""Medication and clinical-phrase dictionaries used by the Extractor."""

import re

# SGLT2 inhibitors (brand + generic names)
SGLT2I_DRUGS: list[str] = [
    "Jardiance",
    "Farxiga",
    "Invokana",
    "Steglatro",
    "empagliflozin",
    "dapagliflozin",
    "canagliflozin",
    "ertugliflozin",
]

# Compiled as a single case-insensitive pattern
SGLT2I_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(d) for d in SGLT2I_DRUGS) + r")\b",
    re.IGNORECASE,
)

# Other common diabetes-related medications (used for context, not rule triggers)
DIABETES_DRUGS: list[str] = [
    "metformin",
    "insulin",
    "glipizide",
    "glyburide",
    "sitagliptin",
    "Januvia",
    "liraglutide",
    "Ozempic",
    "semaglutide",
    "Trulicity",
    "dulaglutide",
]

DIABETES_DRUGS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(d) for d in DIABETES_DRUGS) + r")\b",
    re.IGNORECASE,
)
