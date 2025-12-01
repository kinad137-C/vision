#!/usr/bin/env python3
"""
Sync data from Sejm API (incremental by default).

Usage:
    python sync_data.py              # Sync current term (10)
    python sync_data.py all          # Sync all terms
    python sync_data.py 10 9 8       # Sync specific terms
    python sync_data.py 10 --force   # Force re-download everything
    python sync_data.py --validate   # Check data integrity

Throttling:
    - 20 concurrent requests max
    - 50ms delay between requests  
    - 1s delay between batches
    - Exponential backoff: 2s → 4s → 8s → 16s → 32s → 60s (max)

Data is validated after each term sync.
"""
import sys
import duckdb

from src.logging_config import setup_logging
from src.collector import sync_all, validate_term
from src.settings import MAX_CONCURRENT, BATCH_SIZE, DB_PATH

logger = setup_logging(level="INFO", to_file=True)


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
        print(f"  Coverage: {result['stats']['coverage_pct']}%")
        print(f"  Missing votes: {result['stats']['votings_missing_votes']}")
        print(f"  Orphan votes: {result['stats']['orphan_votes']}")
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


def main():
    args = sys.argv[1:]
    
    # Validate mode
    if "--validate" in args or args == ["validate"]:
        run_validation()
        return
    
    force = "--force" in args or "-f" in args
    args = [a for a in args if a not in ("--force", "-f", "--validate")]
    
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
    
    # Run validation after sync
    logger.info("Running validation...")
    run_validation()


if __name__ == "__main__":
    main()
