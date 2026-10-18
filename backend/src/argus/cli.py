"""ARGUS PRISM: Interactive Terminal CLI."""

import argparse
import json
import sys
from typing import Optional

from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import NodeState, ValidationVerdict
from argus.providers import (
    DuckDuckGoSearchStrategy,
    ISearchProvider,
    MockSearchStrategy,
    WebSearchStrategy,
    get_provider,
)

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def resolve_provider(args) -> ISearchProvider:
    """Resolve active search provider based on CLI arguments."""
    provider_name = getattr(args, "provider", None)
    if provider_name:
        return get_provider(provider_name, fallback_to_mock=True)
    if getattr(args, "live", False):
        return WebSearchStrategy(fallback_to_mock=True)
    return MockSearchStrategy()


# ANSI Color formatting
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def format_state_badge(state: NodeState) -> str:
    if state == NodeState.VERIFIED:
        return f"{Colors.GREEN}[VERIFIED]{Colors.RESET}"
    elif state == NodeState.CONTESTED:
        return f"{Colors.YELLOW}[CONTESTED]{Colors.RESET}"
    elif state == NodeState.REFUTED:
        return f"{Colors.DIM}[REFUTED]{Colors.RESET}"
    else:
        return f"{Colors.RED}[WEAK]{Colors.RESET}"


def format_verdict_badge(verdict: ValidationVerdict) -> str:
    if verdict == ValidationVerdict.FACTUALLY_SOUND:
        return f"{Colors.GREEN}[FACTUALLY SOUND]{Colors.RESET}"
    elif verdict == ValidationVerdict.PARTIALLY_CONTESTED:
        return f"{Colors.YELLOW}[PARTIALLY CONTESTED]{Colors.RESET}"
    else:
        return f"{Colors.RED}[HIGH HALLUCINATION RISK]{Colors.RESET}"


def render_confidence_meter(score: float) -> str:
    total_blocks = 20
    filled = int(round(score / 100.0 * total_blocks))
    empty = total_blocks - filled
    bar = f"[{'█' * filled}{'░' * empty}]"
    if score >= 70:
        return f"{Colors.GREEN}{bar} {score:.1f}%{Colors.RESET}"
    elif score >= 50:
        return f"{Colors.YELLOW}{bar} {score:.1f}%{Colors.RESET}"
    else:
        return f"{Colors.RED}{bar} {score:.1f}%{Colors.RESET}"


