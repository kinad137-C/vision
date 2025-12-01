"""Pydantic schemas for Sejm API responses."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class VoteValue(StrEnum):
    YES = "YES"
    NO = "NO"
    ABSTAIN = "ABSTAIN"
    ABSENT = "ABSENT"
    NO_VOTE = "NO_VOTE"
    PRESENT = "PRESENT"
    VOTE_VALID = "VOTE_VALID"
    VOTE_INVALID = "VOTE_INVALID"


class DocumentType(StrEnum):
    BILL = "BILL"
    DRAFT_RESOLUTION = "DRAFT_RESOLUTION"
    OTHER = "OTHER"
    CONSTITUTIONAL_TRIBUNAL_RULING = "CONSTITUTIONAL_TRIBUNAL_RULING"


class TermSchema(BaseModel):
    """Sejm term (kadencja)."""

    num: int
    from_date: date = Field(alias="from")
    to_date: date | None = Field(alias="to", default=None)
    current: bool = False

    class Config:
        populate_by_name = True


class ClubSchema(BaseModel):
    """Parliamentary club (klub/koło)."""

    id: str
    name: str
    phone: str | None = None
    fax: str | None = None
    email: str | None = None
    members_count: int = Field(alias="membersCount", default=0)

    class Config:
        populate_by_name = True


class MPSchema(BaseModel):
    """Member of Parliament (poseł)."""

    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    club: str | None = None
    district_name: str | None = Field(alias="districtName", default=None)
    active: bool = True
    birth_date: date | None = Field(alias="birthDate", default=None)
    education_level: str | None = Field(alias="educationLevel", default=None)
    profession: str | None = None
    voivodeship: str | None = None

    class Config:
        populate_by_name = True


class ProceedingSchema(BaseModel):
    """Sejm sitting/proceeding (posiedzenie)."""

    number: int
    title: str = ""
    dates: list[str] = []


class VotingSchema(BaseModel):
    """Voting summary (głosowanie)."""

    term: int
    sitting: int
    voting_number: int = Field(alias="votingNumber")
    date: datetime
    title: str
    topic: str | None = None
    description: str | None = None
    yes: int = 0
    no: int = 0
    abstain: int = 0
    not_participating: int = Field(alias="notParticipating", default=0)

    class Config:
        populate_by_name = True


class VoteSchema(BaseModel):
    """Individual MP vote."""

    mp_id: int = Field(alias="MP")
    club: str | None = None
    vote: str

    class Config:
        populate_by_name = True


class VotingDetailsSchema(VotingSchema):
    """Voting with individual votes."""

    votes: list[VoteSchema] = []


# ========== PROCESSES (законопроекты) ==========


class ProcessStageSchema(BaseModel):
    """Stage in legislative process."""

    stage_name: str = Field(alias="stageName")
    date: date | None = None
    stage_type: str | None = Field(alias="stageType", default=None)
    # For voting stages
    sitting_num: int | None = Field(alias="sittingNum", default=None)
    decision: str | None = None
    # For committee stages
    committee_code: str | None = Field(alias="committeeCode", default=None)
    # Nested stages
    children: list["ProcessStageSchema"] = []

    class Config:
        populate_by_name = True


class ProcessHeaderSchema(BaseModel):
    """Legislative process header (list view)."""

    term: int
    number: str
    title: str
    document_type: str | None = Field(alias="documentType", default=None)
    document_type_enum: DocumentType | None = Field(alias="documentTypeEnum", default=None)
    passed: bool | None = None
    process_start_date: date | None = Field(alias="processStartDate", default=None)
    closure_date: date | None = Field(alias="closureDate", default=None)
    change_date: datetime | None = Field(alias="changeDate", default=None)
    description: str | None = None
    comments: str | None = None

    class Config:
        populate_by_name = True


class ProcessDetailsSchema(ProcessHeaderSchema):
    """Full legislative process details."""

    stages: list[ProcessStageSchema] = []
    title_final: str | None = Field(alias="titleFinal", default=None)
    prints_considered_jointly: list[str] | None = Field(alias="printsConsideredJointly", default=None)

    class Config:
        populate_by_name = True


# ========== PRINTS (druki sejmowe) ==========


class PrintSchema(BaseModel):
    """Sejm print (druk sejmowy)."""

    term: int
    number: str
    title: str
    document_date: date | None = Field(alias="documentDate", default=None)
    delivery_date: date | None = Field(alias="deliveryDate", default=None)
    change_date: datetime | None = Field(alias="changeDate", default=None)
    process_print: list[str] | None = Field(alias="processPrint", default=None)
    attachments: list[str] = []

    class Config:
        populate_by_name = True


# Forward ref for nested stages
ProcessStageSchema.model_rebuild()
