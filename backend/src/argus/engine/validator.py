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
                    if w.lower() not in ("the", "this", "that", "with", "from", "when", "into", "over", "and", "for")
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

    def _evaluate_proposition(self, proposition: str, report: EvidenceReport) -> ValidatedClaim:
        """Match an LLM proposition against the evidence report corpus."""
        stopwords = {
            "the", "this", "that", "with", "from", "have", "were", "been", "into", "their",
            "what", "when", "where", "which", "more", "most", "also", "some", "and", "for",
            "are", "was", "will", "can", "has", "had", "not", "but", "about", "your", "than",
            "then", "just", "our", "all", "its", "use", "using", "achieve", "achieves"
        }
        p_tokens = {
            t for t in re.findall(r"[a-z0-9_\-\.]{2,}", proposition.lower())
            if t not in stopwords
        }

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
        best_jaccard = 0.0

        for claim in report.structured_claims:
            c_tokens = {
                t for t in re.findall(r"[a-z0-9_\-\.]{2,}", claim.claim_text.lower())
                if t not in stopwords
            }
            intersection = p_tokens.intersection(c_tokens)
            union = p_tokens.union(c_tokens)
            jaccard = len(intersection) / max(1, len(union))

            if len(intersection) >= 2 and jaccard > best_jaccard:
                best_jaccard = jaccard
                best_match = claim

        # 3. If best match is found in structured claims:
        if best_match and best_jaccard >= 0.12:
            # Check if this claim was refuted in a conflict
            warning = None
            correction = None
            if best_match.node_state == NodeState.REFUTED:
                # Find matching conflict for authoritative correction
                for conf in report.detailed_conflicts:
                    if conf.claim_a == best_match.claim_text or conf.claim_b == best_match.claim_text:
                        warning = f"Contradicts fresh authoritative evidence on {conf.topic}: overruled by latest release notes."
                        correction = conf.resolution_notes or f"Authoritative documentation states: {conf.claim_b}"
                        break
                if not warning:
                    warning = best_match.conflict_rationale or "Overruled by authoritative evidence."
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
            c_a_tokens = {
                t for t in re.findall(r"[a-z0-9_\-\.]{2,}", conf.claim_a.lower())
                if t not in stopwords
            }
            c_b_tokens = {
                t for t in re.findall(r"[a-z0-9_\-\.]{2,}", conf.claim_b.lower())
                if t not in stopwords
            }
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
