"""Dashboard service."""

from app.repositories.core.mp import MpRepository
from app.repositories.legislation.process import ProcessRepository
from app.repositories.voting.voting import VotingRepository


class DashboardService:
    """Dashboard business logic."""

    def __init__(
        self,
        mp_repo: MpRepository,
        voting_repo: VotingRepository,
        process_repo: ProcessRepository,
    ):
        self._mp = mp_repo
        self._voting = voting_repo
        self._process = process_repo

    def get_terms(self) -> dict:
        """Get available terms with metadata."""
        term_ids = self._mp.get_terms()
        data_info = self._mp.get_terms_with_data()

        items = [
            {
                "id": t,
                "has_voting_data": t in data_info["voting"],
                "has_processes": t in data_info["processes"],
            }
            for t in term_ids
        ]

        return {
            "items": items,
            "current": max(term_ids) if term_ids else None,
        }

    def get_overview(self, term_id: int) -> dict:
        """Get dashboard overview for a term."""
        parties = self._mp.get_parties(term_id)
        parties_count = len(parties)
        total_seats = sum(parties.values())

        # Count votings
        votings = self._voting.fetchone(
            "SELECT COUNT(*) FROM voting WHERE term_id = ?",
            [term_id],
        )
        votings_count = votings[0] if votings else 0

        # Process stats
        process_stats = self._process.get_process_stats(term_id)
        processes_count = process_stats["total"]
        pass_rate = None
        if processes_count > 0:
            pass_rate = round(process_stats["passed"] / processes_count * 100, 1)

        return {
            "term_id": term_id,
            "parties_count": parties_count,
            "total_seats": total_seats,
            "votings_count": votings_count,
            "processes_count": processes_count,
            "pass_rate": pass_rate,
        }
