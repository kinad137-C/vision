"""Legislation API client - processes, prints."""

from sejm_client.base import BaseClient


class LegislationClient(BaseClient):
    """Client for legislation Sejm API endpoints."""

    async def processes(self, term: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """GET /sejm/term{term}/processes - legislative processes."""
        return await self._get(f"term{term}/processes?limit={limit}&offset={offset}")

    async def processes_passed(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/processes/passed - passed processes."""
        return await self._get(f"term{term}/processes/passed")

    async def process(self, term: int, number: str) -> dict:
        """GET /sejm/term{term}/processes/{num} - process details."""
        return await self._get(f"term{term}/processes/{number}")

    async def prints(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/prints - sejm prints."""
        return await self._get(f"term{term}/prints")

    async def print_details(self, term: int, number: str) -> dict:
        """GET /sejm/term{term}/prints/{num} - print details."""
        return await self._get(f"term{term}/prints/{number}")

    async def committees(self, term: int) -> list[dict]:
        """GET /sejm/term{term}/committees - committees."""
        return await self._get(f"term{term}/committees")
