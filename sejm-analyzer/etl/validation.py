"""Data validation functions."""

import duckdb


def validate_term(conn: duckdb.DuckDBPyConnection, term: int) -> dict:
    """Validate data integrity for a term."""
    issues = []
    stats = {}

    mp_count = conn.execute("SELECT COUNT(*) FROM mp WHERE term_id = ?", [term]).fetchone()[0]
    stats["mps"] = mp_count
    if mp_count == 0:
        issues.append("No MPs found")

    voting_check = conn.execute(
        """
        SELECT
            COUNT(*) as total_votings,
            SUM(CASE WHEN yes + no + abstain + not_voting = 0 THEN 1 ELSE 0 END) as empty
        FROM voting WHERE term_id = ?
        """,
        [term],
    ).fetchone()
    stats["votings"] = voting_check[0] or 0
    empty_votings = voting_check[1] or 0
    if empty_votings > 0:
        issues.append(f"{empty_votings} votings have zero votes in summary")

    vote_check = conn.execute(
        """
        SELECT COUNT(*) FROM voting v
        LEFT JOIN vote ON vote.voting_id = v.id
        WHERE v.term_id = ? AND vote.id IS NULL AND v.yes + v.no > 0
        """,
        [term],
    ).fetchone()[0]
    stats["votings_missing_votes"] = vote_check
    if vote_check > 0:
        issues.append(f"{vote_check} votings have no individual votes loaded")

    vote_count = conn.execute(
        """
        SELECT COUNT(*) FROM vote
        JOIN voting v ON vote.voting_id = v.id
        WHERE v.term_id = ?
        """,
        [term],
    ).fetchone()[0]
    stats["votes"] = vote_count

    process_count = conn.execute("SELECT COUNT(*) FROM process WHERE term_id = ?", [term]).fetchone()[0]
    stats["processes"] = process_count

    coverage_check = conn.execute(
        """
        SELECT
            COUNT(DISTINCT v.id) as total,
            COUNT(DISTINCT CASE WHEN vote.id IS NOT NULL THEN v.id END) as with_votes
        FROM voting v
        LEFT JOIN vote ON vote.voting_id = v.id
        WHERE v.term_id = ?
        """,
        [term],
    ).fetchone()
    if coverage_check and coverage_check[0]:
        stats["coverage_pct"] = round(coverage_check[1] / coverage_check[0] * 100, 1)
    else:
        stats["coverage_pct"] = 0

    return {
        "term": term,
        "valid": len(issues) == 0,
        "stats": stats,
        "issues": issues,
    }
