"""ResponseValidator: Validates LLM-generated responses and propositions against empirical evidence."""

import logging
import re
from typing import List, Optional
from argus.engine.extractor import ClaimExtractor
from argus.models.domain import (
    Claim,
    EvidenceReport,
    NodeState,
    ValidatedClaim,
    ValidationReport,
    ValidationVerdict,
)
from argus.observability.sentry_tracer import SentryTracer

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Audits arbitrary LLM responses or developer assertions against deterministic evidence."""

    def __init__(self, evaluator):
        self.evaluator = evaluator

    def validate(
        self,
        response_text: str,
        topic: Optional[str] = None,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
        llm_backend: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> ValidationReport:
        """Decompose LLM response into propositions and validate each against empirical search streams."""
        with SentryTracer.trace_span(
            op="argus.validation",
            description=f"Validate propositions [topic={topic or 'auto'}]",
            data={"llm_backend": llm_backend or "regex", "input_chars": len(response_text), "engine": engine or "auto"},
        ):
            model_consensus = None
            if llm_backend in ("backboard", "multi_model", "open_weight"):
                from argus.llm.backboard_client import BackboardClient
                backboard = BackboardClient()
                consensus_res = backboard.compare_open_weight_models(response_text)
                propositions = consensus_res.get("propositions", []) or ClaimExtractor.extract_claims_from_text(response_text)
                model_consensus = consensus_res
            elif llm_backend in ("gemma", "ollama", "gemma2"):
                from argus.llm.gemma_client import GemmaClient
                gemma = GemmaClient()
                propositions = gemma.extract_claims(response_text)
            else:
                propositions = ClaimExtractor.extract_claims_from_text(response_text)

            if not propositions:
                return ValidationReport(
                    original_text=response_text,
                    overall_validity_score=0.0,
                    verdict=ValidationVerdict.HIGH_HALLUCINATION_RISK,
                    summary="No assertional factual propositions could be identified in the input text.",
                    validated_propositions=[],
                    total_claims_evaluated=0,
                )

            # Determine anchor topic for research
            active_topic = topic
            if not active_topic:
                first_p = propositions[0]
                words = [
                    w for w in re.findall(r"[A-Za-z0-9_\-\.]{3,}", first_p)
                    if w.lower() not in (
                        "the", "this", "that", "with", "from", "when", "into", "over", "and", "for",
                        "are", "was", "were", "did", "does", "what", "which", "how", "can"
                    )
                ]
                active_topic = " ".join(words[:6]) if words else first_p[:50]

            # Execute research via active pluggable search provider
            report: EvidenceReport = self.evaluator.execute_research(
                topic=active_topic,
                domain_context=domain_context,
                decay_lambda=decay_lambda,
                engine=engine,
            )

            validated_claims: List[ValidatedClaim] = []

            for prop in propositions:
                val_claim = self._evaluate_proposition(prop, report)
                validated_claims.append(val_claim)

            # Aggregate counts
            total_count = len(validated_claims)
            verified_cnt = sum(1 for c in validated_claims if c.status == NodeState.VERIFIED)
            contested_cnt = sum(1 for c in validated_claims if c.status == NodeState.CONTESTED)
            refuted_cnt = sum(1 for c in validated_claims if c.status == NodeState.REFUTED)
            weak_cnt = sum(1 for c in validated_claims if c.status == NodeState.WEAK)

            avg_score = (
                round(sum(c.confidence_score for c in validated_claims) / max(1, total_count), 2)
                if validated_claims
                else 0.0
            )

            # Determine overall verdict
            if refuted_cnt > 0 or (verified_cnt == 0 and weak_cnt > 0 and avg_score < 30.0):
                verdict = ValidationVerdict.HIGH_HALLUCINATION_RISK
                summary = (
                    f"HIGH RISK: The response contains {refuted_cnt} refuted or deprecated assertions "
                    f"and {weak_cnt} unverified claims. Overall validity score is {avg_score:.1f}%."
                )
            elif contested_cnt > 0 or (weak_cnt > 0 and verified_cnt > 0) or (verified_cnt == 0 and avg_score < 50.0):
                verdict = ValidationVerdict.PARTIALLY_CONTESTED
                summary = (
                    f"CAUTION: The response contains contested or weakly verified claims. "
                    f"{verified_cnt} of {total_count} assertions verified. Overall validity score is {avg_score:.1f}%."
                )
            else:
                verdict = ValidationVerdict.FACTUALLY_SOUND
                summary = (
                    f"FACTUALLY SOUND: All {verified_cnt} extracted propositions are corroborated by fresh, "
                    f"authoritative evidence. Overall validity score is {avg_score:.1f}%."
                )

            SentryTracer.record_breadcrumb(
                category="argus.validation",
                message=f"Verdict: {verdict.value} (score={avg_score}%)",
                level="info",
                data={
                    "verified": verified_cnt,
                    "contested": contested_cnt,
                    "refuted": refuted_cnt,
                    "weak": weak_cnt,
                    "score": avg_score,
                },
            )

            from argus.engine.tabpfn_oracle import TabPFNOracle
            bayesian_res = TabPFNOracle.evaluate_report_propositions(validated_claims)

            return ValidationReport(
                original_text=response_text,
                overall_validity_score=avg_score,
                verdict=verdict,
                summary=summary,
                topic=active_topic,
                validated_propositions=validated_claims,
                total_claims_evaluated=total_count,
                verified_count=verified_cnt,
                contested_count=contested_cnt,
                refuted_count=refuted_cnt,
                weak_count=weak_cnt,
                underlying_evidence_report=report,
                bayesian_confidence_interval=bayesian_res.get("mean_uncertainty_interval"),
                bayesian_distribution=bayesian_res.get("aggregate_distribution"),
                model_consensus=model_consensus,
            )

    @staticmethod
    def _tokenize_semantic(text: str) -> set:
        stopwords = {
            "the", "this", "that", "with", "from", "have", "were", "been", "into", "their",
            "what", "when", "where", "which", "more", "most", "also", "some", "and", "for",
            "are", "was", "will", "can", "has", "had", "not", "but", "about", "your", "than",
            "then", "just", "our", "all", "its", "use", "using", "achieve", "achieves",
            "to", "in", "of", "on", "at", "by", "an", "a", "or", "is", "did", "does", "do",
            "as", "if", "any", "over", "be", "it"
        }
        tokens = set()
        for raw in re.findall(r"[a-zA-Z0-9_\-\.]{2,}", text.lower()):
            clean = raw.strip(".,;:!?-_'\"()")
            if not clean or clean in stopwords:
                continue
            tokens.add(clean)
            if clean.endswith("ed") and len(clean) > 4:
                tokens.add(clean[:-2])
            elif clean.endswith("ing") and len(clean) > 5:
                tokens.add(clean[:-3])
            elif clean.endswith("s") and len(clean) > 3 and not clean.endswith("ss"):
                tokens.add(clean[:-1])
        return tokens

    def _evaluate_proposition(self, proposition: str, report: EvidenceReport) -> ValidatedClaim:
        """Match an LLM proposition against the evidence report corpus."""
        p_tokens = self._tokenize_semantic(proposition)

        # 1. Hallucination Trap check: If the underlying report has 0.0 confidence or 0 claims
        if report.global_confidence_score == 0.0 or not report.structured_claims:
            return ValidatedClaim(
                proposition_text=proposition,
                status=NodeState.WEAK,
                confidence_score=0.0,
                contradiction_warning="Unsubstantiated: Zero empirical evidence found in authoritative sources (hallucination risk).",
                suggested_correction="Verify whether the referenced library or component actually exists.",
            )

        # 2. Check for best match in structured claims
        best_match: Optional[Claim] = None
        best_score = 0.0
        best_jaccard = 0.0

        for claim in report.structured_claims:
            c_tokens = self._tokenize_semantic(claim.claim_text)
            intersection = p_tokens.intersection(c_tokens)
            union = p_tokens.union(c_tokens)
            jaccard = len(intersection) / max(1, len(union))

            # Prioritize verified claims over weak claims
            tier_mult = 1.6 if claim.node_state == NodeState.VERIFIED else (0.4 if claim.node_state == NodeState.WEAK else 1.0)
            score = jaccard * tier_mult

            if len(intersection) >= 2 and score > best_score:
                best_score = score
                best_jaccard = jaccard
                best_match = claim

        # 3. If best match is found in structured claims:
        if best_match and (best_jaccard >= 0.10 or best_score >= 0.12):
            warning = None
            correction = None

            # Check polarity conflict: proposition asserts safe/recommended, but evidence states deprecated/removed
            positive_markers = {"safe", "recommended", "production ready", "stable", "compatible", "supported"}
            negative_markers = {"deprecated", "removed", "unsupported", "discontinued", "breaking change"}
            prop_is_positive = any(m in proposition.lower() for m in positive_markers)
            claim_is_negative = any(m in best_match.claim_text.lower() for m in negative_markers)

            if best_match.node_state == NodeState.REFUTED or (prop_is_positive and claim_is_negative):
                # Find matching conflict for authoritative correction
                for conf in report.detailed_conflicts:
                    if conf.claim_a == best_match.claim_text or conf.claim_b == best_match.claim_text:
                        warning = f"Contradicts fresh authoritative evidence on {conf.topic}: overruled by latest release notes."
                        correction = conf.resolution_notes or f"Authoritative documentation states: {conf.claim_b}"
                        break
                if not warning:
                    warning = best_match.conflict_rationale or f"Contradicts authoritative release notes: {best_match.claim_text}"
                if not correction and best_match.supporting_citations:
                    correction = f"Check primary source: {best_match.supporting_citations[0].url}"

                return ValidatedClaim(
                    proposition_text=proposition,
                    status=NodeState.REFUTED,
                    confidence_score=min(best_match.confidence_score, 10.0),
                    citations=best_match.supporting_citations,
                    contradiction_warning=warning,
                    suggested_correction=correction,
                )

            elif best_match.node_state in (NodeState.CONTESTED, NodeState.WEAK):
                return ValidatedClaim(
                    proposition_text=proposition,
                    status=best_match.node_state,
                    confidence_score=best_match.confidence_score,
                    citations=best_match.supporting_citations,
                    contradiction_warning=best_match.conflict_rationale or "Proposition is contested across sources.",
                )
            else:
                # VERIFIED
                return ValidatedClaim(
                    proposition_text=proposition,
                    status=NodeState.VERIFIED,
                    confidence_score=best_match.confidence_score,
                    citations=best_match.supporting_citations,
                )

        # 4. Check if proposition specifically matches a refuted conflict item
        for conf in report.detailed_conflicts:
            c_a_tokens = self._tokenize_semantic(conf.claim_a)
            c_b_tokens = self._tokenize_semantic(conf.claim_b)
            overlap_a = len(p_tokens.intersection(c_a_tokens))
            overlap_b = len(p_tokens.intersection(c_b_tokens))

            if overlap_a >= 3 and overlap_a > overlap_b:
                return ValidatedClaim(
                    proposition_text=proposition,
                    status=NodeState.REFUTED,
                    confidence_score=5.0,
                    contradiction_warning=f"Contradicts fresh authoritative evidence on {conf.topic}: overruled by latest release notes.",
                    suggested_correction=conf.resolution_notes or f"Authoritative documentation states: {conf.claim_b}",
                )

        # 5. Fallback: Proposition unverified in corpus
        return ValidatedClaim(
            proposition_text=proposition,
            status=NodeState.WEAK,
            confidence_score=25.0,
            contradiction_warning="Unverified proposition: Insufficient corroboration in primary evidence streams.",
        )
