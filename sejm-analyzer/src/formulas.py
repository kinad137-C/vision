"""Pure math formulas - no dependencies, easily testable."""
from collections import defaultdict
from itertools import permutations, combinations
from math import factorial


def shapley_shubik(seats: dict[str, int], quota: int) -> dict[str, float]:
    """Shapley-Shubik power index."""
    parties = list(seats.keys())
    n = len(parties)
    
    if n <= 1:
        return {parties[0]: 1.0} if n == 1 else {}
    
    total = factorial(n)
    counts = {p: 0 for p in parties}
    
    for perm in permutations(parties):
        cumsum = 0
        for party in perm:
            if cumsum < quota <= cumsum + seats[party]:
                counts[party] += 1
                break
            cumsum += seats[party]
    
    return {p: c / total for p, c in counts.items()}


def banzhaf(seats: dict[str, int], quota: int) -> dict[str, float]:
    """Banzhaf power index."""
    parties = list(seats.keys())
    n = len(parties)
    
    if n <= 1:
        return {parties[0]: 1.0} if n == 1 else {}
    
    swings = {p: 0 for p in parties}
    
    for r in range(n + 1):
        for coal in combinations(parties, r):
            coal_set, coal_votes = set(coal), sum(seats[p] for p in coal)
            
            for party in parties:
                if party in coal_set:
                    if coal_votes >= quota > coal_votes - seats[party]:
                        swings[party] += 1
                elif coal_votes < quota <= coal_votes + seats[party]:
                    swings[party] += 1
    
    total = sum(swings.values()) or 1
    return {p: c / total for p, c in swings.items()}


def min_coalitions(seats: dict[str, int], quota: int, max_size: int = 5) -> list[tuple]:
    """Minimal winning coalitions. Returns [(parties, seats, surplus)]."""
    parties = list(seats.keys())
    result = []
    
    for size in range(1, min(max_size + 1, len(parties) + 1)):
        for combo in combinations(parties, size):
            total = sum(seats[p] for p in combo)
            if total >= quota and all(total - seats[p] < quota for p in combo):
                result.append((frozenset(combo), total, total - quota))
    
    largest = max(parties, key=lambda p: seats[p])
    if seats[largest] >= quota:
        others = [p for p in parties if p != largest]
        for size in range(2, min(max_size + 1, len(others) + 1)):
            for combo in combinations(others, size):
                total = sum(seats[p] for p in combo)
                if total >= quota and all(total - seats[p] < quota for p in combo):
                    result.append((frozenset(combo), total, total - quota))
    
    seen = set()
    unique = []
    for item in sorted(result, key=lambda x: (x[2], len(x[0]))):
        key = item[0]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    return unique[:15]


def rice_index(yes: int, no: int) -> float:
    """Rice cohesion: 1.0=unanimous, 0.0=50/50 split."""
    total = yes + no
    return abs(yes - no) / total if total else 0.0


def average_rice(votes: list[tuple[int, int]]) -> float:
    """Average Rice index across votings."""
    return sum(rice_index(y, n) for y, n in votes) / len(votes) if votes else 0.0


def agreement_rate(a: list[bool], b: list[bool]) -> float:
    """How often two vote the same (0-100%)."""
    if not a or len(a) != len(b):
        return 0.0
    return sum(x == y for x, y in zip(a, b)) / len(a) * 100


def transition_matrix(sequence: list[str]) -> dict[str, float]:
    """Voting transition probabilities."""
    seq = [v for v in sequence if v in ("YES", "NO")]
    
    if len(seq) < 2:
        return {"yes_to_yes": 0, "yes_to_no": 0, "no_to_yes": 0, "no_to_no": 0}
    
    counts = defaultdict(lambda: defaultdict(int))
    for i in range(len(seq) - 1):
        counts[seq[i]][seq[i + 1]] += 1
    
    def prob(f, t):
        total = sum(counts[f].values())
        return counts[f][t] / total if total else 0
    
    return {
        "yes_to_yes": prob("YES", "YES"), "yes_to_no": prob("YES", "NO"),
        "no_to_yes": prob("NO", "YES"), "no_to_no": prob("NO", "NO"),
    }


def momentum(trans: dict) -> float:
    """Tendency to repeat vote."""
    return (trans.get("yes_to_yes", 0) + trans.get("no_to_no", 0)) / 2


def volatility(trans: dict) -> float:
    """Tendency to switch vote."""
    return (trans.get("yes_to_no", 0) + trans.get("no_to_yes", 0)) / 2
