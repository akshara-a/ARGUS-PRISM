"""Model Context Protocol (MCP) Server for ARGUS PRISM."""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from mcp.server.mcpserver import MCPServer
from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import Citation, Claim, EvidenceReport, RawDocument
from argus.providers import (
    DuckDuckGoSearchStrategy,
    ISearchProvider,
    MockSearchStrategy,
    WebSearchStrategy,
    get_provider,
)

load_dotenv()
logger = logging.getLogger("argus.mcp")


def create_mcp_server(provider: Optional[ISearchProvider] = None) -> MCPServer:
    """Factory creating configured MCP Server with 9 core tools."""
    server = MCPServer(
        name="argus-prism",
        instructions="ARGUS PRISM: Deterministic Evidence Intelligence Layer backed by pluggable search telemetry",
    )

    # Initialize evaluator facade
    if provider is None:
        p_env = os.getenv("SEARCH_PROVIDER", "").lower().strip()
        if p_env:
            active_provider = get_provider(p_env, fallback_to_mock=True)
        else:
            api_key = os.getenv("SERPAPI_API_KEY", "")
            if api_key and not api_key.startswith("your_serpapi"):
                active_provider = WebSearchStrategy(api_key=api_key)
            else:
                # Deterministic mock fallback for offline or testing mode
                active_provider = MockSearchStrategy()
    else:
        active_provider = provider

    evaluator = ResearchEvaluator(provider=active_provider)

    @server.tool(
        name="execute_research",
        description="Executes adversarial research, deterministic credibility scoring, and self-correction on a given topic.",
    )
    def execute_research(
        topic: str,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Accepts topic and domain_context. Returns EvidenceReport conforming to Pydantic schema."""
        report = evaluator.execute_research(
            topic=topic,
            domain_context=domain_context,
            decay_lambda=decay_lambda,
        )
        return report.model_dump(mode="json")

    @server.tool(
        name="execute_targeted_search",
        description="Performs raw, normalized SerpApi search via the SerpApiAdapter into RawDocument models.",
    )
    def execute_targeted_search(
        query: str,
        search_type: str = "google",
    ) -> List[Dict[str, Any]]:
        """Perform normalized SerpApi retrieval via adapter."""
        docs = evaluator.execute_targeted_search(query=query, search_type=search_type)
        return [doc.model_dump(mode="json") for doc in docs]

    @server.tool(
        name="inspect_evidence",
        description="Retrieves the raw SerpApi snippets and citations associated with a specific claim finding.",
    )
    def inspect_evidence(claim_id: str) -> List[Dict[str, Any]]:
        """Retrieve raw citations for a given claim_id."""
        citations = evaluator.inspect_evidence(claim_id=claim_id)
        return [cit.model_dump(mode="json") for cit in citations]

    @server.tool(
        name="inspect_confidence",
        description="Returns the step-by-step mathematical breakdown and formula for a claim's deterministic confidence score.",
    )
    def inspect_confidence(claim_id: str) -> Dict[str, Any]:
        """Return the mathematical breakdown of a specific score."""
        return evaluator.inspect_confidence(claim_id=claim_id)

    @server.tool(
        name="inspect_conflicts",
        description="Returns competing claims and opposing source URLs detected during research.",
    )
    def inspect_conflicts(claim_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return competing claims and opposing source URLs."""
        return evaluator.inspect_conflicts(claim_id=claim_id)

    @server.tool(
        name="compare_technologies",
        description="Runs head-to-head empirical research comparing two technologies across confidence, debt, and freshness.",
    )
    def compare_technologies(
        tech_a: str,
        tech_b: str,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compare two technologies head-to-head and return trade-off matrix."""
        report = evaluator.compare_technologies(
            tech_a=tech_a,
            tech_b=tech_b,
            domain_context=domain_context,
            decay_lambda=decay_lambda,
        )
        return report.model_dump(mode="json")

    @server.tool(
        name="inspect_telemetry",
        description="Inspects Cost-Guard cache economics, cache hit rates, and estimated API credit savings.",
    )
    def inspect_telemetry() -> Dict[str, Any]:
        """Return Cost-Guard caching and credit savings metrics."""
        return evaluator.inspect_telemetry()

    @server.tool(
        name="generate_dossier",
        description="Generates an enterprise-grade standalone print-ready HTML evidence dossier for compliance audits.",
    )
    def generate_dossier(topic: Optional[str] = None) -> str:
        """Generate standalone HTML evidence dossier."""
        return evaluator.generate_dossier(topic=topic)

    @server.tool(
        name="validate_response",
        description="Audits an LLM-generated response or user statement against empirical evidence (Google, Google Scholar, Google News), catching hallucinations, deprecated claims, and providing corrections.",
    )
    def validate_response(
        response_text: str,
        topic: Optional[str] = None,
        domain_context: Optional[str] = None,
        decay_lambda: Optional[float] = None,
        engine: Optional[str] = "google",
    ) -> Dict[str, Any]:
        """Validate LLM propositions against empirical search evidence."""
        report = evaluator.validate_response(
            response_text=response_text,
            topic=topic,
            domain_context=domain_context,
            decay_lambda=decay_lambda,
            engine=engine,
        )
        return report.model_dump(mode="json")

    @server.tool(
        name="auto_repair_draft",
        description="Autonomously repairs factual errors, deprecations, and hallucinations in a technical draft, returning the corrected text and structured git-style diff blocks.",
    )
    def auto_repair_draft(
        draft_text: str,
        topic: Optional[str] = None,
        domain_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize factual remediation and return repaired text with diff."""
        from argus.engine.auto_fixer import FactualAutoFixer
        report = evaluator.validate_response(response_text=draft_text, topic=topic, domain_context=domain_context)
        fix_data = FactualAutoFixer.repair_document(draft_text, report)
        return {
            "verdict": report.verdict.value,
            "overall_validity_score": report.overall_validity_score,
            "fixes_count": fix_data["fixes_count"],
            "repaired_text": fix_data["repaired_text"],
            "diff_blocks": fix_data["diff_blocks"],
            "fixes_applied": fix_data["fixes_applied"],
        }

    @server.tool(
        name="crawl_and_audit_url",
        description="Crawls a live technical webpage or documentation URL, extracts text, and performs factual verification.",
    )
    def crawl_and_audit_url(
        url: str,
        max_words: Optional[int] = 400,
    ) -> Dict[str, Any]:
        """Fetch URL content and audit factual claims."""
        from argus.engine.url_crawler import WebpageAuditor
        page_data = WebpageAuditor.fetch_url_content(url=url, max_words=max_words or 400)
        report = evaluator.validate_response(response_text=page_data["content"], topic=page_data["title"])
        return {
            "url": page_data["url"],
            "title": page_data["title"],
            "word_count": page_data["word_count"],
            "verdict": report.verdict.value,
            "overall_validity_score": report.overall_validity_score,
            "summary": report.summary,
            "claims": [p.model_dump(mode="json") for p in report.validated_propositions],
        }

    @server.tool(
        name="export_academic_markdown",
        description="Exports a technical article as publication-ready Markdown with in-line numerical footnotes ([^1], [^2]) and an IEEE/APA bibliography based on live citations.",
    )
    def export_academic_markdown(
        text: str,
        topic: Optional[str] = None,
        style: str = "ieee",
    ) -> Dict[str, Any]:
        """Export publication markdown with numerical footnotes and bibliography."""
        from argus.engine.academic_exporter import AcademicExporter
        report = evaluator.validate_response(response_text=text, topic=topic)
        return AcademicExporter.export_publication_markdown(text, report, style=style)

    @server.tool(
        name="generate_verification_badge",
        description="Generates an embeddable SVG verification badge and copyable markdown/HTML snippets for GitHub READMEs, Notion, and technical articles.",
    )
    def generate_verification_badge(
        score: float,
        verdict: str = "FACTUALLY_SOUND",
        label: str = "ARGUS PRISM",
    ) -> Dict[str, Any]:
        """Generate verification badge SVG and embed snippets."""
        from argus.engine.badge_generator import BadgeGenerator
        svg = BadgeGenerator.generate_svg(score=score, verdict=verdict, left_label=label)
        md = BadgeGenerator.generate_markdown_snippet(score=score, verdict=verdict)
        html_code = BadgeGenerator.generate_html_snippet(score=score, verdict=verdict)
        return {
            "svg_badge": svg,
            "markdown_snippet": md,
            "html_snippet": html_code,
            "score": score,
            "verdict": verdict,
        }

    @server.tool(
        name="backboard_compare_models",
        description="Cross-examines a technical draft across open-weight models (Llama 3, Mistral, Gemma 2) using a single Backboard API key in-memory with zero persistence.",
    )
    def backboard_compare_models(
        text: str,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Cross-examine draft across open-weight models via Backboard."""
        from argus.llm.backboard_client import BackboardClient
        client = BackboardClient()
        return client.compare_open_weight_models(text=text, models=models)

    @server.tool(
        name="tabpfn_bayesian_uncertainty",
        description="Evaluates in-memory Bayesian credibility class probabilities and uncertainty confidence intervals (±σ) using TabPFN Prior-data Fitted Networks.",
    )
    def tabpfn_bayesian_uncertainty(
        tier_weight: float = 1.0,
        age_months: float = 0.0,
        corroboration_count: int = 1,
        conflict_count: int = 0,
        base_score: float = 90.0,
    ) -> Dict[str, Any]:
        """Compute in-memory Bayesian uncertainty metrics for a claim."""
        from argus.engine.tabpfn_oracle import TabPFNOracle
        return TabPFNOracle.evaluate_claim(
            tier_weight=tier_weight,
            age_months=age_months,
            corroboration_count=corroboration_count,
            conflict_count=conflict_count,
            base_score=base_score,
        )

    # --- MCP Resources ---
    @server.resource(
        uri="argus://reports/latest",
        name="latest_evidence_report",
        description="Returns the most recent EvidenceReport payload as a serialized JSON string.",
        mime_type="application/json",
    )
    def get_latest_evidence_report() -> str:
        """Read the latest generated evidence report."""
        if evaluator._last_report:
            return evaluator._last_report.model_dump_json(indent=2)
        return json.dumps({"status": "no_report_generated_yet"})

    @server.resource(
        uri="argus://conflicts/active",
        name="active_conflicts",
        description="Returns active and unresolved technical conflicts detected during the latest research session.",
        mime_type="application/json",
    )
    def get_active_conflicts() -> str:
        """Read active contradictions."""
        conflicts = evaluator.inspect_conflicts()
        return json.dumps(conflicts, indent=2)

    @server.resource(
        uri="argus://reports/dossier",
        name="evidence_dossier_html",
        description="Returns standalone print-ready HTML evidence dossier.",
        mime_type="text/html",
    )
    def get_dossier_html() -> str:
        """Read the HTML evidence dossier."""
        if evaluator._last_report:
            return evaluator.generate_dossier()
        return "<html><body><p>No research executed yet.</p></body></html>"

    @server.resource(
        uri="argus://graph/dot",
        name="evidence_dag_dot",
        description="Returns Graphviz DOT representation of the evidence directed acyclic graph.",
        mime_type="text/vnd.graphviz",
    )
    def get_evidence_dag_dot() -> str:
        """Generate DOT graph representation."""
        if not evaluator._last_report:
            return 'digraph EvidenceDAG { empty [label="No research executed"]; }'
        lines = ["digraph EvidenceDAG {", "  rankdir=LR;", "  node [shape=box, style=rounded];"]
        lines.append('  ROOT [label="Research Topic", fillcolor="#3b82f6", style=filled, fontcolor=white];')
        for claim in evaluator._last_report.structured_claims:
            cid = claim.claim_id or "claim"
            color = "#22c55e" if claim.confidence_score >= 70 else "#ef4444"
            clean_text = claim.claim_text.replace('"', '\\"')[:50]
            lines.append(f'  "{cid}" [label="{clean_text}\\nScore: {claim.confidence_score:.1f}", color="{color}"];')
            lines.append(f'  ROOT -> "{cid}";')
        lines.append("}")
        return "\n".join(lines)

    # --- MCP Prompts ---
    @server.prompt(
        name="adversarial_fact_check",
        description="Instructs client LLM to audit a developer assertion against empirical SerpApi telemetry.",
    )
    def adversarial_fact_check(statement: str) -> str:
        """Prompt template guiding adversarial verification."""
        return (
            f"You are an adversarial evidence intelligence evaluator using ARGUS PRISM.\n\n"
            f"Audit the following developer proposition: \"{statement}\"\n\n"
            f"Instructions:\n"
            f"1. Call `execute_research(topic='{statement}')` to retrieve deterministic scores and check for contradictions.\n"
            f"2. Inspect the mathematical decay formula using `inspect_confidence` for any claims with contested or low scores.\n"
            f"3. Highlight any official 2026 deprecation changelogs over legacy SEO blogs.\n"
            f"4. Deliver an authoritative, evidence-backed verdict citing exact URLs."
        )

    @server.prompt(
        name="migration_risk_audit",
        description="Audits a library upgrade for breaking changes and deprecations.",
    )
    def migration_risk_audit(library_name: str, target_version: str) -> str:
        """Prompt template for breaking changes migration audit."""
        return (
            f"Audit the migration path for '{library_name}' to version '{target_version}'.\n\n"
            f"Execute research on '{library_name} breaking changes deprecated features {target_version}' "
            f"using ARGUS PRISM tools to identify technical debt, memory leaks, or removed APIs."
        )

    @server.prompt(
        name="validate_response",
        description="Audits and validates an LLM-generated answer or proposition against empirical evidence (/argus-prism validate).",
    )
    def validate_response_prompt(response_text: str) -> str:
        """Prompt template guiding response validation against empirical search evidence."""
        return (
            f"You are an adversarial evidence intelligence evaluator using ARGUS PRISM.\n\n"
            f"Validate the following LLM-generated response or user statement:\n\"\"\"\n{response_text}\n\"\"\"\n\n"
            f"Instructions:\n"
            f"1. Call tool `validate_response(response_text=...)` to extract atomic propositions and compute empirical confidence.\n"
            f"2. Scrutinize any assertions marked as REFUTED or WEAK (hallucination or deprecation risk).\n"
            f"3. Quote the suggested corrections and corroborate with authoritative primary sources.\n"
            f"4. Output a clear factual audit with confidence metrics and citation links."
        )

    # Attach evaluator instance to server for direct programmatic access
    server.evaluator = evaluator
    return server


def main():
    """Run ARGUS PRISM MCP server via stdio, sse, or streamable-http transports."""
    import argparse

    parser = argparse.ArgumentParser(description="ARGUS PRISM MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface for SSE server")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server")

    args, unknown = parser.parse_known_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    logger.info("Starting ARGUS PRISM MCP Server on transport: %s", args.transport)

    mcp_server = create_mcp_server()
    if args.transport == "sse":
        mcp_server.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        mcp_server.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp_server.run(transport="stdio")



if __name__ == "__main__":
    main()
