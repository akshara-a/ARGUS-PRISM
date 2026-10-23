"""Deterministic Scoring and Decay Math Engine."""

import math
import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

from argus.models.domain import Citation, CredibilityTier, ScoreBreakdown


class CredibilityDecorator:
    """Decorator pattern: classifies URLs into authoritative, community, or unverified tiers."""

    # Tier 1: Official repositories and primary registries (1.5x)
    TIER_1_PATTERNS = [
        re.compile(r"(^|\.)github\.com$", re.I),
        re.compile(r"(^|\.)gitlab\.com$", re.I),
        re.compile(r"^docs\.", re.I),
        re.compile(r"^learn\.microsoft\.com$", re.I),
        re.compile(r"(^|\.)microsoft\.com$", re.I),
        re.compile(r"(^|\.)python\.org$", re.I),
        re.compile(r"(^|\.)pypi\.org$", re.I),
        re.compile(r"(^|\.)npmjs\.com$", re.I),
        re.compile(r"(^|\.)rust-lang\.org$", re.I),
        re.compile(r"(^|\.)golang\.org$", re.I),
        re.compile(r"(^|\.)kubernetes\.io$", re.I),
        re.compile(r"(^|\.)apache\.org$", re.I),
        re.compile(r"(^|\.)ietf\.org$", re.I),
        re.compile(r"(^|\.)w3\.org$", re.I),
        re.compile(r"(^|\.)pytorch\.org$", re.I),
        re.compile(r"(^|\.)tiangolo\.com$", re.I),
        re.compile(r"(^|\.)pydantic\.dev$", re.I),
        re.compile(r"(^|\.)openai\.com$", re.I),
        re.compile(r"(^|\.)huggingface\.co$", re.I),
        re.compile(r"(^|\.)anthropic\.com$", re.I),
        re.compile(r"(^|\.)tensorflow\.org$", re.I),
        re.compile(r"(^|\.)react\.dev$", re.I),
        re.compile(r"(^|\.)nodejs\.org$", re.I),
        re.compile(r"(^|\.)mozilla\.org$", re.I),
        re.compile(r"(^|\.)docker\.com$", re.I),
        re.compile(r"(^|\.)redis\.io$", re.I),
        re.compile(r"(^|\.)postgresql\.org$", re.I),
        re.compile(r"(^|\.)kernel\.org$", re.I),
        re.compile(r"(^|\.)oauth\.net$", re.I),
        re.compile(r"\.gov$", re.I),
        re.compile(r"\.edu$", re.I),
    ]

    # Tier 2: Peer-reviewed or high-reputation engineering hubs (1.0x)
    TIER_2_PATTERNS = [
        re.compile(r"(^|\.)stackoverflow\.com$", re.I),
        re.compile(r"(^|\.)stackexchange\.com$", re.I),
        re.compile(r"(^|\.)netflixtechblog\.com$", re.I),
        re.compile(r"(^|\.)eng\.uber\.com$", re.I),
        re.compile(r"(^|\.)blog\.cloudflare\.com$", re.I),
        re.compile(r"(^|\.)lwn\.net$", re.I),
        re.compile(r"(^|\.)dev\.to$", re.I),
        re.compile(r"(^|\.)news\.ycombinator\.com$", re.I),
        re.compile(r"(^|\.)arxiv\.org$", re.I),
        re.compile(r"(^|\.)infoq\.com$", re.I),
    ]

    @classmethod
    def evaluate_source_tier(cls, url: str) -> Tuple[CredibilityTier, float]:
        """Classify URL and return (CredibilityTier, multiplier)."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            return CredibilityTier.TIER_3_UNVERIFIED, 0.5

        # Check Tier 1
        for pat in cls.TIER_1_PATTERNS:
            if pat.search(domain):
                return CredibilityTier.TIER_1_AUTHORITATIVE, 1.5

        # Check Tier 2
        for pat in cls.TIER_2_PATTERNS:
            if pat.search(domain):
                return CredibilityTier.TIER_2_COMMUNITY, 1.0

        # Tier 3 (Default)
        return CredibilityTier.TIER_3_UNVERIFIED, 0.5


class FreshnessDecayCalculator:
    """Calculates exponential decay penalty for temporal staleness."""

    # Reference "now" defaults to current UTC, but can be anchored for testing
    @classmethod
    def calculate_age_months(
        cls,
        published_date: Optional[datetime],
        reference_date: Optional[datetime] = None,
    ) -> float:
        """Calculate age in months from publication date."""
        if not published_date:
            # Default to fresh/current baseline (1 month) when no explicit publication timestamp is provided
            return 1.0

        ref = reference_date or datetime.now(timezone.utc)
        if published_date.tzinfo is None:
            published_date = published_date.replace(tzinfo=timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)

        delta_days = (ref - published_date).total_seconds() / 86400.0
        months = max(0.0, delta_days / 30.4375)  # average month length
        return round(months, 2)

    @classmethod
    def calculate_decay_multiplier(cls, age_months: float, decay_lambda: float = 0.15) -> float:
        """Compute e^(-lambda * t)."""
        decay = math.exp(-decay_lambda * age_months)
        return max(0.001, min(1.0, decay))


class DomainInferenceEngine:
    """Infers optimal decay constant lambda and domain categorization from topic metadata."""

    FAST_MOVING_KEYWORDS = {
        "react", "vue", "nextjs", "svelte", "llm", "langchain", "openai", "transformer",
        "vite", "node", "npm", "tailwind", "deno", "bun", "gemini", "claude", "agent",
        "huggingface", "pydantic", "fastapi", "rag"
    }
    CLOUD_DEVOPS_KEYWORDS = {
        "kubernetes", "k8s", "docker", "aws", "azure", "gcp", "terraform", "ansible",
        "grpc", "rest", "graphql", "oauth", "jwt", "redis", "kafka", "microservices"
    }
    CORE_SYSTEMS_KEYWORDS = {
        "linux", "posix", "kernel", "c++", "rust", "c", "rfc", "tcp", "udp", "tls",
        "sqlite", "postgres", "mysql", "assembly", "compiler", "operating system"
    }

    @classmethod
    def infer_domain_and_lambda(cls, topic: str, domain_context: Optional[str] = None) -> Tuple[float, str]:
        """Infer domain category and adaptive lambda from keywords."""
        text = f"{topic} {domain_context or ''}".lower()
        tokens = set(re.findall(r"[a-z0-9_\-\+]{2,}", text))

        if tokens.intersection(cls.FAST_MOVING_KEYWORDS):
            return 0.35, "Fast-Moving AI & Modern Web"
        elif tokens.intersection(cls.CLOUD_DEVOPS_KEYWORDS):
            return 0.22, "Cloud Infrastructure & APIs"
        elif tokens.intersection(cls.CORE_SYSTEMS_KEYWORDS):
            return 0.05, "Core Systems & Network Standards"
        return 0.15, "General Engineering"


class BayesianConfidenceEngine:
    """Calculates Bayesian posterior probability P(Claim | Evidence)."""

    @classmethod
    def calculate_posterior(
        cls,
        citation_scores: list,
        is_corroborated: bool,
        has_contradiction: bool,
    ) -> float:
        """Compute Bayesian posterior probability using likelihood ratios."""
        if not citation_scores:
            return 0.0

        prior_prob = 0.50
        prior_odds = prior_prob / (1.0 - prior_prob)  # 1.0

        # Compute composite likelihood ratio
        likelihood_ratio = 1.0
        for weight, age, decay_mult in citation_scores:
            evidence_strength = weight * decay_mult
            # High quality fresh evidence gives LR > 1.0
            lr_i = max(0.2, evidence_strength * 1.5)
            likelihood_ratio *= lr_i

        if is_corroborated:
            likelihood_ratio *= 1.4
        if has_contradiction:
            likelihood_ratio *= 0.35

        posterior_odds = prior_odds * likelihood_ratio
        posterior_prob = posterior_odds / (1.0 + posterior_odds)
        return round(min(0.9999, max(0.0001, posterior_prob)), 4)


class DeterministicScorer:
    """Calculates composite deterministic score for claims."""

    DEFAULT_BASE_SCORE = 60.0
    CORROBORATION_MULTIPLIER = 1.20   # +20% boost when verified across multiple sources
    CONFLICT_PENALTY_FACTOR = 0.60    # 40% penalty if contradicted by another source

    @classmethod
    def score_citation(
        cls,
        citation: Citation,
        published_date: Optional[datetime],
        decay_lambda: float = 0.15,
        reference_date: Optional[datetime] = None,
    ) -> Tuple[float, float, float]:
        """Score single citation: returns (tier_weight, age_months, decay_multiplier)."""
        tier, weight = CredibilityDecorator.evaluate_source_tier(str(citation.url))
        citation.tier_weight = weight
        citation.tier_label = tier.value

        age = FreshnessDecayCalculator.calculate_age_months(published_date, reference_date)
        citation.age_months = age

        decay_mult = FreshnessDecayCalculator.calculate_decay_multiplier(age, decay_lambda)
        citation.decay_multiplier = round(decay_mult, 4)
        citation.effective_weight = round(weight * decay_mult, 4)

        return weight, age, decay_mult

    @classmethod
    def compute_claim_confidence(
        cls,
        citation_scores: list,  # list of (weight, age, decay_mult)
        is_corroborated: bool,
        has_contradiction: bool,
        decay_lambda: float = 0.15,
        base_score: float = 60.0,
        domain_category: str = "General Engineering",
        inferred_lambda: Optional[float] = None,
    ) -> Tuple[float, ScoreBreakdown]:
        """Compute final deterministic score and return detailed ScoreBreakdown."""
        bayes_prob = BayesianConfidenceEngine.calculate_posterior(
            citation_scores=citation_scores,
            is_corroborated=is_corroborated,
            has_contradiction=has_contradiction,
        )

        if not citation_scores:
            breakdown = ScoreBreakdown(
                base_score=0.0,
                tier_weight=0.0,
                age_months=0.0,
                decay_lambda=decay_lambda,
                decay_multiplier=0.0,
                corroboration_bonus=0.0,
                conflict_penalty=0.0,
                final_score=0.0,
                formula="FinalScore = 0.0 (No valid citations)",
                domain_category=domain_category,
                inferred_lambda=inferred_lambda or decay_lambda,
                bayesian_posterior=0.0,
            )
            return 0.0, breakdown

        # Aggregate citations: weighted average of effective weights
        avg_tier = sum(cs[0] for cs in citation_scores) / len(citation_scores)
        avg_age = sum(cs[1] for cs in citation_scores) / len(citation_scores)
        avg_decay = sum(cs[2] for cs in citation_scores) / len(citation_scores)

        # Base math formula: BaseScore * TierWeight * e^(-lambda * t)
        raw_score = base_score * avg_tier * avg_decay

        corrob_factor = cls.CORROBORATION_MULTIPLIER if is_corroborated else 1.0
        conflict_factor = cls.CONFLICT_PENALTY_FACTOR if has_contradiction else 1.0

        final_raw = raw_score * corrob_factor * conflict_factor
        final_score = round(max(0.0, min(100.0, final_raw)), 2)

        formula_str = (
            f"FinalScore = min(100, max(0, Base({base_score}) * Tier({avg_tier:.2f}) "
            f"* e^(-{decay_lambda}*{avg_age:.1f}) [{avg_decay:.4f}] "
            f"* Corrob({corrob_factor:.2f}) * Conflict({conflict_factor:.2f}))) = {final_score:.2f} "
            f"[Bayes P(H|E) = {bayes_prob:.4f}]"
        )

        breakdown = ScoreBreakdown(
            base_score=base_score,
            tier_weight=round(avg_tier, 2),
            age_months=round(avg_age, 2),
            decay_lambda=decay_lambda,
            decay_multiplier=round(avg_decay, 4),
            corroboration_bonus=round((corrob_factor - 1.0) * 100, 1),
            conflict_penalty=round((1.0 - conflict_factor) * 100, 1),
            final_score=final_score,
            formula=formula_str,
            domain_category=domain_category,
            inferred_lambda=inferred_lambda or decay_lambda,
            bayesian_posterior=bayes_prob,
        )

        return final_score, breakdown
