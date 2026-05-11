"""Regex pattern definitions — extract atomic facts from clinical notes.

Each pattern returns (field_name, compiled_regex). The first capture group holds
the numeric or qualitative result.
"""

import re

# ---------- Labs ----------

PH_PATTERN = re.compile(
    r"\b(?:A\.?\s*pH|V\.?\s*pH|ApH|VpH|arterial\s+pH|venous\s+pH|pH)\b"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=]?\s*"
    r"(\d\.\d{1,3})",
    re.IGNORECASE,
)

BICARBONATE_PATTERN = re.compile(
    r"\b(?:AHCO3|VHCO3|V\s+HCO3|A\s+HCO3|HCO3|bicarbonate|bicarb|CO2\s*\(bicarb\))\b"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=<>]?\s*"
    r"(\d+\.?\d*)",
    re.IGNORECASE,
)

GLUCOSE_PATTERN = re.compile(
    r"\b(?:glucose|glu|POC\s+GLUCOSE|blood\s+sugar|BS)\b"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=]?\s*"
    r"(?:[<>]=?\s*)?"
    r"(\d+\.?\d*)",
    re.IGNORECASE,
)

KETONES_PATTERN = re.compile(
    r"\b(?:ketones?|serum\s+ketones?|urine\s+ketones?|acetone|serum\s+acetone|urine\s+acetone)\b"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=]?\s*"
    r"(LARGE|MODERATE|SMALL|TRACE|NEG(?:ATIVE)?|POS(?:ITIVE)?|(?:[<>]=?\s*)?\d+\.?\d*)",
    re.IGNORECASE,
)

WBC_PATTERN = re.compile(
    r"\b(?:WBC|white\s+blood\s+cell(?:s)?|leukocytes?)"
    r"\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

CREATININE_PATTERN = re.compile(
    r"(?<!BUN/)\b(?:creatinine|CREAT)\b\.?"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=]?\s*"
    r"(\d+\.?\d*)",
    re.IGNORECASE,
)

