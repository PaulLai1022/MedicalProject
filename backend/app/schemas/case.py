"""Pydantic schemas for Case resources."""

from pydantic import BaseModel, Field


class CreateCaseReq(BaseModel):
    raw_text: str = Field(..., min_length=20, max_length=50000, alias="rawText")

    model_config = {"populate_by_name": True}


class CaseListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}
