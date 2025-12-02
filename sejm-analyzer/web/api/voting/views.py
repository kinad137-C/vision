"""Voting API views - thin layer over services."""

from app.container import container
from web.api.errors import validate_term_id

from .schemas import (
    AgreementMatrixResponse,
    CoalitionItem,
    CoalitionsResponse,
    CohesionItem,
    CohesionResponse,
    MarkovItem,
    MarkovResponse,
    PowerIndexItem,
    PowerIndicesResponse,
)


def get_power_indices(term_id: int) -> PowerIndicesResponse:
    """Get power indices for all parties."""
    validate_term_id(term_id)
    data = container.voting_analytics.power_indices(term_id)

    items = [
        PowerIndexItem(
            party=p.party,
            seats=p.seats,
            seats_pct=p.seats_pct,
            shapley=p.shapley,
            banzhaf=p.banzhaf,
        )
        for p in data
    ]

    return PowerIndicesResponse(
        term_id=term_id,
        items=items,
        total_seats=sum(p.seats for p in data),
    )


def get_cohesion(term_id: int) -> CohesionResponse:
    """Get cohesion (Rice index) for all parties."""
    validate_term_id(term_id)
    data = container.voting_analytics.cohesion(term_id)

    items = [
        CohesionItem(
            party=p.party,
            rice_index=p.rice_index,
            votings=p.votings,
        )
        for p in data
    ]

    return CohesionResponse(term_id=term_id, items=items)


def get_markov(term_id: int) -> MarkovResponse:
    """Get Markov transition stats for all parties."""
    validate_term_id(term_id)
    data = container.voting_analytics.markov(term_id)

    items = [
        MarkovItem(
            party=d["party"],
            momentum=d["momentum"],
            volatility=d["volatility"],
        )
        for d in data
    ]

    return MarkovResponse(term_id=term_id, items=items)


def get_coalitions(term_id: int) -> CoalitionsResponse:
    """Get minimum winning coalitions."""
    validate_term_id(term_id)
    data = container.voting_analytics.coalitions(term_id)

    # Get quota from power indices calculation
    power = container.voting_analytics.power_indices(term_id)
    total_seats = sum(p.seats for p in power)
    quota = total_seats // 2 + 1

    items = [
        CoalitionItem(
            parties=d["parties"],
            seats=d["seats"],
            surplus=d["surplus"],
        )
        for d in data
    ]

    return CoalitionsResponse(term_id=term_id, quota=quota, items=items)


def get_agreement_matrix(term_id: int) -> AgreementMatrixResponse:
    """Get pairwise party agreement rates."""
    validate_term_id(term_id)
    data = container.voting_analytics.agreement_matrix(term_id)

    parties = list(data.keys())

    return AgreementMatrixResponse(
        term_id=term_id,
        parties=parties,
        matrix=data,
    )
