"""Main sync orchestration."""

import asyncio

import duckdb
import polars as pl
from loguru import logger

from app.repositories.db import init_tables
from etl.core import sync_core_data
from etl.legislation import sync_processes
from etl.validation import validate_term
from etl.voting import sync_votings
from sejm_client.core import CoreClient
from sejm_client.legislation import LegislationClient
from sejm_client.voting import VotingClient
from settings import DB_PATH


async def sync_term(
    term: int,
    conn: duckdb.DuckDBPyConnection,
    batch_size: int = 50,
    force: bool = False,
) -> None:
    """Sync all data for a term incrementally."""
    logger.info("Syncing term {}{}", term, " [FORCE]" if force else " [INCREMENTAL]")

    # Sync core data (MPs, clubs, sittings)
    async with CoreClient() as core_client:
        sittings = await sync_core_data(core_client, term, conn)

    if not sittings:
        return

    # Sync votings
    async with VotingClient() as voting_client:
        await sync_votings(voting_client, term, conn, sittings, batch_size, force)

    # Sync processes
    async with LegislationClient() as legislation_client:
        await sync_processes(legislation_client, term, conn)

    # Validation
    result = validate_term(conn, term)
    if result["valid"]:
        logger.info("Validation OK: {}", result["stats"])
    else:
        logger.warning("Validation issues: {}", result["issues"])


async def _sync_async(
    terms: list[int] | None,
    batch_size: int,
    force: bool,
) -> None:
    """Async sync implementation."""
    conn = duckdb.connect(DB_PATH)
    init_tables(conn)

    async with CoreClient() as client:
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
            await sync_term(t["num"], conn, batch_size, force)
        except Exception as e:
            logger.error("Failed to sync term {}: {}", t["num"], e)
            continue

    conn.close()
    logger.info("Sync complete!")


def sync_all(
    terms: list[int] | None = None,
    batch_size: int = 50,
    force: bool = False,
) -> None:
    """Main sync entry point."""
    asyncio.run(_sync_async(terms, batch_size, force))
