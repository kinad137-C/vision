"""
Topic Modeling and Prediction for Legislative Processes.

Mathematical analysis without heavy ML dependencies.
Uses TF-IDF for topic extraction and Logistic Regression for prediction.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from loguru import logger

from src.repository import Repository


@dataclass
class TopicCluster:
    """A topic cluster with keywords and processes."""

    topic_id: int
    name: str
    keywords: list[str]
    process_count: int
    pass_rate: float
    example_titles: list[str]


@dataclass
class PredictionResult:
    """Prediction result for a process."""

    process_id: str
    predicted_pass: bool
    probability: float
    top_features: list[tuple[str, float]]


class TopicModeling:
    """Extract topics from legislative process titles using keyword analysis."""

    # Polish stopwords (common words to ignore)
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

    def __init__(self, repo: Repository):
        self.repo = repo
        self._idf: dict[str, float] = {}
        self._vocab: list[str] = []

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """Extract keywords from text using simple tokenization."""
        # Normalize and tokenize
        text = text.lower()
        words = re.findall(r"[a-ząćęłńóśźż]+", text)

        # Filter stopwords and short words
        words = [w for w in words if w not in self.STOPWORDS and len(w) > 3]

        # Return most common
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
            logger.warning(f"No processes for term {term_id}")
            return []

        # Group by topic
        topic_groups: dict[str, list] = defaultdict(list)
        for p in processes:
            topic, confidence = self.detect_topic(p["title"])
            topic_groups[topic].append(p)

        # Build clusters
        clusters = []
        for i, (topic, procs) in enumerate(sorted(topic_groups.items(), key=lambda x: -len(x[1]))):
            passed = sum(1 for p in procs if p.get("passed"))
            pass_rate = passed / len(procs) if procs else 0

            # Extract common keywords from this topic
            all_keywords = []
            for p in procs[:50]:  # Sample
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

        logger.info(f"Found {len(clusters)} topic clusters for term {term_id}")
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


class PassPrediction:
    """
    Predict if a legislative process will pass.

    Uses logistic regression with features:
    - document_type (one-hot encoded)
    - topic (from TopicModeling)
    - historical pass rate for similar processes
    """

    def __init__(self, repo: Repository):
        self.repo = repo
        self.topic_model = TopicModeling(repo)
        self._weights: np.ndarray | None = None
        self._feature_names: list[str] = []
        self._doc_type_map: dict[str, int] = {}
        self._topic_map: dict[str, int] = {}
        self._base_rates: dict[str, float] = {}

    def _sigmoid(self, z: np.ndarray) -> np.ndarray:
        """Sigmoid activation function."""
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def _extract_features(self, process: dict) -> np.ndarray:
        """Extract feature vector from a process."""
        features = []

        # Document type one-hot
        doc_type = process.get("document_type", "unknown")
        for dt in self._doc_type_map:
            features.append(1.0 if doc_type == dt else 0.0)

        # Topic one-hot
        topic, _ = self.topic_model.detect_topic(process.get("title", ""))
        for t in self._topic_map:
            features.append(1.0 if topic == t else 0.0)

        # Base rate for this doc type
        features.append(self._base_rates.get(doc_type, 0.5))

        # Base rate for this topic
        features.append(self._base_rates.get(f"topic_{topic}", 0.5))

        return np.array(features)

    def train(self, term_id: int, learning_rate: float = 0.1, iterations: int = 1000):
        """Train the prediction model on historical data."""
        processes = self.repo.get_processes(term_id)

        if not processes:
            logger.warning(f"No processes for training (term {term_id})")
            return

        # Filter processes with known outcome
        labeled = [p for p in processes if p.get("passed") is not None]
        logger.info(f"Training on {len(labeled)} labeled processes")

        # Build vocabulary
        doc_types = sorted({p.get("document_type", "unknown") for p in labeled})
        self._doc_type_map = {dt: i for i, dt in enumerate(doc_types)}

        topics = sorted({self.topic_model.detect_topic(p["title"])[0] for p in labeled})
        self._topic_map = {t: i for i, t in enumerate(topics)}

        # Compute base rates
        for dt in doc_types:
            subset = [p for p in labeled if p.get("document_type") == dt]
            self._base_rates[dt] = sum(1 for p in subset if p["passed"]) / len(subset) if subset else 0.5

        for topic in topics:
            subset = [p for p in labeled if self.topic_model.detect_topic(p["title"])[0] == topic]
            self._base_rates[f"topic_{topic}"] = sum(1 for p in subset if p["passed"]) / len(subset) if subset else 0.5

        # Build feature matrix
        X = np.array([self._extract_features(p) for p in labeled])
        y = np.array([1.0 if p["passed"] else 0.0 for p in labeled])

        # Feature names for interpretability
        self._feature_names = list(self._doc_type_map.keys()) + [f"topic_{t}" for t in self._topic_map]
        self._feature_names += ["base_rate_doctype", "base_rate_topic"]

        # Initialize weights
        n_features = X.shape[1]
        self._weights = np.zeros(n_features)
        bias = 0.0

        # Gradient descent
        for i in range(iterations):
            z = X @ self._weights + bias
            predictions = self._sigmoid(z)

            # Compute gradients
            error = predictions - y
            dw = (X.T @ error) / len(y)
            db = np.mean(error)

            # Update weights
            self._weights -= learning_rate * dw
            bias -= learning_rate * db

            if i % 200 == 0:
                loss = -np.mean(y * np.log(predictions + 1e-10) + (1 - y) * np.log(1 - predictions + 1e-10))
                acc = np.mean((predictions > 0.5) == y)
                logger.debug(f"Iteration {i}: loss={loss:.4f}, accuracy={acc:.2%}")

        # Final metrics
        final_pred = self._sigmoid(X @ self._weights + bias)
        accuracy = np.mean((final_pred > 0.5) == y)
        logger.info(f"Training complete. Accuracy: {accuracy:.2%}")

        self._bias = bias

    def predict(self, process: dict) -> PredictionResult:
        """Predict if a process will pass."""
        if self._weights is None:
            raise ValueError("Model not trained. Call train() first.")

        features = self._extract_features(process)
        prob = self._sigmoid(features @ self._weights + self._bias)

        # Get top contributing features
        contributions = features * self._weights
        top_indices = np.argsort(np.abs(contributions))[-5:][::-1]
        top_features = [
            (self._feature_names[i] if i < len(self._feature_names) else f"f{i}", float(contributions[i]))
            for i in top_indices
        ]

        return PredictionResult(
            process_id=process.get("id", "unknown"),
            predicted_pass=prob > 0.5,
            probability=float(prob),
            top_features=top_features,
        )

    def get_model_stats(self) -> dict:
        """Get model statistics and feature importance."""
        if self._weights is None:
            return {"error": "Model not trained"}

        # Feature importance (absolute weight)
        importance = list(zip(self._feature_names, np.abs(self._weights).tolist()))
        importance.sort(key=lambda x: -x[1])

        return {
            "n_features": len(self._feature_names),
            "feature_importance": importance[:15],
            "base_rates": self._base_rates,
            "doc_type_weights": {
                dt: float(self._weights[i]) for dt, i in self._doc_type_map.items() if i < len(self._weights)
            },
        }

    def evaluate(self, term_id: int) -> dict:
        """Evaluate model on data using cross-validation style split."""
        processes = self.repo.get_processes(term_id)
        labeled = [p for p in processes if p.get("passed") is not None]

        if not labeled or self._weights is None:
            return {"error": "No data or model not trained"}

        # Simple evaluation on all data (for demo)
        correct = 0
        true_pos = 0
        false_pos = 0
        true_neg = 0
        false_neg = 0

        for p in labeled:
            result = self.predict(p)
            actual = p["passed"]

            if result.predicted_pass == actual:
                correct += 1
                if actual:
                    true_pos += 1
                else:
                    true_neg += 1
            else:
                if result.predicted_pass:
                    false_pos += 1
                else:
                    false_neg += 1

        precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
        recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "accuracy": correct / len(labeled),
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "confusion_matrix": {
                "true_positive": true_pos,
                "false_positive": false_pos,
                "true_negative": true_neg,
                "false_negative": false_neg,
            },
            "total_samples": len(labeled),
        }
