"""Database: connection, schema, repository."""
import threading
from collections import defaultdict
from pathlib import Path

import duckdb
from loguru import logger

from src.settings import DB_PATH

_local = threading.local()


def db_exists() -> bool:
    """Check if database file exists."""
    return Path(DB_PATH).exists()


def get_db(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Get thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        if read_only and not db_exists():
            logger.warning(f"DB not found: {DB_PATH}. Creating empty DB.")
            conn = duckdb.connect(DB_PATH)
            init_tables(conn)
            conn.close()
        
        _local.conn = duckdb.connect(DB_PATH, read_only=read_only)
        logger.debug(f"DB connected: {DB_PATH} (read_only={read_only})")
    return _local.conn


def close_db():
    """Close thread-local connection."""
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
        logger.debug("DB connection closed")


def reconnect_db(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Force reconnect."""
    close_db()
    return get_db(read_only)


def init_tables(conn: duckdb.DuckDBPyConnection):
    """Create tables if not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS term (
            id INTEGER PRIMARY KEY, from_date DATE NOT NULL, to_date DATE, current BOOLEAN DEFAULT FALSE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS club (
            id VARCHAR PRIMARY KEY, term_id INTEGER, abbr VARCHAR, name VARCHAR, members_count INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mp (
            id VARCHAR PRIMARY KEY, term_id INTEGER, mp_id INTEGER,
            first_name VARCHAR, last_name VARCHAR, club VARCHAR, district VARCHAR, active BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sitting (
            id VARCHAR PRIMARY KEY, term_id INTEGER, number INTEGER, dates VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS voting (
            id VARCHAR PRIMARY KEY, sitting_id VARCHAR, term_id INTEGER, sitting_num INTEGER, voting_num INTEGER,
            date TIMESTAMP, title VARCHAR, topic VARCHAR, yes INTEGER, no INTEGER, abstain INTEGER, not_voting INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vote (
            id VARCHAR PRIMARY KEY, voting_id VARCHAR, mp_id VARCHAR, club VARCHAR, vote VARCHAR
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mp_term ON mp(term_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_voting ON vote(voting_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_mp ON vote(mp_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_club ON vote(club)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voting_term ON voting(term_id)")
    logger.info("DB tables initialized")


class Repository:
    """All data access in one place."""
    
    def __init__(self):
        self._db = get_db()
        self._cache = {}
        logger.debug("Repository initialized")
    
    def clear_cache(self):
        self._cache.clear()
        logger.debug("Repository cache cleared")
    
    def refresh(self):
        self._db = reconnect_db()
        self.clear_cache()
        logger.info("Repository refreshed")
    
    def _cached(self, key: str, fn):
        if key not in self._cache:
            self._cache[key] = fn()
            logger.debug(f"Cache miss: {key}")
        return self._cache[key]
    
    def get_terms(self) -> list[int]:
        """Available terms with data."""
        rows = self._db.execute("""
            SELECT DISTINCT term_id FROM mp ORDER BY term_id DESC
        """).fetchall()
        return [r[0] for r in rows]
    
    def get_parties(self, term_id: int) -> dict[str, int]:
        """Party seats: {party: count}."""
        def fetch():
            rows = self._db.execute("""
                SELECT club, COUNT(*) FROM mp 
                WHERE term_id = ? AND club IS NOT NULL
                GROUP BY club
            """, [term_id]).fetchall()
            result = {r[0]: int(r[1]) for r in rows}
            logger.debug(f"get_parties({term_id}): {len(result)} parties, {sum(result.values())} MPs")
            return result
        return self._cached(f"parties_{term_id}", fetch)
    
    def get_party_decisions(self, term_id: int) -> list[dict]:
        """Party majority vote per voting."""
        def fetch():
            rows = self._db.execute("""
                SELECT v.voting_id, v.club,
                       SUM(CASE WHEN v.vote = 'YES' THEN 1 ELSE 0 END) as yes,
                       SUM(CASE WHEN v.vote = 'NO' THEN 1 ELSE 0 END) as no
                FROM vote v
                JOIN voting vt ON v.voting_id = vt.id
                WHERE vt.term_id = ? AND v.club IS NOT NULL
                GROUP BY v.voting_id, v.club
            """, [term_id]).fetchall()
            result = [
                {"voting_id": r[0], "party": r[1], "yes": int(r[2]), "no": int(r[3]),
                 "decision": "YES" if int(r[2]) > int(r[3]) else "NO"}
                for r in rows
            ]
            logger.debug(f"get_party_decisions({term_id}): {len(result)} decisions")
            return result
        return self._cached(f"decisions_{term_id}", fetch)
    
    def get_vote_sequences(self, term_id: int) -> dict[str, list[str]]:
        """Vote sequences per party for Markov analysis."""
        def fetch():
            rows = self._db.execute("""
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
            """, [term_id]).fetchall()
            
            result = defaultdict(list)
            for party, decision in rows:
                result[party].append(decision)
            logger.debug(f"get_vote_sequences({term_id}): {len(result)} parties")
            return dict(result)
        return self._cached(f"sequences_{term_id}", fetch)
