"""Core API schemas - terms, MPs, clubs, proceedings."""

from datetime import date

from pydantic import BaseModel, Field


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
