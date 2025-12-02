"""MP repository - access to MPs and parties data."""

from loguru import logger

from app.repositories.base import BaseRepository


class MpRepository(BaseRepository):
    """Repository for MP and party data access."""

    def get_terms(self) -> list[int]:
        """Get available terms with data."""
        rows = self.fetchall("SELECT DISTINCT term_id FROM mp ORDER BY term_id DESC")
        return [r[0] for r in rows]

    def get_parties(self, term_id: int) -> dict[str, int]:
        """Get party seats: {party: count}."""

        def fetch():
            rows = self.fetchall(
                """
                SELECT club, COUNT(*) FROM mp
                WHERE term_id = ? AND club IS NOT NULL
                GROUP BY club
                """,
                [term_id],
            )
            result = {r[0]: int(r[1]) for r in rows}
            logger.debug("get_parties({}): {} parties", term_id, len(result))
            return result

        return self._cached(f"parties_{term_id}", fetch)

    def get_terms_with_data(self) -> dict[str, set[int]]:
        """Get sets of terms that have voting and process data."""

        def fetch():
            # Terms with voting data
            voting_terms = self.fetchall("SELECT DISTINCT term_id FROM voting ORDER BY term_id")
            # Terms with process data
            process_terms = self.fetchall("SELECT DISTINCT term_id FROM process ORDER BY term_id")
            return {
                "voting": {r[0] for r in voting_terms},
                "processes": {r[0] for r in process_terms},
            }

        return self._cached("terms_with_data", fetch)
