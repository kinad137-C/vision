"""Voting analytics service."""

from collections import defaultdict
from collections.abc import Callable

from loguru import logger

from app.models.voting.entities import Cohesion, PowerIndex
from app.repositories.common import CacheRepository
from app.repositories.core import MpRepository
from app.repositories.voting import VotingRepository
from helpers import formulas


class VotingAnalytics:
    """Voting analytics with DB caching."""

    def __init__(
        self,
        voting_repo: VotingRepository,
        mp_repo: MpRepository,
        cache_repo: CacheRepository,
    ):
        self._voting = voting_repo
        self._mp = mp_repo
        self._cache = cache_repo
        logger.debug("VotingAnalytics initialized")

    def _get_cached_or_compute(self, term_id: int, key: str, compute_fn: Callable):
        """Try DB cache first, compute and save if missing."""
        cached = self._cache.get(term_id, key)
        if cached is not None:
            return cached

        result = compute_fn()
        self._cache.set(term_id, key, result)
        return result

    def power_indices(self, term_id: int) -> list[PowerIndex]:
        """Power indices for all parties."""

        def compute() -> list[dict]:
            seats = self._mp.get_parties(term_id)
            total = sum(seats.values())

            if not total:
                logger.warning("No data for term {}", term_id)
                return []

            quota = total // 2 + 1
            ss = formulas.shapley_shubik(seats, quota)
            bz = formulas.banzhaf(seats, quota)

            logger.info("Computed power indices for {} parties", len(seats))
            return [
                {
                    "party": p,
                    "seats": s,
                    "seats_pct": round(s / total * 100, 1),
                    "shapley": round(ss[p] * 100, 1),
                    "banzhaf": round(bz[p] * 100, 1),
                }
                for p, s in seats.items()
            ]

        data = self._get_cached_or_compute(term_id, "power_indices", compute)
        if not data:
            return []

        result = [PowerIndex(**d) for d in data]
        return sorted(result, key=lambda x: x.shapley, reverse=True)

    def cohesion(self, term_id: int) -> list[Cohesion]:
        """Rice index per party."""

        def compute() -> list[dict]:
            by_party: dict[str, list] = defaultdict(list)
            for d in self._voting.get_party_decisions(term_id):
                by_party[d["party"]].append((d["yes"], d["no"]))

            logger.info("Computed cohesion for {} parties", len(by_party))
            return [
                {"party": p, "rice_index": round(formulas.average_rice(v), 3), "votings": len(v)}
                for p, v in by_party.items()
            ]

        data = self._get_cached_or_compute(term_id, "cohesion", compute)
        if not data:
            return []

        result = [Cohesion(**d) for d in data]
        return sorted(result, key=lambda x: x.rice_index, reverse=True)

    def markov(self, term_id: int) -> list[dict]:
        """Markov transitions per party."""

        def compute() -> list[dict]:
            sequences = self._voting.get_vote_sequences(term_id)

            result = []
            for p, seq in sequences.items():
                if len(seq) < 10:
                    continue
                trans = formulas.transition_matrix(seq)
                result.append(
                    {
                        "party": p,
                        "momentum": round(formulas.momentum(trans), 3),
                        "volatility": round(formulas.volatility(trans), 3),
                    }
                )

            logger.info("Computed Markov for {} parties", len(result))
            return result

        return self._get_cached_or_compute(term_id, "markov", compute)

    def coalitions(self, term_id: int) -> list[dict]:
        """Minimum winning coalitions."""

        def compute() -> list[dict]:
            seats = self._mp.get_parties(term_id)
            total = sum(seats.values())

            if not total:
                return []

            result = [
                {"parties": list(c[0]), "seats": c[1], "surplus": c[2]}
                for c in formulas.min_coalitions(seats, total // 2 + 1)[:10]
            ]
            logger.info("Found {} coalitions", len(result))
            return result

        return self._get_cached_or_compute(term_id, "coalitions", compute)

    def agreement_matrix(self, term_id: int) -> dict[str, dict[str, float]]:
        """Pairwise party agreement rates."""

        def compute() -> dict[str, dict[str, float]]:
            parties = list(self._mp.get_parties(term_id).keys())
            decisions = self._voting.get_party_decisions(term_id)

            by_voting: dict[str, dict[str, bool]] = defaultdict(dict)
            for d in decisions:
                by_voting[d["voting_id"]][d["party"]] = d["decision"] == "YES"

            voting_ids = list(by_voting.keys())
            party_votes = {p: [by_voting[v].get(p) for v in voting_ids] for p in parties}

            result = {}
            for p1 in parties:
                result[p1] = {}
                for p2 in parties:
                    if p1 == p2:
                        result[p1][p2] = 100.0
                        continue

                    both = [(a, b) for a, b in zip(party_votes[p1], party_votes[p2]) if a is not None and b is not None]

                    if both:
                        result[p1][p2] = round(sum(a == b for a, b in both) / len(both) * 100, 1)
                    else:
                        result[p1][p2] = 0.0

            logger.info("Computed agreement matrix {}x{}", len(parties), len(parties))
            return result

        return self._get_cached_or_compute(term_id, "agreement_matrix", compute)

    def precompute_all(self, term_id: int) -> None:
        """Precompute and cache all analytics for a term."""
        logger.info("Precomputing all analytics for term {}...", term_id)
        self.power_indices(term_id)
        self.cohesion(term_id)
        self.markov(term_id)
        self.coalitions(term_id)
        self.agreement_matrix(term_id)
        logger.info("All analytics cached for term {}", term_id)
