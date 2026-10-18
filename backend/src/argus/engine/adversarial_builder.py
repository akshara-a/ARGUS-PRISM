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
        ctx_prefix = f"{domain_context.strip()} " if domain_context else ""
        topic_lower = clean_topic.lower()
        ctx_lower = (domain_context or "").lower()

        # Engine routing heuristics targeting SerpApi specialized platforms
        is_academic = any(k in topic_lower or k in ctx_lower for k in ("algorithm", "theory", "paper", "cryptography", "math", "proof", "neural", "attention", "transformer", "latency bound"))
        is_software = any(k in topic_lower or k in ctx_lower for k in ("python", "javascript", "react", "fastapi", "django", "api", "kernel", "rust", "go", "node", "repo", "library", "framework", "pydantic", "docker", "k8s"))

        vectors: List[QueryVector] = []

        # 1. Optimistic Stream: Targets authoritative specs & architecture (Google or Google Scholar)
        optimistic_engine = "google_scholar" if is_academic else "google"
        optimistic_query = f"{ctx_prefix}{clean_topic} official documentation architecture production ready"
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
        skeptic_modifiers = "memory leak bottleneck known issues migration pain performance regressions"
        if custom_modifiers:
            skeptic_modifiers = " ".join(custom_modifiers)
        skeptic_query = f"{ctx_prefix}{clean_topic} {skeptic_modifiers}"
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
        temporal_query = f"{ctx_prefix}{clean_topic} breaking changes deprecated features changelog {self.current_year}"
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
        salient_terms = list(words_a.union(words_b))[:4]
        terms_str = " ".join(salient_terms)

        tie_breaker_engine = "github" if any(k in topic.lower() for k in ("api", "library", "framework", "v1", "v2", "v3", "repo")) else "google"
        tie_breaker_query = f"{topic} {terms_str} official release notes changelog github RFC"
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
        refinement_query = f"{topic} {missing_evidence_aspect} verified benchmarks"
        return QueryVector(
            query_text=refinement_query,
            vector_type=SearchVectorType.TARGETED,
            rationale=f"Refinement query addressing missing evidence domain: {missing_evidence_aspect}",
        )
