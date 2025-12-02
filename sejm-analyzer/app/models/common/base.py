"""Base entity class for all domain entities."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class BaseEntity:
    """Base class for all entities."""

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary."""
        return asdict(self)
