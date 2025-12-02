"""Dashboard API views - thin layer over services."""

from app.container import container
from web.api.errors import validate_term_id

from .schemas import OverviewResponse, TermItem, TermsResponse


def get_terms() -> TermsResponse:
    """Get available terms."""
    data = container.dashboard.get_terms()

    items = [
        TermItem(
            id=t["id"],
            has_voting_data=t["has_voting_data"],
            has_processes=t["has_processes"],
        )
        for t in data["items"]
    ]

    return TermsResponse(items=items, current=data["current"])


def get_overview(term_id: int) -> OverviewResponse:
    """Get dashboard overview for a term."""
    validate_term_id(term_id)
    data = container.dashboard.get_overview(term_id)

    return OverviewResponse(
        term_id=data["term_id"],
        parties_count=data["parties_count"],
        total_seats=data["total_seats"],
        votings_count=data["votings_count"],
        processes_count=data["processes_count"],
        pass_rate=data["pass_rate"],
    )
