"""Core API client - terms, MPs, clubs, proceedings."""

from sejm_client.core.client import CoreClient
from sejm_client.core.schemas import ClubSchema, MPSchema, ProceedingSchema, TermSchema

__all__ = [
    "CoreClient",
    "TermSchema",
    "ClubSchema",
    "MPSchema",
    "ProceedingSchema",
]
