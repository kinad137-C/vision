"""Analytics - single entry point for all calculations."""
from collections import defaultdict
from dataclasses import dataclass

from loguru import logger

from src.db import Repository
from src import formulas


@dataclass
class PowerIndex:
    party: str
    seats: int
    seats_pct: float
    shapley: float
    banzhaf: float


@dataclass
class Cohesion:
    party: str
    rice_index: float
    votings: int


class Analytics:
    """All analytics via single interface."""
    
    def __init__(self, repo: Repository = None):
        self._repo = repo or Repository()
        logger.debug("Analytics initialized")
    
    def power_indices(self, term_id: int) -> list[PowerIndex]:
        """Power indices for all parties."""
        seats = self._repo.get_parties(term_id)
        total = sum(seats.values())
        
        if not total:
            logger.warning(f"No data for term {term_id}")
            return []
        
        quota = total // 2 + 1
        ss = formulas.shapley_shubik(seats, quota)
        bz = formulas.banzhaf(seats, quota)
        
        logger.info(f"Calculated power indices for {len(seats)} parties")
        return sorted([
            PowerIndex(p, s, round(s / total * 100, 1), round(ss[p] * 100, 1), round(bz[p] * 100, 1))
            for p, s in seats.items()
        ], key=lambda x: x.shapley, reverse=True)
    
    def cohesion(self, term_id: int) -> list[Cohesion]:
        """Rice index per party."""
        by_party: dict[str, list] = defaultdict(list)
        for d in self._repo.get_party_decisions(term_id):
            by_party[d["party"]].append((d["yes"], d["no"]))
        
        logger.info(f"Calculated cohesion for {len(by_party)} parties")
        return sorted([
            Cohesion(p, round(formulas.average_rice(v), 3), len(v))
            for p, v in by_party.items()
        ], key=lambda x: x.rice_index, reverse=True)
    
    def markov(self, term_id: int) -> list[dict]:
        """Markov transitions per party."""
        sequences = self._repo.get_vote_sequences(term_id)
        
        result = []
        for p, seq in sequences.items():
            if len(seq) < 10:
                continue
            trans = formulas.transition_matrix(seq)
            result.append({
                "party": p,
                "momentum": round(formulas.momentum(trans), 3),
                "volatility": round(formulas.volatility(trans), 3),
            })
        
        logger.info(f"Calculated Markov for {len(result)} parties")
        return sorted(result, key=lambda x: x["momentum"], reverse=True)
    
    def coalitions(self, term_id: int) -> list[dict]:
        """Minimum winning coalitions."""
        seats = self._repo.get_parties(term_id)
        total = sum(seats.values())
        
        if not total:
            return []
        
        result = [
            {"parties": list(c[0]), "seats": c[1], "surplus": c[2]}
            for c in formulas.min_coalitions(seats, total // 2 + 1)[:10]
        ]
        logger.info(f"Found {len(result)} coalitions")
        return result
    
    def agreement_matrix(self, term_id: int) -> dict[str, dict[str, float]]:
        """Pairwise party agreement rates."""
        parties = list(self._repo.get_parties(term_id).keys())
        decisions = self._repo.get_party_decisions(term_id)
        
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
                
                both = [(a, b) for a, b in zip(party_votes[p1], party_votes[p2]) 
                        if a is not None and b is not None]
                
                if both:
                    result[p1][p2] = round(sum(a == b for a, b in both) / len(both) * 100, 1)
                else:
                    result[p1][p2] = 0.0
        
        logger.info(f"Calculated agreement matrix {len(parties)}x{len(parties)}")
        return result
