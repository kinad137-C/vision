"""Voting API response schemas."""

from pydantic import BaseModel


class PowerIndexItem(BaseModel):
    """Power index for a party."""

    party: str
    seats: int
    seats_pct: float
    shapley: float
    banzhaf: float


class PowerIndicesResponse(BaseModel):
    """Power indices response."""

    term_id: int
    items: list[PowerIndexItem]
    total_seats: int


class CohesionItem(BaseModel):
    """Cohesion for a party."""

    party: str
    rice_index: float
    votings: int


class CohesionResponse(BaseModel):
    """Cohesion response."""

    term_id: int
    items: list[CohesionItem]


class MarkovItem(BaseModel):
    """Markov stats for a party."""

    party: str
    momentum: float
    volatility: float


class MarkovResponse(BaseModel):
    """Markov response."""

    term_id: int
    items: list[MarkovItem]


class CoalitionItem(BaseModel):
    """Winning coalition."""

    parties: list[str]
    seats: int
    surplus: int


class CoalitionsResponse(BaseModel):
    """Coalitions response."""

    term_id: int
    quota: int
    items: list[CoalitionItem]


class AgreementMatrixResponse(BaseModel):
    """Agreement matrix response."""

    term_id: int
    parties: list[str]
    matrix: dict[str, dict[str, float]]
