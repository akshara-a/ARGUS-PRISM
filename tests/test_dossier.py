"""Unit tests for standalone HTML DossierGenerator."""

import pytest
from argus.engine.dossier import DossierGenerator
from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import (
    Citation,
    Claim,
    ConflictItem,
    EvidenceReport,
    NodeState,
)
from argus.providers.mock_provider import MockSearchStrategy


def test_dossier_generator_html_structure():
    """Verify generated HTML dossier includes all essential enterprise report sections."""
    claims = [
        Claim(
            claim_id="cl_01",
            claim_text="FastAPI async handlers utilize asyncio event loop natively",
            confidence_score=94.2,
            node_state=NodeState.VERIFIED,
            supporting_citations=[
                Citation(
                    url="https://docs.python.org/3/library/asyncio.html",
                    snippet="Official python asyncio library guide.",
                    source_domain="docs.python.org",
                    tier_weight=1.5,
                )
            ],
            is_corroborated=True,
        )
    ]

    conflicts = [
        ConflictItem(
            conflict_id="conf_fastapi_01",
            topic="Async Loop",
            claim_a="FastAPI async handlers utilize asyncio event loop natively",
            claim_b="FastAPI relies on synchronous WSGI threading",
            source_a_url="https://docs.python.org/3/library/asyncio.html",
            source_b_url="https://wsgi.tutorial.org",
            severity="HIGH",
            status="RESOLVED",
            resolution_notes="ASGI architecture verified against WSGI.",
        )
    ]

    report = EvidenceReport(
        composite_summary="Comprehensive empirical assessment of FastAPI async architecture.",
        global_confidence_score=94.2,
        structured_claims=claims,
        detailed_conflicts=conflicts,
        total_searches_executed=3,
        domain_category="Fast-Moving AI & Modern Web",
        inferred_lambda=0.35,
    )

    html = DossierGenerator.generate_html(report=report, topic="FastAPI Async Architecture")

    # Assert HTML structure and essential tokens
    assert "<!DOCTYPE html>" in html
    assert "FastAPI Async Architecture" in html
    assert "94.2%" in html
    assert "Fast-Moving AI & Modern Web" in html
    assert "docs.python.org" in html
    assert "ASGI architecture verified against WSGI" in html
    assert "VERIFIED" in html
    assert "ARGUS PRISM" in html
    assert len(html) > 1000


def test_evaluator_generate_dossier():
    """Verify ResearchEvaluator facade generates dossier from previous report."""
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    evaluator.execute_research(topic="FastAPI async", domain_context="Web Services")

    html = evaluator.generate_dossier()
    assert "<!DOCTYPE html>" in html
    assert "Deterministic Confidence" in html
