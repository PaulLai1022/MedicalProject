"""LLM output schemas — Plan B strictness: required fields whose values may be empty ("" / []).

Two schema families:
- LLMNarrativeSchema: narrative output from the Composer (Revised HPI, etc.)
- ExtractedFactsSchema: structured facts output from the LLMExtractor
"""

from pydantic import BaseModel, ConfigDict, Field


# ─── Composer output (Revised HPI, etc.) ───────────────────────────────


class SentenceSchema(BaseModel):
    """A single Revised HPI sentence."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    text: str
    sources: list[str]
    reason_clinical: str = Field(alias="reasonClinical")
    reason_guideline: str = Field(alias="reasonGuideline")


class RevisedHPISchema(BaseModel):
    """Revised HPI structure."""

    model_config = ConfigDict(extra="forbid")

    sentences: list[SentenceSchema]


class LLMNarrativeSchema(BaseModel):
    """Full narrative output from the LLM — excludes `disposition`, which is authoritative from the rules engine."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    chief_complaint: str = Field(alias="chiefComplaint")
    hpi_summary: str = Field(alias="hpiSummary")
    key_findings: list[str] = Field(alias="keyFindings")
    suspected_conditions: list[str] = Field(alias="suspectedConditions")
    uncertainties: list[str]
    revised_hpi: RevisedHPISchema = Field(alias="revisedHPI")


# ─── LLMExtractor output (structured facts) ────────────────────────────


class SourceSpan(BaseModel):
    """Character-level span in the original text: [start, end)."""

    model_config = ConfigDict(extra="forbid")

    start: int
    end: int


class LabFact(BaseModel):
    """Lab value (numeric or qualitative)."""

    model_config = ConfigDict(extra="forbid")

    name: str          # e.g. glucose_mg_dl, arterial_ph, serum_ketones
    value: float | str # numeric, or qualitative (LARGE/MODERATE/SMALL/TRACE/NEG/POS)
    unit: str          # e.g. mg/dL, mmol/L, mEq/L; "" for qualitative results
    source_span: SourceSpan


class VitalFact(BaseModel):
    """Vital sign."""

    model_config = ConfigDict(extra="forbid")

    name: str          # e.g. hr, bp_systolic, bp_diastolic, temp_c, spo2, rr
    value: float
    unit: str          # e.g. bpm, mmHg, °C, %
    source_span: SourceSpan


class SymptomFact(BaseModel):
    """A symptom or qualitative clinical finding."""

    model_config = ConfigDict(extra="forbid")

    name: str          # e.g. fever, RLQ_pain, leukocytosis, AMS, Kussmaul_breathing
    description: str   # original wording; "" is allowed
    source_span: SourceSpan


class MedicationFact(BaseModel):
    """Medication."""

    model_config = ConfigDict(extra="forbid")

    name: str
    dose: str          # "" is allowed
    route: str         # "" is allowed (po/IV/SC/...)
    source_span: SourceSpan


class ExtractedFactsSchema(BaseModel):
    """Full structured facts output from the LLMExtractor.

    All fields are required (Plan B); lists / strings may be empty, but omitting
    any field must be a validation error.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    chief_complaint: str
    hpi_summary: str
    suspected_conditions: list[str]
    differential_diagnoses: list[str] = Field(default_factory=list)
    labs: list[LabFact]
    vitals: list[VitalFact]
    symptoms: list[SymptomFact]
    medications: list[MedicationFact]
    imaging_findings: list[str]
    interventions: list[str]
    history: list[str]
