"""Base HTTP client with retry logic."""

import asyncio

import httpx
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

# Default settings
API_BASE_URL = "https://api.sejm.gov.pl/sejm"
API_TIMEOUT = 60


def set_api_config(base_url: str, timeout: int) -> None:
    """Set API configuration."""
    global API_BASE_URL, API_TIMEOUT
    API_BASE_URL = base_url
    API_TIMEOUT = timeout


def _is_retryable_error(exc: BaseException) -> bool:
    """Check if exception is retryable (network errors + 5xx server errors)."""
    if isinstance(exc, (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


class BaseClient:
    """Base async HTTP client with rate limiting and exponential backoff."""

    def __init__(self, max_concurrent: int = 20):
        self._client: httpx.AsyncClient | None = None
        self._sem = asyncio.Semaphore(max_concurrent)
        self._request_count = 0
        logger.info("{}: max_concurrent={}", self.__class__.__name__, max_concurrent)

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=API_TIMEOUT,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        return self

    async def __aexit__(self, *_):
        logger.info("Total API requests: {}", self._request_count)
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=_is_retryable_error,
    )
    async def _get(self, path: str) -> dict | list:
        """GET request with retry logic."""
        async with self._sem:
            await asyncio.sleep(0.05)
            self._request_count += 1
            resp = await self._client.get(f"{API_BASE_URL}/{path}")
            resp.raise_for_status()
            return resp.json()


async def safe_request(coro, default=None):
    """Execute coroutine, return default on failure."""
    try:
        return await coro
    except Exception as e:
        logger.warning("Request failed: {}", e)
        return default if default is not None else []
