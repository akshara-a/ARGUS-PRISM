"""ARGUS PRISM: Dynamic SVG Verification Badge Generator.

Generates official vector badges (Shields.io standard) for GitHub READMEs,
Notion databases, Substack headers, and developer documentation.
"""

import html
import os
from typing import Optional


class BadgeGenerator:
    """Generates deterministic SVG verification badges."""

    @staticmethod
    def generate_svg(
        score: float = 91.5,
        verdict: str = "FACTUALLY_SOUND",
        left_label: str = "ARGUS PRISM",
    ) -> str:
        """Produce clean, vector-rendered SVG badge with color-coded integrity status."""
        v_upper = (verdict or "").upper()
        if "SOUND" in v_upper or score >= 70.0:
            bg_right = "#059669"  # Emerald 600
            status_text = f"{score:.1f}% · VERIFIED"
        elif "CONTESTED" in v_upper or score >= 40.0:
            bg_right = "#d97706"  # Amber 600
            status_text = f"{score:.1f}% · CAUTION"
        else:
            bg_right = "#e11d48"  # Rose 600
            status_text = f"{score:.1f}% · UNVERIFIED"

        clean_left = html.escape((left_label or "ARGUS PRISM").strip())
        clean_right = html.escape(status_text)

        # Calculate approximate pixel widths (approx 6.5-7.0px per char + 18px padding)
        w_left = max(86, int(len(clean_left) * 7.2 + 16))
        w_right = max(98, int(len(clean_right) * 6.8 + 16))
        total_w = w_left + w_right
        h = 24

        x_left = round(w_left / 2, 1)
        x_right = round(w_left + (w_right / 2), 1)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}" viewBox="0 0 {total_w} {h}" role="img" aria-label="{clean_left}: {clean_right}">
  <title>{clean_left}: {clean_right}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".12"/>
    <stop offset="1" stop-opacity=".08"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_w}" height="{h}" rx="5" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{w_left}" height="{h}" fill="#18181b"/>
    <rect x="{w_left}" width="{w_right}" height="{h}" fill="{bg_right}"/>
    <rect width="{total_w}" height="{h}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif" font-size="11" font-weight="600">
    <text x="{x_left}" y="16" fill="#000" opacity=".3">{clean_left}</text>
    <text x="{x_left}" y="15" fill="#f4f4f5">{clean_left}</text>
    <text x="{x_right}" y="16" fill="#000" opacity=".3">{clean_right}</text>
    <text x="{x_right}" y="15" fill="#ffffff">{clean_right}</text>
  </g>
</svg>"""

    @classmethod
    def generate_markdown_snippet(
        cls,
        score: float,
        verdict: str,
        base_url: Optional[str] = None,
        target_link: Optional[str] = None,
    ) -> str:
        """Return copyable markdown badge embed snippet."""
        active_base = (base_url or os.getenv("ARGUS_API_BASE_URL", "")).rstrip("/")
        active_target = target_link or os.getenv("ARGUS_REPO_URL", "")
        badge_url = f"{active_base}/api/badge?score={score:.1f}&amp;verdict={verdict}"
        return f"[![ARGUS PRISM Factual Verification]({badge_url})]({active_target})"

    @classmethod
    def generate_html_snippet(
        cls,
        score: float,
        verdict: str,
        base_url: Optional[str] = None,
        target_link: Optional[str] = None,
    ) -> str:
        """Return copyable HTML badge embed snippet."""
        active_base = (base_url or os.getenv("ARGUS_API_BASE_URL", "")).rstrip("/")
        active_target = target_link or os.getenv("ARGUS_REPO_URL", "")
        badge_url = f"{active_base}/api/badge?score={score:.1f}&amp;verdict={verdict}"
        return f'<a href="{active_target}" target="_blank" rel="noopener noreferrer"><img src="{badge_url}" alt="ARGUS PRISM Factual Verification" /></a>'
