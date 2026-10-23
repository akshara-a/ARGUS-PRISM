"""Adversarial Query Planning Engine (Builder Pattern)."""

from datetime import datetime
from typing import List, Optional
from argus.models.domain import QueryVector, SearchVectorType


class AdversarialQueryBuilder:
    """Constructs orthogonal, non-biased search vectors to counteract confirmation bias."""

    def __init__(self, current_year: Optional[int] = None):
        self.current_year = current_year or datetime.now().year

    def build_search_vectors(
        self,
        topic: str,
        domain_context: Optional[str] = None,
        custom_modifiers: Optional[List[str]] = None,
    ) -> List[QueryVector]:
        """Spawn parallel, distinct query vectors routed through SerpApi."""
        clean_topic = topic.strip()
        topic_lower = clean_topic.lower()
        ctx_lower = (domain_context or "").lower()

        # Derive concise base query tokens (limit to 4 words to avoid DDG/Google 0-result drops)
        topic_words = clean_topic.split()
        if len(topic_words) <= 4:
            base_topic = clean_topic
        else:
            base_topic = " ".join(topic_words[:4])

        if domain_context and len(topic_words) <= 2 and domain_context.lower() not in clean_topic.lower():
            base_query = f"{domain_context.strip()} {base_topic}"
        else:
            base_query = base_topic

        # Engine routing heuristics targeting SerpApi specialized platforms
        is_academic = any(k in topic_lower or k in ctx_lower for k in ("algorithm", "theory", "paper", "cryptography", "math", "proof", "neural", "attention", "transformer", "latency bound"))
        is_software = any(k in topic_lower or k in ctx_lower for k in ("python", "javascript", "react", "fastapi", "django", "api", "kernel", "rust", "go", "node", "repo", "library", "framework", "pydantic", "docker", "k8s"))

        vectors: List[QueryVector] = []

        # 1. Optimistic Stream: Targets authoritative specs & architecture (Google or Google Scholar)
        optimistic_engine = "google_scholar" if is_academic else "google"
        optimistic_query = f"{base_query} documentation architecture".strip()
        vectors.append(
            QueryVector(
                query_text=optimistic_query,
                vector_type=SearchVectorType.OPTIMISTIC,
                rationale="Targets authoritative specs, official repositories, and architectural documentation",
                target_engine=optimistic_engine,
            )
        )

        # 2. Adversarial / Skeptic Stream: Probes technical debt, regressions, open bug reports (GitHub or Google)
        skeptic_engine = "github" if is_software else "google"
        if custom_modifiers:
            skeptic_modifiers = " ".join(custom_modifiers[:3])
        else:
            skeptic_modifiers = "bottleneck issues"
        skeptic_query = f"{base_query} {skeptic_modifiers}".strip()
        vectors.append(
            QueryVector(
                query_text=skeptic_query,
                vector_type=SearchVectorType.SKEPTIC,
                rationale="Actively probes for edge cases, performance degradation, open bug reports, and operational debt",
                target_engine=skeptic_engine,
            )
        )

        # 3. Temporal Stream: Targets fresh releases, breaking changes, and deprecation news (Google News or Google)
        temporal_engine = "google_news" if any(k in topic_lower for k in ("cve", "vulnerability", "breach", "announcement", "release")) else "google"
        temporal_query = f"{base_query} changelog {self.current_year}".strip()
        vectors.append(
            QueryVector(
                query_text=temporal_query,
                vector_type=SearchVectorType.TEMPORAL,
                rationale=f"Targets fresh release notes, deprecation announcements, and ecosystem shifts in {self.current_year}",
                target_engine=temporal_engine,
            )
        )

        return vectors

    def build_tie_breaker_vector(
        self,
        topic: str,
        claim_a: str,
        claim_b: str,
    ) -> QueryVector:
        """Construct a hyper-specific tie-breaker query to resolve conflicts between opposing sources."""
        # Extract keywords from opposing claims
        stop_words = {"the", "is", "a", "an", "and", "or", "in", "to", "for", "with", "of", "by", "as", "on"}
        words_a = {w.lower() for w in claim_a.split() if w.lower() not in stop_words and len(w) > 3}
        words_b = {w.lower() for w in claim_b.split() if w.lower() not in stop_words and len(w) > 3}
        salient_terms = list(words_a.union(words_b))[:2]
        terms_str = " ".join(salient_terms)

        topic_words = topic.strip().split()[:3]
        base = " ".join(topic_words)

        tie_breaker_engine = "github" if any(k in topic.lower() for k in ("api", "library", "framework", "v1", "v2", "v3", "repo")) else "google"
        tie_breaker_query = f"{base} {terms_str} release notes".strip()
        return QueryVector(
            query_text=tie_breaker_query,
            vector_type=SearchVectorType.TIE_BREAKER,
            rationale=f"Disambiguation query reconciling contradiction: '{claim_a}' vs '{claim_b}'",
            target_engine=tie_breaker_engine,
        )

    def build_refinement_vector(
        self,
        topic: str,
        missing_evidence_aspect: str,
    ) -> QueryVector:
        """Spawn targeted follow-up query when evidence gaps are identified."""
        topic_words = topic.strip().split()[:3]
        base = " ".join(topic_words)
        refinement_query = f"{base} {missing_evidence_aspect} benchmark".strip()
        return QueryVector(
            query_text=refinement_query,
            vector_type=SearchVectorType.TARGETED,
            rationale=f"Refinement query addressing missing evidence domain: {missing_evidence_aspect}",
        )
