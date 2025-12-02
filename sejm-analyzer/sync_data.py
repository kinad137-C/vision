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
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import duckdb

from app.repositories import CacheRepository, MpRepository, VotingRepository
from app.services.voting.analytics import VotingAnalytics
from etl import sync_all
from etl.validation import validate_term
from settings import BATCH_SIZE, DB_PATH, MAX_CONCURRENT
from settings.logging import setup_logging

logger = setup_logging(level="INFO", to_file=True)


def run_validation(terms: list[int] | None = None):
    """Validate terms in database."""
    conn = duckdb.connect(DB_PATH, read_only=True)

    if terms:
        # Validate only specified terms
        all_terms = terms
    else:
        # Get terms that actually have data (MPs > 0)
        all_terms = [r[0] for r in conn.execute("SELECT DISTINCT term_id FROM mp ORDER BY term_id DESC").fetchall()]

    if not all_terms:
        print("\n⚠️  No synced data found. Run 'python sync_data.py' first.\n")
        conn.close()
        return True

    print("\n" + "=" * 60)
    print("DATA VALIDATION REPORT")
    print("=" * 60)

    all_valid = True
    for term in all_terms:
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


def precompute_analytics(terms: list[int] | None = None, force: bool = False):
    """Precompute and cache analytics for terms."""
    mp_repo = MpRepository()
    voting_repo = VotingRepository()
    cache_repo = CacheRepository(read_only=False)
    analytics = VotingAnalytics(voting_repo=voting_repo, mp_repo=mp_repo, cache_repo=cache_repo)

    if terms is None:
        terms = mp_repo.get_terms()

    # Get terms with voting data from DB
    terms_data = mp_repo.get_terms_with_data()
    terms_with_voting = terms_data["voting"]

    for term_id in terms:
        if term_id not in terms_with_voting:
            logger.info("Skipping term {} (no voting data)", term_id)
            continue

        if force:
            cache_repo.clear(term_id)

        if cache_repo.exists(term_id) and not force:
            logger.info("Term {}: analytics already cached", term_id)
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
        logger.info("Syncing terms: {}", terms)

    mode = "FORCE (re-download all)" if force else "INCREMENTAL (skip existing)"
    logger.info("Mode: {}", mode)
    logger.info("Throttling: {} concurrent, {}/batch", MAX_CONCURRENT, BATCH_SIZE)

    sync_all(terms=terms, batch_size=BATCH_SIZE, force=force)

    logger.info("Running validation...")
    run_validation(terms=terms)

    logger.info("Precomputing analytics...")
    precompute_analytics(terms=terms, force=force)


if __name__ == "__main__":
    main()
