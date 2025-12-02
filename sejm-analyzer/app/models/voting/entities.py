"""Voting domain entities - computed analytics results."""

from dataclasses import dataclass

from app.models.common import BaseEntity


@dataclass
class PowerIndex(BaseEntity):
    """Voting power index for a party."""

    party: str
    seats: int
    seats_pct: float
    shapley: float
    banzhaf: float


@dataclass
class Cohesion(BaseEntity):
    """Party voting cohesion metrics."""

    party: str
    rice_index: float
    votings: int
