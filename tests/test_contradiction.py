"""Unit tests for semantic contradiction detection."""

import pytest
from argus.engine.contradiction import ContradictionDetector
from argus.models.domain import Citation, Claim, NodeState


def test_contradiction_detection_opposing_polarity():
    """Verify that opposing claims on the same topic are detected as high-severity conflict."""
    detector = ContradictionDetector()

    c1 = Claim(
        claim_id="c1",
        claim_text="LegacyAPI v1 is officially deprecated and removed in recent releases.",
        confidence_score=75.0,
        supporting_citations=[
            Citation(url="https://github.com/framework/releases", snippet="Deprecated and removed", tier_weight=1.5)
        ],
    )

    c2 = Claim(
        claim_id="c2",
        claim_text="LegacyAPI v1 is production ready with rock-solid stability.",
        confidence_score=50.0,
        supporting_citations=[
            Citation(url="https://medium.com/blog/legacyapi", snippet="Production ready", tier_weight=0.5)
        ],
    )

    conflicts = detector.detect_conflicts([c1, c2])

    assert len(conflicts) == 1
    assert conflicts[0].severity == "HIGH"
    assert c1.node_state == NodeState.CONTESTED
    assert c2.node_state == NodeState.CONTESTED
    assert len(c1.contradicting_citations) == 1
    assert len(c2.contradicting_citations) == 1


def test_no_contradiction_on_orthogonal_claims():
    """Verify that non-conflicting claims do not trigger false conflicts."""
    detector = ContradictionDetector()

    c1 = Claim(
        claim_id="c1",
        claim_text="FastAPI provides asynchronous high throughput routing.",
        confidence_score=80.0,
        supporting_citations=[
            Citation(url="https://github.com/tiangolo/fastapi", snippet="High throughput", tier_weight=1.5)
        ],
    )

    c2 = Claim(
        claim_id="c2",
        claim_text="PostgreSQL connection pooling requires tuning max connections.",
        confidence_score=75.0,
        supporting_citations=[
            Citation(url="https://docs.postgresql.org/guide", snippet="Connection pooling", tier_weight=1.5)
        ],
    )

    conflicts = detector.detect_conflicts([c1, c2])
    assert len(conflicts) == 0
