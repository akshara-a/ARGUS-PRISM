"""Live Web Search Provider backed by SerpApi REST endpoints (Strategy Pattern)."""

import logging
import os
import time
from typing import List, Optional
import requests
from dotenv import load_dotenv

from argus.models.domain import CostGuardTelemetry, RawDocument
from argus.providers.base import ISearchProvider
from argus.providers.cache import SerpApiCache
from argus.providers.mock_provider import MockSearchStrategy
from argus.providers.serpapi_adapter import SerpApiAdapter

load_dotenv()
logger = logging.getLogger(__name__)

SERPAPI_DEFAULT_ENDPOINT = os.getenv("SERPAPI_ENDPOINT", "")


class WebSearchStrategy(ISearchProvider):
    """Executes live searches via SerpApi, with optional mock fallback when no key is set."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        fallback_to_mock: bool = True,
        timeout: int = 15,
        cache: Optional[SerpApiCache] = None,
        endpoint: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self.endpoint = endpoint or os.getenv("SERPAPI_ENDPOINT", SERPAPI_DEFAULT_ENDPOINT)
        self.fallback_to_mock = fallback_to_mock
        self.timeout = timeout
        self.mock_provider = MockSearchStrategy() if fallback_to_mock else None
        self.cache = cache or SerpApiCache()
        self.total_live_calls = 0

    @property
    def provider_name(self) -> str:
        return "WebSearchStrategy (SerpApi)"

    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        return self.cache.get_telemetry()

    def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Query SerpApi REST API with Cost-Guard caching and RawDocument normalization."""
        # 1. Tiered Cache Lookup
        cached_docs = self.cache.get(query=query, engine=engine, num=num_results, vector_type=vector_type)
        if cached_docs is not None:
            logger.info("Cost-Guard Cache HIT for query '%s' [%s]", query, engine)
            return cached_docs

        if not self.api_key or self.api_key.startswith("your_serpapi"):
            if self.fallback_to_mock and self.mock_provider:
                logger.info("SERPAPI_API_KEY not configured. Falling back to deterministic MockSearchStrategy.")
                return self.mock_provider.search(
                    query=query, engine=engine, num_results=num_results, vector_type=vector_type
                )
            raise ValueError("SERPAPI_API_KEY environment variable is required for live SerpApi search.")

        params = {
            "q": query,
            "engine": engine,
            "num": num_results,
            "api_key": self.api_key,
        }

        start_time = time.time()
        try:
            self.total_live_calls += 1
            response = requests.get(self.endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            elapsed_ms = (time.time() - start_time) * 1000.0
            docs = SerpApiAdapter.normalize_serpapi_response(
                payload, search_vector=vector_type, engine=engine
            )
            # Store into memory & SQLite cache
            self.cache.put(
                query=query,
                documents=docs,
                engine=engine,
                num=num_results,
                fetch_latency_ms=elapsed_ms,
                vector_type=vector_type,
            )
            return docs
        except Exception as e:
            logger.warning("SerpApi request failed for query '%s': %s", query, str(e))
            if self.fallback_to_mock and self.mock_provider:
                logger.info("Falling back to MockSearchStrategy following API error.")
                return self.mock_provider.search(
                    query=query, engine=engine, num_results=num_results, vector_type=vector_type
                )
            raise
