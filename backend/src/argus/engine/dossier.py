"""Enterprise Evidence Dossier Generator (Standalone Print-Ready HTML Document)."""

import html
from datetime import datetime, timezone
from argus.models.domain import EvidenceReport, NodeState


class DossierGenerator:
    """Generates standalone, auditable HTML evidence dossiers for engineering leadership."""

    @classmethod
    def generate_html(cls, report: EvidenceReport, topic: str) -> str:
        """Render complete HTML dossier."""
        safe_topic = html.escape(topic)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Claims ledger HTML
        claims_rows = ""
        for idx, c in enumerate(report.structured_claims, 1):
            state_color = "#22c55e" if c.node_state == NodeState.VERIFIED else ("#eab308" if c.node_state == NodeState.CONTESTED else ("#6b7280" if c.node_state == NodeState.REFUTED else "#ef4444"))
            url_links = "".join([
                f'<div><a href="{html.escape(str(cit.url), quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(cit.url.host if hasattr(cit.url, "host") else str(cit.url))}</a> ({cit.tier_weight}x)</div>'
                if str(cit.url).startswith(("http://", "https://"))
                else f'<div><span class="text-muted">{html.escape(str(cit.url))}</span> ({cit.tier_weight}x)</div>'
                for cit in c.supporting_citations[:2]
            ])
            formula_str = html.escape(c.breakdown.formula) if c.breakdown else "N/A"
            bayes_val = f"{c.breakdown.bayesian_posterior:.4f}" if c.breakdown and c.breakdown.bayesian_posterior else "N/A"

            claims_rows += f"""
            <tr>
                <td><strong>#{idx}</strong></td>
                <td><span class="badge" style="background-color: {state_color};">{c.node_state.value}</span></td>
                <td>{html.escape(c.claim_text)}</td>
                <td><strong>{c.confidence_score:.1f}</strong><br><small>Bayes: {bayes_val}</small></td>
                <td>{url_links}</td>
                <td><code>{formula_str}</code></td>
            </tr>
            """

        # Conflicts HTML
        conflicts_html = ""
        if report.detailed_conflicts:
            for conf in report.detailed_conflicts:
                src_a = str(conf.source_a_url or "")
                src_b = str(conf.source_b_url or "")
                link_a = (
                    f'<small><a href="{html.escape(src_a, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(src_a)}</a></small>'
                    if src_a.startswith(("http://", "https://"))
                    else f'<small class="text-muted">{html.escape(src_a)}</small>'
                )
                link_b = (
                    f'<small><a href="{html.escape(src_b, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(src_b)}</a></small>'
                    if src_b.startswith(("http://", "https://"))
                    else f'<small class="text-muted">{html.escape(src_b)}</small>'
                )

                conflicts_html += f"""
                <div class="conflict-card">
                    <div class="conflict-header">⚡ Contradiction [{html.escape(conf.topic)}] — Severity: {conf.severity} ({conf.status})</div>
                    <div class="conflict-grid">
                        <div class="col-neg">
                            <strong>🔴 Disputed Claim A:</strong><br>
                            "{html.escape(conf.claim_a)}"<br>
                            {link_a}
                        </div>
                        <div class="col-pos">
                            <strong>🟢 Competing Claim B:</strong><br>
                            "{html.escape(conf.claim_b)}"<br>
                            {link_b}
                        </div>
                    </div>
                    <div class="conflict-verdict"><strong>🛡️ Tie-Breaker Decision:</strong> {html.escape(conf.resolution_notes or '')}</div>
                </div>
                """
        else:
            conflicts_html = "<p class='text-muted'>Zero active contradictions detected in evidence corpus.</p>"

        # Cost-Guard & Graph Metrics
        density = f"{report.graph_metrics.contradiction_density:.3f}" if report.graph_metrics else "0.000"
        centrality = f"{report.graph_metrics.consensus_centrality:.1f}" if report.graph_metrics else "50.0"
        edges = report.graph_metrics.total_edges if report.graph_metrics else len(report.relations)
        cache_hits = report.cost_guard.cache_hits if report.cost_guard else 0
        cost_saved = f"${report.cost_guard.estimated_cost_saved_usd:.2f}" if report.cost_guard else "$0.00"

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARGUS PRISM Evidence Dossier: {safe_topic}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --muted: #94a3b8;
            --primary: #3b82f6;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 32px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 2.2rem;
            color: #60a5fa;
        }}
        .meta-row {{
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            color: var(--muted);
            font-size: 0.95rem;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 9999px;
            color: #fff;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #38bdf8;
        }}
        .stat-label {{
            font-size: 0.85rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .section-title {{
            font-size: 1.4rem;
            border-left: 4px solid var(--primary);
            padding-left: 12px;
            margin: 36px 0 16px 0;
        }}
        .summary-box {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 24px;
            font-size: 1.05rem;
        }}
        .conflict-card {{
            background: var(--surface);
            border: 1px solid #7f1d1d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .conflict-header {{
            font-weight: 700;
            color: #f87171;
            margin-bottom: 12px;
        }}
        .conflict-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 12px;
        }}
        .col-neg {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--danger);
            border-radius: 6px;
            padding: 12px;
        }}
        .col-pos {{
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid var(--success);
            border-radius: 6px;
            padding: 12px;
        }}
        .conflict-verdict {{
            background: #0284c7;
            border-radius: 6px;
            padding: 10px;
            font-size: 0.9rem;
            color: #fff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            font-size: 0.95rem;
        }}
        th, td {{
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: #0f172a;
            color: var(--muted);
            text-transform: uppercase;
            font-size: 0.8rem;
        }}
        a {{
            color: #38bdf8;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background: #0f172a;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 0.85rem;
            color: #f472b6;
        }}
        .footer {{
            margin-top: 64px;
            border-top: 1px solid var(--border);
            padding-top: 24px;
            text-align: center;
            color: var(--muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ ARGUS PRISM Evidence Dossier</h1>
            <div class="meta-row">
                <div><strong>Target Proposition:</strong> {safe_topic}</div>
                <div><strong>Domain:</strong> {report.domain_category or 'General Software'}</div>
                <div><strong>Generated:</strong> {now_str}</div>
                <div><strong>Engine:</strong> SerpApi Telemetry</div>
            </div>
        </div>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-value">{report.global_confidence_score:.1f}%</div>
                <div class="stat-label">Deterministic Confidence</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(report.structured_claims)}</div>
                <div class="stat-label">Evaluated Propositions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{density}</div>
                <div class="stat-label">Contradiction Density</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{centrality}</div>
                <div class="stat-label">Consensus Centrality</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{cost_saved}</div>
                <div class="stat-label">Cost-Guard Cache Savings ({cache_hits} hits)</div>
            </div>
        </div>

        <div class="section-title">Executive Evidence Briefing</div>
        <div class="summary-box">
            {report.composite_summary.replace(chr(10), "<br>")}
        </div>

        <div class="section-title">⚔️ Contradiction Analysis & Autonomous Disambiguation</div>
        {conflicts_html}

        <div class="section-title">📊 Evaluated Proposition Ledger</div>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Node State</th>
                    <th>Claim Text</th>
                    <th>Confidence</th>
                    <th>Citations & Tier</th>
                    <th>Deterministic Decay Proof</th>
                </tr>
            </thead>
            <tbody>
                {claims_rows}
            </tbody>
        </table>

        <div class="footer">
            Generated autonomously by <strong>ARGUS PRISM</strong> | Deterministic Evidence Intelligence Engine<br>
            All mathematical proofs and Bayesian probability derivations are 100% deterministic and reproducible.
        </div>
    </div>
</body>
</html>
"""
        return html_doc
