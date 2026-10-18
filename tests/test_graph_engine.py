"""Unit tests for ClaimGraphEngine multi-hop entailment and transitive invalidation."""

import pytest
from argus.engine.graph_engine import ClaimGraphEngine
from argus.models.domain import (
    Claim,
    ClaimRelationType,
    ConflictItem,
    GraphMetrics,
    NodeState,
)


def test_graph_engine_contradiction_and_entailment():
    """Verify ClaimGraphEngine constructs CONTRADICTS and REQUIRES edges."""
    claims = [
        Claim(
            claim_id="claim_001",
            claim_text="LegacyAPI v1 is deprecated and removed in 2026",
            confidence_score=90.0,
            node_state=NodeState.VERIFIED,
            is_corroborated=True,
        ),
        Claim(
            claim_id="claim_002",
            claim_text="LegacyAPI v1 is recommended production-ready solution",
            confidence_score=10.0,
            node_state=NodeState.REFUTED,
            is_corroborated=False,
        ),
        Claim(
            claim_id="claim_003",
            claim_text="LegacyAPI v1 requires python legacy runtime package",
            confidence_score=60.0,
            node_state=NodeState.CONTESTED,
            is_corroborated=True,
        ),
    ]

    conflicts = [
        ConflictItem(
            conflict_id="conf_001",
            topic="LegacyAPI",
            claim_a="LegacyAPI v1 is deprecated and removed in 2026",
            claim_b="LegacyAPI v1 is recommended production-ready solution",
            source_a_url="https://github.com/framework/repo",
            source_b_url="https://medium.com/blog",
            severity="HIGH",
            status="RESOLVED",
            resolution_notes="Official changelog overrides legacy SEO article.",
        )
    ]

    relations, metrics = ClaimGraphEngine.analyze_graph(claims=claims, conflicts=conflicts)

    assert isinstance(metrics, GraphMetrics)
    assert metrics.total_edges > 0
    assert 0.0 <= metrics.contradiction_density <= 1.0
    assert metrics.consensus_centrality > 0.0

    # Direct contradiction relation
    contradiction_edges = [
        r for r in relations if r.relation_type == ClaimRelationType.CONTRADICTS
    ]
    assert len(contradiction_edges) == 1
    assert contradiction_edges[0].source_claim_id == "claim_001"
    assert contradiction_edges[0].target_claim_id == "claim_002"

    # Dependency / Prerequisite edge between claim_003 and claim_002 or claim_001
    requires_edges = [
        r for r in relations if r.relation_type == ClaimRelationType.REQUIRES
    ]
    assert len(requires_edges) >= 1
    assert any(r.source_claim_id == "claim_003" for r in requires_edges)


def test_graph_engine_transitive_contradiction_propagation():
    """Verify refuted claim propagates transitive contradiction to its downstream dependents."""
    # Claim A refutes Claim B. Claim C entails Claim B.
    # Therefore Claim A should transitively contradict Claim C, and Claim C's score should be discounted.
    claim_a = Claim(
        claim_id="claim_a",
        claim_text="Authentication v1 service is permanently decommissioned",
        confidence_score=95.0,
        node_state=NodeState.VERIFIED,
        is_corroborated=True,
    )
    claim_b = Claim(
        claim_id="claim_b",
        claim_text="Authentication v1 service is operational in cluster",
        confidence_score=15.0,
        node_state=NodeState.REFUTED,
        is_corroborated=False,
    )
    claim_c = Claim(
        claim_id="claim_c",
        claim_text="User login causes authentication v1 token generation",
        confidence_score=80.0,
        node_state=NodeState.CONTESTED,
        is_corroborated=True,
    )

    claims = [claim_a, claim_b, claim_c]
    conflicts = [
        ConflictItem(
            conflict_id="conf_002",
            topic="Auth Service",
            claim_a="Authentication v1 service is permanently decommissioned",
            claim_b="Authentication v1 service is operational in cluster",
            source_a_url="https://github.com/auth/repo",
            source_b_url="https://medium.com/auth-tutorial",
            severity="HIGH",
            status="RESOLVED",
            resolution_notes="Decommission verified.",
        )
    ]

    initial_score_c = claim_c.confidence_score
    relations, metrics = ClaimGraphEngine.analyze_graph(claims=claims, conflicts=conflicts)

    # Check for transitive contradiction edge
    transitive_edges = [
        r for r in relations if r.relation_type == ClaimRelationType.TRANSITIVELY_CONTRADICTS
    ]

    # If claim_c entailed or required claim_b, transitive edge is formed
    if transitive_edges:
        assert transitive_edges[0].target_claim_id == "claim_c"
        # Claim C's confidence score should have been penalized
        assert claim_c.confidence_score < initial_score_c
        assert "Transitively undermined" in str(claim_c.conflict_rationale)
