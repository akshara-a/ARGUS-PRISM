"""Unit tests for ResearchStateMachine and self-correction loop."""

from datetime import datetime, timezone
import pytest
from argus.engine.state_machine import MasterState, ResearchStateMachine
from argus.models.domain import NodeState
from argus.providers.mock_provider import MockSearchStrategy


def test_state_machine_lifecycle_transitions():
    """Verify clean state transitions from INITIALIZED to COMPLETED."""
    provider = MockSearchStrategy()
    sm = ResearchStateMachine(search_provider=provider)

    report = sm.execute(topic="FastAPI async performance")

    # Verify final state
    assert sm.current_state == MasterState.STATE_COMPLETED
    assert len(sm.state_history) >= 5

    # Verify visited states
    visited = [entry["state"] for entry in sm.state_history]
    assert MasterState.STATE_INITIALIZED.value in visited
    assert MasterState.STATE_PLANNING.value in visited
    assert MasterState.STATE_GATHERING.value in visited
    assert MasterState.STATE_EVALUATING.value in visited
    assert MasterState.STATE_REPORTING.value in visited
    assert MasterState.STATE_COMPLETED.value in visited

    # Verify report structure
    assert report.total_searches_executed >= 3
    assert len(report.structured_claims) > 0


def test_self_correction_tie_breaker_execution():
    """Verify conflict triggers STATE_CONFLICT_RESOLUTION and executes depth 1 tie-breaker."""
    provider = MockSearchStrategy()
    sm = ResearchStateMachine(search_provider=provider, max_recursion_depth=1)

    report = sm.execute(topic="LegacyAPI v1 production readiness")

    visited = [entry["state"] for entry in sm.state_history]
    assert MasterState.STATE_CONFLICT_RESOLUTION.value in visited

    # Search count must increase due to tie-breaker vector execution
    assert report.total_searches_executed >= 4
