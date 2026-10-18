"""Head-to-head empirical technology comparison engine."""

from typing import Optional
from argus.engine.state_machine import ResearchStateMachine
from argus.models.domain import (
    ComparisonReport,
    EvidenceReport,
    NodeState,
    TradeOffDimension,
)
from argus.providers.base import ISearchProvider


class TechnologyComparator:
    """Executes dual adversarial research pipelines and synthesizes empirical trade-off matrices."""

    def __init__(self, provider: ISearchProvider):
        self.provider = provider

    def compare(
        self,
        tech_a: str,
        tech_b: str,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
    ) -> ComparisonReport:
        """Execute parallel empirical research and generate head-to-head comparison."""
        sm_a = ResearchStateMachine(search_provider=self.provider, decay_lambda=decay_lambda)
        sm_b = ResearchStateMachine(search_provider=self.provider, decay_lambda=decay_lambda)

        report_a = sm_a.execute(topic=tech_a, domain_context=domain_context)
        report_b = sm_b.execute(topic=tech_b, domain_context=domain_context)

        # Dimension 1: Global Deterministic Confidence
        score_a = report_a.global_confidence_score
        score_b = report_b.global_confidence_score
        winner_conf = tech_a if score_a > score_b else (tech_b if score_b > score_a else "Tie")
        dim_conf = TradeOffDimension(
            dimension_name="Global Evidence Confidence",
            tech_a_score=score_a,
            tech_b_score=score_b,
            winner=winner_conf,
            notes=f"{winner_conf} demonstrated higher empirical backing across retrieved sources.",
        )

        # Dimension 2: Authoritative Backing (Tier 1 Verified Claims)
        t1_a = sum(1 for c in report_a.structured_claims if c.node_state == NodeState.VERIFIED)
        t1_b = sum(1 for c in report_b.structured_claims if c.node_state == NodeState.VERIFIED)
        scale_t1_a = min(100.0, t1_a * 25.0)
        scale_t1_b = min(100.0, t1_b * 25.0)
        winner_t1 = tech_a if scale_t1_a > scale_t1_b else (tech_b if scale_t1_b > scale_t1_a else "Tie")
        dim_t1 = TradeOffDimension(
            dimension_name="Authoritative Verified Claims",
            tech_a_score=scale_t1_a,
            tech_b_score=scale_t1_b,
            winner=winner_t1,
            notes=f"{tech_a} yielded {t1_a} verified propositions vs {tech_b}'s {t1_b}.",
        )

        # Dimension 3: Technical Debt & Issue Density (Inverted: fewer conflicts is better)
        debt_a = len(report_a.detailed_conflicts) + sum(1 for c in report_a.structured_claims if c.node_state == NodeState.WEAK)
        debt_b = len(report_b.detailed_conflicts) + sum(1 for c in report_b.structured_claims if c.node_state == NodeState.WEAK)
        clean_a = max(0.0, 100.0 - debt_a * 15.0)
        clean_b = max(0.0, 100.0 - debt_b * 15.0)
        winner_debt = tech_a if clean_a > clean_b else (tech_b if clean_b > clean_a else "Tie")
        dim_debt = TradeOffDimension(
            dimension_name="Operational Stability (Low Debt)",
            tech_a_score=clean_a,
            tech_b_score=clean_b,
            winner=winner_debt,
            notes=f"{tech_a} exhibited {debt_a} risk markers vs {tech_b}'s {debt_b}.",
        )

        # Dimension 4: Ecosystem Freshness (Average Decay Multiplier)
        decays_a = [c.breakdown.decay_multiplier for c in report_a.structured_claims if c.breakdown]
        decays_b = [c.breakdown.decay_multiplier for c in report_b.structured_claims if c.breakdown]
        fresh_a = round((sum(decays_a) / len(decays_a) * 100.0), 1) if decays_a else 50.0
        fresh_b = round((sum(decays_b) / len(decays_b) * 100.0), 1) if decays_b else 50.0
        winner_fresh = tech_a if fresh_a > fresh_b else (tech_b if fresh_b > fresh_a else "Tie")
        dim_fresh = TradeOffDimension(
            dimension_name="Ecosystem Freshness & Recency",
            tech_a_score=fresh_a,
            tech_b_score=fresh_b,
            winner=winner_fresh,
            notes=f"Temporal recency weighted by e^(-lambda*t): {tech_a} ({fresh_a}%) vs {tech_b} ({fresh_b}%).",
        )

        dimensions = [dim_conf, dim_t1, dim_debt, dim_fresh]

        # Overall recommendation
        wins_a = sum(1 for d in dimensions if d.winner == tech_a)
        wins_b = sum(1 for d in dimensions if d.winner == tech_b)

        if wins_a > wins_b:
            recommended = tech_a
            rationale = (
                f"{tech_a} outperforms {tech_b} on {wins_a} of 4 evaluation dimensions, "
                f"demonstrating superior authoritative validation and lower operational risk."
            )
        elif wins_b > wins_a:
            recommended = tech_b
            rationale = (
                f"{tech_b} outperforms {tech_a} on {wins_b} of 4 evaluation dimensions, "
                f"presenting fresher ecosystem activity and higher empirical confidence."
            )
        else:
            recommended = "Conditional Trade-Off"
            rationale = (
                f"Both technologies tied across core metrics. Select {tech_a} if prioritizing stability, "
                f"or {tech_b} if prioritizing freshness and community activity."
            )

        summary = (
            f"### Empirical Technology Comparison: {tech_a} vs {tech_b}\n\n"
            f"**Verdict:** **{recommended}**  \n"
            f"**Rationale:** {rationale}\n\n"
            f"| Metric Dimension | {tech_a} Score | {tech_b} Score | Winner |\n"
            f"| :--- | :--- | :--- | :--- |\n"
        )
        for d in dimensions:
            summary += f"| {d.dimension_name} | {d.tech_a_score:.1f} | {d.tech_b_score:.1f} | **{d.winner}** |\n"

        return ComparisonReport(
            tech_a=tech_a,
            tech_b=tech_b,
            report_a=report_a,
            report_b=report_b,
            trade_off_dimensions=dimensions,
            recommended_winner=recommended,
            verdict_rationale=rationale,
            comparison_summary=summary,
        )
