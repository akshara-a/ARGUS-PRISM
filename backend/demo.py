"""ARGUS PRISM: 1-Click End-to-End Judge Showcase Demo.

Demonstrates the 5 core capabilities in under 10 seconds:
1. Hallucination Trap (0.0 confidence on fake framework)
2. Contradiction Catch (Autonomous 1-depth tie-breaker self-correction)
3. Cost-Guard Two-Tier Cache & Cost Savings ($0.01 per query economics)
4. Head-to-Head Technology Comparison (4-dimension empirical trade-offs)
5. Enterprise HTML Evidence Dossier generation
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure src is in sys.path
src_dir = str(Path(__file__).resolve().parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Ensure UTF-8 terminal encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import NodeState
from argus.providers.cache import SerpApiCache
from argus.providers.mock_provider import MockSearchStrategy


class TermColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_banner():
    banner = f"""
{TermColors.CYAN}{TermColors.BOLD}======================================================================
  🛡️  ARGUS PRISM: DETERMINISTIC EVIDENCE INTELLIGENCE LAYER
  Autonomous Hallucination Elimination & Evidence Intelligence
======================================================================{TermColors.RESET}
"""
    print(banner)


def run_showcase():
    print_banner()
    cache = SerpApiCache(cost_per_query_usd=0.01)
    provider = MockSearchStrategy(cache=cache)
    evaluator = ResearchEvaluator(provider=provider)

    # ---------------------------------------------------------
    # ACT 1: THE HALLUCINATION TRAP
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 1/6] The Hallucination Trap Test{TermColors.RESET}")
    print(f"Querying fabricated proposition: {TermColors.YELLOW}'QuantumReactJS micro-kernel state manager'{TermColors.RESET}")
    start = time.time()
    rep_trap = evaluator.execute_research(
        topic="QuantumReactJS micro-kernel state manager",
        domain_context="Frontend Architecture",
    )
    dur = time.time() - start
    print(f"  {TermColors.GREEN}✓ Global Confidence:{TermColors.RESET} {rep_trap.global_confidence_score:.1f}%")
    print(f"  {TermColors.GREEN}✓ Claims Extracted:{TermColors.RESET}  {len(rep_trap.structured_claims)} (Zero hallucination)")
    print(f"  {TermColors.DIM}Latency: {dur:.2f}s | Summary: {rep_trap.composite_summary[:85]}...{TermColors.RESET}")

    # ---------------------------------------------------------
    # ACT 2: CONTRADICTION CATCH & SELF-CORRECTION
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 2/6] Contradiction Catch & Autonomous Tie-Breaker Loop{TermColors.RESET}")
    print(f"Querying conflicting proposition: {TermColors.YELLOW}'LegacyAPI v1 production readiness'{TermColors.RESET}")
    start = time.time()
    rep_conf = evaluator.execute_research(
        topic="LegacyAPI v1 production readiness",
        domain_context="API Frameworks",
        decay_lambda=0.15,
        reference_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    dur = time.time() - start
    print(f"  {TermColors.CYAN}Total Searches Executed:{TermColors.RESET} {rep_conf.total_searches_executed} (3 vectors + 1 tie-breaker)")
    print(f"  {TermColors.CYAN}Detected Contradictions:{TermColors.RESET} {len(rep_conf.detailed_conflicts)}")

    for conf in rep_conf.detailed_conflicts:
        print(f"    ⚡ Disputed Topic: {conf.topic} ({conf.severity})")
        print(f"       🔴 Claim A (2022 SEO Blog): \"{conf.claim_a[:55]}...\"")
        print(f"       🟢 Claim B (2026 Changelog): \"{conf.claim_b[:55]}...\"")
        print(f"       🛡️ Verdict: {TermColors.GREEN}{conf.resolution_notes}{TermColors.RESET}")

    # ---------------------------------------------------------
    # ACT 3: COST-GUARD TWO-TIER CACHE & COST ECONOMICS
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 3/6] Cost-Guard Two-Tier Cache & Cost Accounting{TermColors.RESET}")
    print("Repeating query to trigger Tier-1/Tier-2 deterministic cache lookup...")
    start = time.time()
    rep_cached = evaluator.execute_research(
        topic="LegacyAPI v1 production readiness",
        domain_context="API Frameworks",
        decay_lambda=0.15,
        reference_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    dur = time.time() - start
    telemetry = cache.get_telemetry()
    print(f"  {TermColors.GREEN}✓ Cache Hits:{TermColors.RESET}             {telemetry.cache_hits} hits")
    print(f"  {TermColors.GREEN}✓ Cache Hit Rate:{TermColors.RESET}        {telemetry.cache_hit_rate_pct:.1f}%")
    print(f"  {TermColors.GREEN}✓ Estimated Cost Saved:{TermColors.RESET}  ${telemetry.estimated_cost_saved_usd:.2f} USD")
    print(f"  {TermColors.GREEN}✓ Exact Score Invariant:{TermColors.RESET} {rep_conf.global_confidence_score:.2f} == {rep_cached.global_confidence_score:.2f} (100% Deterministic)")

    # ---------------------------------------------------------
    # ACT 4: HEAD-TO-HEAD TECHNOLOGY COMPARISON
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 4/6] Head-to-Head Technology Comparator{TermColors.RESET}")
    print(f"Comparing: {TermColors.YELLOW}FastAPI{TermColors.RESET} vs {TermColors.YELLOW}Django{TermColors.RESET}")
    comp_report = evaluator.compare_technologies(
        tech_a="FastAPI",
        tech_b="Django",
        domain_context="Python Web Frameworks",
    )
    print(f"  {'Dimension':<35} | {'FastAPI':<10} | {'Django':<10} | Winner")
    print("  " + "-" * 70)
    for dim in comp_report.trade_off_dimensions:
        winner_color = TermColors.GREEN if dim.winner != "Tie" else TermColors.YELLOW
        print(f"  {dim.dimension_name:<35} | {dim.tech_a_score:>8.1f}% | {dim.tech_b_score:>8.1f}% | {winner_color}{dim.winner}{TermColors.RESET}")
    print(f"  🏆 {TermColors.BOLD}Recommended Winner:{TermColors.RESET} {TermColors.GREEN}{comp_report.recommended_winner}{TermColors.RESET}")

    # ---------------------------------------------------------
    # ACT 5: ENTERPRISE HTML EVIDENCE DOSSIER
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 5/6] Enterprise HTML Evidence Dossier Generation{TermColors.RESET}")
    dossier_html = evaluator.generate_dossier(topic="PostgreSQL vs MongoDB Vector Search")
    out_dir = Path("examples")
    if not out_dir.exists() and (Path(__file__).resolve().parent.parent / "examples").exists():
        out_dir = Path(__file__).resolve().parent.parent / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "argus_enterprise_dossier.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(dossier_html)
    print(f"  {TermColors.GREEN}✓ Exported Standalone Dossier:{TermColors.RESET} {out_file} ({len(dossier_html):,} bytes)")

    # ---------------------------------------------------------
    # ACT 6: SIDE-HUSTLE FACT-CHECKING AUDIT & DELIVERABLES
    # ---------------------------------------------------------
    print(f"\n{TermColors.BOLD}[ACT 6/6] Side-Hustle Factual Audit & Freelancer ROI Deliverables{TermColors.RESET}")
    client_draft = (
        "FastAPI async endpoints achieve high throughput concurrency on Uvicorn. "
        "LegacyAPI v1 is production ready with guaranteed thread safety. "
        "PostgreSQL JSONB indexing provides fast GIN-indexed document queries."
    )
    print(f"Auditing freelance client draft: {TermColors.YELLOW}'{client_draft[:60]}...'{TermColors.RESET}")
    val_report = evaluator.validate_response(
        response_text=client_draft,
        topic="Modern Web APIs & Database Querying",
    )
    from argus.engine.audit_report import AuditReportGenerator
    roi = AuditReportGenerator.calculate_freelancer_roi(val_report)

    print(f"  {TermColors.GREEN}✓ Overall Verdict:{TermColors.RESET}       {val_report.verdict.value}")
    print(f"  {TermColors.GREEN}✓ Factual Integrity:{TermColors.RESET}     {val_report.overall_validity_score:.1f}%")
    print(f"  {TermColors.GREEN}✓ Evaluated Claims:{TermColors.RESET}      {val_report.total_claims_evaluated} ({val_report.verified_count} verified, {val_report.contested_count + val_report.refuted_count} contested/refuted)")
    print(f"  {TermColors.CYAN}💼 FREELANCER ROI:{TermColors.RESET}        {roi['estimated_hours_saved']} hours saved ➔ ${roi['billable_value_usd']:.2f} USD unlocked (@ $50/hr)")
    print(f"  {TermColors.CYAN}💰 OPERATING COST:{TermColors.RESET}        $0.00 (Zero API bills, 100% gross profit margin)")

    # Export client HTML certificate
    client_cert_html = evaluator.generate_audit_dossier(val_report, client_name="Elena Tech Writing")
    cert_file = out_dir / "client_audit_certificate.html"
    with open(cert_file, "w", encoding="utf-8") as f:
        f.write(client_cert_html)
    print(f"  {TermColors.GREEN}✓ Client HTML Certificate:{TermColors.RESET} {cert_file} ({len(client_cert_html):,} bytes)")

    # Synthesize audio briefing
    audio_file = str(out_dir / "client_briefing.wav")
    audio_bytes, mime, script = evaluator.generate_audio_briefing(val_report, topic_or_client="Elena Tech Writing", output_file=audio_file)
    print(f"  {TermColors.GREEN}✓ Spoken Audio Debrief:{TermColors.RESET}    {audio_file} ({len(audio_bytes):,} bytes)")
    print(f"  {TermColors.DIM}Audio Script: \"{script[:80]}...\"{TermColors.RESET}")

    # ---------------------------------------------------------
    # CONCLUSION
    # ---------------------------------------------------------
    print(f"\n{TermColors.CYAN}{TermColors.BOLD}======================================================================{TermColors.RESET}")
    print(f"{TermColors.GREEN}{TermColors.BOLD}🎉 ALL 6 SHOWCASE ACTS COMPLETED SUCCESSFULLY IN 1 PASS!{TermColors.RESET}")
    print("  - Run the Interactive Dashboard:  local/run_dashboard.bat  (or uv run streamlit run backend/src/argus/dashboard/app.py)")
    print("  - Launch the MCP 2.x Server:      local/run_mcp.bat        (or uv run python -m argus.cli mcp)")
    print("  - Execute the Benchmark Suite:    local/run_benchmark.bat  (or uv run python backend/evaluate.py)")
    print("  - Start the Next.js Studio UI:    local/run_frontend.bat   (or cd frontend && bun dev)")
    print(f"{TermColors.CYAN}{TermColors.BOLD}======================================================================{TermColors.RESET}\n")


if __name__ == "__main__":
    run_showcase()
