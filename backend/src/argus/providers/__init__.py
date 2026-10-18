from typing import Optional
from argus.providers.base import ISearchProvider
from argus.providers.duckduckgo_search import DuckDuckGoSearchStrategy
from argus.providers.mock_provider import MockSearchStrategy
from argus.providers.serpapi_adapter import SerpApiAdapter
from argus.providers.web_search import WebSearchStrategy


def get_provider(
    provider_name: str = "mock",
    fallback_to_mock: bool = True,
    api_key: Optional[str] = None,
) -> ISearchProvider:
    """Factory creating configured search provider instance.

    Supported names: 'duckduckgo' (or 'ddg'), 'serpapi' (or 'google'), 'mock'.
    """
    p_lower = (provider_name or "").lower().strip()
    if p_lower in ("duckduckgo", "ddg"):
        return DuckDuckGoSearchStrategy(fallback_to_mock=fallback_to_mock)
    elif p_lower in ("serpapi", "google", "live"):
        return WebSearchStrategy(api_key=api_key, fallback_to_mock=fallback_to_mock)
    else:
        return MockSearchStrategy()


__all__ = [
    "ISearchProvider",
    "DuckDuckGoSearchStrategy",
    "MockSearchStrategy",
    "SerpApiAdapter",
    "WebSearchStrategy",
    "get_provider",
]

