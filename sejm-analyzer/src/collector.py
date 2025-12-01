"""Data collection ETL: sync data from Sejm API to database."""

import asyncio
from datetime import datetime

import duckdb
import polars as pl
from loguru import logger

from src.api_client import SejmClient, safe_request
from src.models.tables import init_tables
from src.settings import BATCH_DELAY, DB_PATH

# ========== Helpers ==========


def _get_existing_ids(conn: duckdb.DuckDBPyConnection, table: str, term: int) -> set:
    """Get existing IDs for a term from a table."""
    try:
        rows = conn.execute(f"SELECT id FROM {table} WHERE term_id = ?", [term]).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def _get_existing_voting_ids(conn: duckdb.DuckDBPyConnection, term: int) -> set:
    """Get voting IDs that already have votes loaded."""
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT voting_id FROM vote WHERE voting_id LIKE ?
        """,
            [f"{term}_%"],
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


async def _fetch_votes(client: SejmClient, term: int, sitting: int, voting: int, vid: str) -> list:
    """Fetch individual votes for a voting."""
    try:
        details = await client.voting(term, sitting, voting)
        return [
            (
                f"{vid}_{v.get('MP')}",
                vid,
                f"{term}_{v.get('MP')}",
                v.get("club"),
                v.get("vote", "NO_VOTE"),
            )
            for v in details.get("votes", [])
        ]
    except Exception as e:
        logger.warning(f"Failed votes {vid}: {e}")
        return []


# ========== Validation ==========


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
    stats["coverage_pct"] = round(coverage_check[1] / coverage_check[0] * 100, 1) if coverage_check[0] else 0

    return {
        "term": term,
        "valid": len(issues) == 0,
        "stats": stats,
        "issues": issues,
    }


# ========== Sync Core Data ==========


async def sync_term(
    client: SejmClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
    batch_size: int = 50,
    force: bool = False,
):
    """Sync all data for a term incrementally."""
    logger.info(f"Syncing term {term}" + (" [FORCE]" if force else " [INCREMENTAL]"))

    # Fetch basic data
    clubs = await safe_request(client.clubs(term), [])
    mps = await safe_request(client.mps(term), [])
    proceedings = await safe_request(client.proceedings(term), [])

    if not mps:
        logger.error(f"Failed to fetch MPs for term {term}, skipping")
        return

    # Clubs
    if clubs:
        clubs_df = pl.DataFrame(
            [
                {
                    "id": f"{term}_{c['id']}",
                    "term_id": term,
                    "abbr": c["id"],
                    "name": c["name"],
                    "members_count": c.get("membersCount", 0),
                }
                for c in clubs
            ]
        )
        conn.execute("DELETE FROM club WHERE term_id = ?", [term])
        conn.register("clubs_df", clubs_df)
        conn.execute("INSERT INTO club SELECT * FROM clubs_df")
        conn.unregister("clubs_df")
        logger.info(f"Clubs: {len(clubs)}")

    # MPs
    mps_df = pl.DataFrame(
        [
            {
                "id": f"{term}_{m['id']}",
                "term_id": term,
                "mp_id": m["id"],
                "first_name": m["firstName"],
                "last_name": m["lastName"],
                "club": m.get("club"),
                "district": m.get("districtName"),
                "active": m.get("active", True),
            }
            for m in mps
        ]
    )
    conn.execute("DELETE FROM mp WHERE term_id = ?", [term])
    conn.register("mps_df", mps_df)
    conn.execute("INSERT INTO mp SELECT * FROM mps_df")
    conn.unregister("mps_df")
    logger.info(f"MPs: {len(mps)}")

    # Sittings
    sittings = [p for p in proceedings if p["number"] != 0]
    existing_sittings = _get_existing_ids(conn, "sitting", term)
    new_sittings = [p for p in sittings if f"{term}_{p['number']}" not in existing_sittings]

    if new_sittings:
        sittings_df = pl.DataFrame(
            [
                {
                    "id": f"{term}_{p['number']}",
                    "term_id": term,
                    "number": p["number"],
                    "dates": str(p.get("dates", [])),
                }
                for p in new_sittings
            ]
        )
        conn.register("sittings_df", sittings_df)
        conn.execute("INSERT INTO sitting SELECT * FROM sittings_df")
        conn.unregister("sittings_df")
        logger.info(f"Sittings: +{len(new_sittings)} new (total {len(sittings)})")
    else:
        logger.info(f"Sittings: {len(sittings)} (all exist)")

    # Votings
    await _sync_votings(client, term, conn, sittings, batch_size, force)

    # Processes (NEW)
    await sync_processes(client, term, conn)

    # Validation
    result = validate_term(conn, term)
    if result["valid"]:
        logger.info(f"Validation OK: {result['stats']}")
    else:
        logger.warning(f"Validation issues: {result['issues']}")


async def _sync_votings(
    client: SejmClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
    sittings: list,
    batch_size: int,
    force: bool,
):
    """Sync votings and votes for a term."""
    existing_votings = _get_existing_ids(conn, "voting", term)
    existing_votes = _get_existing_voting_ids(conn, term) if not force else set()

    logger.info(f"Checking {len(sittings)} sittings for new votings...")
    new_votings, voting_ids_to_fetch = [], []

    for p in sittings:
        votings = await safe_request(client.votings(term, p["number"]), [])
        for v in votings:
            vid = f"{term}_{p['number']}_{v['votingNumber']}"

            if vid in existing_votings and not force:
                if vid not in existing_votes:
                    voting_ids_to_fetch.append((p["number"], v["votingNumber"], vid))
                continue

            voting_ids_to_fetch.append((p["number"], v["votingNumber"], vid))
            new_votings.append(
                {
                    "id": vid,
                    "sitting_id": f"{term}_{p['number']}",
                    "term_id": term,
                    "sitting_num": p["number"],
                    "voting_num": v["votingNumber"],
                    "date": datetime.fromisoformat(v["date"]),
                    "title": v["title"],
                    "topic": v.get("topic"),
                    "yes": v.get("yes", 0),
                    "no": v.get("no", 0),
                    "abstain": v.get("abstain", 0),
                    "not_voting": v.get("notParticipating", 0),
                }
            )
        await asyncio.sleep(0.05)

    if new_votings:
        votings_df = pl.DataFrame(new_votings)
        conn.register("votings_df", votings_df)
        conn.execute("INSERT INTO voting SELECT * FROM votings_df")
        conn.unregister("votings_df")
        logger.info(f"Votings: +{len(new_votings)} new")

    if not voting_ids_to_fetch:
        logger.info(f"Votes: all {len(existing_votes)} already loaded")
        return

    # Fetch individual votes
    logger.info(f"Fetching votes for {len(voting_ids_to_fetch)} votings...")
    all_votes = []
    total_batches = (len(voting_ids_to_fetch) + batch_size - 1) // batch_size

    for i in range(0, len(voting_ids_to_fetch), batch_size):
        batch = voting_ids_to_fetch[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"Batch {batch_num}/{total_batches}")

        results = await asyncio.gather(*[_fetch_votes(client, term, s, v, vid) for s, v, vid in batch])

        batch_votes = []
        for votes in results:
            batch_votes.extend(votes)

        if batch_votes:
            votes_df = pl.DataFrame(
                batch_votes,
                schema=["id", "voting_id", "mp_id", "club", "vote"],
                orient="row",
            )
            conn.register("votes_df", votes_df)
            conn.execute("INSERT INTO vote SELECT * FROM votes_df")
            conn.unregister("votes_df")
            all_votes.extend(batch_votes)
            logger.debug(f"Batch {batch_num}: inserted {len(batch_votes)} votes")

        if i + batch_size < len(voting_ids_to_fetch):
            await asyncio.sleep(BATCH_DELAY)

    logger.info(f"Votes: +{len(all_votes)} new")


# ========== Sync Processes (NEW) ==========


async def sync_processes(
    client: SejmClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
):
    """Sync legislative processes for a term."""
    logger.info(f"Syncing processes for term {term}...")

    existing = _get_existing_ids(conn, "process", term)

    # Fetch all processes (with pagination)
    all_processes = []
    offset = 0
    limit = 50

    while True:
        batch = await safe_request(client.processes(term, limit=limit, offset=offset), [])
        if not batch:
            break
        all_processes.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
        await asyncio.sleep(0.1)

    logger.info(f"Found {len(all_processes)} processes")

    # Filter new processes
    new_processes = [p for p in all_processes if f"{term}_{p['number']}" not in existing]

    if not new_processes:
        logger.info("All processes already exist")
        return

    # Process in batches
    process_rows = []
    stage_rows = []

    for proc in new_processes:
        pid = f"{term}_{proc['number']}"

        process_rows.append(
            {
                "id": pid,
                "term_id": term,
                "number": proc["number"],
                "title": proc.get("title", ""),
                "document_type": proc.get("documentType"),
                "document_type_enum": proc.get("documentTypeEnum"),
                "passed": proc.get("passed"),
                "process_start_date": proc.get("processStartDate"),
                "closure_date": proc.get("closureDate"),
                "change_date": proc.get("changeDate"),
                "description": proc.get("description"),
                "title_final": proc.get("titleFinal"),
            }
        )

        # Fetch detailed stages for linking to votings
        try:
            details = await client.process(term, proc["number"])
            stages = details.get("stages", [])

            for idx, stage in enumerate(_flatten_stages(stages)):
                stage_id = f"{pid}_{idx}"

                # Try to find voting link
                voting_id = None
                if stage.get("voting"):
                    v = stage["voting"]
                    voting_id = f"{term}_{v.get('sitting')}_{v.get('votingNumber')}"
                elif stage.get("sittingNum") and "czytanie" in stage.get("stageName", "").lower():
                    # Heuristic: try to link reading stages
                    pass

                stage_rows.append(
                    {
                        "id": stage_id,
                        "process_id": pid,
                        "stage_name": stage.get("stageName", ""),
                        "stage_type": stage.get("stageType"),
                        "date": stage.get("date"),
                        "sitting_num": stage.get("sittingNum"),
                        "decision": stage.get("decision"),
                        "committee_code": stage.get("committeeCode"),
                        "voting_id": voting_id,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to fetch process details {proc['number']}: {e}")

        await asyncio.sleep(0.05)

    # Insert processes
    if process_rows:
        process_df = pl.DataFrame(process_rows)
        conn.register("process_df", process_df)
        conn.execute("INSERT INTO process SELECT * FROM process_df")
        conn.unregister("process_df")
        logger.info(f"Processes: +{len(process_rows)} new")

    # Insert stages
    if stage_rows:
        stage_df = pl.DataFrame(stage_rows)
        conn.register("stage_df", stage_df)
        conn.execute("INSERT INTO process_stage SELECT * FROM stage_df")
        conn.unregister("stage_df")
        logger.info(f"Process stages: +{len(stage_rows)} new")


def _flatten_stages(stages: list, depth: int = 0) -> list:
    """Flatten nested stages structure."""
    result = []
    for stage in stages:
        result.append(stage)
        children = stage.get("children", [])
        if children:
            result.extend(_flatten_stages(children, depth + 1))
    return result


# ========== Entry Points ==========


def sync_all(
    terms: list[int] = None,
    max_concurrent: int = 20,
    batch_size: int = 50,
    force: bool = False,
):
    """Main sync entry point."""
    asyncio.run(_sync_async(terms, max_concurrent, batch_size, force))


async def _sync_async(
    terms: list[int],
    max_concurrent: int,
    batch_size: int,
    force: bool,
):
    conn = duckdb.connect(DB_PATH)
    init_tables(conn)

    async with SejmClient(max_concurrent=max_concurrent) as client:
        api_terms = await client.terms()

        terms_df = pl.DataFrame(
            [
                {
                    "id": t["num"],
                    "from_date": t["from"],
                    "to_date": t.get("to"),
                    "current": t.get("current", False),
                }
                for t in api_terms
            ]
        )
        conn.execute("DELETE FROM term")
        conn.register("terms_df", terms_df)
        conn.execute("INSERT INTO term SELECT * FROM terms_df")
        conn.unregister("terms_df")

        to_sync = [t for t in api_terms if terms is None or t["num"] in terms]
        for t in to_sync:
            try:
                await sync_term(client, t["num"], conn, batch_size, force)
            except Exception as e:
                logger.error(f"Failed to sync term {t['num']}: {e}")
                continue

    conn.close()
    logger.info("Sync complete!")
