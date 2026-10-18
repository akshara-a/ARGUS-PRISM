"""Unit tests for TechnologyComparator and trade-off synthesis."""

import pytest
from argus.engine.comparator import TechnologyComparator
from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import ComparisonReport
from argus.providers.mock_provider import MockSearchStrategy


def test_technology_comparator_trade_offs():
    """Verify head-to-head comparison generates valid 4-dimension matrix."""
    provider = MockSearchStrategy()
    comparator = TechnologyComparator(provider=provider)

    report = comparator.compare(
        tech_a="FastAPI async",
        tech_b="LegacyAPI v1 production readiness",
        domain_context="Web Services",
    )

    assert isinstance(report, ComparisonReport)
    assert report.tech_a == "FastAPI async"
    assert report.tech_b == "LegacyAPI v1 production readiness"
    assert len(report.trade_off_dimensions) == 4

    dim_names = [d.dimension_name for d in report.trade_off_dimensions]
    assert "Global Evidence Confidence" in dim_names
    assert "Authoritative Verified Claims" in dim_names
    assert "Operational Stability (Low Debt)" in dim_names
    assert "Ecosystem Freshness & Recency" in dim_names

    for dim in report.trade_off_dimensions:
        assert 0.0 <= dim.tech_a_score <= 100.0
        assert 0.0 <= dim.tech_b_score <= 100.0
        assert dim.winner in (report.tech_a, report.tech_b, "Tie")
        assert len(dim.notes) > 0

    assert report.recommended_winner in (report.tech_a, report.tech_b, "Tie")
    assert len(report.verdict_rationale) > 0


def test_evaluator_compare_technologies_facade():
    """Verify ResearchEvaluator facade delegates correctly to TechnologyComparator."""
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    report = evaluator.compare_technologies(
        tech_a="Redis Cache",
        tech_b="Memcached Cluster",
    )

    assert isinstance(report, ComparisonReport)
    assert report.report_a is not None
    assert report.report_b is not None
    assert len(report.trade_off_dimensions) == 4
