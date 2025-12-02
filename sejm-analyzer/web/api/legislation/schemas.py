"""Legislation API response schemas."""

from pydantic import BaseModel


class TopicClusterItem(BaseModel):
    """Topic cluster stats."""

    name: str
    count: int
    pass_rate: float
    keywords: list[str]


class TopicStatsResponse(BaseModel):
    """Topic statistics response."""

    term_id: int
    total_topics: int
    clusters: list[TopicClusterItem]


class ByTypeItem(BaseModel):
    """Stats by document type."""

    type: str | None
    total: int
    passed: int


class ProcessStatsResponse(BaseModel):
    """Process statistics response."""

    term_id: int
    total: int
    passed: int
    rejected: int
    pass_rate: float
    by_type: list[ByTypeItem]
