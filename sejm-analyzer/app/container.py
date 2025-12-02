"""Dependency Injection container - initialized at app startup."""

from app.repositories.common.cache import CacheRepository
from app.repositories.core.mp import MpRepository
from app.repositories.legislation.process import ProcessRepository
from app.repositories.voting.voting import VotingRepository
from app.services.dashboard.service import DashboardService
from app.services.legislation.analytics import LegislationAnalytics
from app.services.legislation.topic_modeling import TopicModeling
from app.services.voting.analytics import VotingAnalytics


class Container:
    """Application DI container - holds all singleton instances."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self) -> None:
        """Initialize all dependencies. Call once at app startup."""
        if self._initialized:
            return

        # Repositories (singletons)
        self._mp_repo = MpRepository()
        self._voting_repo = VotingRepository()
        self._process_repo = ProcessRepository()
        self._cache_repo = CacheRepository(read_only=False)

        # Services (with injected repos)
        self.voting_analytics = VotingAnalytics(
            voting_repo=self._voting_repo,
            mp_repo=self._mp_repo,
            cache_repo=self._cache_repo,
        )

        self.topic_modeling = TopicModeling(
            repo=self._process_repo,
        )

        self.legislation_analytics = LegislationAnalytics(
            repo=self._process_repo,
        )

        self.dashboard = DashboardService(
            mp_repo=self._mp_repo,
            voting_repo=self._voting_repo,
            process_repo=self._process_repo,
        )

        self._initialized = True


# Global container instance
container = Container()
