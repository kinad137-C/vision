"""Voting API schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class VoteValue(StrEnum):
    """Possible vote values."""

    YES = "YES"
    NO = "NO"
    ABSTAIN = "ABSTAIN"
    ABSENT = "ABSENT"
    NO_VOTE = "NO_VOTE"
    PRESENT = "PRESENT"
    VOTE_VALID = "VOTE_VALID"
    VOTE_INVALID = "VOTE_INVALID"


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
