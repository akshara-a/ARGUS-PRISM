"""Deterministic Mock Search Provider for testing, CI/CD, and offline execution."""

import hashlib
from datetime import datetime, timedelta, timezone
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

        fresh_date = datetime.now(timezone.utc) - timedelta(days=3)

        # 3. PyTorch Compiler & GPU Triton Architecture
        if "pytorch" in query_lower or "torch.compile" in query_lower or "dynamo" in query_lower or "inductor" in query_lower:
            return [
                RawDocument(
                    doc_id="doc_pytorch_compiler_spec",
                    title="PyTorch 2.5 Documentation: torch.compile Architecture",
                    snippet="PyTorch torch.compile uses TorchDynamo Python frame capture and TorchInductor codegen to achieve 20-40% faster inference than standard eager mode by producing fused Triton GPU kernels.",
                    url="https://pytorch.org/docs/stable/torch.compiler.html",
                    source_domain="pytorch.org",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_pytorch_github_release",
                    title="GitHub - pytorch/pytorch: PyTorch 2.5 Release Notes",
                    snippet="PyTorch 2.5 torch.compile default backend TorchInductor delivers major speedups over standard eager mode with zero accuracy loss.",
                    url="https://github.com/pytorch/pytorch/releases",
                    source_domain="github.com",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_openai_triton_spec",
                    title="Triton Compiler: Open-Source GPU Programming for Neural Networks",
                    snippet="Triton enables TorchInductor to synthesize fused kernel binaries for NVIDIA and AMD GPUs that run significantly faster than un-fused eager kernel launches.",
                    url="https://openai.com/research/triton",
                    source_domain="openai.com",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        # 4. Apache Kafka 4.0 & KRaft Consensus
        if "kafka" in query_lower or "zookeeper" in query_lower or "kraft" in query_lower:
            return [
                RawDocument(
                    doc_id="doc_kafka_kraft_docs",
                    title="Apache Kafka 4.0 Documentation: KRaft Consensus Without ZooKeeper",
                    snippet="Apache Kafka 4.0 officially eliminates ZooKeeper dependency entirely, running all cluster metadata management through the KRaft event log consensus protocol.",
                    url="https://kafka.apache.org/documentation/#kraft",
                    source_domain="kafka.apache.org",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_kafka_kip500",
                    title="KIP-500: Replace ZooKeeper with Self-Managed Metadata Quorum",
                    snippet="Kafka Improvement Proposal 500 completely removes ZooKeeper from the Apache Kafka architecture, achieving sub-second partition leader failover.",
                    url="https://cwiki.apache.org/confluence/display/KAFKA/KIP-500",
                    source_domain="apache.org",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_kafka_github_release",
                    title="GitHub - apache/kafka: Apache Kafka 4.0 Official Release",
                    snippet="Kafka 4.0 is generally available. All ZooKeeper configuration flags have been permanently removed in favor of KRaft.",
                    url="https://github.com/apache/kafka/releases",
                    source_domain="github.com",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        # 5. OAuth 2.1 & PKCE Mandate
        if "oauth" in query_lower or "pkce" in query_lower or "implicit grant" in query_lower:
            return [
                RawDocument(
                    doc_id="doc_ietf_oauth21_spec",
                    title="IETF OAuth 2.1 Security Best Current Practice",
                    snippet="OAuth 2.1 consolidates RFC 6749 and officially removes the implicit grant flow due to token exposure. Proof Key for Code Exchange (PKCE) is strictly mandated for all single page applications and mobile clients.",
                    url="https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1",
                    source_domain="datatracker.ietf.org",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_oauth_net_spec",
                    title="OAuth 2.1 Specification - OAuth Community Site",
                    snippet="OAuth 2.1 mandates Proof Key for Code Exchange (PKCE) for all OAuth clients and completely removes implicit grant.",
                    url="https://oauth.net/2.1/",
                    source_domain="oauth.net",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_ietf_rfc7636",
                    title="RFC 7636: Proof Key for Code Exchange by OAuth Public Clients",
                    snippet="PKCE prevents authorization code injection attacks on mobile apps and browser SPAs lacking a client secret.",
                    url="https://datatracker.ietf.org/doc/html/rfc7636",
                    source_domain="datatracker.ietf.org",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        # 6. FastAPI & AnyIO Concurrency
        if "fastapi" in query_lower or "anyio" in query_lower or "uvicorn" in query_lower or "django wsgi" in query_lower:
            return [
                RawDocument(
                    doc_id="doc_fastapi_async_docs",
                    title="FastAPI Documentation: Async Concurrency and AnyIO Integration",
                    snippet="FastAPI async endpoints achieve exceptional throughput using AnyIO concurrency, running on Uvicorn with ASGI and Pydantic v2 data validation.",
                    url="https://fastapi.tiangolo.com/async/",
                    source_domain="fastapi.tiangolo.com",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_fastapi_github",
                    title="GitHub - tiangolo/fastapi: Modern High-Performance Python Web Framework",
                    snippet="FastAPI benchmark metrics show 3-5x higher request throughput than synchronous Django WSGI frameworks on I/O-bound workloads.",
                    url="https://github.com/fastapi/fastapi",
                    source_domain="github.com",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id="doc_pydantic_v2_docs",
                    title="Pydantic v2 Documentation: Rust-Powered Core Data Validation",
                    snippet="Pydantic V2 core is written in Rust, offering 5-50x speedups for serialization and deterministic validation.",
                    url="https://docs.pydantic.dev/latest/",
                    source_domain="docs.pydantic.dev",
                    publication_time="3 days ago",
                    published_date=fresh_date,
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]

        # 7. Specialized Multi-Engine Telemetry (SerpApi Google Scholar & Google News)
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

        # 8. Default Synthesized Developer Knowledge Base
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", query_lower[:30]).strip("-") or "core"
        if "optimistic" in str(vector_type).lower():
            return [
                RawDocument(
                    doc_id=f"doc_opt_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"{query.title()} - Official Specifications",
                    snippet=f"Official guide and architectural specifications for {query}. Fully corroborated in enterprise production environments.",
                    url=f"https://docs.python.org/3/library/{slug}.html",
                    source_domain="docs.python.org",
                    publication_time="1 month ago",
                    published_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
                RawDocument(
                    doc_id=f"doc_opt_2_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"GitHub - Repository: {query}",
                    snippet=f"Core repository for {query}. Actively maintained with extensive unit test coverage and high performance benchmarks.",
                    url=f"https://github.com/topics/{slug}",
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
                    title=f"StackOverflow Discussion: Best Practices and Trade-offs in {query}",
                    snippet=f"Engineering telemetry and performance trade-offs for {query}. Production systems recommend following official architecture guidelines.",
                    url="https://stackoverflow.com/questions/tagged/python",
                    source_domain="stackoverflow.com",
                    publication_time="3 months ago",
                    published_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
                    search_vector=vector_type,
                    engine=engine,
                ),
            ]
        elif "temporal" in str(vector_type).lower():
            return [
                RawDocument(
                    doc_id=f"doc_temp_1_{hashlib.md5(query.encode()).hexdigest()[:6]}",
                    title=f"What's New in 2026: {query} Latest Release Notes",
                    snippet=f"Summary of 2026 official updates, performance enhancements, and modern features for {query}.",
                    url=f"https://github.com/topics/{slug}",
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
