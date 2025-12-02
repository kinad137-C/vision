"""Legislation domain entities - ML and analytics results."""

from dataclasses import dataclass

from app.models.common import BaseEntity


@dataclass
class TopicCluster(BaseEntity):
    """A topic cluster with keywords and processes."""

    topic_id: int
    name: str
    keywords: list[str]
    process_count: int
    pass_rate: float
    example_titles: list[str]


@dataclass
class PredictionResult(BaseEntity):
    """Prediction result for a process."""

    process_id: str
    predicted_pass: bool
    probability: float
    top_features: list[tuple[str, float]]
