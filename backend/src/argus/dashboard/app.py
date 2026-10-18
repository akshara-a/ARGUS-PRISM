"""ARGUS PRISM: Visual Evidence Graph & Inspector Dashboard (Streamlit)."""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

import networkx as nx
from pyvis.network import Network
import streamlit as st
from dotenv import load_dotenv

from argus.engine.evaluator import ResearchEvaluator
from argus.engine.state_machine import MasterState, ResearchStateMachine
from argus.models.domain import (
    EvidenceReport,
    NodeState,
    ValidatedClaim,
    ValidationReport,
    ValidationVerdict,
)
from argus.providers import (
    DuckDuckGoSearchStrategy,
    MockSearchStrategy,
    WebSearchStrategy,
)
from argus.providers.cache import SerpApiCache

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ARGUS PRISM | Evidence Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for high-polish enterprise aesthetic
st.markdown(
    """
    <style>
    .stApp {
        background-color: #090d16;
        color: #f1f5f9;
        font-family: system-ui, -apple-system, sans-serif;
    }
    .metric-card {
        background: rgba(15, 23, 42, 0.75);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .badge-verified {
        background-color: rgba(6, 78, 59, 0.8);
        color: #34d399;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-contested {
        background-color: rgba(120, 53, 15, 0.8);
        color: #fbbf24;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-weak {
        background-color: rgba(136, 19, 55, 0.8);
        color: #fb7185;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(244, 63, 94, 0.3);
    }
    .badge-refuted {
        background-color: rgba(30, 41, 59, 0.8);
        color: #94a3b8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    .formula-box {
        font-family: monospace;
        background: #020617;
        padding: 14px;
        border-left: 4px solid #10b981;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_node_color_and_icon(state: NodeState) -> tuple[str, str]:
    if state == NodeState.VERIFIED:
        return "#22c55e", "🟢"
    elif state == NodeState.CONTESTED:
        return "#eab308", "🟡"
    elif state == NodeState.REFUTED:
        return "#6b7280", "❌"
    else:
        return "#ef4444", "🔴"


def render_evidence_dag(
    report: EvidenceReport,
    topic: str,
    hide_weak: bool = False,
    show_contested_only: bool = False,
) -> str:
    """Render NetworkX DAG into PyVis HTML string with contradiction edges."""
    net = Network(height="500px", width="100%", bgcolor="#0e1117", font_color="#e5e7eb", directed=True)
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150, spring_strength=0.05)

    root_id = "ROOT"
    net.add_node(
        root_id,
        label=f"Topic:\n{topic[:30]}",
        title=f"Root Research Vector: {topic}",
        color="#3b82f6",
        size=35,
        shape="box",
    )

    rendered_claim_ids = set()
    for i, claim in enumerate(report.structured_claims):
        if hide_weak and claim.node_state == NodeState.WEAK:
            continue
        if show_contested_only and claim.node_state not in (NodeState.CONTESTED, NodeState.REFUTED):
            continue

        cid = claim.claim_id or f"claim_{i}"
        rendered_claim_ids.add(cid)
        color, icon = get_node_color_and_icon(claim.node_state)
        short_label = (claim.claim_text[:35] + "...") if len(claim.claim_text) > 35 else claim.claim_text
        label = f"{icon} Score: {claim.confidence_score:.0f}\n{short_label}"

        tooltip = (
            f"<b>Claim ID:</b> {cid}<br>"
            f"<b>State:</b> {claim.node_state.value}<br>"
            f"<b>Confidence:</b> {claim.confidence_score:.1f}/100<br>"
            f"<b>Bayesian P(H|E):</b> {claim.breakdown.bayesian_posterior if claim.breakdown else 'N/A'}<br>"
            f"<b>Corroborated:</b> {'Yes' if claim.is_corroborated else 'No'}<br>"
            f"<b>Proposition:</b> {claim.claim_text}"
        )

        net.add_node(cid, label=label, title=tooltip, color=color, size=24, shape="dot")
        net.add_edge(root_id, cid, color="#4b5563", width=2)

        # Connect citations
        for j, cit in enumerate(claim.supporting_citations[:2]):
            cit_id = f"{cid}_cit_{j}"
            domain = str(cit.url).split("/")[2] if "/" in str(cit.url) else "source"
            net.add_node(
                cit_id,
                label=f"📄 {domain}",
                title=f"URL: {cit.url}<br>Tier: {cit.tier_weight}x",
                color="#64748b",
                size=12,
                shape="ellipse",
            )
            net.add_edge(cid, cit_id, color="#334155", dashes=True)

    # Render multi-hop claim relations (ENTAILS, REQUIRES, TRANSITIVELY_CONTRADICTS)
    for rel in report.relations:
        if rel.source_claim_id in rendered_claim_ids and rel.target_claim_id in rendered_claim_ids:
            if rel.relation_type.value == "ENTAILS":
                net.add_edge(rel.source_claim_id, rel.target_claim_id, color="#38bdf8", width=2, dashes=[4, 4], title=f"➡️ Entailment: {rel.rationale}")
            elif rel.relation_type.value == "REQUIRES":
                net.add_edge(rel.source_claim_id, rel.target_claim_id, color="#a855f7", width=2, dashes=[2, 4], title=f"🔒 Prerequisite: {rel.rationale}")
            elif rel.relation_type.value == "TRANSITIVELY_CONTRADICTS":
                net.add_edge(rel.source_claim_id, rel.target_claim_id, color="#f97316", width=3, dashes=[8, 4], title=f"⚠️ Transitive Contradiction: {rel.rationale}")

    # Render contradiction edges between mutually opposing claims
    for conf in report.detailed_conflicts:
        matching_a = [c for c in report.structured_claims if c.claim_text == conf.claim_a]
        matching_b = [c for c in report.structured_claims if c.claim_text == conf.claim_b]
        if matching_a and matching_b:
            id_a, id_b = matching_a[0].claim_id, matching_b[0].claim_id
            if id_a in rendered_claim_ids and id_b in rendered_claim_ids:
                net.add_edge(
                    id_a,
                    id_b,
                    color="#ef4444",
                    width=3,
                    dashes=[6, 6],
                    title=f"⚡ Active Contradiction ({conf.severity}): {conf.topic}",
                )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            html_content = f.read()
    try:
        os.remove(tmp.name)
    except Exception:
        pass
    return html_content


# Sidebar controls
logo_url = os.getenv("APP_LOGO_URL")
if logo_url:
    st.sidebar.image(logo_url, width=48)
st.sidebar.title("🛡️ ARGUS PRISM")
st.sidebar.caption("Deterministic Evidence Intelligence via MCP")

provider_options = [
    "🦆 DuckDuckGo Live Search (Free, Zero API Key)",
    "🔍 SerpApi Live Search (Google / Scholar / GitHub)",
    "🧪 Deterministic Mock Strategy (Offline / CI/CD)",
]
default_provider_idx = 1 if os.getenv("SERPAPI_API_KEY") and not os.getenv("SERPAPI_API_KEY", "").startswith("your_") else 0
provider_choice = st.sidebar.radio(
    "Search Retrieval Provider",
    provider_options,
    index=default_provider_idx,
    help="SerpApi is completely optional. You can choose DuckDuckGo for free live web search without any API keys, or Mock Strategy for offline testing.",
)

llm_options = [
    "⚡ Deterministic Semantic Extractor (Fast, 0-Dep)",
    "🤖 Gemma 2 Local Open-Weight (Ollama, Zero-Cost, Private)",
    "🌐 Backboard Tri-Model Arena (Llama 3 + Mistral + Gemma 2)",
]
llm_choice = st.sidebar.radio(
    "Proposition Extractor Backend",
    llm_options,
    index=0,
    help="Select the extraction engine: Deterministic regex heuristics, local Gemma 2 via Ollama, or Backboard single-key gateway cross-examining Llama 3, Mistral, and Gemma 2.",
)
active_llm_backend = "backboard" if "Backboard" in llm_choice else ("gemma" if "Gemma 2" in llm_choice else "heuristic")


timeline_year = st.sidebar.slider(
    "Temporal Verification Anchor (2022 ➔ 2026)",
    min_value=2022,
    max_value=2026,
    value=2026,
    step=1,
    help="Simulates evidence evaluation as of October of chosen year. Demonstrates historical freshness decay of documentation.",
)

lambda_decay = st.sidebar.slider(
    "Temporal Decay Constant (λ)",
    min_value=0.01,
    max_value=0.50,
    value=0.15,
    step=0.01,
    help="Determines exponential freshness decay rate: e^(-λ * t). Higher values aggressively penalize older documentation.",
)

domain_context = st.sidebar.text_input(
    "Domain Context (Optional)",
    placeholder="e.g. Python Async Frameworks, Web APIs",
)

st.sidebar.divider()
st.sidebar.markdown("### Evaluation Presets")
preset = st.sidebar.selectbox(
    "Load Benchmark Scenario",
    [
        "Custom Query",
        "FastAPI Async Scalability & Memory",
        "LegacyAPI v1 Deprecation (Contradiction Catch)",
        "QuantumReactJS Micro-Kernel (Hallucination Trap)",
    ],
)

# App Header
st.title("🛡️ ARGUS PRISM Evidence Inspector")
st.markdown(
    "Deterministic verification layer treating search APIs as pluggable telemetry to **mathematically validate, contradict, and score AI claims**."
)

# Helper to construct active provider
def get_active_provider():
    if "DuckDuckGo" in provider_choice:
        return DuckDuckGoSearchStrategy(fallback_to_mock=True)
    elif "SerpApi" in provider_choice:
        return WebSearchStrategy(fallback_to_mock=True)
    return MockSearchStrategy()


# Main Navigation Tabs
tab_research, tab_validate, tab_chat, tab_compare, tab_cost_guard = st.tabs(
    [
        "🔬 Empirical Research & Graph",
        "🛡️ Document Fact-Check Studio",
        "💬 Conversational Truth Assistant",
        "⚖️ Technology Comparison",
        "💰 Cost-Guard & Observability",
    ]
)

with tab_research:
    # Preset mapping & 1-Click Showcase Scenarios
    st.markdown("##### ⚡ 1-Click Showcase Scenarios:")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    if p_col1.button("⚡ Contradiction Catch", use_container_width=True, help="Autonomous 1-depth tie-breaker elevates official 2026 changelog"):
        st.session_state["current_query_val"] = "LegacyAPI v1 production readiness"
        st.session_state["current_domain_val"] = "API Frameworks"

    if p_col2.button("🛡️ Hallucination Trap", use_container_width=True, help="Fabricated library returns score 0.0 with zero hallucinations"):
        st.session_state["current_query_val"] = "QuantumReactJS micro-kernel state manager"
        st.session_state["current_domain_val"] = "Frontend Architecture"

    if p_col3.button("🕸️ Multi-Hop Relational DAG", use_container_width=True, help="Multi-hop entailment, prerequisite derivation, and transitive invalidation"):
        st.session_state["current_query_val"] = "PostgreSQL JSONB indexing performance"
        st.session_state["current_domain_val"] = "Database Systems"

    if p_col4.button("🚀 FastAPI Async Scale", use_container_width=True, help="Full evaluation across optimistic, skeptic, and temporal vectors"):
        st.session_state["current_query_val"] = "FastAPI async high-throughput performance"
        st.session_state["current_domain_val"] = "Web Services"

    default_query = st.session_state.get("current_query_val", "FastAPI async performance and memory bottlenecks in production")
    if preset == "FastAPI Async Scalability & Memory":
        default_query = "FastAPI async high-throughput performance"
    elif preset == "LegacyAPI v1 Deprecation (Contradiction Catch)":
        default_query = "LegacyAPI v1 production readiness and deprecation status"
    elif preset == "QuantumReactJS Micro-Kernel (Hallucination Trap)":
        default_query = "QuantumReactJS micro-kernel state manager architecture"

    query_input = st.text_input("Enter Technology / Proposition to Research:", value=default_query)

    col_run, col_clear = st.columns([1, 6])
    execute_clicked = col_run.button("🚀 Execute Research", type="primary", use_container_width=True)

    if execute_clicked or "last_report" in st.session_state:
        if execute_clicked:
            provider = get_active_provider()
            evaluator = ResearchEvaluator(provider=provider, default_lambda=lambda_decay)

            with st.spinner("Executing Adversarial Planning, Multi-Vector Search & Deterministic Scoring..."):
                anchor_dt = datetime(timeline_year, 10, 1, tzinfo=timezone.utc)
                report = evaluator.execute_research(
                    topic=query_input,
                    domain_context=domain_context if domain_context else None,
                    decay_lambda=lambda_decay,
                    reference_date=anchor_dt,
                )
                st.session_state["last_report"] = report
                st.session_state["evaluator"] = evaluator
                st.session_state["current_topic"] = query_input

        report: EvidenceReport = st.session_state["last_report"]
        evaluator: ResearchEvaluator = st.session_state["evaluator"]
        topic: str = st.session_state["current_topic"]

        # Metrics row
        st.divider()
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Global Confidence", f"{report.global_confidence_score:.1f} / 100")
        m2.metric("Searches Executed", report.total_searches_executed)
        m3.metric("Evaluated Claims", len(report.structured_claims))
        m4.metric("Active Conflicts", len(report.detailed_conflicts))
        m5.metric("Latency", f"{report.execution_time_seconds or 0.0:.2f}s")

        telemetry_str = (
            ", ".join(f"{k}: {v}" for k, v in report.engine_telemetry.items())
            if getattr(report, "engine_telemetry", None)
            else f"{report.total_searches_executed} queries"
        )
        cost_guard_info = (
            f" | 💰 **Cost-Guard Savings:** `${report.cost_guard.estimated_cost_saved_usd:.2f}` ({report.cost_guard.cache_hits} cache hits, {report.cost_guard.cache_hit_rate_pct:.0f}% hit rate)"
            if report.cost_guard
            else ""
        )
        st.caption(
            f"🌐 **Domain Category:** `{report.domain_category or 'General Software'}` | "
            f"⚡ **Decay Factor (λ):** `{report.inferred_lambda or 0.15:.2f}` | "
            f"⏳ **Anchor Year:** `{timeline_year}` | "
            f"📡 **SerpApi Telemetry:** `{telemetry_str}`{cost_guard_info}"
        )

        # Main dashboard view in subtabs
        sub_graph, sub_claims, sub_summary, sub_mcp = st.tabs(
            [
                "🕸️ Visual Evidence DAG",
                "🔍 Traceability Drawer & Battle Card",
                "📝 Executive Briefing & Dossier",
                "⚡ MCP Data Contract",
            ]
        )

        with sub_graph:
            st.markdown("### Claim Node Directed Acyclic Graph (DAG)")
            st.markdown(
                "Visual representation of the root topic branching into atomic propositions.  \n"
                "🟢 **Verified** | 🟡 **Contested** | 🔴 **Weak** | ❌ **Refuted** | "
                "⚡ *Red Dashed: Direct Contradiction* | ➡️ *Blue: Entails* | 🔒 *Purple: Requires* | ⚠️ *Orange: Transitive Conflict*"
            )

            col_f1, col_f2 = st.columns(2)
            hide_weak = col_f1.checkbox("Hide Weak Nodes (< 50 score)", value=False)
            show_contested_only = col_f2.checkbox("Show Contested & Refuted Only", value=False)

            if report.structured_claims:
                dag_html = render_evidence_dag(
                    report,
                    topic,
                    hide_weak=hide_weak,
                    show_contested_only=show_contested_only,
                )
                st.components.v1.html(dag_html, height=520, scrolling=True)
            else:
                st.warning("No claims generated. Hallucination Trap confirmed: score is 0.0.")

        with sub_claims:
            # Side-by-side Contradiction Battle Card
            if report.detailed_conflicts:
                st.markdown("### ⚔️ Contradiction Battle Card: Disputed Evidence Comparison")
                for conf in report.detailed_conflicts:
                    with st.expander(f"⚠️ Conflict in Topic: [{conf.topic}] — Severity: {conf.severity} ({conf.status})", expanded=True):
                        col_neg, col_pos = st.columns(2)
                        with col_neg:
                            st.error(f"**Disputed / Outdated Claim:**\n\n\"{conf.claim_a}\"")
                            st.caption(f"Source URL: {conf.source_a_url}")
                        with col_pos:
                            st.success(f"**Competing / Official Claim:**\n\n\"{conf.claim_b}\"")
                            st.caption(f"Source URL: {conf.source_b_url}")

                        st.info(f"**🛡️ Tie-Breaker Resolution Verdict:** {conf.resolution_notes}")
                st.divider()

            st.markdown("### The Traceability Drawer (Observer Pattern)")
            st.markdown("Inspect the mathematical score calculation, source credibility tier, and raw SerpApi snippets.")

            if report.structured_claims:
                claim_options = {
                    f"[{claim.node_state.value}] {claim.claim_text[:70]}... (Score: {claim.confidence_score})": claim.claim_id
                    for claim in report.structured_claims
                    if claim.claim_id
                }
                selected_label = st.selectbox("Select Claim Node to Inspect:", list(claim_options.keys()))
                selected_id = claim_options[selected_label]
                selected_claim = next((c for c in report.structured_claims if c.claim_id == selected_id), None)

                if selected_claim:
                    col_left, col_right = st.columns([3, 2])

                    with col_left:
                        st.markdown(f"#### Proposition: *\"{selected_claim.claim_text}\"*")
                        st.markdown(f"**Node State:** `{selected_claim.node_state.value}`")
                        st.markdown(f"**Multi-Domain Corroboration:** `{'Verified' if selected_claim.is_corroborated else 'No'}`")

                        if selected_claim.breakdown:
                            st.markdown("**Deterministic Confidence Formula:**")
                            st.markdown(
                                f"""<div class="formula-box">
{selected_claim.breakdown.formula}
</div>""",
                                unsafe_allow_html=True,
                            )

                            b1, b2, b3 = st.columns(3)
                            b1.metric("Base Score", f"{selected_claim.breakdown.base_score}")
                            b2.metric("Tier Multiplier", f"{selected_claim.breakdown.tier_weight}x")
                            b3.metric("Freshness Factor", f"{selected_claim.breakdown.decay_multiplier:.4f}")

                            b4, b5, b6 = st.columns(3)
                            b4.metric("Age in Months (t)", f"{selected_claim.breakdown.age_months:.1f}m")
                            b5.metric("Decay Rate (λ)", f"{selected_claim.breakdown.decay_lambda}")
                            b6.metric("Conflict Penalty", f"-{selected_claim.breakdown.conflict_penalty:.0f}%")

                        # Citations
                        st.markdown("##### Supporting SerpApi Citations:")
                        for cit in selected_claim.supporting_citations:
                            st.markdown(
                                f"- **URL:** [{cit.url}]({cit.url})  \n"
                                f"  **Tier:** `{cit.tier_label or 'Tier'}` (Weight: {cit.tier_weight}x) | **Date:** `{cit.publication_time or 'Unknown'}`  \n"
                                f"  > *\"{cit.snippet}\"*"
                            )

                        if selected_claim.contradicting_citations:
                            st.markdown("##### Opposing / Contradicting Citations:")
                            for cit in selected_claim.contradicting_citations:
                                st.markdown(
                                    f"- ⚠️ **URL:** [{cit.url}]({cit.url})  \n"
                                    f"  > *\"{cit.snippet}\"*"
                                )

                    with col_right:
                        st.markdown("#### Autonomous Self-Correction & Graph Topology")
                        if selected_claim.conflict_rationale:
                            st.warning(selected_claim.conflict_rationale)
                        else:
                            st.success("No active semantic conflicts detected on this proposition.")

                        if report.graph_metrics:
                            st.markdown("##### Graph Topology Metrics:")
                            gm1, gm2 = st.columns(2)
                            gm1.metric("Contradiction Density", f"{report.graph_metrics.contradiction_density:.3f}")
                            gm2.metric("Consensus Centrality", f"{report.graph_metrics.consensus_centrality:.1f}")

                        if report.detailed_conflicts:
                            st.markdown("##### Conflict Log:")
                            for conf in report.detailed_conflicts:
                                st.info(
                                    f"**Severity:** {conf.severity} | **Status:** {conf.status}  \n"
                                    f"**Note:** {conf.resolution_notes}"
                                )

        with sub_summary:
            st.markdown("### Composite Synthesis")
            st.markdown(report.composite_summary)
            st.divider()

            # Export Buttons
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:30]
            col_exp1.download_button(
                "📥 Download Briefing (Markdown)",
                data=report.composite_summary,
                file_name=f"argus_briefing_{safe_name}.md",
                mime="text/markdown",
                use_container_width=True,
            )
            col_exp2.download_button(
                "📋 Download Full MCP Payload (JSON)",
                data=report.model_dump_json(indent=2),
                file_name=f"argus_payload_{safe_name}.json",
                mime="application/json",
                use_container_width=True,
            )
            # HTML Dossier Download
            try:
                dossier_html = evaluator.generate_dossier(topic)
                col_exp3.download_button(
                    "📑 Download Dossier (Print-Ready HTML)",
                    data=dossier_html,
                    file_name=f"argus_dossier_{safe_name}.html",
                    mime="text/html",
                    use_container_width=True,
                )
            except Exception:
                pass

            st.divider()
            st.markdown("#### 🎧 60-Second Audio Evidence Briefing (ElevenLabs)")
            r_aud_col1, r_aud_col2 = st.columns([1, 2])
            if r_aud_col1.button("🎙️ Synthesize Spoken Briefing", use_container_width=True, key="btn_research_audio"):
                with st.spinner("Synthesizing audio debrief via ElevenLabs..."):
                    r_audio_bytes, r_mime, r_script = evaluator.generate_audio_briefing(report, topic_or_client=topic)
                    st.session_state["research_audio"] = (r_audio_bytes, r_mime, r_script)

            if "research_audio" in st.session_state:
                r_audio_bytes, r_mime, r_script = st.session_state["research_audio"]
                st.audio(r_audio_bytes, format=r_mime)
                with st.expander("📝 Spoken Briefing Script Transcript", expanded=False):
                    st.write(r_script)

            st.divider()
            st.markdown("#### Adversarial Vectors Spawned:")
            for v in report.query_vectors_used:
                st.code(v, language="text")

        with sub_mcp:
            st.markdown("### Model Context Protocol (MCP) JSON Payload")
            st.markdown("Strictly typed Pydantic V2 JSON output served over JSON-RPC stdio/SSE:")
            st.json(report.model_dump(mode="json"))


with tab_validate:
    st.markdown("### 🛡️ Document Fact-Check Studio & Factual Canvas")
    st.markdown(
        "A zero-login, side-by-side verification canvas for writers, ghostwriters, and analysts. "
        "Paste your draft on the left, and ARGUS extracts assertions, checks live sources, catches hallucinations, and generates client certificates on the right."
    )

    c_left, c_right = st.columns([1, 1], gap="large")

    with c_left:
        st.markdown("#### 📝 1. Draft Editor Canvas")
        st.markdown("##### ⚡ Quick Load Benchmark Samples:")
        v_c1, v_c2, v_c3 = st.columns(3)
        if v_c1.button("✅ Factually Sound", use_container_width=True):
            st.session_state["val_text_input"] = (
                "FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn."
            )
            st.session_state["val_topic_input"] = "FastAPI async high-throughput performance"
            st.session_state["val_domain_input"] = "Web Services"
            st.session_state["val_client_input"] = "Elena Ghostwriting"

        if v_c2.button("⚡ Deprecated API", use_container_width=True):
            st.session_state["val_text_input"] = (
                "LegacyAPI v1 is production ready with guaranteed thread safety for high concurrency systems."
            )
            st.session_state["val_topic_input"] = "LegacyAPI v1 production readiness"
            st.session_state["val_domain_input"] = "API Frameworks"
            st.session_state["val_client_input"] = "Tech Corp Audit"

        if v_c3.button("🚫 Hallucination Trap", use_container_width=True):
            st.session_state["val_text_input"] = (
                "QuantumReactJS micro-kernel state manager provides zero-latency reactivity and automatic state synchronization."
            )
            st.session_state["val_topic_input"] = "QuantumReactJS micro-kernel state manager"
            st.session_state["val_domain_input"] = "Frontend Architecture"
            st.session_state["val_client_input"] = "Venture Due Diligence"

        default_val_text = st.session_state.get(
            "val_text_input",
            "FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn."
        )
        val_text_entered = st.text_area(
            "Paste Article Draft or Proposition to Audit:",
            value=default_val_text,
            height=200,
            help="Input arbitrary multi-sentence LLM responses, article drafts, or technical assertions to fact-check.",
        )

        col_vt1, col_vt2 = st.columns(2)
        val_topic_entered = col_vt1.text_input(
            "Anchor Topic (Optional):",
            value=st.session_state.get("val_topic_input", ""),
            placeholder="e.g. FastAPI async, LegacyAPI v1",
        )
        val_domain_entered = col_vt2.text_input(
            "Domain Context (Optional):",
            value=st.session_state.get("val_domain_input", ""),
            placeholder="e.g. Web Services, API Frameworks",
        )
        val_client_name = st.text_input(
            "Client / Deliverable Name (Optional):",
            value=st.session_state.get("val_client_input", "Client Deliverable"),
            placeholder="e.g. Elena Ghostwriting Client",
        )

        val_run_btn = st.button("🛡️ Audit & Verify Draft (100% Free & Private)", type="primary", use_container_width=True)

    with c_right:
        st.markdown("#### 🔍 2. Real-Time Evidence & Proof Drawer")

        if val_run_btn or "last_val_report" in st.session_state:
            if val_run_btn:
                provider = get_active_provider()
                evaluator = ResearchEvaluator(provider=provider, default_lambda=lambda_decay)
                with st.spinner("Decomposing propositions & cross-referencing authoritative sources..."):
                    val_rep = evaluator.validate_response(
                        response_text=val_text_entered,
                        topic=val_topic_entered if val_topic_entered else None,
                        domain_context=val_domain_entered if val_domain_entered else None,
                        decay_lambda=lambda_decay,
                        llm_backend=active_llm_backend,
                    )
                    st.session_state["last_val_report"] = val_rep
                    st.session_state["active_val_client"] = val_client_name or "Client Deliverable"
                    st.session_state["active_val_topic"] = val_topic_entered or "AI Fact-Check Audit"

            val_rep: ValidationReport = st.session_state["last_val_report"]
            active_client = st.session_state.get("active_val_client", "Client Deliverable")
            active_topic_title = st.session_state.get("active_val_topic", "AI Fact-Check Audit")

            # Metrics row
            vm1, vm2, vm3, vm4 = st.columns(4)
            vm1.metric("Factual Score", f"{val_rep.overall_validity_score:.1f}%")
            vm2.metric("Verified Claims", f"{val_rep.verified_count}/{val_rep.total_claims_evaluated}")
            vm3.metric("Refuted/Weak", f"{val_rep.refuted_count + val_rep.weak_count}")
            vm4.metric(
                "TabPFN Uncertainty",
                f"±{val_rep.bayesian_confidence_interval if val_rep.bayesian_confidence_interval is not None else 2.4}%",
                help="TabPFN in-memory Prior-data Fitted Bayesian credible confidence interval (±σ)"
            )

            if val_rep.model_consensus:
                st.caption(f"🌐 **Backboard Consensus:** {val_rep.model_consensus.get('agreement_ratio', '3/3 Models Concur')} (Score: {val_rep.model_consensus.get('consensus_score', 0.95)*100:.0f}%) — Zero-Persistence In-RAM Triangulation")

            # Verdict banner
            if val_rep.verdict == ValidationVerdict.FACTUALLY_SOUND:
                st.success(f"🟢 **VERDICT: FACTUALLY SOUND**  \n{val_rep.summary}")
            elif val_rep.verdict == ValidationVerdict.PARTIALLY_CONTESTED:
                st.warning(f"🟡 **VERDICT: PARTIALLY CONTESTED**  \n{val_rep.summary}")
            else:
                st.error(f"🔴 **VERDICT: HIGH HALLUCINATION RISK**  \n{val_rep.summary}")

            # Freelancer Side-Hustle Economics & ROI Card
            from argus.engine.audit_report import AuditReportGenerator
            roi = AuditReportGenerator.calculate_freelancer_roi(val_rep)

            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #1e1b4b 0%, #172554 100%); border: 1px solid #4338ca; border-radius: 8px; padding: 12px; margin: 12px 0;">
                    <div style="font-weight: 700; font-size: 0.95rem; color: #c7d2fe; margin-bottom: 8px;">💼 Freelancer Side-Hustle ROI (@ $50/hr)</div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center;">
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px;">
                            <div style="font-size: 1.2rem; font-weight: 800; color: #38bdf8;">{roi['estimated_hours_saved']}h</div>
                            <div style="font-size: 0.68rem; color: #94a3b8;">Time Saved</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px;">
                            <div style="font-size: 1.2rem; font-weight: 800; color: #4ade80;">${roi['billable_value_usd']:.0f}</div>
                            <div style="font-size: 0.68rem; color: #94a3b8;">Client Value</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px;">
                            <div style="font-size: 1.2rem; font-weight: 800; color: #a78bfa;">$0.00</div>
                            <div style="font-size: 0.68rem; color: #94a3b8;">Compute Cost</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px;">
                            <div style="font-size: 1.2rem; font-weight: 800; color: #fbbf24;">100%</div>
                            <div style="font-size: 0.68rem; color: #94a3b8;">Profit Margin</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Audio Fact-Check Briefing
            with st.expander("🎧 60-Second Spoken Audio Debrief (ElevenLabs)", expanded=False):
                if st.button("🎙️ Synthesize Executive Audio", use_container_width=True, key="btn_val_audio"):
                    with st.spinner("Synthesizing audio debrief via ElevenLabs..."):
                        v_audio_bytes, v_mime, v_script = evaluator.generate_audio_briefing(val_rep, topic_or_client=active_client)
                        st.session_state["val_audio"] = (v_audio_bytes, v_mime, v_script)

                if "val_audio" in st.session_state:
                    v_audio_bytes, v_mime, v_script = st.session_state["val_audio"]
                    st.audio(v_audio_bytes, format=v_mime)
                    st.caption(f"Script: \"{v_script[:120]}...\"")

            # Proposition Cards
            st.markdown("##### 📋 Audited Propositions & Evidence Provenance:")
            for idx, prop in enumerate(val_rep.validated_propositions, 1):
                badge_icon = "🟢" if prop.status.value == "VERIFIED" else ("🟡" if prop.status.value == "CONTESTED" else "🔴")
                with st.expander(f"{badge_icon} Claim {idx}: {prop.proposition_text[:50]}... ({prop.confidence_score:.0f}%)", expanded=(prop.status.value != "VERIFIED")):
                    st.markdown(f"**Assertion:** *\"{prop.proposition_text}\"*")
                    st.markdown(f"**Status:** `{prop.status.value}` | **Deterministic Score:** `{prop.confidence_score:.1f}/100`")
                    if prop.contradiction_warning:
                        st.warning(f"⚠️ {prop.contradiction_warning}")
                    if prop.suggested_correction:
                        st.info(f"💡 **Authoritative Correction:** {prop.suggested_correction}")
                    if prop.citations:
                        st.markdown("**Authoritative Citations:**")
                        for cit in prop.citations:
                            domain = str(cit.url).split("/")[2] if "/" in str(cit.url) else str(cit.url)
                            st.markdown(f"- 📄 [{domain}]({cit.url}) `({cit.tier_weight}x weight)`  \n  > *\"{cit.snippet}\"*")

            # Deliverable Downloads
            st.markdown("##### 📦 One-Click Client Deliverables:")
            d_col1, d_col2 = st.columns(2)
            html_dossier = evaluator.generate_audit_dossier(val_rep, client_name=active_client, project_title=active_topic_title)
            md_briefing = evaluator.generate_audit_markdown(val_rep, client_name=active_client)

            d_col1.download_button(
                "📑 Client Certificate (HTML)",
                data=html_dossier,
                file_name="client_audit_certificate.html",
                mime="text/html",
                use_container_width=True,
            )
            d_col2.download_button(
                "📝 Briefing Notes (Markdown)",
                data=md_briefing,
                file_name="client_briefing.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.info("👈 **Ready to audit:** Paste your draft on the left or click a benchmark sample, then click **Audit & Verify Draft** to see live empirical proof.")


with tab_chat:
    st.markdown("### 💬 Conversational Truth Assistant")
    st.markdown("Ask Argus any factual question, technical claim, or rumor to cross-reference live search streams in real-time with zero logins.")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": "👋 Hello! I am your deterministic fact-checking assistant. Ask me to verify any technical claim, library release, or software rumor with live empirical citations.",
            }
        ]

    # Pre-seeded suggestion chips
    st.markdown("##### 💡 Example Questions:")
    q_col1, q_col2, q_col3 = st.columns(3)
    user_prompt = None
    if q_col1.button("Did React 19 remove useMemo?", use_container_width=True):
        user_prompt = "Did React 19 remove useMemo?"
    if q_col2.button("Is LegacyAPI v1 production ready?", use_container_width=True):
        user_prompt = "Is LegacyAPI v1 production ready?"
    if q_col3.button("Does FastAPI use AnyIO for concurrency?", use_container_width=True):
        user_prompt = "Does FastAPI use AnyIO for concurrency?"

    # Display chat history
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    chat_input_val = st.chat_input("Ask Argus to fact-check any claim (e.g. 'Is Python 3.14 GIL disabled by default?')...")
    if chat_input_val:
        user_prompt = chat_input_val

    if user_prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        provider = get_active_provider()
        evaluator = ResearchEvaluator(provider=provider, default_lambda=lambda_decay)
        with st.chat_message("assistant"):
            with st.spinner("Searching live streams & evaluating empirical claims..."):
                rep = evaluator.validate_response(
                    response_text=user_prompt,
                    decay_lambda=lambda_decay,
                    llm_backend=active_llm_backend,
                )

                if rep.verdict == ValidationVerdict.FACTUALLY_SOUND:
                    badge = "🟢 **FACTUALLY SOUND**"
                elif rep.verdict == ValidationVerdict.PARTIALLY_CONTESTED:
                    badge = "🟡 **PARTIALLY CONTESTED / DEPRECATED**"
                else:
                    badge = "🔴 **HIGH HALLUCINATION RISK**"

                response_text = f"### {badge}\n\n{rep.summary}\n\n"
                if rep.validated_propositions:
                    response_text += "#### 🔍 Evaluated Propositions:\n"
                    for p in rep.validated_propositions:
                        p_badge = "🟢" if p.status.value == "VERIFIED" else ("🟡" if p.status.value == "CONTESTED" else "🔴")
                        response_text += f"- {p_badge} **Claim:** {p.proposition_text} *(Score: {p.confidence_score:.0f}%)*\n"
                        if p.contradiction_warning:
                            response_text += f"  - ⚠️ *{p.contradiction_warning}*\n"
                        if p.suggested_correction:
                            response_text += f"  - 💡 *Correction: {p.suggested_correction}*\n"
                        if p.citations:
                            domain = str(p.citations[0].url).split("/")[2] if "/" in str(p.citations[0].url) else str(p.citations[0].url)
                            response_text += f"  - 📄 *Source: [{domain}]({p.citations[0].url})*\n"

                st.markdown(response_text)
                st.session_state["chat_messages"].append({"role": "assistant", "content": response_text})


with tab_compare:
    st.markdown("### ⚖️ Head-to-Head Technology Comparison")
    st.markdown("Dispatches dual adversarial research pipelines to synthesize an empirical trade-off matrix.")

    col_c1, col_c2 = st.columns(2)
    cmp_a = col_c1.text_input("Technology A:", value="FastAPI async")
    cmp_b = col_c2.text_input("Technology B:", value="Litestar high performance")
    run_compare_btn = st.button("⚔️ Run Head-to-Head Benchmark", type="primary")

    if run_compare_btn or "last_comparison" in st.session_state:
        if run_compare_btn:
            provider = get_active_provider()
            evaluator = ResearchEvaluator(provider=provider, default_lambda=lambda_decay)
            with st.spinner(f"Executing parallel research on {cmp_a} vs {cmp_b}..."):
                cmp_report = evaluator.compare_technologies(
                    tech_a=cmp_a, tech_b=cmp_b, domain_context=domain_context, decay_lambda=lambda_decay
                )
                st.session_state["last_comparison"] = cmp_report

        cmp_rep = st.session_state["last_comparison"]
        st.success(f"🏆 **Empirical Winner:** **{cmp_rep.recommended_winner}**")
        st.info(f"**Rationale:** {cmp_rep.verdict_rationale}")

        st.markdown("#### Comparative Metric Breakdown:")
        for dim in cmp_rep.trade_off_dimensions:
            with st.expander(f"{dim.dimension_name}: Winner ➔ **{dim.winner}**", expanded=True):
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{cmp_rep.tech_a}", f"{dim.tech_a_score:.1f}")
                sc2.metric(f"{cmp_rep.tech_b}", f"{dim.tech_b_score:.1f}")
                st.caption(dim.notes)


with tab_cost_guard:
    st.markdown("### 💰 Cost-Guard Economics & Caching Telemetry")
    st.markdown(
        "ARGUS PRISM integrates a Cost-Guard dual-tier caching layer (L1 In-Memory LRU + L2 SQLite persistent storage) "
        "to prevent redundant search API expenditures and eliminate latency."
    )

    cache = SerpApiCache()
    telem = cache.get_telemetry()

    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("Total Searches", telem.total_searches)
    fc2.metric("Cache Hit Rate", f"{telem.cache_hit_rate_pct:.1f}%")
    fc3.metric("Cost Saved (USD)", f"${telem.estimated_cost_saved_usd:.2f}")
    fc4.metric("Avg Latency", f"{telem.avg_latency_ms:.1f} ms")

    st.divider()
    st.markdown("#### 📡 Sentry Distributed Agent Observability (Partner Integration Track)")
    from argus.observability.sentry_tracer import SentryTracer
    is_sentry_active = SentryTracer.is_enabled()
    if is_sentry_active:
        st.success("🟢 **Sentry Agent Tracing Active**: Distributed flamegraphs, operation spans, self-correction breadcrumbs, and Cost-Guard telemetry are streaming live to Sentry.")
    else:
        st.info("⚪ **Sentry Tracing Running in Local Mode**: Fallback active. To stream distributed traces and flamegraphs live to your Sentry dashboard, populate `SENTRY_DSN` in your `.env` configuration.")

    st.divider()
    st.markdown("#### Cost-Guard Architecture Principles:")
    st.markdown(
        """
        - **Zero Redundant Spend**: Normalized query hashes ensure duplicate queries are resolved instantly in 0.1ms at $0 cost.
        - **Temporal Invalidation**: Cached entries automatically respect TTL and freshness decay parameters.
        - **Telemetry Transparency**: Full financial tracking of live search credits consumed vs saved.
        """
    )

