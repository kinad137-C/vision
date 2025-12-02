"""Core ETL - sync MPs, clubs, sittings."""

import duckdb
import polars as pl
from loguru import logger

from etl.helpers import get_existing_ids
from sejm_client import safe_request
from sejm_client.core import CoreClient


async def sync_core_data(
    client: CoreClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
) -> list:
    """Sync MPs, clubs, sittings for a term."""
    clubs = await safe_request(client.clubs(term), [])
    mps = await safe_request(client.mps(term), [])
    proceedings = await safe_request(client.proceedings(term), [])

    if not mps:
        logger.error("Failed to fetch MPs for term {}, skipping", term)
        return []

    # Clubs (with transaction)
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
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute("DELETE FROM club WHERE term_id = ?", [term])
            conn.register("clubs_df", clubs_df)
            conn.execute("INSERT INTO club SELECT * FROM clubs_df")
            conn.unregister("clubs_df")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        logger.info("Clubs: {}", len(clubs))

    # MPs (with transaction)
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
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("DELETE FROM mp WHERE term_id = ?", [term])
        conn.register("mps_df", mps_df)
        conn.execute("INSERT INTO mp SELECT * FROM mps_df")
        conn.unregister("mps_df")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    logger.info("MPs: {}", len(mps))

    # Sittings
    sittings = [p for p in proceedings if p["number"] != 0]
    existing_sittings = get_existing_ids(conn, "sitting", term)
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
        logger.info("Sittings: +{} new (total {})", len(new_sittings), len(sittings))
    else:
        logger.info("Sittings: {} (all exist)", len(sittings))

    return sittings
