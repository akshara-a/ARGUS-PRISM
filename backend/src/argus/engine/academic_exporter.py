"""ARGUS PRISM: Academic & Publishing Exporter.

Converts verified technical drafts into publication-ready Markdown
with in-line numerical footnotes ([^1], [^2]) and an IEEE/APA-formatted
evidence bibliography suitable for Substack, Notion, Obsidian, and technical papers.
"""

import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from argus.models.domain import ValidationReport, NodeState, ValidatedClaim


class AcademicExporter:
    """Transforms validated articles into academic and publishing-grade Markdown with footnote citations."""

    @classmethod
    def export_publication_markdown(
        cls,
        text: str,
        report: ValidationReport,
        style: str = "ieee",
        author_or_client: str = "Elena Tech Ghostwriting",
    ) -> Dict[str, Any]:
        """Inject numerical footnote citations into text and append an authoritative bibliography."""
        annotated_text = text
        bibliography: List[Dict[str, Any]] = []
        footnote_index = 1
        citation_cache: Dict[str, int] = {}

        # Scan each verified or corroborated claim
        for prop in report.validated_propositions:
            if not prop.citations:
                continue

            # Pick primary citation
            primary_cit = prop.citations[0]
            cit_url = str(primary_cit.url)

            # Check if this citation URL was already assigned a footnote index
            if cit_url in citation_cache:
                assigned_idx = citation_cache[cit_url]
            else:
                assigned_idx = footnote_index
                citation_cache[cit_url] = assigned_idx
                
                # Derive title and host
                host = cit_url.split("/")[2] if "/" in cit_url else cit_url
                snippet_preview = primary_cit.snippet[:120].strip() if primary_cit.snippet else "Primary corroborating reference"
                
                bibliography.append({
                    "index": assigned_idx,
                    "url": cit_url,
                    "host": host,
                    "tier_weight": primary_cit.tier_weight,
                    "snippet": snippet_preview,
                    "proposition": prop.proposition_text,
                    "status": prop.status.value,
                })
                footnote_index += 1

            # Match proposition or sentence in text to append footnote marker
            clean_prop = prop.proposition_text.strip()
            footnote_marker = f"[^{assigned_idx}]"

            # Check if already has marker
            if footnote_marker not in annotated_text:
                pattern = re.compile(re.escape(clean_prop) + r"(\.|\?|\!)?", re.IGNORECASE)
                if pattern.search(annotated_text):
                    annotated_text = pattern.sub(rf"\g<0>{footnote_marker} ", annotated_text, count=1)
                else:
                    # Partial match
                    words = [w for w in re.findall(r"\w+", clean_prop) if len(w) > 3]
                    if len(words) >= 3:
                        sub_pat = re.compile(re.escape(words[0]) + r".*?" + re.escape(words[-1]) + r"(\.|\?|\!)?", re.IGNORECASE)
                        if sub_pat.search(annotated_text):
                            annotated_text = sub_pat.sub(rf"\g<0>{footnote_marker} ", annotated_text, count=1)

        # Build formatted bibliography in IEEE / APA style
        now_str = datetime.now(timezone.utc).strftime("%B %Y")
        bib_lines = [
            "",
            "---",
            "",
            "### 📚 References & Verified Empirical Sources",
            "",
        ]

        if not bibliography:
            bib_lines.append("*No external primary citations recorded.*")
        else:
            for item in sorted(bibliography, key=lambda x: x["index"]):
                idx = item["index"]
                url = item["url"]
                host = item["host"]
                tier_label = "Tier 1 (Authoritative)" if item["tier_weight"] >= 1.5 else "Tier 2 (Community)" if item["tier_weight"] >= 1.0 else "Tier 3 (Web)"
                
                if style.lower() == "apa":
                    # APA style: Author/Domain (Year). Title/Snippet. Retrieved from URL
                    bib_lines.append(
                        f"[^{idx}]: **{host}** ({now_str}). *\"{item['snippet']}...\"* "
                        f"[{tier_label}]. Available: [{url}]({url})"
                    )
                else:
                    # IEEE style: [1] Domain, "Snippet...", Tier, Month Year. [Online]. Available: URL
                    bib_lines.append(
                        f"[^{idx}]: {host}, *\"{item['snippet']}...\"* "
                        f"[{tier_label}]. Accessed {now_str}. Available: [{url}]({url})"
                    )

        report_topic = getattr(report, "topic", None) or "Technical Article"
        full_document = [
            f"# {report_topic}",
            f"> *Factually verified by **ARGUS PRISM** Consensus Intelligence Layer.*  ",
            f"> *Integrity Score: **{report.overall_validity_score:.1f}%** | Verdict: `{report.verdict.value}`*",
            "",
            annotated_text.strip(),
            "",
            "\n".join(bib_lines),
        ]

        formatted_markdown = "\n".join(full_document)

        return {
            "formatted_markdown": formatted_markdown,
            "annotated_body": annotated_text.strip(),
            "footnotes_count": len(bibliography),
            "bibliography": bibliography,
            "style": style.upper(),
        }
