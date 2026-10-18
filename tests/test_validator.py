"""Unit tests for the ARGUS PRISM LLM Response Validator."""

import pytest
from argus.engine.evaluator import ResearchEvaluator
from argus.engine.extractor import ClaimExtractor
from argus.engine.validator import ResponseValidator
from argus.models.domain import NodeState, ValidationVerdict
from argus.providers.mock_provider import MockSearchStrategy


def test_extract_claims_from_text():
    """Verify propositional extraction strips filler and extracts clean claims."""
    raw_llm_text = (
        "Here is the technical overview you requested:\n\n"
        "- FastAPI async endpoints achieve high throughput on Uvicorn.\n"
        "- It utilizes AnyIO for event loop management.\n"
        "Hope this helps you understand the architecture!"
    )
    propositions = ClaimExtractor.extract_claims_from_text(raw_llm_text)
    assert len(propositions) == 2
    assert "FastAPI async endpoints achieve high throughput on Uvicorn" in propositions[0]
    assert "It utilizes AnyIO for event loop management" in propositions[1]


def test_validate_factually_sound_response():
    """Verify factually sound response returns high integrity and corroborated claims."""
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)

    llm_response = (
        "LegacyAPI v1 is officially deprecated and removed as of March 2026. "
        "Developers must migrate to UnifiedAPI v2."
    )

    report = evaluator.validate_response(
        response_text=llm_response,
        topic="LegacyAPI v1 production readiness",
    )

    assert report.total_claims_evaluated == 2
    assert report.verified_count == 2
    assert report.refuted_count == 0
    assert report.overall_validity_score >= 50.0
    assert report.verdict == ValidationVerdict.FACTUALLY_SOUND


def test_validate_deprecated_response_contradiction_catch():
    """Verify outdated/deprecated assertions are caught as REFUTED with authoritative corrections."""
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)

    llm_response = (
        "LegacyAPI v1 is production ready with guaranteed thread safety for high concurrency distributed systems."
    )

    report = evaluator.validate_response(
        response_text=llm_response,
        topic="LegacyAPI v1 production readiness",
    )

    assert report.total_claims_evaluated >= 1
    assert report.refuted_count >= 1
    assert report.verdict == ValidationVerdict.HIGH_HALLUCINATION_RISK

    refuted_claim = next(c for c in report.validated_propositions if c.status == NodeState.REFUTED)
    assert refuted_claim.contradiction_warning is not None
    assert "overruled" in refuted_claim.contradiction_warning.lower() or "contradicts" in refuted_claim.contradiction_warning.lower()
    assert refuted_claim.suggested_correction is not None


def test_validate_hallucinated_library_trap():
    """Verify fabricated or non-existent library assertions are caught with zero evidence."""
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)

    llm_response = (
        "QuantumReactJS micro-kernel state manager provides zero-latency reactivity and automatic state synchronization."
    )

    report = evaluator.validate_response(
        response_text=llm_response,
        topic="QuantumReactJS micro-kernel state manager",
    )

    assert report.total_claims_evaluated >= 1
    assert report.verdict == ValidationVerdict.HIGH_HALLUCINATION_RISK
    assert report.overall_validity_score == 0.0

    weak_claim = report.validated_propositions[0]
    assert weak_claim.status == NodeState.WEAK
    assert "hallucination" in weak_claim.contradiction_warning.lower() or "unsubstantiated" in weak_claim.contradiction_warning.lower()


def test_validate_empty_response():
    """Verify validator handles empty or whitespace input safely without crashing."""
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)

    report = evaluator.validate_response(response_text="   \n\n  ")
    assert report.total_claims_evaluated == 0
    assert report.verdict == ValidationVerdict.HIGH_HALLUCINATION_RISK
    assert "No assertional factual propositions" in report.summary
