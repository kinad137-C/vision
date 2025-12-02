"""Legislation API."""

from web.api.legislation.views import get_process_stats, get_topic_stats

__all__ = [
    "get_topic_stats",
    "get_process_stats",
]
