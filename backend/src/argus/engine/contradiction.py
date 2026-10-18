"""Semantic Contradiction Detector and Conflict Mapping Engine."""

import hashlib
import re
from typing import List, Set, Tuple
from argus.models.domain import Claim, ConflictItem, NodeState


class ContradictionDetector:
    """Detects semantic disagreements and polarity conflicts across extracted claims."""

    # Polarity lexicons for engineering domains
    POSITIVE_INDICATORS = {
        "production ready",
        "recommended",
        "stable",
        "fully supported",
        "backward compatible",
        "supported",
        "optimal",
        "zero leak",
        "fast",
        "high performance",
        "works properly",
        "rock-solid",
    }

    NEGATIVE_INDICATORS = {
        "deprecated",
        "removed",
        "unsupported",
        "discontinued",
        "breaking change",
        "memory leak",
        "bottleneck",
        "garbage collection stall",
        "migration pain",
        "throws importerror",
        "broken",
        "abandoned",
        "unsafe",
    }

    @staticmethod
    def _extract_keywords(text: str) -> Set[str]:
        """Extract significant technical tokens from text."""
        # Include 2+ char alphanumeric tokens (e.g. v1, v2, go, js)
        tokens = re.findall(r"[a-zA-Z0-9_\-\.]{2,}", text.lower())
        stopwords = {
            "this", "that", "with", "from", "have", "were", "been", "into", "their",
            "what", "when", "where", "which", "more", "most", "also", "some", "official",
            "officially", "guide", "tutorial", "overview", "documentation", "article",
            "latest", "recent", "about", "your", "than", "then", "just"
        }
        return {t for t in tokens if t not in stopwords}

    def _has_positive_polarity(self, text: str) -> bool:
        t_lower = text.lower()
        return any(ind in t_lower for ind in self.POSITIVE_INDICATORS)

    def _has_negative_polarity(self, text: str) -> bool:
        t_lower = text.lower()
        return any(ind in t_lower for ind in self.NEGATIVE_INDICATORS)

    def detect_conflicts(self, claims: List[Claim]) -> List[ConflictItem]:
        """Identify pairwise contradictions among claims and update contradiction lists."""
        conflicts: List[ConflictItem] = []

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                kw1 = self._extract_keywords(c1.claim_text)
                kw2 = self._extract_keywords(c2.claim_text)

                # Check subject/entity overlap
                shared_keywords = kw1.intersection(kw2)
                if len(shared_keywords) < 1:
                    continue

                pos1 = self._has_positive_polarity(c1.claim_text)
                neg1 = self._has_negative_polarity(c1.claim_text)

                pos2 = self._has_positive_polarity(c2.claim_text)
                neg2 = self._has_negative_polarity(c2.claim_text)

                # True contradiction: one claims positive capability/status, other claims negative/deprecated/broken
                is_contradiction = (pos1 and neg2) or (neg1 and pos2)

                if is_contradiction:
                    # Severity calculation:
                    # If dealing with deprecation/removal vs production-ready, it is HIGH severity
                    text_pair = (c1.claim_text + " " + c2.claim_text).lower()
                    if "deprecat" in text_pair or "remov" in text_pair or "breaking" in text_pair:
                        severity = "HIGH"
                    else:
                        severity = "MEDIUM"

                    c1_url = str(c1.supporting_citations[0].url) if c1.supporting_citations else "unknown"
                    c2_url = str(c2.supporting_citations[0].url) if c2.supporting_citations else "unknown"

                    conf_hash = hashlib.md5(f"{c1.claim_text[:20]}:{c2.claim_text[:20]}".encode()).hexdigest()[:8]
                    conflict = ConflictItem(
                        conflict_id=f"conf_{conf_hash}",
                        topic=", ".join(list(shared_keywords)[:3]),
                        claim_a=c1.claim_text,
                        claim_b=c2.claim_text,
                        source_a_url=c1_url,
                        source_b_url=c2_url,
                        severity=severity,
                        status="IN_PROGRESS",
                        resolution_notes=f"Conflicting polarity on technical attributes: {', '.join(shared_keywords)}",
                    )
                    conflicts.append(conflict)

                    # Cross-link citations
                    for cit in c2.supporting_citations:
                        if cit not in c1.contradicting_citations:
                            c1.contradicting_citations.append(cit)
                    for cit in c1.supporting_citations:
                        if cit not in c2.contradicting_citations:
                            c2.contradicting_citations.append(cit)

                    # Mutate node states
                    c1.node_state = NodeState.CONTESTED
                    c2.node_state = NodeState.CONTESTED
                    c1.conflict_rationale = f"Contradicted by: {c2.claim_text[:80]}..."
                    c2.conflict_rationale = f"Contradicted by: {c1.claim_text[:80]}..."

        return conflicts
