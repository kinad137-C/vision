"""ETL package - data sync from Sejm API to database."""

from etl.sync import sync_all, sync_term

__all__ = [
    "sync_all",
    "sync_term",
]
