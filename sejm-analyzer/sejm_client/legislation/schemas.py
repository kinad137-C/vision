"""Legislation API schemas - processes, prints."""

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    """Document type enum."""

    BILL = "BILL"
    DRAFT_RESOLUTION = "DRAFT_RESOLUTION"
    OTHER = "OTHER"
    CONSTITUTIONAL_TRIBUNAL_RULING = "CONSTITUTIONAL_TRIBUNAL_RULING"


class ProcessStageSchema(BaseModel):
    """Stage in legislative process."""

    stage_name: str = Field(alias="stageName")
    date: Optional[date] = None
    stage_type: Optional[str] = Field(alias="stageType", default=None)
    sitting_num: Optional[int] = Field(alias="sittingNum", default=None)
    decision: Optional[str] = None
    committee_code: Optional[str] = Field(alias="committeeCode", default=None)
    children: list["ProcessStageSchema"] = []

    class Config:
        populate_by_name = True


class ProcessHeaderSchema(BaseModel):
    """Legislative process header (list view)."""

    term: int
    number: str
    title: str
    document_type: Optional[str] = Field(alias="documentType", default=None)
    document_type_enum: Optional[DocumentType] = Field(alias="documentTypeEnum", default=None)
    passed: Optional[bool] = None
    process_start_date: Optional[date] = Field(alias="processStartDate", default=None)
    closure_date: Optional[date] = Field(alias="closureDate", default=None)
    change_date: Optional[datetime] = Field(alias="changeDate", default=None)
    description: Optional[str] = None
    comments: Optional[str] = None

    class Config:
        populate_by_name = True


class ProcessDetailsSchema(ProcessHeaderSchema):
    """Full legislative process details."""

    stages: list[ProcessStageSchema] = []
    title_final: Optional[str] = Field(alias="titleFinal", default=None)
    prints_considered_jointly: Optional[list[str]] = Field(alias="printsConsideredJointly", default=None)

    class Config:
        populate_by_name = True


class PrintSchema(BaseModel):
    """Sejm print (druk sejmowy)."""

    term: int
    number: str
    title: str
    document_date: Optional[date] = Field(alias="documentDate", default=None)
    delivery_date: Optional[date] = Field(alias="deliveryDate", default=None)
    change_date: Optional[datetime] = Field(alias="changeDate", default=None)
    process_print: Optional[list[str]] = Field(alias="processPrint", default=None)
    attachments: list[str] = []

    class Config:
        populate_by_name = True
