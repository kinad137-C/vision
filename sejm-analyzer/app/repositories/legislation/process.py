"""Process repository - access to legislative processes data."""

from app.repositories.base import BaseRepository


class ProcessRepository(BaseRepository):
    """Repository for legislative process data access."""

    def get_processes(self, term_id: int, passed_only: bool = False) -> list[dict]:
        """Get legislative processes for a term."""

        def fetch():
            query = """
                SELECT id, number, title, document_type, passed,
                       process_start_date, closure_date, title_final
                FROM process
                WHERE term_id = ?
            """
            if passed_only:
                query += " AND passed = TRUE"
            query += " ORDER BY process_start_date DESC"

            rows = self.fetchall(query, [term_id])
            return [
                {
                    "id": r[0],
                    "number": r[1],
                    "title": r[2],
                    "document_type": r[3],
                    "passed": r[4],
                    "process_start_date": r[5],
                    "closure_date": r[6],
                    "title_final": r[7],
                }
                for r in rows
            ]

        key = f"processes_{term_id}_{'passed' if passed_only else 'all'}"
        return self._cached(key, fetch)

    def get_process_voting_links(self, term_id: int) -> list[dict]:
        """Get links between processes and votings."""

        def fetch():
            rows = self.fetchall(
                """
                SELECT ps.process_id, ps.voting_id, ps.stage_name, ps.decision,
                       p.number, p.title, p.passed
                FROM process_stage ps
                JOIN process p ON ps.process_id = p.id
                WHERE p.term_id = ? AND ps.voting_id IS NOT NULL
                """,
                [term_id],
            )
            return [
                {
                    "process_id": r[0],
                    "voting_id": r[1],
                    "stage_name": r[2],
                    "decision": r[3],
                    "process_number": r[4],
                    "process_title": r[5],
                    "passed": r[6],
                }
                for r in rows
            ]

        return self._cached(f"process_votings_{term_id}", fetch)

    def get_process_stats(self, term_id: int) -> dict:
        """Get aggregate statistics for processes."""

        def fetch():
            basic = self.fetchone(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN passed = false THEN 1 ELSE 0 END) as rejected
                FROM process WHERE term_id = ?
                """,
                [term_id],
            )

            by_type = self.fetchall(
                """
                SELECT document_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed
                FROM process WHERE term_id = ?
                GROUP BY document_type
                ORDER BY COUNT(*) DESC
                """,
                [term_id],
            )

            return {
                "total": basic[0] or 0,
                "passed": basic[1] or 0,
                "rejected": basic[2] or 0,
                "by_type": [{"type": r[0], "total": r[1], "passed": r[2]} for r in by_type],
            }

        return self._cached(f"process_stats_{term_id}", fetch)
