import os
from typing import Optional
from argus.providers.base import ISearchProvider
from argus.providers.duckduckgo_search import DuckDuckGoSearchStrategy
from argus.providers.mock_provider import MockSearchStrategy
from argus.providers.serpapi_adapter import SerpApiAdapter
from argus.providers.web_search import WebSearchStrategy


def get_provider(
    provider_name: Optional[str] = None,
    fallback_to_mock: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> ISearchProvider:
    """Factory creating configured search provider instance.

    Supported names: 'duckduckgo' (or 'ddg'), 'serpapi' (or 'google'), 'mock'.
    """
    if fallback_to_mock is None:
        mock_env = os.getenv("ARGUS_MOCK_FALLBACK", "false").lower()
        fallback_to_mock = mock_env in ("true", "1", "yes")

    effective_api_key = api_key or os.getenv("SERPAPI_API_KEY")
    default_provider = os.getenv("DEFAULT_SEARCH_PROVIDER", "duckduckgo")
    p_lower = (provider_name or default_provider or "duckduckgo").lower().strip()

    if not provider_name and effective_api_key:
        p_lower = "serpapi"

    if p_lower in ("duckduckgo", "ddg"):
        return DuckDuckGoSearchStrategy(fallback_to_mock=fallback_to_mock)
    elif p_lower in ("serpapi", "google", "live"):
        return WebSearchStrategy(api_key=effective_api_key, fallback_to_mock=fallback_to_mock)
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

