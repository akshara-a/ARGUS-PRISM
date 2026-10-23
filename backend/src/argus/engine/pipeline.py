"""Evidence Evaluation Pipeline (Chain of Responsibility Pattern)."""

from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from argus.engine.contradiction import ContradictionDetector
from argus.engine.extractor import ClaimExtractor
from argus.engine.scoring import DeterministicScorer
from argus.models.domain import Claim, ConflictItem, NodeState, RawDocument


class EvidenceEvaluationPipeline:
    """Sequential Chain of Responsibility executing ClaimExtractor -> CredibilityScorer -> FreshnessDecay -> ContradictionDetector."""

    def __init__(self, decay_lambda: float = 0.15, base_score: float = 75.0):
        self.decay_lambda = decay_lambda
        self.base_score = base_score
        self.extractor = ClaimExtractor()
        self.contradiction_detector = ContradictionDetector()

    def process(
        self,
        documents: List[RawDocument],
        reference_date: Optional[datetime] = None,
        domain_category: str = "General Engineering",
        inferred_lambda: Optional[float] = None,
    ) -> Tuple[List[Claim], List[ConflictItem]]:
        """Execute full evaluation pipeline on normalized documents."""
        if not documents:
            return [], []

        # Step 1: Claim Extractor Node
        extracted_pairs = self.extractor.extract_claims(documents)
        if not extracted_pairs:
            return [], []

        raw_claims: List[Claim] = []
        doc_map = {}
        for claim, doc in extracted_pairs:
            raw_claims.append(claim)
            doc_map[claim.claim_id] = doc

        # Step 2: Corroboration Aggregation
        # Group identical or near-identical claims from multiple distinct domains
        claims_by_text = {}
        for c in raw_claims:
            key = c.claim_text.lower().strip()
            if key in claims_by_text:
                existing = claims_by_text[key]
                # Merge supporting citations if distinct URL
                existing_urls = {str(cit.url) for cit in existing.supporting_citations}
                for new_cit in c.supporting_citations:
                    if str(new_cit.url) not in existing_urls:
                        existing.supporting_citations.append(new_cit)
            else:
                claims_by_text[key] = c

        unique_claims = list(claims_by_text.values())

        # Determine multi-domain corroboration
        for c in unique_claims:
            domains = {urlparse(str(cit.url)).netloc for cit in c.supporting_citations}
            if len(domains) >= 2:
                c.is_corroborated = True

        # Step 3: Credibility Scorer Node & Freshness Decay Node
        for c in unique_claims:
            citation_scores = []
            for cit in c.supporting_citations:
                doc = doc_map.get(c.claim_id)
                pub_date = doc.published_date if doc else None
                weight, age, decay_mult = DeterministicScorer.score_citation(
                    citation=cit,
                    published_date=pub_date,
                    decay_lambda=self.decay_lambda,
                    reference_date=reference_date,
                )
                citation_scores.append((weight, age, decay_mult))

            # Initial score calculation before contradiction pass
            score, breakdown = DeterministicScorer.compute_claim_confidence(
                citation_scores=citation_scores,
                is_corroborated=c.is_corroborated,
                has_contradiction=False,
                decay_lambda=self.decay_lambda,
                base_score=self.base_score,
                domain_category=domain_category,
                inferred_lambda=inferred_lambda,
            )
            c.confidence_score = score
            c.breakdown = breakdown

        # Step 4: Contradiction Detector Node
        conflicts = self.contradiction_detector.detect_conflicts(unique_claims)

        # Step 5: Post-contradiction recalculation and NodeState assignment
        for c in unique_claims:
            has_contradiction = len(c.contradicting_citations) > 0

            # Re-compute with contradiction penalty if conflict detected
            citation_scores = [
                (
                    cit.tier_weight if cit.tier_weight is not None else 1.0,
                    cit.age_months if cit.age_months is not None else 1.0,
                    cit.decay_multiplier if cit.decay_multiplier is not None else 0.86,
                )
                for cit in c.supporting_citations
            ]
            final_score, breakdown = DeterministicScorer.compute_claim_confidence(
                citation_scores=citation_scores,
                is_corroborated=c.is_corroborated,
                has_contradiction=has_contradiction,
                decay_lambda=self.decay_lambda,
                base_score=self.base_score,
                domain_category=domain_category,
                inferred_lambda=inferred_lambda,
            )
            c.confidence_score = final_score
            c.breakdown = breakdown

            # Assign Visual NodeState
            if has_contradiction:
                c.node_state = NodeState.CONTESTED
            elif c.confidence_score >= 70.0 and c.is_corroborated:
                c.node_state = NodeState.VERIFIED
            elif c.confidence_score < 50.0:
                c.node_state = NodeState.WEAK
            else:
                c.node_state = NodeState.VERIFIED if c.confidence_score >= 60.0 else NodeState.WEAK

        # Sort claims descending by confidence score
        unique_claims.sort(key=lambda x: x.confidence_score, reverse=True)
        return unique_claims, conflicts
