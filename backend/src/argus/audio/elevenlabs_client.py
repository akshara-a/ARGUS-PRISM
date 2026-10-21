"""ElevenLabs Audio Executive Briefing Generator for ARGUS PRISM."""

import io
import logging
import math
import os
import struct
import wave
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

from argus.models.domain import EvidenceReport, ValidationReport, ValidationVerdict

load_dotenv()
logger = logging.getLogger(__name__)


class ElevenLabsBriefing:
    """Generates broadcast-quality 60-second spoken executive audio briefings using ElevenLabs API.
    
    Includes a zero-dependency synthetic audio generator fallback when offline or when no API key is set.
    """

    DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
    API_URL = os.getenv("ELEVENLABS_API_ENDPOINT", "")

    VOICE_PERSONAS = {
        "rachel": {"id": os.getenv("ELEVENLABS_VOICE_RACHEL", os.getenv("ELEVENLABS_VOICE_ID", "")), "label": "Rachel (Executive Auditor)"},
        "adam": {"id": os.getenv("ELEVENLABS_VOICE_ADAM", ""), "label": "Adam (Skeptical Fact-Checker)"},
        "drew": {"id": os.getenv("ELEVENLABS_VOICE_DREW", ""), "label": "Drew (Technical Ghostwriter)"},
    }

    @classmethod
    def resolve_voice_id(cls, persona_or_id: Optional[str] = None) -> str:
        """Resolve persona identifier into a valid ElevenLabs voice ID strictly from environment variables."""
        default_vid = os.getenv("ELEVENLABS_VOICE_ID", "")
        if not persona_or_id:
            return default_vid

        p_clean = persona_or_id.lower().strip()
        if p_clean in ("rachel", "executive"):
            return os.getenv("ELEVENLABS_VOICE_RACHEL", os.getenv("ELEVENLABS_VOICE_ID", ""))
        elif p_clean in ("adam", "skeptical"):
            return os.getenv("ELEVENLABS_VOICE_ADAM", "")
        elif p_clean in ("drew", "ghostwriter"):
            return os.getenv("ELEVENLABS_VOICE_DREW", "")

        if p_clean in cls.VOICE_PERSONAS:
            return cls.VOICE_PERSONAS[p_clean]["id"] or default_vid
        return persona_or_id

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Fetch API key from environment."""
        key = os.getenv("ELEVENLABS_API_KEY")
        if key and not key.startswith("your_") and len(key) > 10:
            return key
        return None

    @classmethod
    def create_script_from_validation(cls, report: ValidationReport, client_name: str = "") -> str:
        """Compose a concise 45-60 second spoken briefing script from a ValidationReport."""
        verdict_text = "factually sound"
        if report.verdict == ValidationVerdict.PARTIALLY_CONTESTED:
            verdict_text = "partially contested with warnings"
        elif report.verdict == ValidationVerdict.HIGH_HALLUCINATION_RISK:
            verdict_text = "flagged for high hallucination risk"

        client_intro = f" for {client_name}" if client_name else ""

        # Find notable warnings or corrections to highlight
        key_highlight = ""
        for p in report.validated_propositions:
            if p.contradiction_warning:
                key_highlight = f"Notably, the proposition '{p.proposition_text[:60]}' was flagged: {p.contradiction_warning}"
                break

        if not key_highlight:
            key_highlight = f"All {report.verified_count} verified propositions matched authoritative documentation."

        script = (
            f"Hello. This is your ARGUS PRISM factual verification briefing{client_intro}. "
            f"Our deterministic consensus engine evaluated {report.total_claims_evaluated} atomic assertions. "
            f"The final factual integrity score is {report.overall_validity_score:.0f} percent, "
            f"resulting in a verdict of {verdict_text}. "
            f"{key_highlight} "
            f"A complete evidence dossier with clickable citations and mathematical proofs has been compiled for your review. "
            f"Thank you for using ARGUS PRISM."
        )
        return script

    @classmethod
    def create_script_from_research(cls, report: EvidenceReport, topic: str) -> str:
        """Compose a concise spoken briefing script from an EvidenceReport."""
        conflicts_count = len(report.detailed_conflicts)
        conflict_phrase = (
            f"Disambiguation resolved {conflicts_count} active documentation contradictions."
            if conflicts_count > 0
            else "Zero contradictions were detected in the primary evidence streams."
        )

        script = (
            f"Hello. This is the ARGUS PRISM executive evidence briefing for {topic}. "
            f"The multi-vector research pipeline evaluated {len(report.structured_claims)} technical propositions, "
            f"establishing a deterministic confidence score of {report.global_confidence_score:.0f} percent. "
            f"{conflict_phrase} "
            f"All findings have been grounded in verified primary sources and recorded in your evidence ledger."
        )
        return script

    @classmethod
    def synthesize_audio(
        cls,
        script: str,
        voice_id: str = DEFAULT_VOICE_ID,
        output_file: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """Synthesize spoken audio via ElevenLabs, or generate a valid synthetic audio chime if offline.
        
        Returns:
            Tuple of (audio_bytes, mime_type: "audio/mp3" or "audio/wav")
        """
        api_key = cls.get_api_key()
        effective_voice_id = cls.resolve_voice_id(voice_id)

        if api_key and effective_voice_id:
            endpoint_tpl = os.getenv("ELEVENLABS_API_ENDPOINT") or cls.API_URL
            if endpoint_tpl:
                try:
                    url = endpoint_tpl.format(voice_id=effective_voice_id)
                    headers = {
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": api_key,
                    }
                    payload = {
                        "text": script,
                        "model_id": "eleven_turbo_v2_5",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    }
                    response = requests.post(url, json=payload, headers=headers, timeout=20.0)
                    if response.status_code == 200:
                        audio_bytes = response.content
                        if output_file:
                            with open(output_file, "wb") as f:
                                f.write(audio_bytes)
                        return audio_bytes, "audio/mp3"
                    else:
                        logger.warning(f"ElevenLabs API returned {response.status_code}: {response.text}")
                except Exception as e:
                    logger.warning(f"ElevenLabs request error: {e}. Falling back to synthetic tone.")

        # Zero-dependency synthetic chime fallback (WAV audio format)
        audio_bytes = cls._generate_synthetic_tone(duration_seconds=3.0)
        if output_file:
            with open(output_file, "wb") as f:
                f.write(audio_bytes)
        return audio_bytes, "audio/wav"

    @classmethod
    def _generate_synthetic_tone(cls, duration_seconds: float = 2.5) -> bytes:
        """Generate a gentle harmonic audio chime in memory using Python standard library."""
        sample_rate = 22050
        num_samples = int(sample_rate * duration_seconds)
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            # Generate pleasant chord: 440Hz (A4) + 554.37Hz (C#5) + 659.25Hz (E5) with decay envelope
            chord_freqs = [440.0, 554.37, 659.25]
            frames = bytearray()

            for i in range(num_samples):
                t = i / sample_rate
                envelope = math.exp(-2.5 * t)  # Exponential decay
                val = sum(math.sin(2.0 * math.pi * f * t) for f in chord_freqs) / len(chord_freqs)
                sample = int(val * envelope * 24000)
                sample = max(-32767, min(32767, sample))
                frames.extend(struct.pack("<h", sample))

            wav_file.writeframes(frames)

        return buffer.getvalue()
