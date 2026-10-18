"""ResearchEvaluator Facade hiding planning, search, pipeline, and state machine complexities."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from argus.engine.comparator import TechnologyComparator
from argus.engine.dossier import DossierGenerator
from argus.engine.state_machine import ResearchStateMachine
from argus.models.domain import (
    Citation,
    Claim,
    ComparisonReport,
    ConflictItem,
    EvidenceReport,
    RawDocument,
    ValidationReport,
)
from argus.observability.sentry_tracer import SentryTracer
from argus.providers.base import ISearchProvider
from argus.providers.web_search import WebSearchStrategy

logger = logging.getLogger(__name__)


class ResearchEvaluator:
    """Facade pattern: unified high-level interface for AI agents and the MCP Server."""

    def __init__(self, provider: Optional[ISearchProvider] = None, default_lambda: Optional[float] = None):
        SentryTracer.init_tracer()
        self.provider = provider or WebSearchStrategy()
        self.default_lambda = default_lambda
        self._last_report: Optional[EvidenceReport] = None
        self._last_topic: Optional[str] = None
        self._claim_index: Dict[str, Claim] = {}
        self._conflict_index: Dict[str, ConflictItem] = {}

    def execute_research(
        self,
        topic: str,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
        reference_date: Optional[datetime] = None,
        engine: Optional[str] = None,
    ) -> EvidenceReport:
        """Run full end-to-end research workflow."""
        eff_lambda = decay_lambda if decay_lambda is not None else self.default_lambda
        state_machine = ResearchStateMachine(
            search_provider=self.provider,
            decay_lambda=eff_lambda,
        )

        report = state_machine.execute(
            topic=topic,
            domain_context=domain_context,
            reference_date=reference_date,
            decay_lambda_override=eff_lambda,
            engine_override=engine,
        )

        # Index claims and conflicts for inspection tools
        self._last_report = report
        self._last_topic = topic
        self._claim_index = {c.claim_id: c for c in report.structured_claims if c.claim_id}
        self._conflict_index = {conf.conflict_id: conf for conf in report.detailed_conflicts}

        return report

    def compare_technologies(
        self,
        tech_a: str,
        tech_b: str,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
    ) -> ComparisonReport:
        """Run head-to-head empirical technology comparison."""
        with SentryTracer.trace_span(
            op="argus.comparison",
            description=f"Compare {tech_a} vs {tech_b}",
            data={"tech_a": tech_a, "tech_b": tech_b},
        ):
            comparator = TechnologyComparator(provider=self.provider)
            return comparator.compare(
                tech_a=tech_a,
                tech_b=tech_b,
                domain_context=domain_context,
                decay_lambda=decay_lambda,
            )

    def validate_response(
        self,
        response_text: str,
        topic: Optional[str] = None,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
        llm_backend: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> ValidationReport:
        """Validate an LLM-generated response or user assertion against empirical evidence."""
        from argus.engine.validator import ResponseValidator
        validator = ResponseValidator(evaluator=self)
        return validator.validate(
            response_text=response_text,
            topic=topic,
            domain_context=domain_context,
            decay_lambda=decay_lambda,
            llm_backend=llm_backend,
            engine=engine,
        )

    def generate_audit_dossier(
        self,
        report: ValidationReport,
        client_name: str = "Client Briefing",
        project_title: str = "AI Content Factual Audit & Hallucination Assessment",
        hourly_rate_usd: float = 50.0,
    ) -> str:
        """Generate standalone client-ready HTML audit certificate and evidence dossier."""
        with SentryTracer.trace_span(
            op="argus.deliverable.html",
            description=f"Generate HTML audit dossier for {client_name}",
        ):
            from argus.engine.audit_report import AuditReportGenerator
            return AuditReportGenerator.generate_html_dossier(
                report=report,
                client_name=client_name,
                project_title=project_title,
                hourly_rate_usd=hourly_rate_usd,
            )

    def generate_audit_markdown(
        self,
        report: ValidationReport,
        client_name: str = "Client Briefing",
        hourly_rate_usd: float = 50.0,
    ) -> str:
        """Generate clean Markdown client briefing for Notion, Slack, or email."""
        from argus.engine.audit_report import AuditReportGenerator
        return AuditReportGenerator.generate_markdown_briefing(
            report=report,
            client_name=client_name,
            hourly_rate_usd=hourly_rate_usd,
        )

    def generate_audio_briefing(
        self,
        report: Union[ValidationReport, EvidenceReport],
        topic_or_client: str = "",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        output_file: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        """Generate 60-second spoken executive audio briefing via ElevenLabs.
        
        Returns:
            Tuple of (audio_bytes, mime_type, spoken_script)
        """
        with SentryTracer.trace_span(
            op="argus.audio_generation",
            description=f"Synthesize ElevenLabs briefing for {topic_or_client or 'Research'}",
            data={"voice_id": voice_id},
        ):
            from argus.audio.elevenlabs_client import ElevenLabsBriefing
            if isinstance(report, ValidationReport):
                script = ElevenLabsBriefing.create_script_from_validation(report, client_name=topic_or_client)
            else:
                script = ElevenLabsBriefing.create_script_from_research(report, topic=topic_or_client)
            audio_bytes, mime_type = ElevenLabsBriefing.synthesize_audio(script, voice_id=voice_id, output_file=output_file)
            return audio_bytes, mime_type, script

    def inspect_telemetry(self) -> Dict[str, Any]:
        """Return Cost-Guard caching and API credit telemetry."""
        cost_guard = self.provider.get_cost_guard_telemetry()
        if cost_guard:
            return cost_guard.model_dump()
        return {"status": "telemetry_unavailable"}

    def generate_dossier(self, topic: Optional[str] = None) -> str:
        """Generate standalone print-ready HTML evidence dossier."""
        if not self._last_report:
            raise ValueError("No research report available to generate dossier. Run execute_research first.")
        active_topic = topic or self._last_topic or "Evaluated Technical Claim"
        return DossierGenerator.generate_html(report=self._last_report, topic=active_topic)

    def execute_targeted_search(
        self,
        query: str,
        search_type: str = "google",
    ) -> List[RawDocument]:
        """Perform raw, normalized SerpApi retrieval via the adapter."""
        return self.provider.search(query=query, engine=search_type, num_results=5)

    def inspect_evidence(self, claim_id: str) -> List[Citation]:
        """Retrieve the raw SerpApi snippets and citations associated with a specific finding."""
        claim = self._claim_index.get(claim_id)
        if not claim:
            raise KeyError(f"Claim ID '{claim_id}' not found in active research cache.")
        return claim.supporting_citations

    def inspect_confidence(self, claim_id: str) -> Dict[str, Any]:
        """Return the mathematical breakdown of a specific score."""
        claim = self._claim_index.get(claim_id)
        if not claim:
            raise KeyError(f"Claim ID '{claim_id}' not found in active research cache.")

        if not claim.breakdown:
            return {
                "claim_id": claim_id,
                "confidence_score": claim.confidence_score,
                "formula": "No breakdown available",
            }

        return {
            "claim_id": claim_id,
            "claim_text": claim.claim_text,
            "confidence_score": claim.confidence_score,
            "base_score": claim.breakdown.base_score,
            "tier_weight": claim.breakdown.tier_weight,
            "age_months": claim.breakdown.age_months,
            "decay_lambda": claim.breakdown.decay_lambda,
            "decay_multiplier": claim.breakdown.decay_multiplier,
            "corroboration_bonus_percent": claim.breakdown.corroboration_bonus,
            "conflict_penalty_percent": claim.breakdown.conflict_penalty,
            "formula": claim.breakdown.formula,
            "is_corroborated": claim.is_corroborated,
            "node_state": claim.node_state.value,
        }

    def inspect_conflicts(self, claim_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return competing claims and opposing source URLs."""
        if not self._last_report:
            return []

        results = []
        for conf in self._last_report.detailed_conflicts:
            if claim_id:
                # Filter to specific claim
                claim = self._claim_index.get(claim_id)
                if claim and (claim.claim_text in (conf.claim_a, conf.claim_b)):
                    results.append(conf.model_dump())
            else:
                results.append(conf.model_dump())

        return results
