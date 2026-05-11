"""Pydantic schemas for the structured result — used by PATCH requests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScalarPatch(BaseModel):
    user_value: str | None = Field(default=None, alias="userValue")
    model_config = {"populate_by_name": True}


class JsonArrayPatch(BaseModel):
    user_value: list[str] | None = Field(default=None, alias="userValue")
    model_config = {"populate_by_name": True}


class SentencePatch(BaseModel):
    id: str | None = None
    user_text: str | None = Field(default=None, alias="userText")
    sources: list[str] | None = None
    reason_clinical: str | None = Field(default=None, alias="reasonClinical")
    reason_guideline: str | None = Field(default=None, alias="reasonGuideline")
    sort_order: int | None = Field(default=None, alias="sortOrder")
    model_config = {"populate_by_name": True}


class RevisedHPIPatch(BaseModel):
    sentences: list[SentencePatch] | None = None
    deleted_sentence_ids: list[str] | None = Field(default=None, alias="deletedSentenceIds")
    model_config = {"populate_by_name": True}


class StructuredPatch(BaseModel):
    chief_complaint: ScalarPatch | None = Field(default=None, alias="chiefComplaint")
    hpi_summary: ScalarPatch | None = Field(default=None, alias="hpiSummary")
    disposition: ScalarPatch | None = None
    key_findings: JsonArrayPatch | None = Field(default=None, alias="keyFindings")
    suspected_conditions: JsonArrayPatch | None = Field(default=None, alias="suspectedConditions")
    uncertainties: JsonArrayPatch | None = None
    revised_hpi: RevisedHPIPatch | None = Field(default=None, alias="revisedHPI")
    model_config = {"populate_by_name": True}


class PatchCaseReq(BaseModel):
    structured: StructuredPatch
