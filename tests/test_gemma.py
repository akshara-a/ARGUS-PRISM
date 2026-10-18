"""Tests for GemmaClient local open-weight model integration and fallbacks."""

from argus.engine.evaluator import ResearchEvaluator
from argus.llm.gemma_client import GemmaClient
from argus.models.domain import NodeState, ValidationVerdict
from argus.providers import MockSearchStrategy


def test_gemma_client_fallback_mode():
    client = GemmaClient(model_name="gemma2:2b", endpoint="http://localhost:11434/api/generate")
    # Even if Ollama daemon is offline, client must not crash and must return clean propositions
    text = (
        "FastAPI async endpoints achieve high throughput using AnyIO concurrency. "
        "Uvicorn manages asynchronous worker processes."
    )
    claims = client.extract_claims(text)
    assert len(claims) >= 1
    assert any("FastAPI" in c or "endpoints" in c for c in claims)


def test_gemma_client_adversarial_stances():
    client = GemmaClient()
    stances = client.synthesize_adversarial_stances("FastAPI async scalability")
    assert "affirmative" in stances
    assert "skeptical" in stances
    assert len(stances["affirmative"]) > 5
    assert len(stances["skeptical"]) > 5


def test_evaluator_validate_with_gemma_backend():
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    report = evaluator.validate_response(
        response_text="LegacyAPI v1 is officially deprecated and removed as of March 2026. Developers must migrate to UnifiedAPI v2.",
        topic="LegacyAPI v1 production readiness",
        llm_backend="gemma",
    )
    assert report.total_claims_evaluated == 2
    assert report.verified_count == 2
    assert report.verdict == ValidationVerdict.FACTUALLY_SOUND