BUN_PATTERN = re.compile(
    r"\b(?:BUN|blood\s+urea\s+nitrogen)"
    r"\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

SODIUM_PATTERN = re.compile(
    r"\b(?:Na|sodium)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

POTASSIUM_PATTERN = re.compile(
    r"\b(?:K|potassium)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

CHLORIDE_PATTERN = re.compile(
    r"\b(?:Cl|chloride)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

CO2_PATTERN = re.compile(
    r"\b(?:CO2|carbon\s+dioxide)\b"
    r"(?:\s*\([^)]*\))*"
    r"\s*[:=]?\s*"
    r"(\d+\.?\d*)",
    re.IGNORECASE,
)

ANION_GAP_PATTERN = re.compile(
    r"\b(?:anion\s+gap|AG)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

LACTATE_PATTERN = re.compile(
    r"\b(?:lactate|lactic\s+acid)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

TROPONIN_PATTERN = re.compile(
    r"\b(?:troponin|trop(?:\s*I|\s*T)?)\s*[:=]?\s*([<>]?\s*\d+\.?\d*)",
    re.IGNORECASE,
)

HEMOGLOBIN_PATTERN = re.compile(
    r"\b(?:Hgb|Hb|hemoglobin)\s*[:=]?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

GFR_PATTERN = re.compile(
    r"\b(?:GFR|eGFR|glomerular\s+filtration)\s*[:=]?\s*([<>]?\s*\d+\.?\d*)",
    re.IGNORECASE,
)

# ---------- Vitals ----------

HR_PATTERN = re.compile(
    r"\b(?:HR|heart\s+rate|pulse)\s*[:=]?\s*(\d+)",
    re.IGNORECASE,
)

RR_PATTERN = re.compile(
    r"\b(?:RR|resp(?:iratory)?\s*rate|respirations?)\s*[:=]?\s*(\d+)",
    re.IGNORECASE,
)

TEMP_PATTERN = re.compile(
    r"\b(?:Temp|temperature)\b(?:\s*\([^)]*\))?\s*[:=]?\s*(\d+\.?\d*)\s*(?:°?\s*[CF])?",
    re.IGNORECASE,
)

BP_PATTERN = re.compile(
    r"\b(?:BP|blood\s+pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})",
    re.IGNORECASE,
)

SPO2_PATTERN = re.compile(
    r"\b(?:SpO2|O2\s*sat|oxygen\s+sat(?:uration)?|sat)\s*[:=]?\s*(\d+)\s*%?",
    re.IGNORECASE,
)

# ---------- Clinical Phrases ----------

AMS_PATTERN = re.compile(
    r"\b(?:altered\s+mental\s+status|AMS|not\s+alert|not\s+oriented"
    r"|responds?\s+to\s+(?:painful\s+)?stimuli|confused|obtunded|lethargic)\b",
    re.IGNORECASE,
)

KUSSMAUL_PATTERN = re.compile(
    r"\b(?:Kussmaul(?:\s+breathing|\s+respirations?)?|deep\s+labored\s+breathing)\b",
    re.IGNORECASE,
)

DKA_PHRASE_PATTERN = re.compile(
    r"\b(?:DKA|diabetic\s+ketoacidosis)\b",
    re.IGNORECASE,
)

HHS_PHRASE_PATTERN = re.compile(
    r"\b(?:HHS|hyperosmolar\s+hyperglycemic\s+(?:state|syndrome))\b",
    re.IGNORECASE,
)

EUGLYCEMIC_DKA_PATTERN = re.compile(
    r"\b(?:euglycemic\s+DKA|euDKA|normoglycemic\s+DKA)\b",
    re.IGNORECASE,
)

AKI_PATTERN = re.compile(
    r"\b(?:AKI|acute\s+kidney\s+injury|acute\s+renal\s+failure)\b",
    re.IGNORECASE,
)

DEHYDRATION_PATTERN = re.compile(
    r"\b(?:dehydrat(?:ion|ed)|volume\s+depletion|hypovolemia)\b",
    re.IGNORECASE,
)

INFECTION_PATTERN = re.compile(
    r"\b(?:infection|sepsis|septic|infected|UTI|pneumonia|cellulitis)\b",
    re.IGNORECASE,
)

# ---------- Aggregates ----------

LAB_PATTERNS: dict[str, re.Pattern] = {
    "arterial_ph": PH_PATTERN,
    "venous_ph": PH_PATTERN,
    "bicarbonate": BICARBONATE_PATTERN,
    "glucose_mg_dl": GLUCOSE_PATTERN,
    "serum_ketones": KETONES_PATTERN,
    "urine_ketones": KETONES_PATTERN,
    "wbc": WBC_PATTERN,
    "creatinine": CREATININE_PATTERN,
    "bun": BUN_PATTERN,
    "sodium": SODIUM_PATTERN,
    "potassium": POTASSIUM_PATTERN,
    "chloride": CHLORIDE_PATTERN,
    "co2": CO2_PATTERN,
    "anion_gap": ANION_GAP_PATTERN,
    "lactate": LACTATE_PATTERN,
    "troponin": TROPONIN_PATTERN,
    "hemoglobin": HEMOGLOBIN_PATTERN,
    "gfr": GFR_PATTERN,
}

VITAL_PATTERNS: dict[str, re.Pattern] = {
    "hr": HR_PATTERN,
    "rr": RR_PATTERN,
    "temp_c": TEMP_PATTERN,
    "bp": BP_PATTERN,
    "spo2": SPO2_PATTERN,
}

CLINICAL_PHRASE_PATTERNS: dict[str, re.Pattern] = {
    "AMS": AMS_PATTERN,
    "Kussmaul": KUSSMAUL_PATTERN,
    "DKA": DKA_PHRASE_PATTERN,
    "HHS": HHS_PHRASE_PATTERN,
    "euglycemic_DKA": EUGLYCEMIC_DKA_PATTERN,
    "AKI": AKI_PATTERN,
    "dehydration": DEHYDRATION_PATTERN,
    "infection": INFECTION_PATTERN,
}
