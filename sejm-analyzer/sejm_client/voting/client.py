"""Voting API client."""

from sejm_client.base import BaseClient


class VotingClient(BaseClient):
    """Client for voting Sejm API endpoints."""

    async def votings(self, term: int, sitting: int) -> list[dict]:
        """GET /sejm/term{term}/votings/{sitting} - votings in a sitting."""
        return await self._get(f"term{term}/votings/{sitting}")

    async def voting(self, term: int, sitting: int, voting: int) -> dict:
        """GET /sejm/term{term}/votings/{sitting}/{voting} - voting details."""
        return await self._get(f"term{term}/votings/{sitting}/{voting}")
