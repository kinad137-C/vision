"""Base repository class."""

from collections.abc import Callable
from typing import Any

from loguru import logger

from app.repositories.db import get_db, reconnect_db


class BaseRepository:
    """Base repository with common functionality."""

    def __init__(self, read_only: bool = True):
        self._db = get_db(read_only)
        self._read_only = read_only
        self._cache: dict[str, Any] = {}
        logger.debug("{} initialized", self.__class__.__name__)

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def refresh(self) -> None:
        """Reconnect to database and clear cache."""
        self._db = reconnect_db(self._read_only)
        self.clear_cache()
        logger.info("Repository refreshed")

    def _cached(self, key: str, fn: Callable[[], Any]) -> Any:
        """Get from cache or compute."""
        if key not in self._cache:
            self._cache[key] = fn()
            logger.debug("Cache miss: {}", key)
        return self._cache[key]

    def execute(self, query: str, params: list | None = None) -> Any:
        """Execute SQL query."""
        if params:
            return self._db.execute(query, params)
        return self._db.execute(query)

    def fetchall(self, query: str, params: list | None = None) -> list:
        """Execute and fetch all rows."""
        return self.execute(query, params).fetchall()

    def fetchone(self, query: str, params: list | None = None) -> Any:
        """Execute and fetch one row."""
        return self.execute(query, params).fetchone()
