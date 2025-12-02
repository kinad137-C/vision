"""Topic modeling for legislative processes."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from loguru import logger

from app.repositories.legislation import ProcessRepository


@dataclass
class TopicCluster:
    """A topic cluster with keywords and processes."""

    topic_id: int
    name: str
    keywords: list[str]
    process_count: int
    pass_rate: float
    example_titles: list[str]


class TopicModeling:
    """Extract topics from legislative process titles using keyword analysis."""

    # Polish stopwords
    STOPWORDS = {
        "w",
        "i",
        "z",
        "na",
        "do",
        "o",
        "oraz",
        "przez",
        "dla",
        "ze",
        "od",
        "po",
        "się",
        "jest",
        "jako",
        "tym",
        "też",
        "już",
        "lub",
        "być",
        "sprawie",
        "projekt",
        "ustawy",
        "uchwały",
        "zmianie",
        "niektórych",
        "poselski",
        "rządowy",
        "senacki",
        "komisyjny",
        "obywatelski",
        "przedstawiony",
        "druk",
        "nr",
        "poseł",
        "posła",
        "kandydat",
    }

    # Topic patterns (regex -> topic name)
    TOPIC_PATTERNS = {
        r"podatk|podat|vat|pit|cit|akcyz": "Podatki",
        r"emerytur|rent|zus|ubezpiecz": "Emerytury i ZUS",
        r"zdrow|lecznic|szpital|medyc|lekar": "Zdrowie",
        r"edukac|szkoł|nauczyc|student|uczel": "Edukacja",
        r"wojsk|obron|żołnier|armia": "Obronność",
        r"sąd|sędzi|prokurat|sprawiedliw": "Wymiar sprawiedliwości",
        r"budżet|finansow|pieniąd": "Finanse publiczne",
        r"energi|prąd|gaz|węgl|atom": "Energetyka",
        r"rolni|wieś|agrar|żywnoś": "Rolnictwo",
        r"transport|drog|kolej|lotnisk": "Transport",
        r"środowisk|ekolog|klimat|emisj": "Środowisko",
        r"mieszkan|budowl|nieruchom": "Mieszkalnictwo",
        r"prac|zatrudni|płac|wynagrodzeni": "Prawo pracy",
        r"cudzoziemiec|migrac|uchodź|granica|wiz": "Migracja",
        r"cyber|internet|cyfryz|dane osobow": "Cyfryzacja",
        r"wybor|głosow|referendum": "Prawo wyborcze",
        r"samorząd|gmina|powiat|województw": "Samorządy",
        r"korupc|przejrzyst|lobbying": "Antykorupcja",
    }

    def __init__(self, repo: ProcessRepository):
        self.repo = repo

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """Extract keywords from text using simple tokenization."""
        text = text.lower()
        words = re.findall(r"[a-ząćęłńóśźż]+", text)
        words = [w for w in words if w not in self.STOPWORDS and len(w) > 3]
        counter = Counter(words)
        return [w for w, _ in counter.most_common(top_n)]

    def detect_topic(self, title: str) -> tuple[str, float]:
        """Detect topic from title using pattern matching."""
        title_lower = title.lower()

        for pattern, topic in self.TOPIC_PATTERNS.items():
            if re.search(pattern, title_lower):
                return topic, 1.0

        return "Inne", 0.5

    def analyze_topics(self, term_id: int) -> list[TopicCluster]:
        """Analyze all processes and cluster by topic."""
        processes = self.repo.get_processes(term_id)

        if not processes:
            logger.warning("No processes for term {}", term_id)
            return []

        # Group by topic
        topic_groups: dict[str, list] = defaultdict(list)
        for p in processes:
            topic, _ = self.detect_topic(p["title"])
            topic_groups[topic].append(p)

        # Build clusters
        clusters = []
        for i, (topic, procs) in enumerate(sorted(topic_groups.items(), key=lambda x: -len(x[1]))):
            passed = sum(1 for p in procs if p.get("passed"))
            pass_rate = passed / len(procs) if procs else 0

            # Extract common keywords from this topic
            all_keywords = []
            for p in procs[:50]:
                all_keywords.extend(self.extract_keywords(p["title"], 5))
            top_keywords = [w for w, _ in Counter(all_keywords).most_common(8)]

            clusters.append(
                TopicCluster(
                    topic_id=i,
                    name=topic,
                    keywords=top_keywords,
                    process_count=len(procs),
                    pass_rate=pass_rate,
                    example_titles=[p["title"][:80] for p in procs[:3]],
                )
            )

        logger.info("Found {} topic clusters for term {}", len(clusters), term_id)
        return clusters

    def get_topic_stats(self, term_id: int) -> dict:
        """Get topic statistics."""
        clusters = self.analyze_topics(term_id)

        return {
            "total_topics": len(clusters),
            "clusters": [
                {
                    "name": c.name,
                    "count": c.process_count,
                    "pass_rate": round(c.pass_rate * 100, 1),
                    "keywords": c.keywords[:5],
                }
                for c in clusters
            ],
            "topic_pass_rates": {c.name: c.pass_rate for c in clusters},
        }
