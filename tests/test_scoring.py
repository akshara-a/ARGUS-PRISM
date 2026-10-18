"""Unit tests for CredibilityDecorator, FreshnessDecay, and DeterministicScorer."""

import math
from datetime import datetime, timezone
import pytest
from argus.engine.scoring import (
    CredibilityDecorator,
    DeterministicScorer,
    FreshnessDecayCalculator,
)
from argus.models.domain import Citation, CredibilityTier


def test_credibility_tiering_classification():
    """Verify source tiering and multiplier assignment."""
    # Tier 1
    t1, w1 = CredibilityDecorator.evaluate_source_tier("https://github.com/encode/fastapi")
    assert t1 == CredibilityTier.TIER_1_AUTHORITATIVE
    assert w1 == 1.5

    t1_ms, w1_ms = CredibilityDecorator.evaluate_source_tier("https://docs.microsoft.com/en-us/azure")
    assert t1_ms == CredibilityTier.TIER_1_AUTHORITATIVE
    assert w1_ms == 1.5

    # Tier 2
    t2, w2 = CredibilityDecorator.evaluate_source_tier("https://stackoverflow.com/questions/12345")
    assert t2 == CredibilityTier.TIER_2_COMMUNITY
    assert w2 == 1.0

    t2_net, w2_net = CredibilityDecorator.evaluate_source_tier("https://netflixtechblog.com/microservices")
    assert t2_net == CredibilityTier.TIER_2_COMMUNITY
    assert w2_net == 1.0

    # Tier 3
    t3, w3 = CredibilityDecorator.evaluate_source_tier("https://medium.com/programming-guide/tips")
    assert t3 == CredibilityTier.TIER_3_UNVERIFIED
    assert w3 == 0.5


def test_freshness_decay_math():
    """Verify exponential decay e^(-lambda * t)."""
    # Age 0 months -> decay mult ~ 1.0
    decay_0 = FreshnessDecayCalculator.calculate_decay_multiplier(age_months=0.0, decay_lambda=0.15)
    assert abs(decay_0 - 1.0) < 0.01

    # Age 10 months, lambda 0.15 -> e^(-1.5) ~ 0.2231
    decay_10 = FreshnessDecayCalculator.calculate_decay_multiplier(age_months=10.0, decay_lambda=0.15)
    assert abs(decay_10 - math.exp(-1.5)) < 0.01

    # High age (e.g. 48 months from 2022) heavily penalized
    decay_old = FreshnessDecayCalculator.calculate_decay_multiplier(age_months=48.0, decay_lambda=0.15)
    assert decay_old < 0.01


def test_deterministic_scoring_reproducibility():
    """Verify identical inputs yield exact deterministic float results."""
    cit_scores = [(1.5, 2.0, 0.7408)]  # tier 1.5, 2 months, decay ~0.7408
    score1, b1 = DeterministicScorer.compute_claim_confidence(
        citation_scores=cit_scores,
        is_corroborated=True,
        has_contradiction=False,
        decay_lambda=0.15,
        base_score=60.0,
    )
    score2, b2 = DeterministicScorer.compute_claim_confidence(
        citation_scores=cit_scores,
        is_corroborated=True,
        has_contradiction=False,
        decay_lambda=0.15,
        base_score=60.0,
    )

    assert score1 == score2
    assert score1 > 70.0  # Tier 1 + fresh + corroborated yields high score
    assert b1.final_score == b2.final_score
