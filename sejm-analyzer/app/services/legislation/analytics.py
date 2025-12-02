"""Legislation analytics service."""

from dataclasses import dataclass

import numpy as np
from loguru import logger

from app.repositories.legislation import ProcessRepository
from app.services.legislation.topic_modeling import TopicModeling


@dataclass
class PredictionResult:
    """Prediction result for a process."""

    process_id: str
    predicted_pass: bool
    probability: float
    top_features: list[tuple[str, float]]


class LegislationAnalytics:
    """Legislation analytics with pass prediction."""

    def __init__(self, repo: ProcessRepository):
        self.repo = repo
        self.topic_model = TopicModeling(repo)
        self._weights: np.ndarray | None = None
        self._feature_names: list[str] = []
        self._doc_type_map: dict[str, int] = {}
        self._topic_map: dict[str, int] = {}
        self._base_rates: dict[str, float] = {}
        self._bias: float = 0.0

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

        # Base rates
        features.append(self._base_rates.get(doc_type, 0.5))
        features.append(self._base_rates.get(f"topic_{topic}", 0.5))

        return np.array(features)

    def train(self, term_id: int, learning_rate: float = 0.1, iterations: int = 1000) -> None:
        """Train the prediction model on historical data."""
        processes = self.repo.get_processes(term_id)

        if not processes:
            logger.warning("No processes for training (term {})", term_id)
            return

        labeled = [p for p in processes if p.get("passed") is not None]
        logger.info("Training on {} labeled processes", len(labeled))

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

        self._feature_names = list(self._doc_type_map.keys()) + [f"topic_{t}" for t in self._topic_map]
        self._feature_names += ["base_rate_doctype", "base_rate_topic"]

        # Initialize and train
        n_features = X.shape[1]
        self._weights = np.zeros(n_features)
        self._bias = 0.0

        for i in range(iterations):
            z = X @ self._weights + self._bias
            predictions = self._sigmoid(z)

            error = predictions - y
            dw = (X.T @ error) / len(y)
            db = np.mean(error)

            self._weights -= learning_rate * dw
            self._bias -= learning_rate * db

            if i % 200 == 0:
                loss = -np.mean(y * np.log(predictions + 1e-10) + (1 - y) * np.log(1 - predictions + 1e-10))
                acc = np.mean((predictions > 0.5) == y)
                logger.debug("Iteration {}: loss={:.4f}, accuracy={:.2f}%", i, loss, acc * 100)

        final_pred = self._sigmoid(X @ self._weights + self._bias)
        accuracy = np.mean((final_pred > 0.5) == y)
        logger.info("Training complete. Accuracy: {:.2f}%", accuracy * 100)

    def predict(self, process: dict) -> PredictionResult:
        """Predict if a process will pass."""
        if self._weights is None:
            raise ValueError("Model not trained. Call train() first.")

        features = self._extract_features(process)
        prob = self._sigmoid(features @ self._weights + self._bias)

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

    def get_topic_stats(self, term_id: int) -> dict:
        """Get topic statistics."""
        return self.topic_model.get_topic_stats(term_id)

    def get_processes_data(self, term_id: int) -> dict:
        """Get processes data for a term."""
        processes = self.repo.get_processes(term_id)
        process_stats = self.repo.get_process_stats(term_id)
        voting_links = self.repo.get_process_voting_links(term_id)
        return {
            "processes": processes,
            "stats": process_stats,
            "voting_links": voting_links,
        }

    def evaluate(self, term_id: int) -> dict:
        """Evaluate model on data."""
        processes = self.repo.get_processes(term_id)
        labeled = [p for p in processes if p.get("passed") is not None]

        if not labeled or self._weights is None:
            return {"error": "No data or model not trained"}

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
            "total_samples": len(labeled),
        }
