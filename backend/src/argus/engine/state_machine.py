"""Autonomous Research State Machine and Self-Correction Loop (State Pattern)."""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from argus.engine.adversarial_builder import AdversarialQueryBuilder
from argus.engine.graph_engine import ClaimGraphEngine
from argus.engine.pipeline import EvidenceEvaluationPipeline
from argus.engine.scoring import DomainInferenceEngine
from argus.models.domain import (
    Claim,
    ConflictItem,
    EvidenceReport,
    NodeState,
    RawDocument,
    SearchVectorType,
)
from argus.observability.sentry_tracer import SentryTracer
from argus.providers.base import ISearchProvider

logger = logging.getLogger(__name__)


class MasterState(str, Enum):
    """Formal Master States of the Research State Machine."""
    STATE_INITIALIZED = "STATE_INITIALIZED"
    STATE_PLANNING = "STATE_PLANNING"
    STATE_GATHERING = "STATE_GATHERING"
    STATE_EVALUATING = "STATE_EVALUATING"
    STATE_CONFLICT_RESOLUTION = "STATE_CONFLICT_RESOLUTION"
    STATE_REPORTING = "STATE_REPORTING"
    STATE_COMPLETED = "STATE_COMPLETED"


class ResearchStateMachine:
    """Coordinates deterministic research lifecycle and executes autonomous tie-breaker self-correction."""

    def __init__(
        self,
        search_provider: ISearchProvider,
        decay_lambda: Optional[float] = None,
        max_recursion_depth: int = 1,
    ):
        self.provider = search_provider
        self.decay_lambda = decay_lambda
        self.max_recursion_depth = max_recursion_depth
        self.current_state = MasterState.STATE_INITIALIZED
        self.state_history: List[Dict[str, str]] = []
        self.query_builder = AdversarialQueryBuilder()
        self.pipeline = EvidenceEvaluationPipeline(decay_lambda=decay_lambda or 0.15)

    def _transition_to(self, new_state: MasterState, reason: str = ""):
        """Record state transition."""
        self.current_state = new_state
        entry = {
            "state": new_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        self.state_history.append(entry)
        logger.info("ResearchStateMachine transitioned to %s: %s", new_state.value, reason)

    def execute(
        self,
        topic: str,
        domain_context: Optional[str] = None,
        reference_date: Optional[datetime] = None,
        decay_lambda_override: Optional[float] = None,
        engine_override: Optional[str] = None,
    ) -> EvidenceReport:
        """Run full autonomous research cycle from planning to evidence report."""
        start_time = time.time()
        self._transition_to(MasterState.STATE_INITIALIZED, f"Initialized with topic: '{topic}'")

        # 0. Infer Domain Category & Adaptive Lambda
        auto_lambda, domain_category = DomainInferenceEngine.infer_domain_and_lambda(topic, domain_context)
        effective_lambda = decay_lambda_override or self.decay_lambda or auto_lambda
        self.pipeline.decay_lambda = effective_lambda

        # 1. Planning State: Generate multi-vector search queries
        self._transition_to(
            MasterState.STATE_PLANNING,
            f"Deriving orthogonal query vectors for [{domain_category}] (lambda={effective_lambda:.2f})",
        )
        with SentryTracer.trace_span("argus.state.planning", "Derive search vectors", {"domain": domain_category}):
            vectors = self.query_builder.build_search_vectors(topic, domain_context)
            vectors_used = [f"[{v.vector_type.value.upper()}:{engine_override or v.target_engine}] {v.query_text}" for v in vectors]

        # 2. Gathering State: Ingest telemetry streams via ISearchProvider across target engines
        self._transition_to(MasterState.STATE_GATHERING, f"Executing {len(vectors)} parallel query vectors")
        documents: List[RawDocument] = []
        total_searches = 0
        engine_telemetry: Dict[str, int] = {}

        with SentryTracer.trace_span("argus.state.gathering", f"Execute {len(vectors)} search vectors", {"provider": self.provider.provider_name}):
            for vec in vectors:
                engine = engine_override or vec.target_engine or "google"
                docs = self.provider.search(
                    query=vec.query_text,
                    engine=engine,
                    vector_type=vec.vector_type.value,
                    num_results=5,
                )
                total_searches += 1
                engine_telemetry[engine] = engine_telemetry.get(engine, 0) + 1
                documents.extend(docs)

        # Deduplicate gathered documents by URL
        unique_docs_by_url: Dict[str, RawDocument] = {}
        for d in documents:
            if d.url not in unique_docs_by_url:
                unique_docs_by_url[d.url] = d
        normalized_documents = list(unique_docs_by_url.values())

        # 2.5 Deep Page Crawling on top search URLs
        # Extract full page article text from top authoritative documentation sources
        from argus.engine.url_crawler import WebpageAuditor
        deep_crawled_count = 0
        is_mock_provider = "mock" in self.provider.provider_name.lower()

        if not is_mock_provider:
            for doc in normalized_documents:
                if deep_crawled_count >= 3:
                    break
                if not doc.url.startswith("http") or doc.engine in ("crawler", "mock"):
                    continue

                try:
                    crawl_data = WebpageAuditor.fetch_url_content(doc.url, max_words=350)
                    content = (crawl_data.get("content") or "").strip()
                    if content and len(content.split()) > 20:
                        # Enrich snippet with full article content
                        doc.snippet = f"{doc.snippet} {content}".strip()
                        deep_crawled_count += 1
                except Exception as exc:
                    logger.debug("Deep crawl skipped for %s: %s", doc.url, exc)

        # 3. Evaluating State: Run through Chain of Responsibility pipeline
        self._transition_to(
            MasterState.STATE_EVALUATING,
            f"Passing {len(normalized_documents)} documents to deterministic evaluation pipeline",
        )
        with SentryTracer.trace_span("argus.state.evaluating", "Execute evaluation pipeline", {"docs_count": len(normalized_documents)}):
            claims, conflicts = self.pipeline.process(
                documents=normalized_documents,
                reference_date=reference_date,
                domain_category=domain_category,
                inferred_lambda=effective_lambda,
            )

        # 4. Conflict Resolution State (Autonomous Self-Correction Loop)
        high_severity_conflicts = [c for c in conflicts if c.severity == "HIGH"]
        recursion_count = 0
        unresolved_conflict_summaries: List[str] = []

        if high_severity_conflicts and recursion_count < self.max_recursion_depth:
            self._transition_to(
                MasterState.STATE_CONFLICT_RESOLUTION,
                f"Halting report generation: {len(high_severity_conflicts)} High-Severity conflicts detected. Executing depth 1 tie-breaker search",
            )
            recursion_count += 1

            for conf in high_severity_conflicts:
                tie_breaker_vec = self.query_builder.build_tie_breaker_vector(
                    topic=topic,
                    claim_a=conf.claim_a,
                    claim_b=conf.claim_b,
                )
                vectors_used.append(f"[TIE_BREAKER] {tie_breaker_vec.query_text}")

                tb_engine = tie_breaker_vec.target_engine or "google"
                tie_breaker_docs = self.provider.search(
                    query=tie_breaker_vec.query_text,
                    engine=tb_engine,
                    vector_type=SearchVectorType.TIE_BREAKER.value,
                    num_results=3,
                )
                total_searches += 1
                engine_telemetry[tb_engine] = engine_telemetry.get(tb_engine, 0) + 1

                # Append newly discovered evidence
                for tb_doc in tie_breaker_docs:
                    if tb_doc.url not in unique_docs_by_url:
                        unique_docs_by_url[tb_doc.url] = tb_doc
                        normalized_documents.append(tb_doc)

            # Re-evaluate entire evidence corpus with tie-breaker documents
            claims, new_conflicts = self.pipeline.process(
                documents=normalized_documents, reference_date=reference_date
            )

            # Check if tie-breaker resolved the conflict authoritatively
            for conf in high_severity_conflicts:
                # Find matching claims in re-evaluated list
                matched_claims = [c for c in claims if c.claim_text in (conf.claim_a, conf.claim_b)]
                if len(matched_claims) >= 2:
                    c_a, c_b = matched_claims[0], matched_claims[1]
                    # If one claim significantly outweighs the other (> 30 point delta) due to Tier 1 freshness
                    score_diff = abs(c_a.confidence_score - c_b.confidence_score)
                    if score_diff >= 30.0:
                        conf.status = "RESOLVED"
                        winner = c_a if c_a.confidence_score > c_b.confidence_score else c_b
                        loser = c_b if winner == c_a else c_a
                        winner.node_state = NodeState.VERIFIED
                        loser.node_state = NodeState.REFUTED
                        conf.resolution_notes = (
                            f"Resolved via authoritative tie-breaker: '{winner.claim_text[:60]}...' "
                            f"(Score: {winner.confidence_score}) overrules '{loser.claim_text[:60]}...' "
                            f"(Score: {loser.confidence_score})."
                        )
                        SentryTracer.record_conflict_resolution(
                            topic=conf.topic,
                            severity=conf.severity,
                            claim_a=conf.claim_a,
                            claim_b=conf.claim_b,
                            resolution_notes=conf.resolution_notes,
                        )
                    else:
                        conf.status = "UNRESOLVED"
                        conf.resolution_notes = "Tie-breaker retrieved mixed evidence; discrepancy remains contested."
                        unresolved_conflict_summaries.append(
                            f"Unresolved contradiction between '{conf.claim_a}' ({conf.source_a_url}) "
                            f"and '{conf.claim_b}' ({conf.source_b_url})"
                        )
                else:
                    conf.status = "RESOLVED"

        # Record any remaining unresolved conflicts
        for conf in conflicts:
            if conf.status == "UNRESOLVED" and conf.resolution_notes:
                summary_str = f"Conflict [{conf.topic}]: {conf.resolution_notes}"
                if summary_str not in unresolved_conflict_summaries:
                    unresolved_conflict_summaries.append(summary_str)

        # 5. Reporting State: Synthesize evidence report
        self._transition_to(MasterState.STATE_REPORTING, "Synthesizing composite summary and MCP evidence report")
        elapsed = round(time.time() - start_time, 2)

        global_confidence = self._calculate_global_confidence(claims, unresolved_conflict_summaries)
        composite_summary = self._synthesize_composite_summary(
            topic=topic,
            claims=claims,
            unresolved_conflicts=unresolved_conflict_summaries,
            global_confidence=global_confidence,
        )

        # 4.5 Graph Entailment & Topological Analysis
        relations, graph_metrics = ClaimGraphEngine.analyze_graph(claims, conflicts)
        cost_guard = self.provider.get_cost_guard_telemetry()

        report = EvidenceReport(
            composite_summary=composite_summary,
            global_confidence_score=global_confidence,
            structured_claims=claims,
            unresolved_conflicts=unresolved_conflict_summaries,
            total_searches_executed=total_searches,
            detailed_conflicts=conflicts,
            execution_time_seconds=elapsed,
            query_vectors_used=vectors_used,
            domain_category=domain_category,
            inferred_lambda=effective_lambda,
            engine_telemetry=engine_telemetry,
            relations=relations,
            graph_metrics=graph_metrics,
            cost_guard=cost_guard,
        )

        if cost_guard:
            SentryTracer.record_cost_guard_metrics(
                total_searches=total_searches,
                cache_hits=cost_guard.cache_hits,
                cost_saved_usd=cost_guard.estimated_cost_saved_usd,
                provider_name=self.provider.provider_name,
            )

        self._transition_to(MasterState.STATE_COMPLETED, "EvidenceReport generated and validated against Pydantic schema")
        return report

    def _calculate_global_confidence(
        self,
        claims: List[Claim],
        unresolved_conflicts: List[str],
    ) -> float:
        """Compute composite global confidence score bounded in [0, 100]."""
        if not claims:
            return 0.0

        top_claims = claims[:5]
        avg_score = sum(c.confidence_score for c in top_claims) / len(top_claims)
        corroborated_count = sum(1 for c in top_claims if c.is_corroborated)
        corroboration_ratio = corroborated_count / len(top_claims)

        # Base composite
        global_score = (avg_score * 0.8) + (corroboration_ratio * 100.0 * 0.2)

        # Proportional penalty for unresolved high-severity conflicts
        if unresolved_conflicts:
            discount = max(0.40, 1.0 - (len(unresolved_conflicts) * 0.15))
            global_score = global_score * discount

        return round(max(0.0, min(100.0, global_score)), 1)

    def _synthesize_composite_summary(
        self,
        topic: str,
        claims: List[Claim],
        unresolved_conflicts: List[str],
        global_confidence: float,
    ) -> str:
        """Synthesize deterministic evidence briefing."""
        if not claims:
            return f"No verifiable empirical evidence found for '{topic}'. Confidence score is 0.0."

        verified = [c for c in claims if c.node_state == NodeState.VERIFIED]
        contested = [c for c in claims if c.node_state == NodeState.CONTESTED]
        weak = [c for c in claims if c.node_state == NodeState.WEAK]

        sections = [
            f"### Evidence Intelligence Synthesis: {topic}",
            f"**Global Deterministic Confidence:** {global_confidence}/100",
            f"**Evaluated Propositions:** {len(claims)} atomic claims ({len(verified)} verified, {len(contested)} contested, {len(weak)} weak).",
        ]

        if verified:
            sections.append("\n**Authoritative & Corroborated Findings:**")
            for v in verified[:4]:
                domain = v.supporting_citations[0].url.host if v.supporting_citations else "source"
                sections.append(f"- {v.claim_text} *(Confidence: {v.confidence_score:.1f}, Source: {domain})*")

        if contested or unresolved_conflicts:
            sections.append("\n**Flagged Contradictions & Divergent Claims:**")
            for u in unresolved_conflicts:
                sections.append(f"- ⚠️ {u}")
            for c in contested[:2]:
                if c.conflict_rationale:
                    sections.append(f"- ⚠️ {c.claim_text}: {c.conflict_rationale}")

        if weak:
            sections.append(f"\n**Low Confidence / Stale Telemetry:** {len(weak)} claims exhibited high temporal decay or lacked independent corroboration.")

        return "\n".join(sections)
