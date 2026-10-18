"""Unit tests for TabPFN in-memory Bayesian credibility oracle."""

import pytest
from argus.engine.tabpfn_oracle import TabPFNOracle
from argus.models.domain import Citation, NodeState, ValidatedClaim


def test_tabpfn_evaluate_claim_verified():
    """Verify in-memory Bayesian evaluation of a verified proposition."""
    res = TabPFNOracle.evaluate_claim(
        tier_weight=1.5,
        age_months=1.0,
        corroboration_count=3,
        conflict_count=0,
        base_score=95.0,
    )

    assert res["zero_persistence"] is True
    assert "probabilities" in res
    probs = res["probabilities"]
    assert probs["verified"] > probs["contested"]
    assert probs["verified"] > probs["refuted"]
    assert pytest.approx(probs["verified"] + probs["contested"] + probs["refuted"], rel=1e-3) == 1.0
    assert res["dominant_state"] == NodeState.VERIFIED.value
    assert 1.2 <= res["uncertainty_interval"] <= 8.5
    assert res["entropy"] >= 0.0


def test_tabpfn_evaluate_claim_conflicted():
    """Verify Bayesian evaluation with conflicting evidence increases uncertainty and refutation."""
    res = TabPFNOracle.evaluate_claim(
        tier_weight=1.0,
        age_months=12.0,
        corroboration_count=0,
        conflict_count=3,
        base_score=20.0,
    )

    assert res["zero_persistence"] is True
    probs = res["probabilities"]
    assert probs["refuted"] > probs["verified"]
    assert res["dominant_state"] in (NodeState.REFUTED.value, NodeState.CONTESTED.value)
    assert res["entropy"] > 0.0


def test_tabpfn_evaluate_report_propositions():
    """Verify aggregated Bayesian evaluation over a list of propositions."""
    # Test empty list
    empty_res = TabPFNOracle.evaluate_report_propositions([])
    assert empty_res["zero_persistence"] is True
    assert empty_res["claim_metrics"] == []

    # Test with propositions
    claim1 = ValidatedClaim(
        proposition_text="FastAPI achieves high performance with Uvicorn.",
        status=NodeState.VERIFIED,
        confidence_score=92.0,
        citations=[Citation(source_title="FastAPI Docs", url="https://fastapi.tiangolo.com", tier_weight=1.5, snippet="FastAPI high-performance benchmarks")],
    )
    claim2 = ValidatedClaim(
        proposition_text="QuantumReactJS was deprecated in 2021.",
        status=NodeState.REFUTED,
        confidence_score=15.0,
        contradiction_warning="Direct conflict with package registry",
    )

    report_eval = TabPFNOracle.evaluate_report_propositions([claim1, claim2])
    assert report_eval["zero_persistence"] is True
    assert len(report_eval["claim_metrics"]) == 2
    assert "aggregate_distribution" in report_eval
    dist = report_eval["aggregate_distribution"]
    assert pytest.approx(dist["verified"] + dist["contested"] + dist["refuted"], rel=1e-3) == 1.0
    assert report_eval["mean_uncertainty_interval"] > 0.0
