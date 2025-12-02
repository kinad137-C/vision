"""DuckDB connection management."""

import threading
from pathlib import Path

import duckdb
from loguru import logger

from app.models import ALL_DDL
from settings import DB_PATH

_local = threading.local()


def db_exists() -> bool:
    """Check if database file exists."""
    return Path(DB_PATH).exists()


def _tables_exist(conn: duckdb.DuckDBPyConnection) -> bool:
    """Check if main tables already exist."""
    try:
        result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'mp'").fetchone()
        return result[0] > 0
    except Exception:
        return False


def init_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize all tables from DDL statements (idempotent - uses IF NOT EXISTS)."""
    if _tables_exist(conn):
        return

    for ddl in ALL_DDL:
        conn.execute(ddl)
    logger.info("DB tables initialized")


def _ensure_db_exists() -> None:
    """Create DB with tables if it doesn't exist."""
    if not db_exists():
        logger.warning("DB not found: {}. Creating empty DB.", DB_PATH)
        conn = duckdb.connect(DB_PATH)
        init_tables(conn)
        conn.close()


def get_db(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Get thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _ensure_db_exists()
        _local.conn = duckdb.connect(DB_PATH, read_only=read_only)
        logger.debug("DB connected: {} (read_only={})", DB_PATH, read_only)
    return _local.conn


def close_db() -> None:
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
    _ensure_db_exists()
    conn = duckdb.connect(DB_PATH)
    init_tables(conn)
    return conn
