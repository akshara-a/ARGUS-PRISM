"""Unit tests for SerpApi Multi-Engine Telemetry (Scholar, News, Web)."""

from argus.engine.evaluator import ResearchEvaluator
from argus.providers.mock_provider import MockSearchStrategy


def test_serpapi_engine_scholar():
    provider = MockSearchStrategy()
    docs = provider.search("Transformer Attention Mechanism", engine="google_scholar")
    assert len(docs) >= 1
    assert any("arxiv.org" in d.url or "dl.acm.org" in d.url for d in docs)
    assert docs[0].engine == "google_scholar"


def test_serpapi_engine_news():
    provider = MockSearchStrategy()
    docs = provider.search("Python 3.14 Release", engine="google_news")
    assert len(docs) >= 1
    assert any("techcrunch.com" in d.url or "reuters.com" in d.url for d in docs)
    assert docs[0].engine == "google_news"


def test_evaluator_validate_with_engine():
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)
    report = evaluator.validate_response(
        response_text="Attention mechanism achieves sub-quadratic memory complexity.",
        topic="Transformer Attention",
        engine="google_scholar",
    )
    assert report.total_claims_evaluated >= 1
    assert report.overall_validity_score >= 0.0
