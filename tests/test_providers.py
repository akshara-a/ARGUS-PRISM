"""Unit tests for providers and SerpApiAdapter."""

from datetime import datetime, timezone
import pytest
from argus.models.domain import CredibilityTier
from argus.providers.mock_provider import MockSearchStrategy
from argus.providers.serpapi_adapter import SerpApiAdapter


def test_serpapi_adapter_relative_dates():
    """Test relative date parsing from SerpApi strings."""
    d1 = SerpApiAdapter.parse_relative_date("2 days ago")
    assert d1 is not None

    d2 = SerpApiAdapter.parse_relative_date("3 months ago")
    assert d2 is not None

    d3 = SerpApiAdapter.parse_relative_date("2026")
    assert d3 is not None
    assert d3.year == 2026

    d4 = SerpApiAdapter.parse_relative_date("Oct 12, 2025")
    assert d4 is not None
    assert d4.year == 2025
    assert d4.month == 10


def test_serpapi_adapter_deduplication():
    """Test deduplication and normalization of raw organic results."""
    raw_payload = {
        "organic_results": [
            {
                "title": "Python Docs",
                "link": "https://docs.python.org/3/library/asyncio.html",
                "snippet": "Asyncio is a library to write concurrent code.",
                "date": "2 months ago",
            },
            {
                "title": "Duplicate Python Docs",
                "link": "https://docs.python.org/3/library/asyncio.html",
                "snippet": "Duplicate link should be deduplicated.",
            },
            {
                "title": "GitHub Repo",
                "link": "https://github.com/python/cpython",
                "snippet": "CPython source code repository.",
                "date": "1 day ago",
            },
        ]
    }

    docs = SerpApiAdapter.normalize_serpapi_response(raw_payload, search_vector="optimistic")
    assert len(docs) == 2
    assert docs[0].source_domain == "docs.python.org"
    assert docs[1].source_domain == "github.com"
    assert docs[0].doc_id != docs[1].doc_id


def test_mock_search_provider():
    """Test deterministic mock strategy responses."""
    provider = MockSearchStrategy()

    # Hallucination test query
    empty_docs = provider.search("QuantumReactJS state manager")
    assert len(empty_docs) == 0

    # Normal developer query
    opt_docs = provider.search("FastAPI async", vector_type="optimistic")
    assert len(opt_docs) > 0
    assert any("github.com" in d.url or "docs.python.org" in d.url for d in opt_docs)


def test_duckduckgo_search_provider():
    """Test DuckDuckGo provider with mock fallback safety."""
    from argus.providers import DuckDuckGoSearchStrategy

    ddg = DuckDuckGoSearchStrategy(fallback_to_mock=True)
    assert ddg.provider_name.startswith("DuckDuckGo")

    # Test search with fallback to mock
    docs = ddg.search("FastAPI async performance", num_results=3)
    assert len(docs) > 0
    assert all(hasattr(d, "url") and hasattr(d, "snippet") for d in docs)


def test_duckduckgo_zero_results_avoids_unnecessary_fallback(monkeypatch):
    """Test that 0 results from DuckDuckGo does NOT fall back to mock."""
    from argus.providers import DuckDuckGoSearchStrategy

    ddg = DuckDuckGoSearchStrategy(fallback_to_mock=True, endpoint="https://example.com/search")
    # Simulate live fetch returning 0 results
    monkeypatch.setattr(ddg, "_fetch_ddg_html", lambda *args, **kwargs: [])

    docs = ddg.search("SuperObscureNonExistentQueryXYZ12345")
    # Must return empty list, NOT mock documents
    assert docs == []


def test_adversarial_query_builder_concise_vectors():
    """Test that query builder produces concise queries avoiding keyword over-specification."""
    from argus.engine.adversarial_builder import AdversarialQueryBuilder

    builder = AdversarialQueryBuilder(current_year=2026)
    topic = "FastAPI async high-throughput performance"
    vectors = builder.build_search_vectors(topic, domain_context="Web Services")

    assert len(vectors) == 3
    for v in vectors:
        words = v.query_text.split()
        # Verify no 10+ word queries that break search engines
        assert len(words) <= 7, f"Query '{v.query_text}' exceeds 7 words ({len(words)} words)"



def test_get_provider_factory():
    """Test get_provider factory for all supported options."""
    from argus.providers import (
        DuckDuckGoSearchStrategy,
        MockSearchStrategy,
        WebSearchStrategy,
        get_provider,
    )

    p_mock = get_provider("mock")
    assert isinstance(p_mock, MockSearchStrategy)

    p_ddg = get_provider("duckduckgo")
    assert isinstance(p_ddg, DuckDuckGoSearchStrategy)

    p_ddg_short = get_provider("ddg")
    assert isinstance(p_ddg_short, DuckDuckGoSearchStrategy)

    p_serp = get_provider("serpapi")
    assert isinstance(p_serp, WebSearchStrategy)

