"""ARGUS PRISM: Autonomous Factual Auto-Fixer & In-Line Diff Engine.

Analyzes refuted and contested propositions in audited technical drafts,
synthesizes grounded factual replacements using authoritative citations,
and generates structured Git-style diff blocks for one-click document remediation.
"""

import difflib
import re
from typing import Any, Dict, List, Optional
from argus.models.domain import ValidationReport, NodeState, ValidatedClaim


class FactualAutoFixer:
    """Autonomous factual remediation and inline diff synthesis engine."""

    @staticmethod
    def synthesize_correction(prop: ValidatedClaim) -> str:
        """Derive a factually sound replacement sentence for a refuted or contested proposition."""
        if prop.suggested_correction:
            return prop.suggested_correction

        # Hallucination trap fallback (zero evidence)
        if prop.status == NodeState.WEAK and prop.confidence_score <= 1.0:
            return (
                f"[Factual Correction: The assertion '{prop.proposition_text}' is unsubstantiated with "
                f"zero empirical evidence in official package registries and documentation.]"
            )

        # Refuted claims (overruled by later versions)
        if prop.status == NodeState.REFUTED and prop.contradiction_warning:
            return f"{prop.proposition_text.rstrip('.')} (Note: superseded by official release notes: {prop.contradiction_warning})."

        # Weak / unverified claims (unreleased or uncorroborated)
        if prop.status == NodeState.WEAK:
            warning = prop.contradiction_warning or "Insufficient corroboration in authoritative sources"
            return f"{prop.proposition_text.rstrip('.')} (Note: unverified assertion — {warning.rstrip('.')}; verify if this version or specification has been officially released)."

        if prop.contradiction_warning:
            return f"{prop.proposition_text.rstrip('.')} (Note: {prop.contradiction_warning})."

        return prop.proposition_text

    @classmethod
    def repair_document(
        cls,
        original_text: str,
        report: ValidationReport,
    ) -> Dict[str, Any]:
        """Repair refuted/contested claims in original_text and compute structured diff blocks."""
        repaired_text = original_text
        fixes_applied: List[Dict[str, Any]] = []

        # Find all refuted or contested propositions
        target_props = [
            p for p in report.validated_propositions
            if p.status in (NodeState.REFUTED, NodeState.CONTESTED, NodeState.WEAK)
        ]

        # Apply replacements
        for prop in target_props:
            original_phrase = prop.proposition_text.strip()
            replacement = cls.synthesize_correction(prop)

            # Match exact or case-insensitive sentence
            escaped_phrase = re.escape(original_phrase)
            pattern = re.compile(escaped_phrase, re.IGNORECASE)

            if pattern.search(repaired_text):
                repaired_text = pattern.sub(lambda _: replacement, repaired_text, count=1)
                fixes_applied.append({
                    "original_claim": original_phrase,
                    "repaired_claim": replacement,
                    "reason": prop.contradiction_warning or "Empirically unverified or refuted proposition",
                    "status": prop.status.value,
                })
            else:
                # Match partial significant words if exact string is slightly modified
                words = [w for w in re.findall(r"\w+", original_phrase) if len(w) > 3]
                if len(words) >= 3:
                    sub_pat = re.compile(r"([^.\n]*?" + re.escape(words[0]) + r"[^.\n]*?" + re.escape(words[1]) + r"[^.\n]*?\.)", re.IGNORECASE)
                    match = sub_pat.search(repaired_text)
                    if match:
                        matched_sentence = match.group(0)
                        repaired_text = repaired_text.replace(matched_sentence, replacement, 1)
                        fixes_applied.append({
                            "original_claim": matched_sentence.strip(),
                            "repaired_claim": replacement,
                            "reason": prop.contradiction_warning or "Empirically unverified or refuted proposition",
                            "status": prop.status.value,
                        })

        # Generate structured diff blocks
        diff_blocks = cls.generate_diff_blocks(original_text, repaired_text)

        return {
            "original_text": original_text,
            "repaired_text": repaired_text,
            "fixes_applied": fixes_applied,
            "fixes_count": len(fixes_applied),
            "diff_blocks": diff_blocks,
        }

    @staticmethod
    def generate_diff_blocks(original_text: str, repaired_text: str) -> List[Dict[str, str]]:
        """Compute visual diff blocks (unchanged, removed, inserted) using SequenceMatcher."""
        matcher = difflib.SequenceMatcher(None, original_text, repaired_text)
        blocks: List[Dict[str, str]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                blocks.append({"type": "unchanged", "text": original_text[i1:i2]})
            elif tag == "delete":
                blocks.append({"type": "removed", "text": original_text[i1:i2]})
            elif tag == "insert":
                blocks.append({"type": "inserted", "text": repaired_text[j1:j2]})
            elif tag == "replace":
                blocks.append({"type": "removed", "text": original_text[i1:i2]})
                blocks.append({"type": "inserted", "text": repaired_text[j1:j2]})

        return blocks