def cmd_research(args):
    """Execute adversarial research via CLI."""
    provider = resolve_provider(args)
    evaluator = ResearchEvaluator(provider=provider, default_lambda=args.decay_lambda)

    print(f"\n{Colors.BOLD}{Colors.CYAN}🛡️  ARGUS PRISM: Initiating Evidence Research{Colors.RESET}")
    print(f"Topic: {Colors.BOLD}{args.topic}{Colors.RESET}")
    print(f"Provider: {Colors.DIM}{provider.provider_name}{Colors.RESET}")
    if args.domain:
        print(f"Domain Context: {args.domain}")
    print("-" * 65)

    report = evaluator.execute_research(
        topic=args.topic,
        domain_context=args.domain,
        decay_lambda=args.decay_lambda,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
        return

    print(f"\n{Colors.BOLD}Domain Classification:{Colors.RESET} {report.domain_category or 'General Software'}")
    print(f"{Colors.BOLD}Adaptive Decay Constant (λ):{Colors.RESET} {report.inferred_lambda or 0.15:.2f}")
    print(f"{Colors.BOLD}Global Deterministic Confidence:{Colors.RESET} {render_confidence_meter(report.global_confidence_score)}")
    print(f"{Colors.BOLD}Searches Executed:{Colors.RESET} {report.total_searches_executed} across telemetry streams")
    print(f"{Colors.BOLD}Execution Latency:{Colors.RESET} {report.execution_time_seconds or 0.0:.2f}s\n")

    print(f"{Colors.BOLD}EVALUATED ATOMIC CLAIMS:{Colors.RESET}")
    print("-" * 65)
    for idx, claim in enumerate(report.structured_claims, 1):
        badge = format_state_badge(claim.node_state)
        bayes_str = f" | Bayes: {claim.breakdown.bayesian_posterior:.2f}" if claim.breakdown and claim.breakdown.bayesian_posterior else ""
        print(f"{idx:2d}. {badge} ({claim.confidence_score:.1f}/100{bayes_str})")
        print(f"    {claim.claim_text}")
        if claim.supporting_citations:
            domain = str(claim.supporting_citations[0].url).split("/")[2]
            print(f"    {Colors.DIM}↳ Primary Source: {domain} ({claim.supporting_citations[0].tier_weight}x weight){Colors.RESET}")
        if claim.conflict_rationale:
            print(f"    {Colors.YELLOW}⚠️  {claim.conflict_rationale}{Colors.RESET}")
        print()

    if report.detailed_conflicts:
        print(f"\n{Colors.BOLD}⚔️  CONTRADICTION ANALYSIS & SELF-CORRECTION:{Colors.RESET}")
        print("-" * 65)
        for conf in report.detailed_conflicts:
            print(f"Conflict [{conf.topic}] ({conf.severity}):")
            print(f"  🔴 Opposing A: \"{conf.claim_a[:70]}...\"")
            print(f"  🟢 Opposing B: \"{conf.claim_b[:70]}...\"")
            print(f"  🛡️ Resolution: {conf.resolution_notes}\n")

    print(f"{Colors.BOLD}EXECUTIVE SUMMARY:{Colors.RESET}")
    print("-" * 65)
    print(report.composite_summary)
    print("-" * 65 + "\n")

    if getattr(args, "audio", None):
        audio_bytes, mime, script = evaluator.generate_audio_briefing(
            report=report,
            topic_or_client=args.topic,
            output_file=args.audio,
        )
        print(f"{Colors.GREEN}✓ Spoken Executive Audio Briefing saved to:{Colors.RESET} {args.audio} ({len(audio_bytes):,} bytes)\n")


def cmd_benchmark(args):
    """Execute CI/CD benchmark harness."""
    from evaluate import ArgusBenchmarkHarness
    harness = ArgusBenchmarkHarness()
    success = harness.execute_all()
    sys.exit(0 if success else 1)


def cmd_search(args):
    """Execute raw targeted search via adapter."""
    provider = resolve_provider(args)
    docs = provider.search(query=args.query, engine=args.engine, num_results=args.num)
    print(f"\nRetrieved {len(docs)} documents for '{args.query}' [{provider.provider_name}]:\n")
    for d in docs:
        print(f"[{d.source_domain}] {d.title}")
        print(f"URL: {d.url}")
        print(f"Snippet: {d.snippet[:120]}...\n")


def cmd_compare(args):
    """Execute head-to-head empirical technology comparison."""
    provider = resolve_provider(args)
    evaluator = ResearchEvaluator(provider=provider)

    print(f"\n{Colors.BOLD}{Colors.CYAN}⚖️  ARGUS PRISM: Head-to-Head Technology Comparison{Colors.RESET}")
    print(f"Comparing: {Colors.BOLD}{args.tech_a}{Colors.RESET} vs {Colors.BOLD}{args.tech_b}{Colors.RESET}")
    print(f"Provider: {Colors.DIM}{provider.provider_name}{Colors.RESET}")
    if args.domain:
        print(f"Domain Context: {args.domain}")
    print("-" * 75)

    report = evaluator.compare_technologies(
        tech_a=args.tech_a,
        tech_b=args.tech_b,
        domain_context=args.domain,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
        return

    print(f"\n{Colors.BOLD}{'Dimension':<35} | {args.tech_a[:12]:<12} | {args.tech_b[:12]:<12} | Winner{Colors.RESET}")
    print("-" * 75)
    for dim in report.trade_off_dimensions:
        winner_color = Colors.GREEN if dim.winner != "Tie" else Colors.YELLOW
        print(f"{dim.dimension_name:<35} | {dim.tech_a_score:>10.1f}% | {dim.tech_b_score:>10.1f}% | {winner_color}{dim.winner}{Colors.RESET}")
    print("-" * 75)

    print(f"\n{Colors.BOLD}🏆 RECOMMENDED WINNER:{Colors.RESET} {Colors.GREEN}{Colors.BOLD}{report.recommended_winner}{Colors.RESET}")
    print(f"{Colors.BOLD}VERDICT RATIONALE:{Colors.RESET} {report.verdict_rationale}\n")


def cmd_dossier(args):
    """Generate standalone enterprise HTML evidence dossier."""
    provider = resolve_provider(args)
    evaluator = ResearchEvaluator(provider=provider)

    print(f"\n{Colors.BOLD}{Colors.CYAN}📑 ARGUS PRISM: Compiling Evidence Dossier{Colors.RESET}")
    print(f"Topic: {Colors.BOLD}{args.topic}{Colors.RESET}")
    print(f"Provider: {Colors.DIM}{provider.provider_name}{Colors.RESET}")
    if args.domain:
        print(f"Domain Context: {args.domain}")

    report = evaluator.execute_research(
        topic=args.topic,
        domain_context=args.domain,
    )

    html_content = evaluator.generate_dossier(topic=args.topic)
    output_path = args.output
    if not output_path:
        safe_topic = "".join(c if c.isalnum() else "_" for c in args.topic).strip("_")
        output_path = f"dossier_{safe_topic[:30]}.html"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n{Colors.GREEN}✓ Successfully generated dossier:{Colors.RESET} {output_path}")
    print(f"File size: {len(html_content):,} bytes")
    print(f"Total claims evaluated: {len(report.structured_claims)}")
    print(f"Global deterministic confidence: {report.global_confidence_score:.1f}%\n")


def cmd_telemetry(args):
    """Inspect Cost-Guard cache and cost efficiency metrics."""
    from argus.providers.cache import SerpApiCache
    cache = SerpApiCache()
    telemetry = cache.get_telemetry()

    if args.json:
        print(telemetry.model_dump_json(indent=2))
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}💰 ARGUS PRISM: Cost-Guard & Cache Telemetry{Colors.RESET}")
    print("-" * 55)
    print(f"{Colors.BOLD}Total Queries Processed:{Colors.RESET}    {telemetry.total_searches}")
    print(f"{Colors.BOLD}Cache Hits (In-Memory/Disk):{Colors.RESET} {telemetry.cache_hits}")
    print(f"{Colors.BOLD}Live SerpApi Calls Made:{Colors.RESET}     {telemetry.live_api_calls}")
    print(f"{Colors.BOLD}Cache Hit Rate:{Colors.RESET}              {telemetry.cache_hit_rate_pct:.1f}%")
    print(f"{Colors.BOLD}Estimated API Cost Saved:{Colors.RESET}    ${telemetry.estimated_cost_saved_usd:.2f} USD")
    print(f"{Colors.BOLD}Average Query Latency:{Colors.RESET}       {telemetry.avg_latency_ms:.1f} ms")
    from argus.observability.sentry_tracer import SentryTracer
    sentry_status = f"{Colors.GREEN}Active (Distributed Spans & Flamegraphs){Colors.RESET}" if SentryTracer.is_enabled() else f"{Colors.DIM}Local Fallback (Set SENTRY_DSN in .env to stream){Colors.RESET}"
    print(f"{Colors.BOLD}Sentry Agent Tracing:{Colors.RESET}       {sentry_status}")
    print("-" * 55 + "\n")


def cmd_mcp(args):
    """Start the ARGUS PRISM Model Context Protocol server."""
    from argus.mcp.server import create_mcp_server
    provider = resolve_provider(args)
    server = create_mcp_server(provider=provider)

    print(f"{Colors.CYAN}Starting ARGUS PRISM MCP Server on transport '{args.transport}' [{provider.provider_name}]...{Colors.RESET}", file=sys.stderr)
    if args.transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        server.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        server.run(transport="stdio")


def cmd_validate(args):
    """Validate an LLM-generated response or user statement against empirical evidence."""
    input_text = args.text
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            print(f"{Colors.RED}Error reading file '{args.file}': {e}{Colors.RESET}")
            sys.exit(1)

    if not input_text or not input_text.strip():
        print(f"{Colors.RED}Error: No input text provided to validate. Provide text as argument or via --file.{Colors.RESET}")
        sys.exit(1)

    provider = resolve_provider(args)
    evaluator = ResearchEvaluator(provider=provider)

    print(f"\n{Colors.BOLD}{Colors.CYAN}🛡️  ARGUS PRISM: LLM Response Validation Audit{Colors.RESET}")
    print(f"Text Length: {len(input_text)} characters")
    print(f"Provider: {Colors.DIM}{provider.provider_name}{Colors.RESET}")
    if args.topic:
        print(f"Anchor Topic: {Colors.BOLD}{args.topic}{Colors.RESET}")
    if args.domain:
        print(f"Domain Context: {args.domain}")
    llm_backend = getattr(args, "llm", None)
    if llm_backend:
        print(f"LLM Proposition Extractor: {Colors.DIM}{llm_backend}{Colors.RESET}")

    report = evaluator.validate_response(
        response_text=input_text,
        topic=args.topic,
        domain_context=args.domain,
        llm_backend=llm_backend,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
        return

    from argus.engine.audit_report import AuditReportGenerator
    client_name = getattr(args, "client", None) or "Client Deliverable"
    roi = AuditReportGenerator.calculate_freelancer_roi(report)

    print(f"\n{Colors.BOLD}Overall Verdict:{Colors.RESET} {format_verdict_badge(report.verdict)}")
    print(f"{Colors.BOLD}Factual Integrity Score:{Colors.RESET} {render_confidence_meter(report.overall_validity_score)}")
    print(
        f"{Colors.BOLD}Evaluated Propositions:{Colors.RESET} {report.total_claims_evaluated} "
        f"({Colors.GREEN}{report.verified_count} verified{Colors.RESET}, "
        f"{Colors.YELLOW}{report.contested_count} contested{Colors.RESET}, "
        f"{Colors.DIM}{report.refuted_count} refuted{Colors.RESET}, "
        f"{Colors.RED}{report.weak_count} weak{Colors.RESET})\n"
    )

    print(f"{Colors.BOLD}💼 SIDE-HUSTLE FREELANCER ROI:{Colors.RESET}")
    print(f"• Estimated manual research saved: {Colors.GREEN}{roi['estimated_hours_saved']} hours{Colors.RESET}")
    print(f"• Client billable value unlocked:  {Colors.GREEN}${roi['billable_value_usd']:.2f} USD{Colors.RESET} (@ ${roi['hourly_rate_usd']:.0f}/hr)")
    print(f"• Open-source compute cost:        {Colors.GREEN}$0.00{Colors.RESET} (Zero SaaS lock-in)")
    print(f"• Turnaround latency:              {roi['turnaround_time_seconds']}s\n")

    print(f"{Colors.BOLD}AUDIT SUMMARY:{Colors.RESET}")
    print(f"{report.summary}\n")

    print(f"{Colors.BOLD}PROPOSITION BREAKDOWN:{Colors.RESET}")
    print("-" * 70)
    for idx, prop in enumerate(report.validated_propositions, 1):
        badge = format_state_badge(prop.status)
        print(f"{idx:2d}. {badge} ({prop.confidence_score:.1f}/100)")
        print(f"    Assertion: \"{prop.proposition_text}\"")
        if prop.contradiction_warning:
            print(f"    {Colors.YELLOW}⚠️  Warning: {prop.contradiction_warning}{Colors.RESET}")
        if prop.suggested_correction:
            print(f"    {Colors.CYAN}💡 Suggested Correction: {prop.suggested_correction}{Colors.RESET}")
        if prop.citations:
            domain = str(prop.citations[0].url).split("/")[2] if "/" in str(prop.citations[0].url) else "evidence"
            print(f"    {Colors.DIM}↳ Primary Source: {domain} ({prop.citations[0].tier_weight}x weight){Colors.RESET}")
        print()
    print("-" * 70 + "\n")

    # Export deliverables if requested
    if getattr(args, "export_report", None):
        html_dossier = evaluator.generate_audit_dossier(
            report=report,
            client_name=client_name,
            project_title=args.topic or "Factual Audit",
        )
        with open(args.export_report, "w", encoding="utf-8") as f:
            f.write(html_dossier)
        print(f"{Colors.GREEN}✓ Client HTML Audit Dossier saved to:{Colors.RESET} {args.export_report}")

    if getattr(args, "markdown_report", None):
        md_briefing = evaluator.generate_audit_markdown(
            report=report,
            client_name=client_name,
        )
        with open(args.markdown_report, "w", encoding="utf-8") as f:
            f.write(md_briefing)
        print(f"{Colors.GREEN}✓ Client Markdown Briefing saved to:{Colors.RESET} {args.markdown_report}")

    if getattr(args, "audio", None):
        audio_bytes, mime, script = evaluator.generate_audio_briefing(
            report=report,
            topic_or_client=client_name,
            output_file=args.audio,
        )
        print(f"{Colors.GREEN}✓ Spoken Audio Briefing saved to:{Colors.RESET} {args.audio} ({len(audio_bytes):,} bytes)")
        print(f"{Colors.DIM}Script: \"{script[:90]}...\"{Colors.RESET}\n")



def main():
    parser = argparse.ArgumentParser(
        prog="argus",
        description="ARGUS PRISM: Deterministic Evidence Intelligence Layer",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate command
    p_validate = subparsers.add_parser("validate", help="Validate an LLM response or proposition against empirical evidence")
    p_validate.add_argument("text", nargs="?", default=None, type=str, help="LLM response text or assertion to validate")
    p_validate.add_argument("--file", "-f", type=str, default=None, help="Path to text file containing LLM response")
    p_validate.add_argument("--topic", "-t", type=str, default=None, help="Anchor topic for evidence retrieval")
    p_validate.add_argument("--domain", "-d", type=str, default=None, help="Domain context")
    p_validate.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_validate.add_argument("--llm", choices=["heuristic", "gemma", "ollama"], default="heuristic", help="Proposition extraction backend (gemma=local Gemma 2 via Ollama, heuristic=regex)")
    p_validate.add_argument("--client", "-c", type=str, default="Client Deliverable", help="Client name for billable audit deliverable")
    p_validate.add_argument("--export-report", "-e", type=str, default=None, help="Export client-ready HTML audit dossier to path")
    p_validate.add_argument("--markdown-report", "-m", type=str, default=None, help="Export client Markdown briefing to path")
    p_validate.add_argument("--audio", "-a", type=str, default=None, help="Export 60-second spoken executive audio briefing (ElevenLabs)")
    p_validate.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_validate.add_argument("--json", action="store_true", help="Output raw JSON payload")
    p_validate.set_defaults(func=cmd_validate)

    # Research command
    p_research = subparsers.add_parser("research", help="Execute adversarial research and scoring")
    p_research.add_argument("topic", type=str, help="Research topic or technical claim")
    p_research.add_argument("--domain", "-d", type=str, default=None, help="Domain context")
    p_research.add_argument("--lambda", dest="decay_lambda", type=float, default=None, help="Decay constant lambda")
    p_research.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_research.add_argument("--audio", "-a", type=str, default=None, help="Export 60-second spoken executive audio briefing (ElevenLabs)")
    p_research.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_research.add_argument("--json", action="store_true", help="Output raw JSON payload")
    p_research.set_defaults(func=cmd_research)

    # Compare command
    p_compare = subparsers.add_parser("compare", help="Compare two technologies head-to-head")
    p_compare.add_argument("tech_a", type=str, help="First technology name or stack")
    p_compare.add_argument("tech_b", type=str, help="Second technology name or stack")
    p_compare.add_argument("--domain", "-d", type=str, default=None, help="Domain context")
    p_compare.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_compare.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_compare.add_argument("--json", action="store_true", help="Output raw JSON payload")
    p_compare.set_defaults(func=cmd_compare)

    # Dossier command
    p_dossier = subparsers.add_parser("dossier", help="Generate enterprise HTML evidence dossier")
    p_dossier.add_argument("topic", type=str, help="Research topic or technical claim")
    p_dossier.add_argument("--output", "-o", type=str, default=None, help="Output HTML file path")
    p_dossier.add_argument("--domain", "-d", type=str, default=None, help="Domain context")
    p_dossier.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_dossier.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_dossier.set_defaults(func=cmd_dossier)

    # Telemetry command
    p_telemetry = subparsers.add_parser("telemetry", help="View Cost-Guard cache and cost savings telemetry")
    p_telemetry.add_argument("--json", action="store_true", help="Output raw JSON payload")
    p_telemetry.set_defaults(func=cmd_telemetry)

    # MCP server command
    p_mcp = subparsers.add_parser("mcp", help="Run ARGUS PRISM Model Context Protocol server")
    p_mcp.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    p_mcp.add_argument("--host", default="0.0.0.0", help="Host interface for SSE/HTTP server")
    p_mcp.add_argument("--port", type=int, default=8000, help="Port for SSE/HTTP server")
    p_mcp.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_mcp.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_mcp.set_defaults(func=cmd_mcp)

    # Benchmark command
    p_benchmark = subparsers.add_parser("benchmark", help="Run deterministic verification benchmark suite")
    p_benchmark.set_defaults(func=cmd_benchmark)

    # Targeted search command
    p_search = subparsers.add_parser("search", help="Execute raw targeted search via adapter")
    p_search.add_argument("query", type=str, help="Search query")
    p_search.add_argument("--engine", "-e", type=str, default="google", help="Search engine")
    p_search.add_argument("--num", "-n", type=int, default=5, help="Number of results")
    p_search.add_argument("--provider", "-p", choices=["mock", "serpapi", "duckduckgo", "ddg"], default=None, help="Search provider (duckduckgo=free live, serpapi=live API, mock=offline)")
    p_search.add_argument("--live", action="store_true", help="Use live search API (SerpApi)")
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
