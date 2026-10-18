"""Sentry Agent Tracing & Observability Layer for ARGUS PRISM."""

import contextlib
import logging
import os
import time
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Optional sentry_sdk import with graceful fallback
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None  # type: ignore
    SENTRY_AVAILABLE = False


class SentryTracer:
    """Manages Sentry distributed tracing, agent spans, breadcrumbs, and performance telemetry.
    
    Provides 100% crash-proof fallback when SENTRY_DSN is absent or sentry_sdk is unavailable.
    """

    _initialized: bool = False
    _is_enabled: bool = False

    @classmethod
    def init_tracer(
        cls,
        dsn: Optional[str] = None,
        environment: Optional[str] = None,
        sample_rate: Optional[float] = None,
    ) -> bool:
        """Initialize Sentry SDK with agent performance tracing."""
        if cls._initialized:
            return cls._is_enabled

        cls._initialized = True
        active_dsn = dsn or os.getenv("SENTRY_DSN")

        if not active_dsn or not SENTRY_AVAILABLE:
            cls._is_enabled = False
            logger.info("Sentry Agent Tracing disabled (no SENTRY_DSN provided). Running in local mode.")
            return False

        try:
            active_env = environment or os.getenv("SENTRY_ENVIRONMENT", "production")
            active_rate = sample_rate if sample_rate is not None else float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))

            sentry_sdk.init(
                dsn=active_dsn,
                environment=active_env,
                traces_sample_rate=active_rate,
                profiles_sample_rate=0.2,
                release="argus-prism@0.1.0",
                send_default_pii=False,  # Privacy preservation for proprietary client claims
            )
            sentry_sdk.set_tag("app.name", "argus-prism")
            sentry_sdk.set_tag("agent.version", "0.1.0")

            cls._is_enabled = True
            logger.info("Sentry Agent Tracing initialized successfully [env=%s, sample_rate=%.1f]", active_env, active_rate)
            return True
        except Exception as e:
            logger.warning("Failed to initialize Sentry SDK (%s). Running with tracing disabled.", e)
            cls._is_enabled = False
            return False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Sentry tracing is actively capturing telemetry."""
        return cls._is_enabled

    @classmethod
    @contextlib.contextmanager
    def trace_span(
        cls,
        op: str,
        description: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Generator[Any, None, None]:
        """Context manager to measure agent execution spans and performance flamegraphs."""
        start_time = time.time()

        if cls._is_enabled and sentry_sdk is not None:
            with sentry_sdk.start_span(op=op, description=description) as span:
                if data:
                    for k, v in data.items():
                        span.set_data(k, v)
                try:
                    yield span
                except Exception as e:
                    span.set_status("internal_error")
                    sentry_sdk.capture_exception(e)
                    raise
                finally:
                    elapsed_ms = (time.time() - start_time) * 1000.0
                    span.set_data("duration_ms", elapsed_ms)
        else:
            # Zero-overhead local fallback
            span_context = {"op": op, "description": description, "data": data or {}}
            try:
                yield span_context
            finally:
                span_context["elapsed_ms"] = (time.time() - start_time) * 1000.0

    @classmethod
    def record_breadcrumb(
        cls,
        category: str,
        message: str,
        level: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ):
        """Record an agent execution breadcrumb (e.g. tie-breaker decision, cache hit)."""
        if cls._is_enabled and sentry_sdk is not None:
            sentry_sdk.add_breadcrumb(
                category=category,
                message=message,
                level=level,
                data=data or {},
            )

    @classmethod
    def record_conflict_resolution(
        cls,
        topic: str,
        severity: str,
        claim_a: str,
        claim_b: str,
        resolution_notes: str,
    ):
        """Record an autonomous tie-breaker self-correction event for Sentry timeline."""
        cls.record_breadcrumb(
            category="agent.tie_breaker",
            message=f"Disambiguated contradiction on [{topic}] ({severity})",
            level="warning" if severity == "HIGH" else "info",
            data={
                "disputed_topic": topic,
                "opposing_a": claim_a[:80],
                "opposing_b": claim_b[:80],
                "resolution": resolution_notes[:100],
            },
        )

    @classmethod
    def record_cost_guard_metrics(
        cls,
        total_searches: int,
        cache_hits: int,
        cost_saved_usd: float,
        provider_name: str,
    ):
        """Record search economics and cache efficiency into Sentry context."""
        if cls._is_enabled and sentry_sdk is not None:
            sentry_sdk.set_tag("cost_guard.provider", provider_name)
            sentry_sdk.set_context(
                "cost_guard_telemetry",
                {
                    "total_searches": total_searches,
                    "cache_hits": cache_hits,
                    "cost_saved_usd": cost_saved_usd,
                    "hit_rate_pct": (cache_hits / max(1, total_searches)) * 100.0,
                },
            )
