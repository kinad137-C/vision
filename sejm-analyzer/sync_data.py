#!/usr/bin/env python3
"""
Sync data from Sejm API and precompute analytics.

Usage:
    python sync_data.py              # Sync current term (10)
    python sync_data.py all          # Sync all terms
    python sync_data.py 10 9 8       # Sync specific terms
    python sync_data.py 10 --force   # Force re-download everything
    python sync_data.py --validate   # Check data integrity
    python sync_data.py --recompute  # Recompute analytics only (no sync)
"""

import sys

import duckdb

from src.analytics import Analytics
from src.collector import sync_all, validate_term
from src.logging_config import setup_logging
from src.repository import Repository
from src.settings import BATCH_SIZE, DB_PATH, MAX_CONCURRENT

logger = setup_logging(level="INFO", to_file=True)

TERMS_WITH_VOTING_DATA = {7, 8, 9, 10}


def run_validation():
    """Validate all terms in database."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    terms = [r[0] for r in conn.execute("SELECT id FROM term ORDER BY id DESC").fetchall()]

    print("\n" + "=" * 60)
    print("DATA VALIDATION REPORT")
    print("=" * 60)

    all_valid = True
    for term in terms:
        result = validate_term(conn, term)
        status = "✅" if result["valid"] else "❌"
        print(f"\nTerm {term} {status}")
        print(f"  MPs: {result['stats']['mps']:,}")
        print(f"  Votings: {result['stats']['votings']:,}")
        print(f"  Votes: {result['stats']['votes']:,}")
        print(f"  Processes: {result['stats'].get('processes', 0):,}")
        print(f"  Coverage: {result['stats']['coverage_pct']}%")
        print(f"  Missing votes: {result['stats']['votings_missing_votes']}")
        if result["issues"]:
            all_valid = False
            for issue in result["issues"]:
                print(f"  ⚠️  {issue}")

    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All data valid!")
    else:
        print("❌ Some issues found. Run sync again to fix.")
    print("=" * 60 + "\n")

    conn.close()
    return all_valid


def precompute_analytics(terms: list[int] = None, force: bool = False):
    """Precompute and cache analytics for terms."""
    repo = Repository(read_only=False)
    analytics = Analytics(repo)

    if terms is None:
        terms = repo.get_terms()

    for term_id in terms:
        if term_id not in TERMS_WITH_VOTING_DATA:
            logger.info(f"Skipping term {term_id} (no voting data)")
            continue

        if force:
            repo.clear_analytics_cache(term_id)

        if repo.has_analytics_cache(term_id) and not force:
            logger.info(f"Term {term_id}: analytics already cached")
            continue

        analytics.precompute_all(term_id)

    logger.info("Analytics precomputation complete!")


def main():
    args = sys.argv[1:]

    if "--validate" in args or args == ["validate"]:
        run_validation()
        return

    if "--recompute" in args:
        force = "--force" in args or "-f" in args
        logger.info("Recomputing analytics only...")
        precompute_analytics(force=force)
        return

    force = "--force" in args or "-f" in args
    args = [a for a in args if a not in ("--force", "-f", "--validate", "--recompute")]

    if not args:
        terms = [10]
        logger.info("Syncing current term (10)")
    elif args[0] == "all":
        terms = None
        logger.info("Syncing ALL terms")
    else:
        terms = [int(t) for t in args if t.isdigit()]
        if not terms:
            print(__doc__)
            sys.exit(1)
        logger.info(f"Syncing terms: {terms}")

    mode = "FORCE (re-download all)" if force else "INCREMENTAL (skip existing)"
    logger.info(f"Mode: {mode}")
    logger.info(f"Throttling: {MAX_CONCURRENT} concurrent, {BATCH_SIZE}/batch, exponential backoff 2-60s")

    sync_all(terms=terms, max_concurrent=MAX_CONCURRENT, batch_size=BATCH_SIZE, force=force)

    logger.info("Running validation...")
    run_validation()

    logger.info("Precomputing analytics...")
    precompute_analytics(terms=terms, force=force)


if __name__ == "__main__":
    main()
