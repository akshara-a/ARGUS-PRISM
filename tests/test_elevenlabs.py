"""Tests for ElevenLabs audio executive briefings and synthetic fallback."""

import os
import tempfile
from argus.audio.elevenlabs_client import ElevenLabsBriefing
from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import NodeState, ValidatedClaim, ValidationReport, ValidationVerdict
from argus.providers import MockSearchStrategy


def test_elevenlabs_create_script_from_validation():
    report = ValidationReport(
        original_text="FastAPI async endpoints achieve high throughput.",
        overall_validity_score=95.0,
        verdict=ValidationVerdict.FACTUALLY_SOUND,
        summary="All propositions verified.",
        validated_propositions=[
            ValidatedClaim(
                proposition_text="FastAPI async endpoints achieve high throughput",
                status=NodeState.VERIFIED,
                confidence_score=95.0,
            )
        ],
        total_claims_evaluated=1,
        verified_count=1,
    )

    script = ElevenLabsBriefing.create_script_from_validation(report, client_name="TechCorp")
    assert "ARGUS PRISM" in script
    assert "TechCorp" in script
    assert "95 percent" in script or "95" in script
    assert "factually sound" in script


def test_elevenlabs_create_script_from_research():
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    report = evaluator.execute_research(topic="FastAPI async high-throughput performance")
    script = ElevenLabsBriefing.create_script_from_research(report, topic="FastAPI async performance")
    assert "ARGUS PRISM" in script
    assert "FastAPI async performance" in script
    assert len(script) > 50


def test_elevenlabs_synthesize_audio_synthetic_fallback():
    script = "Hello. This is a test of the ARGUS PRISM automated briefing."
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        audio_bytes, mime_type = ElevenLabsBriefing.synthesize_audio(script, output_file=tmp_path)
        assert len(audio_bytes) > 100
        assert mime_type in ("audio/wav", "audio/mp3")
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 100
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_evaluator_audio_briefing_facade():
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    report = evaluator.validate_response("FastAPI async endpoints achieve high throughput.")
    audio_bytes, mime, script = evaluator.generate_audio_briefing(report, topic_or_client="Demo")
    assert len(audio_bytes) > 0
    assert mime in ("audio/wav", "audio/mp3")
    assert "ARGUS PRISM" in script


def test_elevenlabs_personas():
    """Verify voice persona resolution and custom voice ID pass-through."""
    assert ElevenLabsBriefing.resolve_voice_id("rachel") == "21m00Tcm4TlvDq8ikWAM"
    assert ElevenLabsBriefing.resolve_voice_id("adam") == "pNInz6obpgDQGcFmaJgB"
    assert ElevenLabsBriefing.resolve_voice_id("drew") == "29vD33N1CtxCmqQRPOHJ"
    # Fallback to default when None
    assert ElevenLabsBriefing.resolve_voice_id(None) == ElevenLabsBriefing.DEFAULT_VOICE_ID
    # Custom ID passed as is
    assert ElevenLabsBriefing.resolve_voice_id("custom_voice_id_xyz") == "custom_voice_id_xyz"

