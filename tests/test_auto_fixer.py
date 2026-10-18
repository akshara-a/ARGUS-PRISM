"""Tests for FactualAutoFixer and diff generator."""

from argus.engine.auto_fixer import FactualAutoFixer
from argus.models.domain import (
    NodeState,
    ValidatedClaim,
    ValidationReport,
    ValidationVerdict,
)


def test_auto_fixer_replaces_refuted_proposition():
    original = "LegacyAPI v1 is production ready with guaranteed thread safety. It is widely used."
    refuted_prop = ValidatedClaim(
        proposition_text="LegacyAPI v1 is production ready with guaranteed thread safety",
        status=NodeState.REFUTED,
        confidence_score=0.02,
        contradiction_warning="Removed in v2.0 per 2026 changelog.",
        suggested_correction="UnifiedAPI v2.0 is production ready with guaranteed thread safety, as LegacyAPI v1 was removed.",
    )

    report = ValidationReport(
        original_text=original,
        topic="LegacyAPI",
        overall_validity_score=15.0,
        verdict=ValidationVerdict.PARTIALLY_CONTESTED,
        summary="Found deprecated assertions.",
        validated_propositions=[refuted_prop],
    )

    result = FactualAutoFixer.repair_document(original, report)

    assert result["fixes_count"] == 1
    assert "UnifiedAPI v2.0" in result["repaired_text"]
    assert "LegacyAPI v1 is production ready" not in result["repaired_text"]
    assert len(result["diff_blocks"]) >= 2

    # Check diff blocks types
    types = [b["type"] for b in result["diff_blocks"]]
    assert "removed" in types
    assert "inserted" in types


def test_auto_fixer_handles_sound_document():
    original = "FastAPI async endpoints achieve high throughput using AnyIO concurrency."
    sound_prop = ValidatedClaim(
        proposition_text="FastAPI async endpoints achieve high throughput using AnyIO concurrency.",
        status=NodeState.VERIFIED,
        confidence_score=94.0,
    )

    report = ValidationReport(
        original_text=original,
        topic="FastAPI",
        overall_validity_score=95.0,
        verdict=ValidationVerdict.FACTUALLY_SOUND,
        summary="All sound.",
        validated_propositions=[sound_prop],
    )

    result = FactualAutoFixer.repair_document(original, report)

    assert result["fixes_count"] == 0
    assert result["repaired_text"] == original
    assert len(result["diff_blocks"]) == 1
    assert result["diff_blocks"][0]["type"] == "unchanged"


def test_auto_fixer_handles_backslash_and_group_references():
    """Verify that replacements containing backslashes (e.g. \\1, \\g<0>, LaTeX) do not cause regex errors."""
    original = "The formula uses parameter alpha."
    refuted_prop = ValidatedClaim(
        proposition_text="The formula uses parameter alpha",
        status=NodeState.REFUTED,
        confidence_score=5.0,
        suggested_correction=r"The formula uses \1 \g<0> \alpha parameter.",
    )

    report = ValidationReport(
        original_text=original,
        overall_validity_score=10.0,
        verdict=ValidationVerdict.PARTIALLY_CONTESTED,
        summary="Refuted formula claim.",
        validated_propositions=[refuted_prop],
    )

    result = FactualAutoFixer.repair_document(original, report)
    assert result["fixes_count"] == 1
    assert r"\1 \g<0> \alpha" in result["repaired_text"]

