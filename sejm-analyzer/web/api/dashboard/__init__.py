"""Dashboard API."""

from web.api.dashboard.views import get_overview, get_terms

__all__ = [
    "get_terms",
    "get_overview",
]
