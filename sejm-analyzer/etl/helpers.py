"""ETL helper functions."""

import duckdb


def get_existing_ids(conn: duckdb.DuckDBPyConnection, table: str, term: int) -> set[str]:
    """Get existing IDs for a term from a table."""
    try:
        rows = conn.execute(f"SELECT id FROM {table} WHERE term_id = ?", [term]).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def get_existing_voting_ids(conn: duckdb.DuckDBPyConnection, term: int) -> set[str]:
    """Get voting IDs that already have votes loaded."""
    try:
        rows = conn.execute(
            "SELECT DISTINCT voting_id FROM vote WHERE voting_id LIKE ?",
            [f"{term}_%"],
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
