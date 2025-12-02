"""Legislation ETL - sync processes and stages."""

import asyncio

import duckdb
import polars as pl
from loguru import logger

from etl.helpers import get_existing_ids
from sejm_client import safe_request
from sejm_client.legislation import LegislationClient


def flatten_stages(stages: list, depth: int = 0) -> list:
    """Flatten nested stages structure."""
    result = []
    for stage in stages:
        result.append(stage)
        children = stage.get("children", [])
        if children:
            result.extend(flatten_stages(children, depth + 1))
    return result


async def sync_processes(
    client: LegislationClient,
    term: int,
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Sync legislative processes for a term."""
    logger.info("Syncing processes for term {}...", term)

    existing = get_existing_ids(conn, "process", term)

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

    logger.info("Found {} processes", len(all_processes))

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
        details = await safe_request(client.process(term, proc["number"]), None)
        if details is None:
            logger.debug("Skipping process {} (API unavailable)", proc["number"])
            await asyncio.sleep(0.05)
            continue

        stages = details.get("stages", [])
        for idx, stage in enumerate(flatten_stages(stages)):
            stage_id = f"{pid}_{idx}"

            # Try to find voting link
            voting_id = None
            if stage.get("voting"):
                v = stage["voting"]
                voting_id = f"{term}_{v.get('sitting')}_{v.get('votingNumber')}"

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

        await asyncio.sleep(0.05)

    # Insert processes
    if process_rows:
        process_df = pl.DataFrame(process_rows)
        conn.register("process_df", process_df)
        conn.execute("INSERT INTO process SELECT * FROM process_df")
        conn.unregister("process_df")
        logger.info("Processes: +{} new", len(process_rows))

    # Insert stages
    if stage_rows:
        stage_df = pl.DataFrame(stage_rows)
        conn.register("stage_df", stage_df)
        conn.execute("INSERT INTO process_stage SELECT * FROM stage_df")
        conn.unregister("stage_df")
        logger.info("Process stages: +{} new", len(stage_rows))
