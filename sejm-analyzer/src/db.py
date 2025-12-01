"""Database connection management."""

import threading
from pathlib import Path

import duckdb
from loguru import logger

from src.models.tables import init_tables
from src.settings import DB_PATH

_local = threading.local()


def db_exists() -> bool:
    """Check if database file exists."""
    return Path(DB_PATH).exists()


def get_db(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Get thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        if not db_exists():
            logger.warning(f"DB not found: {DB_PATH}. Creating empty DB.")
            conn = duckdb.connect(DB_PATH)
            init_tables(conn)
            conn.close()
        else:
            # Ensure tables exist
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


def get_write_connection() -> duckdb.DuckDBPyConnection:
    """Get a writable connection (for ETL operations)."""
    return duckdb.connect(DB_PATH)
