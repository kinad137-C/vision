"""Legislation API views - thin layer over services."""

from app.container import container
from web.api.errors import validate_term_id

from .schemas import (
    ByTypeItem,
    ProcessStatsResponse,
    TopicClusterItem,
    TopicStatsResponse,
)


def get_topic_stats(term_id: int) -> TopicStatsResponse:
    """Get topic statistics for legislative processes."""
    validate_term_id(term_id)
    data = container.topic_modeling.get_topic_stats(term_id)

    clusters = [
        TopicClusterItem(
            name=c["name"],
            count=c["count"],
            pass_rate=c["pass_rate"],
            keywords=c["keywords"],
        )
        for c in data["clusters"]
    ]

    return TopicStatsResponse(
        term_id=term_id,
        total_topics=data["total_topics"],
        clusters=clusters,
    )


def get_process_stats(term_id: int) -> ProcessStatsResponse:
    """Get process statistics."""
    validate_term_id(term_id)
    data = container.legislation_analytics.repo.get_process_stats(term_id)

    by_type = [
        ByTypeItem(
            type=item["type"],
            total=item["total"],
            passed=item["passed"],
        )
        for item in data["by_type"]
    ]

    total = data["total"]
    passed = data["passed"]
    pass_rate = round(passed / total * 100, 1) if total else 0

    return ProcessStatsResponse(
        term_id=term_id,
        total=total,
        passed=passed,
        rejected=data["rejected"],
        pass_rate=pass_rate,
        by_type=by_type,
    )
