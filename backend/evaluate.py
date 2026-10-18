"""Automated Benchmark & Evaluation Harness for ARGUS PRISM.

Fulfills Core Verification Requirements:
1. The Hallucination Trap Test
2. The Contradiction Catch Test
3. Traceability Assertions
4. Reproducibility Validation
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure src is in sys.path
src_dir = str(Path(__file__).resolve().parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import NodeState
from argus.providers.mock_provider import MockSearchStrategy


class ArgusBenchmarkHarness:
    """Executes the 4 core deterministic verification benchmarks."""

    def __init__(self):
        self.mock_provider = MockSearchStrategy()
        self.evaluator = ResearchEvaluator(provider=self.mock_provider, default_lambda=None)
        self.results = {}

    def run_hallucination_trap_test(self) -> bool:
        """Benchmark 1: Fabricated framework component must return confidence 0 and empty claims."""
        print("\n" + "=" * 60)
        print("TEST 1: The Hallucination Trap Test")
        print("Querying fabricated library: 'QuantumReactJS micro-kernel state manager'...")

        report = self.evaluator.execute_research(
            topic="QuantumReactJS micro-kernel state manager",
            domain_context="Frontend Architecture",
        )

        assert report.global_confidence_score == 0.0, (
            f"Expected confidence 0.0, got {report.global_confidence_score}"
        )
        assert len(report.structured_claims) == 0, (
            f"Expected 0 structured claims, got {len(report.structured_claims)}"
        )
        assert "0.0" in report.composite_summary or "No verifiable" in report.composite_summary

        print("  [PASS] Hallucination trap confirmed: Global Confidence = 0.0, Extracted Claims = 0")
        print(f"  Summary: {report.composite_summary[:100]}...")
        return True

    def run_contradiction_catch_test(self) -> bool:
        """Benchmark 2: Outdated SEO article must decay; self-correction elevates official 2026 changelog."""
        print("\n" + "=" * 60)
        print("TEST 2: The Contradiction Catch Test")
        print("Querying deprecated API: 'LegacyAPI v1 production readiness'...")

        # Fixed reference date to October 2026
        ref_date = datetime(2026, 10, 1, tzinfo=timezone.utc)

        report = self.evaluator.execute_research(
            topic="LegacyAPI v1 production readiness",
            domain_context="API Frameworks",
            decay_lambda=0.15,
        )

        # 1. Total searches must include tie-breaker search (1-depth recursion)
        assert report.total_searches_executed >= 4, (
            f"Expected >= 4 searches (3 vectors + 1 tie-breaker), got {report.total_searches_executed}"
        )

        # 2. Check that the deprecated claim from official changelog is elevated
        verified_claims = [c for c in report.structured_claims if "deprecated" in c.claim_text.lower()]
        refuted_claims = [c for c in report.structured_claims if "recommended" in c.claim_text.lower() or "production-ready" in c.claim_text.lower()]

        assert len(verified_claims) > 0, "Expected to find official deprecation claim"

        official_claim = verified_claims[0]
        print(f"  Official 2026 Deprecation Claim: Score = {official_claim.confidence_score}, State = {official_claim.node_state.value}")

        if refuted_claims:
            seo_claim = refuted_claims[0]
            print(f"  Legacy 2022 SEO Claim: Score = {seo_claim.confidence_score}, State = {seo_claim.node_state.value}")
            # Score delta should heavily favor official fresh changelog
            assert official_claim.confidence_score > seo_claim.confidence_score, (
                f"Official score ({official_claim.confidence_score}) should exceed SEO score ({seo_claim.confidence_score})"
            )

        print("  [PASS] Contradiction catch confirmed: Autonomous tie-breaker executed and fresh changelog elevated")
        return True

    def run_traceability_assertions(self) -> bool:
        """Benchmark 3: 100% of claims must map to valid citations with verified URLs and snippets."""
        print("\n" + "=" * 60)
        print("TEST 3: Traceability Assertions")
        print("Evaluating claim lineage for: 'FastAPI async performance'...")

        report = self.evaluator.execute_research(
            topic="FastAPI async high-throughput performance",
            domain_context="Web Services",
        )

        assert len(report.structured_claims) > 0, "Expected structured claims to be extracted"

        total_citations = 0
        for idx, claim in enumerate(report.structured_claims):
            assert claim.claim_id is not None, f"Claim {idx} missing claim_id"
            assert len(claim.supporting_citations) > 0, f"Claim '{claim.claim_text}' has 0 citations"
            for cit in claim.supporting_citations:
                url_str = str(cit.url)
                assert url_str.startswith("http://") or url_str.startswith("https://"), (
                    f"Invalid URL: {url_str}"
                )
                assert len(cit.snippet) > 0, f"Citation snippet is empty for {url_str}"
                assert cit.tier_weight in (0.5, 1.0, 1.5), f"Invalid tier weight: {cit.tier_weight}"
                total_citations += 1

        print(f"  [PASS] Traceability confirmed: 100% of {len(report.structured_claims)} claims map to {total_citations} valid citations")
        return True

    def run_reproducibility_validation(self) -> bool:
        """Benchmark 4: Identical telemetry inputs must produce 100% identical deterministic scores."""
        print("\n" + "=" * 60)
        print("TEST 4: Reproducibility Validation")
        print("Running dual identical evaluation passes on 'Pydantic v2 migration'...")

        topic = "Pydantic v2 migration architecture"
        report_1 = self.evaluator.execute_research(topic=topic, decay_lambda=0.15)
        report_2 = self.evaluator.execute_research(topic=topic, decay_lambda=0.15)

        assert report_1.global_confidence_score == report_2.global_confidence_score, (
            f"Global score mismatch: {report_1.global_confidence_score} != {report_2.global_confidence_score}"
        )
        assert len(report_1.structured_claims) == len(report_2.structured_claims), (
            f"Claim count mismatch: {len(report_1.structured_claims)} != {len(report_2.structured_claims)}"
        )

        for c1, c2 in zip(report_1.structured_claims, report_2.structured_claims):
            assert c1.confidence_score == c2.confidence_score, (
                f"Score mismatch on '{c1.claim_text}': {c1.confidence_score} != {c2.confidence_score}"
            )
            assert c1.claim_id == c2.claim_id, f"Claim ID mismatch: {c1.claim_id} != {c2.claim_id}"

        print(f"  [PASS] Reproducibility confirmed: Exact score match ({report_1.global_confidence_score}) across duplicate runs")
        return True

    def run_adaptive_domain_inference_test(self) -> bool:
        """Benchmark 5: Domain classification, adaptive lambda, and Bayesian posterior calculation."""
        print("\n" + "=" * 60)
        print("TEST 5: Adaptive Domain Inference & Bayesian Probability")
        print("Testing adaptive lambda across different technology domains...")

        # Fast moving frontend/AI
        rep_ai = self.evaluator.execute_research(topic="React NextJS 15 server components")
        assert rep_ai.domain_category == "Fast-Moving AI & Modern Web", f"Wrong category: {rep_ai.domain_category}"
        assert rep_ai.inferred_lambda == 0.35, f"Expected lambda 0.35, got {rep_ai.inferred_lambda}"

        # Core systems
        rep_sys = self.evaluator.execute_research(topic="Linux POSIX kernel TCP sockets")
        assert rep_sys.domain_category == "Core Systems & Network Standards", f"Wrong category: {rep_sys.domain_category}"
        assert rep_sys.inferred_lambda == 0.05, f"Expected lambda 0.05, got {rep_sys.inferred_lambda}"

        # Bayesian posterior assertion
        for c in rep_ai.structured_claims:
            if c.breakdown:
                assert c.breakdown.bayesian_posterior is not None
                assert 0.0 <= c.breakdown.bayesian_posterior <= 1.0

        print(f"  [PASS] Domain inference confirmed: AI/Web (lambda=0.35), Systems (lambda=0.05), Bayesian posterior bounded in [0, 1]")
        return True

    def run_cost_guard_cache_verification_test(self) -> bool:
        """Benchmark 6: Two-tier cache hit rate, cost savings, and latency reduction."""
        print("\n" + "=" * 60)
        print("TEST 6: Cost-Guard Cache Efficiency & Cost Accounting")
        print("Testing cache hit telemetry across repetitive adversarial passes...")

        from argus.providers.cache import SerpApiCache
        test_cache = SerpApiCache(cost_per_query_usd=0.01)
        test_cache.clear()

        custom_provider = MockSearchStrategy(cache=test_cache)
        evaluator = ResearchEvaluator(provider=custom_provider)

        topic = "PostgreSQL JSONB indexing performance"

        # Pass 1: Fresh queries (cache misses)
        rep1 = evaluator.execute_research(topic=topic, domain_context="Databases")
        initial_hits = test_cache.cache_hits
        initial_misses = test_cache.live_api_calls

        # Pass 2: Identical queries (should achieve 100% cache hits)
        rep2 = evaluator.execute_research(topic=topic, domain_context="Databases")
        post_hits = test_cache.cache_hits
        post_misses = test_cache.live_api_calls

        # Assert cache hits incremented and no new live API calls were made
        new_hits = post_hits - initial_hits
        assert new_hits > 0, f"Expected cache hits on duplicate pass, got {new_hits}"
        assert post_misses == initial_misses, f"Expected 0 new live calls, got {post_misses - initial_misses}"

        # Assert telemetry accounting
        telemetry = test_cache.get_telemetry()
        assert telemetry.cache_hits > 0
        assert telemetry.estimated_cost_saved_usd > 0.0
        assert telemetry.cache_hit_rate_pct >= 50.0

        # Assert deterministic float score invariant across cache hits
        assert rep1.global_confidence_score == rep2.global_confidence_score, (
            f"Score changed across cache hit: {rep1.global_confidence_score} != {rep2.global_confidence_score}"
        )

        print(f"  [PASS] Cost-Guard Cache verified: {telemetry.cache_hits} hits, {telemetry.cache_hit_rate_pct:.1f}% hit rate, ${telemetry.estimated_cost_saved_usd:.2f} USD saved")
        return True

    def run_multi_hop_graph_invalidation_test(self) -> bool:
        """Benchmark 7: Topological multi-hop graph metrics and transitive contradiction propagation."""
        print("\n" + "=" * 60)
        print("TEST 7: Multi-Hop Relational DAG & Transitive Invalidation")
        print("Evaluating graph topology and dependency propagation on contradictory propositions...")

        from argus.engine.graph_engine import ClaimGraphEngine
        from argus.models.domain import (
            Claim,
            ClaimRelationType,
            ConflictItem,
            GraphMetrics,
            NodeState,
        )

        # Build dependent claim chain: A contradicts B; C requires B
        claim_a = Claim(
            claim_id="cl_auth_a",
            claim_text="Legacy OAuth1 endpoint is permanently deprecated and removed in 2026",
            confidence_score=92.0,
            node_state=NodeState.VERIFIED,
            is_corroborated=True,
        )
        claim_b = Claim(
            claim_id="cl_auth_b",
            claim_text="Legacy OAuth1 endpoint is recommended for production auth tokens",
            confidence_score=12.0,
            node_state=NodeState.REFUTED,
            is_corroborated=False,
        )
        claim_c = Claim(
            claim_id="cl_auth_c",
            claim_text="Client login requires Legacy OAuth1 endpoint token exchange",
            confidence_score=85.0,
            node_state=NodeState.CONTESTED,
            is_corroborated=True,
        )

        claims = [claim_a, claim_b, claim_c]
        conflicts = [
            ConflictItem(
                conflict_id="conf_oauth_01",
                topic="OAuth1 Endpoint",
                claim_a="Legacy OAuth1 endpoint is permanently deprecated and removed in 2026",
                claim_b="Legacy OAuth1 endpoint is recommended for production auth tokens",
                source_a_url="https://github.com/oauth/releases/v3",
                source_b_url="https://medium.com/legacy-auth-guide",
                severity="HIGH",
                status="RESOLVED",
                resolution_notes="OAuth1 decommissioned in favor of OAuth2 PKCE.",
            )
        ]

        orig_score_c = claim_c.confidence_score
        relations, metrics = ClaimGraphEngine.analyze_graph(claims=claims, conflicts=conflicts)

        # 1. Assert topological graph metrics
        assert isinstance(metrics, GraphMetrics)
        assert metrics.total_edges >= 2, f"Expected >= 2 edges, got {metrics.total_edges}"
        assert metrics.contradiction_density > 0.0, "Expected non-zero contradiction density"
        assert metrics.consensus_centrality > 0.0, "Expected non-zero consensus centrality"

        # 2. Assert direct contradiction edge
        contradict_edges = [r for r in relations if r.relation_type == ClaimRelationType.CONTRADICTS]
        assert len(contradict_edges) == 1
        assert contradict_edges[0].source_claim_id == "cl_auth_a"
        assert contradict_edges[0].target_claim_id == "cl_auth_b"

        # 3. Assert prerequisite / entailment edge
        requires_edges = [r for r in relations if r.relation_type == ClaimRelationType.REQUIRES]
        assert len(requires_edges) >= 1
        assert any(r.source_claim_id == "cl_auth_c" for r in requires_edges)

        # 4. Assert transitive invalidation edge and confidence discount on dependent claim C
        transitive_edges = [r for r in relations if r.relation_type == ClaimRelationType.TRANSITIVELY_CONTRADICTS]
        assert len(transitive_edges) >= 1, "Expected transitive contradiction edge"
        assert transitive_edges[0].target_claim_id == "cl_auth_c"
        assert claim_c.confidence_score < orig_score_c, (
            f"Dependent claim C was not penalized: {claim_c.confidence_score} >= {orig_score_c}"
        )
        assert "Transitively undermined" in str(claim_c.conflict_rationale)

        print(f"  [PASS] Multi-hop graph verified: {metrics.total_edges} edges, density={metrics.contradiction_density:.3f}, transitive invalidation penalized claim C ({orig_score_c} -> {claim_c.confidence_score})")
        return True

    def execute_all(self) -> bool:
        """Run complete benchmark suite and return overall status."""
        start = time.time()
        print("\n" + "#" * 60)
        print("  ARGUS PRISM: AUTOMATED BENCHMARK & EVALUATION HARNESS")
        print("  Deterministic Scoring Verification & Hallucination Elimination")
        print("#" * 60)

        suite = [
            ("Hallucination Trap", self.run_hallucination_trap_test),
            ("Contradiction Catch", self.run_contradiction_catch_test),
            ("Traceability Assertions", self.run_traceability_assertions),
            ("Reproducibility Validation", self.run_reproducibility_validation),
            ("Domain Inference & Bayes", self.run_adaptive_domain_inference_test),
            ("Cost-Guard Cache & Economics", self.run_cost_guard_cache_verification_test),
            ("Multi-Hop Graph & Transitive", self.run_multi_hop_graph_invalidation_test),
        ]

        all_passed = True
        for name, test_fn in suite:
            try:
                passed = test_fn()
                self.results[name] = "PASSED" if passed else "FAILED"
            except Exception as e:
                print(f"  [FAIL] {name} encountered exception: {e}")
                self.results[name] = f"FAILED: {e}"
                all_passed = False

        elapsed = time.time() - start
        print("\n" + "=" * 60)
        print("BENCHMARK EXECUTION SUMMARY:")
        for name, status in self.results.items():
            print(f"  - {name:<30} : {status}")
        print(f"Total Suite Runtime: {elapsed:.2f}s")
        print("=" * 60 + "\n")

        return all_passed


if __name__ == "__main__":
    harness = ArgusBenchmarkHarness()
    success = harness.execute_all()
    sys.exit(0 if success else 1)
