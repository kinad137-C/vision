"""Data collection from Sejm API with incremental sync."""
import asyncio
from datetime import datetime

import duckdb
import httpx
import polars as pl
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.settings import DB_PATH, API_BASE_URL, API_TIMEOUT, BATCH_DELAY
from src.db import init_tables


class SejmClient:
    """Async HTTP client with rate limiting and exponential backoff."""
    
    def __init__(self, max_concurrent: int = 20):
        self._client = None
        self._sem = asyncio.Semaphore(max_concurrent)
        self._request_count = 0
        logger.info(f"Client: max_concurrent={max_concurrent}")
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=API_TIMEOUT,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        return self
    
    async def __aexit__(self, *_):
        logger.info(f"Total API requests: {self._request_count}")
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _get(self, path: str):
        async with self._sem:
            await asyncio.sleep(0.05)
            self._request_count += 1
            resp = await self._client.get(f"{API_BASE_URL}/{path}")
            resp.raise_for_status()
            return resp.json()
    
    async def terms(self): return await self._get("term")
    async def mps(self, term: int): return await self._get(f"term{term}/MP")
    async def clubs(self, term: int): return await self._get(f"term{term}/clubs")
    async def proceedings(self, term: int): return await self._get(f"term{term}/proceedings")
    async def votings(self, term: int, sitting: int): return await self._get(f"term{term}/votings/{sitting}")
    async def voting(self, term: int, sitting: int, voting: int): return await self._get(f"term{term}/votings/{sitting}/{voting}")


async def _safe(coro, default):
    """Execute coroutine, return default on failure."""
    try:
        result = await coro
        return (default[0], result) if isinstance(default, tuple) else result
    except Exception as e:
        logger.warning(f"Failed: {e}")
        return default


async def _fetch_votes(client: SejmClient, term: int, sitting: int, voting: int, vid: str) -> list:
    """Fetch individual votes for a voting."""
    try:
        details = await client.voting(term, sitting, voting)
        return [
            (f"{vid}_{v.get('MP')}", vid, f"{term}_{v.get('MP')}", v.get("club"), v.get("vote", "NO_VOTE"))
            for v in details.get("votes", [])
        ]
    except Exception as e:
        logger.warning(f"Failed votes {vid}: {e}")
        return []


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
        rows = conn.execute("""
            SELECT DISTINCT voting_id FROM vote WHERE voting_id LIKE ?
        """, [f"{term}_%"]).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def validate_term(conn: duckdb.DuckDBPyConnection, term: int) -> dict:
    """Validate data integrity for a term."""
    issues = []
    stats = {}
    
    mp_count = conn.execute("SELECT COUNT(*) FROM mp WHERE term_id = ?", [term]).fetchone()[0]
    stats["mps"] = mp_count
    if mp_count == 0:
        issues.append("No MPs found")
    
    voting_check = conn.execute("""
        SELECT 
            COUNT(*) as total_votings,
            SUM(CASE WHEN yes + no + abstain + not_voting = 0 THEN 1 ELSE 0 END) as empty_votings
        FROM voting WHERE term_id = ?
    """, [term]).fetchone()
    stats["votings"] = voting_check[0] or 0
    empty_votings = voting_check[1] or 0
    if empty_votings > 0:
        issues.append(f"{empty_votings} votings have zero votes in summary")
    
    vote_check = conn.execute("""
        SELECT 
            v.id,
            v.yes + v.no + v.abstain + v.not_voting as expected,
            COUNT(vote.id) as actual
        FROM voting v
        LEFT JOIN vote ON vote.voting_id = v.id
        WHERE v.term_id = ?
        GROUP BY v.id, expected
        HAVING actual = 0 AND expected > 0
        LIMIT 10
    """, [term]).fetchall()
    stats["votings_missing_votes"] = len(vote_check)
    if vote_check:
        issues.append(f"{len(vote_check)}+ votings have no individual votes loaded")
    
    orphan_check = conn.execute("""
        SELECT COUNT(*) FROM vote 
        JOIN voting v ON vote.voting_id = v.id
        WHERE v.term_id = ?
        AND vote.mp_id NOT IN (SELECT id FROM mp WHERE term_id = ?)
    """, [term, term]).fetchone()[0]
    stats["orphan_votes"] = orphan_check
    if orphan_check > 0:
        issues.append(f"{orphan_check} votes reference non-existent MPs")
    
    vote_count = conn.execute("""
        SELECT COUNT(*) FROM vote 
        JOIN voting v ON vote.voting_id = v.id
        WHERE v.term_id = ?
    """, [term]).fetchone()[0]
    stats["votes"] = vote_count
    
    coverage_check = conn.execute("""
        SELECT 
            COUNT(DISTINCT v.id) as total,
            COUNT(DISTINCT CASE WHEN vote.id IS NOT NULL THEN v.id END) as with_votes
        FROM voting v
        LEFT JOIN vote ON vote.voting_id = v.id
        WHERE v.term_id = ?
    """, [term]).fetchone()
    stats["coverage_pct"] = round(coverage_check[1] / coverage_check[0] * 100, 1) if coverage_check[0] else 0
    
    return {
        "term": term,
        "valid": len(issues) == 0,
        "stats": stats,
        "issues": issues,
    }


