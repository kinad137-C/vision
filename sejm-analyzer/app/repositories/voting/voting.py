"""Voting repository - access to votings and votes data."""

from collections import defaultdict

from loguru import logger

from app.repositories.base import BaseRepository


class VotingRepository(BaseRepository):
    """Repository for voting and vote data access."""

    def get_party_decisions(self, term_id: int) -> list[dict]:
        """Get party majority vote per voting."""

        def fetch():
            rows = self.fetchall(
                """
                SELECT v.voting_id, v.club,
                       SUM(CASE WHEN v.vote = 'YES' THEN 1 ELSE 0 END) as yes,
                       SUM(CASE WHEN v.vote = 'NO' THEN 1 ELSE 0 END) as no
                FROM vote v
                JOIN voting vt ON v.voting_id = vt.id
                WHERE vt.term_id = ? AND v.club IS NOT NULL
                GROUP BY v.voting_id, v.club
                """,
                [term_id],
            )
            result = [
                {
                    "voting_id": r[0],
                    "party": r[1],
                    "yes": int(r[2]),
                    "no": int(r[3]),
                    "decision": "YES" if int(r[2]) > int(r[3]) else "NO",
                }
                for r in rows
            ]
            logger.debug("get_party_decisions({}): {} decisions", term_id, len(result))
            return result

        return self._cached(f"decisions_{term_id}", fetch)

    def get_vote_sequences(self, term_id: int) -> dict[str, list[str]]:
        """Get vote sequences per party for Markov analysis."""

        def fetch():
            rows = self.fetchall(
                """
                WITH decisions AS (
                    SELECT v.club, vt.date,
                           CASE WHEN SUM(CASE WHEN v.vote='YES' THEN 1 ELSE 0 END) >
                                     SUM(CASE WHEN v.vote='NO' THEN 1 ELSE 0 END)
                                THEN 'YES' ELSE 'NO' END as decision
                    FROM vote v JOIN voting vt ON v.voting_id = vt.id
                    WHERE vt.term_id = ? AND v.club IS NOT NULL
                    GROUP BY v.club, vt.id, vt.date
                    ORDER BY v.club, vt.date
                )
                SELECT club, decision FROM decisions
                """,
                [term_id],
            )

            result = defaultdict(list)
            for party, decision in rows:
                result[party].append(decision)
            logger.debug("get_vote_sequences({}): {} parties", term_id, len(result))
            return dict(result)

        return self._cached(f"sequences_{term_id}", fetch)

    def get_voting_with_process(self, term_id: int) -> list[dict]:
        """Get votings enriched with process info."""

        def fetch():
            rows = self.fetchall(
                """
                SELECT v.id, v.title, v.topic, v.date, v.yes, v.no,
                       p.number as process_number, p.title as process_title,
                       p.document_type, p.passed
                FROM voting v
                LEFT JOIN process_stage ps ON ps.voting_id = v.id
                LEFT JOIN process p ON ps.process_id = p.id
                WHERE v.term_id = ?
                ORDER BY v.date DESC
                """,
                [term_id],
            )
            return [
                {
                    "voting_id": r[0],
                    "voting_title": r[1],
                    "topic": r[2],
                    "date": r[3],
                    "yes": r[4],
                    "no": r[5],
                    "process_number": r[6],
                    "process_title": r[7],
                    "document_type": r[8],
                    "passed": r[9],
                }
                for r in rows
            ]

        return self._cached(f"voting_process_{term_id}", fetch)
