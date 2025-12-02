"""Dashboard API response schemas."""

from pydantic import BaseModel


class TermItem(BaseModel):
    """Term info."""

    id: int
    has_voting_data: bool
    has_processes: bool


class TermsResponse(BaseModel):
    """Available terms response."""

    items: list[TermItem]
    current: int | None


class OverviewResponse(BaseModel):
    """Dashboard overview response."""

    term_id: int
    parties_count: int
    total_seats: int
    votings_count: int
    processes_count: int
    pass_rate: float | None
