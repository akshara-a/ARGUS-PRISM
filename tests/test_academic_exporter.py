"""Tests for AcademicExporter with footnotes and bibliography."""

from pydantic import HttpUrl
from argus.engine.academic_exporter import AcademicExporter
from argus.models.domain import (
    Citation,
    NodeState,
    ValidatedClaim,
    ValidationReport,
    ValidationVerdict,
)


def test_academic_exporter_generates_footnotes_and_bibliography():
    text = "FastAPI async endpoints achieve high throughput using AnyIO concurrency on Uvicorn."
    citation = Citation(
        url=HttpUrl("https://fastapi.tiangolo.com/async/"),
        snippet="FastAPI supports concurrency and async endpoints out of the box.",
        tier_weight=1.5,
    )
    claim = ValidatedClaim(
        proposition_text="FastAPI async endpoints achieve high throughput using AnyIO concurrency",
        status=NodeState.VERIFIED,
        confidence_score=94.0,
        citations=[citation],
    )
    report = ValidationReport(
        original_text=text,
        topic="FastAPI Concurrency Guide",
        overall_validity_score=94.0,
        verdict=ValidationVerdict.FACTUALLY_SOUND,
        summary="Sound and corroborated.",
        validated_propositions=[claim],
    )

    result = AcademicExporter.export_publication_markdown(text, report, style="ieee")

    assert result["footnotes_count"] == 1
    assert "[^1]" in result["annotated_body"]
    assert "### 📚 References & Verified Empirical Sources" in result["formatted_markdown"]
    assert "[^1]:" in result["formatted_markdown"]
    assert "fastapi.tiangolo.com" in result["formatted_markdown"]


def test_academic_exporter_apa_style():
    text = "FastAPI is modern."
    citation = Citation(
        url=HttpUrl("https://fastapi.tiangolo.com/"),
        snippet="FastAPI framework, high performance, easy to learn.",
        tier_weight=1.5,
    )
    claim = ValidatedClaim(
        proposition_text="FastAPI is modern",
        status=NodeState.VERIFIED,
        confidence_score=90.0,
        citations=[citation],
    )
    report = ValidationReport(
        original_text=text,
        topic="FastAPI Intro",
        overall_validity_score=90.0,
        verdict=ValidationVerdict.FACTUALLY_SOUND,
        summary="Sound.",
        validated_propositions=[claim],
    )

    result = AcademicExporter.export_publication_markdown(text, report, style="apa")

    assert result["style"] == "APA"
    assert "Available: [https://fastapi.tiangolo.com/]" in result["formatted_markdown"]
