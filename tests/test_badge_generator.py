"""Unit tests for Dynamic SVG Verification Badge Generator."""

from argus.engine.badge_generator import BadgeGenerator


def test_badge_svg_generation_sound():
    svg = BadgeGenerator.generate_svg(score=94.5, verdict="FACTUALLY_SOUND")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "94.5% · VERIFIED" in svg
    assert "#059669" in svg  # Emerald color


def test_badge_svg_generation_caution():
    svg = BadgeGenerator.generate_svg(score=52.0, verdict="PARTIALLY_CONTESTED")
    assert "<svg" in svg
    assert "52.0% · CAUTION" in svg
    assert "#d97706" in svg  # Amber color


def test_badge_svg_generation_unverified():
    svg = BadgeGenerator.generate_svg(score=15.0, verdict="HIGH_HALLUCINATION_RISK")
    assert "<svg" in svg
    assert "15.0% · UNVERIFIED" in svg
    assert "#e11d48" in svg  # Rose color


def test_badge_snippets():
    md = BadgeGenerator.generate_markdown_snippet(score=92.0, verdict="FACTUALLY_SOUND")
    assert "[![ARGUS PRISM Factual Verification]" in md
    assert "/api/badge?score=92.0" in md

    html_code = BadgeGenerator.generate_html_snippet(score=92.0, verdict="FACTUALLY_SOUND")
    assert "<a href=" in html_code
    assert '<img src="' in html_code
