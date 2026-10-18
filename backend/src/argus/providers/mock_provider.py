"""Deterministic Mock Search Provider for testing, CI/CD, and offline execution."""

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional
from argus.models.domain import CostGuardTelemetry, RawDocument
from argus.providers.base import ISearchProvider
from argus.providers.cache import SerpApiCache
from argus.providers.serpapi_adapter import SerpApiAdapter


class MockSearchStrategy(ISearchProvider):
    """Deterministic mock provider delivering predefined and synthesized SerpApi responses."""

    def __init__(
        self,
        fixtures: Optional[Dict[str, List[Dict]]] = None,
        cache: Optional[SerpApiCache] = None,
    ):
        self.fixtures = fixtures or {}
        self.search_history: List[Dict[str, str]] = []
        self.cache = cache or SerpApiCache()

    @property
    def provider_name(self) -> str:
        return "MockSearchStrategy"

    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        return self.cache.get_telemetry()

    def register_fixture(self, query_substring: str, raw_results: List[Dict]):
        """Register specific fixture results matching a query substring."""
        self.fixtures[query_substring.lower()] = raw_results

    def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Return deterministic mock search results with Cost-Guard cache accounting."""
        self.search_history.append({"query": query, "vector_type": vector_type or "unknown"})
        query_lower = query.lower()

        # 1. Hallucination Trap Test Fixture (never cached to guarantee 0 results)
        if "quantumreactjs" in query_lower or "flimflam_engine" in query_lower or "fake_lib_xyz" in query_lower:
            return []

        # Check Cost-Guard cache
        cached = self.cache.get(query, engine, num_results, vector_type=vector_type)
        if cached is not None:
            return cached

        results = self._generate_mock_results(query, query_lower, engine, num_results, vector_type)
        self.cache.put(query, results, engine=engine, num=num_results, fetch_latency_ms=1.5, vector_type=vector_type)
        return results

    def _generate_mock_results(
        self,
        query: str,
        query_lower: str,
        engine: str,
        num_results: int,
        vector_type: Optional[str],
    ) -> List[RawDocument]:
        """Internal deterministic generator for mock telemetry."""
        # Check registered fixtures
        for key, res_list in self.fixtures.items():
            if key in query_lower:
                payload = {"organic_results": res_list}
                return SerpApiAdapter.normalize_serpapi_response(
                    payload, search_vector=vector_type, engine=engine
                )

        # 2. Contradiction Catch Test Fixture (Deprecated API test)
        if "legacyapi" in query_lower or "deprecat" in query_lower and "v1" in query_lower:
            if "changelog" in query_lower or "github" in query_lower or "tie_breaker" in str(vector_type).lower():
                # Official changelog from 2026 (Tier 1, very fresh)
                return [
                    RawDocument(
                        doc_id="doc_official_changelog_2026",
                        title="Official Release Notes v3.0 - Breaking Changes",
                        snippet="LegacyAPI v1 is officially deprecated and removed as of March 2026. Developers must migrate to UnifiedAPI v2.",
                        url="https://github.com/framework/repo/releases/tag/v3.0.0",
                        source_domain="github.com",
                        publication_time="1 month ago",
                        published_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
                        search_vector=vector_type,
                        engine=engine,
                    )
                ]
            elif "skeptic" in str(vector_type).lower() or "temporal" in str(vector_type).lower():
                return [
                    RawDocument(
                        doc_id="doc_github_issue_99",
                        title="Issue #99: LegacyAPI v1 removed in latest release",
                        snippet="Upgraded to v3 and LegacyAPI v1 throws ImportError. Official migration guide confirms deprecation.",
                        url="https://github.com/framework/repo/issues/99",
                        source_domain="github.com",
                        publication_time="2 months ago",
                        published_date=datetime(2026, 8, 15, tzinfo=timezone.utc),
                        search_vector=vector_type,
                        engine=engine,
                    )
                ]
            else:
                # Legacy SEO article from 2022 claiming it works (Tier 3, 48 months old)
                return [
                    RawDocument(
                        doc_id="doc_seo_blog_2022",
                        title="Comprehensive Tutorial on LegacyAPI v1",
                        snippet="LegacyAPI v1 is the recommended production-ready solution with full backward compatibility and rock-solid stability.",
                        url="https://medium.com/tech-digest/how-to-use-legacyapi-v1",
                        source_domain="medium.com",
                        publication_time="3 years ago",
                        published_date=datetime(2022, 5, 10, tzinfo=timezone.utc),
                        search_vector=vector_type,
                        engine=engine,
                    )
                ]

        # 3. Specialized Multi-Engine Telemetry (SerpApi Google Scholar & Google News)
        if engine in ("google_scholar", "scholar"):
            q_hash = hashlib.md5(query.encode()).hexdigest()[:6]
            return [
                RawDocument(
                    doc_id=f"doc_scholar_1_{q_hash}",
                    title=f"Empirical Analysis and Formal Verification of {query.title()}",
                    snippet=f"Peer-reviewed evaluation of {query}. Demonstrates deterministic bounds, concurrency invariance, and formal correctness.",
                    url=f"https://arxiv.org/abs/2603.{q_hash}",
                    source_domain="arxiv.org",
                    publication_time="4 months ago",
                    published_date=datetime(2026, 6, 15, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id=f"doc_scholar_2_{q_hash}",
                    title=f"ACM Proceedings: Scalability Invariants in {query.title()}",
                    snippet=f"In-depth academic survey validating proposition truth values and latency guarantees for {query} against modern benchmarks.",
                    url=f"https://dl.acm.org/doi/10.1145/3688{q_hash}",
                    source_domain="dl.acm.org",
                    publication_time="6 months ago",
                    published_date=datetime(2026, 4, 10, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        if engine in ("google_news", "news"):
            q_hash = hashlib.md5(query.encode()).hexdigest()[:6]
            return [
                RawDocument(
                    doc_id=f"doc_news_1_{q_hash}",
                    title=f"Breaking Tech: Major 2026 Shift Announced for {query.title()}",
                    snippet=f"Industry report covering zero-day updates, architectural roadmaps, and breaking deprecation schedules for {query}.",
                    url=f"https://techcrunch.com/2026/10/breaking-{q_hash}",
                    source_domain="techcrunch.com",
                    publication_time="3 days ago",
                    published_date=datetime(2026, 10, 13, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id=f"doc_news_2_{q_hash}",
                    title=f"Reuters Tech Wire: Enterprise Adoption Surges for {query.title()}",
                    snippet=f"Global market survey and corporate migration bulletin detailing production deployments and compliance requirements for {query}.",
                    url=f"https://reuters.com/technology/enterprise-{q_hash}",
                    source_domain="reuters.com",
                    publication_time="1 week ago",
                    published_date=datetime(2026, 10, 9, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        # 4. Default Synthesized Developer Knowledge Base
        # Produce tiered documents according to vector_type
        if "optimistic" in str(vector_type).lower():
            return [
                RawDocument(
                    doc_id=f"doc_opt_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"{query.title()} - Official Documentation",
                    snippet=f"Official guide and architectural overview for {query}. Provides high throughput, asynchronous I/O, and type-safe interfaces.",
                    url=f"https://docs.python.org/3/library/{hashlib.md5(query.encode()).hexdigest()[:4]}.html",
                    source_domain="docs.python.org",
                    publication_time="3 months ago",
                    published_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id=f"doc_opt_2_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"GitHub - Repository: {query}",
                    snippet=f"Core repository for {query}. Actively maintained with extensive unit test coverage and high performance benchmarks.",
                    url=f"https://github.com/verified-org/{hashlib.md5(query.encode()).hexdigest()[:4]}",
                    source_domain="github.com",
                    publication_time="1 month ago",
                    published_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]
        elif "skeptic" in str(vector_type).lower():
            return [
                RawDocument(
                    doc_id=f"doc_skep_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"StackOverflow: Memory leak and bottleneck issues in {query}",
                    snippet=f"High memory consumption observed during heavy parallel workloads with {query}. Garbage collection stalls reported under extreme concurrency.",
                    url="https://stackoverflow.com/questions/9876543/memory-leak-under-load",
                    source_domain="stackoverflow.com",
                    publication_time="6 months ago",
                    published_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id=f"doc_skep_2_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"Engineering Blog: Why we hit migration pain with {query}",
                    snippet=f"Detailed postmortem on migrating to {query}. Breaking changes in serialization logic required full schema refactoring.",
                    url="https://netflixtechblog.com/lessons-learned-migration-pitfalls",
                    source_domain="netflixtechblog.com",
                    publication_time="8 months ago",
                    published_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]
        elif "temporal" in str(vector_type).lower():
            return [
                RawDocument(
                    doc_id=f"doc_temp_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"What's New in 2026: {query} Latest Release Notes",
                    snippet=f"Summary of 2026 breaking changes, deprecated flags, and new Rust-accelerated core components for {query}.",
                    url=f"https://github.com/verified-org/{hashlib.md5(query.encode()).hexdigest()[:4]}/releases",
                    source_domain="github.com",
                    publication_time="2 weeks ago",
                    published_date=datetime(2026, 9, 25, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                )
            ]
        else:
            # Fallback general query
            return [
                RawDocument(
                    doc_id=f"doc_gen_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"Engineering Overview: {query}",
                    snippet=f"Production evidence and best practices for {query}. Evaluated across multi-tenant enterprise clusters.",
                    url="https://docs.microsoft.com/en-us/azure/architecture/guide",
                    source_domain="docs.microsoft.com",
                    publication_time="4 months ago",
                    published_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                )
            ]
