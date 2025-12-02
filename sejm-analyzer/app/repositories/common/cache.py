"""Cache repository - analytics cache storage."""

import json
from datetime import datetime

from loguru import logger

from app.repositories.base import BaseRepository


class CacheRepository(BaseRepository):
    """Repository for analytics cache operations."""

    def get(self, term_id: int, key: str) -> dict | None:
        """Load cached analytics from DB."""
        row = self.fetchone(
            "SELECT data FROM analytics_cache WHERE term_id = ? AND key = ?",
            [term_id, key],
        )
        if row:
            logger.debug("Cache hit: term={}, key={}", term_id, key)
            return json.loads(row[0])
        return None

    def set(self, term_id: int, key: str, data: dict) -> None:
        """Save analytics to cache."""
        if self._read_only:
            raise RuntimeError("Cannot write cache in read-only mode")

        json_data = json.dumps(data)
        self.execute(
            """
            INSERT OR REPLACE INTO analytics_cache (term_id, key, data, computed_at)
            VALUES (?, ?, ?, ?)
            """,
            [term_id, key, json_data, datetime.utcnow()],
        )
        logger.debug("Cache saved: term={}, key={}", term_id, key)

    def clear(self, term_id: int | None = None) -> None:
        """Clear cache for a term or all."""
        if self._read_only:
            raise RuntimeError("Cannot clear cache in read-only mode")

        if term_id:
            self.execute("DELETE FROM analytics_cache WHERE term_id = ?", [term_id])
            logger.info("Cache cleared for term {}", term_id)
        else:
            self.execute("DELETE FROM analytics_cache")
            logger.info("All cache cleared")

    def exists(self, term_id: int) -> bool:
        """Check if term has cached analytics."""
        row = self.fetchone(
            "SELECT COUNT(*) FROM analytics_cache WHERE term_id = ?",
            [term_id],
        )
        return row[0] > 0