async def sync_term(client: SejmClient, term: int, conn: duckdb.DuckDBPyConnection, batch_size: int = 50, force: bool = False):
    """Sync data for a term incrementally."""
    logger.info(f"Syncing term {term}" + (" [FORCE]" if force else " [INCREMENTAL]"))
    
    clubs = await _safe(client.clubs(term), [])
    mps = await _safe(client.mps(term), [])
    proceedings = await _safe(client.proceedings(term), [])
    
    if not mps:
        logger.error(f"Failed to fetch MPs for term {term}, skipping")
        return
    
    if clubs:
        df = pl.DataFrame([
            {"id": f"{term}_{c['id']}", "term_id": term, "abbr": c["id"],
             "name": c["name"], "members_count": c.get("membersCount", 0)}
            for c in clubs
        ])
        conn.execute("DELETE FROM club WHERE term_id = ?", [term])
        conn.execute("INSERT INTO club SELECT * FROM df")
        logger.info(f"Clubs: {len(clubs)}")
    
    df = pl.DataFrame([
        {"id": f"{term}_{m['id']}", "term_id": term, "mp_id": m["id"],
         "first_name": m["firstName"], "last_name": m["lastName"],
         "club": m.get("club"), "district": m.get("districtName"), "active": m.get("active", True)}
        for m in mps
    ])
    conn.execute("DELETE FROM mp WHERE term_id = ?", [term])
    conn.execute("INSERT INTO mp SELECT * FROM df")
    logger.info(f"MPs: {len(mps)}")
    
    sittings = [p for p in proceedings if p["number"] != 0]
    existing_sittings = _get_existing_ids(conn, "sitting", term)
    new_sittings = [p for p in sittings if f"{term}_{p['number']}" not in existing_sittings]
    
    if new_sittings:
        df = pl.DataFrame([
            {"id": f"{term}_{p['number']}", "term_id": term, "number": p["number"], "dates": str(p.get("dates", []))}
            for p in new_sittings
        ])
        conn.execute("INSERT INTO sitting SELECT * FROM df")
        logger.info(f"Sittings: +{len(new_sittings)} new (total {len(sittings)})")
    else:
        logger.info(f"Sittings: {len(sittings)} (all exist)")
    
    existing_votings = _get_existing_ids(conn, "voting", term)
    existing_votes = _get_existing_voting_ids(conn, term) if not force else set()
    
    logger.info(f"Checking {len(sittings)} sittings for new votings...")
    new_votings, voting_ids_to_fetch = [], []
    
    for p in sittings:
        votings = await _safe(client.votings(term, p["number"]), [])
        for v in votings:
            vid = f"{term}_{p['number']}_{v['votingNumber']}"
            
            if vid in existing_votings and not force:
                if vid not in existing_votes:
                    voting_ids_to_fetch.append((p["number"], v["votingNumber"], vid))
                continue
            
            voting_ids_to_fetch.append((p["number"], v["votingNumber"], vid))
            new_votings.append({
                "id": vid, "sitting_id": f"{term}_{p['number']}", "term_id": term,
                "sitting_num": p["number"], "voting_num": v["votingNumber"],
                "date": datetime.fromisoformat(v["date"]), "title": v["title"], "topic": v.get("topic"),
                "yes": v.get("yes", 0), "no": v.get("no", 0),
                "abstain": v.get("abstain", 0), "not_voting": v.get("notParticipating", 0),
            })
        await asyncio.sleep(0.05)
    
    if new_votings:
        df = pl.DataFrame(new_votings)
        conn.execute("INSERT INTO voting SELECT * FROM df")
        logger.info(f"Votings: +{len(new_votings)} new")
    
    if not voting_ids_to_fetch:
        logger.info(f"Votes: all {len(existing_votes)} already loaded")
        result = validate_term(conn, term)
        if result["valid"]:
            logger.info(f"Validation OK: {result['stats']}")
        else:
            logger.warning(f"Validation issues: {result['issues']}")
        return
    
    logger.info(f"Fetching votes for {len(voting_ids_to_fetch)} votings (skipping {len(existing_votes)} loaded)...")
    all_votes = []
    total_batches = (len(voting_ids_to_fetch) + batch_size - 1) // batch_size
    
    for i in range(0, len(voting_ids_to_fetch), batch_size):
        batch = voting_ids_to_fetch[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"Batch {batch_num}/{total_batches}")
        
        results = await asyncio.gather(*[
            _fetch_votes(client, term, s, v, vid) for s, v, vid in batch
        ])
        
        batch_votes = []
        for votes in results:
            batch_votes.extend(votes)
        
        if batch_votes:
            df = pl.DataFrame(batch_votes, schema=["id", "voting_id", "mp_id", "club", "vote"], orient="row")
            conn.execute("INSERT INTO vote SELECT * FROM df")
            all_votes.extend(batch_votes)
            logger.debug(f"Batch {batch_num}: inserted {len(batch_votes)} votes")
        
        if i + batch_size < len(voting_ids_to_fetch):
            await asyncio.sleep(BATCH_DELAY)
    
    logger.info(f"Term {term}: {len(mps)} MPs, {len(clubs)} clubs, +{len(new_votings)} votings, +{len(all_votes)} votes")
    
    result = validate_term(conn, term)
    if result["valid"]:
        logger.info(f"Validation OK: coverage={result['stats']['coverage_pct']}%")
    else:
        logger.warning(f"Validation issues: {result['issues']}")


def sync_all(terms: list[int] = None, max_concurrent: int = 20, batch_size: int = 50, force: bool = False):
    """Main sync entry point."""
    asyncio.run(_sync_async(terms, max_concurrent, batch_size, force))


async def _sync_async(terms: list[int], max_concurrent: int, batch_size: int, force: bool):
    conn = duckdb.connect(DB_PATH)
    init_tables(conn)
    
    async with SejmClient(max_concurrent=max_concurrent) as client:
        api_terms = await client.terms()
        
        df = pl.DataFrame([
            {"id": t["num"], "from_date": t["from"], "to_date": t.get("to"), "current": t.get("current", False)}
            for t in api_terms
        ])
        conn.execute("DELETE FROM term")
        conn.execute("INSERT INTO term SELECT * FROM df")
        
        to_sync = [t for t in api_terms if terms is None or t["num"] in terms]
        for t in to_sync:
            try:
                await sync_term(client, t["num"], conn, batch_size, force)
            except Exception as e:
                logger.error(f"Failed to sync term {t['num']}: {e}")
                continue
    
    conn.close()
    logger.info("Sync complete!")
