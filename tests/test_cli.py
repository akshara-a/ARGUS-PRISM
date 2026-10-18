"""Unit tests for the ARGUS CLI."""

import pytest
from argus.cli import format_state_badge, render_confidence_meter
from argus.models.domain import NodeState


def test_cli_badge_formatting():
    """Verify ANSI badge outputs."""
    v_badge = format_state_badge(NodeState.VERIFIED)
    assert "VERIFIED" in v_badge

    c_badge = format_state_badge(NodeState.CONTESTED)
    assert "CONTESTED" in c_badge

    w_badge = format_state_badge(NodeState.WEAK)
    assert "WEAK" in w_badge


def test_cli_confidence_meter():
    """Verify confidence meter bar formatting."""
    m_high = render_confidence_meter(85.0)
    assert "85.0%" in m_high
    assert "█" in m_high

    m_low = render_confidence_meter(12.5)
    assert "12.5%" in m_low


def test_cli_subparsers():
    """Verify CLI argument parsers for newly added subcommands."""
    import argparse
    from argus.cli import main

    # We can inspect parser structure without calling sys.exit
    from argus.cli import cmd_compare, cmd_dossier, cmd_telemetry, cmd_mcp

    assert callable(cmd_compare)
    assert callable(cmd_dossier)
    assert callable(cmd_telemetry)
    assert callable(cmd_mcp)
    from argus.cli import cmd_validate, format_verdict_badge
    from argus.models.domain import ValidationVerdict

    assert callable(cmd_validate)
    assert "SOUND" in format_verdict_badge(ValidationVerdict.FACTUALLY_SOUND)
    assert "RISK" in format_verdict_badge(ValidationVerdict.HIGH_HALLUCINATION_RISK)

