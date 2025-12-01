"""Async HTTP client for Sejm API."""

import asyncio

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.settings import API_BASE_URL, API_TIMEOUT


class SejmClient:
    """Async HTTP client with rate limiting and exponential backoff."""

    def __init__(self, max_concurrent: int = 20):
        self._client: httpx.AsyncClient | None = None
        self._sem = asyncio.Semaphore(max_concurrent)
        self._request_count = 0
        logger.info(f"SejmClient: max_concurrent={max_concurrent}")

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=API_TIMEOUT,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        return self

    async def __aexit__(self, *_):
        logger.info(f"Total API requests: {self._request_count}")
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _get(self, path: str) -> dict | list:
        """GET request with retry logic."""
        async with self._sem:
            await asyncio.sleep(0.05)  # Rate limiting
            self._request_count += 1
            resp = await self._client.get(f"{API_BASE_URL}/{path}")
            resp.raise_for_status()
            return resp.json()

    # ========== Core endpoints ==========

    async def terms(self) -> list[dict]:
        """GET /sejm/term - list of terms."""
        return await self._get("term")

    async def mps(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/MP - MPs in a term."""
        return await self._get(f"term{term}/MP")

    async def clubs(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/clubs - clubs in a term."""
        return await self._get(f"term{term}/clubs")

    async def proceedings(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/proceedings - sittings in a term."""
        return await self._get(f"term{term}/proceedings")

    async def votings(self, term: int, sitting: int) -> list[dict]:
        """GET /sejm/term{term}/votings/{sitting} - votings in a sitting."""
        return await self._get(f"term{term}/votings/{sitting}")

    async def voting(self, term: int, sitting: int, voting: int) -> dict:
        """GET /sejm/term{term}/votings/{sitting}/{voting} - voting details."""
        return await self._get(f"term{term}/votings/{sitting}/{voting}")

    # ========== Processes (NEW) ==========

    async def processes(
        self,
        term: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """GET /sejm/term{term}/processes - legislative processes."""
        return await self._get(f"term{term}/processes?limit={limit}&offset={offset}")

    async def processes_passed(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/processes/passed - passed processes."""
        return await self._get(f"term{term}/processes/passed")

    async def process(self, term: int, number: str) -> dict:
        """GET /sejm/term{term}/processes/{num} - process details."""
        return await self._get(f"term{term}/processes/{number}")

    # ========== Prints (NEW) ==========

    async def prints(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/prints - sejm prints."""
        return await self._get(f"term{term}/prints")

    async def print_details(self, term: int, number: str) -> dict:
        """GET /sejm/term{term}/prints/{num} - print details."""
        return await self._get(f"term{term}/prints/{number}")

    # ========== Committees (future) ==========

    async def committees(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/committees - committees."""
        return await self._get(f"term{term}/committees")


async def safe_request(coro, default=None):
    """Execute coroutine, return default on failure."""
    try:
        return await coro
    except Exception as e:
        logger.warning(f"Request failed: {e}")
        return default if default is not None else []
