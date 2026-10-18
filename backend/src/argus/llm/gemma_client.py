"""Gemma 2 Open-Weight LLM Integration (Ollama / Local Inference Engine)."""

import json
import logging
import os
import re
from typing import List, Dict, Optional, Any
import requests
from dotenv import load_dotenv

from argus.engine.extractor import ClaimExtractor

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_HOST = os.getenv("OLLAMA_HOST", "").rstrip("/")
DEFAULT_MODEL = os.getenv("GEMMA_MODEL_NAME", "gemma2:2b")
DEFAULT_ENDPOINT = os.getenv("OLLAMA_GENERATE_ENDPOINT", f"{DEFAULT_HOST}/api/generate" if DEFAULT_HOST else "")
TAGS_ENDPOINT = os.getenv("OLLAMA_TAGS_ENDPOINT", f"{DEFAULT_HOST}/api/tags" if DEFAULT_HOST else "")


class GemmaClient:
    """Client for Google's Gemma 2 open-weight models running locally via Ollama or local endpoint.
    
    Provides 100% private, zero-cost, local-first claim extraction and adversarial stance generation.
    Gracefully falls back to ARGUS's deterministic semantic heuristic extractor when the local daemon is offline.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        tags_endpoint: Optional[str] = None,
        timeout_seconds: float = 8.0,
    ):
        self.model_name = model_name or os.getenv("GEMMA_MODEL_NAME", DEFAULT_MODEL)
        self.endpoint = endpoint or os.getenv("OLLAMA_GENERATE_ENDPOINT", DEFAULT_ENDPOINT)
        self.tags_endpoint = tags_endpoint or os.getenv("OLLAMA_TAGS_ENDPOINT", TAGS_ENDPOINT)
        self.timeout_seconds = timeout_seconds
        self._is_available: Optional[bool] = None

    def is_available(self, force_check: bool = False) -> bool:
        """Check if local Ollama daemon hosting Gemma is reachable."""
        if self._is_available is not None and not force_check:
            return self._is_available

        try:
            resp = requests.get(self.tags_endpoint, timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                self._is_available = any(self.model_name in m or "gemma" in m for m in models) or len(models) > 0
                return self._is_available
        except Exception:
            pass

        self._is_available = False
        return False

    def extract_claims(self, text: str) -> List[str]:
        """Extract atomic propositions using local Gemma 2, falling back to heuristic parsing if offline."""
        if not text or not text.strip():
            return []

        if self.is_available():
            try:
                claims = self._query_gemma_for_claims(text)
                if claims:
                    return claims
            except Exception as e:
                logger.warning(f"Gemma inference failed ({e}); falling back to deterministic extractor.")

        # Deterministic semantic regex fallback
        return ClaimExtractor.extract_claims_from_text(text)

    def _query_gemma_for_claims(self, text: str) -> List[str]:
        """Send prompt to local Gemma 2 instance via Ollama JSON API."""
        prompt = (
            "You are a strict, objective fact-checking proposition parser.\n"
            "Task: Break down the following input text into atomic, independently verifiable factual statements.\n"
            "Rules:\n"
            "1. Output each statement on a new line prefixed with '- '.\n"
            "2. Strip out conversational pleasantries, opinions, and rhetorical filler.\n"
            "3. Do not include markdown headers, bold words, or explanations.\n\n"
            f"Input Text:\n{text}\n\n"
            "Atomic Propositions:"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic extraction
                "top_p": 0.9,
            },
        }

        resp = requests.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
        if resp.status_code == 200:
            result = resp.json().get("response", "")
            extracted = []
            for line in result.splitlines():
                clean_line = re.sub(r"^[\*\-\#\d\.\s\:\>\–\—]+", "", line).strip()
                if clean_line and len(clean_line) > 15:
                    extracted.append(clean_line)
            return extracted

        return []

    def synthesize_adversarial_stances(self, topic: str) -> Dict[str, str]:
        """Generate affirmative and skeptical debate stances for multi-vector evidence arbitration."""
        if self.is_available():
            try:
                prompt = (
                    f"Topic: {topic}\n"
                    "Formulate two opposing technical angles for adversarial validation:\n"
                    "1. AFFIRMATIVE: The strongest technical claim supporting production viability.\n"
                    "2. SKEPTICAL: The primary known failure mode, bottleneck, deprecation risk, or limitation.\n"
                    "Format:\nAFFIRMATIVE: <claim>\nSKEPTICAL: <claim>"
                )
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                }
                resp = requests.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
                if resp.status_code == 200:
                    text = resp.json().get("response", "")
                    aff = re.search(r"AFFIRMATIVE:\s*(.+)", text, re.I)
                    skep = re.search(r"SKEPTICAL:\s*(.+)", text, re.I)
                    if aff and skep:
                        return {
                            "affirmative": aff.group(1).strip(),
                            "skeptical": skep.group(1).strip(),
                            "engine": f"Gemma 2 ({self.model_name})",
                        }
            except Exception:
                pass

        # Heuristic fallback
        return {
            "affirmative": f"{topic} production benchmark efficiency and stability",
            "skeptical": f"{topic} known bottlenecks vulnerabilities and deprecation risks",
            "engine": "Deterministic Heuristic",
        }
