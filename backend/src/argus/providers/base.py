"""Base abstract interface for search providers (Strategy Pattern)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from argus.models.domain import CostGuardTelemetry, RawDocument


class ISearchProvider(ABC):
    """Abstract search provider interface."""

    @abstractmethod
    def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Execute a search query and return normalized RawDocument domain entities."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider implementation."""
        pass

    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        """Return dual-tier cache and Cost-Guard telemetry if supported."""
        return None
