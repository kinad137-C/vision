"""Repository: data access layer with caching."""

import json
from collections import defaultdict
from datetime import datetime

from loguru import logger

from src.db import get_db, reconnect_db


class Repository:
    """All data access in one place."""

    def __init__(self, read_only: bool = True):
        self._db = get_db(read_only)
        self._read_only = read_only
        self._cache: dict = {}
        logger.debug("Repository initialized")

    def clear_cache(self):
        self._cache.clear()
        logger.debug("Repository cache cleared")

    def refresh(self):
        self._db = reconnect_db(self._read_only)
        self.clear_cache()
        logger.info("Repository refreshed")

    def _cached(self, key: str, fn):
        if key not in self._cache:
            self._cache[key] = fn()
            logger.debug(f"Cache miss: {key}")
        return self._cache[key]

    # ========== Terms ==========

    def get_terms(self) -> list[int]:
        """Available terms with data."""
        rows = self._db.execute(
            """
            SELECT DISTINCT term_id FROM mp ORDER BY term_id DESC
        """
        ).fetchall()
        return [r[0] for r in rows]

    # ========== Parties ==========

    def get_parties(self, term_id: int) -> dict[str, int]:
        """Party seats: {party: count}."""

        def fetch():
            rows = self._db.execute(
                """
                SELECT club, COUNT(*) FROM mp
                WHERE term_id = ? AND club IS NOT NULL
                GROUP BY club
            """,
                [term_id],
            ).fetchall()
            result = {r[0]: int(r[1]) for r in rows}
            logger.debug(f"get_parties({term_id}): {len(result)} parties")
            return result

        return self._cached(f"parties_{term_id}", fetch)

    # ========== Voting decisions ==========

    def get_party_decisions(self, term_id: int) -> list[dict]:
        """Party majority vote per voting."""

        def fetch():
            rows = self._db.execute(
                """
                SELECT v.voting_id, v.club,
                       SUM(CASE WHEN v.vote = 'YES' THEN 1 ELSE 0 END) as yes,
                       SUM(CASE WHEN v.vote = 'NO' THEN 1 ELSE 0 END) as no
                FROM vote v
                JOIN voting vt ON v.voting_id = vt.id
                WHERE vt.term_id = ? AND v.club IS NOT NULL
                GROUP BY v.voting_id, v.club
            """,
                [term_id],
            ).fetchall()
            result = [
                {
                    "voting_id": r[0],
                    "party": r[1],
                    "yes": int(r[2]),
                    "no": int(r[3]),
                    "decision": "YES" if int(r[2]) > int(r[3]) else "NO",
                }
                for r in rows
            ]
            logger.debug(f"get_party_decisions({term_id}): {len(result)} decisions")
            return result

        return self._cached(f"decisions_{term_id}", fetch)

    def get_vote_sequences(self, term_id: int) -> dict[str, list[str]]:
        """Vote sequences per party for Markov analysis."""

        def fetch():
            rows = self._db.execute(
                """
                WITH decisions AS (
                    SELECT v.club, vt.date,
                           CASE WHEN SUM(CASE WHEN v.vote='YES' THEN 1 ELSE 0 END) >
                                     SUM(CASE WHEN v.vote='NO' THEN 1 ELSE 0 END)
                                THEN 'YES' ELSE 'NO' END as decision
                    FROM vote v JOIN voting vt ON v.voting_id = vt.id
                    WHERE vt.term_id = ? AND v.club IS NOT NULL
                    GROUP BY v.club, vt.id, vt.date
                    ORDER BY v.club, vt.date
                )
                SELECT club, decision FROM decisions
            """,
                [term_id],
            ).fetchall()

            result = defaultdict(list)
            for party, decision in rows:
                result[party].append(decision)
            logger.debug(f"get_vote_sequences({term_id}): {len(result)} parties")
            return dict(result)

        return self._cached(f"sequences_{term_id}", fetch)

    # ========== Processes (NEW) ==========

    def get_processes(self, term_id: int, passed_only: bool = False) -> list[dict]:
        """Get legislative processes for a term."""

        def fetch():
            query = """
                SELECT id, number, title, document_type, passed,
                       process_start_date, closure_date, title_final
                FROM process
                WHERE term_id = ?
            """
            if passed_only:
                query += " AND passed = TRUE"
            query += " ORDER BY process_start_date DESC"

            rows = self._db.execute(query, [term_id]).fetchall()
            return [
                {
                    "id": r[0],
                    "number": r[1],
                    "title": r[2],
                    "document_type": r[3],
                    "passed": r[4],
                    "process_start_date": r[5],
                    "closure_date": r[6],
                    "title_final": r[7],
                }
                for r in rows
            ]

        key = f"processes_{term_id}_{'passed' if passed_only else 'all'}"
        return self._cached(key, fetch)

    def get_process_voting_links(self, term_id: int) -> list[dict]:
        """Get links between processes and votings."""

        def fetch():
            rows = self._db.execute(
                """
                SELECT ps.process_id, ps.voting_id, ps.stage_name, ps.decision,
                       p.number, p.title, p.passed
                FROM process_stage ps
                JOIN process p ON ps.process_id = p.id
                WHERE p.term_id = ? AND ps.voting_id IS NOT NULL
            """,
                [term_id],
            ).fetchall()
            return [
                {
                    "process_id": r[0],
                    "voting_id": r[1],
                    "stage_name": r[2],
                    "decision": r[3],
                    "process_number": r[4],
                    "process_title": r[5],
                    "passed": r[6],
                }
                for r in rows
            ]

        return self._cached(f"process_votings_{term_id}", fetch)

    def get_voting_with_process(self, term_id: int) -> list[dict]:
        """Get votings enriched with process info."""

        def fetch():
            rows = self._db.execute(
                """
                SELECT v.id, v.title, v.topic, v.date, v.yes, v.no,
                       p.number as process_number, p.title as process_title,
                       p.document_type, p.passed
                FROM voting v
                LEFT JOIN process_stage ps ON ps.voting_id = v.id
                LEFT JOIN process p ON ps.process_id = p.id
                WHERE v.term_id = ?
                ORDER BY v.date DESC
            """,
                [term_id],
            ).fetchall()
            return [
                {
                    "voting_id": r[0],
                    "voting_title": r[1],
                    "topic": r[2],
                    "date": r[3],
                    "yes": r[4],
                    "no": r[5],
                    "process_number": r[6],
                    "process_title": r[7],
                    "document_type": r[8],
                    "passed": r[9],
                }
                for r in rows
            ]

        return self._cached(f"voting_process_{term_id}", fetch)

    def get_process_stats(self, term_id: int) -> dict:
        """Get aggregate statistics for processes."""

        def fetch():
            # Basic stats
            basic = self._db.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN passed = false THEN 1 ELSE 0 END) as rejected
                FROM process WHERE term_id = ?
            """,
                [term_id],
            ).fetchone()

            # By document type
            by_type = self._db.execute(
                """
                SELECT document_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed
                FROM process WHERE term_id = ?
                GROUP BY document_type
                ORDER BY COUNT(*) DESC
            """,
                [term_id],
            ).fetchall()

            return {
                "total": basic[0] or 0,
                "passed": basic[1] or 0,
                "rejected": basic[2] or 0,
                "by_type": [{"type": r[0], "total": r[1], "passed": r[2]} for r in by_type],
            }

        return self._cached(f"process_stats_{term_id}", fetch)

    # ========== Analytics cache ==========

    def get_analytics_cache(self, term_id: int, key: str) -> dict | None:
        """Load precomputed analytics from DB."""
        row = self._db.execute(
            """
            SELECT data FROM analytics_cache WHERE term_id = ? AND key = ?
        """,
            [term_id, key],
        ).fetchone()
        if row:
            logger.debug(f"Analytics cache hit: term={term_id}, key={key}")
            return json.loads(row[0])
        return None

    def set_analytics_cache(self, term_id: int, key: str, data: dict):
        """Save precomputed analytics to DB."""
        if self._read_only:
            logger.warning("Cannot write analytics cache in read-only mode")
            return

        json_data = json.dumps(data)
        self._db.execute(
            """
            INSERT OR REPLACE INTO analytics_cache (term_id, key, data, computed_at)
            VALUES (?, ?, ?, ?)
        """,
            [term_id, key, json_data, datetime.utcnow()],
        )
        logger.debug(f"Analytics cache saved: term={term_id}, key={key}")

    def clear_analytics_cache(self, term_id: int = None):
        """Clear analytics cache for a term or all."""
        if self._read_only:
            logger.warning("Cannot clear analytics cache in read-only mode")
            return

        if term_id:
            self._db.execute("DELETE FROM analytics_cache WHERE term_id = ?", [term_id])
            logger.info(f"Analytics cache cleared for term {term_id}")
        else:
            self._db.execute("DELETE FROM analytics_cache")
            logger.info("All analytics cache cleared")

    def has_analytics_cache(self, term_id: int) -> bool:
        """Check if term has precomputed analytics."""
        row = self._db.execute(
            """
            SELECT COUNT(*) FROM analytics_cache WHERE term_id = ?
        """,
            [term_id],
        ).fetchone()
        return row[0] > 0
