"""Claim Graph Engine: Multi-hop entailment, prerequisite derivation, and transitive contradiction propagation."""

import re
from typing import Dict, List, Set, Tuple

from argus.models.domain import (
    Claim,
    ClaimRelation,
    ClaimRelationType,
    ConflictItem,
    GraphMetrics,
    NodeState,
)


class ClaimGraphEngine:
    """Builds multi-hop relational topology across claims and propagates transitive contradictions."""

    # Semantic markers suggesting prerequisites and entailments
    ENTAILMENT_MARKERS = [
        re.compile(r"\b(causes|leads to|results in|forces|implies|enables)\b", re.I),
        re.compile(r"\b(therefore|hence|consequently)\b", re.I),
    ]

    PREREQUISITE_MARKERS = [
        re.compile(r"\b(requires|needs|depends on|prerequisite|must have)\b", re.I),
    ]

    @classmethod
    def analyze_graph(
        cls,
        claims: List[Claim],
        conflicts: List[ConflictItem],
    ) -> Tuple[List[ClaimRelation], GraphMetrics]:
        """Construct relational edges and calculate topological graph metrics."""
        relations: List[ClaimRelation] = []
        claim_map: Dict[str, Claim] = {c.claim_id: c for c in claims if c.claim_id}

        # 1. Register direct contradiction edges from ConflictItems
        contradiction_pairs: Set[Tuple[str, str]] = set()
        for conf in conflicts:
            c_a = next((c for c in claims if c.claim_text == conf.claim_a), None)
            c_b = next((c for c in claims if c.claim_text == conf.claim_b), None)
            if c_a and c_b and c_a.claim_id and c_b.claim_id:
                relations.append(
                    ClaimRelation(
                        source_claim_id=c_a.claim_id,
                        target_claim_id=c_b.claim_id,
                        relation_type=ClaimRelationType.CONTRADICTS,
                        rationale=f"Direct polarity conflict ({conf.severity}) on entity: {conf.topic}",
                        confidence=1.0,
                    )
                )
                contradiction_pairs.add((c_a.claim_id, c_b.claim_id))
                contradiction_pairs.add((c_b.claim_id, c_a.claim_id))

        # 2. Derive Entailment & Prerequisite edges
        for i in range(len(claims)):
            for j in range(len(claims)):
                if i == j:
                    continue
                c1 = claims[i]
                c2 = claims[j]
                if not c1.claim_id or not c2.claim_id:
                    continue

                if (c1.claim_id, c2.claim_id) in contradiction_pairs:
                    continue

                # Check for prerequisite relationships
                t1 = c1.claim_text
                t2 = c2.claim_text

                # If c1 specifies requirements and shares subject tokens with c2
                stopwords = {"is", "in", "to", "on", "of", "at", "by", "or", "an", "as", "if", "the", "and", "for", "with"}
                words1 = set(re.findall(r"[a-z0-9_]{2,}", t1.lower())) - stopwords
                words2 = set(re.findall(r"[a-z0-9_]{2,}", t2.lower())) - stopwords
                overlap = words1.intersection(words2)

                if len(overlap) >= 2 or any(len(w) >= 4 for w in overlap):
                    if any(p.search(t1) for p in cls.PREREQUISITE_MARKERS):
                        relations.append(
                            ClaimRelation(
                                source_claim_id=c1.claim_id,
                                target_claim_id=c2.claim_id,
                                relation_type=ClaimRelationType.REQUIRES,
                                rationale=f"Identified prerequisite dependency linking: '{t1[:50]}...'",
                                confidence=0.85,
                            )
                        )
                    elif any(p.search(t1) for p in cls.ENTAILMENT_MARKERS) or ("deprecated" in t1.lower() and "importerror" in t2.lower()):
                        relations.append(
                            ClaimRelation(
                                source_claim_id=c1.claim_id,
                                target_claim_id=c2.claim_id,
                                relation_type=ClaimRelationType.ENTAILS,
                                rationale=f"Logical downstream entailment from '{t1[:50]}...'",
                                confidence=0.80,
                            )
                        )

        # 3. Transitive Contradiction Propagation
        # If A contradicts B, and C entails/requires B, then A transitively contradicts C
        transitive_relations: List[ClaimRelation] = []
        visited_transitive: Set[Tuple[str, str]] = set()

        for src_id, refuted_target_id in list(contradiction_pairs):
            refuted_claim = claim_map.get(refuted_target_id)
            if refuted_claim and (refuted_claim.node_state == NodeState.REFUTED or refuted_claim.confidence_score < 30.0):
                # Check if any claim C depended on this refuted claim
                for rel in list(relations):
                    if rel.relation_type in (ClaimRelationType.ENTAILS, ClaimRelationType.REQUIRES):
                        dependent_id = None
                        if rel.target_claim_id == refuted_target_id:
                            dependent_id = rel.source_claim_id
                        elif rel.source_claim_id == refuted_target_id and rel.relation_type == ClaimRelationType.ENTAILS:
                            dependent_id = rel.target_claim_id

                        if (
                            dependent_id
                            and dependent_id in claim_map
                            and dependent_id != src_id
                            and (src_id, dependent_id) not in visited_transitive
                        ):
                            visited_transitive.add((src_id, dependent_id))
                            dep_claim = claim_map[dependent_id]
                            # Penalize dependent claim
                            dep_claim.confidence_score = round(max(0.0, dep_claim.confidence_score * 0.70), 2)
                            dep_claim.conflict_rationale = (
                                f"Transitively undermined: depends on refuted claim '{refuted_claim.claim_text[:60]}...'"
                            )
                            transitive_relations.append(
                                ClaimRelation(
                                    source_claim_id=src_id,
                                    target_claim_id=dependent_id,
                                    relation_type=ClaimRelationType.TRANSITIVELY_CONTRADICTS,
                                    rationale=f"Transitive invalidation propagated via dependency on {refuted_target_id}",
                                    confidence=0.75,
                                )
                            )

        relations.extend(transitive_relations)

        # 4. Topological Graph Metrics
        total_pairs = (len(claims) * (len(claims) - 1)) / 2 if len(claims) > 1 else 1
        conflict_count = len(contradiction_pairs) // 2 + len(transitive_relations)
        density = round(min(1.0, conflict_count / max(1, total_pairs)), 3)

        corroborated_scores = [c.confidence_score for c in claims if c.is_corroborated]
        centrality = round(sum(corroborated_scores) / len(corroborated_scores), 1) if corroborated_scores else 50.0

        entail_count = sum(1 for r in relations if r.relation_type in (ClaimRelationType.ENTAILS, ClaimRelationType.REQUIRES))

        metrics = GraphMetrics(
            contradiction_density=density,
            consensus_centrality=centrality,
            total_edges=len(relations),
            entailment_count=entail_count,
        )

        return relations, metrics
