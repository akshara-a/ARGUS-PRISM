"""ResponseValidator: Validates LLM-generated responses and propositions against empirical evidence."""

import logging
import re
from typing import List, Optional
from argus.engine.extractor import ClaimExtractor
from argus.engine.semantic_matcher import (
    NaturalLanguageInferenceEngine,
    NLIVerdict,
    SemanticSimilarityEngine,
)
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
            stopwords = {
                "the", "this", "that", "with", "from", "when", "into", "over", "and", "for",
                "are", "was", "were", "did", "does", "what", "which", "how", "can", "using",
                "use", "used", "running", "integrates", "provides", "achieve", "achieves"
            }
            if not active_topic:
                all_keywords = []
                for p in propositions:
                    for w in re.findall(r"[A-Za-z0-9_\-\.]{3,}", p):
                        if w.lower() not in stopwords and w.lower() not in [k.lower() for k in all_keywords]:
                            all_keywords.append(w)
                            if len(all_keywords) >= 5:
                                break
                    if len(all_keywords) >= 5:
                        break
                active_topic = " ".join(all_keywords[:4]) if all_keywords else propositions[0][:50]

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
                # Multi-proposition targeted refinement: if proposition remains uncorroborated by broad anchor topic
                if (val_claim.status == NodeState.WEAK or val_claim.confidence_score < 40.0) and len(propositions) > 1:
                    prop_words = [
                        w for w in re.findall(r"[A-Za-z0-9_\-\.]{2,}", prop)
                        if w.lower() not in stopwords
                    ]
                    if prop_words:
                        prop_topic = " ".join(prop_words[:4])
                        if prop_topic.lower() != active_topic.lower():
                            prop_report = self.evaluator.execute_research(
                                topic=prop_topic,
                                domain_context=domain_context,
                                decay_lambda=decay_lambda,
                                engine=engine,
                            )
                            refined_claim = self._evaluate_proposition(prop, prop_report)
                            if refined_claim.confidence_score > val_claim.confidence_score:
                                val_claim = refined_claim

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

        # 2. Check for best match in structured claims via Semantic Cosine & NLI Entailment
        best_match: Optional[Claim] = None
        best_score = 0.0
        best_nli_res = None

        for claim in report.structured_claims:
            nli_res = NaturalLanguageInferenceEngine.evaluate_entailment(
                premise=claim.claim_text,
                hypothesis=proposition,
            )
            sim = SemanticSimilarityEngine.cosine_similarity(claim.claim_text, proposition)

            # Prioritize verified claims over weak claims
            tier_mult = 1.6 if claim.node_state == NodeState.VERIFIED else (0.4 if claim.node_state == NodeState.WEAK else 1.0)
            score = sim * tier_mult

            # Direct contradiction detection
            if nli_res.verdict == NLIVerdict.CONTRADICTION and score > 0.15:
                best_match = claim
                best_score = score
                best_nli_res = nli_res
                break

            if nli_res.verdict == NLIVerdict.ENTAILMENT and score > best_score:
                best_score = score
                best_match = claim
                best_nli_res = nli_res

        # 3. If best match is found in structured claims:
        if best_match and best_score >= 0.12 and best_nli_res:
            warning = None
            correction = None

            if best_nli_res.verdict == NLIVerdict.CONTRADICTION or best_match.node_state == NodeState.REFUTED:
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
                # VERIFIED via Semantic Entailment
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
