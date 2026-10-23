"""Semantic Claim Extraction Node (Chain of Responsibility Component)."""

import hashlib
import re
from typing import List, Tuple
from argus.models.domain import Citation, Claim, NodeState, RawDocument


class ClaimExtractor:
    """Extracts atomic semantic propositions from normalized RawDocument snippets and titles."""

    # Sentence boundary delimiters
    SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

    # Semantic pattern markers indicating assertional engineering claims
    ASSERTION_PATTERNS = [
        re.compile(r"\b(is|are|was|were)\s+(officially\s+)?(deprecated|removed|unsupported|discontinued|legacy)\b", re.I),
        re.compile(r"\b(is|are|was|were)\s+(production\s+ready|recommended|stable|verified)\b", re.I),
        re.compile(r"\b(memory\s+leak|high\s+memory|bottleneck|garbage\s+collection\s+stall)\b", re.I),
        re.compile(r"\b(supports?|supported|provides?|features?|requires?|breaking\s+changes?)\b", re.I),
        re.compile(r"\b(fast|faster|slow|high\s+throughput|latency|stalls?)\b", re.I),
    ]

    def extract_claims(self, documents: List[RawDocument]) -> List[Tuple[Claim, RawDocument]]:
        """Extract atomic claims linked with their source RawDocument."""
        extracted: List[Tuple[Claim, RawDocument]] = []
        seen_claim_texts = set()

        for doc in documents:
            text_blocks = []
            if doc.title:
                text_blocks.append(doc.title.strip())
            if doc.snippet:
                text_blocks.append(doc.snippet.strip())

            full_text = ". ".join(text_blocks)
            full_text = re.sub(r"[\r\n]+", ". ", full_text)
            sentences = self.SPLIT_REGEX.split(full_text)

            for sentence in sentences:
                sentence_clean = sentence.strip()
                # Basic length and token filtering
                if len(sentence_clean) < 20 or len(sentence_clean.split()) < 4:
                    continue

                # Clean leading noise
                sentence_clean = re.sub(r"^[0-9\.\-\–\—\s:]+", "", sentence_clean)
                norm_key = sentence_clean.lower()

                if norm_key in seen_claim_texts:
                    continue
                seen_claim_texts.add(norm_key)

                # Generate deterministic claim ID
                claim_hash = hashlib.sha256(sentence_clean.encode("utf-8")).hexdigest()[:10]
                claim_id = f"claim_{claim_hash}"

                citation = Citation(
                    url=doc.url,  # validated by Pydantic HttpUrl
                    snippet=doc.snippet or sentence_clean,
                    publication_time=doc.publication_time,
                    tier_weight=1.0,  # to be mutated by CredibilityDecorator
                )

                claim = Claim(
                    claim_id=claim_id,
                    claim_text=sentence_clean,
                    confidence_score=50.0,
                    supporting_citations=[citation],
                    contradicting_citations=[],
                    is_corroborated=False,
                    node_state=NodeState.WEAK,
                )

                extracted.append((claim, doc))

        return extracted

    @classmethod
    def extract_claims_from_text(cls, text: str) -> List[str]:
        """Extract individual proposition statements from arbitrary LLM response text or user statements."""
        if not text or not text.strip():
            return []

        # Clean markdown headers, bold, bullets
        clean = text.strip()
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        candidate_sentences: List[str] = []

        for line in lines:
            # Strip markdown bullet markers, numbers, quote markers
            line_clean = re.sub(r"^[\*\-\#\d\.\s\:\>\–\—]+", "", line).strip()
            # Split line into sentences
            splits = cls.SPLIT_REGEX.split(line_clean)
            for s in splits:
                s_strip = s.strip()
                if s_strip:
                    candidate_sentences.append(s_strip)

        claims: List[str] = []
        seen = set()

        for s in candidate_sentences:
            s_clean = re.sub(r"^[\*\-\#\d\.\s\:\>\–\—]+", "", s).strip()
            s_clean = re.sub(r"[\*\_`]", "", s_clean)  # Strip markdown formatting
            if len(s_clean) < 15 or len(s_clean.split()) < 3:
                continue
            # Filter typical conversational pleasantries and filler
            if re.match(r"^(sure|here is|certainly|hope this helps|let me know|as an ai|in conclusion|summary:?|based on)\b", s_clean, re.I):
                continue
            key = s_clean.lower()
            if key not in seen:
                seen.add(key)
                claims.append(s_clean)

        # Fallback if no sentences passed filtering
        if not claims and len(text.strip()) >= 10:
            claims.append(text.strip())

        return claims
