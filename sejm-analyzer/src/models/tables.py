"""SQL DDL for database tables."""

import duckdb
from loguru import logger


def init_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables if not exist."""

    # Core entities
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS term (
            id INTEGER PRIMARY KEY,
            from_date DATE NOT NULL,
            to_date DATE,
            current BOOLEAN DEFAULT FALSE
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS club (
            id VARCHAR PRIMARY KEY,
            term_id INTEGER,
            abbr VARCHAR,
            name VARCHAR,
            members_count INTEGER
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mp (
            id VARCHAR PRIMARY KEY,
            term_id INTEGER,
            mp_id INTEGER,
            first_name VARCHAR,
            last_name VARCHAR,
            club VARCHAR,
            district VARCHAR,
            active BOOLEAN
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sitting (
            id VARCHAR PRIMARY KEY,
            term_id INTEGER,
            number INTEGER,
            dates VARCHAR
        )
    """
    )

    # Votings
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS voting (
            id VARCHAR PRIMARY KEY,
            sitting_id VARCHAR,
            term_id INTEGER,
            sitting_num INTEGER,
            voting_num INTEGER,
            date TIMESTAMP,
            title VARCHAR,
            topic VARCHAR,
            yes INTEGER,
            no INTEGER,
            abstain INTEGER,
            not_voting INTEGER
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vote (
            id VARCHAR PRIMARY KEY,
            voting_id VARCHAR,
            mp_id VARCHAR,
            club VARCHAR,
            vote VARCHAR
        )
    """
    )

    # Legislative processes (NEW)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS process (
            id VARCHAR PRIMARY KEY,
            term_id INTEGER,
            number VARCHAR,
            title VARCHAR,
            document_type VARCHAR,
            document_type_enum VARCHAR,
            passed BOOLEAN,
            process_start_date DATE,
            closure_date DATE,
            change_date TIMESTAMP,
            description VARCHAR,
            title_final VARCHAR
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS process_stage (
            id VARCHAR PRIMARY KEY,
            process_id VARCHAR,
            stage_name VARCHAR,
            stage_type VARCHAR,
            date DATE,
            sitting_num INTEGER,
            decision VARCHAR,
            committee_code VARCHAR,
            voting_id VARCHAR
        )
    """
    )

    # Prints (NEW)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS print (
            id VARCHAR PRIMARY KEY,
            term_id INTEGER,
            number VARCHAR,
            title VARCHAR,
            document_date DATE,
            delivery_date DATE,
            change_date TIMESTAMP,
            process_print VARCHAR
        )
    """
    )

    # Analytics cache
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_cache (
            term_id INTEGER NOT NULL,
            key VARCHAR NOT NULL,
            data JSON NOT NULL,
            computed_at TIMESTAMP NOT NULL,
            PRIMARY KEY (term_id, key)
        )
    """
    )

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mp_term ON mp(term_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_voting ON vote(voting_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_mp ON vote(mp_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_club ON vote(club)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voting_term ON voting(term_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_process_term ON process(term_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_process_passed ON process(passed)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stage_process ON process_stage(process_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stage_voting ON process_stage(voting_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_print_term ON print(term_id)")

    logger.info("DB tables initialized")
