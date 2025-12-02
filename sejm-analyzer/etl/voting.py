"""Voting ETL - sync votings and votes."""

import asyncio
from datetime import datetime

import duckdb
import polars as pl
from loguru import logger

from etl.helpers import get_existing_ids, get_existing_voting_ids
from sejm_client import safe_request
from sejm_client.voting import VotingClient

BATCH_DELAY = 2.0


async def fetch_votes(client: VotingClient, term: int, sitting: int, voting: int, vid: str) -> list:
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
        logger.warning("Failed votes {}: {}", vid, e)
        return []


async def sync_votings(
    client: VotingClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
    sittings: list,
    batch_size: int,
    force: bool,
) -> None:
    """Sync votings and votes for a term."""
    existing_votings = get_existing_ids(conn, "voting", term)
    existing_votes = get_existing_voting_ids(conn, term) if not force else set()

    logger.info("Checking {} sittings for new votings...", len(sittings))
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
        logger.info("Votings: +{} new", len(new_votings))

    if not voting_ids_to_fetch:
        logger.info("Votes: all {} already loaded", len(existing_votes))
        return

    # Fetch individual votes
    logger.info("Fetching votes for {} votings...", len(voting_ids_to_fetch))
    all_votes = []
    total_batches = (len(voting_ids_to_fetch) + batch_size - 1) // batch_size

    for i in range(0, len(voting_ids_to_fetch), batch_size):
        batch = voting_ids_to_fetch[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info("Batch {}/{}", batch_num, total_batches)

        results = await asyncio.gather(*[fetch_votes(client, term, s, v, vid) for s, v, vid in batch])

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
            logger.debug("Batch {}: inserted {} votes", batch_num, len(batch_votes))

        if i + batch_size < len(voting_ids_to_fetch):
            await asyncio.sleep(BATCH_DELAY)

    logger.info("Votes: +{} new", len(all_votes))
