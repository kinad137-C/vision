"""Core API client - terms, MPs, clubs, proceedings."""

from sejm_client.base import BaseClient


class CoreClient(BaseClient):
    """Client for core Sejm API endpoints."""

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
