"""Data models: API schemas and DB tables."""
# Lazy imports to avoid circular dependencies

__all__ = [
    "TermSchema",
    "ClubSchema",
    "MPSchema",
    "ProceedingSchema",
    "VotingSchema",
    "VotingDetailsSchema",
    "VoteSchema",
    "ProcessHeaderSchema",
    "ProcessDetailsSchema",
    "ProcessStageSchema",
    "PrintSchema",
    "init_tables",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "init_tables":
        from src.models.tables import init_tables

        return init_tables

    # API schemas
    from src.models import api

    return getattr(api, name)
