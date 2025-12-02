"""Common models - base classes and shared tables."""

from app.models.common.base import BaseEntity
from app.models.common.cache import CACHE_DDL

__all__ = [
    "BaseEntity",
    "CACHE_DDL",
]
