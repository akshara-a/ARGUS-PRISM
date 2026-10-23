"""Semantic Similarity and Natural Language Inference (NLI) Engine.

Provides deep semantic matching, subword cosine similarity, and factual entailment
verification without requiring heavy GPU or high-RAM models (optimized for Render free tier).
"""

import math
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class NLIVerdict(str, Enum):
    """Natural Language Inference verdict categories."""
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"


@dataclass
class NLIResult:
    """Outcome of an NLI entailment / contradiction evaluation."""
    verdict: NLIVerdict
    entailment_score: float
    contradiction_score: float
    confidence: float
    rationale: str


class SemanticSimilarityEngine:
    """High-performance subword and entity-aware cosine similarity engine."""

    SYNONYM_CLUSTERS = [
        {"async", "asynchronous", "concurrency", "concurrent", "coroutine", "coroutines", "anyio", "trio", "asyncio"},
        {"uvicorn", "asgi", "server", "workers", "gunicorn"},
        {"pydantic", "schema", "validation", "validate", "validator", "validators", "models", "v2"},
        {"throughput", "performance", "speed", "fast", "latency", "rps", "scale", "scalability"},
        {"endpoint", "endpoints", "api", "route", "routes", "handler"},
        {"deprecated", "removed", "unsupported", "discontinued", "obsolete", "breaking change"},
        {"recommended", "stable", "production-ready", "production ready", "supported", "verified"},
    ]

    STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "and", "for", "in", "of", "to",
        "with", "by", "on", "at", "or", "it", "its", "as", "be", "this", "that", "from",
        "have", "has", "had", "been", "into", "their", "using", "use", "used", "which",
        "will", "can", "does", "did", "do", "about", "than", "then", "over", "achieve",
        "achieves", "running", "integrates", "integrate", "provides", "provide", "run"
    }

    @classmethod
    def _get_expanded_tokens(cls, text: str) -> Dict[str, float]:
        """Compute weighted subword and synonym-expanded feature vector."""
        tokens = re.findall(r"[a-zA-Z0-9_\-\.]{2,}", text.lower())
        weights: Dict[str, float] = {}

        for t in tokens:
            if t in cls.STOPWORDS:
                continue

            # Core token weight
            weights[t] = weights.get(t, 0.0) + 1.0

            # Technical version token boost (e.g., v2, v3, 2.0)
            if re.match(r"^v?\d+(\.\d+)?$", t):
                weights[t] += 2.0

            # Synonym and technical alias cluster expansion
            for cluster in cls.SYNONYM_CLUSTERS:
                if t in cluster:
                    for syn in cluster:
                        if syn not in weights:
                            weights[syn] = 0.5

        # Character 3-grams for morphological and substring resilience
        words = [t for t in tokens if t not in cls.STOPWORDS]
        for w in words:
            if len(w) >= 4:
                for i in range(len(w) - 2):
                    ng = f"#{w[i:i+3]}"
                    weights[ng] = weights.get(ng, 0.0) + 0.25

        return weights

    @classmethod
    def cosine_similarity(cls, text_a: str, text_b: str) -> float:
        """Compute dense cosine similarity between two text strings."""
        if not text_a or not text_b:
            return 0.0

        vec_a = cls._get_expanded_tokens(text_a)
        vec_b = cls._get_expanded_tokens(text_b)
        all_keys = set(vec_a.keys()).union(set(vec_b.keys()))
        if not all_keys:
            return 0.0

        dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in all_keys)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot / (norm_a * norm_b)


class NaturalLanguageInferenceEngine:
    """Determines factual entailment vs contradiction between premise evidence and hypothesis claim."""

    POSITIVE_ASSERTIONS = {
        "production ready", "recommended", "stable", "fully supported",
        "backward compatible", "supported", "optimal", "fast", "high performance",
        "works properly", "high throughput", "compatible", "integrates"
    }

    NEGATIVE_ASSERTIONS = {
        "deprecated", "removed", "unsupported", "discontinued", "breaking change",
        "memory leak", "bottleneck", "broken", "abandoned", "unsafe", "incompatible"
    }

    @classmethod
    def evaluate_entailment(
        cls,
        premise: str,
        hypothesis: str,
    ) -> NLIResult:
        """Evaluate if premise entails, contradicts, or is neutral towards the hypothesis."""
        similarity = SemanticSimilarityEngine.cosine_similarity(premise, hypothesis)

        premise_lower = premise.lower()
        hypo_lower = hypothesis.lower()

        # Check polarity indicators
        hypo_is_positive = any(re.search(rf"\b{re.escape(p)}\b", hypo_lower) for p in cls.POSITIVE_ASSERTIONS)
        premise_is_negative = any(re.search(rf"\b{re.escape(n)}\b", premise_lower) for n in cls.NEGATIVE_ASSERTIONS)
        premise_is_positive = any(re.search(rf"\b{re.escape(p)}\b", premise_lower) for p in cls.POSITIVE_ASSERTIONS)

        # 1. Contradiction Detection: Proposition asserts capability, premise asserts deprecation/removal
        if hypo_is_positive and premise_is_negative and similarity >= 0.15:
            return NLIResult(
                verdict=NLIVerdict.CONTRADICTION,
                entailment_score=0.05,
                contradiction_score=0.90,
                confidence=round(similarity * 100, 1),
                rationale="Premise evidence explicitly reports deprecation, removal, or breaking incompatibilities.",
            )

        # 2. Strong Entailment: High semantic alignment with matching polarity or authoritative confirmation
        if similarity >= 0.18:
            entail_score = min(0.99, max(0.50, similarity * 1.5))
            return NLIResult(
                verdict=NLIVerdict.ENTAILMENT,
                entailment_score=round(entail_score, 2),
                contradiction_score=0.02,
                confidence=round(similarity * 100, 1),
                rationale="Premise evidence corroborates the core assertion with high semantic affinity.",
            )

        # 3. Moderate Entailment: Partial overlap
        if similarity >= 0.12:
            return NLIResult(
                verdict=NLIVerdict.ENTAILMENT,
                entailment_score=round(similarity, 2),
                contradiction_score=0.05,
                confidence=round(similarity * 100, 1),
                rationale="Premise evidence partially supports the proposition.",
            )

        # 4. Neutral
        return NLIResult(
            verdict=NLIVerdict.NEUTRAL,
            entailment_score=0.10,
            contradiction_score=0.10,
            confidence=0.0,
            rationale="Insufficient semantic overlap to establish definitive entailment or refutation.",
        )
