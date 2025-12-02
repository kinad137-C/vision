"""Models package - DDL and entities for all domains."""

from app.models.common import CACHE_DDL, BaseEntity
from app.models.core import (
    CLUB_DDL,
    MP_DDL,
    SITTING_DDL,
    TERM_DDL,
)
from app.models.legislation import (
    PRINT_DDL,
    PROCESS_DDL,
    PROCESS_STAGE_DDL,
    PredictionResult,
    TopicCluster,
)
from app.models.voting import (
    VOTE_DDL,
    VOTING_DDL,
    Cohesion,
    PowerIndex,
)

ALL_DDL = [
    # Core
    TERM_DDL,
    CLUB_DDL,
    MP_DDL,
    SITTING_DDL,
    # Voting
    VOTING_DDL,
    VOTE_DDL,
    # Legislation
    PROCESS_DDL,
    PROCESS_STAGE_DDL,
    PRINT_DDL,
    # Common
    CACHE_DDL,
]

__all__ = [
    # Common
    "BaseEntity",
    "CACHE_DDL",
    # Core
    "TERM_DDL",
    "CLUB_DDL",
    "MP_DDL",
    "SITTING_DDL",
    # Voting
    "VOTING_DDL",
    "VOTE_DDL",
    "PowerIndex",
    "Cohesion",
    # Legislation
    "PROCESS_DDL",
    "PROCESS_STAGE_DDL",
    "PRINT_DDL",
    "TopicCluster",
    "PredictionResult",
    # All DDL
    "ALL_DDL",
]
